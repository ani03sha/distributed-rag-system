from typing import Protocol
from ..models.query import ScoredChunk


class Reranker(Protocol):
    async def rerank(
        self, query: str, chunks: list[ScoredChunk], top_n: int
    ) -> list[ScoredChunk]: ...
