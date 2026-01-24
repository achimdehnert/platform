"""
Report Views - Expert Hub Domain
Expert reports and assessments (Gutachten)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def report_list(request):
    """
    List all expert reports

    URL: /reports/
    """
    context = {
        'title': 'Expert Reports',
        'reports': [],  # TODO: Query from DB
    }
    return render(request, 'expert_hub/report_list.html', context)


@login_required
@require_http_methods(["GET"])
def report_create(request):
    """
    Create new expert report

    Report Types:
    - Forensic Analysis
    - Insurance Assessment
    - Technical Expert Opinion
    - Damage Assessment

    URL: /reports/create/
    """
    context = {
        'title': 'New Expert Report',
    }
    return render(request, 'expert_hub/report_form.html', context)
