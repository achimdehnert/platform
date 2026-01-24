#!/usr/bin/env python
"""Check which table has the templates"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate, PromptTemplateLegacy

print("=" * 70)
print("TEMPLATE TABLE CHECK")
print("=" * 70)
print()

# Check new table
print("NEW TABLE (prompt_templates):")
new_count = PromptTemplate.objects.count()
print(f"  Count: {new_count}")
if new_count > 0:
    sample = PromptTemplate.objects.first()
    print(f"  Sample: {sample.name} (key: {sample.template_key})")
print()

# Check legacy table
print("LEGACY TABLE (prompt_templates_legacy):")
legacy_count = PromptTemplateLegacy.objects.count()
print(f"  Count: {legacy_count}")
if legacy_count > 0:
    sample = PromptTemplateLegacy.objects.first()
    print(f"  Sample: {sample.name}")
    print(f"  Has template_key? {hasattr(sample, 'template_key')}")
print()

print("=" * 70)
print("CONCLUSION:")
if new_count > 0:
    print("✅ Templates are in the NEW table (prompt_templates)")
    print("   → Ready to use template_key lookups")
elif legacy_count > 0:
    print("⚠️  Templates are in LEGACY table (prompt_templates_legacy)")
    print("   → Need to migrate data or use PromptTemplateLegacy for now")
else:
    print("❌ No templates found in either table!")
    print("   → Need to create initial templates")
print("=" * 70)
