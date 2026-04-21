#!/usr/bin/env python3
"""Quick test for inception tools."""
import asyncio
import sys
sys.path.insert(0, '/home/dehnert/github/platform/packages/inception-mcp/src')
import os
if 'DATABASE_URL' not in os.environ:
    raise RuntimeError("Set DATABASE_URL env var before running this script")

from inception_mcp.tools import get_categories, list_business_cases, start_business_case

async def test():
    print("=== Testing get_categories ===")
    cats = await get_categories()
    print(f"Found {len(cats.get('categories', []))} categories")
    for c in cats.get('categories', []):
        print(f"  - {c['code']}: {c['name']}")
    
    print("\n=== Testing list_business_cases ===")
    bcs = await list_business_cases()
    print(f"Found {bcs.get('count', 0)} business cases")
    
    print("\n=== Testing start_business_case ===")
    result = await start_business_case(
        initial_description="Wir brauchen eine bessere Suchfunktion für die Dokumentation"
    )
    print(f"Created: {result.get('bc_code')}")
    print(f"Session: {result.get('session_id')}")
    print(f"Question: {result.get('question')}")
    print(f"Remaining: {result.get('questions_remaining')}")

if __name__ == "__main__":
    asyncio.run(test())
