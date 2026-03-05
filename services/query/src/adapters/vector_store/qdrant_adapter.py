import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FusionQuery, Prefetch, SparseVector

from ...domain.models.query import ScoredChunk

log = structlog.get_logger()


class QdrantAdapter:
    def __init__(self, host: str, port: int, collection: str) -> None:
        self._client = AsyncQdrantClient(host=host, port=port)
        self._collection = collection

    async def search(
        self, query_vector: list[float], top_k: int, filters: dict
    ) -> list[ScoredChunk]:
        results = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
        return [self._to_scored_chunk(point) for point in results.points]

    async def hybrid_search(
        self,
        dense_vector: list[float],
        sparse_vector: dict[int, float],
        top_k: int,
        filters: dict,
    ) -> list[ScoredChunk]:
        results = await self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=SparseVector(
                        indices=list(sparse_vector.keys()),
                        values=list(sparse_vector.values()),
                    ),
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion="rrf"),  # Reciprocal rank fusion
            limit=top_k,
            with_payload=True,
        )
        return [self._to_scored_chunk(r) for r in results.points]

    def _to_scored_chunk(self, result) -> ScoredChunk:
        payload = result.payload
        return ScoredChunk(
            id=str(result.id),
            document_id=payload.get("document_id", ""),
            content=payload.get("content", ""),
            score=result.score,
            title=payload.get("title", ""),
            source_url=payload.get("source_url", ""),
            index_version=payload.get("index_version", ""),
        )

    async def close(self) -> None:
        await self._client.close()
