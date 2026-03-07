from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

from ....config import settings

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    api_key: str
    

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_int: int
    
    
@router.post("/auth/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest) -> TokenResponse:
    valid_keys = {k.strip() for k in settings.api_keys.split(",")}
    
    if request.api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    expiry = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    
    payload = {
        "sub": request.api_key[:8] + "...", # Don't store full key in token
        "scopes": ["query"],
        "exp": expiry,
        "iss": "rag-system",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    return TokenResponse(
        access_token=token,
        expires_int=settings.jwt_expiry_minutes * 60
    )