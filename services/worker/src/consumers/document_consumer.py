import json
from datetime import datetime, UTC
from uuid import uuid4

import structlog
from aiokafka import AIOKafkaConsumer

from ..domain.models.chunk import DocumentChunk
from ..domain.services.chunker import RecursiveChunker
from ..domain.services.embedder import OllamaEmbedder
from ..adapters.qdrant_adapter import QdrantAdapter

log = structlog.get_logger()

TOPIC = "rag.ingest.requested"
GROUP_ID = "rag-workers"


class DocumentConsumer:
    def __init__(
        self,
        brokers: str,
        chunker: RecursiveChunker,
        embedder: OllamaEmbedder,
        vector_store: QdrantAdapter,
    ) -> None:
        self._brokers = brokers
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store

    async def run(self) -> None:
        consumer = AIOKafkaConsumer(
            TOPIC,
            bootstrap_servers=self._brokers,
            group_id=GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="earliest",
            enable_auto_commit=False,  # manual commit only, after successful processing
        )
        await consumer.start()
        log.info("consumer.started", topic=TOPIC, group=GROUP_ID)

        try:
            async for message in consumer:
                await self._process(message.value)
                await consumer.commit()  # Commit only after successful upsert
        finally:
            await consumer.stop()

    async def _process(self, event: dict) -> None:
        document_id = event["document_id"]
        title = event["title"]
        log.info("document.processing", document_id=document_id, title=title)

        # 1. Chunk
        text_chunks = self._chunker.chunk(event["content"])
        log.info(
            "document.chunked", document_id=document_id, chunk_count=len(text_chunks)
        )

        # 2. Embed all chunks
        embeddings = await self._embedder.embed_batch(text_chunks)

        # 3. Build chunk objects
        chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                content=text,
                embedding=embedding,
                metadata={
                    "source_url": event["url"],
                    "title": title,
                    "index_version": event["index_version"],
                    "ingested_at": datetime.now(UTC).isoformat(),
                },
            )
            for text, embedding in zip(text_chunks, embeddings)
        ]

        # 4. Upsert into Qdrant
        await self._vector_store.upsert(chunks)
        log.info("document.indexed", document_id=document_id, chunk_count=len(chunks))
