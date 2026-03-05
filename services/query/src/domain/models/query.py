from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchQuery:
    text: str
    top_k: int
    index_version: str = "v1.0.0-nomic-768"
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredChunk:
    id: str
    document_id: str
    content: str
    score: float  # Similarity score from vector store
    title: str
    source_url: str
    index_version: str


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    chunks: list[ScoredChunk]
    total_found: int
