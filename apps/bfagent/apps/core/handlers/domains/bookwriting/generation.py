"""
Generation handlers for Book Writing Studio.

These handlers generate new content (chapters, characters, etc.).
"""

from typing import Any, Dict, Optional
from apps.core.handlers.base import BaseHandler


class ChapterGenerateHandler(BaseHandler):
    """
    Generates new chapters for a book project.

    Creates chapter structures based on outline or generates
    chapter drafts using AI.
    """

    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.chapter.generate"
        self.name = "Chapter Generation Handler"
        self.description = "Generates new chapters for book projects"
        self.version = "1.0.0"

    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ['project', 'agent']
        missing = [key for key in required if key not in context]

        if missing:
            return False, f"Missing required context: {', '.join(missing)}"

        return True, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate chapters.

        Args:
            context: {
                'project': BookProject instance
                'agent': Agent instance
                'action': str (e.g., 'generate_chapters_from_outline')
                'count': Optional[int] - Number of chapters to generate
                'user': Optional[User] for tracking
            }

        Returns:
            {
                'success': bool
                'chapters': List[dict] - Generated chapter data
                'error': Optional[str]
                'metadata': {...}
            }
        """
        from apps.bfagent.models import BookChapters
        from apps.bfagent.services.project_enrichment import (
            _choose_llm,
            _call_llm,
        )

        project = context['project']
        agent = context['agent']
        action = context.get('action', 'generate_chapters_from_outline')
        count = context.get('count', 5)

        try:
            # Choose LLM
            llm = _choose_llm(agent)
            if not llm:
                return {
                    'success': False,
                    'chapters': [],
                    'error': 'No active LLM configured',
                    'metadata': {}
                }

            # Build prompt for chapter generation
            system = agent.system_prompt or "You are a creative writing assistant."
            user_message = f"""
Generate {count} chapter outlines for:

Title: {project.title}
Genre: {project.genre}
Premise: {project.story_premise}

For each chapter provide:
1. Chapter Number
2. Chapter Title
3. Summary (2-3 sentences)
4. Key Events (3-5 bullet points)

Format as:
## Chapter 1: [Title]
**Summary:** [2-3 sentences]
**Key Events:**
- Event 1
- Event 2
- Event 3
"""

            # Call LLM
            response = _call_llm(llm, system, user_message)

            # Parse response and create chapters
            chapters_data = self._parse_chapters(response)

            # Create chapter records
            created_chapters = []
            for i, chapter_data in enumerate(chapters_data[:count], start=1):
                chapter = BookChapters.objects.create(
                    project=project,
                    chapter_number=i,
                    title=chapter_data.get('title', f'Chapter {i}'),
                    summary=chapter_data.get('summary', ''),
                    outline=chapter_data.get('outline', ''),
                    notes=chapter_data.get('notes', ''),
                )
                created_chapters.append({
                    'id': chapter.pk,
                    'number': chapter.chapter_number,
                    'title': chapter.title,
                })

            return {
                'success': True,
                'chapters': created_chapters,
                'error': None,
                'metadata': {
                    'llm_id': llm.pk,
                    'agent_id': agent.pk,
                    'project_id': project.pk,
                    'count': len(created_chapters),
                }
            }

        except Exception as e:
            return {
                'success': False,
                'chapters': [],
                'error': str(e),
                'metadata': {
                    'project_id': project.pk,
                }
            }

    def _parse_chapters(self, response: str) -> list[dict]:
        """Parse LLM response into chapter data."""
        chapters = []
        lines = response.split('\n')

        current_chapter = None
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith('## Chapter'):
                if current_chapter:
                    chapters.append(current_chapter)

                # Extract title
                parts = line.split(':', 1)
                title = parts[1].strip() if len(parts) > 1 else line

                current_chapter = {
                    'title': title,
                    'summary': '',
                    'outline': '',
                    'notes': '',
                }
                current_section = None

            elif line.startswith('**Summary:**'):
                current_section = 'summary'
                summary = line.replace('**Summary:**', '').strip()
                if current_chapter and summary:
                    current_chapter['summary'] = summary

            elif line.startswith('**Key Events:**'):
                current_section = 'outline'

            elif line.startswith('-') and current_chapter:
                event = line[1:].strip()
                if current_section == 'outline':
                    current_chapter['outline'] += f"- {event}\n"

            elif line and current_chapter and current_section == 'summary':
                current_chapter['summary'] += f" {line}"

        if current_chapter:
            chapters.append(current_chapter)

        return chapters


class WorldCreationHandler(BaseHandler):
    """
    Creates world definitions for book projects.
    
    Analyzes project data (outline, premise, genre) and creates
    one or more world definitions with AI-generated details.
    """
    
    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.world.create"
        self.name = "World Creation Handler"
        self.description = "Creates world definitions from project data"
        self.version = "1.0.0"
    
    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ['project', 'agent']
        missing = [key for key in required if key not in context]
        
        if missing:
            return False, f"Missing required context: {', '.join(missing)}"
        
        return True, None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create world definitions.
        
        Args:
            context: {
                'project': BookProject instance
                'agent': Agent instance
                'world_count': Optional[int] - Number of worlds to create (default: 1)
                'world_names': Optional[List[str]] - Specific world names
                'user': Optional[User] for tracking
            }
        
        Returns:
            {
                'success': bool
                'worlds': List[Worlds] - Created world instances
                'error': Optional[str]
                'metadata': {...}
            }
        """
        from apps.bfagent.models import Worlds
        from apps.bfagent.services.project_enrichment import (
            _choose_llm,
            _call_llm,
        )
        
        project = context['project']
        agent = context['agent']
        world_count = context.get('world_count', 1)
        world_names = context.get('world_names', [])
        user = context.get('user')
        
        try:
            # Choose LLM
            llm = _choose_llm(agent)
            if not llm:
                return {
                    'success': False,
                    'worlds': [],
                    'error': 'No active LLM configured',
                    'metadata': {}
                }
            
            # Determine world count and names
            if world_names:
                world_count = len(world_names)
            elif world_count < 1:
                world_count = 1
            
            # Build prompt for world creation
            system = agent.system_prompt or "You are a creative world-building assistant."
            user_message = f"""
Create {world_count} detailed world definition(s) for this book project:

Title: {project.title}
Genre: {project.genre}
Premise: {project.story_premise or 'Not yet defined'}
Themes: {project.story_themes or 'Not yet defined'}

{f'World Names: {", ".join(world_names)}' if world_names else 'Generate creative world names'}

For each world, provide:

## World Name: [Creative Name]
**Type:** [primary/secondary/parallel]
**Description:** [2-3 sentence overview]
**Setting Details:** [Time period, general atmosphere, key features]
**Geography:** [Major regions, landscapes, climate]
**Culture:** [Social structures, customs, beliefs]
**Technology Level:** [Medieval/Renaissance/Modern/Futuristic/etc.]
**Magic System:** [If applicable - rules, limitations, sources]
**Politics:** [Government types, power structures, conflicts]
**History:** [Major events, founding, evolution]
**Inhabitants:** [Species/races, demographics, notable groups]
**Connections:** [How this world relates to others, if multiple worlds]

Make the worlds rich, internally consistent, and appropriate for the genre.
"""
            
            # Call LLM
            response = _call_llm(
                llm=llm,
                system_prompt=system,
                user_message=user_message,
                temperature=0.8,  # Higher creativity for world-building
                max_tokens=4000,  # More tokens for detailed world descriptions
            )
            
            if not response:
                return {
                    'success': False,
                    'worlds': [],
                    'error': 'LLM returned empty response',
                    'metadata': {}
                }
            
            # Parse response and create world instances
            worlds = self._parse_and_create_worlds(
                response=response,
                project=project,
                world_count=world_count,
                world_names=world_names,
            )
            
            return {
                'success': True,
                'worlds': worlds,
                'error': None,
                'metadata': {
                    'world_count': len(worlds),
                    'llm_response_length': len(response),
                    'llm_name': llm.name,
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'worlds': [],
                'error': str(e),
                'metadata': {}
            }
    
    def _parse_and_create_worlds(
        self,
        response: str,
        project: Any,
        world_count: int,
        world_names: list = None
    ) -> list:
        """
        Parse LLM response and create World instances.
        
        Args:
            response: LLM response text
            project: BookProject instance
            world_count: Expected number of worlds
            world_names: Optional list of world names
        
        Returns:
            List of created Worlds instances
        """
        from apps.bfagent.models import Worlds
        import re
        
        worlds = []
        
        # Split response into world sections
        world_sections = re.split(r'##\s*World\s+Name:', response)
        world_sections = [s.strip() for s in world_sections if s.strip()]
        
        for idx, section in enumerate(world_sections[:world_count]):
            try:
                # Extract world data using regex patterns
                world_data = self._extract_world_data(section)
                
                # Use provided name or extracted name
                if world_names and idx < len(world_names):
                    world_data['name'] = world_names[idx]
                
                # Create world instance
                world = Worlds.objects.create(
                    project=project,
                    name=world_data.get('name', f'World {idx + 1}'),
                    description=world_data.get('description', ''),
                    world_type=world_data.get('type', 'primary'),
                    setting_details=world_data.get('setting_details', ''),
                    geography=world_data.get('geography', ''),
                    culture=world_data.get('culture', ''),
                    technology_level=world_data.get('technology_level', ''),
                    magic_system=world_data.get('magic_system', ''),
                    politics=world_data.get('politics', ''),
                    history=world_data.get('history', ''),
                    inhabitants=world_data.get('inhabitants', ''),
                    connections=world_data.get('connections', ''),
                )
                
                worlds.append(world)
            
            except Exception as e:
                # Log error but continue with other worlds
                print(f"Error creating world {idx + 1}: {e}")
                continue
        
        return worlds
    
    def _extract_world_data(self, section: str) -> Dict[str, str]:
        """
        Extract world data from a section of LLM response.
        
        Args:
            section: Text section containing world data
        
        Returns:
            Dictionary with extracted world attributes
        """
        import re
        
        data = {}
        
        # Pattern mapping: field -> regex pattern
        patterns = {
            'name': r'^([^\n*]+)',  # First line before any markdown
            'type': r'\*\*Type:\*\*\s*([^\n]+)',
            'description': r'\*\*Description:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'setting_details': r'\*\*Setting Details:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'geography': r'\*\*Geography:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'culture': r'\*\*Culture:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'technology_level': r'\*\*Technology Level:\*\*\s*([^\n]+)',
            'magic_system': r'\*\*Magic System:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'politics': r'\*\*Politics:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'history': r'\*\*History:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'inhabitants': r'\*\*Inhabitants:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
            'connections': r'\*\*Connections:\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, section, re.MULTILINE | re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        return data


class CharacterCastHandler(BaseHandler):
    """
    Generates a cast of characters for a book project.

    Creates multiple character records based on story requirements.
    """

    def __init__(self):
        super().__init__()
        self.handler_id = "bookwriting.character.cast"
        self.name = "Character Cast Handler"
        self.description = "Generates character cast for book projects"
        self.version = "1.0.0"

    def validate_input(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate required context."""
        required = ['project', 'agent']
        missing = [key for key in required if key not in context]

        if missing:
            return False, f"Missing required context: {', '.join(missing)}"

        return True, None

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate character cast.

        Args:
            context: {
                'project': BookProject instance
                'agent': Agent instance
                'count': Optional[int] - Number of characters to generate
                'user': Optional[User] for tracking
            }

        Returns:
            {
                'success': bool
                'characters': List[dict] - Generated character data
                'error': Optional[str]
                'metadata': {...}
            }
        """
        from apps.bfagent.models import Characters
        from apps.bfagent.services.project_enrichment import (
            _choose_llm,
            _call_llm,
        )

        project = context['project']
        agent = context['agent']
        count = context.get('count', 6)

        try:
            # Choose LLM
            llm = _choose_llm(agent)
            if not llm:
                return {
                    'success': False,
                    'characters': [],
                    'error': 'No active LLM configured',
                    'metadata': {}
                }

            # Build prompt for character generation
            system = agent.system_prompt or "You are a character development expert."
            user_message = f"""
Generate {count} distinct characters for:

Title: {project.title}
Genre: {project.genre}
Premise: {project.story_premise}
Setting: {project.setting_time}, {project.setting_location}
Protagonist Concept: {project.protagonist_concept}
Antagonist Concept: {project.antagonist_concept}

For each character provide:
1. Name
2. Role (Protagonist, Antagonist, Supporting, Minor)
3. Age
4. Description (2-3 sentences: appearance, personality, background)

Format as:
## Character 1
**Name:** [Full Name]
**Role:** [Role Type]
**Age:** [Age]
**Description:** [2-3 sentences]
"""

            # Call LLM
            response = _call_llm(llm, system, user_message)

            # Parse response and create characters
            characters_data = self._parse_characters(response)

            # Create character records
            created_characters = []
            for character_data in characters_data[:count]:
                character = Characters.objects.create(
                    project=project,
                    name=character_data.get('name', 'Unnamed Character'),
                    role=character_data.get('role', 'Supporting'),
                    age=character_data.get('age'),
                    description=character_data.get('description', ''),
                )
                created_characters.append({
                    'id': character.pk,
                    'name': character.name,
                    'role': character.role,
                })

            return {
                'success': True,
                'characters': created_characters,
                'error': None,
                'metadata': {
                    'llm_id': llm.pk,
                    'agent_id': agent.pk,
                    'project_id': project.pk,
                    'count': len(created_characters),
                }
            }

        except Exception as e:
            return {
                'success': False,
                'characters': [],
                'error': str(e),
                'metadata': {
                    'project_id': project.pk,
                }
            }

    def _parse_characters(self, response: str) -> list[dict]:
        """Parse LLM response into character data."""
        characters = []
        lines = response.split('\n')

        current_character = None

        for line in lines:
            line = line.strip()

            if line.startswith('## Character'):
                if current_character:
                    characters.append(current_character)
                current_character = {
                    'name': '',
                    'role': 'Supporting',
                    'age': None,
                    'description': '',
                }

            elif line.startswith('**Name:**') and current_character:
                name = line.replace('**Name:**', '').strip()
                current_character['name'] = name

            elif line.startswith('**Role:**') and current_character:
                role = line.replace('**Role:**', '').strip()
                current_character['role'] = role

            elif line.startswith('**Age:**') and current_character:
                age_str = line.replace('**Age:**', '').strip()
                try:
                    current_character['age'] = int(age_str.split()[0])
                except (ValueError, IndexError):
                    pass

            elif line.startswith('**Description:**') and current_character:
                desc = line.replace('**Description:**', '').strip()
                current_character['description'] = desc

            elif line and current_character and current_character['description']:
                # Continue description
                current_character['description'] += f" {line}"

        if current_character:
            characters.append(current_character)

        return characters
