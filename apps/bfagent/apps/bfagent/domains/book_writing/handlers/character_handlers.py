"""
Character Handlers - Book Writing Domain
Modular handlers for character generation and creation
"""
from typing import Dict, Any, List
import logging

from django.conf import settings
from apps.bfagent.models import BookProjects, Characters
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class CharacterCastGeneratorHandler:
    """
    Generate character cast using LLM from provided context
    
    Input:
    - project_context: dict (from ProjectContextExtractorHandler)
    - outline_context: dict (from OutlineContextExtractorHandler, optional)
    - user_requirements: str (optional)
    - character_count: int (optional, default: auto)
    
    Output:
    - characters: list of character dicts
    - raw_content: str
    - usage: dict (LLM usage stats)
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate characters with LLM"""
        project_context = data.get('project_context', {})
        outline_context = data.get('outline_context', {})
        user_requirements = data.get('user_requirements', '')
        
        if not project_context:
            return {'success': False, 'error': 'project_context required'}
        
        # Check API key
        api_key_available = (
            getattr(settings, 'OPENAI_API_KEY', None) or
            getattr(settings, 'ANTHROPIC_API_KEY', None)
        )
        
        if not api_key_available:
            return {'success': False, 'error': 'No LLM API key configured'}
        
        # Build prompt
        prompt = CharacterCastGeneratorHandler._build_prompt(
            project_context, outline_context, user_requirements
        )
        
        # Generate with LLM
        provider = getattr(settings, 'LLM_PROVIDER', 'openai')
        model = getattr(settings, 'LLM_MODEL', None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7
        )
        
        if not result['success']:
            return result
        
        # Parse characters
        characters = CharacterCastGeneratorHandler._parse_characters(result['content'])
        
        logger.info(f"Generated {len(characters)} characters")
        
        return {
            'success': True,
            'characters': characters,
            'raw_content': result['content'],
            'usage': result.get('usage'),
            'cost': llm.calculate_cost(result['usage']) if result.get('usage') else 0
        }
    
    @staticmethod
    def _build_prompt(
        project_context: Dict,
        outline_context: Dict,
        user_requirements: str
    ) -> str:
        """Build LLM prompt"""
        parts = [
            "# Task: Generate Character Cast for Novel",
            "",
            "## Book Information:",
            f"- **Title:** {project_context.get('title', 'Untitled')}",
            f"- **Genre:** {project_context.get('genre', 'Fiction')}",
            f"- **Description:** {project_context.get('description', 'N/A')}",
            "",
        ]
        
        if outline_context.get('has_outline'):
            parts.extend([
                "## Story Outline:",
                outline_context['formatted'],
                "",
            ])
        
        if user_requirements:
            parts.extend([
                "## Additional Requirements:",
                user_requirements,
                "",
            ])
        
        parts.extend([
            "## Instructions:",
            "Generate 3-6 main characters. For each provide:",
            "- NAME: Full name",
            "- ROLE: (Protagonist/Antagonist/Mentor/Supporting)",
            "- AGE: Age",
            "- DESCRIPTION: 2-3 sentences",
            "- PERSONALITY: Key traits",
            "- APPEARANCE: Physical description",
            "- MOTIVATION: What drives them",
            "- CONFLICT: Their struggle",
            "- BACKGROUND: Brief backstory",
            "- ARC: Character development",
            "",
            "## Format (EXACT):",
            "---CHARACTER START---",
            "NAME: [name]",
            "ROLE: [role]",
            "AGE: [age]",
            "DESCRIPTION: [description]",
            "PERSONALITY: [personality]",
            "APPEARANCE: [appearance]",
            "MOTIVATION: [motivation]",
            "CONFLICT: [conflict]",
            "BACKGROUND: [background]",
            "ARC: [arc]",
            "---CHARACTER END---",
            "",
            "Generate now:",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_characters(content: str) -> List[Dict]:
        """Parse LLM output into character dicts"""
        characters = []
        blocks = content.split('---CHARACTER START---')
        
        for block in blocks[1:]:
            if '---CHARACTER END---' not in block:
                continue
            
            char_data = block.split('---CHARACTER END---')[0].strip()
            character = {}
            
            for line in char_data.split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'name':
                    character['name'] = value
                elif key == 'role':
                    character['role'] = value
                elif key == 'age':
                    try:
                        character['age'] = int(value)
                    except ValueError:
                        character['age'] = 0
                elif key == 'description':
                    character['description'] = value
                elif key == 'personality':
                    character['personality'] = value
                elif key == 'appearance':
                    character['appearance'] = value
                elif key == 'motivation':
                    character['motivation'] = value
                elif key == 'conflict':
                    character['conflict'] = value
                elif key == 'background':
                    character['background'] = value
                elif key == 'arc':
                    character['arc'] = value
            
            if character.get('name'):
                characters.append(character)
        
        return characters


class SingleCharacterCreatorHandler:
    """
    Create single character in database
    
    Input:
    - project_id: int
    - character: dict (name, role, age, etc.)
    
    Output:
    - character_id: int
    - created: bool
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create single character"""
        project_id = data.get('project_id')
        character_data = data.get('character', {})
        
        if not project_id or not character_data:
            return {'success': False, 'error': 'project_id and character required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Project not found'}
        
        # Create character
        character = Characters.objects.create(
            project=project,
            name=character_data.get('name', 'Unnamed'),
            role=character_data.get('role', ''),
            age=character_data.get('age', 0),
            description=character_data.get('description', ''),
            personality=character_data.get('personality', ''),
            appearance=character_data.get('appearance', ''),
            motivation=character_data.get('motivation', ''),
            conflict=character_data.get('conflict', ''),
            background=character_data.get('background', ''),
            arc=character_data.get('arc', '')
        )
        
        logger.info(f"Created character {character.name} for project {project_id}")
        
        return {
            'success': True,
            'character_id': character.id,
            'created': True
        }


class CharacterBatchCreatorHandler:
    """
    Create multiple characters in database
    
    Input:
    - project_id: int
    - characters: list of character dicts
    
    Output:
    - character_ids: list of ints
    - created_count: int
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create multiple characters"""
        project_id = data.get('project_id')
        characters_data = data.get('characters', [])
        
        if not project_id or not characters_data:
            return {'success': False, 'error': 'project_id and characters required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Project not found'}
        
        created_ids = []
        
        for char_data in characters_data:
            try:
                character = Characters.objects.create(
                    project=project,
                    name=char_data.get('name', 'Unnamed'),
                    role=char_data.get('role', ''),
                    age=char_data.get('age', 0),
                    description=char_data.get('description', ''),
                    personality=char_data.get('personality', ''),
                    appearance=char_data.get('appearance', ''),
                    motivation=char_data.get('motivation', ''),
                    conflict=char_data.get('conflict', ''),
                    background=char_data.get('background', ''),
                    arc=char_data.get('arc', '')
                )
                created_ids.append(character.id)
                logger.info(f"Created character {character.name}")
            except Exception as e:
                logger.error(f"Failed to create character: {e}")
                continue
        
        logger.info(f"Created {len(created_ids)} characters for project {project_id}")
        
        return {
            'success': True,
            'character_ids': created_ids,
            'created_count': len(created_ids)
        }
