from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveChunker:
    """
    Splits text on paragraph -> line -> sentence -> word boundaries in order.
    Produces chunks that respects natural language structure
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ", ", " ", ""],
        )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        return [c for c in self._splitter.split_text(text) if c.strip()]
