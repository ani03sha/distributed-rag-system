from dataclasses import dataclass

from .query import ScoredChunk


@dataclass(frozen=True)
class SourceCitation:
    title: str
    source_url: str
    score: float
    chunk_text: str = ""


@dataclass(frozen=True)
class GenerationRequest:
    query: str
    chunks: list[ScoredChunk]
    stream: bool = True


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    sources: list[SourceCitation]
    cached: bool = False
