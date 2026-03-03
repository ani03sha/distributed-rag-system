import httpx
import structlog

log = structlog.get_logger()


class OllamaEmbedder:
    "Call Ollama's /api/embeddings endpoint for dense vector generation"

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed_text(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Ollama has no batch endpoint so sequential with logging
        embeddings = []
        for i, text in enumerate(texts):
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
            if (i + 1) % 10 == 0:
                log.info("embedder.progress", done=i + 1, total=len(texts))
        return embeddings

    @property
    def dimensions(self) -> int:
        return 768
    
    @property
    def model_name(self) -> str:
        return self._model

    async def close(self) -> None:
        await self._client.aclose()