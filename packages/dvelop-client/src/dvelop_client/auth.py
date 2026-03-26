"""Authentication helpers for d.velop API requests."""

from __future__ import annotations

import httpx


class DvelopAuth(httpx.Auth):
    """httpx Auth handler for d.velop Bearer + Origin CSRF.

    All requests get:
        Authorization: Bearer {api_key}
        Accept: application/hal+json

    Write requests (POST/PUT/DELETE/PATCH) additionally get:
        Origin: {base_url}
        Content-Type: application/hal+json
    """

    WRITE_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._origin = base_url.rstrip("/")

    def auth_flow(
        self, request: httpx.Request,
    ) -> httpx.Auth:  # type: ignore[override]
        request.headers["Authorization"] = f"Bearer {self._api_key}"
        request.headers["Accept"] = "application/hal+json"

        if request.method in self.WRITE_METHODS:
            request.headers["Origin"] = self._origin
            if "Content-Type" not in request.headers:
                request.headers["Content-Type"] = (
                    "application/hal+json"
                )

        yield request
