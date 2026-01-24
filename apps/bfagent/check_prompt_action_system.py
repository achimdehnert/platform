#!/usr/bin/env python
"""Check existing Prompt/Action Management System"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import (
    AgentAction, 
    ActionTemplate, 
    PromptTemplate, 
    PromptTemplateLegacy,
    Agents
)

print("=" * 80)
print("📊 PROMPT/ACTION MANAGEMENT SYSTEM")
print("=" * 80)

# Check Agents
print("\n✅ AGENTS:")
agents = Agents.objects.all()
print(f"   Total: {agents.count()}")
for agent in agents[:5]:
    print(f"   - {agent.name} ({agent.agent_type})")

# Check AgentActions
print("\n✅ AGENT ACTIONS:")
actions = AgentAction.objects.all()
print(f"   Total: {actions.count()}")

chapter_actions = AgentAction.objects.filter(name__icontains='chapter')
print(f"\n   Chapter-related actions: {chapter_actions.count()}")
for action in chapter_actions:
    print(f"   - {action.name}: {action.display_name}")
    print(f"     Target: {action.target_model}")
    print(f"     Has Template: {action.prompt_template is not None}")
    if action.has_templates:
        print(f"     V2 Templates: {action.action_templates.count()}")

# Check PromptTemplate (V2)
print("\n✅ PROMPT TEMPLATES (V2):")
templates_v2 = PromptTemplate.objects.all()
print(f"   Total: {templates_v2.count()}")

chapter_templates = PromptTemplate.objects.filter(category='chapter')
print(f"\n   Chapter templates: {chapter_templates.count()}")
for tmpl in chapter_templates:
    print(f"   - {tmpl.template_key}: {tmpl.name}")
    print(f"     Active: {tmpl.is_active}")
    print(f"     Usage: {tmpl.usage_count}")

# Check Legacy Templates
print("\n✅ LEGACY PROMPT TEMPLATES:")
legacy_templates = PromptTemplateLegacy.objects.all()
print(f"   Total: {legacy_templates.count()}")
for tmpl in legacy_templates[:5]:
    print(f"   - {tmpl.name}")

# Check ActionTemplate mappings
print("\n✅ ACTION → TEMPLATE MAPPINGS:")
mappings = ActionTemplate.objects.all()
print(f"   Total: {mappings.count()}")
for mapping in mappings[:5]:
    print(f"   - {mapping.action.name} → {mapping.template.name}")
    print(f"     Default: {mapping.is_default}")

print("\n" + "=" * 80)
print("🎯 SYSTEM ARCHITECTURE")
print("=" * 80)

print("""
OLD SYSTEM (Legacy):
-------------------
Agent → AgentAction → PromptTemplateLegacy
                       ↓
                   ActionTemplate (M2M)

NEW SYSTEM (V2):
---------------
PromptTemplate (standalone, category-based)
- More features
- Better tracking
- A/B testing
- Multi-language

CURRENT STATE:
-------------
✅ Both systems exist
⚠️ ChapterGenerateHandler uses NEITHER!
→ Hardcoded prompts in code

RECOMMENDATION:
--------------
Option 1: Use PromptTemplate (V2) ✅ BEST
- Modern system
- More features
- Better for our use case
- Category-based (chapter, character, etc.)

Option 2: Use AgentAction → PromptTemplate
- Connects to Agent system
- Good for multi-agent workflows
- More complex setup

Option 3: Hybrid
- AgentAction for routing
- PromptTemplate for actual prompts
- Best of both worlds
""")

print("\n" + "=" * 80)
print("💡 NEXT STEPS")
print("=" * 80)

print("""
1. CREATE CHAPTER GENERATION TEMPLATES IN DB:
   - chapter_outline_generation
   - chapter_content_generation
   - chapter_section_expansion

2. UPDATE ChapterGenerateHandler:
   - Load prompts from PromptTemplate
   - Use template rendering
   - Track executions

3. IMPLEMENT STORAGE SERVICE:
   - Domain-based file structure
   - Automatic path generation
   - Version control

4. BONUS - CONNECT TO AGENTS:
   - Create "Chapter Writer" Agent
   - Connect AgentActions
   - Full workflow integration
""")

print("\n" + "=" * 80)
