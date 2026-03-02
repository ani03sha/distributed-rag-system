from typing import Protocol
from datetime import datetime
from ..models.document import RawDocument


class DocumentSource(Protocol):
    async def fetch_by_category(
        self, category: str, limit: int
    ) -> list[RawDocument]: ...
    async def fetch_by_title(self, title: str) -> RawDocument | None: ...
    async def fetch_updates(self, since: datetime) -> list[RawDocument]: ...
