"""
TenantAwareHttpClient — ADR-056 Kanal 1 (ausgehende REST-Calls).

HTTP-Client der automatisch den aktuellen Tenant-Context (X-Tenant-Schema Header)
an Service-zu-Service-Calls weitergibt.

Requires: httpx (install separately: pip install httpx)
"""

from __future__ import annotations

from typing import Any

TENANT_HEADER = "X-Tenant-Schema"


def _get_current_schema() -> str:
    """Get current tenant schema from django-tenants connection."""
    try:
        from django.db import connection
        return getattr(connection, "schema_name", "public") or "public"
    except Exception:
        return "public"


class TenantAwareHttpClient:
    """
    HTTP client that automatically propagates the current tenant context
    via X-Tenant-Schema header to all outgoing service-to-service calls.

    Usage::

        client = TenantAwareHttpClient(base_url="http://risk-hub:8000")
        response = client.get("/api/v1/assessments/")
        response = client.post("/api/v1/assessments/", json={"title": "Test"})
    """

    def __init__(self, base_url: str, extra_headers: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._extra_headers = extra_headers or {}

    def _headers(self) -> dict[str, str]:
        headers = {
            TENANT_HEADER: _get_current_schema(),
            "Content-Type": "application/json",
        }
        headers.update(self._extra_headers)
        return headers

    def get(self, path: str, **kwargs: Any) -> Any:
        """GET request with tenant context header."""
        import httpx
        return httpx.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def post(self, path: str, **kwargs: Any) -> Any:
        """POST request with tenant context header."""
        import httpx
        return httpx.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def put(self, path: str, **kwargs: Any) -> Any:
        """PUT request with tenant context header."""
        import httpx
        return httpx.put(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def patch(self, path: str, **kwargs: Any) -> Any:
        """PATCH request with tenant context header."""
        import httpx
        return httpx.patch(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def delete(self, path: str, **kwargs: Any) -> Any:
        """DELETE request with tenant context header."""
        import httpx
        return httpx.delete(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )
