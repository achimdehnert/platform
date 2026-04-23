#!/usr/bin/env python3
"""Explore d.velop Cloud API — raw responses for debugging."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "https://iil.d-velop.cloud"
KEY_FILE = Path.home() / ".secrets" / "dvelop_api_key"


def main() -> None:
    api_key = KEY_FILE.read_text().strip()

    with httpx.Client(
        base_url=BASE_URL, timeout=30.0,
    ) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/hal+json",
        }

        repo_id = "371f456d-c21d-4f9e-a01f-2a55a0d47bd4"
        endpoints = [
            f"/dms/r/{repo_id}/objdef",
            f"/dms/r/{repo_id}/o2/",
            f"/dms/r/{repo_id}",
        ]

        for ep in endpoints:
            print(f"\n{'='*60}")
            print(f"GET {ep}")
            print("=" * 60)
            try:
                resp = client.get(ep, headers=headers)
                print(f"Status: {resp.status_code}")
                print(f"Content-Type: {resp.headers.get('content-type', '?')}")
                try:
                    data = resp.json()
                    print(json.dumps(data, indent=2)[:2000])
                except Exception:
                    print(resp.text[:500])
            except httpx.HTTPError as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    sys.path.insert(
        0, str(Path(__file__).resolve().parent.parent / "src"),
    )
    main()
