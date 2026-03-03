from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    content: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)
