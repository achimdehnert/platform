"""JSON-HAL response parser for d.velop API responses."""

from __future__ import annotations

from typing import Any


def extract_links(data: dict[str, Any]) -> dict[str, str]:
    """Extract _links from a HAL response into a flat {rel: href} dict."""
    links = data.get("_links", {})
    result: dict[str, str] = {}
    for rel, link_data in links.items():
        if isinstance(link_data, dict):
            result[rel] = link_data.get("href", "")
        elif isinstance(link_data, list) and link_data:
            result[rel] = link_data[0].get("href", "")
    return result


def extract_embedded(
    data: dict[str, Any], key: str,
) -> list[dict[str, Any]]:
    """Extract _embedded items by key."""
    embedded = data.get("_embedded", {})
    items = embedded.get(key, [])
    if isinstance(items, dict):
        return [items]
    return items


def extract_location(headers: dict[str, str]) -> str:
    """Extract Location header (case-insensitive)."""
    for k, v in headers.items():
        if k.lower() == "location":
            return v
    return ""
