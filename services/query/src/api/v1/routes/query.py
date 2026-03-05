from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ....domain.models.query import SearchQuery

router = APIRouter(tags=["query"])

_retriever = None


def set_retriever(retriever):
    global _retriever
    _retriever = retriever


class QueryRequest(BaseModel):
    text: str
    top_k: int


class ChunkResponse(BaseModel):
    content: str
    title: str
    source_url: str
    score: float


class QueryResponse(BaseModel):
    query: str
    chunks: list[ChunkResponse]
    total_found: int


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    if _retriever is None:
        raise HTTPException(status_code=503, detail="Retriever is not initialized")
    
    result = await _retriever.retrieve(SearchQuery(text=request.text, top_k=request.top_k))
    
    return QueryResponse(
        query=result.query,
        chunks=[
            ChunkResponse(
                content=c.content,
                title=c.title,
                source_url=c.source_url,
                score=c.score,
            )
            for c in result.chunks
        ],
        total_found=result.total_found
    )