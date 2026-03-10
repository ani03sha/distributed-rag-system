from src.domain.services.prompt_builder import PromptBuilder
from src.domain.models.query import ScoredChunk


def make_chunk(i: int) -> ScoredChunk:
    return ScoredChunk(
        id=f"id-{i}",
        document_id=f"doc-{i}",
        content=f"Content about topic {i}",
        score=0.9,
        title=f"Article {i}",
        source_url=f"https://example.com/{i}",
        index_version="v1.0.0-nomic-768",
    )


def test_prompt_contains_query():
    builder = PromptBuilder()
    prompt = builder.build_user_prompt("What is CAP theorem?", [make_chunk(1)])
    assert "What is CAP theorem?" in prompt


def test_prompt_contains_all_chunk_titles():
    builder = PromptBuilder()
    chunks = [make_chunk(i) for i in range(3)]
    prompt = builder.build_user_prompt("test query", chunks)
    for chunk in chunks:
        assert chunk.title in prompt


def test_prompt_contains_all_chunk_contents():
    builder = PromptBuilder()
    chunks = [make_chunk(i) for i in range(3)]
    prompt = builder.build_user_prompt("test query", chunks)
    for chunk in chunks:
        assert chunk.content in prompt


def test_prompt_with_empty_chunks():
    builder = PromptBuilder()
    prompt = builder.build_user_prompt("test query", [])
    assert "test query" in prompt


def test_system_prompt_is_non_empty():
    builder = PromptBuilder()
    assert len(builder.system_prompt) > 0


def test_system_prompt_contains_key_instruction():
    builder = PromptBuilder()
    assert "ONLY" in builder.system_prompt
