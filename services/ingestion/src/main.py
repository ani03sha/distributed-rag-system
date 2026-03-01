from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from .api.v1.routes import health
from .config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("service.starting", service=settings.service_name)
    yield
    log.info("service.stopping", service=settings.service_name)


app = FastAPI(title="RAG Ingestion Service", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, prefix="/v1")

if __name__ == "__main__":
    uvicorn.run("main.app", host="0.0.0.0", port=8002, reload=settings.debug)
