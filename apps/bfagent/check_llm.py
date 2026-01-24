#!/usr/bin/env python
"""Debug script für KI-Verbesserung JSON Parsing."""
import os
import json
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('apps.writing_hub.services.creative_agent_service')
logger.setLevel(logging.DEBUG)

from apps.bfagent.models import Llms
from apps.writing_hub.models import CreativeSession
from apps.writing_hub.services.creative_agent_service import CreativeAgentService, IdeaSketch

print("=" * 60)
print("DEBUG: KI-Verbesserung JSON Parsing")
print("=" * 60)

# Test mit realistischen Daten wie vom Frontend
idea = IdeaSketch(
    title_sketch="Der letzte Wächter",
    hook="Ein alter Ritter muss sein Königreich ein letztes Mal verteidigen",
    genre="Fantasy",
    setting_sketch="Mittelalterliches Königreich am Rande des Untergangs",
    protagonist_sketch="Sir Aldric, 65 Jahre alt, müde aber pflichtbewusst",
    conflict_sketch="Eine Armee von Untoten bedroht das letzte Dorf"
)

# Nutze GPT-4o-mini (zuverlässiger für JSON)
llm = Llms.objects.filter(llm_name__icontains='gpt-4o-mini', is_active=True).first()
if not llm:
    llm = Llms.objects.filter(is_active=True).first()
print(f"\nUsing LLM: {llm.name} ({llm.provider}/{llm.llm_name})")

service = CreativeAgentService(llm=llm)

print("\n--- Calling refine_idea ---")
result = service.refine_idea(idea, "Mache den Hook spannender und füge mehr Details hinzu")

print(f"\n--- Result ---")
print(f"Success: {result.success}")
print(f"Error: {result.error}")
print(f"Ideas count: {len(result.ideas) if result.ideas else 0}")

if result.ideas:
    for i, idea in enumerate(result.ideas):
        print(f"\nIdea {i+1}:")
        print(f"  Title: {idea.title_sketch}")
        print(f"  Hook: {idea.hook[:100] if idea.hook else 'None'}...")
        print(f"  Genre: {idea.genre}")
else:
    print("No ideas parsed!")
