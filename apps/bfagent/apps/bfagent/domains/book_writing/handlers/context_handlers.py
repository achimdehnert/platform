"""
Context Extraction Handlers - Book Writing Domain
Extract context from various project sources
"""
from typing import Dict, Any
import logging

from apps.bfagent.models import BookProjects, BookChapters

logger = logging.getLogger(__name__)


class ProjectContextExtractorHandler:
    """
    Extract basic context from project data
    
    Input:
    - project_id: int
    
    Output:
    - project_context: dict with title, genre, description
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract project context"""
        project_id = data.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Project not found'}
        
        context = {
            'title': project.title or 'Untitled',
            'genre': project.genre or 'Fiction',
            'description': project.description or '',
            'target_audience': getattr(project, 'target_audience', ''),
            'writing_status': getattr(project, 'writing_status', ''),
        }
        
        logger.info(f"Extracted context from project {project_id}")
        
        return {
            'success': True,
            'project_context': context
        }


class OutlineContextExtractorHandler:
    """
    Extract outline/beats from project chapters
    
    Input:
    - project_id: int
    - max_chapters: int (optional, default 5)
    
    Output:
    - outline_context: dict with chapters outline
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract outline from chapters"""
        project_id = data.get('project_id')
        max_chapters = data.get('max_chapters', 5)
        
        if not project_id:
            return {'success': False, 'error': 'project_id required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Project not found'}
        
        # Get chapters with outline
        chapters = BookChapters.objects.filter(
            project=project
        ).exclude(
            outline__isnull=True
        ).exclude(
            outline=''
        ).order_by('chapter_number')[:max_chapters]
        
        if not chapters.exists():
            return {
                'success': True,
                'outline_context': {
                    'has_outline': False,
                    'chapters': [],
                    'formatted': 'No outline available'
                }
            }
        
        # Format chapters
        chapter_list = []
        formatted_parts = []
        
        for chapter in chapters:
            chapter_data = {
                'number': chapter.chapter_number,
                'title': chapter.title,
                'outline': chapter.outline
            }
            chapter_list.append(chapter_data)
            
            formatted_parts.append(
                f"Chapter {chapter.chapter_number}: {chapter.title}\n"
                f"Outline: {chapter.outline}"
            )
        
        context = {
            'has_outline': True,
            'chapter_count': len(chapter_list),
            'chapters': chapter_list,
            'formatted': '\n\n'.join(formatted_parts)
        }
        
        logger.info(f"Extracted outline with {len(chapter_list)} chapters from project {project_id}")
        
        return {
            'success': True,
            'outline_context': context
        }
