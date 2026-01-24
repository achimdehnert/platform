#!/usr/bin/env python
"""
Test REAL LLM call using API keys from .env
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.services.llm_client import execute_template

print("=" * 70)
print("TESTING REAL LLM CALL WITH API KEYS FROM .env")
print("=" * 70)
print()

# Check environment variables
print("ENVIRONMENT VARIABLES:")
print("-" * 70)
openai_key = os.environ.get("OPENAI_API_KEY", "")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

if openai_key:
    print(f"✅ OPENAI_API_KEY: {'*' * 20}{openai_key[-4:]}")
else:
    print("❌ OPENAI_API_KEY: Not found")

if anthropic_key:
    print(f"✅ ANTHROPIC_API_KEY: {'*' * 20}{anthropic_key[-4:]}")
else:
    print("❌ ANTHROPIC_API_KEY: Not found")

print()

if not (openai_key or anthropic_key):
    print("⚠️  NO API KEYS FOUND!")
    print()
    print("Please add to your .env file:")
    print("  OPENAI_API_KEY=sk-...")
    print("  ANTHROPIC_API_KEY=sk-ant-...")
    print()
    exit(1)

# Test Character Generation with real LLM
print("=" * 70)
print("TEST: CHARACTER GENERATION WITH REAL LLM")
print("=" * 70)
print()

print("Input Variables:")
print("  Character Name: Alexandra Chen")
print("  Character Role: Cybersecurity Expert")
print("  Genre: Techno-Thriller")
print()

print("Calling LLM...")
print("-" * 70)

result = execute_template(
    template_key="character_generation",
    variables={
        "character_name": "Alexandra Chen",
        "character_role": "Cybersecurity Expert",
        "genre": "Techno-Thriller"
    },
    version="1.0"
)

print()

if result["ok"]:
    print("✅ SUCCESS!")
    print("-" * 70)
    print()
    
    print(f"🤖 LLM Used: {result['llm_used'].provider} - {result['llm_used'].name}")
    print(f"📊 Execution ID: {result['execution'].id}")
    print(f"⏱️  Latency: {result['latency_ms']}ms")
    print()
    
    print("📝 GENERATED CHARACTER PROFILE:")
    print("=" * 70)
    print(result["text"])
    print("=" * 70)
    print()
    
    # Show template stats
    template = result["template"]
    print(f"📈 Template Statistics:")
    print(f"   Usage Count: {template.usage_count}")
    print(f"   Success Rate: {template.success_rate:.1f}%")
    print()
    
else:
    print("❌ FAILED!")
    print("-" * 70)
    print()
    print(f"Error: {result['error']}")
    print()
    
    if "API key" in str(result['error']):
        print("💡 TIP: Make sure API key is set in .env:")
        print("   OPENAI_API_KEY=sk-...")
        print()

# Test Dialogue Enhancement (shorter prompt)
print("=" * 70)
print("TEST 2: DIALOGUE ENHANCEMENT")
print("=" * 70)
print()

print("Input:")
print('  Original: "Hello there."')
print("  Character: Detective Morgan")
print()

print("Calling LLM...")
print("-" * 70)

result2 = execute_template(
    template_key="dialogue_enhancement",
    variables={
        "original_dialogue": "Hello there.",
        "character_name": "Detective Morgan"
    }
)

print()

if result2["ok"]:
    print("✅ SUCCESS!")
    print("-" * 70)
    print()
    print("📝 ENHANCED DIALOGUE:")
    print(result2["text"])
    print()
else:
    print("❌ FAILED!")
    print(f"Error: {result2['error']}")
    print()

print("=" * 70)
print("🎉 REAL LLM CALL TEST COMPLETE!")
print("=" * 70)
