"""
World Building Handlers - Book Writing Domain
Modular handlers for world generation and creation
"""
from typing import Dict, Any, List
import logging

from django.conf import settings
from apps.bfagent.models import BookProjects, Worlds
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class WorldGeneratorHandler:
    """
    Generate world setting using LLM from project context
    
    Input:
    - project_context: dict
    - outline_context: dict (optional)
    - user_requirements: str (optional)
    
    Output:
    - world: dict (world data)
    - locations: list of location dicts
    - rules: list of rule dicts
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate world with LLM"""
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
        prompt = WorldGeneratorHandler._build_prompt(
            project_context, outline_context, user_requirements
        )
        
        # Generate with LLM
        provider = getattr(settings, 'LLM_PROVIDER', 'openai')
        model = getattr(settings, 'LLM_MODEL', None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=2500,
            temperature=0.7
        )
        
        if not result['success']:
            return result
        
        # Parse response
        parsed = WorldGeneratorHandler._parse_world(result['content'])
        
        logger.info(f"Generated world with {len(parsed['locations'])} locations and {len(parsed['rules'])} rules")
        
        return {
            'success': True,
            'world': parsed['world'],
            'locations': parsed['locations'],
            'rules': parsed['rules'],
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
        """Build LLM prompt for world generation"""
        parts = [
            "# Task: Create World Setting for Novel",
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
            "Create a comprehensive world setting with:",
            "",
            "### World Setting (Overall):",
            "- NAME: World name",
            "- TIME_PERIOD: When story takes place",
            "- GEOGRAPHY: Physical setting",
            "- CULTURE: Social structure, customs",
            "- TECHNOLOGY: Tech level",
            "- MAGIC: Magic system (if applicable)",
            "- HISTORY: Brief history",
            "",
            "### Locations (3-5):",
            "For each location:",
            "- NAME: Location name",
            "- TYPE: (city/building/region/landmark)",
            "- IMPORTANCE: (major/minor/background)",
            "- DESCRIPTION: What it is",
            "",
            "### Rules (3-5):",
            "Critical world rules:",
            "- CATEGORY: (magic/physics/social/technology)",
            "- TITLE: Rule name",
            "- IMPORTANCE: (critical/important/flavor)",
            "- DESCRIPTION: What the rule is",
            "",
            "## Format (EXACT):",
            "---WORLD START---",
            "NAME: [world name]",
            "TIME_PERIOD: [time period]",
            "GEOGRAPHY: [geography]",
            "CULTURE: [culture]",
            "TECHNOLOGY: [tech level]",
            "MAGIC: [magic system]",
            "HISTORY: [history]",
            "---WORLD END---",
            "",
            "---LOCATION START---",
            "NAME: [location name]",
            "TYPE: [type]",
            "IMPORTANCE: [importance]",
            "DESCRIPTION: [description]",
            "---LOCATION END---",
            "",
            "---RULE START---",
            "CATEGORY: [category]",
            "TITLE: [title]",
            "IMPORTANCE: [importance]",
            "DESCRIPTION: [description]",
            "---RULE END---",
            "",
            "Generate now:",
        ])
        
        return "\n".join(parts)
    
    @staticmethod
    def _parse_world(content: str) -> Dict:
        """Parse LLM output"""
        result = {
            'world': {},
            'locations': [],
            'rules': []
        }
        
        # Parse world
        if '---WORLD START---' in content:
            world_block = content.split('---WORLD START---')[1]
            if '---WORLD END---' in world_block:
                world_data = world_block.split('---WORLD END---')[0].strip()
                world = {}
                
                for line in world_data.split('\n'):
                    line = line.strip()
                    if ':' not in line:
                        continue
                    
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'name':
                        world['name'] = value
                    elif key == 'time_period':
                        world['time_period'] = value
                    elif key == 'geography':
                        world['geography'] = value
                    elif key == 'culture':
                        world['culture'] = value
                    elif key == 'technology':
                        world['technology_level'] = value
                    elif key == 'magic':
                        world['magic_system'] = value
                    elif key == 'history':
                        world['history'] = value
                
                result['world'] = world
        
        # Parse locations
        location_blocks = content.split('---LOCATION START---')
        for block in location_blocks[1:]:
            if '---LOCATION END---' not in block:
                continue
            
            loc_data = block.split('---LOCATION END---')[0].strip()
            location = {}
            
            for line in loc_data.split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'name':
                    location['name'] = value
                elif key == 'type':
                    location['location_type'] = value
                elif key == 'importance':
                    location['importance'] = value
                elif key == 'description':
                    location['description'] = value
            
            if location.get('name'):
                result['locations'].append(location)
        
        # Parse rules
        rule_blocks = content.split('---RULE START---')
        for block in rule_blocks[1:]:
            if '---RULE END---' not in block:
                continue
            
            rule_data = block.split('---RULE END---')[0].strip()
            rule = {}
            
            for line in rule_data.split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'category':
                    rule['category'] = value
                elif key == 'title':
                    rule['title'] = value
                elif key == 'importance':
                    rule['importance'] = value
                elif key == 'description':
                    rule['description'] = value
            
            if rule.get('title'):
                result['rules'].append(rule)
        
        return result


class WorldCreatorHandler:
    """
    Create World in database using the Worlds model
    
    Input:
    - project_id: int
    - world: dict (from WorldGeneratorHandler)
    
    Output:
    - world_id: int
    - created: bool
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create world in database"""
        project_id = data.get('project_id')
        world_data = data.get('world', {})
        
        if not project_id or not world_data:
            return {'success': False, 'error': 'project_id and world required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': 'Project not found'}
        
        # Create using the actual Worlds model
        world = Worlds.objects.create(
            project=project,
            name=world_data.get('name', 'Unnamed World'),
            world_type=world_data.get('world_type', 'primary'),
            description=world_data.get('description', ''),
            setting_details=world_data.get('time_period', ''),
            geography=world_data.get('geography', ''),
            culture=world_data.get('culture', ''),
            technology_level=world_data.get('technology_level', ''),
            magic_system=world_data.get('magic_system', ''),
            politics=world_data.get('politics', ''),
            history=world_data.get('history', ''),
            inhabitants=world_data.get('inhabitants', ''),
        )
        
        logger.info(f"Created world '{world.name}' for project {project_id}")
        
        return {
            'success': True,
            'world_id': world.id,
            'world_name': world.name,
            'created': True
        }


class LocationCreatorHandler:
    """
    Create Location in database
    
    Input:
    - world_id: int
    - location: dict
    
    Output:
    - location_id: int
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create location"""
        world_id = data.get('world_id')
        location_data = data.get('location', {})
        
        if not world_id or not location_data:
            return {'success': False, 'error': 'world_id and location required'}
        
        try:
            world = WorldSetting.objects.get(id=world_id)
        except WorldSetting.DoesNotExist:
            return {'success': False, 'error': 'World not found'}
        
        location = Location.objects.create(
            world=world,
            name=location_data.get('name', 'Unnamed Location'),
            location_type=location_data.get('location_type', 'other'),
            importance=location_data.get('importance', 'minor'),
            description=location_data.get('description', '')
        )
        
        logger.info(f"Created location {location.name} for world {world_id}")
        
        return {
            'success': True,
            'location_id': location.id,
            'created': True
        }


class RuleCreatorHandler:
    """
    Create WorldRule in database
    
    Input:
    - world_id: int
    - rule: dict
    
    Output:
    - rule_id: int
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create world rule"""
        world_id = data.get('world_id')
        rule_data = data.get('rule', {})
        
        if not world_id or not rule_data:
            return {'success': False, 'error': 'world_id and rule required'}
        
        try:
            world = WorldSetting.objects.get(id=world_id)
        except WorldSetting.DoesNotExist:
            return {'success': False, 'error': 'World not found'}
        
        rule = WorldRule.objects.create(
            world=world,
            category=rule_data.get('category', 'other'),
            title=rule_data.get('title', 'Unnamed Rule'),
            importance=rule_data.get('importance', 'flavor'),
            description=rule_data.get('description', '')
        )
        
        logger.info(f"Created rule {rule.title} for world {world_id}")
        
        return {
            'success': True,
            'rule_id': rule.id,
            'created': True
        }


class WorldBatchCreatorHandler:
    """
    Create complete world with locations and rules
    
    Input:
    - project_id: int
    - world: dict
    - locations: list of dicts
    - rules: list of dicts
    
    Output:
    - world_id: int
    - location_ids: list
    - rule_ids: list
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create complete world setup"""
        project_id = data.get('project_id')
        world_data = data.get('world', {})
        locations_data = data.get('locations', [])
        rules_data = data.get('rules', [])
        
        if not project_id or not world_data:
            return {'success': False, 'error': 'project_id and world required'}
        
        # Create world
        world_result = WorldCreatorHandler.handle({
            'project_id': project_id,
            'world': world_data
        })
        
        if not world_result['success']:
            return world_result
        
        world_id = world_result['world_id']
        
        # Create locations
        location_ids = []
        for loc_data in locations_data:
            loc_result = LocationCreatorHandler.handle({
                'world_id': world_id,
                'location': loc_data
            })
            if loc_result['success']:
                location_ids.append(loc_result['location_id'])
        
        # Create rules
        rule_ids = []
        for rule_data in rules_data:
            rule_result = RuleCreatorHandler.handle({
                'world_id': world_id,
                'rule': rule_data
            })
            if rule_result['success']:
                rule_ids.append(rule_result['rule_id'])
        
        logger.info(
            f"Created world {world_id} with {len(location_ids)} locations "
            f"and {len(rule_ids)} rules for project {project_id}"
        )
        
        return {
            'success': True,
            'world_id': world_id,
            'location_ids': location_ids,
            'rule_ids': rule_ids,
            'created_counts': {
                'locations': len(location_ids),
                'rules': len(rule_ids)
            }
        }
