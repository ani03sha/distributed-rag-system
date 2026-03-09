"""
Auto-refreshing HTTP auth for eval runners.

Usage:
    auth = AutoRefreshAuth(api_key="dev-key-1", base_url="http://localhost:8001")
    client = httpx.Client(auth=auth, timeout=120.0)
    # Token refresh is completely transparent — just use client normally.
"""

import httpx


class AutoRefreshAuth(httpx.Auth):
    """
    httpx Auth implementation that:
    1. Fetches access + refresh tokens on construction using the API key.
    2. Injects the current access token into every request.
    3. On 401, calls /auth/refresh, updates tokens, and retries once.

    Why httpx.Auth and not a wrapper function?
    httpx.Auth is a generator-based protocol — it controls the request/response
    cycle cleanly without needing to duplicate retry logic in every caller.
    """

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._fetch_initial_tokens()

    def _fetch_initial_tokens(self) -> None:
        response = httpx.post(
            f"{self._base_url}/v1/auth/token",
            json={"api_key": self._api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        self._store(response.json())
        print(f"[auth] Token acquired (expires in {response.json()['expires_in']}s)")

    def _do_refresh(self) -> None:
        response = httpx.post(
            f"{self._base_url}/v1/auth/refresh",
            json={"refresh_token": self._refresh_token},
            timeout=10.0,
        )
        response.raise_for_status()
        self._store(response.json())
        print("[auth] Access token refreshed")

    def _store(self, data: dict) -> None:
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._access_token}"
        response = yield request

        if response.status_code == 401:
            self._do_refresh()
            request.headers["Authorization"] = f"Bearer {self._access_token}"
            yield request
