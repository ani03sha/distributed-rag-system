import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(tags=["query"])

_query_service = None


def set_query_service(svc):
    global _query_service
    _query_service = svc


class QueryRequest(BaseModel):
    text: str
    top_k: int = 5
    stream: bool = True


class SourceResponse(BaseModel):
    title: str
    url: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    cached: bool = False


@router.post("/query")
async def query(request: QueryRequest):
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
            SourceResponse(title=s.title, url=s.url, score=s.score)
            for s in result.sources
        ],
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
                yield f'data: {json.dumps({"token": word + " "})}\n\n'
            yield "data: [DONE]\n\n"
            return

        # Cache miss - stream directly from LLM
        async for token in _query_service.answer_stream(query, top_k):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
