from typing import Protocol
from ..models.query import ScoredChunk


class VectorStore(Protocol):
    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict,
    ) -> list[ScoredChunk]: ...
