import json
from typing import AsyncIterator
import httpx
import structlog

log = structlog.get_logger()


class OllamaProvider:
    """
    Calls Ollama's /api/chat endpoint.

    Streaming: Ollama sends one JSON object per line.
    Each line: {"message": {"content": "<token>"}, "done": false}
    Final line: {"done": true}
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model
        # Long timeout - generation can take 30+ seconds for large context
        self._client = httpx.AsyncClient(timeout=300.0)

    async def generate(
        self, system_prompt: str, user_prompt: str, stream: bool = True
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": stream,
            "options": {
                "temperature": 0.0,  # Deterministic - critical for factual RAG
            },
        }

        async with self._client.stream(
            "POST", f"{self._base_url}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break

    async def close(self) -> None:
        await self._client.aclose()
