"""
Main views for BF Agent
Clean slate for auto-generation
"""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import BookProjects, ProjectPhaseHistory

# ============================================================================
# AUTO-GENERATED CRUD VIEWS SECTION
# ============================================================================
# Views will be generated here by auto_compliance_fixer.py


# ============================================================================
# CUSTOM WORKFLOW TRANSITION VIEWS
# ============================================================================


@require_POST
def project_workflow_start(request, pk):
    """Start workflow for a project - set to first step"""
    project = get_object_or_404(BookProjects, pk=pk)

    if not project.workflow_template:
        return HttpResponse("No workflow template assigned", status=400)

    # Get first step
    first_step = project.workflow_template.steps.order_by("order").first()
    if not first_step:
        return HttpResponse("Workflow template has no steps", status=400)

    # Set current step
    project.current_phase_step = first_step
    project.save()

    # Create history entry
    ProjectPhaseHistory.objects.create(
        project=project,
        workflow_step=first_step,
        phase=first_step.phase,
        entered_at=timezone.now(),
        entered_by=request.user if request.user.is_authenticated else None,
    )

    # Render updated workflow status
    return HttpResponse(
        render_to_string(
            "bfagent/partials/workflow_status.html", {"project": project}, request=request
        )
    )


@require_POST
def project_workflow_next(request, pk):
    """Move project to next workflow phase"""
    project = get_object_or_404(BookProjects, pk=pk)

    if not project.current_phase_step:
        return HttpResponse("No active workflow step", status=400)

    # Get next step
    next_step = (
        project.workflow_template.steps.filter(order__gt=project.current_phase_step.order)
        .order_by("order")
        .first()
    )

    if not next_step:
        return HttpResponse("Already at final step", status=400)

    # Close current phase in history
    current_history = project.phase_history.filter(exited_at__isnull=True).first()
    if current_history:
        current_history.exited_at = timezone.now()
        current_history.save()

    # Update to next step
    project.current_phase_step = next_step
    project.save()

    # Create new history entry
    ProjectPhaseHistory.objects.create(
        project=project,
        workflow_step=next_step,
        phase=next_step.phase,
        entered_at=timezone.now(),
        entered_by=request.user if request.user.is_authenticated else None,
    )

    # Render updated workflow status
    return HttpResponse(
        render_to_string(
            "bfagent/partials/workflow_status.html", {"project": project}, request=request
        )
    )


@require_POST
def project_workflow_previous(request, pk):
    """Move project to previous workflow phase"""
    project = get_object_or_404(BookProjects, pk=pk)

    if not project.current_phase_step:
        return HttpResponse("No active workflow step", status=400)

    if not project.current_phase_step.can_return:
        return HttpResponse("Cannot return from this phase", status=400)

    # Get previous step
    previous_step = (
        project.workflow_template.steps.filter(order__lt=project.current_phase_step.order)
        .order_by("-order")
        .first()
    )

    if not previous_step:
        return HttpResponse("Already at first step", status=400)

    # Close current phase in history
    current_history = project.phase_history.filter(exited_at__isnull=True).first()
    if current_history:
        current_history.exited_at = timezone.now()
        current_history.save()

    # Update to previous step
    project.current_phase_step = previous_step
    project.save()

    # Create new history entry
    ProjectPhaseHistory.objects.create(
        project=project,
        workflow_step=previous_step,
        phase=previous_step.phase,
        entered_at=timezone.now(),
        entered_by=request.user if request.user.is_authenticated else None,
        notes="Returned to previous phase",
    )

    # Render updated workflow status
    return HttpResponse(
        render_to_string(
            "bfagent/partials/workflow_status.html", {"project": project}, request=request
        )
    )
