from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from .adapters.embedder.ollama_embedder import OllamaEmbedder
from .adapters.embedder.bm25_embedder import BM25Embedder
from .adapters.reranker.flashrank_reranker import FlashRankReranker
from .adapters.vector_store.qdrant_adapter import QdrantAdapter
from .api.v1.routes import health, query
from .config import settings
from .domain.services.retriever import RetrieverService

log = structlog.get_logger()

embedder = OllamaEmbedder(
    base_url=settings.ollama_base_url,
    model=settings.embedding_model,
)

vector_store = QdrantAdapter(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    collection=settings.qdrant_collection,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("service.starting", service=settings.service_name)
    
    retriever = RetrieverService(
        embedder=embedder,
        sparse_embedder=BM25Embedder(),
        vector_store=vector_store,
        reranker=FlashRankReranker() if settings.reranker_enabled else None,
    )
    
    query.set_retriever(retriever)
    
    yield
    
    await embedder.close()
    await vector_store.close()
    log.info("service.stopping", service=settings.service_name)


app = FastAPI(title="RAG Query Service", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, prefix="/v1")
app.include_router(query.router, prefix="/v1")

if __name__ == "__main__":
    uvicorn.run("main.app", host="0.0.0.0", port=8001, reload=settings.debug)
