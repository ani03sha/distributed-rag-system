import json
from uuid import uuid4

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

log = structlog.get_logger()

SIMILARITY_THRESHOLD = 0.95
COLLECTION = "query_cache"
CACHE_TTL_SECONDS = 3600


class SemanticCache:
    """
    Layer 2 cache: embedding similarity lookup over past queries.

    "What is CAP theorem?" and "Explain the CAP theorem" share
    cosine similarity > 0.95 — both return the same cached answer.

    Hit rate: ~35-45% additional hits beyond exact cache.
    Latency: ~10-20ms (embed already done by caller + Qdrant search).
    """

    def __init__(self, qdrant_host: str, qdrant_port: int) -> None:
        self._client = AsyncQdrantClient(
            host=qdrant_host, port=qdrant_port, check_compatibility=False
        )

    async def ensure_collection(self, dense_size: int = 768) -> None:
        if not await self._client.collection_exists(COLLECTION):
            await self._client.create_collection(
                collection_name=COLLECTION,
                vectors_config={
                    "dense": VectorParams(size=dense_size, distance=Distance.COSINE)
                },
            )

    async def get(self, query_vector: list[float]) -> dict | None:
        try:
            results = await self._client.query_points(
                collection_name=COLLECTION,
                query=query_vector,
                using="dense",
                limit=1,
                with_payload=True,
            )
        except UnexpectedResponse as e:
            if e.status_code == 404:
                return None  # collection deleted — treat as cache miss, recreated on next set()
            raise
        if not results.points:
            return None

        top = results.points[0]
        if top.score < SIMILARITY_THRESHOLD:
            log.info(
                "cache.semantic_miss",
                score=round(top.score, 3),
                threshold=SIMILARITY_THRESHOLD,
            )
            return None

        log.info("cache.semantic_hit", score=round(top.score, 3))
        return json.loads(top.payload["answer_json"])

    async def set(self, query_vector: list[float], answer: dict) -> None:
        await self.ensure_collection()
        await self._client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid4()),
                    vector={"dense": query_vector},
                    payload={"answer_json": json.dumps(answer)},
                )
            ],
        )

    async def close(self):
        await self._client.close()
