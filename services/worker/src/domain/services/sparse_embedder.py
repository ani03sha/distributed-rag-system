from fastembed import SparseTextEmbedding


class BM25SparseEmbedder:
    """
    Computes BM25 sparse vectors using fastembed.
    Each token maps to a dimension index; value is the BM25 weight.
    Compatible with Qdrant's SparseVector format.
    """

    def __init__(self) -> None:
        # Downloads ~20MB model on first use, cached locally after that
        self._model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def embed_text(self, text: str) -> dict[int, float]:
        result = list(self._model.embed([text]))[0]
        return dict(zip(result.indices.tolist(), result.values.tolist()))

    def embed_batch(self, texts: list[str]) -> list[dict[int, float]]:
        results = list(self._model.embed(texts))
        return [
            dict(zip(result.indices.tolist(), result.values.tolist()))
            for result in results
        ]
