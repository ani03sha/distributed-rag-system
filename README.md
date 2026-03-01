# Distributed RAG System

A production-grade distributed Retrieval Augmented Generation (RAG) system built on distributed systems principles.
Designed as a reference implementation for engineering teams.

## Architecture Overview

- **Query Service** — hybrid retrieval (dense + sparse) + LLM generation via Ollama
- **Ingestion Service** — event-driven document pipeline via Redpanda (Kafka-compatible)
- **Worker Service** — async chunk, embed, and index processing
- **Vector Store** — Qdrant with named vectors (dense + sparse)
- **Semantic Cache** — Redis with embedding-based similarity lookup
- **API Gateway** — Traefik (dev) / Kong (prod) with JWT auth + rate limiting

## Stack

| Concern        | Technology                                     |
|----------------|------------------------------------------------|
| LLM            | `qwen2.5:14b` via Ollama (pluggable)           |
| Embeddings     | `nomic-embed-text` 768d via Ollama (pluggable) |
| Vector Store   | Qdrant                                         |
| Cache          | Redis (exact + semantic)                       |
| Message Broker | Redpanda (Kafka-compatible)                    |
| Metadata DB    | PostgreSQL                                     |
| API Gateway    | Traefik (dev), Kong (prod)                     |
| Evaluation     | RAGAS                                          |
| Observability  | structlog + Prometheus + OpenTelemetry         |
| Deployment     | Docker Compose + Kubernetes (k3d)              |

## Documentation

See [`docs/SYSTEM_DESIGN.md`](docs/high_level_design/high_leve_design_doc.md) for the complete design document including:

- High-level and low-level architecture
- All technology decisions with rationale
- Implementation phases with hour estimates
- Evaluation framework design
- Learning milestones
