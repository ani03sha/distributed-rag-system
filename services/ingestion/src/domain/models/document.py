from dataclasses import dataclass


@dataclass(frozen=True)
class RawDocument:
    """A document as fetched from the source - no processing applied."""

    external_id: str  # Source specific id, e.g. "wikipedia:12345"
    source: str
    title: str
    url: str
    content: str
    content_hash: str  # SHA-256 for deduplication
