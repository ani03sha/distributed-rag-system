from ..models.query import ScoredChunk

SYSTEM_PROMPT = """\
You are a precise, factual assistant. Answer questions using ONLY the context documents provided below.

Rules:
- If the context does not contain enough information to answer, say: "I don't have enough information to answer this."
- Never invent facts or extrapolate beyond what the context states.
- Cite the source title for each key claim using [Title] notation.
- Be concise. Prefer a direct answer over a long one.\
"""


class PromptBuilder:
    def build_user_prompt(self, query: str, chunks: list[ScoredChunk]) -> str:
        context_blocks = []
        for i, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                f"[{i}] Title: {chunk.title}\n"
                f"Source: {chunk.source_url}\n"
                f"Content: {chunk.content}"
            )

        context_text = "\n\n---\n\n".join(context_blocks)

        return (
            f"Context documents:\n\n"
            f"{context_text}\n\n"
            f"---\n\n"
            f"Question: {query}"
        )

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT
