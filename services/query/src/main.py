from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .adapters.embedder.ollama_embedder import OllamaEmbedder
from .adapters.embedder.bm25_embedder import BM25Embedder
from .adapters.llm.ollama_provider import OllamaProvider
from .adapters.reranker.flashrank_reranker import FlashRankReranker
from .adapters.vector_store.qdrant_adapter import QdrantAdapter
from .adapters.cache.exact_cache import ExactCache
from .adapters.cache.semantic_cache import SemanticCache
from .api.v1.routes import health, query, auth
from .config import settings
from .domain.services.prompt_builder import PromptBuilder
from .domain.services.query_service import QueryService
from .domain.services.retriever import RetrieverService
from .domain.services.cached_query_service import CachedQueryService
from .api.middleware import LoggingMiddleware
from .tracing import setup_tracing

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("service.starting", service=settings.service_name)

    embedder = OllamaEmbedder(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model,
    )

    vector_store = QdrantAdapter(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection=settings.qdrant_collection,
    )

    llm = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.llm_model,
    )

    retriever = RetrieverService(
        embedder=embedder,
        sparse_embedder=BM25Embedder(),
        vector_store=vector_store,
        reranker=FlashRankReranker() if settings.reranker_enabled else None,
    )

    exact_cache = ExactCache(redis_url=settings.redis_url)
    semantic_cache = SemanticCache(
        qdrant_host=settings.qdrant_host,
        qdrant_port=settings.qdrant_port,
    )
    await semantic_cache.ensure_collection(dense_size=embedder.dimensions)

    raw_svc = QueryService(
        retriever=retriever,
        llm=llm,
        prompt_builder=PromptBuilder(),
    )

    cached_svc = CachedQueryService(
        query_service=raw_svc,
        exact_cache=exact_cache,
        semantic_cache=semantic_cache,
        embedder=embedder,
    )

    query.set_query_service(cached_svc)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )

    yield

    await exact_cache.close()
    await semantic_cache.close()
    await embedder.close()
    await vector_store.close()
    await llm.close()
    log.info("service.stopping", service=settings.service_name)


app = FastAPI(title="RAG Query Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(LoggingMiddleware)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
if settings.tracing_enabled:
    setup_tracing(app, settings.service_name, settings.otlp_endpoint)

app.include_router(health.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(query.router, prefix="/v1")

if __name__ == "__main__":
    uvicorn.run("main.app", host="0.0.0.0", port=8001, reload=settings.debug)
