from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

from ....config import settings

router = APIRouter(tags=["auth"])


class TokenRequest(BaseModel):
    api_key: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int        # access token TTL in seconds
    refresh_expires_in: int  # refresh token TTL in seconds


def _make_access_token(sub: str) -> str:
    expiry = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    return jwt.encode(
        {"sub": sub, "type": "access", "scopes": ["query"], "exp": expiry, "iss": "rag-system"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _make_refresh_token(sub: str) -> str:
    expiry = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expiry_days)
    return jwt.encode(
        {"sub": sub, "type": "refresh", "exp": expiry, "iss": "rag-system"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/auth/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest) -> TokenResponse:
    valid_keys = {k.strip() for k in settings.api_keys.split(",")}
    if request.api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    sub = request.api_key[:8] + "..."
    return TokenResponse(
        access_token=_make_access_token(sub),
        refresh_token=_make_refresh_token(sub),
        expires_in=settings.jwt_expiry_minutes * 60,
        refresh_expires_in=settings.jwt_refresh_expiry_days * 86400,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    sub = payload["sub"]
    return TokenResponse(
        access_token=_make_access_token(sub),
        refresh_token=_make_refresh_token(sub),  # rotate refresh token too
        expires_in=settings.jwt_expiry_minutes * 60,
        refresh_expires_in=settings.jwt_refresh_expiry_days * 86400,
    )