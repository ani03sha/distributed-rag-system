import pytest
from src.adapters.cache.exact_cache import ExactCache


@pytest.fixture
def cache():
    # Redis client is lazy — no actual connection until get/set is called
    return ExactCache(redis_url="redis://localhost:6389")


def test_key_is_deterministic(cache):
    key1 = cache._key("What is the CAP theorem?")
    key2 = cache._key("What is the CAP theorem?")
    assert key1 == key2


def test_different_queries_produce_different_keys(cache):
    key1 = cache._key("What is the CAP theorem?")
    key2 = cache._key("What is consistent hashing?")
    assert key1 != key2


def test_key_normalizes_case(cache):
    key1 = cache._key("CAP theorem")
    key2 = cache._key("cap theorem")
    assert key1 == key2


def test_key_normalizes_whitespace(cache):
    key1 = cache._key("  CAP theorem  ")
    key2 = cache._key("cap theorem")
    assert key1 == key2


def test_key_has_expected_prefix(cache):
    key = cache._key("test query")
    assert key.startswith("cache:exact:")
