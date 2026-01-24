"""
MCP Book Writing Tools Implementation
=====================================

Actual implementation of book-writing MCP tools that connect to the
workflow orchestrator and handlers.
"""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds, BookTypes
from apps.bfagent.domains.book_writing.handlers.workflow_orchestrator import (
    BookWorkflowOrchestrator,
    WorkflowPhase
)
from apps.bfagent.domains.book_writing.handlers.outline_handlers import (
    SaveTheCatOutlineHandler,
    HerosJourneyOutlineHandler,
    ThreeActOutlineHandler,
    OutlineContextExtractorHandler
)
from apps.bfagent.domains.book_writing.handlers.character_handlers import (
    CharacterCastGeneratorHandler
)
from apps.bfagent.domains.book_writing.handlers.world_handlers import (
    WorldGeneratorHandler,
    WorldCreatorHandler
)
from apps.bfagent.domains.book_writing.handlers.story_handlers import (
    UniversalStoryChapterHandler
)
from apps.bfagent.domains.book_writing.services.context_builder import ContextBuilder
from apps.writing_hub.handlers.concept_handlers import (
    PremiseGeneratorHandler,
    ThemeIdentifierHandler,
    LoglineGeneratorHandler
)

logger = logging.getLogger(__name__)


class BookMCPTools:
    """
    Implementation of all book-writing MCP tools.
    Each method corresponds to a tool in the MCP registry.
    """
    
    # =========================================================================
    # PROJECT MANAGEMENT
    # =========================================================================
    
    @staticmethod
    def book_create_project(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new book project"""
        title = params.get('title')
        genre = params.get('genre')
        book_type_name = params.get('book_type', 'novel')
        description = params.get('description', '')
        
        if not title or not genre:
            return {'success': False, 'error': 'title and genre are required'}
        
        try:
            # Get book type (optional)
            book_type = None
            try:
                book_type = BookTypes.objects.filter(name__icontains=book_type_name).first()
                if not book_type:
                    book_type = BookTypes.objects.first()
            except Exception:
                pass  # BookTypes may not exist
            
            # Create project - handle required fields
            from django.db import connection
            
            # Check if book_type field allows null
            project_data = {
                'title': title,
                'genre': genre,
                'description': description,
                'status': 'planning',
                'content_rating': 'General',
                'target_word_count': 50000,
            }
            
            # Try to add book_type if available and required
            if book_type:
                project_data['book_type'] = book_type
            else:
                # Create a default book type if none exists
                book_type, _ = BookTypes.objects.get_or_create(
                    name='Novel',
                    defaults={
                        'description': 'Standard novel format',
                        'complexity': 'medium'
                    }
                )
                project_data['book_type'] = book_type
            
            project = BookProjects.objects.create(**project_data)
            
            return {
                'success': True,
                'project_id': project.id,
                'title': project.title,
                'genre': project.genre,
                'message': f"Project '{title}' created successfully"
            }
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_get_project(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get project details"""
        project_id = params.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            
            # Get related data
            characters = list(Characters.objects.filter(project=project).values(
                'id', 'name', 'role', 'description'
            ))
            chapters = list(BookChapters.objects.filter(project=project).values(
                'id', 'chapter_number', 'title', 'word_count', 'status'
            ))
            worlds = list(Worlds.objects.filter(project=project).values(
                'id', 'name', 'world_type', 'description'
            ))
            
            return {
                'success': True,
                'project': {
                    'id': project.id,
                    'title': project.title,
                    'genre': project.genre,
                    'description': project.description,
                    'status': project.status,
                    'book_type': project.book_type.name if project.book_type else None,
                    'target_word_count': project.target_word_count,
                    'current_word_count': project.current_word_count,
                },
                'characters': characters,
                'chapters': chapters,
                'worlds': worlds,
                'stats': {
                    'character_count': len(characters),
                    'chapter_count': len(chapters),
                    'world_count': len(worlds),
                }
            }
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_list_projects(params: Dict[str, Any]) -> Dict[str, Any]:
        """List all projects"""
        genre = params.get('genre')
        status = params.get('status')
        limit = params.get('limit', 20)
        
        try:
            queryset = BookProjects.objects.all()
            
            if genre:
                queryset = queryset.filter(genre__icontains=genre)
            if status:
                queryset = queryset.filter(status=status)
            
            projects = list(queryset[:limit].values(
                'id', 'title', 'genre', 'status', 'created_at'
            ))
            
            return {
                'success': True,
                'projects': projects,
                'total': len(projects)
            }
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # PLANNING PHASE
    # =========================================================================
    
    @staticmethod
    def book_generate_premise(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate story premise using AI"""
        project_id = params.get('project_id')
        inspiration = params.get('inspiration', '')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            result = PremiseGeneratorHandler.handle({
                'project_id': project_id,
                'inspiration': inspiration
            })
            return result
        except Exception as e:
            logger.error(f"Error generating premise: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_identify_themes(params: Dict[str, Any]) -> Dict[str, Any]:
        """Identify story themes"""
        project_id = params.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            result = ThemeIdentifierHandler.handle({
                'project_id': project_id
            })
            return result
        except Exception as e:
            logger.error(f"Error identifying themes: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_generate_logline(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate logline"""
        project_id = params.get('project_id')
        style = params.get('style', 'concise')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            result = LoglineGeneratorHandler.handle({
                'project_id': project_id,
                'style': style
            })
            return result
        except Exception as e:
            logger.error(f"Error generating logline: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # CHARACTERS PHASE
    # =========================================================================
    
    @staticmethod
    def book_generate_characters(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate character cast using AI"""
        project_id = params.get('project_id')
        character_count = params.get('character_count', 5)
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            project_context = ContextBuilder.build_project_context(project)
            
            result = CharacterCastGeneratorHandler.handle({
                'project_context': project_context,
                'outline_context': {},
                'character_count': character_count
            })
            
            # Save characters if successful
            if result.get('success') and result.get('characters'):
                saved = 0
                for char_data in result['characters']:
                    try:
                        Characters.objects.create(
                            project=project,
                            name=char_data.get('name', 'Unnamed'),
                            role=char_data.get('role', 'supporting'),
                            description=char_data.get('description', ''),
                        )
                        saved += 1
                    except Exception as e:
                        logger.warning(f"Could not save character: {e}")
                
                result['saved_count'] = saved
            
            return result
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error generating characters: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_create_character(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a character manually"""
        project_id = params.get('project_id')
        name = params.get('name')
        role = params.get('role')
        description = params.get('description', '')
        
        if not project_id or not name or not role:
            return {'success': False, 'error': 'project_id, name, and role are required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            
            character = Characters.objects.create(
                project=project,
                name=name,
                role=role,
                description=description
            )
            
            return {
                'success': True,
                'character_id': character.id,
                'name': character.name,
                'role': character.role
            }
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error creating character: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_list_characters(params: Dict[str, Any]) -> Dict[str, Any]:
        """List all characters in a project"""
        project_id = params.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            characters = list(Characters.objects.filter(
                project_id=project_id
            ).values('id', 'name', 'role', 'description', 'age', 'personality'))
            
            return {
                'success': True,
                'characters': characters,
                'total': len(characters)
            }
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # WORLD BUILDING PHASE
    # =========================================================================
    
    @staticmethod
    def book_generate_world(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate world using AI"""
        project_id = params.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            project_context = ContextBuilder.build_project_context(project)
            
            result = WorldGeneratorHandler.handle({
                'project_context': project_context,
                'outline_context': {}
            })
            
            # Save world if successful
            if result.get('success') and result.get('world'):
                create_result = WorldCreatorHandler.handle({
                    'project_id': project_id,
                    'world': result['world']
                })
                if create_result.get('success'):
                    result['world_id'] = create_result.get('world_id')
            
            return result
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error generating world: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_create_world(params: Dict[str, Any]) -> Dict[str, Any]:
        """Create world manually"""
        project_id = params.get('project_id')
        name = params.get('name')
        world_type = params.get('world_type', 'primary')
        geography = params.get('geography', '')
        culture = params.get('culture', '')
        
        if not project_id or not name:
            return {'success': False, 'error': 'project_id and name are required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            
            world = Worlds.objects.create(
                project=project,
                name=name,
                world_type=world_type,
                geography=geography,
                culture=culture
            )
            
            return {
                'success': True,
                'world_id': world.id,
                'name': world.name
            }
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error creating world: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # OUTLINE PHASE
    # =========================================================================
    
    @staticmethod
    def book_generate_outline(params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate story outline"""
        project_id = params.get('project_id')
        framework = params.get('framework', 'save_the_cat')
        num_chapters = params.get('num_chapters', 12)
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            
            # Select handler based on framework
            handlers = {
                'save_the_cat': SaveTheCatOutlineHandler,
                'heros_journey': HerosJourneyOutlineHandler,
                'three_act': ThreeActOutlineHandler,
            }
            
            handler = handlers.get(framework, SaveTheCatOutlineHandler)
            
            result = handler.handle({
                'title': project.title,
                'genre': project.genre,
                'description': project.description or project.story_premise or '',
                'num_chapters': num_chapters
            })
            
            # Create chapters in database
            if result.get('success') and result.get('chapters'):
                created = 0
                for ch in result['chapters']:
                    try:
                        BookChapters.objects.create(
                            project=project,
                            chapter_number=ch.get('number', created + 1),
                            title=ch.get('title', f'Chapter {created + 1}'),
                            outline=ch.get('outline', ch.get('beat', '')),
                            target_word_count=ch.get('target_words', 2000),
                            status='draft'
                        )
                        created += 1
                    except Exception as e:
                        logger.warning(f"Could not create chapter: {e}")
                
                result['chapters_created'] = created
            
            return result
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error generating outline: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_get_outline(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current outline"""
        project_id = params.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            outline_context = ContextBuilder.build_outline_context(project)
            
            return {
                'success': True,
                **outline_context
            }
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error getting outline: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # CHAPTER WRITING PHASE
    # =========================================================================
    
    @staticmethod
    def book_write_chapter(params: Dict[str, Any]) -> Dict[str, Any]:
        """Write a specific chapter"""
        project_id = params.get('project_id')
        chapter_number = params.get('chapter_number')
        use_ai = params.get('use_ai', True)
        
        if not project_id or not chapter_number:
            return {'success': False, 'error': 'project_id and chapter_number are required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            chapter = BookChapters.objects.get(
                project=project,
                chapter_number=chapter_number
            )
            
            # Get previous chapters for context
            previous_chapters = list(BookChapters.objects.filter(
                project=project,
                chapter_number__lt=chapter_number
            ).order_by('chapter_number').values('title', 'content', 'outline'))
            
            result = UniversalStoryChapterHandler.handle({
                'chapter_number': chapter_number,
                'chapter_title': chapter.title,
                'chapter_outline': chapter.outline or '',
                'project_id': project_id,
                'project_title': project.title,
                'project_genre': project.genre,
                'project_description': project.description or '',
                'target_word_count': chapter.target_word_count or 2000,
                'previous_chapters': previous_chapters[-3:]  # Last 3
            }, {'use_llm': use_ai})
            
            # Update chapter if successful
            if result.get('success'):
                chapter.content = result.get('content', '')
                chapter.word_count = result.get('word_count', 0)
                chapter.save()
            
            return result
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except BookChapters.DoesNotExist:
            return {'success': False, 'error': f'Chapter {chapter_number} not found'}
        except Exception as e:
            logger.error(f"Error writing chapter: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_write_all_chapters(params: Dict[str, Any]) -> Dict[str, Any]:
        """Write all chapters sequentially"""
        project_id = params.get('project_id')
        use_ai = params.get('use_ai', True)
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            chapters = BookChapters.objects.filter(
                project_id=project_id
            ).order_by('chapter_number')
            
            results = []
            for chapter in chapters:
                result = BookMCPTools.book_write_chapter({
                    'project_id': project_id,
                    'chapter_number': chapter.chapter_number,
                    'use_ai': use_ai
                })
                results.append({
                    'chapter_number': chapter.chapter_number,
                    'success': result.get('success', False),
                    'word_count': result.get('word_count', 0)
                })
            
            return {
                'success': True,
                'chapters': results,
                'total': len(results),
                'successful': sum(1 for r in results if r['success'])
            }
        except Exception as e:
            logger.error(f"Error writing all chapters: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_get_chapter(params: Dict[str, Any]) -> Dict[str, Any]:
        """Get chapter content"""
        project_id = params.get('project_id')
        chapter_number = params.get('chapter_number')
        
        if not project_id or not chapter_number:
            return {'success': False, 'error': 'project_id and chapter_number are required'}
        
        try:
            chapter = BookChapters.objects.get(
                project_id=project_id,
                chapter_number=chapter_number
            )
            
            return {
                'success': True,
                'chapter': {
                    'id': chapter.id,
                    'chapter_number': chapter.chapter_number,
                    'title': chapter.title,
                    'outline': chapter.outline,
                    'content': chapter.content,
                    'word_count': chapter.word_count,
                    'status': chapter.status,
                }
            }
        except BookChapters.DoesNotExist:
            return {'success': False, 'error': f'Chapter {chapter_number} not found'}
        except Exception as e:
            logger.error(f"Error getting chapter: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # FULL WORKFLOW
    # =========================================================================
    
    @staticmethod
    def book_run_workflow(params: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete book writing workflow"""
        project_id = params.get('project_id')
        use_ai = params.get('use_ai', False)
        skip_phases = params.get('skip_phases', [])
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            orchestrator = BookWorkflowOrchestrator(
                project_id=project_id,
                use_ai=use_ai
            )
            
            result = orchestrator.run_full_workflow(skip_phases=skip_phases)
            return result
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def book_run_phase(params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific workflow phase"""
        project_id = params.get('project_id')
        phase = params.get('phase')
        use_ai = params.get('use_ai', False)
        
        if not project_id or not phase:
            return {'success': False, 'error': 'project_id and phase are required'}
        
        try:
            orchestrator = BookWorkflowOrchestrator(
                project_id=project_id,
                use_ai=use_ai
            )
            
            phase_handlers = {
                'planning': orchestrator.run_planning_phase,
                'characters': orchestrator.run_characters_phase,
                'world_building': orchestrator.run_world_building_phase,
                'outline': orchestrator.run_outline_phase,
                'chapters': orchestrator.run_chapters_phase,
            }
            
            handler = phase_handlers.get(phase)
            if not handler:
                return {
                    'success': False,
                    'error': f'Unknown phase: {phase}. Valid: {list(phase_handlers.keys())}'
                }
            
            result = handler()
            return {
                'success': result.success,
                'phase': phase,
                'data': result.data,
                'error': result.error,
                'cost': result.cost
            }
        except Exception as e:
            logger.error(f"Error running phase: {e}")
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # EXPORT
    # =========================================================================
    
    @staticmethod
    def book_export_manuscript(params: Dict[str, Any]) -> Dict[str, Any]:
        """Export book as manuscript"""
        project_id = params.get('project_id')
        format_type = params.get('format', 'markdown')
        
        if not project_id:
            return {'success': False, 'error': 'project_id is required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
            chapters = BookChapters.objects.filter(
                project=project
            ).order_by('chapter_number')
            
            if format_type == 'markdown':
                content = BookMCPTools._export_markdown(project, chapters)
            else:
                content = BookMCPTools._export_markdown(project, chapters)  # Default
            
            return {
                'success': True,
                'format': format_type,
                'content': content,
                'word_count': sum(c.word_count or 0 for c in chapters),
                'chapter_count': chapters.count()
            }
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        except Exception as e:
            logger.error(f"Error exporting manuscript: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _export_markdown(project, chapters):
        """Export as Markdown"""
        lines = [
            f"# {project.title}",
            "",
            f"**Genre:** {project.genre}",
            f"**Author:** [Your Name]",
            "",
            "---",
            ""
        ]
        
        if project.description:
            lines.extend([
                "## Synopsis",
                "",
                project.description,
                "",
                "---",
                ""
            ])
        
        for chapter in chapters:
            lines.extend([
                f"## Chapter {chapter.chapter_number}: {chapter.title}",
                "",
                chapter.content or "*Chapter content not yet written*",
                "",
                "---",
                ""
            ])
        
        return "\n".join(lines)


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

def execute_book_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a book-writing tool by name.
    
    Args:
        tool_name: Name of the tool (e.g., 'book_create_project')
        params: Tool parameters
        
    Returns:
        Tool execution result
    """
    tools = {
        'book_create_project': BookMCPTools.book_create_project,
        'book_get_project': BookMCPTools.book_get_project,
        'book_list_projects': BookMCPTools.book_list_projects,
        'book_generate_premise': BookMCPTools.book_generate_premise,
        'book_identify_themes': BookMCPTools.book_identify_themes,
        'book_generate_logline': BookMCPTools.book_generate_logline,
        'book_generate_characters': BookMCPTools.book_generate_characters,
        'book_create_character': BookMCPTools.book_create_character,
        'book_list_characters': BookMCPTools.book_list_characters,
        'book_generate_world': BookMCPTools.book_generate_world,
        'book_create_world': BookMCPTools.book_create_world,
        'book_generate_outline': BookMCPTools.book_generate_outline,
        'book_get_outline': BookMCPTools.book_get_outline,
        'book_write_chapter': BookMCPTools.book_write_chapter,
        'book_write_all_chapters': BookMCPTools.book_write_all_chapters,
        'book_get_chapter': BookMCPTools.book_get_chapter,
        'book_run_workflow': BookMCPTools.book_run_workflow,
        'book_run_phase': BookMCPTools.book_run_phase,
        'book_export_manuscript': BookMCPTools.book_export_manuscript,
    }
    
    tool_func = tools.get(tool_name)
    if not tool_func:
        return {
            'success': False,
            'error': f"Unknown tool: {tool_name}. Available: {list(tools.keys())}"
        }
    
    return tool_func(params)
