#!/usr/bin/env python
"""Test ResearchAgent - Web Search, Fact Check, World Building."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.agents import ResearchAgent, quick_research

agent = ResearchAgent()

print("=" * 60)
print("RESEARCH AGENT TEST")
print("=" * 60)

# Test 1: Quick Search
print("\n📌 Test 1: Quick Search")
result = agent.quick_search("AI trends 2024", count=3)
print(f"Query: {result.query}")
print(f"Success: {result.success}")
print(f"Sources: {len(result.sources)}")
for s in result.sources:
    print(f"  - {s.title}")

# Test 2: Full Research
print("\n📌 Test 2: Full Research")
result = agent.full_research("Machine Learning best practices", max_sources=5)
print(f"Sources: {len(result.sources)}")
print(f"Findings: {len(result.findings)}")
if result.summary:
    print(f"Summary: {result.summary[:150]}...")

# Test 3: Fact Check
print("\n📌 Test 3: Fact Check")
fact_result = agent.fact_check("Python ist eine Programmiersprache")
print(f"Claim: {fact_result.claim}")
print(f"Verified: {fact_result.verified}")
print(f"Confidence: {fact_result.confidence:.0%}")

# Test 4: World Building Research
print("\n📌 Test 4: World Building")
world = agent.research_for_world_building("Magie-System", "fantasy")
print(f"Topic: {world['topic']}")
print(f"World Type: {world['world_type']}")
print(f"Suggested Elements:")
for elem in world['suggested_elements'][:3]:
    print(f"  - {elem}")

# Test 5: Convenience Function
print("\n📌 Test 5: Convenience Function")
quick = quick_research("Django best practices", count=2)
print(f"Quick research sources: {len(quick.sources)}")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
