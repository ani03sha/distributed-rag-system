# Graph Report - .  (2026-06-15)

## Corpus Check
- 125 files · ~185,349 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 506 nodes · 674 edges · 78 communities (70 shown, 8 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 65 edges (avg confidence: 0.7)
- Token cost: 114,302 input · 28,573 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Domain Models & Caching|Domain Models & Caching]]
- [[_COMMUNITY_Vector Store & Ingestion Workers|Vector Store & Ingestion Workers]]
- [[_COMMUNITY_Infrastructure & CI|Infrastructure & CI]]
- [[_COMMUNITY_Document Source & Events|Document Source & Events]]
- [[_COMMUNITY_Authentication & API Layer|Authentication & API Layer]]
- [[_COMMUNITY_Auth Client & Evaluation|Auth Client & Evaluation]]
- [[_COMMUNITY_Query Flow (Cache Miss)|Query Flow (Cache Miss)]]
- [[_COMMUNITY_Embedders & Reranking|Embedders & Reranking]]
- [[_COMMUNITY_System Architecture Diagram|System Architecture Diagram]]
- [[_COMMUNITY_Semantic Cache Flow|Semantic Cache Flow]]
- [[_COMMUNITY_Hexagonal Ports & Adapters|Hexagonal Ports & Adapters]]
- [[_COMMUNITY_Configuration Settings|Configuration Settings]]
- [[_COMMUNITY_Prompt Builder Tests|Prompt Builder Tests]]
- [[_COMMUNITY_Exact Cache (Layer 1)|Exact Cache (Layer 1)]]
- [[_COMMUNITY_Semantic Cache (Layer 2)|Semantic Cache (Layer 2)]]
- [[_COMMUNITY_Query Embedder|Query Embedder]]
- [[_COMMUNITY_Ingestion Flow Diagram|Ingestion Flow Diagram]]
- [[_COMMUNITY_Qdrant Hybrid Search|Qdrant Hybrid Search]]
- [[_COMMUNITY_Logging Middleware|Logging Middleware]]
- [[_COMMUNITY_RAGAS Eval Reports|RAGAS Eval Reports]]
- [[_COMMUNITY_DB Migrations (Alembic)|DB Migrations (Alembic)]]
- [[_COMMUNITY_Domain Port Interfaces|Domain Port Interfaces]]
- [[_COMMUNITY_Kafka Topic Init|Kafka Topic Init]]
- [[_COMMUNITY_FastAPI App Lifespan|FastAPI App Lifespan]]
- [[_COMMUNITY_Design Principles|Design Principles]]
- [[_COMMUNITY_Qdrant Init Script|Qdrant Init Script]]

## God Nodes (most connected - your core abstractions)
1. `QueryService` - 14 edges
2. `AutoRefreshAuth` - 13 edges
3. `WikipediaAdapter` - 11 edges
4. `ScoredChunk` - 11 edges
5. `PromptBuilder` - 11 edges
6. `OllamaEmbedder` - 11 edges
7. `Domain Core` - 11 edges
8. `Query Service` - 11 edges
9. `RetrieverService` - 10 edges
10. `ExactCache` - 9 edges

## Surprising Connections (you probably didn't know these)
- `DocumentSource` --uses--> `DocumentIngestRequested`  [INFERRED]
  services/ingestion/src/domain/services/ingestion_service.py → shared/src/rag_shared/models/events.py
- `EventPublisher` --uses--> `DocumentIngestRequested`  [INFERRED]
  services/ingestion/src/domain/services/ingestion_service.py → shared/src/rag_shared/models/events.py
- `Redis Container` --implements--> `Two-Layer Semantic Cache`  [INFERRED]
  infrastructure/docker/docker-compose.infra.yml → docs/high_level_design/high_level_design_doc.md
- `Prometheus Scrape Config` --references--> `Query Service`  [INFERRED]
  infrastructure/docker/prometheus.yml → docs/high_level_design/high_level_design_doc.md
- `IngestionService` --uses--> `DocumentIngestRequested`  [INFERRED]
  services/ingestion/src/domain/services/ingestion_service.py → shared/src/rag_shared/models/events.py

## Import Cycles
- 1-file cycle: `services/admin/src/main.py -> services/admin/src/main.py`
- 1-file cycle: `services/ingestion/src/main.py -> services/ingestion/src/main.py`
- 1-file cycle: `services/ingestion/src/adapters/sources/wikipedia.py -> services/ingestion/src/adapters/sources/wikipedia.py`
- 1-file cycle: `services/ingestion/src/domain/ports/document_source.py -> services/ingestion/src/domain/ports/document_source.py`
- 1-file cycle: `services/query/src/main.py -> services/query/src/main.py`

## Hyperedges (group relationships)
- **Hybrid Retrieval Pipeline** — high_level_design_doc_hybrid_search, high_level_design_doc_rrf, high_level_design_doc_reranking, high_level_design_doc_qdrant [EXTRACTED 0.90]
- **Event-Driven Ingestion Flow** — high_level_design_doc_ingestion_service, high_level_design_doc_redpanda_kafka, high_level_design_doc_worker_service, high_level_design_doc_chunking_strategies, high_level_design_doc_qdrant [EXTRACTED 0.90]
- **Infrastructure Containers on rag-network** — docker_compose_infra_qdrant, docker_compose_infra_redis, docker_compose_infra_postgres, docker_compose_infra_redpanda, docker_compose_infra_ollama [EXTRACTED 0.85]

## Communities (78 total, 8 thin omitted)

### Community 0 - "Domain Models & Caching"
Cohesion: 0.06
Nodes (35): ExactCache, LLMProvider, GeneratedAnswer, GenerationRequest, SourceCitation, RetrievalResult, ScoredChunk, SearchQuery (+27 more)

### Community 1 - "Vector Store & Ingestion Workers"
Cohesion: 0.06
Nodes (16): QdrantAdapter, Create the collection with dense + sparse vectors if it doesn't exist., DocumentConsumer, DocumentChunk, DocumentChunk, OllamaEmbedder, QdrantAdapter, RecursiveChunker (+8 more)

### Community 2 - "Infrastructure & CI"
Cohesion: 0.05
Nodes (45): CI Lint & Format Job, CI Unit Tests Job, Jaeger Container, Ollama Container, PostgreSQL Container, Prometheus Container, Qdrant Container, rag-network Shared Network (+37 more)

### Community 3 - "Document Source & Events"
Cohesion: 0.07
Nodes (18): DocumentSource, EventPublisher, A document as fetched from the source - no processing applied., RawDocument, DocumentIngestRequested, Published to rag.ingest.requested when a document is ready to be processed, DocumentSource, EventPublisher (+10 more)

### Community 4 - "Authentication & API Layer"
Cohesion: 0.08
Nodes (32): FastAPI dependency. Add to any route that needs auth:         @router.post("/que, require_auth(), BaseModel, HTTPAuthorizationCredentials, DocumentIngestCompleted, DocumentIngestFailed, Published to rag.ingest.completed when worker finished a document., Published to rag.ingest.failed when worker cannot process a document. (+24 more)

### Community 5 - "Auth Client & Evaluation"
Cohesion: 0.09
Nodes (20): BaseChatModel, ChatResult, Client, generate(), Generates candidate golden Q&A pairs from ingested documents. Run once, then man, Request, AutoRefreshAuth, Auto-refreshing HTTP auth for eval runners.  Usage:     auth = AutoRefreshAuth(a (+12 more)

### Community 6 - "Query Flow (Cache Miss)"
Cohesion: 0.12
Nodes (23): API Gateway, Build Prompt, Cache MISS, Cache Results, Client, Query Flow Happy Path Cache Miss Diagram, Embed Query, Generate (+15 more)

### Community 7 - "Embedders & Reranking"
Cohesion: 0.12
Nodes (8): BM25Embedder, OllamaProvider, Calls Ollama's /api/chat endpoint.      Streaming: Ollama sends one JSON object, FlashRankReranker, Cross-encoder re-ranker using FlashRank.     Unlike bi-encoder (embedding) searc, ScoredChunk, FastAPI, lifespan()

### Community 8 - "System Architecture Diagram"
Cohesion: 0.19
Nodes (13): Admin Service, Async Workers, Cache (Semantic Cache / Result Cache), Client, Distributed RAG System Architecture Diagram, Ingestion Service, Ollama, Postgres (+5 more)

### Community 9 - "Semantic Cache Flow"
Cohesion: 0.21
Nodes (13): Cached Result, Semantic Cache Flow Diagram, Embed Query, Find Similar Past Queries, Generate (LLM), Hint: Similarity >= 0.95, Miss: Similarity < 0.95, Qdrant (+5 more)

### Community 10 - "Hexagonal Ports & Adapters"
Cohesion: 0.26
Nodes (12): Chroma Adapter, Hexagonal Architecture Diagram, Domain Core, Ollama Adapter, OpenAI Adapter, PgVector Adapter, Port: Document Source, Port: Embedding Provider (+4 more)

### Community 11 - "Configuration Settings"
Cohesion: 0.22
Nodes (5): BaseSettings, Settings, Settings, Settings, Settings

### Community 12 - "Prompt Builder Tests"
Cohesion: 0.31
Nodes (5): ScoredChunk, make_chunk(), test_prompt_contains_all_chunk_contents(), test_prompt_contains_all_chunk_titles(), test_prompt_contains_query()

### Community 16 - "Ingestion Flow Diagram"
Cohesion: 0.62
Nodes (7): Ingestion Flow (Scheduled Refresh), Ingestion Service, PostgreSQL, Qdrant, Redpanda, Scheduler, Worker

### Community 20 - "Logging Middleware"
Cohesion: 0.40
Nodes (3): LoggingMiddleware, BaseHTTPMiddleware, Request

### Community 21 - "RAGAS Eval Reports"
Cohesion: 0.50
Nodes (4): DataFrame, compare(), load_report(), Compare multiple RAGAS evaluation CSVs side-by-side.

### Community 22 - "DB Migrations (Alembic)"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 23 - "Domain Port Interfaces"
Cohesion: 0.40
Nodes (4): Reranker, EmbeddingProvider, SparseEmbeddingProvider, VectorStore

## Knowledge Gaps
- **51 isolated node(s):** `Request`, `DataFrame`, `init_qdrant.sh script`, `ScoredChunk`, `HTTPAuthorizationCredentials` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DocumentSource` connect `Document Source & Events` to `Domain Models & Caching`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `PromptBuilder` connect `Domain Models & Caching` to `Prompt Builder Tests`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `RetrieverService` connect `Domain Models & Caching` to `Domain Port Interfaces`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `QueryService` (e.g. with `ExactCache` and `QueryService`) actually correct?**
  _`QueryService` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `AutoRefreshAuth` (e.g. with `ChatResult` and `Client`) actually correct?**
  _`AutoRefreshAuth` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ScoredChunk` (e.g. with `GeneratedAnswer` and `GenerationRequest`) actually correct?**
  _`ScoredChunk` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Generates candidate golden Q&A pairs from ingested documents. Run once, then man`, `Request`, `Auto-refreshing HTTP auth for eval runners.  Usage:     auth = AutoRefreshAuth(a` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._