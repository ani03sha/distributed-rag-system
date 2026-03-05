import structlog
from flashrank import Ranker, RerankRequest

from ...domain.models.query import ScoredChunk

log = structlog.get_logger()

# Downloads ~5MB cross-encoder model on first use
_DEFAULT_MODEL = "ms-marco-MiniLM-L-12-v2"


class FlashRankReranker:
    """
    Cross-encoder re-ranker using FlashRank.
    Unlike bi-encoder (embedding) search, a cross-encoder reads the query
    and each candidate document together, producing a more accurate score.
    Latency: ~50–100ms for 20 candidates on CPU.
    """

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._ranker = Ranker(model_name=model)

    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_n: int
    ) -> list[ScoredChunk]:
        request = RerankRequest(
            query=query,
            passages=[{"id": chunk.id, "text": chunk.content} for chunk in chunks],
        )
        results = self._ranker.rerank(request)

        # Map reranked results back to ScoredChunk with updated scores
        id_to_chunk = {chunk.id: chunk for chunk in chunks}
        reranked = [
            ScoredChunk(
                id=r["id"],
                document_id=id_to_chunk[r["id"]].document_id,
                content=id_to_chunk[r["id"]].content,
                score=r["score"],
                title=id_to_chunk[r["id"]].title,
                source_url=id_to_chunk[r["id"]].source_url,
                index_version=id_to_chunk[r["id"]].index_version,
            )
            for r in results
        ]
        log.info("reranker.done", input=len(chunks), output=len(reranked))
        return reranked
