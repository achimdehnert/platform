"""UI Hub views."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import GuardrailCategory, GuardrailRule, HTMXPattern, RuleViolation, ValidationSession
from .services import HTMXPatternService, ScaffolderService, ValidationService


@login_required
def dashboard_view(request):
    """UI Hub dashboard."""
    stats = {
        "total_categories": GuardrailCategory.objects.filter(is_active=True).count(),
        "total_rules": GuardrailRule.objects.filter(is_active=True).count(),
        "total_patterns": HTMXPattern.objects.filter(is_active=True).count(),
        "unresolved_violations": RuleViolation.objects.filter(is_resolved=False).count(),
    }
    context = {"stats": stats}

    return render(request, "ui_hub/dashboard.html", context)


@login_required
def rules_list_view(request):
    """List all guardrail rules."""
    category_filter = request.GET.get("category")

    rules = GuardrailRule.objects.select_related("category").filter(is_active=True)

    if category_filter:
        rules = rules.filter(category__code=category_filter)

    return render(
        request,
        "ui_hub/rules_list.html",
        {
            "rules": rules,
            "category_filter": category_filter,
        },
    )


@login_required
def violations_list_view(request):
    """List rule violations."""
    resolved_filter = request.GET.get("resolved", "false")
    severity_filter = request.GET.get("severity")

    violations = RuleViolation.objects.select_related("rule").order_by("-created_at")[:100]

    if resolved_filter == "false":
        violations = violations.filter(is_resolved=False)
    elif resolved_filter == "true":
        violations = violations.filter(is_resolved=True)

    if severity_filter:
        violations = violations.filter(severity=severity_filter)

    stats = {
        "total": RuleViolation.objects.count(),
        "errors": RuleViolation.objects.filter(severity="error").count(),
        "warnings": RuleViolation.objects.filter(severity="warning").count(),
        "resolved": RuleViolation.objects.filter(is_resolved=True).count(),
        "unresolved": RuleViolation.objects.filter(is_resolved=False).count(),
    }

    return render(
        request,
        "ui_hub/violations_list.html",
        {
            "violations": violations,
            "stats": stats,
            "resolved_filter": resolved_filter,
            "severity_filter": severity_filter,
        },
    )


@login_required
@require_http_methods(["POST"])
def validate_name_api(request):
    """API endpoint to validate a name."""
    name = request.POST.get("name", "")
    category = request.POST.get("category", "views")

    validator = ValidationService()
    result = validator.validate_name(name, category)

    return JsonResponse(result)


@login_required
@require_http_methods(["POST"])
def suggest_name_api(request):
    """API endpoint to suggest a name."""
    entity = request.POST.get("entity", "")
    action = request.POST.get("action", "")
    category = request.POST.get("category", "views")

    validator = ValidationService()
    suggestion = validator.suggest_name(entity, action, category)

    return JsonResponse(
        {
            "suggestion": suggestion,
            "entity": entity,
            "action": action,
            "category": category,
        }
    )


@login_required
@require_http_methods(["POST"])
def scaffold_view_api(request):
    """API endpoint to scaffold a view."""
    entity = request.POST.get("entity", "")
    action = request.POST.get("action", "list")
    app = request.POST.get("app", "")
    with_htmx = request.POST.get("with_htmx", "true") == "true"

    if not entity or not app:
        return JsonResponse({"error": "Entity and app are required"}, status=400)

    scaffolder = ScaffolderService()
    result = scaffolder.scaffold_view(entity, action, app, with_htmx)

    return JsonResponse(result)


@login_required
def patterns_list_view(request):
    """List HTMX patterns."""
    patterns = HTMXPattern.objects.filter(is_active=True)

    return render(
        request,
        "ui_hub/patterns_list.html",
        {
            "patterns": patterns,
        },
    )


@login_required
def pattern_detail_view(request, pk):
    """View HTMX pattern details."""
    pattern = get_object_or_404(HTMXPattern, pk=pk)

    return render(
        request,
        "ui_hub/pattern_detail.html",
        {
            "pattern": pattern,
        },
    )


@login_required
@require_http_methods(["POST"])
def violation_resolve_api(request, pk):
    """Resolve a violation."""
    violation = get_object_or_404(RuleViolation, pk=pk)
    note = request.POST.get("note", "")

    violation.resolve(note)

    if request.htmx:
        return render(
            request,
            "ui_hub/partials/_violation_row.html",
            {
                "violation": violation,
            },
        )

    return redirect("ui_hub:violations-list")
