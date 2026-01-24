#!/usr/bin/env python
import httpx

# Test mit ID
print("=== Test mit LLM ID 7 ===")
resp = httpx.post(
    "http://127.0.0.1:8100/generate",
    json={"prompt": "Say hello", "model": "7"}
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")

# Test mit Name
print("\n=== Test mit LLM Name 'GPT-4o' ===")
resp = httpx.post(
    "http://127.0.0.1:8100/generate",
    json={"prompt": "Say hello", "model": "GPT-4o"}
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")

# Test ohne model (default)
print("\n=== Test ohne model (default) ===")
resp = httpx.post(
    "http://127.0.0.1:8100/generate",
    json={"prompt": "Say hello"}
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")
