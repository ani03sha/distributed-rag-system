from fastembed import SparseTextEmbedding


class BM25Embedder:

    def __init__(self) -> None:
        self._model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def embed_query(self, text: str) -> dict[int, float]:
        result = list(self._model.embed([text]))[0]
        return dict(zip(result.indices.tolist(), result.values.tolist()))
