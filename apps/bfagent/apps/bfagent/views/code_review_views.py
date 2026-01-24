"""
Code Review Views

Web UI for Review Framework integration.
"""

from pathlib import Path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.bfagent.review.core import ReviewOrchestrator
from apps.bfagent.review.handlers import (
    SecurityReviewHandler,
    PerformanceReviewHandler,
    IllustrationReviewHandler,
)


@login_required
def code_review_dashboard(request):
    """Code review dashboard in control center"""
    
    # Predefined paths for quick access
    quick_paths = [
        {'name': 'Handlers', 'path': 'apps/bfagent/handlers/'},
        {'name': 'Views', 'path': 'apps/bfagent/views/'},
        {'name': 'Models', 'path': 'apps/bfagent/models.py'},
        {'name': 'Illustration System', 'path': 'apps/bfagent/views/illustration_*.py'},
        {'name': 'Templates', 'path': 'apps/bfagent/templates/'},
        {'name': 'Full App', 'path': 'apps/bfagent/'},
    ]
    
    context = {
        'quick_paths': quick_paths,
        'available_checks': [
            {'id': 'security', 'name': 'Security', 'icon': '🔒'},
            {'id': 'performance', 'name': 'Performance', 'icon': '⚡'},
            {'id': 'illustration', 'name': 'Illustration', 'icon': '🖼️'},
        ],
        'output_formats': [
            {'id': 'text', 'name': 'Text'},
            {'id': 'json', 'name': 'JSON'},
            {'id': 'markdown', 'name': 'Markdown'},
        ],
    }
    
    return render(request, 'bfagent/code_review/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def run_code_review(request):
    """Execute code review via AJAX"""
    
    # Get parameters
    target_path = request.POST.get('path', 'apps/bfagent/')
    enable_security = request.POST.get('security') == 'true'
    enable_performance = request.POST.get('performance') == 'true'
    enable_illustration = request.POST.get('illustration') == 'true'
    output_format = request.POST.get('format', 'text')
    
    # Default to all checks if none selected
    if not any([enable_security, enable_performance, enable_illustration]):
        enable_security = enable_performance = enable_illustration = True
    
    try:
        # Create orchestrator
        orchestrator = ReviewOrchestrator()
        
        # Register handlers
        if enable_security:
            orchestrator.register_review_handler(SecurityReviewHandler())
        if enable_performance:
            orchestrator.register_review_handler(PerformanceReviewHandler())
        if enable_illustration:
            orchestrator.register_review_handler(IllustrationReviewHandler())
        
        # Run review
        path = Path(target_path)
        if not path.exists():
            return JsonResponse({
                'success': False,
                'error': f'Path does not exist: {target_path}'
            })
        
        result = orchestrator.review(path)
        
        # Format output
        if output_format == 'json':
            output = result.to_dict()
        elif output_format == 'markdown':
            output = _format_markdown(result)
        else:
            output = _format_text(result)
        
        return JsonResponse({
            'success': True,
            'output': output,
            'stats': result.to_dict()['stats'],
            'duration': result.duration_seconds,
            'files_reviewed': result.files_reviewed,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def _format_text(result):
    """Format result as text"""
    lines = []
    
    for finding in result.findings:
        severity_icon = {
            'critical': '🔴',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'style': '💅',
        }.get(finding.severity.value, '•')
        
        lines.append(f"{severity_icon} [{finding.severity.value.upper()}] {finding.title}")
        lines.append(f"  📁 File: {finding.file_path}")
        if finding.line_number:
            lines.append(f"  📍 Line: {finding.line_number}")
        lines.append(f"  📝 {finding.description}")
        if finding.suggestion:
            lines.append(f"  💡 Suggestion: {finding.suggestion}")
        lines.append("")
    
    if not lines:
        lines.append("✅ No issues found!")
    
    return "\n".join(lines)


def _format_markdown(result):
    """Format result as markdown"""
    lines = [
        "# Code Review Report",
        "",
        f"**Duration:** {result.duration_seconds:.2f}s",
        f"**Files:** {result.files_reviewed}",
        f"**Findings:** {len(result.findings)}",
        "",
        "## Summary",
        ""
    ]
    
    stats = result.to_dict()['stats']
    for severity in ['critical', 'error', 'warning', 'info', 'style']:
        count = stats[severity]
        if count > 0:
            lines.append(f"- **{severity.upper()}:** {count}")
    
    if result.findings:
        lines.extend(["", "## Findings", ""])
        
        for finding in result.findings:
            lines.append(f"### {finding.title}")
            lines.append(f"- **Severity:** `{finding.severity.value}`")
            lines.append(f"- **File:** `{finding.file_path}`")
            if finding.line_number:
                lines.append(f"- **Line:** {finding.line_number}")
            lines.append(f"- **Description:** {finding.description}")
            if finding.suggestion:
                lines.append(f"- **Fix:** {finding.suggestion}")
            lines.append("")
    
    return "\n".join(lines)


@login_required
def project_code_review(request, project_id):
    """Code review for specific project"""
    from apps.bfagent.models import BookProjects
    
    project = BookProjects.objects.get(pk=project_id, user=request.user)
    
    # Paths relevant to this project
    project_paths = [
        {'name': 'Project Models', 'path': f'apps/bfagent/models.py'},
        {'name': 'Project Views', 'path': f'apps/bfagent/views/'},
        {'name': 'Project Handlers', 'path': f'apps/bfagent/handlers/'},
    ]
    
    context = {
        'project': project,
        'project_paths': project_paths,
        'available_checks': [
            {'id': 'security', 'name': 'Security', 'icon': '🔒'},
            {'id': 'performance', 'name': 'Performance', 'icon': '⚡'},
        ],
    }
    
    return render(request, 'bfagent/code_review/project_review.html', context)
