from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from .adapters.publisher.redpanda import RedpandaPublisher
from .adapters.sources.wikipedia import WikipediaAdapter
from .api.v1.routes import ingest, health
from .config import settings
from .domain.services.ingestion_service import IngestionService

log = structlog.get_logger()
publisher = RedpandaPublisher(brokers=settings.kafka_brokers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("service.starting", service=settings.service_name)

    await publisher.start()

    svc = IngestionService(
        source=WikipediaAdapter,
        publisher=publisher,
        index_version=settings.index_version,
    )
    ingest.set_ingestion_service(svc)

    yield

    await publisher.close()
    log.info("service.stopping", service=settings.service_name)


app = FastAPI(title="RAG Ingestion Service", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, prefix="/v1")
app.include_router(ingest.router, prefix="/v1")

if __name__ == "__main__":
    uvicorn.run("main.app", host="0.0.0.0", port=8002, reload=settings.debug)
