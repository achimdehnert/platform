"""V2 Migration Dashboard - Track DB-driven architecture adoption"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.bfagent.models import (
    WorkflowPhase, PhaseActionConfig, AgentAction,
    PromptTemplate, ActionTemplate
)
import re
from pathlib import Path
@login_required
def v2_migration_dashboard(request):
    """Main V2 migration tracking dashboard"""
    stats = {
        'database': {
            'workflow_phases': WorkflowPhase.objects.count(),
            'phase_actions': PhaseActionConfig.objects.count(),
            'agent_actions': AgentAction.objects.count(),
            'prompt_templates': PromptTemplate.objects.count(),
        },
        'progress': _calculate_progress()
    }
    return render(request, 'bfagent/v2_dashboard.html', {
        'stats': stats,
        'title': 'V2 Migration Dashboard'
    })
def _calculate_progress():
    """Calculate overall V2 migration progress"""
    # Simple progress based on DB setup
    db_progress = 100 if WorkflowPhase.objects.count() > 0 else 0
    return {
        'total': db_progress,
        'database': db_progress
    }
