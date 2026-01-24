#!/usr/bin/env python
"""
Test All Templates - Verify all 4 sample templates work
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate

print("=" * 70)
print("TESTING ALL TEMPLATES")
print("=" * 70)
print()

templates = PromptTemplate.objects.all().order_by('template_key', 'version')

print(f"Found {templates.count()} templates")
print()

for template in templates:
    print("-" * 70)
    print(f"Template: {template.name}")
    print(f"Key: {template.template_key} | Version: {template.version}")
    print(f"Category: {template.category}")
    print()
    
    # Test specific templates
    if template.template_key == "character_generation" and template.version == "1.0":
        print("Testing basic character generation...")
        try:
            rendered = template.render({
                "character_name": "Test Character",
                "character_role": "Hero",
                "genre": "Fantasy"
            })
            if "Test Character" in rendered and "Hero" in rendered:
                print("✅ Variables substituted correctly!")
            else:
                print("❌ Variables NOT substituted!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    elif template.template_key == "chapter_outline":
        print("Testing chapter outline...")
        try:
            rendered = template.render({
                "chapter_number": "5",
                "story_arc": "Rising Action"
            })
            if "5" in rendered and "Rising Action" in rendered:
                print("✅ Chapter variables working!")
            else:
                print("❌ Chapter variables NOT working!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    elif template.template_key == "dialogue_enhancement":
        print("Testing dialogue enhancement...")
        try:
            rendered = template.render({
                "original_dialogue": "Hello there.",
                "character_name": "Obi-Wan"
            })
            if "Hello there." in rendered and "Obi-Wan" in rendered:
                print("✅ Dialogue variables working!")
            else:
                print("❌ Dialogue variables NOT working!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    elif template.template_key == "character_generation" and template.version == "2.0-beta":
        print("Testing BETA version (A/B Test)...")
        print(f"A/B Test Group: {template.ab_test_group}")
        print(f"A/B Test Weight: {template.ab_test_weight} (20% traffic)")
        try:
            rendered = template.render({
                "character_name": "Beta Test",
                "character_role": "Tester",
                "genre": "Testing"
            })
            if "Beta Test" in rendered:
                print("✅ Beta version working!")
            else:
                print("❌ Beta version NOT working!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()

print("=" * 70)
print("🎉 ALL TEMPLATES TESTED!")
print("=" * 70)
