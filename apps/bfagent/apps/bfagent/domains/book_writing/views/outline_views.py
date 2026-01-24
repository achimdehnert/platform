"""
Outline Generation Views - Book Writing Domain
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.bfagent.models import BookProjects, BookChapters
from ..handlers.outline_handlers import SaveTheCatOutlineHandler

import logging

logger = logging.getLogger(__name__)


@login_required
def outline_generator(request, project_id):
    """
    Show outline generator page with framework selection
    """
    project = get_object_or_404(
        BookProjects,
        id=project_id,
        user=request.user
    )
    
    context = {
        'project': project,
        'frameworks': [
            {
                'id': 'save_the_cat',
                'name': 'Save the Cat',
                'description': '15-Beat Structure für packende Page-Turner',
                'chapters': 15
            },
            {
                'id': 'heros_journey',
                'name': "Hero's Journey",
                'description': '12-Stage Heldenreise nach Joseph Campbell',
                'chapters': 12
            },
            {
                'id': 'three_act',
                'name': 'Three-Act Structure',
                'description': 'Klassische 3-Akt-Struktur',
                'chapters': 10
            }
        ]
    }
    
    return render(request, 'bfagent/outline_generator.html', context)


@login_required
@require_http_methods(["POST"])
def generate_outline(request, project_id):
    """
    Generate outline using selected framework
    
    POST data:
    - framework: str ('save_the_cat', 'heros_journey', 'three_act')
    - num_chapters: int (optional)
    - create_chapters: bool (optional, default False)
    """
    try:
        project = get_object_or_404(
            BookProjects,
            id=project_id,
            user=request.user
        )
        
        # Get parameters
        framework = request.POST.get('framework', 'save_the_cat')
        num_chapters = int(request.POST.get('num_chapters', 15))
        create_chapters = request.POST.get('create_chapters', 'false').lower() == 'true'
        
        # Select handler
        handler_map = {
            'save_the_cat': SaveTheCatOutlineHandler,
        }
        
        handler_class = handler_map.get(framework)
        
        if not handler_class:
            return JsonResponse({
                'success': False,
                'error': f'Framework "{framework}" not yet implemented'
            }, status=400)
        
        # Prepare handler input
        handler_data = {
            'title': project.title,
            'genre': project.genre or 'General Fiction',
            'description': project.description or '',
            'num_chapters': num_chapters
        }
        
        # Call handler
        logger.info(f"Generating {framework} outline for project {project.id}")
        result = handler_class.handle(handler_data)
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Could not generate outline')
            }, status=500)
        
        # Save outline to project
        project.story_premise = result['outline']
        project.save()
        
        # Optional: Create chapters based on beats
        if create_chapters:
            beats = result.get('beats', [])
            for beat_info in beats:
                # Check if chapter already exists
                chapter_num = beat_info['chapter']
                existing = BookChapters.objects.filter(
                    project=project,
                    chapter_number=chapter_num
                ).first()
                
                if not existing:
                    BookChapters.objects.create(
                        project=project,
                        chapter_number=chapter_num,
                        title=beat_info['beat_name'],
                        outline=beat_info['description'],
                        target_word_count=project.target_word_count // num_chapters if project.target_word_count else 1000,
                        writing_stage='planning',
                        status='draft'
                    )
            
            logger.info(f"Created {len(beats)} chapters for project {project.id}")
        
        return JsonResponse({
            'success': True,
            'outline': result['outline'],
            'beats': result.get('beats', []),
            'chapter_count': result['chapter_count'],
            'framework': result['framework'],
            'chapters_created': create_chapters,
            'message': f'{framework.replace("_", " ").title()} Outline erfolgreich generiert!'
        })
        
    except Exception as e:
        logger.error(f"Error generating outline: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
