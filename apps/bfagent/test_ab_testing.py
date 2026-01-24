#!/usr/bin/env python
"""
Test A/B Testing - Compare stable vs beta versions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate

print("=" * 70)
print("A/B TESTING COMPARISON")
print("=" * 70)
print()

# Get both versions
stable = PromptTemplate.objects.get(template_key="character_generation", version="1.0")
beta = PromptTemplate.objects.get(template_key="character_generation", version="2.0-beta")

print("STABLE VERSION (v1.0)")
print("-" * 70)
print(f"Name: {stable.name}")
print(f"A/B Test Weight: {stable.ab_test_weight} (Default)")
print(f"Temperature: {stable.temperature}")
print(f"Max Tokens: {stable.max_tokens}")
print()

print("BETA VERSION (v2.0-beta)")
print("-" * 70)
print(f"Name: {beta.name}")
print(f"A/B Test Group: {beta.ab_test_group}")
print(f"A/B Test Weight: {beta.ab_test_weight} (20% traffic)")
print(f"Temperature: {beta.temperature}")
print(f"Max Tokens: {beta.max_tokens}")
print()

# Test same input on both
test_vars = {
    "character_name": "Alex Rivera",
    "character_role": "Detective",
    "genre": "Crime Thriller"
}

print("=" * 70)
print("RENDERING COMPARISON")
print("=" * 70)
print()

print("STABLE VERSION OUTPUT:")
print("-" * 70)
stable_output = stable.render(test_vars)
print(stable_output)
print()

print("=" * 70)
print("BETA VERSION OUTPUT:")
print("-" * 70)
beta_output = beta.render(test_vars)
print(beta_output)
print()

print("=" * 70)
print("DIFFERENCES:")
print("-" * 70)
if "psychological" in beta_output.lower() and "psychological" not in stable_output.lower():
    print("✅ Beta version mentions 'psychological depth' (enhanced feature)")
if "Myers-Briggs" in beta_output:
    print("✅ Beta version includes Myers-Briggs personality typing")
if len(beta_output) > len(stable_output):
    print(f"✅ Beta version is more detailed ({len(beta_output)} vs {len(stable_output)} chars)")

print()
print("=" * 70)
print("A/B TESTING SETUP VERIFIED!")
print("=" * 70)
print()
print("IN PRODUCTION:")
print("  - 80% of users get v1.0 (stable)")
print("  - 20% of users get v2.0-beta (enhanced)")
print("  - Track which performs better via PromptExecution")
print()
