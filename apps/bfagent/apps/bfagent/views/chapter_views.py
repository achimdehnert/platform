"""
Chapter Views - Phase 2 Chapter Writing System
HTMX-powered chapter management with AI integration
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from ..models import Agents, BookChapters
from ..services.project_enrichment import run_enrichment

# SIMPLIFIED: Essential actions for testing
ENRICH_ACTIONS_BY_AGENT = {
    "chapter_agent": [
        "outline",
        "write_short_content",
        "write_everything",
    ],
}


@require_http_methods(["POST"])
def chapter_action(request, pk, action):
    """PHASE 2: Handle Chapter AI Actions with storyline context

    Executes AI actions on chapters using the integrated Chapter Writing System.
    Supports all chapter_agent actions with full storyline context.
    """
    chapter = get_object_or_404(BookChapters, pk=pk)

    # Get chapter agent (first available chapter_agent)
    chapter_agent = Agents.objects.filter(agent_type="chapter_agent", status="active").first()

    if not chapter_agent:
        return JsonResponse(
            {
                "error": "No active Chapter Agent found. Please create and activate a Chapter Agent first."
            },
            status=400,
        )

    # Validate action is allowed for chapter_agent
    chapter_actions = ENRICH_ACTIONS_BY_AGENT.get("chapter_agent", [])
    if action not in chapter_actions:
        return JsonResponse(
            {
                "error": f'Action "{action}" is not supported for Chapter Agent. Available actions: {", ".join(chapter_actions)}'
            },
            status=400,
        )

    try:
        # Run enrichment with full storyline context
        results = run_enrichment(
            project=chapter.project, agent=chapter_agent, action=action, chapter=chapter
        )

        # Extract suggestions
        suggestions = results.get("suggestions", [])
        if not suggestions:
            return JsonResponse(
                {
                    "error": "No suggestions generated. Please try again or check your LLM configuration."
                },
                status=500,
            )

        suggestion = suggestions[0]  # Take first suggestion

        # Render result partial
        context = {
            "suggestion": suggestion,
            "chapter": chapter,
            "action": action,
            "agent": chapter_agent,
            "success": True,
        }

        return render(request, "bfagent/partials/chapter_action_result.html", context)

    except Exception as e:
        # Error handling
        context = {
            "error": str(e),
            "chapter": chapter,
            "action": action,
            "agent": chapter_agent,
            "success": False,
        }

        return render(request, "bfagent/partials/chapter_action_result.html", context)


@require_http_methods(["GET", "POST"])
def chapter_form_view(request, pk=None):
    """Enhanced Chapter form with CRUDConfig integration

    PHASE 2: Integrates HTMX + CRUDConfig + Chapter Writing System
    """
    from django.forms import ModelForm

    from ..models import BookChapters

    # Get chapter if editing
    chapter = None
    if pk:
        chapter = get_object_or_404(BookChapters, pk=pk)

    # Create dynamic form based on CRUDConfig
    class ChapterForm(ModelForm):
        class Meta:
            model = BookChapters
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            # Apply CRUDConfig form customizations
            if hasattr(BookChapters, "CRUDConfig"):
                crud_config = BookChapters.CRUDConfig()

                # Apply field customizations based on CRUDConfig
                for field_name, field in self.fields.items():
                    # Add Bootstrap classes
                    field.widget.attrs.update({"class": "form-control"})

                    # Special handling for different field types
                    if field_name in ["content", "summary", "outline"]:
                        field.widget.attrs.update(
                            {"class": "form-control", "rows": 10 if field_name == "content" else 5}
                        )
                    elif field_name in ["character_arcs", "metadata"]:
                        field.widget.attrs.update({"class": "form-control", "rows": 6})

    if request.method == "POST":
        form = ChapterForm(request.POST, instance=chapter)

        if form.is_valid():
            chapter = form.save()

            # HTMX Success - Return updated chapter list
            if request.htmx:
                chapters = (
                    BookChapters.objects.filter(project=chapter.project)
                    .select_related("story_arc", "project")
                    .prefetch_related("plot_points", "featured_characters")
                )

                context = {"chapters": chapters, "project": chapter.project}
                return render(request, "bfagent/partials/chapter_list.html", context)
            else:
                # Non-HTMX redirect
                from django.shortcuts import redirect

                return redirect("bfagent:chapter-detail", pk=chapter.pk)
        else:
            # HTMX Error - Return 422 with form
            if request.htmx:
                context = {
                    "form": form,
                    "chapter": chapter,
                    "crud_config": (
                        BookChapters.CRUDConfig() if hasattr(BookChapters, "CRUDConfig") else None
                    ),
                    "title": f"Edit {chapter.title}" if chapter else "Create Chapter",
                }
                response = render(request, "bfagent/partials/chapter_form.html", context)
                response.status_code = 422
                return response
    else:
        # GET request
        form = ChapterForm(instance=chapter)

    # Render form
    context = {
        "form": form,
        "chapter": chapter,
        "crud_config": BookChapters.CRUDConfig() if hasattr(BookChapters, "CRUDConfig") else None,
        "title": f"Edit {chapter.title}" if chapter else "Create Chapter",
    }

    if request.htmx:
        return render(request, "bfagent/partials/chapter_form.html", context)
    else:
        return render(request, "bfagent/chapter_form.html", context)
