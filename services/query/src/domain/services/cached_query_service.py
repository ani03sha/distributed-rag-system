import structlog

from ..models.generation import GeneratedAnswer, SourceCitation
from .query_service import QueryService
from ...adapters.cache.exact_cache import ExactCache
from ...adapters.cache.semantic_cache import SemanticCache
from ..ports.embedding_provider import EmbeddingProvider

log = structlog.get_logger()


class CachedQueryService:
    """
    Decorator around QueryService that adds two cache layers.

    Lookup order per query:
    1. Exact cache  (Redis, <1ms)   — identical query string
    2. Semantic cache (Qdrant, ~15ms) — similar query embedding
    3. Full RAG pipeline             — embed → retrieve → generate
        then populate both caches.
    """

    def __init__(
        self,
        query_service: QueryService,
        exact_cache: ExactCache,
        semantic_cache: SemanticCache,
        embedder: EmbeddingProvider,
    ) -> None:
        self._svc = query_service
        self._exact = exact_cache
        self._semantic = semantic_cache
        self._embedder = embedder

    async def answer(self, query: str, top_k: int = 5) -> GeneratedAnswer:
        # Layer 1: Exact cache
        cached = await self._exact.get(query)
        if cached:
            return self._deserialize(cached, cached=True)

        # Layer 2: Semantic cache (embed once, reuse for both cache + retrieval)
        query_vector = await self._embedder.embed_text(query)
        cached = await self._semantic.get(query_vector)
        if cached:
            return self._deserialize(cached, cached=True)

        # Layer 3: Full RAG pipeline
        log.info("cache.miss", query=query[:60])
        result = await self._svc.answer(query, top_k)

        # Only cache successful responses — don't poison the cache with fallback answers
        if result.sources:
            serialized = self._serialize(result)
            await self._exact.set(query, serialized)
            await self._semantic.set(query_vector, serialized)

        return result

    def _serialize(self, answer: GeneratedAnswer) -> dict:
        return {
            "answer": answer.answer,
            "sources": [
                {
                    "title": s.title,
                    "source_url": s.source_url,
                    "score": float(s.score),
                    "chunk_text": s.chunk_text,
                }
                for s in answer.sources
            ],
        }

    def _deserialize(self, data: dict, cached: bool) -> GeneratedAnswer:
        return GeneratedAnswer(
            answer=data["answer"],
            sources=[
                SourceCitation(
                    title=s["title"],
                    source_url=s["source_url"],
                    score=s["score"],
                    chunk_text=s.get("chunk_text", ""),
                )
                for s in data.get("sources", [])
            ],
            cached=cached,
        )
