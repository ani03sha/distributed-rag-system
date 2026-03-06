from dataclasses import dataclass

from .query import ScoredChunk


@dataclass(frozen=True)
class SourceCitation:
    title: str
    url: str
    score: float


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
