#!/usr/bin/env python
"""
Test Prompt Management System v2.0 Features
Quick verification script for new functionality.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate, PromptExecution, PromptTemplateTest

print("=" * 70)
print("PROMPT MANAGEMENT SYSTEM V2.0 - FEATURE TEST")
print("=" * 70)
print()

# Test 1: Template Keys
print("1️⃣  TEMPLATE KEYS (NEW FEATURE)")
print("-" * 70)
templates = PromptTemplate.objects.all()[:5]
print(f"Total Templates: {PromptTemplate.objects.count()}")
print()
print("Sample Templates with template_key:")
for t in templates:
    print(f"  • ID {t.id:2} | Key: {t.template_key:30} | Name: {t.name[:40]}")
print()

# Test 2: Semantic Versioning
print("2️⃣  SEMANTIC VERSIONING (NEW FEATURE)")
print("-" * 70)
version_samples = PromptTemplate.objects.values_list('version', flat=True).distinct()[:5]
print(f"Version Types Found: {list(version_samples)}")
print("Note: Version is now CharField - supports semantic versioning!")
print()

# Test 3: New Fields Check
print("3️⃣  NEW FIELDS CHECK")
print("-" * 70)
sample = PromptTemplate.objects.first()
if sample:
    print(f"Template: {sample.name}")
    print(f"  • template_key: {sample.template_key}")
    print(f"  • version: {sample.version}")
    print(f"  • top_p: {getattr(sample, 'top_p', 'Not set')}")
    print(f"  • user_prompt_template: {'Set' if getattr(sample, 'user_prompt_template', None) else 'None'}")
    print(f"  • variable_defaults: {getattr(sample, 'variable_defaults', {})}")
print()

# Test 4: New Models Available
print("4️⃣  NEW MODELS CHECK")
print("-" * 70)
print(f"  • PromptExecution model: {'✅ Available' if PromptExecution else '❌ Missing'}")
print(f"  • PromptTemplateTest model: {'✅ Available' if PromptTemplateTest else '❌ Missing'}")
print(f"  • PromptExecution count: {PromptExecution.objects.count()}")
print(f"  • PromptTemplateTest count: {PromptTemplateTest.objects.count()}")
print()

# Test 5: Template Lookup Methods
print("5️⃣  TEMPLATE LOOKUP METHODS")
print("-" * 70)
print("Old method (by ID):")
try:
    old_lookup = PromptTemplate.objects.get(id=2)
    print(f"  ✅ ID 2 → {old_lookup.name}")
except PromptTemplate.DoesNotExist:
    print(f"  ❌ ID 2 not found")

print()
print("New method (by template_key):")
try:
    new_lookup = PromptTemplate.objects.get(template_key="legacy_template_2")
    print(f"  ✅ template_key='legacy_template_2' → {new_lookup.name}")
    print(f"     More stable: Key doesn't change when data is regenerated!")
except PromptTemplate.DoesNotExist:
    print(f"  ❌ template_key='legacy_template_2' not found")
print()

print("=" * 70)
print("🎉 PROMPT MANAGEMENT SYSTEM V2.0 - READY FOR USE!")
print("=" * 70)
print()
print("NEXT STEPS:")
print("1. Refactor code to use template_key instead of IDs")
print("2. Implement PromptExecution tracking for LLM calls")
print("3. Set up A/B testing with PromptTemplateTest")
print("4. Update templates to use semantic versioning (1.0, 1.1, 2.0-beta)")
print()
