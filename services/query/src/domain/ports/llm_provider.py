from typing import AsyncIterator, Protocol

from ...domain.models.query import ScoredChunk


class LLMProvider(Protocol):
    async def generate(
        self, system_prompt: str, user_prompt: str, stream: bool = True
    ) -> AsyncIterator[ScoredChunk]: ...
