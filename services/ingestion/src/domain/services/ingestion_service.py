from datetime import datetime, UTC
from uuid import uuid4

from rag_shared.models.events import DocumentIngestRequested
from ..ports.document_source import DocumentSource
from ..ports.event_publisher import EventPublisher

TOPIC_INGESTED_REQUESTED = "rag.ingest.requested"


class IngestionService:
    def __init__(
        self, source: DocumentSource, publisher: EventPublisher, index_version: str
    ):
        self._source = source
        self._publisher = publisher
        self._index_version = index_version

    async def ingest_category(self, category: str, limit: int = 20) -> dict:
        job_id = str(uuid4())
        docs = await self._source.fetch_by_category(category, limit)

        published = 0
        for doc in docs:
            event = DocumentIngestRequested(
                job_id=job_id,
                document_id=str(uuid4()),
                external_id=doc.external_id,
                source=doc.source,
                title=doc.title,
                url=doc.url,
                content=doc.content,
                content_hash=doc.content_hash,
                index_version=self._index_version,
                timestamp=datetime.now(UTC),
            )
            await self._publisher.publish(
                TOPIC_INGESTED_REQUESTED,
                event.model_dump(mode="json"),
            )
            published += 1

        return {"job_id": job_id, "documents_queued": published}

    async def ingest_title(self, title: str) -> dict:
        job_id = str(uuid4())
        doc = await self._source.fetch_by_title(title)

        if doc is None:
            return {"job_id": job_id, "documents_queued": 0}

        event = DocumentIngestRequested(
            job_id=job_id,
            document_id=str(uuid4()),
            external_id=doc.external_id,
            source=doc.source,
            title=doc.title,
            url=doc.url,
            content=doc.content,
            content_hash=doc.content_hash,
            index_version=self._index_version,
            timestamp=datetime.now(UTC),
        )
        await self._publisher.publish(
            TOPIC_INGESTED_REQUESTED,
            event.model_dump(mode="json"),
        )
        return {"job_id": job_id, "documents_queued": 1}
