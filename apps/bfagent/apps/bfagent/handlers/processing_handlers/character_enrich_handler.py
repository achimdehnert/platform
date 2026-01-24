"""
CharacterEnrichHandler - Feature #29
Deep character development: traits, relationships, arcs, backstory, voice

Architecture:
    Input → Validation → LLM Processing → Character Update → Output

Dependencies:
    - BaseProcessingHandler
    - Characters, BookProjects models
    - Agents, Llms models (for LLM integration)
"""

import logging
from typing import Any, Dict, List

from apps.bfagent.handlers.base import BaseProcessingHandler, ProcessingError
from apps.bfagent.models import Characters, BookProjects
from apps.bfagent.services.context_enrichment.enricher import DatabaseContextEnricher

logger = logging.getLogger(__name__)


class CharacterEnrichHandler(BaseProcessingHandler):
    """
    Handler for AI-powered character enrichment and development

    Features:
        - Character profile development (personality, traits, flaws)
        - Backstory generation
        - Character arc planning
        - Relationship dynamics
        - Dialogue voice enhancement
        - Character motivation analysis
        - Psychological depth

    Usage:
        handler = CharacterEnrichHandler()
        result = handler.execute({
            'action': 'develop_character_profile',
            'character_id': 1,
            'project_id': 1,
            'parameters': {...}
        })
    """

    def __init__(self):
        super().__init__(name="character_enrichment", version="1.0.0")
        self.context_enricher = DatabaseContextEnricher()
        self.supported_actions = [
            'develop_character_profile',
            'generate_character_backstory',
            'analyze_character_arc',
            'create_character_relationships',
            'enhance_character_voice',
            'define_character_motivation',
            'create_character_flaws',
            'generate_character_goals',
        ]

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute character enrichment action

        Args:
            context: Dictionary containing:
                - action: str (required) - Action to perform
                - character_id: int (required) - Character ID
                - project_id: int (optional) - Project context
                - parameters: Dict (optional) - Action-specific parameters
                - agent_id: int (optional) - Specific agent to use

        Returns:
            Dictionary with:
                - success: bool
                - action: str
                - data: Dict with enrichment results
                - suggestions: List of field updates
                - message: str (optional)

        Raises:
            ProcessingError: If action fails
        """
        action = context.get('action')
        if not action:
            raise ProcessingError("Action is required in context")

        if action not in self.supported_actions:
            raise ProcessingError(
                f"Unsupported action: {action}. "
                f"Supported: {', '.join(self.supported_actions)}"
            )

        logger.info(f"CharacterEnrichHandler executing action: {action}")

        # Validate character exists
        character_id = context.get('character_id')
        if not character_id:
            raise ProcessingError("character_id is required")

        try:
            character = Characters.objects.get(pk=character_id)
        except Characters.DoesNotExist:
            raise ProcessingError(f"Character {character_id} not found")

        # Get project context if available
        project = None
        project_id = context.get('project_id')
        if project_id:
            try:
                project = BookProjects.objects.get(pk=project_id)
            except BookProjects.DoesNotExist:
                logger.warning(f"Project {project_id} not found, continuing without project context")

        # Route to specific action handler
        action_handlers = {
            'develop_character_profile': self._develop_character_profile,
            'generate_character_backstory': self._generate_character_backstory,
            'analyze_character_arc': self._analyze_character_arc,
            'create_character_relationships': self._create_character_relationships,
            'enhance_character_voice': self._enhance_character_voice,
            'define_character_motivation': self._define_character_motivation,
            'create_character_flaws': self._create_character_flaws,
            'generate_character_goals': self._generate_character_goals,
        }

        handler = action_handlers[action]
        return handler(context, character, project)

    # ========================================================================
    # ACTION HANDLERS
    # ========================================================================

    def _develop_character_profile(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Develop comprehensive character profile

        Context parameters:
            - depth: str (optional - 'basic', 'detailed', 'comprehensive')
            - focus_areas: List[str] (optional - specific traits to develop)
        """
        parameters = context.get('parameters', {})
        depth = parameters.get('depth', 'detailed')
        focus_areas = parameters.get('focus_areas', [])

        # Build character and project context
        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Generate profile (mock for now)
        profile = self._mock_generate_profile(
            char_context,
            proj_context,
            depth,
            focus_areas
        )

        result = {
            'success': True,
            'action': 'develop_character_profile',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'profile': profile,
                'depth': depth,
            },
            'suggestions': [
                {
                    'field_name': 'personality',
                    'new_value': profile['personality'],
                    'confidence': 0.85,
                    'rationale': f'AI-generated {depth} personality profile',
                },
                {
                    'field_name': 'character_traits',
                    'new_value': ', '.join(profile['traits']),
                    'confidence': 0.82,
                    'rationale': 'AI-identified character traits',
                },
            ],
            'message': f"Developed {depth} profile for {character.character_name}",
        }

        logger.info(
            f"Developed {depth} profile for character {character.id} "
            f"({character.character_name})"
        )
        return result

    def _generate_character_backstory(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Generate detailed character backstory

        Context parameters:
            - length: str (optional - 'brief', 'standard', 'detailed')
            - themes: List[str] (optional - backstory themes)
            - formative_events: int (optional - number of key events)
        """
        parameters = context.get('parameters', {})
        length = parameters.get('length', 'standard')
        themes = parameters.get('themes', [])
        num_events = parameters.get('formative_events', 3)

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Generate backstory (mock for now)
        backstory = self._mock_generate_backstory(
            char_context,
            proj_context,
            length,
            themes,
            num_events
        )

        result = {
            'success': True,
            'action': 'generate_character_backstory',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'backstory': backstory,
                'length': length,
                'formative_events': num_events,
            },
            'suggestions': [
                {
                    'field_name': 'background',
                    'new_value': backstory['narrative'],
                    'confidence': 0.88,
                    'rationale': f'AI-generated {length} backstory with {num_events} formative events',
                },
            ],
            'message': f"Generated {length} backstory for {character.character_name}",
        }

        logger.info(
            f"Generated {length} backstory for character {character.id} "
            f"with {num_events} formative events"
        )
        return result

    def _analyze_character_arc(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Analyze and develop character arc

        Context parameters:
            - arc_type: str (optional - 'positive', 'negative', 'flat', 'complex')
            - story_phases: List[str] (optional - phases for arc progression)
        """
        parameters = context.get('parameters', {})
        arc_type = parameters.get('arc_type', 'positive')
        story_phases = parameters.get('story_phases', ['beginning', 'middle', 'end'])

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Analyze arc (mock for now)
        arc_analysis = self._mock_analyze_arc(
            char_context,
            proj_context,
            arc_type,
            story_phases
        )

        result = {
            'success': True,
            'action': 'analyze_character_arc',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'arc_analysis': arc_analysis,
                'arc_type': arc_type,
            },
            'suggestions': [
                {
                    'field_name': 'arc',
                    'new_value': arc_analysis['summary'],
                    'confidence': 0.82,
                    'rationale': f'AI-analyzed {arc_type} character arc across {len(story_phases)} phases',
                },
            ],
            'message': f"Analyzed {arc_type} arc for {character.character_name}",
        }

        logger.info(
            f"Analyzed {arc_type} character arc for character {character.id}"
        )
        return result

    def _create_character_relationships(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Create and define character relationships

        Context parameters:
            - relationship_types: List[str] (optional - types to focus on)
            - other_characters: List[int] (optional - specific character IDs)
        """
        parameters = context.get('parameters', {})
        rel_types = parameters.get('relationship_types', [])
        other_char_ids = parameters.get('other_characters', [])

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Get other characters if specified
        other_chars = []
        if other_char_ids and project:
            other_chars = list(
                Characters.objects.filter(
                    id__in=other_char_ids,
                    project=project
                )
            )

        # Create relationships (mock for now)
        relationships = self._mock_create_relationships(
            char_context,
            proj_context,
            rel_types,
            other_chars
        )

        result = {
            'success': True,
            'action': 'create_character_relationships',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'relationships': relationships,
                'num_relationships': len(relationships),
            },
            'suggestions': [
                {
                    'field_name': 'description',
                    'new_value': relationships['summary'],
                    'confidence': 0.78,
                    'rationale': f'AI-generated relationship dynamics with {len(relationships["details"])} characters',
                },
            ],
            'message': f"Created {len(relationships['details'])} relationships for {character.character_name}",
        }

        logger.info(
            f"Created relationships for character {character.id} "
            f"with {len(other_chars)} other characters"
        )
        return result

    def _enhance_character_voice(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Enhance character dialogue voice and speech patterns

        Context parameters:
            - voice_traits: List[str] (optional - specific voice characteristics)
            - sample_dialogue: str (optional - example dialogue to analyze)
        """
        parameters = context.get('parameters', {})
        voice_traits = parameters.get('voice_traits', [])
        sample_dialogue = parameters.get('sample_dialogue', '')

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Enhance voice (mock for now)
        voice_profile = self._mock_enhance_voice(
            char_context,
            proj_context,
            voice_traits,
            sample_dialogue
        )

        result = {
            'success': True,
            'action': 'enhance_character_voice',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'voice_profile': voice_profile,
            },
            'suggestions': [
                {
                    'field_name': 'personality',
                    'new_value': voice_profile['description'],
                    'confidence': 0.85,
                    'rationale': 'AI-enhanced dialogue voice characteristics',
                },
            ],
            'message': f"Enhanced voice for {character.character_name}",
        }

        logger.info(f"Enhanced voice for character {character.id}")
        return result

    def _define_character_motivation(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Define character core motivations and desires

        Context parameters:
            - motivation_categories: List[str] (optional - 'internal', 'external', 'subconscious')
        """
        parameters = context.get('parameters', {})
        categories = parameters.get('motivation_categories', ['internal', 'external'])

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Define motivations (mock for now)
        motivations = self._mock_define_motivations(
            char_context,
            proj_context,
            categories
        )

        result = {
            'success': True,
            'action': 'define_character_motivation',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'motivations': motivations,
            },
            'suggestions': [
                {
                    'field_name': 'motivation',
                    'new_value': motivations['summary'],
                    'confidence': 0.80,
                    'rationale': f'AI-defined {len(categories)} types of character motivation',
                },
            ],
            'message': f"Defined motivations for {character.character_name}",
        }

        logger.info(f"Defined motivations for character {character.id}")
        return result

    def _create_character_flaws(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Create realistic character flaws and weaknesses

        Context parameters:
            - flaw_types: List[str] (optional - 'moral', 'physical', 'psychological')
            - num_flaws: int (optional - number of flaws to generate)
        """
        parameters = context.get('parameters', {})
        flaw_types = parameters.get('flaw_types', ['moral', 'psychological'])
        num_flaws = parameters.get('num_flaws', 3)

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Create flaws (mock for now)
        flaws = self._mock_create_flaws(
            char_context,
            proj_context,
            flaw_types,
            num_flaws
        )

        result = {
            'success': True,
            'action': 'create_character_flaws',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'flaws': flaws,
                'num_flaws': num_flaws,
            },
            'suggestions': [
                {
                    'field_name': 'flaws',
                    'new_value': ', '.join([f['name'] for f in flaws['details']]),
                    'confidence': 0.83,
                    'rationale': f'AI-created {num_flaws} character flaws',
                },
            ],
            'message': f"Created {num_flaws} flaws for {character.character_name}",
        }

        logger.info(f"Created {num_flaws} flaws for character {character.id}")
        return result

    def _generate_character_goals(
        self,
        context: Dict[str, Any],
        character: Characters,
        project: BookProjects = None
    ) -> Dict[str, Any]:
        """
        Generate character goals and objectives

        Context parameters:
            - time_horizon: str (optional - 'immediate', 'short_term', 'long_term', 'all')
            - goal_types: List[str] (optional - 'personal', 'professional', 'relational')
        """
        parameters = context.get('parameters', {})
        time_horizon = parameters.get('time_horizon', 'all')
        goal_types = parameters.get('goal_types', ['personal', 'professional'])

        char_context = self._build_character_context(character)
        proj_context = self._build_project_context(project) if project else {}

        # Generate goals (mock for now)
        goals = self._mock_generate_goals(
            char_context,
            proj_context,
            time_horizon,
            goal_types
        )

        result = {
            'success': True,
            'action': 'generate_character_goals',
            'data': {
                'character_id': character.id,
                'character_name': character.character_name,
                'goals': goals,
                'time_horizon': time_horizon,
            },
            'suggestions': [
                {
                    'field_name': 'goals',
                    'new_value': goals['summary'],
                    'confidence': 0.81,
                    'rationale': f'AI-generated {time_horizon} goals across {len(goal_types)} categories',
                },
            ],
            'message': f"Generated {time_horizon} goals for {character.character_name}",
        }

        logger.info(
            f"Generated {time_horizon} goals for character {character.id}"
        )
        return result

    # ========================================================================
    # HELPER METHODS - CONTEXT BUILDING
    # ========================================================================

    def _build_character_context(self, character: Characters) -> Dict[str, Any]:
        """Build comprehensive character context"""
        return {
            'character_id': character.id,
            'name': character.character_name or '',
            'role': character.role or '',
            'archetype': character.archetype or '',
            'description': character.description or '',
            'personality': getattr(character, 'personality', ''),
            'background': getattr(character, 'background', ''),
            'motivation': getattr(character, 'motivation', ''),
        }

    def _build_project_context(self, project: BookProjects, character_id: int = None) -> Dict[str, Any]:
        """
        Build project context using DatabaseContextEnricher
        Falls back to basic context if enrichment fails
        
        Args:
            project: BookProjects instance
            character_id: Optional character ID for character-specific context
        
        Returns:
            Enriched project context dictionary
        """
        try:
            params = {'project_id': project.id}
            if character_id:
                params['character_id'] = character_id
            
            # Try to use chapter_generation schema for project context
            enriched_context = self.context_enricher.enrich(
                'chapter_generation',
                **params
            )
            
            logger.info(
                f"Enriched project context for project {project.id} "
                f"using DatabaseContextEnricher"
            )
            
            return enriched_context
            
        except Exception as e:
            # Fallback to basic context if enrichment fails
            logger.warning(
                f"Context enrichment failed: {e}. Using fallback basic context."
            )
            return {
                'project_id': project.id,
                'title': project.title or '',
                'genre': project.genre or '',
                'themes': project.story_themes or '',
                'tone': project.atmosphere_tone or '',
                'setting': f"{project.setting_time or ''}, {project.setting_location or ''}",
                'conflict': project.main_conflict or '',
            }

    # ========================================================================
    # MOCK GENERATION METHODS (Will be replaced with LLM calls)
    # ========================================================================

    def _mock_generate_profile(
        self,
        char_context: Dict,
        proj_context: Dict,
        depth: str,
        focus_areas: List[str]
    ) -> Dict[str, Any]:
        """Mock profile generation - will be replaced with LLM"""
        name = char_context.get('name', 'Character')
        role = char_context.get('role', 'protagonist')

        return {
            'personality': f"Complex {role} with depth: brave, loyal, compassionate, yet vulnerable",
            'traits': ['brave', 'loyal', 'compassionate', 'vulnerable', 'determined'],
            'strengths': ['physical prowess', 'leadership', 'empathy'],
            'weaknesses': ['impulsiveness', 'trust issues', 'fear of failure'],
            'depth_level': depth,
            'focus_areas': focus_areas or ['all aspects'],
        }

    def _mock_generate_backstory(
        self,
        char_context: Dict,
        proj_context: Dict,
        length: str,
        themes: List[str],
        num_events: int
    ) -> Dict[str, Any]:
        """Mock backstory generation - will be replaced with LLM"""
        name = char_context.get('name', 'Character')

        return {
            'narrative': f"""{name}'s journey began in hardship, shaped by {num_events} pivotal moments.
Growing up in challenging circumstances, they learned resilience early.
Each formative event carved their character deeper, creating the person they are today.

[In production, this will be a rich, detailed backstory generated by LLM]""",
            'formative_events': [
                {'age': 8, 'event': 'Loss of mentor', 'impact': 'Developed self-reliance'},
                {'age': 15, 'event': 'First major challenge', 'impact': 'Discovered inner strength'},
                {'age': 20, 'event': 'Defining choice', 'impact': 'Shaped core values'},
            ][:num_events],
            'themes': themes or ['loss', 'growth', 'redemption'],
            'length': length,
        }

    def _mock_analyze_arc(
        self,
        char_context: Dict,
        proj_context: Dict,
        arc_type: str,
        story_phases: List[str]
    ) -> Dict[str, Any]:
        """Mock arc analysis - will be replaced with LLM"""
        return {
            'summary': f"Journey from self-doubt to confidence. {arc_type.capitalize()} arc across {len(story_phases)} phases.",
            'arc_type': arc_type,
            'phases': {
                phase: f"Character development during {phase} phase"
                for phase in story_phases
            },
            'transformation': {
                'start_state': 'Uncertain, isolated, defensive',
                'end_state': 'Confident, connected, open',
                'key_changes': ['trust', 'self-belief', 'relationships'],
            }
        }

    def _mock_create_relationships(
        self,
        char_context: Dict,
        proj_context: Dict,
        rel_types: List[str],
        other_chars: List
    ) -> Dict[str, Any]:
        """Mock relationship creation - will be replaced with LLM"""
        return {
            'summary': "Complex web of relationships driving character growth and conflict.",
            'details': [
                {
                    'relationship_type': 'mentor',
                    'description': 'Strong bonds with mentor figure, source of wisdom',
                    'dynamic': 'respectful, learning-focused',
                },
                {
                    'relationship_type': 'rivalry',
                    'description': 'Tense rivalry with competing character',
                    'dynamic': 'competitive, challenging',
                },
                {
                    'relationship_type': 'romantic',
                    'description': 'Developing romantic interest',
                    'dynamic': 'uncertain, evolving',
                },
            ],
            'num_relationships': 3,
        }

    def _mock_enhance_voice(
        self,
        char_context: Dict,
        proj_context: Dict,
        voice_traits: List[str],
        sample_dialogue: str
    ) -> Dict[str, Any]:
        """Mock voice enhancement - will be replaced with LLM"""
        return {
            'description': "Speaks in short, direct sentences. Uses vivid metaphors. Occasional dry humor to mask emotion.",
            'speech_patterns': [
                'Short sentences',
                'Action-oriented verbs',
                'Minimal adjectives',
                'Occasional regional dialect',
            ],
            'dialogue_style': 'direct, honest, sometimes blunt',
            'vocabulary_level': 'practical, conversational',
            'unique_phrases': ['I reckon...', 'Fair enough', 'Could be worse'],
        }

    def _mock_define_motivations(
        self,
        char_context: Dict,
        proj_context: Dict,
        categories: List[str]
    ) -> Dict[str, Any]:
        """Mock motivation definition - will be replaced with LLM"""
        return {
            'summary': "Driven by desire for belonging and redemption, tempered by fear of vulnerability.",
            'internal': 'Need for self-acceptance and inner peace',
            'external': 'Desire to protect loved ones and community',
            'subconscious': 'Fear of abandonment, need for validation',
            'hierarchy': ['belonging', 'redemption', 'protection', 'peace'],
        }

    def _mock_create_flaws(
        self,
        char_context: Dict,
        proj_context: Dict,
        flaw_types: List[str],
        num_flaws: int
    ) -> Dict[str, Any]:
        """Mock flaw creation - will be replaced with LLM"""
        return {
            'summary': f"{num_flaws} flaws that humanize and challenge the character",
            'details': [
                {
                    'name': 'Impulsiveness',
                    'type': 'psychological',
                    'description': 'Acts before thinking in emotional situations',
                    'impact': 'Creates complications, damages relationships',
                },
                {
                    'name': 'Trust issues',
                    'type': 'psychological',
                    'description': 'Difficulty trusting others due to past betrayals',
                    'impact': 'Isolates self, misses opportunities for connection',
                },
                {
                    'name': 'Pride',
                    'type': 'moral',
                    'description': 'Reluctant to ask for help or admit mistakes',
                    'impact': 'Prevents growth, leads to preventable failures',
                },
            ][:num_flaws],
        }

    def _mock_generate_goals(
        self,
        char_context: Dict,
        proj_context: Dict,
        time_horizon: str,
        goal_types: List[str]
    ) -> Dict[str, Any]:
        """Mock goal generation - will be replaced with LLM"""
        return {
            'summary': f"Multi-layered {time_horizon} goals driving character actions and decisions",
            'immediate': ['Survive current challenge', 'Protect allies'],
            'short_term': ['Gain skills', 'Build trust'],
            'long_term': ['Find belonging', 'Achieve redemption'],
            'categories': {
                gt: f"Goals related to {gt} development"
                for gt in goal_types
            },
        }
