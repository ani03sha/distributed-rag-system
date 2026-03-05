from typing import Protocol


class SparseEmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> dict[int, float]: ...
