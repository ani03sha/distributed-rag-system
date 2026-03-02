import json

from aiokafka import AIOKafkaProducer

from ...domain.ports.event_publisher import EventPublisher


class RedpandaPublisher:
    def __init__(self, brokers: str):
        self._brokers = brokers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._brokers,
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
            compression_type="gzip",
        )
        await self._producer.start()

    async def publish(self, topic: str, event: dict) -> None:
        assert self._producer is not None, "Call start() before publish"
        await self._producer.send_and_wait(topic, event)

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
