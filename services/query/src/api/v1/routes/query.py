import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ....api.dependencies import require_auth

router = APIRouter(tags=["query"])

_query_service = None


def set_query_service(svc):
    global _query_service
    _query_service = svc


class QueryRequest(BaseModel):
    text: str
    top_k: int = 5
    stream: bool = True


class ChunkContext(BaseModel):
    title: str
    source_url: str
    score: float
    chunk_text: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[ChunkContext]
    cached: bool = False


@router.post("/query")
async def query(request: QueryRequest, _: dict = Depends(require_auth)):
    if _query_service is None:
        raise HTTPException(status_code=503, detail="Query service not initialized")

    if request.stream:
        return StreamingResponse(
            _stream_sse(request.text, request.top_k),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # disable nginx buffering if behind proxy
            },
        )

    # Non-streaming: buffer and return JSON
    result = await _query_service.answer(request.text, request.top_k)
    return QueryResponse(
        answer=result.answer,
        sources=[
            ChunkContext(
                title=s.title,
                source_url=s.source_url,
                score=s.score,
                chunk_text=s.chunk_text,
            )
            for s in result.sources
        ],
        cached=result.cached,
    )


async def _stream_sse(query: str, top_k: int):
    """Wraps token stream in Server-Sent Events format."""
    # SSE format explained: Each event is data: <payload>\n\n. The double newline terminates the event.
    # The client reads EventSource and accumulates tokens. [DONE] is the sentinel — same convention as
    # OpenAI's API, so any SSE client library will work.
    try:
        # Check cache first - if hit, stream the cached answer immediately
        result = await _query_service.answer(query, top_k)
        if result.cached:
            # Stream cached answer token by token (still feels responsive)
            for word in result.answer.split(" "):
                yield f"data: {json.dumps({'token': word + ' '})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Note: The streaming path (answer_stream) bypasses the cache — you can't cache a stream mid-flight.
        # The answer() method (non-streaming) is what gets cached. In practice, make the streaming route check
        # the cache first and stream from the cached string if available, or from LLM if not.

        # Cache miss - stream directly from LLM
        async for token in _query_service.answer_stream(query, top_k):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
