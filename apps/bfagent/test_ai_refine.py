#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.bfagent.models import Llms
from apps.writing_hub.services.creative_agent_service import CreativeAgentService, IdeaSketch

# Test LLM call with first active LLM
print("=== Testing AI Refine ===")
llm = Llms.objects.filter(is_active=True).first()
print(f"Using LLM: {llm.name} ({llm.provider}/{llm.llm_name})")

service = CreativeAgentService(llm=llm)
idea = IdeaSketch(
    title_sketch="Der Letzte Wächter",
    hook="Ein alter Krieger muss sein Dorf vor einer uralten Bedrohung schützen",
    genre="Fantasy",
    setting_sketch="Mittelalterliche Welt mit Magie",
    protagonist_sketch="Ein müder Veteran, der seine Kampftage hinter sich lassen wollte",
    conflict_sketch="Dunkle Mächte erwachen und bedrohen alles, was er liebt"
)

print(f"\nInput Idea:")
print(f"  Title: {idea.title_sketch}")
print(f"  Hook: {idea.hook}")

result = service.refine_idea(idea, "Verbessere diese Idee und mache sie origineller")
print(f"\n=== Result ===")
print(f"Success: {result.success}")
print(f"Error: {result.error}")
if result.ideas:
    print(f"Ideas count: {len(result.ideas)}")
    refined = result.ideas[0]
    print(f"\nRefined Idea:")
    print(f"  Title: {refined.title_sketch}")
    print(f"  Hook: {refined.hook}")
    print(f"  Genre: {refined.genre}")
    print(f"  Setting: {refined.setting_sketch[:100] if refined.setting_sketch else '(none)'}...")
else:
    print("No ideas returned!")
