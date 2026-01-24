#!/usr/bin/env python
"""Test des zentralen LLM-Agents (Option C)."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from apps.bfagent.services.llm_agent import LLMAgent, ModelPreference, llm_generate

print("=" * 60)
print("TEST: Zentraler LLM-Agent (Option C)")
print("=" * 60)

agent = LLMAgent()

# 1. Health Check
print("\n1. Health Check")
healthy = agent.health_check()
print(f"   Gateway erreichbar: {healthy}")

if not healthy:
    print("   ❌ Gateway nicht erreichbar! Bitte starten.")
    exit(1)

# 2. Models auflisten
print("\n2. Verfügbare Models")
models = agent.list_models()
print(f"   {len(models)} Models gefunden")
for m in models[:5]:
    print(f"   - [{m['id']}] {m['name']} ({m['provider']})")

# 3. Einfacher Generate-Aufruf
print("\n3. Einfacher Generate (Auto-Routing)")
response = agent.generate("Sage Hallo auf Deutsch in einem Satz.")
print(f"   Success: {response.success}")
print(f"   Model: {response.model_used}")
print(f"   Content: {response.content}")
print(f"   Latency: {response.latency_ms:.0f}ms")
print(f"   Cached: {response.cached}")

# 4. Mit Quality-Präferenz "fast"
print("\n4. Generate mit Präferenz 'fast'")
response = agent.generate(
    "Was ist 2+2?",
    preferences=ModelPreference(quality="fast")
)
print(f"   Success: {response.success}")
print(f"   Model: {response.model_used}")
print(f"   Content: {response.content}")
print(f"   Latency: {response.latency_ms:.0f}ms")

# 5. Cache-Test (zweiter Aufruf sollte gecached sein)
print("\n5. Cache-Test")
response1 = agent.generate("Was ist die Hauptstadt von Deutschland?")
print(f"   Erster Aufruf: {response1.latency_ms:.0f}ms, cached={response1.cached}")
response2 = agent.generate("Was ist die Hauptstadt von Deutschland?")
print(f"   Zweiter Aufruf: {response2.latency_ms:.0f}ms, cached={response2.cached}")

# 6. JSON-Response
print("\n6. JSON-Response")
response = agent.generate(
    "Gib mir 3 Farben als JSON-Array zurück. Nur das Array, keine Erklärung.",
    response_format="json"
)
print(f"   Success: {response.success}")
print(f"   Content: {response.content}")

# 7. Convenience-Funktion
print("\n7. Convenience-Funktion llm_generate()")
response = llm_generate("Sage 'Test OK' auf Deutsch.")
print(f"   Success: {response.success}")
print(f"   Content: {response.content}")

print("\n" + "=" * 60)
print("TEST ABGESCHLOSSEN")
print("=" * 60)
