"""
Research Views - Science Writer Domain
Scientific research project management
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def research_list(request):
    """
    List all research projects

    URL: /research/
    """
    context = {
        'title': 'Research Projects',
        'projects': [],  # TODO: Query from DB
    }
    return render(request, 'science_writer/research_list.html', context)


@login_required
@require_http_methods(["GET"])
def research_create(request):
    """
    Create new research project

    7 Phases:
    1. Research Planning
    2. Literature Review
    3. Methodology Design
    4. Data Analysis
    5. Paper Writing
    6. Quality Assurance
    7. Finalization

    URL: /research/create/
    """
    context = {
        'title': 'New Research Project',
    }
    return render(request, 'science_writer/research_form.html', context)
