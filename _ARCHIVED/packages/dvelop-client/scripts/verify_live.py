#!/usr/bin/env python3
"""Verify iil-dvelop-client against live d.velop Cloud API.

Usage:
    python scripts/verify_live.py

Reads API key from ~/.secrets/dvelop_api_key
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on path for local dev
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dvelop_client import DvelopClient, DvelopError  # noqa: E402

BASE_URL = "https://iil.d-velop.cloud"
KEY_FILE = Path.home() / ".secrets" / "dvelop_api_key"


def load_api_key() -> str:
    if not KEY_FILE.exists():
        print(f"ERROR: Key file not found: {KEY_FILE}")
        sys.exit(1)
    key = KEY_FILE.read_text().strip()
    if not key:
        print(f"ERROR: Key file is empty: {KEY_FILE}")
        sys.exit(1)
    print(f"[OK] API key loaded ({len(key)} chars)")
    return key


def main() -> None:
    print("=== d.velop API Verify Script ===")
    print(f"Base URL: {BASE_URL}")
    print()

    api_key = load_api_key()

    with DvelopClient(base_url=BASE_URL, api_key=api_key) as client:
        # 1. List repositories
        print("1. Listing repositories...")
        try:
            repos = client.list_repositories()
            print(f"   [OK] {len(repos)} repositories found")
            for r in repos:
                print(f"   - {r.id}: {r.name}")
        except DvelopError as e:
            print(f"   [FAIL] {e}")
            sys.exit(1)

        if not repos:
            print("   [WARN] No repositories — cannot test further")
            print("\n=== PARTIAL SUCCESS ===")
            return

        repo_id = repos[0].id
        print(f"\n   Using repo: {repo_id} ({repos[0].name})")

        # 2. List categories
        print("\n2. Listing categories...")
        try:
            cats = client.list_categories(repo_id)
            print(f"   [OK] {len(cats)} categories found")
            for c in cats[:10]:
                print(f"   - {c.key}: {c.display_name}")
            if len(cats) > 10:
                print(f"   ... and {len(cats) - 10} more")
        except DvelopError as e:
            print(f"   [FAIL] {e}")

        # 3. Search (empty query = recent docs)
        print("\n3. Searching documents...")
        try:
            results = client.search(repo_id, "*", max_results=5)
            n = len(results.items)
            print(f"   [OK] {results.total} total, {n} shown")
            for item in results.items:
                print(f"   - {item.id}: {item.title}")
        except DvelopError as e:
            print(f"   [INFO] Search returned: {e}")

    print("\n=== VERIFY COMPLETE ===")


if __name__ == "__main__":
    main()
