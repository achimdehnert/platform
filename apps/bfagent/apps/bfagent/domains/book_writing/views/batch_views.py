"""
Batch Generation Views - Book Writing Domain
Generate multiple chapters in sequence
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.bfagent.models import BookProjects, BookChapters

import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def generate_all_chapters(request, project_id):
    """
    Generate all chapters sequentially
    
    Returns count of generated chapters
    """
    try:
        project = get_object_or_404(
            BookProjects,
            id=project_id,
            user=request.user
        )
        
        # Get parameters
        regenerate_existing = request.POST.get('regenerate_existing', 'false').lower() == 'true'
        
        # Get all chapters without content
        if regenerate_existing:
            chapters = project.chapters.all().order_by('chapter_number')
        else:
            chapters = project.chapters.filter(content__isnull=True).order_by('chapter_number')
            # Also include chapters with empty content
            empty_chapters = project.chapters.filter(content='').order_by('chapter_number')
            chapters = (chapters | empty_chapters).distinct().order_by('chapter_number')
        
        chapters_list = list(chapters)
        
        if not chapters_list:
            return JsonResponse({
                'success': True,
                'chapters_generated': 0,
                'message': 'Alle Kapitel haben bereits Content'
            })
        
        # Return list of chapters to generate (frontend will handle sequential calls)
        chapter_ids = [ch.id for ch in chapters_list]
        
        return JsonResponse({
            'success': True,
            'chapter_ids': chapter_ids,
            'total_chapters': len(chapter_ids),
            'message': f'{len(chapter_ids)} Kapitel werden generiert'
        })
        
    except Exception as e:
        logger.error(f"Error in batch generation: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
