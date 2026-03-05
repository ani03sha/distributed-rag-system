from typing import Protocol
from ..models.query import ScoredChunk


class VectorStore(Protocol):
    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict,
    ) -> list[ScoredChunk]: ...

    async def hybrid_search(
        self,
        dense_vector: list[float],
        sparse_vector: dict[int, float],
        top_k: int,
        filters: dict,
    ) -> list[ScoredChunk]: ...
