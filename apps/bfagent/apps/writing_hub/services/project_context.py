"""
Project Context Service
Gathers accumulated context from all project phases for AI generation.
Integrates with PromptFactory for context-aware prompts.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Complete context from a project for AI generation"""
    
    # Project basics
    project_id: int = 0
    title: str = ""
    genre: str = ""
    description: str = ""
    target_audience: str = ""
    target_word_count: int = 0
    
    # Planning phase
    premise: str = ""
    themes: List[str] = field(default_factory=list)
    logline: str = ""
    tone: str = ""
    
    # Characters
    characters: List[Dict[str, Any]] = field(default_factory=list)
    protagonist: Optional[Dict[str, Any]] = None
    antagonist: Optional[Dict[str, Any]] = None
    
    # World building
    worlds: List[Dict[str, Any]] = field(default_factory=list)
    setting: str = ""
    
    # Outline / Structure
    outline: List[Dict[str, Any]] = field(default_factory=list)
    chapter_summaries: List[str] = field(default_factory=list)
    
    # Idea Session (if linked)
    idea_responses: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    content_type: str = "novel"
    current_phase: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'project': {
                'id': self.project_id,
                'title': self.title,
                'genre': self.genre,
                'description': self.description,
                'target_audience': self.target_audience,
                'target_word_count': self.target_word_count,
            },
            'planning': {
                'premise': self.premise,
                'themes': self.themes,
                'logline': self.logline,
                'tone': self.tone,
            },
            'characters': {
                'all': self.characters,
                'protagonist': self.protagonist,
                'antagonist': self.antagonist,
                'count': len(self.characters),
            },
            'world': {
                'all': self.worlds,
                'setting': self.setting,
            },
            'structure': {
                'outline': self.outline,
                'chapter_summaries': self.chapter_summaries,
                'chapter_count': len(self.outline),
            },
            'ideas': self.idea_responses,
            'meta': {
                'content_type': self.content_type,
                'current_phase': self.current_phase,
            }
        }
    
    def get_summary(self, max_length: int = 500) -> str:
        """Get a condensed summary for prompt context"""
        parts = []
        
        if self.title:
            parts.append(f"Projekt: {self.title}")
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.premise:
            parts.append(f"Premise: {self.premise[:200]}...")
        if self.themes:
            parts.append(f"Themes: {', '.join(self.themes[:5])}")
        if self.protagonist:
            parts.append(f"Protagonist: {self.protagonist.get('name', 'Unbekannt')}")
        if self.setting:
            parts.append(f"Setting: {self.setting[:100]}...")
        
        summary = "\n".join(parts)
        return summary[:max_length] if len(summary) > max_length else summary


class ProjectContextService:
    """
    Service for gathering complete project context from all phases.
    
    Usage:
        service = ProjectContextService()
        context = service.get_context(project_id)
        
        # Use with PromptFactory
        from apps.bfagent.services.prompt_factory import PromptFactory
        factory = PromptFactory()
        prompt = factory.build('premise_generator', context.to_dict())
    """
    
    def get_context(self, project_id: int, current_phase: str = "") -> ProjectContext:
        """
        Gather complete context from a project
        
        Args:
            project_id: The project ID
            current_phase: Current workflow phase (planning, characters, world, outline, write)
        
        Returns:
            ProjectContext with all available data
        """
        from apps.bfagent.models import BookProjects, BookChapters, Characters
        
        context = ProjectContext(project_id=project_id, current_phase=current_phase)
        
        try:
            project = BookProjects.objects.get(pk=project_id)
        except BookProjects.DoesNotExist:
            logger.warning(f"Project {project_id} not found")
            return context
        
        # Basic project info
        context.title = project.title or ""
        context.genre = project.genre or ""
        context.description = project.description or ""
        context.target_audience = project.target_audience or ""
        context.target_word_count = project.target_word_count or 50000
        
        # Planning data
        context.premise = project.story_premise or ""
        context.logline = project.tagline or ""
        context.tone = project.atmosphere_tone or ""
        
        if project.story_themes:
            context.themes = [t.strip() for t in project.story_themes.split(',') if t.strip()]
        
        # Parse content type from settings
        try:
            settings = json.loads(project.genre_settings) if project.genre_settings else {}
            context.content_type = settings.get('content_type', 'novel')
            idea_session_id = settings.get('idea_session_id')
        except (json.JSONDecodeError, Exception):
            idea_session_id = None
        
        # Load idea session if linked
        if idea_session_id:
            context.idea_responses = self._load_idea_session(idea_session_id)
        
        # Load characters
        context.characters = self._load_characters(project_id)
        context.protagonist = self._find_character_by_role(context.characters, 'protagonist')
        context.antagonist = self._find_character_by_role(context.characters, 'antagonist')
        
        # Load world building
        context.worlds = self._load_worlds(project_id)
        if context.worlds:
            context.setting = context.worlds[0].get('description', '')
        
        # Load outline/chapters
        context.outline = self._load_outline(project_id)
        context.chapter_summaries = [ch.get('summary', '') for ch in context.outline if ch.get('summary')]
        
        logger.info(f"Loaded context for project {project_id}: "
                   f"{len(context.characters)} characters, "
                   f"{len(context.worlds)} worlds, "
                   f"{len(context.outline)} chapters")
        
        return context
    
    def _load_idea_session(self, session_id: int) -> Dict[str, str]:
        """Load responses from linked idea session"""
        from apps.writing_hub.models import IdeaSession
        
        responses = {}
        try:
            session = IdeaSession.objects.get(pk=session_id)
            for resp in session.responses.filter(is_accepted=True).select_related('step'):
                responses[resp.step.name] = resp.content
        except Exception as e:
            logger.warning(f"Could not load idea session {session_id}: {e}")
        
        return responses
    
    def _load_characters(self, project_id: int) -> List[Dict[str, Any]]:
        """Load all characters for a project"""
        from apps.bfagent.models import Characters
        
        characters = []
        try:
            for char in Characters.objects.filter(project_id=project_id):
                characters.append({
                    'id': char.id,
                    'name': char.name or "",
                    'role': char.character_type or "",
                    'age': char.age,
                    'description': char.description or "",
                    'background': char.background or "",
                    'motivation': char.motivation or "",
                    'personality': char.personality_traits or "",
                    'arc': char.character_arc or "",
                })
        except Exception as e:
            logger.warning(f"Could not load characters for project {project_id}: {e}")
        
        return characters
    
    def _load_worlds(self, project_id: int) -> List[Dict[str, Any]]:
        """Load world building elements"""
        from apps.bfagent.models import Worlds
        
        worlds = []
        try:
            for world in Worlds.objects.filter(project_id=project_id):
                worlds.append({
                    'id': world.id,
                    'name': world.name or "",
                    'type': getattr(world, 'world_type', '') or "",
                    'description': world.description or "",
                    'rules': getattr(world, 'magic_system', '') or "",
                    'history': getattr(world, 'history', '') or "",
                })
        except Exception as e:
            logger.warning(f"Could not load worlds for project {project_id}: {e}")
        
        return worlds
    
    def _load_outline(self, project_id: int) -> List[Dict[str, Any]]:
        """Load chapter outline"""
        from apps.bfagent.models import BookChapters
        
        chapters = []
        try:
            for ch in BookChapters.objects.filter(project_id=project_id).order_by('sequence_number'):
                chapters.append({
                    'id': ch.id,
                    'number': ch.sequence_number or 0,
                    'title': ch.title or "",
                    'summary': ch.summary or "",
                    'status': ch.status or "",
                    'word_count': ch.word_count or 0,
                })
        except Exception as e:
            logger.warning(f"Could not load chapters for project {project_id}: {e}")
        
        return chapters
    
    def _find_character_by_role(self, characters: List[Dict], role: str) -> Optional[Dict]:
        """Find character by role (protagonist, antagonist, etc.)"""
        for char in characters:
            char_role = (char.get('role') or '').lower()
            if role.lower() in char_role:
                return char
        return None
    
    def get_phase_suggestions(self, project_id: int, target_phase: str) -> Dict[str, Any]:
        """
        Get AI-ready suggestions for a specific phase based on prior phases
        
        Args:
            project_id: Project ID
            target_phase: Phase to generate suggestions for
        
        Returns:
            Dictionary with suggested values for the target phase
        """
        context = self.get_context(project_id, target_phase)
        suggestions = {}
        
        if target_phase == 'planning':
            # Suggestions from idea session
            if context.idea_responses:
                if 'premise' in context.idea_responses:
                    suggestions['premise'] = context.idea_responses['premise']
                if 'core_conflict' in context.idea_responses:
                    suggestions['premise'] = context.idea_responses['core_conflict']
                if 'themes' in context.idea_responses:
                    suggestions['themes'] = [t.strip() for t in context.idea_responses['themes'].split(',')]
                if 'protagonist' in context.idea_responses:
                    suggestions['logline_hint'] = context.idea_responses['protagonist']
        
        elif target_phase == 'characters':
            # Suggestions from planning + ideas
            suggestions['genre'] = context.genre
            suggestions['tone'] = context.tone
            if context.idea_responses:
                if 'protagonist' in context.idea_responses:
                    suggestions['protagonist_hint'] = context.idea_responses['protagonist']
                if 'antagonist' in context.idea_responses:
                    suggestions['antagonist_hint'] = context.idea_responses['antagonist']
        
        elif target_phase == 'world':
            # Suggestions from planning + characters
            suggestions['genre'] = context.genre
            suggestions['tone'] = context.tone
            suggestions['character_names'] = [c['name'] for c in context.characters if c.get('name')]
            if context.idea_responses:
                if 'magic' in context.idea_responses:
                    suggestions['magic_system'] = context.idea_responses['magic']
                if 'setting' in context.idea_responses:
                    suggestions['setting_hint'] = context.idea_responses['setting']
        
        elif target_phase == 'outline':
            # Full context for outline generation
            suggestions['premise'] = context.premise
            suggestions['themes'] = context.themes
            suggestions['characters'] = context.characters
            suggestions['worlds'] = context.worlds
            if context.idea_responses:
                if 'trials' in context.idea_responses:
                    suggestions['plot_points'] = context.idea_responses['trials']
                if 'reward' in context.idea_responses:
                    suggestions['ending_hint'] = context.idea_responses['reward']
        
        elif target_phase == 'write':
            # Everything for chapter writing
            suggestions['full_context'] = context.to_dict()
        
        return suggestions


# Singleton instance for easy access
project_context_service = ProjectContextService()
