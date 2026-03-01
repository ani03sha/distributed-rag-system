# Distributed RAG System: Complete Design & Implementation Guide

> **Audience**: This document is written for engineers who want to build a distributed RAG system from scratch,
> who are familiar with distributed systems and have some knowledge about AI Engineering.
>
> This project is designed in such a way that it can be seen as a reference implementation of a RAG system that one
> wishes to deploy in production with minor tweaks.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design Philosophy](#2-design-philosophy)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Technology Stack & Rationale](#4-technology-stack--rationale)
5. [Data Source Selection](#5-data-source-selection)
6. [LLM & Embedding Model Selection](#6-llm--embedding-model-selection)
7. [Data Flows & Sequence Diagrams](#7-data-flows--sequence-diagrams)
8. [Component Low-Level Design](#8-component-low-level-design)
9. [Ingestion Pipeline](#9-ingestion-pipeline)
10. [Retrieval Architecture](#10-retrieval-architecture)
11. [Generation Layer](#11-generation-layer)
12. [Caching Strategy](#12-caching-strategy)
13. [Authentication & Authorization](#13-authentication--authorization)
14. [Infrastructure: Docker & Kubernetes](#14-infrastructure-docker--kubernetes)
15. [API Gateway](#15-api-gateway)
16. [Database & Kafka: Why and How](#16-database--kafka-why-and-how)
17. [Evaluation Framework](#17-evaluation-framework)
18. [Observability](#18-observability)
19. [Implementation Phases](#19-implementation-phases)
20. [Design Patterns Used](#20-design-patterns-used)
21. [Architecture Decision Records](#21-architecture-decision-records)
22. [Learning Milestones](#22-learning-milestones)

---

## 1. Executive Summary

This system is a **production-grade Retrieval Augmented Generation (RAG) platform** built on distributed systems
principles. It ingests documents from open-source data sources (easily configurable), chunks and embeds them into a
vector database, and answers natural language queries by retrieving relevant context and generating grounded responses
via a local LLM (or you can point it to the foundational model of your choice).

### What Makes This "Production-Grade"

- **Not a notebook project.** Every component is a deployable service.
- **No framework lock-in.** Core logic is behind interfaces; swapping LangChain for LlamaIndex requires only a single
  adapter class change.
- **Operationally complete.** Includes ingestion scheduling, caching, auth, observability, evals.
- **Horizontally scalable.** Each service is stateless and scales independently.
- **Timeless architecture.** The patterns (event-driven ingestion, semantic caching, hybrid retrieval) predate and will
  outlast any specific library version.

### What This System Is NOT

- It is not a chatbot with memory (no session state, no history — that is a separate concern).
- It is not an ML training platform.
- It is not a multi-agent framework.

---

## 2. Design Philosophy

Every architectural decision in this system is anchored to these principles:

### 2.1 Hexagonal Architecture (Ports & Adapters)

Since, we are going to build this system in a way that we can update/replace various external factors (vector database,
LLM provider, datasource, metadata database, etc.), it makes sense for us to
use [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture) pattern.

The core business logic: chunking, retrieval, ranking, etc. lives in a pure domain layer with zero infrastructure
dependencies. Databases, HTTP clients, and LLM providers plug in as adapters.

![Hexagonal Architecture](/docs/high_level_design/hexagonal_architecture.png)

**Benefits**: Swap Qdrant for pgvector in a single line. Swap Ollama for OpenAI for benchmarking. No coupling = no fear.

### 2.2 Event-Driven Ingestion

Ingestion is never synchronous with query serving. Documents flow through a pipeline triggered by events (scheduled or
on-demand), not by API calls chained together.

**Why**: Document ingestion can take hours for large corpora. Tying it to a request/response cycle creates timeouts,
partial failures, and unrecoverable states.

### 2.3 Stateless Services

Every service is stateless. State lives in: Qdrant (vectors), PostgreSQL (metadata), Redis (cache), Redpanda (in-flight
events). Services die and restart freely.

**Why**: Horizontal scaling, zero-downtime deployments, simple failure recovery.

### 2.4 Semantic Versioning of Indexes

The vector index is versioned. A new embedding model or chunking strategy creates a new index version, not an in place
mutation. Old version serves traffic while the new one is being built.

**Why**: We never want a re-indexing job to cause query degradation.

### 2.5 Separation of Ingestion and Query Paths

Ingestion and query serving are entirely separate services with separate scaling policies. They share only the vector
store and metadata DB.

---

## 3. High-Level Architecture

![High Level System Architecture](/docs/high_level_design/distributed_rag_system_architecture.png)

### Service Responsibilities

| Service           | Responsibility                            | Scales With      |
|-------------------|-------------------------------------------|------------------|
| API Gateway       | Auth, routing, rate limiting              | Request volume   |
| Query Service     | Orchestrate retrieve + generate           | Query QPS        |
| Ingestion Service | Accept ingestion requests, publish events | Write throughput |
| Worker Service    | Process events: chunk, embed, store       | Document volume  |
| Admin Service     | Index management, job status, metrics     | Ops traffic      |

---

## 4. Technology Stack & Rationale

### 4.1 Core Application

| Component       | Choice         | Rationale                                                                 |
|-----------------|----------------|---------------------------------------------------------------------------|
| Language        | Python 3.12+   | Dominant in AI/ML tooling; async-native; type hints                       |
| Web Framework   | FastAPI        | Async, auto OpenAPI docs, Pydantic validation                             |
| Package Manager | uv             | 10-100x faster than pip; deterministic locks; replaces pip+venv+pip-tools |
| Task Queue      | Celery + Redis | Well-understood, production-proven; Kafka for events, Celery for retries  |
| Data Validation | Pydantic v2    | Runtime type safety; JSON schema generation; used by FastAPI              |

### 4.2 Data Layer

| Component      | Choice         | Rationale                                                                          |
|----------------|----------------|------------------------------------------------------------------------------------|
| Vector Store   | **Qdrant**     | Native hybrid search; filtering on payload; Docker + cloud; gRPC+REST; open source |
| Relational DB  | PostgreSQL 16+ | ACID compliance; JSONB for flexible metadata; pgvector if needed; battle-tested    |
| Cache          | Redis 7        | Hash-based exact cache; embedding-based semantic cache; pub/sub; sorted sets       |
| Message Broker | **Redpanda**   | Kafka-compatible API; single binary; no ZooKeeper; runs natively in Docker         |

**Why Qdrant over alternatives:**

- Chroma: Great for prototyping, not production-ready (no distributed mode, no gRPC)
- Weaviate: Feature-rich but heavy, complex configuration
- Milvus: Production-ready but operationally complex for a single team
- pgvector: Good if PostgreSQL is already present, but lacks advanced filtering and performance at scale. However, if
  possible, always give preference to `pgvector` to avoid complexity.
- **Qdrant**: Clean API, payload filtering (filter by category, date, source), supports named vectors (store dense AND
  sparse in the same collection), Rust performance, official Python client

**Why Redpanda over Kafka:**

- Kafka requires ZooKeeper (or KRaft) — operationally non-trivial locally
- Redpanda is a single binary, Kafka-compatible, starts in seconds, consumes less RAM
- In production, we'd switch the broker URL, nothing else changes

### 4.3 Infrastructure

| Component        | Choice                              | Rationale                                                                     |
|------------------|-------------------------------------|-------------------------------------------------------------------------------|
| Containerization | Docker + Docker Compose             | Local dev parity with production                                              |
| Orchestration    | Kubernetes (k3d locally)            | Industry standard; local via k3d (lightweight k3s in Docker)                  |
| API Gateway      | **Kong** (prod) / **Traefik** (dev) | Kong: plugin ecosystem, JWT, rate limiting; Traefik: auto-discovery in Docker |
| Service Mesh     | None (Phase 1)                      | Overhead not justified at this scale; can add Istio later                     |
| Secrets          | Kubernetes Secrets / Doppler        | Never hardcode secrets                                                        |

### 4.4 Observability

| Component | Choice                 | Rationale                                                                       |
|-----------|------------------------|---------------------------------------------------------------------------------|
| Logging   | structlog + JSON       | Machine-parseable; correlation IDs; no printf debugging                         |
| Metrics   | Prometheus + Grafana   | Industry standard; pull-based; Qdrant/Redis ship native exporters               |
| Tracing   | OpenTelemetry + Jaeger | Vendor-neutral; traces span across services; LangChain has OTEL instrumentation |
| Alerting  | Grafana Alerts         | Co-located with dashboards                                                      |

### 4.5 RAG-Specific Libraries

| Component          | Choice                                 | Rationale                                                                     |
|--------------------|----------------------------------------|-------------------------------------------------------------------------------|
| RAG Orchestration  | LangChain                              | Rich ecosystem; LCEL (LangChain Expression Language) for composable pipelines |
| Evaluation         | **RAGAS**                              | Purpose-built for RAG evaluation; reference-free metrics; widely cited        |
| Embeddings (local) | via Ollama                             | Same runtime as LLM; no separate service needed                               |
| Re-ranking         | **FlashRank** or **Cohere Rerank API** | FlashRank is local, zero-cost; Cohere for quality benchmark                   |
| BM25               | **rank_bm25**                          | Pure Python; plugs into Qdrant's sparse vector workflow                       |

---

## 5. Data Source Selection

### Recommendation: Wikipedia via `wikipedia-api`

**Why Wikipedia:**

1. **Open license** (CC BY-SA 4.0) — no legal risk, no API keys needed
2. **Structured and clean** — articles are well-written, factual, and consistently formatted
3. **Enormous corpus** — 6.7M English articles; you decide the scope
4. **Domain-agnostic** — test with Technology, Science, History, etc.
5. **Refresh-friendly** — Wikipedia has recent changes API; perfect for demonstrating the refresh pipeline
6. **Universal understanding** — anyone can verify your RAG answers without domain expertise
7. **Pluggable pattern** — your `DocumentSource` interface also accepts PDFs, arXiv, GitHub docs

**How to scope it:** Don't ingest all of Wikipedia. Pick a category tree (e.g., "Computer science",
"Distributed computing", "Machine learning") for focused, high-quality eval.

### Alternative Sources (same adapter interface)

| Source         | Use Case                | Notes                  |
|----------------|-------------------------|------------------------|
| arXiv papers   | Technical depth         | PDF parsing needed     |
| GitHub READMEs | Developer tool docs     | GitHub API rate limits |
| HackerNews     | Current discourse       | Noisier content        |
| Company docs   | Enterprise demo         | Requires PDF pipeline  |
| Custom PDFs    | Portfolio customization | Add a PDF adapter      |

**Design principle**: The `DocumentSource` port abstracts all of these. Swapping data source is a config change, not a
code change.

---

## 6. LLM & Embedding Model Selection

### 6.1 LLM for Generation (via Ollama)

I am build this in my MacBook Pro with 36GB RAM, so I have considered the following options:

| Model               | Size (Q4) | RAM Usage | Quality    | Speed     | Recommendation      |
|---------------------|-----------|-----------|------------|-----------|---------------------|
| `llama3.2:3b`       | ~2GB      | ~4GB      | Good       | Very fast | Dev/testing         |
| `llama3.1:8b`       | ~5GB      | ~7GB      | Very good  | Fast      | **Primary default** |
| `mistral-nemo:12b`  | ~8GB      | ~10GB     | Excellent  | Medium    | Better answers      |
| `qwen2.5:14b`       | ~9GB      | ~11GB     | Excellent  | Medium    | **Recommended**     |
| `llama3.1:70b` (Q4) | ~40GB     | ~42GB     | Near GPT-4 | Slow      | Too large for 36GB  |

**Primary Recommendation: `qwen2.5:14b`**

- Qwen 2.5 14B outperforms Llama 3.1 8B on most benchmarks at modest RAM cost
- Excellent instruction following and long-context handling
- Perfect for RAG (good at grounded, factual responses)
- Fits in ~11GB, leaving headroom for services

**Pluggability pattern:**

```python
class LLMProvider(Protocol):
    async def generate(self, prompt: str, context: list[str]) -> AsyncIterator[str]: ...


class OllamaProvider:  # local


class OpenAIProvider:  # cloud benchmark


class AnthropicProvider:  # cloud benchmark
```

Switch via environment variable: `LLM_PROVIDER=ollama MODEL=qwen2.5:14b`

### 6.2 Embedding Model

| Model                    | Dimensions | RAM      | Quality | Notes                        |
|--------------------------|------------|----------|---------|------------------------------|
| `nomic-embed-text`       | 768        | ~1GB     | Good    | **Default; via Ollama**      |
| `mxbai-embed-large`      | 1024       | ~2GB     | Better  | Runs via Ollama              |
| `text-embedding-3-small` | 1536       | API only | Best    | OpenAI; use for benchmarking |

**Recommendation: `nomic-embed-text` for default, `mxbai-embed-large` for production quality.**

**Why embedding model choice matters for evals:** Our eval suite benchmarks retrieval quality across dimension sizes.
We will run eval with all three and compare. This is one of the most educationally rich parts of the project.

### 6.3 Sparse Embeddings (for Hybrid Search)

Use **SPLADE** (via `fastembed`) or **BM25** (via `rank_bm25`) for sparse vectors.
Store both dense and sparse in Qdrant's named vector support.

---

## 7. Data Flows & Sequence Diagrams

### 7.1 Query Flow (Happy Path with Cache Miss)

![Query Flow - Happy Path With Cache Miss](/docs/high_level_design/query_flow_happy_path_cache_miss.png)

### 7.2 Ingestion Flow (Scheduled Refresh)

![Ingestion Flow (Scheduled Refresh)](/docs/high_level_design/ingestion_flow_scheduled_refresh.png)

### 7.3 Semantic Cache Flow

![Semantic Cache Flow](/docs/high_level_design/semantic_cache_flow.png)

---

## 8. Component Low-Level Design

### 8.1 Domain Models

```python
@dataclass(frozen=True)
class DocumentChunk:
    id: str  # UUID
    document_id: str
    content: str
    metadata: ChunkMetadata
    embedding: list[float] | None = None
    sparse_embedding: dict[int, float] | None = None  # for BM25/SPLADE


@dataclass(frozen=True)
class ChunkMetadata:
    source_url: str
    title: str
    section: str
    char_offset: int
    token_count: int
    ingested_at: datetime
    index_version: str  # "v1.0.0-nomic-768"


@dataclass(frozen=True)
class QueryResult:
    answer: str
    sources: list[SourceCitation]
    confidence: float  # 0.0–1.0, derived from top-k similarity scores
    latency_ms: int
    cached: bool


@dataclass(frozen=True)
class SourceCitation:
    title: str
    url: str
    relevance_score: float
    excerpt: str
```

### 8.2 Port Definitions (Abstract Interfaces)

```python
# These never change. Adapters are swapped, ports are stable.

class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...

    @property
    def model_name(self) -> str: ...


class VectorStore(Protocol):
    async def upsert(self, chunks: list[DocumentChunk]) -> None: ...

    async def search(
            self, query_vector: list[float], top_k: int, filters: dict
    ) -> list[ScoredChunk]: ...

    async def hybrid_search(
            self, dense: list[float], sparse: dict[int, float], top_k: int
    ) -> list[ScoredChunk]: ...

    async def delete_by_document(self, document_id: str) -> None: ...


class LLMProvider(Protocol):
    async def generate(
            self, prompt: str, context: list[str], stream: bool = True
    ) -> AsyncIterator[str]: ...


class DocumentSource(Protocol):
    async def fetch(self, query: str, limit: int) -> list[RawDocument]: ...

    async def fetch_updates(self, since: datetime) -> list[RawDocument]: ...


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int) -> None: ...

    async def get_semantic(
            self, query_vector: list[float], threshold: float
    ) -> str | None: ...

    async def set_semantic(
            self, query_vector: list[float], result: str, ttl: int
    ) -> None: ...
```

### 8.3 PostgreSQL Schema

```sql
-- Documents table: source-of-truth for what has been ingested
CREATE TABLE documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      VARCHAR(50) NOT NULL,   -- 'wikipedia', 'arxiv', 'pdf'
    external_id VARCHAR(500) UNIQUE,    -- Wikipedia page ID, arXiv ID
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    content_hash CHAR(64) NOT NULL,     -- SHA-256; detect if content changed
    chunk_count  INT,
    index_version VARCHAR(50),          -- which vector index version
    status      VARCHAR(20) DEFAULT 'pending',  -- pending/indexed/failed
    ingested_at TIMESTAMP WITH TIME ZONE,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ingestion jobs: track scheduled and on-demand runs
CREATE TABLE ingestion_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger     VARCHAR(20) NOT NULL,   -- 'scheduled', 'manual', 'webhook'
    source      VARCHAR(50) NOT NULL,
    status      VARCHAR(20) DEFAULT 'queued',  -- queued/running/done/failed
    docs_total  INT,
    docs_indexed INT DEFAULT 0,
    docs_failed  INT DEFAULT 0,
    error       TEXT,
    started_at  TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API keys: bearer token auth for services
CREATE TABLE api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    key_hash    CHAR(64) NOT NULL,     -- SHA-256 of the actual key
    scopes      TEXT[] NOT NULL,       -- ['query', 'ingest', 'admin']
    rate_limit  INT DEFAULT 100,       -- requests per minute
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Index versions: track what's in Qdrant
CREATE TABLE index_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         VARCHAR(50) UNIQUE NOT NULL,  -- "v1.0.0-nomic-768"
    embedding_model VARCHAR(200) NOT NULL,
    dimensions      INT NOT NULL,
    chunk_strategy  VARCHAR(50) NOT NULL,
    chunk_size      INT NOT NULL,
    chunk_overlap   INT NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE,         -- only one active at a time
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 9. Ingestion Pipeline

### 9.1 Chunking Strategies

The worker service implements multiple chunking strategies behind the same interface:

```
Strategy 1: Fixed-Size (Baseline)
  "The quick brown fox..." → [512 tokens] → [512 tokens] → [512 tokens]
  Overlap: 50 tokens
  Use: Simple, predictable, good baseline for eval

Strategy 2: Recursive Character Splitting (Default)
  Split on ["\n\n", "\n", ". ", " "] in order until chunk < max_size
  Preserves paragraph and sentence boundaries
  Use: General purpose; LangChain's RecursiveCharacterTextSplitter

Strategy 3: Semantic Chunking (Advanced)
  Split when embedding similarity drops below threshold
  Produces variable-size, semantically coherent chunks
  Use: Higher retrieval quality; higher ingestion cost
```

**Default**: Recursive with `chunk_size=512, overlap=64`. Configurable per index version.

### 9.2 Redpanda Event Schema

```json
{
  "event_type": "document.ingest.requested",
  "version": "1.0",
  "job_id": "uuid",
  "document": {
    "external_id": "wikipedia:Distributed_computing",
    "source": "wikipedia",
    "title": "Distributed computing",
    "url": "https://en.wikipedia.org/wiki/Distributed_computing",
    "content": "...",
    "content_hash": "sha256..."
  },
  "config": {
    "chunk_strategy": "recursive",
    "chunk_size": 512,
    "index_version": "v1.0.0-nomic-768"
  },
  "timestamp": "2026-03-01T00:00:00Z"
}
```

Topics:

- `rag.ingest.requested` — new document to process
- `rag.ingest.completed` — document indexed successfully
- `rag.ingest.failed` — document failed; worker will DLQ after 3 retries
- `rag.ingest.dlq` — dead letter queue for manual review

### 9.3 Ingestion Rate Control

Wikipedia allows fetching at ~200 req/s. We deliberately throttle to 10 req/s to be a good
citizen. The Redpanda consumer group handles backpressure naturally — if workers are slow,
messages queue up safely.

### 9.4 Idempotency

Every ingestion is idempotent. Before processing:

1. Check PostgreSQL for `content_hash`
2. If hash matches → skip (already indexed, content unchanged)
3. If hash differs → re-chunk, re-embed, replace in Qdrant, update metadata

This makes scheduled refreshes safe to run without fear of duplication.

---

## 10. Retrieval Architecture

### 10.1 Why Hybrid Search

Dense retrieval (semantic) finds documents that are conceptually related even without keyword
overlap. Sparse retrieval (BM25) finds exact keyword matches. Neither is sufficient alone:

- Dense miss: "What is RPC?" — may miss docs containing "remote procedure call" if the embedding
  space doesn't perfectly align
- Sparse miss: "Explain how systems communicate across machines" — finds nothing if docs use
  different vocabulary

**Hybrid = best of both.** Qdrant's Query API supports this natively with Reciprocal Rank Fusion.

### 10.2 Retrieval Pipeline

```
Query Text
    │
    ▼
Query Preprocessing
    - Lowercase, remove special chars
    - Detect language
    - Extract explicit filters (if any): "papers after 2023", "from Wikipedia"
    │
    ▼
Parallel Embedding                         ┌── Dense embedding (Ollama)
    │                                      └── Sparse (BM25 over query terms)
    ▼
Qdrant Hybrid Search (RRF fusion)
    - Top-k = 20 candidates
    - Filter by: source, date_range, index_version
    │
    ▼
Re-ranking (FlashRank cross-encoder)
    - Input: query + 20 candidates
    - Output: top-5 reranked
    │
    ▼
Context Assembly
    - Dedup by document_id (same doc, different chunks)
    - Order by relevance
    - Truncate to context_window limit
    │
    ▼
Generation
```

### 10.3 Re-ranking

Re-ranking is a cross-encoder: it reads both the query and each candidate document together
(not just their pre-computed embeddings) and produces a more accurate relevance score.

FlashRank is a lightweight, local cross-encoder that adds ~50ms latency for 20 candidates
and typically improves answer quality significantly compared to vector similarity alone.

### 10.4 Qdrant Collection Configuration

```python
# Named vectors: store both dense and sparse in same collection
collection_config = {
    "vectors": {
        "dense": {"size": 768, "distance": "Cosine"},
    },
    "sparse_vectors": {
        "sparse": {"index": {"on_disk": False}}
    },
    "optimizers_config": {
        "indexing_threshold": 10000  # build HNSW after 10k vectors
    },
    "hnsw_config": {
        "m": 16,  # graph connectivity
        "ef_construct": 100  # build-time accuracy
    }
}
```

**HNSW tuning matters:** `m=16, ef_construct=100` balances index build time and query accuracy.
Higher `ef_construct` = better accuracy, slower indexing. Your eval suite will measure this.

---

## 11. Generation Layer

### 11.1 Prompt Architecture

Never concatenate strings for prompts. Use structured templates:

```python
SYSTEM_PROMPT = """You are a factual assistant. Answer questions using ONLY the provided context.
If the context does not contain the answer, say "I don't have enough information."
Never invent facts. Always cite the source title for each claim."""

RAG_PROMPT_TEMPLATE = """
Context documents:
{context}

Question: {question}

Instructions:
- Answer based strictly on the context above
- Cite sources using [Title] notation
- If uncertain, express that uncertainty
"""
```

### 11.2 Context Window Management

```
Model context window: ~8192 tokens (qwen2.5:14b supports 32k)
Reserved for response: 512 tokens
Reserved for system prompt: 256 tokens
Available for context: ~7424 tokens → ~5500 words

Chunk size 512 tokens × 5 chunks = 2560 tokens
→ Comfortable fit with room for multi-hop context
```

### 11.3 Streaming Responses

Use Server-Sent Events (SSE) for streaming, not WebSockets (SSE is simpler, HTTP-native,
and sufficient for unidirectional streaming):

```python
@router.post("/v1/query")
async def query(request: QueryRequest) -> StreamingResponse:
    async def generate():
        async for token in query_service.execute(request):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 11.4 Hallucination Mitigation

1. **Grounded prompt** — instruct model to only use provided context
2. **Temperature = 0.0** — deterministic, factual responses
3. **Source citations in response** — forces model to reference actual documents
4. **Confidence scoring** — compute from retrieval scores, return alongside answer
5. **Faithfulness eval** (RAGAS) — measure post-hoc during eval runs

---

## 12. Caching Strategy

### 12.1 Two Layers of Cache

**Layer 1: Exact Cache** (Redis GET/SET)

- Key: `SHA256(normalized_query_string)`
- TTL: 1 hour for frequent queries
- Hit rate: ~15-20% in practice (exact same queries)
- Latency: <1ms

**Layer 2: Semantic Cache** (Redis + vector similarity)

- Embed the query, store embedding → result mapping in Redis
- On new query: embed, find cosine nearest neighbor in stored embeddings
- If similarity > 0.95 → cache hit (semantically equivalent question)
- Implementation: Use `redis-py` with sorted sets or a dedicated lib like `GPTCache`
- Hit rate: ~35-45% additional hits beyond exact cache
- Latency: ~5-10ms (embed + similarity lookup)

**Why semantic cache is a key distributed systems pattern here:**
It solves the vocabulary mismatch problem for caching. "What is CAP theorem?" and
"Explain the CAP theorem" should return the same cached result.

### 12.2 Cache Invalidation

When documents are re-ingested (content changed), invalidate:

1. Exact cache: pattern-delete `cache:query:*` (or scope by topic)
2. Semantic cache: version the cache key with `index_version`

Never serve cached answers from an old index version for new index queries.

---

## 13. Authentication & Authorization

### 13.1 Bearer Token Architecture

```
Client ──► API Gateway ──► Kong JWT Plugin ──► Verify signature ──► Route to service
                                ↓ if invalid
                           401 Unauthorized
```

Two token types:

- **Short-lived JWT** (15 min): For end-user query access; issued by auth endpoint
- **Long-lived API Key** (stored as hash in PostgreSQL): For service-to-service and
  programmatic access; hashed with SHA-256, never stored in plaintext

### 13.2 Scopes

```
query       → POST /v1/query (read-only, rate-limited)
ingest      → POST /v1/ingest, GET /v1/jobs (write access)
admin       → all endpoints including index management
```

### 13.3 JWT Payload

```json
{
  "sub": "api_key_id",
  "scopes": [
    "query"
  ],
  "iat": 1740000000,
  "exp": 1740003600,
  "iss": "rag-system"
}
```

### 13.4 Kong JWT Plugin (Production)

```yaml
plugins:
  - name: jwt
    config:
      secret_is_base64: false
      claims_to_verify: [ "exp" ]
      key_claim_name: "iss"
  - name: rate-limiting
    config:
      minute: 100
      policy: redis
      redis_host: redis
```

---

## 14. Infrastructure: Docker & Kubernetes

### 14.1 Docker Compose (Development)

Three compose files that layer on each other:

```bash
# Just infrastructure (Qdrant, Redis, Redpanda, PostgreSQL, Ollama)
docker compose -f docker-compose.infra.yml up

# Full stack for development (with hot reload via bind mounts)
docker compose -f docker-compose.infra.yml -f docker-compose.dev.yml up

# Production-like full stack
docker compose up
```

`docker-compose.infra.yml` declares:

- Qdrant on `:6333` (REST) and `:6334` (gRPC)
- Redis on `:6379`
- Redpanda on `:9092` (Kafka) and `:8080` (Redpanda Console)
- PostgreSQL on `:5432`
- Ollama on `:11434` (with GPU passthrough if available)

### 14.2 Kubernetes Architecture (k3d locally)

```bash
# Start local k3d cluster
k3d cluster create rag-dev --agents 2 --port "8080:80@loadbalancer"

# Deploy with Kustomize
kubectl apply -k infrastructure/kubernetes/overlays/local
```

Resource allocation (local development):

| Service           | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-------------------|-------------|-----------|----------------|--------------|
| query-service     | 100m        | 500m      | 128Mi          | 512Mi        |
| ingestion-service | 100m        | 200m      | 128Mi          | 256Mi        |
| worker (×2)       | 200m        | 1000m     | 256Mi          | 1Gi          |
| qdrant            | 200m        | 2000m     | 512Mi          | 4Gi          |
| redis             | 100m        | 500m      | 128Mi          | 512Mi        |
| redpanda          | 200m        | 1000m     | 512Mi          | 2Gi          |
| postgres          | 100m        | 500m      | 256Mi          | 1Gi          |

### 14.3 Key Kubernetes Patterns

**ConfigMap for configuration:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: query-service-config
data:
  QDRANT_HOST: "qdrant"
  QDRANT_PORT: "6333"
  REDIS_URL: "redis://redis:6389"
  LLM_PROVIDER: "ollama"
  OLLAMA_BASE_URL: "http://ollama:11434"
  EMBEDDING_MODEL: "nomic-embed-text"
  LLM_MODEL: "qwen2.5:14b"
```

**HorizontalPodAutoscaler:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: query-service-hpa
spec:
  scaleTargetRef:
    name: query-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 15. API Gateway

### 15.1 Traefik (Development)

Traefik auto-discovers Docker containers via labels. Zero config routing:

```yaml
# In docker-compose.dev.yml
services:
  query-service:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.query.rule=PathPrefix(`/v1/query`)"
      - "traefik.http.middlewares.query-auth.forwardauth.address=http://auth:8004/verify"
```

### 15.2 Kong (Production)

Kong configured declaratively via `kong.yml`:

```yaml
services:
  - name: query-service
    url: http://query-service:8001
    routes:
      - name: query-route
        paths: [ "/v1/query" ]
        methods: [ "POST" ]
    plugins:
      - name: jwt
      - name: rate-limiting
        config: { minute: 100, policy: redis }
      - name: prometheus
      - name: correlation-id
```

### 15.3 Gateway Responsibilities

| Concern           | Implementation                               |
|-------------------|----------------------------------------------|
| Auth              | JWT plugin verifies Bearer token             |
| Rate limiting     | Per API key, stored in Redis                 |
| Request ID        | Correlation-ID plugin injects `X-Request-ID` |
| Logging           | Access logs in JSON to stdout                |
| Retries           | Retry plugin for 503s (worker overloaded)    |
| Circuit breaking  | Circuit-breaker plugin                       |
| HTTPS termination | Kong handles TLS in production               |

---

## 16. Database & Kafka: Why and How

### 16.1 Why PostgreSQL (Not Just Qdrant)

A common mistake is thinking the vector store replaces all databases. It does not.

| Concern                  | Qdrant                  | PostgreSQL                |
|--------------------------|-------------------------|---------------------------|
| Vector similarity search | ✅ Native                | ⚠️ pgvector (slower)      |
| Ingestion job status     | ❌ Not designed for      | ✅ ACID transactions       |
| Document deduplication   | ⚠️ Possible but awkward | ✅ Unique constraints      |
| API key management       | ❌                       | ✅ With hashing            |
| Audit trails             | ❌                       | ✅ Append-only tables      |
| Complex queries          | ❌                       | ✅ SQL joins, aggregations |
| ACID guarantees          | ❌                       | ✅                         |

PostgreSQL handles **operational state** (what is happening, what happened).
Qdrant handles **retrieval state** (what do we know, how to find it).

### 16.2 Why Redpanda/Kafka (Not Just HTTP Calls)

**Problem with synchronous ingestion:**

```
POST /ingest
  → fetch Wikipedia article (~200ms)
  → chunk 50 paragraphs (~100ms)
  → embed 50 chunks (~5000ms via Ollama)  ← TIMEOUT
```

**Solution with async event pipeline:**

```
POST /ingest → 202 Accepted (job_id returned immediately)
  ↓ (async)
Event: {article content} → Kafka topic → worker picks up
  → chunks at worker pace
  → embeds at worker pace (retries on failure)
  → updates job status in PostgreSQL
```

**What Kafka adds beyond a task queue:**

1. **Replay**: Re-process all documents if you change chunking strategy. Just reset consumer offset.
2. **Fan-out**: Multiple consumers on same topic — one for indexing, one for analytics, one for backup.
3. **Backpressure**: If Ollama is slow, events queue up in Kafka without losing anything.
4. **Audit log**: Kafka is an immutable log; you have a complete record of every document ever ingested.
5. **Exactly-once semantics**: Redpanda supports this; prevents double-indexing on worker crash.

**When you would NOT use Kafka**: Small scale (<10K documents, single server). Use Celery + Redis.
This project uses Kafka to demonstrate the pattern correctly at distributed scale.

---

## 17. Evaluation Framework

### 17.1 RAGAS Metrics Explained

RAGAS (Retrieval Augmented Generation Assessment) provides reference-free evaluation:

| Metric                | What It Measures                                  | Formula Concept                                         |
|-----------------------|---------------------------------------------------|---------------------------------------------------------|
| **Faithfulness**      | Is the answer supported by the retrieved context? | Claims in answer / Claims verifiable in context         |
| **Answer Relevancy**  | Does the answer address the question?             | Cosine similarity of question ↔ generated Q from answer |
| **Context Recall**    | Did retrieval find the relevant chunks?           | Requires ground truth; how much GT is in retrieved      |
| **Context Precision** | Are the retrieved chunks actually useful?         | Relevant chunks / Total retrieved chunks                |

### 17.2 Golden Dataset

Build a ground truth dataset of 100 question-answer pairs derived from your Wikipedia corpus:

```json
[
  {
    "question": "What is the CAP theorem?",
    "ground_truth": "The CAP theorem states that a distributed data store can only guarantee two of three properties simultaneously: Consistency, Availability, and Partition tolerance.",
    "source_document": "CAP theorem",
    "source_url": "https://en.wikipedia.org/wiki/CAP_theorem"
  }
]
```

### 17.3 Benchmarking Dimensions

Run evals across these dimensions and produce comparison reports:

```
Dimension 1: Embedding Model
  - nomic-embed-text (768d) vs mxbai-embed-large (1024d) vs text-embedding-3-small (1536d)
  Measure: Context Recall, Context Precision, Faithfulness

Dimension 2: Chunking Strategy
  - Fixed 256 tokens vs Fixed 512 tokens vs Recursive 512 tokens vs Semantic
  Measure: Context Precision, Answer Relevancy

Dimension 3: Top-K Retrieval
  - k=3 vs k=5 vs k=10 vs k=20
  Measure: Context Recall, latency

Dimension 4: Re-ranking
  - Without reranker vs FlashRank vs Cohere
  Measure: Context Precision, latency delta

Dimension 5: LLM
  - llama3.1:8b vs qwen2.5:14b vs gpt-4o-mini (cloud baseline)
  Measure: Faithfulness, Answer Relevancy, latency, cost
```

### 17.4 Latency Benchmarks

```python
# Target SLOs (Service Level Objectives)
P50_LATENCY_MS = 800  # 50th percentile query latency
P95_LATENCY_MS = 2000  # 95th percentile
P99_LATENCY_MS = 5000  # 99th percentile (LLM cold start)

CACHE_HIT_LATENCY_MS = 50  # semantic cache hit
EMBED_LATENCY_MS = 100  # query embedding
RETRIEVAL_LATENCY_MS = 50  # Qdrant search
RERANK_LATENCY_MS = 100  # FlashRank for 20 candidates
GENERATION_LATENCY_MS = 500  # first token (qwen2.5:14b)
```

---

## 18. Observability

### 18.1 Structured Logging

Every log line is a JSON object. No plain strings.

```python
import structlog

log = structlog.get_logger()

# Every request gets a correlation ID propagated across services
log.info(
    "query.executed",
    query_id=query_id,
    user_id=user_id,
    latency_ms=latency,
    cache_hit=cached,
    retrieval_count=len(chunks),
    model=model_name,
)
```

### 18.2 Prometheus Metrics

```python
# Custom metrics per service
query_latency = Histogram(
    "rag_query_duration_seconds",
    "Query end-to-end latency",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    labelnames=["cache_hit", "model"]
)

cache_hit_rate = Counter(
    "rag_cache_hits_total",
    "Cache hit count",
    labelnames=["cache_type"]  # "exact" or "semantic"
)

ingestion_events = Counter(
    "rag_ingestion_events_total",
    "Documents processed by worker",
    labelnames=["status", "source"]  # status: success/failed
)
```

### 18.3 Distributed Tracing (OpenTelemetry)

Every request gets a `trace_id` propagated via HTTP headers across services:

```
API Gateway → Query Service → Qdrant call → Ollama call
                                ↑              ↑
                           span: retrieval   span: generation
```

LangChain has native OpenTelemetry support via `langchain-opentelemetry`. Jaeger UI shows
the full trace across every hop, invaluable for debugging latency outliers.

---

## 19. Implementation Phases

### Phase 1: Foundation & Infra (5–7 hours)

**Goal**: Running local stack with health checks.

Steps:

1. Initialize uv workspace: `uv init --workspace`
2. Create service directories with `pyproject.toml` per service
3. Write `docker-compose.infra.yml` for Qdrant, Redis, Redpanda, PostgreSQL, Ollama
4. Write base FastAPI app for query service with `/health` endpoint
5. Write `Makefile` with targets: `make infra-up`, `make dev`, `make test`
6. Write `infrastructure/scripts/setup.sh` to pull Ollama models
7. Validate all services start and health checks pass

**Learning milestone**: Docker networking, service discovery via hostnames, environment
variable injection patterns.

---

### Phase 2: Ingestion Pipeline (8–10 hours)

**Goal**: Wikipedia articles flowing through Redpanda into Qdrant.

Steps:

1. Implement `WikipediaAdapter(DocumentSource)` using `wikipedia-api` library
2. Write `IngestionService` that fetches articles by category and publishes to Redpanda
3. Implement `DocumentConsumer` (Kafka consumer loop in worker service)
4. Implement `RecursiveChunker(Chunker)` using LangChain text splitters
5. Implement `OllamaEmbedder(EmbeddingProvider)` for `nomic-embed-text`
6. Implement `QdrantAdapter(VectorStore)` with upsert
7. Create PostgreSQL migrations with Alembic
8. Wire up ingestion flow end-to-end
9. Trigger ingestion via `POST /v1/ingest` and verify chunks appear in Qdrant

**Learning milestone**: Event-driven architecture, Kafka consumer groups, idempotent processing,
the purpose of `content_hash` for deduplication.

---

### Phase 3: Retrieval Engine (6–8 hours)

**Goal**: Given a query, return top-k relevant chunks.

Steps:

1. Implement dense vector search via `QdrantAdapter.search()`
2. Implement BM25 sparse vectors and store alongside dense in Qdrant
3. Implement `HybridRetriever` combining dense + sparse with RRF
4. Integrate FlashRank for re-ranking
5. Expose `POST /v1/query` returning raw chunks (no LLM yet)
6. Write integration tests verifying retrieval quality on 10 hand-picked questions

**Learning milestone**: HNSW index mechanics, RRF fusion math, why dense + sparse beats either alone,
cross-encoder vs bi-encoder trade-offs.

---

### Phase 4: Generation Layer (4–5 hours)

**Goal**: End-to-end RAG query with streaming response.

Steps:

1. Implement `OllamaProvider(LLMProvider)` with async streaming
2. Write `PromptBuilder` with system prompt + context injection
3. Wire retrieval → context assembly → generation in `QueryService`
4. Implement SSE streaming response in FastAPI endpoint
5. Add `confidence` scoring based on retrieval scores
6. Test end-to-end with 20 questions from your golden dataset

**Learning milestone**: Prompt engineering for grounded generation, context window management,
why temperature=0 matters for RAG, streaming vs buffered responses.

---

### Phase 5: Caching & Auth (6–8 hours)

**Goal**: Semantic cache working; JWT auth on all endpoints.

Steps:

1. Implement `RedisCacheAdapter` with exact cache
2. Implement semantic cache (embed query, cosine similarity lookup)
3. Write JWT issuance endpoint (`POST /v1/auth/token`)
4. Implement API key management (hash + store in PostgreSQL)
5. Write FastAPI dependency `require_scope("query")` using `python-jose`
6. Configure Traefik (dev) to forward-auth all requests
7. Configure Kong (prod-like) with JWT plugin
8. Measure cache hit rate on 100 repeated queries from golden set

**Learning milestone**: Semantic cache is one of the most underrated distributed system patterns
for LLM applications. Understanding why it works (and where it fails) is a principal-level insight.

---

### Phase 6: Kubernetes Deployment (5–6 hours)

**Goal**: Full stack running in local k3d cluster.

Steps:

1. Write Dockerfiles for each service (multi-stage, distroless base)
2. Write Kubernetes manifests: Deployments, Services, ConfigMaps, Secrets
3. Write Kustomize base + local overlay
4. Configure Ingress for external access
5. Configure HPA for query-service
6. Write `Makefile` targets: `make k8s-up`, `make k8s-down`, `make k8s-logs`
7. Validate all services start in cluster; run 20-query smoke test

**Learning milestone**: Kustomize overlay pattern (not Helm — Helm adds templating complexity
inappropriate for this scope), resource requests/limits tuning, PersistentVolumeClaims for Qdrant.

---

### Phase 7: Evaluation Framework (5–6 hours)

**Goal**: Reproducible eval runs with comparison reports.

Steps:

1. Build golden dataset of 100 Q&A pairs from your Wikipedia corpus
2. Implement RAGAS evaluation runner
3. Implement latency benchmark suite (p50, p95, p99)
4. Run eval across embedding model dimensions (768 vs 1024)
5. Run eval across chunking strategies
6. Run eval with/without re-ranking
7. Generate HTML/Markdown comparison report
8. Write GitHub Actions workflow to run evals on schedule

**Learning milestone**: Why evaluation is non-negotiable before calling a RAG system "production."
The eval framework is what separates a demo from a production system.

---

### Phase 8: Observability (3–4 hours)

**Goal**: Full observability stack with useful dashboards.

Steps:

1. Add structlog to all services with correlation ID propagation
2. Add Prometheus metrics (query latency, cache hit rate, ingestion throughput)
3. Add OpenTelemetry tracing with Jaeger
4. Write Grafana dashboard JSON for key metrics
5. Add `docker-compose.observability.yml` for Prometheus + Grafana + Jaeger

**Learning milestone**: Reading traces to find latency outliers, using metrics to decide when to
scale, why structured logs are non-negotiable in distributed systems.

---

**Total: ~42–54 hours** for a focused single developer.

---

## 20. Design Patterns Used

| Pattern                | Where                         | Why                                               |
|------------------------|-------------------------------|---------------------------------------------------|
| **Ports & Adapters**   | All domain services           | Isolates business logic from infrastructure       |
| **Repository Pattern** | PostgreSQL, Qdrant access     | Abstracts data access, enables testing with fakes |
| **Strategy Pattern**   | Chunking, retrieval           | Swap algorithms without changing callers          |
| **Factory Pattern**    | Adapter instantiation         | Create concrete implementations from config       |
| **Pipeline Pattern**   | Ingestion worker              | Linear data transformation stages                 |
| **Decorator Pattern**  | Caching layer wraps retriever | Add cache behavior without modifying retriever    |
| **Observer Pattern**   | Kafka consumer                | Decouple event producers from consumers           |
| **Template Method**    | Base document source          | Common fetch flow; subclasses implement specifics |
| **Circuit Breaker**    | Ollama calls                  | Fail fast when LLM is overloaded                  |
| **Bulkhead**           | Separate worker pool          | Ingestion failures don't affect query serving     |

---

## 21. Architecture Decision Records

ADRs document "why we chose this over that." Format: Context → Decision → Rationale → Consequences.

Create these files in `docs/adr/`:

- `001-vector-store-selection.md` — Qdrant vs alternatives
- `002-message-broker-selection.md` — Redpanda vs Kafka vs Celery
- `003-chunking-default.md` — Recursive vs fixed vs semantic as default
- `004-embedding-model.md` — nomic-embed-text as default, why pluggable
- `005-llm-provider.md` — Ollama-first, provider-agnostic interface
- `006-auth-strategy.md` — JWT + API keys vs OAuth
- `007-semantic-cache.md` — Why semantic cache is worth the complexity

ADRs are one of the most undervalued artifacts in software engineering. They let future you
(and future readers of this project) understand why decisions were made.

---

## 22. Learning Milestones

These are the deep concepts you'll internalize by completing each phase:

### Distributed Systems Concepts

- **Event-driven architecture**: Why async beats sync for data pipelines
- **Consumer groups**: How Kafka enables parallel processing with ordering guarantees
- **Idempotency**: Why it's non-negotiable for distributed ingestion
- **Backpressure**: How Kafka naturally handles slow consumers
- **Semantic versioning of indexes**: Zero-downtime re-indexing
- **Cache invalidation**: The hardest problem in CS, now with semantic cache
- **Circuit breakers**: Protecting downstream services from cascade failures

### AI Engineering Concepts

- **Chunking trade-offs**: Why chunk size is one of the highest-leverage RAG tuning parameters
- **Dense vs sparse retrieval**: When BM25 beats embeddings and why
- **Cross-encoder re-ranking**: The quality jump from bi-encoder retrieval
- **Semantic cache**: Why it reduces LLM costs by 35-45% in production
- **RAGAS metrics**: How to measure RAG quality without human labeling at scale
- **Context window management**: Why you don't dump everything into the prompt
- **Embedding model dimensionality**: Higher dimensions ≠ better retrieval

### System Design Concepts

- **Hexagonal architecture**: How to build systems that survive framework changes
- **Horizontal scaling**: Why stateless services enable this trivially
- **Observability**: The difference between logging and observability
- **Distributed tracing**: How to find which service is causing latency

---

## Quick Reference: Technology Stack Summary

```
Service Framework:     FastAPI + Python 3.12 + uv
RAG Orchestration:     LangChain
LLM (default):         qwen2.5:14b via Ollama  [pluggable]
Embedding (default):   nomic-embed-text (768d)  [pluggable]
Vector Store:          Qdrant                   [pluggable via port]
Relational DB:         PostgreSQL 16
Cache:                 Redis 7
Message Broker:        Redpanda (Kafka-compatible)
API Gateway (dev):     Traefik
API Gateway (prod):    Kong
Container:             Docker + Docker Compose
Orchestration:         Kubernetes via k3d (local)
Evaluation:            RAGAS
Observability:         structlog + Prometheus + OpenTelemetry + Jaeger
Data Source:           Wikipedia (pluggable via DocumentSource port)
Re-ranking:            FlashRank (local) or Cohere (cloud benchmark)
Auth:                  JWT Bearer tokens + API keys (SHA-256 hashed)
```

---

*This document is a living reference. Update the ADRs when decisions change.
Every design choice here has a rationale — understanding the rationale matters
more than memorizing the choice.*
