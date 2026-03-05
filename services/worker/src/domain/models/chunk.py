from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    content: str
    embedding: list[float]
    sparse_embedding: dict[int, float] = field(default_factory=dict)  # BM25 sparse
    metadata: dict = field(default_factory=dict)
