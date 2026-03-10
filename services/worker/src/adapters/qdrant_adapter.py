from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from ..domain.models.chunk import DocumentChunk


class QdrantAdapter:
    def __init__(self, host: str, port: int, collection: str) -> None:
        self.__client = AsyncQdrantClient(host=host, port=port)
        self._collection = collection

    async def ensure_collection(self, dense_size: int = 768) -> None:
        """Create the collection with dense + sparse vectors if it doesn't exist."""
        exists = await self.__client.collection_exists(self._collection)
        if not exists:
            await self.__client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    "dense": VectorParams(size=dense_size, distance=Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=SparseIndexParams())
                },
            )

    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        points = [
            PointStruct(
                id=chunk.id,
                vector={
                    "dense": chunk.embedding,
                    "sparse": SparseVector(
                        indices=list(chunk.sparse_embedding.keys()),
                        values=list(chunk.sparse_embedding.values()),
                    ),
                },
                payload={
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "source_url": chunk.metadata.get("source_url", ""),
                    "title": chunk.metadata.get("title", ""),
                    "index_version": chunk.metadata.get("index_version", ""),
                    "ingested_at": chunk.metadata.get("ingested_at", ""),
                },
            )
            for chunk in chunks
        ]
        await self.__client.upsert(collection_name=self._collection, points=points)

    async def close(self) -> None:
        await self.__client.close()
