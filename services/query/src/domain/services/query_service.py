from typing import AsyncIterator

import structlog

from ..models.generation import GeneratedAnswer, GenerationRequest, SourceCitation
from ..models.query import SearchQuery, ScoredChunk
from ..ports.llm_provider import LLMProvider
from .prompt_builder import PromptBuilder
from .retriever import RetrieverService

log = structlog.get_logger()

# Why two methods (answer_stream and answer)? 
# 
# Streaming is what users see in the UI — tokens appear as they're generated. 
# The non-streaming answer() is used for the cache check (you need the full answer to cache it) and for evaluation runs 
# (RAGAS needs complete answers).

class QueryService:
    def __init__(
        self,
        retriever: RetrieverService,
        llm: LLMProvider,
        prompt_builder: PromptBuilder,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._prompt_builder = prompt_builder

    async def answer_stream(self, query: str, top_k: int = 5) -> AsyncIterator:
        """
        Full RAG pipeline as an async generator of string tokens.
        Caller is responsible for wrapping tokens in SSE format.
        """
        
        # 1. Retrieve relevant chunks
        result = await self._retriever.retrieve(SearchQuery(text=query, top_k=top_k))
        log.info("query_service.retrieved", chunks=len(result.chunks), query=query[:60])
        
        if not result.chunks:
            yield "I don't have enough information to answer this question"
            return
        
        # 2. Build prompt
        user_prompt = self._prompt_builder.build_user_prompt(query, result.chunks)
        system_prompt = self._prompt_builder.system_prompt
        
        # 3. Stream tokens from LLM
        log.info("query_service.generating", model="ollama")
        async for token in self._llm.generate(system_prompt, user_prompt, stream=True):
            yield token
        
    async def answer(self, query: str, top_k: int = 5) -> GeneratedAnswer:
        """
        Non-streaming version — buffers the full answer.
        Used for caching and testing.
        """
        tokens = []
        result = await self._retriever.retrieve(SearchQuery(text=query, top_k=top_k))
        
        if not result.chunks:
            return GeneratedAnswer(
                answer="I don't have enough information to answer this question.",
                sources=[]
            )
        
        user_prompt = self._prompt_builder.build_user_prompt(query, result.chunks)
        async for token in self._llm.generate(
            self._prompt_builder.system_prompt, user_prompt, stream=False
        ):
            tokens.append(token)
            
        sources = [
            SourceCitation(title=c.title, url=c.source_url, score=c.score)
            for c in result.chunks
        ]
        
        return GeneratedAnswer(answer="".join(tokens), sources=sources)