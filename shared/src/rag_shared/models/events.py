from datetime import datetime
from pydantic import BaseModel


class DocumentIngestRequested(BaseModel):
    """Published to rag.ingest.requested when a document is ready to be processed"""

    event_type: str = "document.ingest.requested"
    version: str = "1.0"
    job_id: str
    document_id: str  # Internal UUID we assign
    external_id: str  # e.g. "wikipedia:12345"
    source: str  # "Wikipedia"
    title: str
    url: str
    content: str
    content_hash: str  # SHA-256 of content
    chunk_strategy: str = "recursive"
    chunk_overlap: int = 64
    index_version: str
    timestamp: datetime


class DocumentIngestCompleted(BaseModel):
    """Published to rag.ingest.completed when worker finished a document."""

    event_type: str = "document.ingest.completed"
    job_id: str
    document_id: str
    chunk_content: str
    timestamp: str


class DocumentIngestFailed(BaseModel):
    """Published to rag.ingest.failed when worker cannot process a document."""

    event_type: str = "document.ingest.failed"
    job_id: str
    document_id: str
    error: str
    attempt: int
    timestamp: datetime
