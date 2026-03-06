import asyncio

import structlog

from .adapters.qdrant_adapter import QdrantAdapter
from .config import settings
from .consumers.document_consumer import DocumentConsumer
from .domain.services.chunker import RecursiveChunker
from .domain.services.embedder import OllamaEmbedder

log = structlog.get_logger()


async def main() -> None:
    log.info("worker.starting")

    chunker = RecursiveChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    embedder = OllamaEmbedder(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model,
    )

    vector_store = QdrantAdapter(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
    )
    await vector_store.ensure_collection(dense_size=settings.dense_vector_size)

    consumer = DocumentConsumer(
        brokers=settings.kafka_brokers,
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
    )

    try:
        await consumer.run()
    finally:
        await embedder.close()
        await vector_store.close()


if __name__ == "__main__":
    asyncio.run(main())
