#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug Enrichment Panel - Why no agents?"""
import os
import sys
import django
from pathlib import Path

# Fix Windows Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import (
    BookProjects, WorkflowPhase, PhaseAgentConfig, 
    Agents, WorkflowTemplate, BookTypes
)

print("=" * 80)
print("DEBUG ENRICHMENT PANEL")
print("=" * 80)

# Get project 16
project = BookProjects.objects.get(pk=16)

print(f"\n[*] Project: {project.title}")
print(f"   Genre: {project.genre}")
print(f"   book_type_id: {project.book_type_id}")
print(f"   workflow_template: {project.workflow_template}")
print(f"   current_phase_step: {project.current_phase_step}")

# Check phase from URL (phase=1)
phase_id = 1
current_phase = WorkflowPhase.objects.filter(id=phase_id).first()

print(f"\n[*] Current Phase (from URL phase={phase_id}):")
print(f"   Phase: {current_phase.name if current_phase else 'None'}")

# Check workflow template logic
workflow_template = project.workflow_template

print(f"\n[*] Workflow Template Check:")
print(f"   project.workflow_template: {workflow_template}")

if not workflow_template and project.book_type_id:
    print(f"   No workflow assigned, checking book_type_id: {project.book_type_id}")
    
    book_type = BookTypes.objects.filter(id=project.book_type_id).first()
    print(f"   BookType found: {book_type}")
    
    if book_type:
        workflow_template = (
            WorkflowTemplate.objects.filter(book_type=book_type, is_active=True)
            .filter(is_default=True)
            .first()
        )
        print(f"   Default workflow: {workflow_template}")
        
        if not workflow_template:
            workflow_template = (
                WorkflowTemplate.objects.filter(book_type=book_type, is_active=True)
                .first()
            )
            print(f"   First active workflow: {workflow_template}")

if workflow_template:
    valid_phase_ids = list(
        workflow_template.steps.values_list("phase_id", flat=True)
    )
    print(f"   Valid phase IDs from workflow: {valid_phase_ids}")
else:
    valid_phase_ids = []
    print(f"   No workflow template - valid_phase_ids is empty!")

# Check which agents should be shown
print(f"\n[*] Agent Selection Logic:")

if current_phase:
    print(f"   Using current_phase: {current_phase.name}")
    agent_ids = PhaseAgentConfig.objects.filter(phase=current_phase).values_list(
        "agent_id", flat=True
    )
    print(f"   Agent IDs for this phase: {list(agent_ids)}")
    
    agents = Agents.objects.filter(id__in=agent_ids, status="active").order_by(
        "agent_type", "name"
    )
    print(f"   Active agents found: {agents.count()}")
    for agent in agents:
        print(f"      - {agent.name} (id={agent.id}, status={agent.status})")
        
elif valid_phase_ids:
    print(f"   No specific phase, using valid_phase_ids: {valid_phase_ids}")
    agent_ids = PhaseAgentConfig.objects.filter(
        phase_id__in=valid_phase_ids
    ).values_list("agent_id", flat=True).distinct()
    print(f"   Agent IDs for workflow: {list(agent_ids)}")
    
    agents = Agents.objects.filter(id__in=agent_ids, status="active").order_by(
        "agent_type", "name"
    )
    print(f"   Active agents found: {agents.count()}")
    for agent in agents:
        print(f"      - {agent.name} (id={agent.id}, status={agent.status})")
else:
    print(f"   Fallback: Showing all active agents")
    agents = Agents.objects.filter(status="active").order_by("agent_type", "name")
    print(f"   Active agents found: {agents.count()}")

print("\n" + "=" * 80)
print("[OK] DEBUG COMPLETE")
print("=" * 80)
