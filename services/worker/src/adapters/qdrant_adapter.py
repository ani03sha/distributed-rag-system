from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..domain.models.chunk import DocumentChunk


class QdrantAdapter:
    def __init__(self, host: str, port: int, collection: str) -> None:
        self.__client = AsyncQdrantClient(host=host, port=port)
        self._collection = collection

    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        points = [
            PointStruct(
                id=chunk.id,
                vector={"dense": chunk.embedding},
                payload={
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "source_url": chunk.metadata["source_url"],
                    "title": chunk.metadata["title"],
                    "index_version": chunk.metadata["index_version"],
                    "ingested_at": chunk.metadata["ingested_at"],
                },
            )
            for chunk in chunks
        ]
        await self.__client.upsert(collection_name=self._collection, points=points)

    async def close(self) -> None:
        await self.__client.close()
