import httpx
import structlog

log = structlog.get_logger()


class OllamaEmbedder:
    """Query side embedder. Embeds are single query string."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def embed_text(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": text},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    @property
    def dimensions(self) -> int:
        return 768

    async def close(self) -> None:
        await self._client.aclose()
