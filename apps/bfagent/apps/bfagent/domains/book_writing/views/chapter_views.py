"""
Chapter Generation Views - Book Writing Domain
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.bfagent.models import BookProjects, BookChapters
from ..handlers.essay_handlers import (
    EssayIntroductionHandler,
    EssayBodyHandler,
    EssayConclusionHandler
)
from ..handlers.story_handlers import UniversalStoryChapterHandler

import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def generate_chapter(request, project_id, chapter_id):
    """
    Generate content for a single chapter using AI
    
    Works with Essay BookType using essay handlers
    """
    try:
        # Get project and chapter
        project = get_object_or_404(
            BookProjects,
            id=project_id,
            user=request.user
        )
        
        chapter = get_object_or_404(
            BookChapters,
            id=chapter_id,
            project=project
        )
        
        # Determine handler based on book type and chapter number
        book_type_name = project.book_type.name if project.book_type else 'Story'
        
        # Use Essay handlers for Essay books with chapters 1-3
        if book_type_name == 'Essay' and chapter.chapter_number <= 3:
            # Essay-specific logic
            keywords = project.genre or 'allgemeine Themen'
            thesis = project.description or 'Eine wichtige These'
            
            handler_map = {
                1: EssayIntroductionHandler,
                2: EssayBodyHandler,
                3: EssayConclusionHandler
            }
            
            handler_class = handler_map.get(chapter.chapter_number)
            
            if not handler_class:
                return JsonResponse({
                    'success': False,
                    'error': f'Kein Handler für Essay Chapter {chapter.chapter_number} gefunden'
                }, status=400)
            
            handler_data = {
                'keywords': keywords,
                'thesis': thesis
            }
            
            # Add previous content for Body and Conclusion
            if chapter.chapter_number == 2:
                intro_chapter = project.chapters.filter(chapter_number=1).first()
                if intro_chapter and intro_chapter.content:
                    handler_data['introduction'] = intro_chapter.content
            
            elif chapter.chapter_number == 3:
                intro_chapter = project.chapters.filter(chapter_number=1).first()
                body_chapter = project.chapters.filter(chapter_number=2).first()
                
                if intro_chapter and intro_chapter.content:
                    handler_data['introduction'] = intro_chapter.content
                if body_chapter and body_chapter.content:
                    handler_data['body'] = body_chapter.content
            
            logger.info(f"Generating Essay chapter {chapter.chapter_number} for project {project.id}")
            result = handler_class.handle(handler_data)
            
            if not result.get('success'):
                return JsonResponse({
                    'success': False,
                    'error': 'Handler konnte keinen Content generieren'
                }, status=500)
            
            content_key_map = {
                1: 'introduction',
                2: 'body',
                3: 'conclusion'
            }
            
            content_key = content_key_map.get(chapter.chapter_number)
            generated_content = result.get(content_key, '')
        
        else:
            # Use Universal Story Handler for all other books/chapters
            # Get previous chapters for context
            previous_chapters = []
            prev_chaps = project.chapters.filter(
                chapter_number__lt=chapter.chapter_number
            ).order_by('chapter_number')
            
            for prev_ch in prev_chaps:
                if prev_ch.content:
                    previous_chapters.append({
                        'title': prev_ch.title,
                        'content': prev_ch.content
                    })
            
            handler_data = {
                'chapter_number': chapter.chapter_number,
                'chapter_title': chapter.title,
                'chapter_outline': chapter.outline or '',
                'project_title': project.title,
                'project_genre': project.genre or 'Fiction',
                'project_description': project.description or '',
                'target_word_count': chapter.target_word_count,
                'previous_chapters': previous_chapters
            }
            
            logger.info(f"Generating Story chapter {chapter.chapter_number} for project {project.id}")
            result = UniversalStoryChapterHandler.handle(handler_data)
            
            if not result.get('success'):
                return JsonResponse({
                    'success': False,
                    'error': 'Handler konnte keinen Content generieren'
                }, status=500)
            
            generated_content = result.get('content', '')
        word_count = result.get('word_count', 0)
        
        # Update chapter
        chapter.content = generated_content
        chapter.word_count = word_count
        chapter.writing_stage = 'drafting'
        chapter.save()
        
        logger.info(f"Successfully generated {word_count} words for chapter {chapter.id}")
        
        return JsonResponse({
            'success': True,
            'chapter_id': chapter.id,
            'chapter_number': chapter.chapter_number,
            'title': chapter.title,
            'word_count': word_count,
            'target_word_count': chapter.target_word_count,
            'content_preview': generated_content[:200] + '...' if len(generated_content) > 200 else generated_content,
            'message': f'Chapter {chapter.chapter_number} erfolgreich generiert!'
        })
        
    except Exception as e:
        logger.error(f"Error generating chapter: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
