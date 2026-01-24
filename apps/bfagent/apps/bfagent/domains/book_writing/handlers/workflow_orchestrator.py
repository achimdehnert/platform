"""
Book Writing Workflow Orchestrator
Coordinates all phases of book creation with proper context propagation
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from django.conf import settings
from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds
from ..services.llm_service import LLMService
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class WorkflowPhase(Enum):
    """Book writing workflow phases"""
    PLANNING = "planning"
    CHARACTERS = "characters"
    WORLD_BUILDING = "world_building"
    OUTLINE = "outline"
    CHAPTERS = "chapters"
    REVIEW = "review"
    EXPORT = "export"


@dataclass
class PhaseResult:
    """Result from a workflow phase"""
    phase: WorkflowPhase
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    usage: Optional[Dict] = None
    cost: float = 0.0


@dataclass
class WorkflowContext:
    """Accumulated context across all phases"""
    project_id: int
    project_context: Dict = field(default_factory=dict)
    premise: str = ""
    themes: List[str] = field(default_factory=list)
    logline: str = ""
    characters: List[Dict] = field(default_factory=list)
    world: Dict = field(default_factory=dict)
    outline: Dict = field(default_factory=dict)
    chapters: List[Dict] = field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0


class BookWorkflowOrchestrator:
    """
    Orchestrates the complete book writing workflow.
    
    Phases:
    1. Planning - Generate premise, themes, logline
    2. Characters - Generate character cast
    3. World Building - Create world setting
    4. Outline - Generate story structure and chapter outlines
    5. Chapters - Write all chapters with context
    6. Review - Quality check and editing suggestions
    7. Export - Generate final output
    """
    
    def __init__(self, project_id: int, use_ai: bool = True):
        self.project_id = project_id
        self.use_ai = use_ai
        self.context = WorkflowContext(project_id=project_id)
        self.project = None
        self.llm = None
        
        self._load_project()
        self._init_llm()
    
    def _load_project(self):
        """Load project from database"""
        try:
            self.project = BookProjects.objects.get(id=self.project_id)
            self.context.project_context = ContextBuilder.build_project_context(self.project)
            logger.info(f"Loaded project: {self.project.title}")
        except BookProjects.DoesNotExist:
            raise ValueError(f"Project {self.project_id} not found")
    
    def _init_llm(self):
        """Initialize LLM service"""
        if self.use_ai:
            api_key_available = (
                getattr(settings, 'OPENAI_API_KEY', None) or
                getattr(settings, 'ANTHROPIC_API_KEY', None)
            )
            if api_key_available:
                provider = getattr(settings, 'LLM_PROVIDER', 'openai')
                model = getattr(settings, 'LLM_MODEL', None)
                self.llm = LLMService(provider=provider, model=model)
            else:
                logger.warning("No API key - falling back to mock mode")
                self.use_ai = False
    
    def run_full_workflow(self, skip_phases: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete book writing workflow.
        
        Args:
            skip_phases: List of phase names to skip (e.g., ['planning'] if already done)
            
        Returns:
            Complete workflow results with all phase data
        """
        skip_phases = skip_phases or []
        results = {}
        
        phases = [
            (WorkflowPhase.PLANNING, self.run_planning_phase),
            (WorkflowPhase.CHARACTERS, self.run_characters_phase),
            (WorkflowPhase.WORLD_BUILDING, self.run_world_building_phase),
            (WorkflowPhase.OUTLINE, self.run_outline_phase),
            (WorkflowPhase.CHAPTERS, self.run_chapters_phase),
        ]
        
        for phase, handler in phases:
            if phase.value in skip_phases:
                logger.info(f"Skipping phase: {phase.value}")
                continue
            
            logger.info(f"Starting phase: {phase.value}")
            result = handler()
            results[phase.value] = result
            
            if not result.success:
                logger.error(f"Phase {phase.value} failed: {result.error}")
                return {
                    'success': False,
                    'failed_phase': phase.value,
                    'error': result.error,
                    'results': results,
                    'context': self._serialize_context()
                }
            
            self.context.total_cost += result.cost
            if result.usage:
                self.context.total_tokens += result.usage.get('total_tokens', 0)
        
        logger.info(f"Workflow complete! Total cost: ${self.context.total_cost:.4f}")
        
        return {
            'success': True,
            'results': results,
            'context': self._serialize_context(),
            'total_cost': self.context.total_cost,
            'total_tokens': self.context.total_tokens
        }
    
    def run_planning_phase(self) -> PhaseResult:
        """
        Phase 1: Planning
        Generate premise, themes, and logline
        """
        from .concept_handlers import (
            PremiseGeneratorHandler,
            ThemeIdentifierHandler,
            LoglineGeneratorHandler
        )
        
        try:
            # Generate premise
            premise_result = PremiseGeneratorHandler.handle({
                'project_id': self.project_id
            })
            
            if not premise_result.get('success'):
                # Fallback to mock
                premise_result = self._mock_premise()
            
            self.context.premise = premise_result.get('premise', '')
            
            # Generate themes (only if premise exists)
            if self.context.premise:
                theme_result = ThemeIdentifierHandler.handle({
                    'project_id': self.project_id,
                    'premise': self.context.premise
                })
                if theme_result.get('success'):
                    self.context.themes = theme_result.get('themes', [])
                
                # Generate logline
                logline_result = LoglineGeneratorHandler.handle({
                    'project_id': self.project_id,
                    'premise': self.context.premise
                })
                if logline_result.get('success'):
                    self.context.logline = logline_result.get('logline', '')
            
            return PhaseResult(
                phase=WorkflowPhase.PLANNING,
                success=True,
                data={
                    'premise': self.context.premise,
                    'themes': self.context.themes,
                    'logline': self.context.logline
                },
                usage=premise_result.get('usage'),
                cost=premise_result.get('cost', 0)
            )
            
        except Exception as e:
            logger.error(f"Planning phase error: {e}")
            return PhaseResult(
                phase=WorkflowPhase.PLANNING,
                success=False,
                error=str(e)
            )
    
    def run_characters_phase(self) -> PhaseResult:
        """
        Phase 2: Characters
        Generate character cast based on project context and premise
        """
        from .character_handlers import CharacterCastGeneratorHandler
        
        try:
            # Build context for character generation
            char_context = {
                'project_context': self.context.project_context,
                'outline_context': {'has_outline': False},
                'user_requirements': f"Genre: {self.project.genre}. Premise: {self.context.premise[:500]}"
            }
            
            result = CharacterCastGeneratorHandler.handle(char_context)
            
            if not result.get('success'):
                # Fallback to mock characters
                result = self._mock_characters()
            
            characters = result.get('characters', [])
            self.context.characters = characters
            
            # Save characters to database
            saved_count = self._save_characters(characters)
            
            return PhaseResult(
                phase=WorkflowPhase.CHARACTERS,
                success=True,
                data={
                    'characters': characters,
                    'saved_count': saved_count
                },
                usage=result.get('usage'),
                cost=result.get('cost', 0)
            )
            
        except Exception as e:
            logger.error(f"Characters phase error: {e}")
            return PhaseResult(
                phase=WorkflowPhase.CHARACTERS,
                success=False,
                error=str(e)
            )
    
    def run_world_building_phase(self) -> PhaseResult:
        """
        Phase 3: World Building
        Generate world setting based on project and characters
        """
        from .world_handlers import WorldGeneratorHandler, WorldCreatorHandler
        
        try:
            # Build context for world generation
            world_context = {
                'project_context': self.context.project_context,
                'outline_context': {'has_outline': bool(self.context.premise)},
                'user_requirements': ''
            }
            
            result = WorldGeneratorHandler.handle(world_context)
            
            if not result.get('success'):
                # Fallback to mock world
                result = self._mock_world()
            
            world_data = result.get('world', {})
            self.context.world = world_data
            
            # Save world to database
            world_id = None
            if world_data:
                create_result = WorldCreatorHandler.handle({
                    'project_id': self.project_id,
                    'world': world_data
                })
                if create_result.get('success'):
                    world_id = create_result.get('world_id')
            
            return PhaseResult(
                phase=WorkflowPhase.WORLD_BUILDING,
                success=True,
                data={
                    'world': world_data,
                    'world_id': world_id,
                    'locations': result.get('locations', []),
                    'rules': result.get('rules', [])
                },
                usage=result.get('usage'),
                cost=result.get('cost', 0)
            )
            
        except Exception as e:
            logger.error(f"World building phase error: {e}")
            return PhaseResult(
                phase=WorkflowPhase.WORLD_BUILDING,
                success=False,
                error=str(e)
            )
    
    def run_outline_phase(self) -> PhaseResult:
        """
        Phase 4: Outline
        Generate story structure and chapter outlines
        """
        from ..handlers.outline_handlers import (
            OutlineContextExtractorHandler,
            SaveTheCatOutlineHandler
        )
        
        try:
            # Extract context
            context_result = OutlineContextExtractorHandler.handle({
                'project_id': self.project_id
            })
            
            # Generate outline using Save the Cat structure
            outline_result = SaveTheCatOutlineHandler.handle({
                'project_id': self.project_id,
                'project_context': self.context.project_context,
                'character_context': {'characters': self.context.characters},
                'target_chapters': 12  # Default for novel
            })
            
            if not outline_result.get('success'):
                # Fallback to mock outline
                outline_result = self._mock_outline()
            
            outline_data = outline_result.get('outline', {})
            self.context.outline = outline_data
            
            # Create chapters in database with outlines
            chapters_created = self._create_chapter_outlines(outline_data)
            
            return PhaseResult(
                phase=WorkflowPhase.OUTLINE,
                success=True,
                data={
                    'outline': outline_data,
                    'structure_type': outline_result.get('structure_type', 'save_the_cat'),
                    'chapters_created': chapters_created
                },
                usage=outline_result.get('usage'),
                cost=outline_result.get('cost', 0)
            )
            
        except Exception as e:
            logger.error(f"Outline phase error: {e}")
            return PhaseResult(
                phase=WorkflowPhase.OUTLINE,
                success=False,
                error=str(e)
            )
    
    def run_chapters_phase(self) -> PhaseResult:
        """
        Phase 5: Chapters
        Write all chapters with full context from previous phases
        """
        from .story_handlers import UniversalStoryChapterHandler
        
        try:
            chapters = BookChapters.objects.filter(
                project=self.project
            ).order_by('chapter_number')
            
            if not chapters.exists():
                return PhaseResult(
                    phase=WorkflowPhase.CHAPTERS,
                    success=False,
                    error="No chapters found. Run outline phase first."
                )
            
            written_chapters = []
            total_cost = 0
            previous_chapters = []
            
            for chapter in chapters:
                # Build chapter data with full context
                chapter_data = {
                    'chapter_number': chapter.chapter_number,
                    'chapter_title': chapter.title,
                    'chapter_outline': chapter.outline or '',
                    'project_id': self.project_id,
                    'project_title': self.project.title,
                    'project_genre': self.project.genre or 'Fiction',
                    'project_description': self.project.description or '',
                    'target_word_count': chapter.target_word_count or 2000,
                    'previous_chapters': previous_chapters[-3:]  # Last 3 chapters
                }
                
                config = {'use_llm': self.use_ai}
                result = UniversalStoryChapterHandler.handle(chapter_data, config)
                
                if result.get('success'):
                    content = result.get('content', '')
                    word_count = result.get('word_count', len(content.split()))
                    
                    # Update chapter in database
                    chapter.content = content
                    chapter.word_count = word_count
                    chapter.writing_stage = 'drafting'
                    chapter.save()
                    
                    # Add to previous chapters for context
                    previous_chapters.append({
                        'title': chapter.title,
                        'content': content,
                        'outline': chapter.outline,
                        'summary': ContextBuilder.summarize_chapter(content)
                    })
                    
                    written_chapters.append({
                        'chapter_number': chapter.chapter_number,
                        'title': chapter.title,
                        'word_count': word_count,
                        'success': True
                    })
                    
                    total_cost += result.get('cost', 0)
                else:
                    written_chapters.append({
                        'chapter_number': chapter.chapter_number,
                        'title': chapter.title,
                        'success': False,
                        'error': result.get('error')
                    })
                
                logger.info(f"Chapter {chapter.chapter_number} written: {result.get('success')}")
            
            self.context.chapters = written_chapters
            
            return PhaseResult(
                phase=WorkflowPhase.CHAPTERS,
                success=True,
                data={
                    'chapters': written_chapters,
                    'total_chapters': len(written_chapters),
                    'successful_chapters': sum(1 for c in written_chapters if c.get('success'))
                },
                cost=total_cost
            )
            
        except Exception as e:
            logger.error(f"Chapters phase error: {e}")
            return PhaseResult(
                phase=WorkflowPhase.CHAPTERS,
                success=False,
                error=str(e)
            )
    
    # Helper methods
    
    def _save_characters(self, characters: List[Dict]) -> int:
        """Save characters to database"""
        saved = 0
        for char_data in characters:
            try:
                Characters.objects.create(
                    project=self.project,
                    name=char_data.get('name', 'Unnamed'),
                    role=char_data.get('role', 'supporting'),
                    description=char_data.get('description', ''),
                    age=char_data.get('age'),
                    personality=char_data.get('personality', ''),
                    appearance=char_data.get('appearance', ''),
                    motivation=char_data.get('motivation', ''),
                    conflict=char_data.get('conflict', ''),
                    background=char_data.get('background', ''),
                    arc=char_data.get('arc', '')
                )
                saved += 1
            except Exception as e:
                logger.warning(f"Could not save character {char_data.get('name')}: {e}")
        return saved
    
    def _create_chapter_outlines(self, outline_data: Dict) -> int:
        """Create chapters with outlines in database"""
        chapters = outline_data.get('chapters', [])
        created = 0
        
        for ch in chapters:
            try:
                BookChapters.objects.create(
                    project=self.project,
                    chapter_number=ch.get('number', created + 1),
                    title=ch.get('title', f'Chapter {created + 1}'),
                    outline=ch.get('outline', ch.get('beat', '')),
                    target_word_count=ch.get('target_words', 2000),
                    status='draft',
                    writing_stage='planning'
                )
                created += 1
            except Exception as e:
                logger.warning(f"Could not create chapter: {e}")
        
        return created
    
    def _serialize_context(self) -> Dict:
        """Serialize workflow context for output"""
        return {
            'project_id': self.context.project_id,
            'premise': self.context.premise[:500] if self.context.premise else '',
            'themes': [t.get('name') if isinstance(t, dict) else t for t in self.context.themes[:5]],
            'logline': self.context.logline,
            'character_count': len(self.context.characters),
            'world_name': self.context.world.get('name', ''),
            'chapter_count': len(self.context.chapters),
            'total_cost': self.context.total_cost,
            'total_tokens': self.context.total_tokens
        }
    
    # Mock fallback methods
    
    def _mock_premise(self) -> Dict:
        """Generate mock premise"""
        genre = self.project.genre or 'Fiction'
        return {
            'success': True,
            'premise': f"In a world where {genre.lower()} meets reality, our protagonist must face their greatest challenge yet. "
                      f"As dark forces gather, they discover that the power to change everything lies within.",
            'premise_short': f"A {genre.lower()} tale of courage, discovery, and transformation.",
            'key_conflict': "The battle between destiny and free will",
            'cost': 0
        }
    
    def _mock_characters(self) -> Dict:
        """Generate mock characters"""
        genre = self.project.genre or 'Fiction'
        
        character_templates = {
            'Fantasy': [
                {'name': 'Aldric', 'role': 'protagonist', 'description': 'A young mage with untapped potential'},
                {'name': 'Lyra', 'role': 'mentor', 'description': 'A wise elder who guides the hero'},
                {'name': 'Thorne', 'role': 'antagonist', 'description': 'A dark sorcerer seeking ultimate power'}
            ],
            'Science Fiction': [
                {'name': 'Zara', 'role': 'protagonist', 'description': 'A starship captain facing impossible odds'},
                {'name': 'Nova', 'role': 'ally', 'description': 'An AI companion with emerging consciousness'},
                {'name': 'Rex', 'role': 'antagonist', 'description': 'A rogue admiral with a secret agenda'}
            ],
            'Romance': [
                {'name': 'Emma', 'role': 'protagonist', 'description': 'A career-focused woman rediscovering love'},
                {'name': 'Alexander', 'role': 'love_interest', 'description': 'A mysterious stranger with a hidden past'},
                {'name': 'Victoria', 'role': 'rival', 'description': 'A sophisticated competitor for affection'}
            ]
        }
        
        characters = character_templates.get(genre, character_templates['Fantasy'])
        
        return {
            'success': True,
            'characters': characters,
            'cost': 0
        }
    
    def _mock_world(self) -> Dict:
        """Generate mock world"""
        genre = self.project.genre or 'Fiction'
        
        world_templates = {
            'Fantasy': {
                'name': 'The Realm of Ardenia',
                'time_period': 'Medieval Fantasy Era',
                'geography': 'A vast continent with mountains, forests, and ancient ruins',
                'culture': 'Feudal society with guilds of mages and warrior orders',
                'technology_level': 'Pre-industrial with magic supplementing technology',
                'magic_system': 'Elemental magic tied to bloodlines'
            },
            'Science Fiction': {
                'name': 'The Terran Collective',
                'time_period': '27th Century',
                'geography': 'Multiple star systems connected by jump gates',
                'culture': 'Post-scarcity society with AI integration',
                'technology_level': 'FTL travel, quantum computing, bioengineering',
                'magic_system': 'None - hard science fiction'
            }
        }
        
        world = world_templates.get(genre, world_templates['Fantasy'])
        
        return {
            'success': True,
            'world': world,
            'locations': [],
            'rules': [],
            'cost': 0
        }
    
    def _mock_outline(self) -> Dict:
        """Generate mock outline using Save the Cat structure"""
        beats = [
            {'number': 1, 'title': 'Opening Image', 'beat': 'Establish the protagonist\'s ordinary world'},
            {'number': 2, 'title': 'Setup', 'beat': 'Introduce characters, world, and stakes'},
            {'number': 3, 'title': 'Catalyst', 'beat': 'The inciting incident that changes everything'},
            {'number': 4, 'title': 'Debate', 'beat': 'Protagonist hesitates before committing'},
            {'number': 5, 'title': 'Break Into Two', 'beat': 'Protagonist enters the new world'},
            {'number': 6, 'title': 'B Story', 'beat': 'Introduction of the love/friendship subplot'},
            {'number': 7, 'title': 'Fun and Games', 'beat': 'The promise of the premise'},
            {'number': 8, 'title': 'Midpoint', 'beat': 'A major revelation or false victory'},
            {'number': 9, 'title': 'Bad Guys Close In', 'beat': 'Opposition intensifies'},
            {'number': 10, 'title': 'All Is Lost', 'beat': 'The darkest moment'},
            {'number': 11, 'title': 'Dark Night of the Soul', 'beat': 'Protagonist faces their deepest fears'},
            {'number': 12, 'title': 'Finale', 'beat': 'The climactic confrontation and resolution'}
        ]
        
        return {
            'success': True,
            'outline': {
                'structure_type': 'save_the_cat',
                'chapters': beats
            },
            'structure_type': 'save_the_cat',
            'cost': 0
        }
