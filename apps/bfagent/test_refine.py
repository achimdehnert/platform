#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.bfagent.models import Llms
from apps.writing_hub.models import CreativeSession
from apps.writing_hub.services.creative_agent_service import CreativeAgentService, IdeaSketch

# Check session LLM
session = CreativeSession.objects.get(id='ab8e0948-b2ee-431a-a33e-674195f991a4')
print(f'Session LLM: {session.llm}')
print(f'Session LLM active: {session.llm.is_active if session.llm else None}')

# Use session's LLM like the web view does
llm = session.llm
if not llm or not llm.is_active:
    llm = Llms.objects.filter(is_active=True).first()
print(f'Using LLM: {llm.name} ({llm.provider}/{llm.llm_name})')

service = CreativeAgentService(llm=llm)
idea = IdeaSketch(
    title_sketch='Das Dritte Licht',
    hook='Karl und Eliza entdecken etwas Unglaubliches',
    genre='Fantasy',
    setting_sketch='Sibirische Tundra',
    protagonist_sketch='Karl mit besonderem Talent',
    conflict_sketch='Die Welt steht vor einer Entscheidung'
)

# First test raw LLM call to see actual response
from apps.bfagent.services import llm_client
raw_result = llm_client.generate_text(
    prompt='Antworte nur mit: {"test": "ok"}',
    llm_id=str(llm.id)
)
print(f'Raw LLM test: {raw_result}')
print(f'Raw text: {raw_result.get("text", "")[:500]}')

result = service.refine_idea(idea, 'Verbessere diese Idee')
print(f'Result: success={result.success}')
print(f'Error: {result.error}')
print(f'Ideas count: {len(result.ideas) if result.ideas else 0}')
if result.ideas:
    print(f'First idea title: {result.ideas[0].title_sketch}')
