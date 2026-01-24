import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass(frozen=True)
class McpHubReportOverview:
    kpis: Dict[str, int]
    repositories: list
    generated_at: Optional[str] = None
    version: Optional[str] = None


_CACHE: Dict[str, tuple[float, float, Any]] = {}
_INFLIGHT: Dict[str, bool] = {}
_LOCK = threading.Lock()


def _cache_get(key: str) -> Any:
    item = _CACHE.get(key)
    if not item:
        return None
    expires_at, _stale_until, value = item
    if time.time() > expires_at:
        return None
    return value


def _cache_get_stale(key: str) -> Any:
    item = _CACHE.get(key)
    if not item:
        return None
    _expires_at, stale_until, value = item
    if time.time() > stale_until:
        return None
    return value


def _cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    now = time.time()
    expires_at = now + ttl_seconds
    stale_until = now + max(ttl_seconds, 0) * 3
    _CACHE[key] = (expires_at, stale_until, value)


def _fetch_overview_http(base_url: str, timeout_seconds: float) -> McpHubReportOverview:
    url = base_url.rstrip("/") + "/api/v1/dlm/report/overview"

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return McpHubReportOverview(
        kpis=data.get("kpis") or {},
        repositories=data.get("repositories") or [],
        generated_at=data.get("generated_at"),
        version=data.get("version"),
    )


def _refresh_async(
    cache_key: str,
    base_url: str,
    timeout_seconds: float,
    cache_ttl_seconds: int,
) -> None:
    try:
        result = _fetch_overview_http(base_url=base_url, timeout_seconds=timeout_seconds)
        with _LOCK:
            _cache_set(cache_key, result, cache_ttl_seconds)
    finally:
        with _LOCK:
            _INFLIGHT.pop(cache_key, None)


def fetch_dlm_report_overview(
    base_url: str,
    timeout_seconds: float = 2.0,
    cache_ttl_seconds: int = 10,
) -> McpHubReportOverview:
    cache_key = f"dlm_overview::{base_url}"
    with _LOCK:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        stale = _cache_get_stale(cache_key)
        if stale is not None:
            if not _INFLIGHT.get(cache_key):
                _INFLIGHT[cache_key] = True
                t = threading.Thread(
                    target=_refresh_async,
                    args=(cache_key, base_url, timeout_seconds, cache_ttl_seconds),
                    daemon=True,
                )
                t.start()
            return stale

        if _INFLIGHT.get(cache_key):
            return McpHubReportOverview(kpis={}, repositories=[])
        _INFLIGHT[cache_key] = True

    try:
        result = _fetch_overview_http(base_url=base_url, timeout_seconds=timeout_seconds)
        with _LOCK:
            _cache_set(cache_key, result, cache_ttl_seconds)
        return result
    finally:
        with _LOCK:
            _INFLIGHT.pop(cache_key, None)
