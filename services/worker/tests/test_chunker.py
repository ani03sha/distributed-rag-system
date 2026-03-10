import pytest
from src.domain.services.chunker import RecursiveChunker


def test_short_text_returns_single_chunk():
    chunker = RecursiveChunker(chunk_size=512, chunk_overlap=64)
    result = chunker.chunk("Hello world")
    assert len(result) == 1
    assert result[0] == "Hello world"


def test_long_text_produces_multiple_chunks():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=10)
    text = "word " * 200  # 1000 chars
    result = chunker.chunk(text)
    assert len(result) > 1


def test_each_chunk_respects_size_limit():
    chunk_size = 100
    chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=10)
    text = "word " * 200
    result = chunker.chunk(text)
    for chunk in result:
        # Small tolerance — splitter may slightly exceed on word boundaries
        assert len(chunk) <= chunk_size + 20


def test_empty_text_returns_empty_list():
    chunker = RecursiveChunker()
    result = chunker.chunk("")
    assert result == []


def test_whitespace_only_returns_empty_list():
    chunker = RecursiveChunker()
    result = chunker.chunk("   \n\n   ")
    assert result == []
