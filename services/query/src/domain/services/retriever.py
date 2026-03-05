import structlog

from ..models.query import RetrievalResult, SearchQuery, ScoredChunk
from ..ports.embedding_provider import EmbeddingProvider
from ..ports.reranker import Reranker
from ..ports.sparse_embedding_provider import SparseEmbeddingProvider
from ..ports.vector_store import VectorStore

log = structlog.get_logger()


class RetrieverService:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        sparse_embedder: SparseEmbeddingProvider,
        vector_store: VectorStore,
        reranker: Reranker | None = None,
        candidate_multiplier: int = 4,
    ) -> None:
        self._embedder = embedder
        self._sparse_embedder = sparse_embedder
        self._vector_store = vector_store
        self._reranker = reranker
        # Fetch more candidates than needed so reranker has room to work
        self._candidate_multiplier = candidate_multiplier

    async def retrieve(self, query: SearchQuery) -> RetrievalResult:
        # 1. Embed the query
        dense_vector = await self._embedder.embed_text(query.text)
        log.info("retriever.embedded", query=query.text[:60])

        # 2. Fetch more candidates than top_k (reranker needs headroom)
        candidates_k = query.top_k * self._candidate_multiplier

        if self._sparse_embedder:
            sparse_vector = self._sparse_embedder.embed_query(query.text)
            chunks = await self._vector_store.hybrid_search(
                dense_vector=dense_vector,
                sparse_vector=sparse_vector,
                top_k=candidates_k,
                filters=query.filters,
            )
        else:
            chunks = await self._vector_store.search(
                query_vector=dense_vector,
                top_k=candidates_k,
                filters=query.filters,
            )
        log.info("retriever.fetched", candidates=len(chunks))

        # 3. Rerank if available, then trim to top_k
        if self._reranker and chunks:
            chunks = await self._reranker.rerank(query.text, chunks, query.top_k)
        else:
            chunks = chunks[: query.top_k]

        log.info("retriever.done", returned=len(chunks))

        return RetrievalResult(query=query.text, chunks=chunks, total_found=len(chunks))
