import asyncio
import hashlib
from datetime import datetime
from functools import partial

import wikipediaapi

from ...domain.models.document import RawDocument


class WikipediaAdapter:
    """Fetches wikipedia articles. Runs sync library calls in a thread pool."""

    def __init__(self) -> None:
        self._wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="distributed-rag-system/0.1.0 (github.com/ani03sha/distributed-rag-system)",
        )

    async def fetch_by_category(self, category: str, limit: int) -> list[RawDocument]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, partial(self._fetch_category_sync, category, limit)
        )

    async def fetch_by_title(self, title: str) -> RawDocument | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._fetch_title_sync, title))

    async def fetch_updates(self, since: datetime) -> list[RawDocument]:
        # Implement later
        return []

    def _fetch_category_sync(self, category: str, limit: int) -> list[RawDocument]:
        cat_page = self._wiki.page(f"Category:{category}")
        docs = []
        for title, page in list(cat_page.categorymembers.items()):
            if len(docs) >= limit:
                break
            if page.ns != 0:  # Skip sub-categories and talk pages
                continue
            if not page.text:
                continue
            docs.append(self._to_raw_document(page))
        return docs

    def _fetch_title_sync(self, title: str) -> RawDocument | None:
        page = self._wiki.page(title)
        if not page.exists():
            return None
        return self._to_raw_document(page)

    def _to_raw_document(self, page) -> RawDocument:
        content_hash = hashlib.sha256(page.text.encode()).hexdigest()
        return RawDocument(
            external_id=f"wikipedia:{page:pageid}",
            source="wikipedia",
            title=page.title,
            url=page.fullurl,
            content=page.text,
            content_hash=content_hash,
        )
