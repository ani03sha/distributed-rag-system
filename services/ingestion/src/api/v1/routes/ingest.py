from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["ingestion"])

# Injected via FastAPI dependency: wired in main
_ingestion_service = None


def set_ingestion_service(svc):
    global _ingestion_service
    _ingestion_service = svc


class IngestCategoryRequest(BaseModel):
    category: str  # For example: "Distributed Computing"
    limit: int = 20  # Maximum articles to fetch


class IngestTitleRequest(BaseModel):
    title: str  # Exact Wikipedia article title, e.g. "Raft (algorithm)"


class IngestResponse(BaseModel):
    job_id: str
    documents_queued: int


@router.post("/ingest/category")
async def ingest_category(request: IngestCategoryRequest) -> IngestResponse:
    result = await _ingestion_service.ingest_category(request.category, request.limit)
    return IngestResponse(**result)


@router.post("/ingest/title")
async def ingest_title(request: IngestTitleRequest) -> IngestResponse:
    result = await _ingestion_service.ingest_title(request.title)
    return IngestResponse(**result)
