from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...

    @property
    def dimensions(self) -> int: ...
