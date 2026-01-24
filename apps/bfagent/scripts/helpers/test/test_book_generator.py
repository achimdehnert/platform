"""
Quick test for Book Generator

Tests the book generator with a minimal 3-chapter story.
"""

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import Llms

print("=" * 70)
print("🧪 BOOK GENERATOR QUICK TEST")
print("=" * 70)
print()

# Check LLM availability
print("🔍 Checking available LLMs...")
llms = Llms.objects.filter(is_active=True)

if not llms.exists():
    print("❌ No active LLMs found!")
    print()
    print("💡 Please add an LLM first:")
    print("   python manage.py shell")
    print("   >>> from apps.bfagent.models import Llms")
    print("   >>> Llms.objects.create(")
    print("   ...     name='GPT-4 Mini',")
    print("   ...     provider='openai',")
    print("   ...     llm_name='gpt-4o-mini',")
    print("   ...     api_key='sk-...',")
    print("   ...     is_active=True")
    print("   ... )")
    sys.exit(1)

print("✅ Available LLMs:")
for llm in llms:
    print(f"   {llm.id}: {llm.llm_name} ({llm.provider})")
print()

# Use first LLM
llm = llms.first()
print(f"🤖 Using: {llm.llm_name}")
print()

# Test outline
test_outline = """
Chapter 1: The Beginning - A young wizard discovers their powers
Chapter 2: The Challenge - They must face their first magical duel  
Chapter 3: The Victory - They triumph and gain confidence
"""

print("📝 Test Outline:")
print(test_outline)
print()

# Check API key
if not llm.api_key or llm.api_key == "":
    print("⚠️  WARNING: No API key configured for this LLM")
    print("   The script will run but generation will fail without a valid API key")
    print()
    response = input("   Continue anyway? (y/n): ")
    if response.lower() != 'y':
        print("   Aborted.")
        sys.exit(0)

# Run test
print("=" * 70)
print("🚀 Starting test generation...")
print("=" * 70)
print()

try:
    from generate_book import BookGenerator
    
    generator = BookGenerator(
        title="The Young Wizard",
        outline=test_outline,
        llm_id=llm.id,
        genre="Fantasy",
        words_per_chapter=500,  # Short chapters for quick test
        temperature=0.7
    )
    
    result = generator.generate_book()
    
    print()
    print("=" * 70)
    print("✅ TEST SUCCESSFUL!")
    print("=" * 70)
    print()
    print(f"📁 Your book is ready at:")
    print(f"   {result['book_file']}")
    print()
    print("💡 To generate a real book:")
    print(f"   python generate_book.py --interactive")
    print()
    
except Exception as e:
    print()
    print("=" * 70)
    print("❌ TEST FAILED")
    print("=" * 70)
    print()
    print(f"Error: {e}")
    print()
    import traceback
    traceback.print_exc()
    print()
    print("💡 Common issues:")
    print("   1. No API key configured")
    print("   2. Invalid API key")
    print("   3. API rate limit exceeded")
    print("   4. Network connection issues")
    print()
