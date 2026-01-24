"""
Context Provider System for Dynamic Prompt Template Resolution

This module provides a flexible system for resolving context variables
based on the action type and available data.
"""

from typing import Dict, Any, Optional


class ContextProvider:
    """Base class for context providers"""
    
    @staticmethod
    def get_available_variables() -> Dict[str, str]:
        """Return dict of available variables with descriptions"""
        raise NotImplementedError
    
    @staticmethod
    def resolve_context(action, **kwargs) -> Dict[str, Any]:
        """Resolve context based on action and inputs"""
        raise NotImplementedError


class ProjectContextProvider(ContextProvider):
    """Provides project-level context"""
    
    @staticmethod
    def get_available_variables() -> Dict[str, str]:
        return {
            'project_title': 'Title of the book project',
            'project_genre': 'Genre of the book',
            'project_outline': 'Full outline of the book',
            'project_premise': 'Story premise',
            'project_tagline': 'Project tagline',
            'target_audience': 'Target audience',
            'unique_elements': 'Unique story elements',
            'genre_settings': 'Genre-specific settings',
            'word_count_target': 'Target word count',
        }
    
    @staticmethod
    def resolve_context(action, project_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if not project_id:
            return {}
        
        from apps.bfagent.models import BookProjects
        try:
            project = BookProjects.objects.get(id=project_id)
            return {
                'project_title': project.title or '',
                'project_genre': project.genre or '',
                'project_outline': project.outline or '',
                'project_premise': project.story_premise or '',
                'project_tagline': project.tagline or '',
                'target_audience': project.target_audience or '',
                'unique_elements': project.unique_elements or '',
                'genre_settings': project.genre_settings or '',
                'word_count_target': project.word_count_target or 0,
            }
        except BookProjects.DoesNotExist:
            return {}


class CustomFieldContextProvider(ContextProvider):
    """Provides custom field values as context"""
    
    @staticmethod
    def get_available_variables(project_id: Optional[int] = None) -> Dict[str, str]:
        """
        Dynamically get available custom field variables for a project.
        Returns all active field definitions with 'custom.' prefix
        """
        from apps.bfagent.models import FieldDefinition
        
        variables = {}
        
        # Get all active field definitions
        field_definitions = FieldDefinition.objects.filter(
            is_active=True,
            target_model='project'  # Only project-level fields for now
        ).order_by('name')
        
        for field_def in field_definitions:
            # Add with 'custom.' prefix
            var_name = f'custom.{field_def.name}'
            variables[var_name] = f'{field_def.display_name} (Custom Field)'
        
        return variables
    
    @staticmethod
    def resolve_context(action, project_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Resolve custom field values for a project.
        Returns dict with 'custom.field_name' keys
        """
        if not project_id:
            return {}
        
        from apps.bfagent.models import ProjectFieldValue, FieldDefinition
        
        context = {}
        
        # Get all field values for this project
        field_values = ProjectFieldValue.objects.filter(
            project_id=project_id,
            field_definition__is_active=True,
            field_definition__target_model='project'
        ).select_related('field_definition')
        
        for field_value in field_values:
            # Create 'custom.field_name' variable
            var_name = f'custom.{field_value.field_definition.name}'
            value = field_value.get_value()
            
            # Convert value to string if needed
            if value is not None:
                if isinstance(value, (dict, list)):
                    import json
                    context[var_name] = json.dumps(value, indent=2)
                else:
                    context[var_name] = str(value)
            else:
                context[var_name] = ''
        
        return context


class ChapterContextProvider(ContextProvider):
    """Provides chapter-specific context"""
    
    @staticmethod
    def get_available_variables() -> Dict[str, str]:
        return {
            'chapter_number': 'Chapter number',
            'chapter_title': 'Current chapter title',
            'chapter_summary': 'Chapter summary',
            'chapter_content': 'Chapter content',
            'previous_chapter_summary': 'Summary of previous chapter',
            'next_chapter_summary': 'Summary of next chapter',
            'story_arc': 'Current story arc',
            'plot_points': 'Plot points in this chapter',
            'featured_characters': 'Characters in this chapter',
            'mood_tone': 'Mood and tone of the chapter',
            'setting_location': 'Setting/location of the chapter',
        }
    
    @staticmethod
    def resolve_context(action, chapter_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if not chapter_id:
            return {}
        
        from apps.bfagent.models import BookChapters
        try:
            chapter = BookChapters.objects.select_related(
                'project', 'story_arc'
            ).prefetch_related('featured_characters', 'plot_points').get(id=chapter_id)
            
            # Get previous chapter
            prev_chapter = BookChapters.objects.filter(
                project=chapter.project,
                chapter_number__lt=chapter.chapter_number
            ).order_by('-chapter_number').first()
            
            # Get next chapter
            next_chapter = BookChapters.objects.filter(
                project=chapter.project,
                chapter_number__gt=chapter.chapter_number
            ).order_by('chapter_number').first()
            
            return {
                'chapter_number': chapter.chapter_number,
                'chapter_title': chapter.title or '',
                'chapter_summary': chapter.summary or '',
                'chapter_content': chapter.content or '',
                'previous_chapter_summary': prev_chapter.summary if prev_chapter else '',
                'next_chapter_summary': next_chapter.summary if next_chapter else '',
                'story_arc': chapter.story_arc.name if chapter.story_arc else '',
                'plot_points': '\n'.join([
                    f"- {pp.name}: {pp.description}" 
                    for pp in chapter.plot_points.all()
                ]),
                'featured_characters': ', '.join([c.name for c in chapter.featured_characters.all()]),
                'mood_tone': chapter.mood_tone or '',
                'setting_location': chapter.setting_location or '',
            }
        except BookChapters.DoesNotExist:
            return {}


class CharacterContextProvider(ContextProvider):
    """Provides character-specific context"""
    
    @staticmethod
    def get_available_variables() -> Dict[str, str]:
        return {
            'character_name': 'Character name',
            'character_role': 'Character role',
            'character_description': 'Character description',
            'character_backstory': 'Character backstory',
            'character_age': 'Character age',
            'existing_characters': 'All project characters',
            'character_count': 'Number of existing characters',
            'main_characters': 'List of main characters',
            'supporting_characters': 'List of supporting characters',
        }
    
    @staticmethod
    def resolve_context(action, character_id: Optional[int] = None, project_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        context = {}
        
        if character_id:
            from apps.bfagent.models import Characters
            try:
                char = Characters.objects.get(id=character_id)
                context.update({
                    'character_name': char.name or '',
                    'character_role': char.role or '',
                    'character_description': char.description or '',
                    'character_backstory': char.backstory or '',
                    'character_age': char.age or '',
                })
            except Characters.DoesNotExist:
                pass
        
        if project_id:
            from apps.bfagent.models import Characters
            chars = Characters.objects.filter(project_id=project_id)
            main_chars = [c for c in chars if c.role and 'main' in c.role.lower()]
            supporting_chars = [c for c in chars if c.role and 'support' in c.role.lower()]
            
            context.update({
                'existing_characters': '\n'.join([f"- {c.name} ({c.role})" for c in chars]),
                'character_count': chars.count(),
                'main_characters': ', '.join([c.name for c in main_chars]),
                'supporting_characters': ', '.join([c.name for c in supporting_chars]),
            })
        
        return context


class WorldContextProvider(ContextProvider):
    """Provides world-building context"""
    
    @staticmethod
    def get_available_variables() -> Dict[str, str]:
        return {
            'world_name': 'Name of the world',
            'world_description': 'World description',
            'world_rules': 'Rules and constraints',
            'magic_system': 'Magic system description',
            'technology_level': 'Technology level',
            'culture_notes': 'Cultural notes',
        }
    
    @staticmethod
    def resolve_context(action, world_id: Optional[int] = None, project_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if not world_id:
            return {}
        
        from apps.bfagent.models import Worlds
        try:
            world = Worlds.objects.get(id=world_id)
            return {
                'world_name': world.name or '',
                'world_description': world.description or '',
                'world_rules': world.rules or '',
                'magic_system': world.magic_system or '',
                'technology_level': world.technology_level or '',
                'culture_notes': world.culture_notes or '',
            }
        except Worlds.DoesNotExist:
            return {}


# Registry for context providers
CONTEXT_PROVIDERS = {
    'project': ProjectContextProvider,
    'chapter': ChapterContextProvider,
    'character': CharacterContextProvider,
    'world': WorldContextProvider,
    'custom_fields': CustomFieldContextProvider,  # NEW: Dynamic custom fields
}


def get_context_for_action(action, **kwargs) -> Dict[str, Any]:
    """
    Resolve all applicable context for an action based on its type and inputs.
    
    Args:
        action: The AgentAction instance
        **kwargs: Context parameters (project_id, chapter_id, character_id, etc.)
    
    Returns:
        Dict with all resolved context variables
    """
    context = {}
    
    # Determine which providers to use based on action name/agent type
    agent_type = action.agent.agent_type.lower() if action.agent.agent_type else ''
    action_name = action.name.lower()
    
    # Always include project context if available
    if kwargs.get('project_id'):
        context.update(CONTEXT_PROVIDERS['project'].resolve_context(action, **kwargs))
    
    # Chapter-related actions
    if 'chapter' in agent_type or 'chapter' in action_name:
        if kwargs.get('chapter_id'):
            context.update(CONTEXT_PROVIDERS['chapter'].resolve_context(action, **kwargs))
    
    # Character-related actions
    if 'character' in agent_type or 'character' in action_name:
        context.update(CONTEXT_PROVIDERS['character'].resolve_context(action, **kwargs))
    
    # World-building actions
    if 'world' in agent_type or 'world' in action_name:
        if kwargs.get('world_id'):
            context.update(CONTEXT_PROVIDERS['world'].resolve_context(action, **kwargs))
    
    # ALWAYS include custom fields if project_id is available
    if kwargs.get('project_id'):
        context.update(CONTEXT_PROVIDERS['custom_fields'].resolve_context(action, **kwargs))
    
    # Add user-provided context and requirements
    if kwargs.get('context'):
        context['user_context'] = kwargs['context']
    if kwargs.get('requirements'):
        context['user_requirements'] = kwargs['requirements']
    
    # Add action and agent metadata
    context.update({
        'action_name': action.display_name or action.name,
        'agent_name': action.agent.name,
        'agent_type': action.agent.agent_type or '',
    })
    
    return context


def get_available_variables_for_action(action) -> Dict[str, str]:
    """
    Get all available template variables for an action.
    
    Returns:
        Dict mapping variable names to descriptions
    """
    variables = {
        'action_name': 'Name of the current action',
        'agent_name': 'Name of the agent',
        'agent_type': 'Type of the agent',
        'user_context': 'User-provided context',
        'user_requirements': 'User-provided requirements',
    }
    
    # Determine which providers are applicable
    agent_type = action.agent.agent_type.lower() if action.agent.agent_type else ''
    action_name = action.name.lower()
    
    # Always include project variables
    variables.update(CONTEXT_PROVIDERS['project'].get_available_variables())
    
    # ALWAYS include custom field variables (dynamically loaded)
    variables.update(CONTEXT_PROVIDERS['custom_fields'].get_available_variables())
    
    # Add context-specific variables
    if 'chapter' in agent_type or 'chapter' in action_name:
        variables.update(CONTEXT_PROVIDERS['chapter'].get_available_variables())
    
    if 'character' in agent_type or 'character' in action_name:
        variables.update(CONTEXT_PROVIDERS['character'].get_available_variables())
    
    if 'world' in agent_type or 'world' in action_name:
        variables.update(CONTEXT_PROVIDERS['world'].get_available_variables())
    
    return variables
