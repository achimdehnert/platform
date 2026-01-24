#!/usr/bin/env python
"""Quick check for prompt templates"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import AgentAction, PromptTemplate

# Get sample actions
actions = AgentAction.objects.select_related('agent', 'prompt_template').all()[:3]

print("=" * 80)
print("SAMPLE AGENTACTIONS WITH PROMPTS")
print("=" * 80)

for action in actions:
    print(f"\n{'='*80}")
    print(f"Agent: {action.agent.name}")
    print(f"Action: {action.display_name}")
    print(f"Action Name: {action.name}")
    
    if action.prompt_template:
        print(f"\nPrompt Template: {action.prompt_template.name}")
        print(f"Prompt Length: {len(action.prompt_template.template_text)} chars")
        print(f"\nPrompt Preview (first 300 chars):")
        print("-" * 80)
        print(action.prompt_template.template_text[:300])
        print("-" * 80)
    else:
        print("❌ NO PROMPT TEMPLATE!")

print(f"\n{'='*80}")
print(f"SUMMARY: {actions.count()} total actions")
print(f"Actions with prompts: {AgentAction.objects.filter(prompt_template__isnull=False).count()}")
print(f"Actions without prompts: {AgentAction.objects.filter(prompt_template__isnull=True).count()}")
print("=" * 80)
