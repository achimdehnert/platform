#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add Context Variables to Prompt Templates"""
import os
import sys
import django

# Fix Windows Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import PromptTemplate, AgentAction

print("=" * 80)
print("ADDING CONTEXT VARIABLES TO PROMPT TEMPLATES")
print("=" * 80)

print("\n[*] Finding ALL templates that need context variables...")

# Get ALL actions with templates
all_actions = AgentAction.objects.filter(prompt_template__isnull=False).select_related('prompt_template', 'agent')

updated = 0
skipped = 0
errors = 0

for action in all_actions:
    try:
        action_name = action.display_name
        
        if not action.prompt_template:
            print(f"   [ERROR] {action_name}: No template assigned")
            errors += 1
            continue
        
        template = action.prompt_template
        
        # Check if context variables already exist
        has_context = "{{ context }}" in template.template_text
        has_requirements = "{{ requirements }}" in template.template_text
        
        if has_context and has_requirements:
            print(f"   [SKIP] {action_name}: Already has context variables")
            skipped += 1
            continue
        
        # Add context section if missing
        if not has_context or not has_requirements:
            # Find where to insert (usually after instructions)
            template_text = template.template_text
            
            # Add context and requirements sections before "## Output" if it exists
            if "## Output" in template_text:
                parts = template_text.split("## Output")
                context_section = "\n\n## Input Context\n{{ context }}\n\n## Requirements\n{{ requirements }}\n\n"
                template_text = parts[0] + context_section + "## Output" + parts[1]
            else:
                # Add at the end
                template_text += "\n\n## Input Context\n{{ context }}\n\n## Requirements\n{{ requirements }}\n"
            
            # Update template
            template.template_text = template_text
            template.save()
            
            print(f"   [OK] Updated: {action.agent.name} -> {action_name}")
            updated += 1
            
    except Exception as e:
        print(f"   [ERROR] {action_name}: {e}")
        errors += 1

print("\n" + "=" * 80)
print(f"[SUMMARY] Updated: {updated} | Skipped: {skipped} | Errors: {errors}")
print("=" * 80)

# Verify all templates
print("\n[*] Verifying all templates...")
all_actions = AgentAction.objects.filter(prompt_template__isnull=False).select_related('prompt_template')
total = all_actions.count()
with_context = 0

for action in all_actions:
    if "{{ context }}" in action.prompt_template.template_text:
        with_context += 1

coverage = (with_context / total * 100) if total > 0 else 0
print(f"\n[COVERAGE] {with_context}/{total} templates have context variables ({coverage:.0f}%)")

if coverage == 100:
    print("\n[SUCCESS] All templates have context variables!")
else:
    print(f"\n[WARNING] {total - with_context} templates still need context variables")

print("\n" + "=" * 80)
print("[OK] CONTEXT VARIABLES COMPLETE")
print("=" * 80)
