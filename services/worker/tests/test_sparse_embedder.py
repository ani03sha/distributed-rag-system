import pytest
from src.domain.services.sparse_embedder import BM25SparseEmbedder


@pytest.fixture(scope="module")
def embedder():
    # scope=module: model is loaded once for all tests in this file
    return BM25SparseEmbedder()


def test_embed_text_returns_non_empty_dict(embedder):
    result = embedder.embed_text("distributed systems and consensus algorithms")
    assert isinstance(result, dict)
    assert len(result) > 0


def test_embed_text_keys_are_ints(embedder):
    result = embedder.embed_text("test text")
    assert all(isinstance(k, int) for k in result.keys())


def test_embed_text_values_are_floats(embedder):
    result = embedder.embed_text("test text")
    assert all(isinstance(v, float) for v in result.values())


def test_embed_batch_returns_one_result_per_input(embedder):
    texts = ["first text", "second text", "third text"]
    results = embedder.embed_batch(texts)
    assert len(results) == len(texts)


def test_different_texts_produce_different_embeddings(embedder):
    result1 = embedder.embed_text("distributed systems")
    result2 = embedder.embed_text("machine learning neural networks")
    assert result1 != result2
