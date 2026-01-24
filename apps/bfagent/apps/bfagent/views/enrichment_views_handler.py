"""
Handler-Based Enrichment Views (NEW)
Clean, modular, testable enrichment implementation
"""

import json
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.bfagent.handlers import (
    CharacterOutputHandler,
    EnrichmentHandler,
    ProcessingError,
    ProjectInputHandler,
    ValidationError,
)
from apps.bfagent.models import Agents, EnrichmentResponse

logger = logging.getLogger(__name__)


def project_enrich_run_handler(request, pk):
    """
    STEP 1: Preview filled prompt before execution (HANDLER VERSION)

    This is the CLEAN, handler-based version that replaces the old
    148-line monolithic function.
    """
    logger.info(f"🚀 project_enrich_run_handler - Project: {pk}")

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        # INPUT HANDLER - Validate and prepare context
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=pk,
            agent_id=request.POST.get("agent_id"),
            action=request.POST.get("action"),
            parameters={
                "context": request.POST.get("context", ""),
                "requirements": request.POST.get("requirements", ""),
            },
        )

        logger.info(f"✅ Context prepared for action: {context['action']}")

        # Get agent and action for template rendering
        project = context["project"]
        agent = get_object_or_404(Agents, pk=context["agent_id"])

        # Special handling for outline_agent (framework actions)
        if agent.agent_type == "outline_agent":
            return _handle_framework_action(request, context)

        # Regular template-based actions
        return _handle_template_action(request, context, project, agent)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return HttpResponse(f"<div class='alert alert-danger'>{e}</div>", status=400)
    except Exception as e:
        logger.exception(f"Error in enrich run: {e}")
        return HttpResponse(f"<div class='alert alert-danger'>Error: {e}</div>", status=500)


def _handle_framework_action(request, context):
    """Handle framework-based actions (outline generation)"""
    from apps.bfagent.services.outline_actions import handle_outline_action

    project = context["project"]
    action_name = context["action"]

    try:
        results = handle_outline_action(
            action=action_name,
            project=project,
            context={
                "num_chapters": context["parameters"].get("num_chapters", 12),
                "requirements": context["parameters"].get("context", ""),
            },
        )

        logger.info(f"✅ Framework action completed: {len(results)} results")

        # Return results directly
        agent = get_object_or_404(Agents, pk=context["agent_id"])
        from apps.bfagent.models import AgentAction

        action = AgentAction.objects.filter(agent=agent, name=action_name).first()

        return render(
            request,
            "bfagent/partials/project_enrich_results.html",
            {
                "project": project,
                "agent": agent,
                "action": action,
                "suggestions": results,
                "append_mode": False,
            },
        )

    except Exception as e:
        logger.exception(f"Framework action failed: {e}")
        raise ProcessingError(f"Framework action failed: {e}")


def _handle_template_action(request, context, project, agent):
    """Handle template-based enrichment actions"""
    from apps.bfagent.models import AgentAction

    action_name = context["action"]

    # Get action and template
    action = (
        AgentAction.objects.filter(agent=agent, name=action_name)
        .select_related("prompt_template")
        .first()
    )

    if not action:
        raise ValidationError(f"Action '{action_name}' not found")

    template = action.prompt_template
    if not template:
        raise ValidationError("No template assigned to this action")

    # Build filled template
    filled_template = template.template_text
    system_prompt = ""

    # Extract system prompt from template metadata
    if template.description:
        try:
            metadata = json.loads(template.description)
            system_prompt = metadata.get("system_prompt", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Replace template variables
    project_context = context["project_context"]
    for key, value in project_context.items():
        placeholder = "{{" + f" {key} " + "}}"
        filled_template = filled_template.replace(placeholder, str(value))

    # Get previous outputs for context
    previous_outputs = (
        EnrichmentResponse.objects.filter(project=project, status="applied")
        .select_related("agent")
        .order_by("-applied_at")[:10]
    )

    # Render preview
    return render(
        request,
        "bfagent/partials/prompt_preview.html",
        {
            "project": project,
            "agent": agent,
            "action_name": action_name,
            "filled_template": filled_template,
            "system_prompt": system_prompt,
            "context_data": project_context,
            "user_context": context["parameters"].get("context", ""),
            "previous_outputs": previous_outputs,
            "selected_fields_json": json.dumps(list(project_context.keys())),
        },
    )


def project_enrich_execute_handler(request, pk):
    """
    STEP 2: Execute enrichment with LLM (HANDLER VERSION)

    This is the CLEAN version that replaces the old 282-line function.
    Uses handlers for all business logic.
    """
    logger.info(f"🚀 project_enrich_execute_handler - Project: {pk}")

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        # INPUT HANDLER - Prepare execution context
        input_handler = ProjectInputHandler()
        context = input_handler.prepare_enrichment_context(
            project_id=pk,
            agent_id=request.POST.get("agent_id"),
            action=request.POST.get("action"),
            parameters={
                "system_prompt": request.POST.get("system_prompt", ""),
                "user_prompt": request.POST.get("user_prompt", ""),
            },
        )

        # PROCESSING HANDLER - Execute enrichment
        processing_handler = EnrichmentHandler()
        result = processing_handler.execute(context)

        if not result.get("success"):
            raise ProcessingError(result.get("error", "Unknown error"))

        logger.info(f"✅ Enrichment executed successfully")

        # OUTPUT HANDLER - Save results
        return _save_enrichment_results(request, context, result)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return HttpResponse(f"<div class='alert alert-danger'>{e}</div>", status=400)
    except ProcessingError as e:
        logger.error(f"Processing error: {e}")
        return HttpResponse(f"<div class='alert alert-danger'>{e}</div>", status=500)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return HttpResponse(
            f"<div class='alert alert-danger'>Unexpected error: {e}</div>", status=500
        )


def _save_enrichment_results(request, context, result):
    """Save enrichment results to database"""
    project = context["project"]
    agent = get_object_or_404(Agents, pk=context["agent_id"])
    action_name = context["action"]

    suggestions = result.get("suggestions", [])

    # Create EnrichmentResponse records
    enrichment_responses = []
    for suggestion in suggestions:
        # Skip object creation suggestions (handled separately)
        if suggestion.get("creates_object") or suggestion.get("creates_multiple"):
            continue

        enrichment_response = EnrichmentResponse.objects.create(
            project=project,
            agent=agent,
            action_name=action_name,
            field_name=suggestion.get("field_name", "unknown"),
            suggested_value=suggestion.get("new_value", ""),
            confidence=float(suggestion.get("confidence", 0)),
            rationale=suggestion.get("rationale", ""),
            target_model=suggestion.get("target_model", "project"),
            target_id=suggestion.get("target_id"),
            status="pending",
        )
        enrichment_responses.append(enrichment_response)

    # Handle character cast generation
    for suggestion in suggestions:
        if suggestion.get("creates_multiple") and suggestion.get("target_model") == "characters":
            _create_character_cast(project, suggestion)

    # Handle complete book generation
    for suggestion in suggestions:
        if suggestion.get("creates_multiple") and suggestion.get("target_model") == "chapters":
            _create_book_chapters(project, suggestion)

    # Render results
    from apps.bfagent.models import AgentAction

    action = AgentAction.objects.filter(agent=agent, name=action_name).first()

    return render(
        request,
        "bfagent/partials/project_enrich_results.html",
        {
            "project": project,
            "agent": agent,
            "action": action,
            "suggestions": suggestions,
            "enrichment_responses": enrichment_responses,
            "append_mode": False,
        },
    )


def _create_character_cast(project, suggestion):
    """Create multiple characters from AI generation"""
    from apps.bfagent.utils.character_parser_v2 import parse_character_cast

    logger.info("🎭 Creating character cast...")

    content = suggestion.get("new_value", "")
    characters_data = parse_character_cast(content, project)

    if not characters_data:
        logger.warning("No characters parsed from content")
        return

    # Use OUTPUT HANDLER for bulk creation
    output_handler = CharacterOutputHandler()
    characters = output_handler.bulk_create(characters_data)

    logger.info(f"✅ Created {len(characters)} characters")

    # Update suggestion
    suggestion["created_objects_count"] = len(characters)
    suggestion["rationale"] = f"Successfully created {len(characters)} characters"


def _create_book_chapters(project, suggestion):
    """Create multiple chapters from complete book generation"""
    from apps.bfagent.models import BookChapters
    from apps.bfagent.utils.book_parser import parse_complete_book

    logger.info("📚 Creating book chapters...")

    content = suggestion.get("new_value", "")
    chapters_data = parse_complete_book(content)

    if not chapters_data:
        logger.warning("No chapters parsed from content")
        return

    created_count = 0
    for chapter_data in chapters_data:
        try:
            BookChapters.objects.create(project=project, **chapter_data)
            created_count += 1
        except Exception as e:
            logger.error(f"Failed to create chapter: {e}")

    logger.info(f"✅ Created {created_count} chapters")

    # Update suggestion
    suggestion["created_objects_count"] = created_count
    suggestion["rationale"] = f"Successfully created {created_count} chapters"
