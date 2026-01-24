"""
Outline Generator Views
========================

Views for the dynamic outline generator.
"""

import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from ..services.outline_generator import get_outline_generator, OutlineSection

logger = logging.getLogger(__name__)


def outline_generator_view(request):
    """Main outline generator page."""
    return render(request, 'research/outline_generator.html')


@require_http_methods(["POST"])
def generate_outline_view(request):
    """Generate outline via HTMX."""
    try:
        # Get form data
        project_type = request.POST.get('project_type', 'book')
        title = request.POST.get('title', 'Untitled')
        framework = request.POST.get('framework', '')
        genre = request.POST.get('genre', '')
        research_question = request.POST.get('research_question', '')
        word_count = int(request.POST.get('word_count', 80000))
        use_ai = request.POST.get('use_ai') == 'on'
        
        # Build context
        context = {}
        if genre:
            context['genre'] = genre
        if research_question:
            context['research_question'] = research_question
        if request.POST.get('protagonist'):
            context['protagonist'] = request.POST.get('protagonist')
        if request.POST.get('setting'):
            context['setting'] = request.POST.get('setting')
        if request.POST.get('theme'):
            context['theme'] = request.POST.get('theme')
        
        # Build constraints
        constraints = {'word_count': word_count}
        
        # Determine rules to apply
        rules = []
        if genre:
            rules.append(genre)
        
        # Generate outline
        generator = get_outline_generator()
        outline = generator.generate_sync(
            project_type=project_type,
            title=title,
            framework=framework if framework else None,
            context=context,
            constraints=constraints,
            rules=rules,
            use_ai=use_ai
        )
        
        # Render result
        return render(request, 'research/partials/outline_result.html', {
            'outline': outline,
            'outline_json': json.dumps(outline.to_dict())
        })
        
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        return render(request, 'research/partials/outline_error.html', {
            'error': str(e)
        })


@require_http_methods(["POST"])
def export_outline_view(request):
    """Export outline to format."""
    try:
        data = json.loads(request.body)
        outline_data = data.get('outline', {})
        export_format = data.get('format', 'markdown')
        
        # Reconstruct outline
        from ..services.outline_generator import GeneratedOutline
        
        sections = [OutlineSection(**s) for s in outline_data.get('sections', [])]
        outline = GeneratedOutline(
            sections=sections,
            **{k: v for k, v in outline_data.items() if k != 'sections'}
        )
        
        if export_format == 'markdown':
            content = outline.to_markdown()
        elif export_format == 'json':
            content = json.dumps(outline.to_dict(), indent=2)
        else:
            content = outline.to_markdown()
        
        return JsonResponse({
            'success': True,
            'content': content,
            'format': export_format
        })
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def list_frameworks_view(request):
    """List available frameworks."""
    try:
        from ..services.paper_frameworks import list_paper_frameworks
        from apps.bfagent.services.story_frameworks import list_frameworks
        
        project_type = request.GET.get('type', 'all')
        
        frameworks = []
        
        if project_type in ['book', 'all']:
            story_fws = list_frameworks()
            for fw in story_fws:
                fw['category'] = 'creative_writing'
            frameworks.extend(story_fws)
        
        if project_type in ['paper', 'all']:
            paper_fws = list_paper_frameworks()
            for fw in paper_fws:
                fw['category'] = 'scientific_writing'
            frameworks.extend(paper_fws)
        
        return JsonResponse({
            'success': True,
            'frameworks': frameworks
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
