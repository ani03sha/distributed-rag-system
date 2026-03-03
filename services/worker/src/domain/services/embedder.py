import httpx
import structlog

log = structlog.get_logger()


class OllamaEmbedder:
    """Calls Ollama's /api/embed endpoint for dense vector generation.

    Uses the current Ollama API (v0.3+):
      - Endpoint: POST /api/embed  (replaces the deprecated /api/embeddings)
      - Field:    'input'          (replaces the deprecated 'prompt')
      - Response: 'embeddings'     (list of vectors, one per input)
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed_text(self, text: str) -> list[float]:
        response = await self._client.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": text},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # /api/embed supports native batching — pass the full list in one request
        log.info("embedder.batch_start", total=len(texts), model=self._model)
        response = await self._client.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": texts},
        )
        response.raise_for_status()
        embeddings = response.json()["embeddings"]
        log.info("embedder.batch_done", total=len(embeddings))
        return embeddings

    @property
    def dimensions(self) -> int:
        return 768
    
    @property
    def model_name(self) -> str:
        return self._model

    async def close(self) -> None:
        await self._client.aclose()