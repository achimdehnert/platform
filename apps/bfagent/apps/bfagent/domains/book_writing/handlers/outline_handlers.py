"""
Outline Handlers - Book Writing Domain
Generate structured outlines based on story frameworks with AI integration
"""
from typing import Dict, Any, List
import logging
import json
import re

from django.conf import settings
from apps.bfagent.models import BookProjects
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SaveTheCatOutlineHandler:
    """
    Generate outline based on Save the Cat Beat Sheet
    
    Input:
    - title: str
    - genre: str
    - description: str (premise)
    - target_word_count: int
    - num_chapters: int (optional, default 15)
    
    Output:
    - outline: str (formatted markdown)
    - beats: list (individual beats with details)
    - chapter_count: int
    """
    
    # Save the Cat 15 Beats
    BEATS = [
        {
            'name': 'Opening Image',
            'position': 0.0,
            'description': 'Snapshot des Protagonisten vor der Transformation',
            'guidance': 'Zeige den Protagonisten in seiner aktuellen, unvollkommenen Welt',
            'emotional_arc': 'Status Quo, Routine'
        },
        {
            'name': 'Theme Stated',
            'position': 0.05,
            'description': 'Jemand stellt die Frage oder das Thema der Geschichte',
            'guidance': 'Ein Nebencharakter deutet das Thema/die Lektion an',
            'emotional_arc': 'Leichtes Unbehagen'
        },
        {
            'name': 'Set-Up',
            'position': 0.08,
            'description': 'Zeige die Welt des Helden und was fehlt',
            'guidance': 'Etabliere alle wichtigen Charaktere und die Welt',
            'emotional_arc': 'Routine, wachsende Unzufriedenheit'
        },
        {
            'name': 'Catalyst',
            'position': 0.10,
            'description': 'Lebensveränderndes Ereignis',
            'guidance': 'Ein Ereignis, das alles verändert - kein Zurück mehr',
            'emotional_arc': 'Schock, Aufruhr'
        },
        {
            'name': 'Debate',
            'position': 0.17,
            'description': 'Soll der Held handeln? Zweifel und Ängste',
            'guidance': 'Der Held zögert, überlegt Optionen, zeigt Angst',
            'emotional_arc': 'Unsicherheit, innerer Konflikt'
        },
        {
            'name': 'Break into Two',
            'position': 0.25,
            'description': 'Der Held entscheidet sich für Handlung',
            'guidance': 'Entscheidung getroffen, Eintritt in Akt 2',
            'emotional_arc': 'Entschlossenheit, Aufregung'
        },
        {
            'name': 'B Story',
            'position': 0.30,
            'description': 'Neue Beziehung, die das Thema erforscht',
            'guidance': 'Einführung des Mentors oder Liebesinteresses',
            'emotional_arc': 'Neue Verbindungen, Hoffnung'
        },
        {
            'name': 'Fun and Games',
            'position': 0.40,
            'description': 'Das Versprechen der Prämisse',
            'guidance': 'Der Held erforscht die neue Welt',
            'emotional_arc': 'Entdeckung, Aufregung, erste Erfolge'
        },
        {
            'name': 'Midpoint',
            'position': 0.50,
            'description': 'Falscher Sieg oder falsche Niederlage',
            'guidance': 'Scheint großartig oder alles verloren',
            'emotional_arc': 'Höhepunkt der Hoffnung oder Verzweiflung'
        },
        {
            'name': 'Bad Guys Close In',
            'position': 0.60,
            'description': 'Antagonisten gewinnen Oberhand',
            'guidance': 'Probleme häufen sich, Team zerfällt',
            'emotional_arc': 'Zunehmende Spannung, Druck'
        },
        {
            'name': 'All Is Lost',
            'position': 0.75,
            'description': 'Tiefster Punkt',
            'guidance': 'Der schlimmste Moment, symbolischer Tod',
            'emotional_arc': 'Verzweiflung, totale Niederlage'
        },
        {
            'name': 'Dark Night of the Soul',
            'position': 0.80,
            'description': 'Der Held ist am Boden',
            'guidance': 'Moment der Dunkelheit vor Erleuchtung',
            'emotional_arc': 'Hoffnungslosigkeit, letzte Zweifel'
        },
        {
            'name': 'Break into Three',
            'position': 0.83,
            'description': 'Lösung wird gefunden',
            'guidance': 'Der Held findet die Antwort',
            'emotional_arc': 'Erkenntnis, neue Entschlossenheit'
        },
        {
            'name': 'Finale',
            'position': 0.92,
            'description': 'Der Held wendet Gelerntes an',
            'guidance': 'Finale Konfrontation, Held beweist Wachstum',
            'emotional_arc': 'Triumph, Katharsis'
        },
        {
            'name': 'Final Image',
            'position': 1.0,
            'description': 'Spiegelbild des Opening Image',
            'guidance': 'Zeige Transformation, Gegenteil von Anfang',
            'emotional_arc': 'Neue Normalität, Erfüllung'
        }
    ]
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Save the Cat outline with optional AI enhancement"""
        title = data.get('title', 'Untitled')
        genre = data.get('genre', 'General Fiction')
        description = data.get('description', '')
        num_chapters = data.get('num_chapters', 15)
        use_ai = config.get('use_ai', True) if config else True
        
        # Check for AI availability
        api_key_available = (
            getattr(settings, 'OPENAI_API_KEY', None) or
            getattr(settings, 'ANTHROPIC_API_KEY', None)
        )
        
        if use_ai and api_key_available:
            return SaveTheCatOutlineHandler._generate_with_ai(
                title, genre, description, num_chapters
            )
        
        # Fallback to template-based generation
        return SaveTheCatOutlineHandler._generate_template(
            title, genre, description, num_chapters
        )
    
    @staticmethod
    def _generate_with_ai(title: str, genre: str, description: str, num_chapters: int) -> Dict[str, Any]:
        """Generate outline using AI"""
        prompt = SaveTheCatOutlineHandler._build_ai_prompt(title, genre, description, num_chapters)
        
        provider = getattr(settings, 'LLM_PROVIDER', 'openai')
        model = getattr(settings, 'LLM_MODEL', None)
        llm = LLMService(provider=provider, model=model)
        
        result = llm.generate_chapter_content(
            prompt=prompt,
            max_tokens=3000,
            temperature=0.7
        )
        
        if not result['success']:
            # Fallback to template
            logger.warning(f"AI generation failed, using template: {result.get('error')}")
            return SaveTheCatOutlineHandler._generate_template(title, genre, description, num_chapters)
        
        # Parse AI response
        parsed = SaveTheCatOutlineHandler._parse_ai_outline(result['content'], num_chapters)
        
        return {
            'success': True,
            'outline': parsed.get('outline', ''),
            'beats': parsed.get('beats', []),
            'chapters': parsed.get('chapters', []),
            'chapter_count': len(parsed.get('chapters', [])),
            'framework': 'Save the Cat (AI)',
            'usage': result.get('usage'),
            'cost': llm.calculate_cost(result['usage']) if result.get('usage') else 0
        }
    
    @staticmethod
    def _build_ai_prompt(title: str, genre: str, description: str, num_chapters: int) -> str:
        """Build prompt for AI outline generation"""
        beats_info = "\n".join([
            f"- **{beat['name']}** ({int(beat['position']*100)}%): {beat['description']}"
            for beat in SaveTheCatOutlineHandler.BEATS
        ])
        
        return f"""# Task: Generate Story Outline using Save the Cat Beat Sheet

## Book Information:
- **Title:** {title}
- **Genre:** {genre}
- **Premise:** {description}
- **Target Chapters:** {num_chapters}

## Save the Cat Beats to Follow:
{beats_info}

## Your Task:

Create a detailed chapter-by-chapter outline for this story. For each chapter:

1. Assign it to the appropriate Save the Cat beat
2. Write a compelling title
3. Write a 2-3 sentence outline of what happens
4. Specify the emotional arc

## Output Format (JSON):

```json
{{
  "chapters": [
    {{
      "number": 1,
      "title": "Chapter title",
      "beat": "Opening Image",
      "outline": "What happens in this chapter...",
      "emotional_arc": "The emotional journey in this chapter",
      "target_words": 2000
    }}
  ]
}}
```

Generate exactly {num_chapters} chapters that tell a complete, satisfying {genre} story based on the premise.
Make each chapter outline specific to THIS story - not generic beat descriptions.
"""

    @staticmethod
    def _parse_ai_outline(content: str, num_chapters: int) -> Dict[str, Any]:
        """Parse AI-generated outline"""
        # Try JSON first
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                chapters = data.get('chapters', [])
                
                # Format as outline text
                outline_lines = []
                for ch in chapters:
                    outline_lines.append(f"## Chapter {ch['number']}: {ch['title']}")
                    outline_lines.append(f"**Beat:** {ch.get('beat', 'N/A')}")
                    outline_lines.append(f"**Outline:** {ch.get('outline', '')}")
                    outline_lines.append(f"**Emotional Arc:** {ch.get('emotional_arc', '')}")
                    outline_lines.append("")
                
                return {
                    'outline': "\n".join(outline_lines),
                    'chapters': chapters,
                    'beats': [{'beat': ch.get('beat'), 'chapter': ch['number']} for ch in chapters]
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: return raw content
        return {
            'outline': content,
            'chapters': [],
            'beats': []
        }
    
    @staticmethod
    def _generate_template(title: str, genre: str, description: str, num_chapters: int) -> Dict[str, Any]:
        """Generate template-based outline (fallback)"""
        outline_lines = []
        outline_lines.append(f"# {title} - Story Outline")
        outline_lines.append(f"**Framework:** Save the Cat Beat Sheet")
        outline_lines.append(f"**Genre:** {genre}")
        outline_lines.append(f"**Premise:** {description}")
        outline_lines.append("")
        outline_lines.append("---")
        outline_lines.append("")
        
        beats_output = []
        
        # Map chapters to beats
        for i in range(1, num_chapters + 1):
            position = i / num_chapters
            
            # Find closest beat
            beat = SaveTheCatOutlineHandler._get_beat_for_position(position)
            
            outline_lines.append(f"## Chapter {i}: {beat['name']}")
            outline_lines.append(f"**Story Position:** {int(position * 100)}%")
            outline_lines.append(f"**Beat:** {beat['description']}")
            outline_lines.append(f"**Focus:** {beat['guidance']}")
            outline_lines.append(f"**Emotional Arc:** {beat['emotional_arc']}")
            outline_lines.append("")
            
            beats_output.append({
                'chapter': i,
                'beat_name': beat['name'],
                'position': position,
                'description': beat['description'],
                'guidance': beat['guidance'],
                'emotional_arc': beat['emotional_arc']
            })
        
        outline_text = "\n".join(outline_lines)
        
        logger.info(f"Generated Save the Cat outline with {num_chapters} chapters")
        
        return {
            'success': True,
            'outline': outline_text,
            'beats': beats_output,
            'chapter_count': num_chapters,
            'framework': 'Save the Cat',
            'word_count': len(outline_text.split())
        }
    
    @staticmethod
    def _get_beat_for_position(position: float) -> Dict[str, Any]:
        """Get the closest beat for a story position"""
        closest_beat = SaveTheCatOutlineHandler.BEATS[0]
        min_distance = abs(position - closest_beat['position'])
        
        for beat in SaveTheCatOutlineHandler.BEATS:
            distance = abs(position - beat['position'])
            if distance < min_distance:
                min_distance = distance
                closest_beat = beat
        
        return closest_beat


class HerosJourneyOutlineHandler:
    """Generate outline based on Hero's Journey (12 stages)"""
    
    STAGES = [
        {'name': 'Ordinary World', 'act': 1, 'description': 'Hero in their normal world before the adventure'},
        {'name': 'Call to Adventure', 'act': 1, 'description': 'The hero receives a challenge or quest'},
        {'name': 'Refusal of the Call', 'act': 1, 'description': 'Hero initially refuses or hesitates'},
        {'name': 'Meeting the Mentor', 'act': 1, 'description': 'Hero meets a guide who provides aid'},
        {'name': 'Crossing the Threshold', 'act': 2, 'description': 'Hero commits to the adventure'},
        {'name': 'Tests, Allies, Enemies', 'act': 2, 'description': 'Hero faces challenges and makes friends/foes'},
        {'name': 'Approach to Inmost Cave', 'act': 2, 'description': 'Hero prepares for major challenge'},
        {'name': 'Ordeal', 'act': 2, 'description': 'Hero faces greatest fear or most difficult challenge'},
        {'name': 'Reward', 'act': 2, 'description': 'Hero takes possession of the treasure/achievement'},
        {'name': 'The Road Back', 'act': 3, 'description': 'Hero begins journey home'},
        {'name': 'Resurrection', 'act': 3, 'description': 'Hero faces final test using all lessons learned'},
        {'name': 'Return with Elixir', 'act': 3, 'description': 'Hero returns transformed with the prize'},
    ]
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Hero's Journey outline"""
        title = data.get('title', 'Untitled')
        genre = data.get('genre', 'General Fiction')
        description = data.get('description', '')
        num_chapters = data.get('num_chapters', 12)
        
        chapters = []
        outline_lines = [
            f"# {title} - Hero's Journey Outline",
            f"**Framework:** The Hero's Journey (Campbell/Vogler)",
            f"**Genre:** {genre}",
            f"**Premise:** {description}",
            "",
            "---",
            ""
        ]
        
        # Map chapters to stages
        for i, stage in enumerate(HerosJourneyOutlineHandler.STAGES[:num_chapters], 1):
            chapters.append({
                'number': i,
                'title': stage['name'],
                'beat': stage['name'],
                'outline': stage['description'],
                'act': stage['act'],
                'target_words': 2000
            })
            
            outline_lines.extend([
                f"## Chapter {i}: {stage['name']}",
                f"**Act:** {stage['act']}",
                f"**Stage:** {stage['description']}",
                ""
            ])
        
        return {
            'success': True,
            'outline': "\n".join(outline_lines),
            'chapters': chapters,
            'beats': [{'stage': s['name'], 'act': s['act']} for s in HerosJourneyOutlineHandler.STAGES[:num_chapters]],
            'chapter_count': len(chapters),
            'framework': "Hero's Journey"
        }


class ThreeActOutlineHandler:
    """Generate outline based on Three-Act Structure"""
    
    STRUCTURE = {
        'act1': {
            'name': 'Setup',
            'percentage': 0.25,
            'beats': [
                {'name': 'Hook', 'description': 'Opening that grabs attention'},
                {'name': 'Introduction', 'description': 'Establish characters and world'},
                {'name': 'Inciting Incident', 'description': 'Event that sets story in motion'},
                {'name': 'First Plot Point', 'description': 'Hero commits to the journey'},
            ]
        },
        'act2': {
            'name': 'Confrontation',
            'percentage': 0.50,
            'beats': [
                {'name': 'Rising Action', 'description': 'Obstacles and complications'},
                {'name': 'Midpoint', 'description': 'Major revelation or shift'},
                {'name': 'Escalation', 'description': 'Stakes increase dramatically'},
                {'name': 'Crisis', 'description': 'All seems lost'},
            ]
        },
        'act3': {
            'name': 'Resolution',
            'percentage': 0.25,
            'beats': [
                {'name': 'Climax Build', 'description': 'Final preparations'},
                {'name': 'Climax', 'description': 'Ultimate confrontation'},
                {'name': 'Falling Action', 'description': 'Immediate aftermath'},
                {'name': 'Resolution', 'description': 'New equilibrium established'},
            ]
        }
    }
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Three-Act outline"""
        title = data.get('title', 'Untitled')
        genre = data.get('genre', 'General Fiction')
        description = data.get('description', '')
        num_chapters = data.get('num_chapters', 12)
        
        chapters = []
        outline_lines = [
            f"# {title} - Three-Act Structure",
            f"**Framework:** Classic Three-Act Structure",
            f"**Genre:** {genre}",
            f"**Premise:** {description}",
            "",
            "---",
            ""
        ]
        
        chapter_num = 1
        for act_key, act_data in ThreeActOutlineHandler.STRUCTURE.items():
            act_chapters = int(num_chapters * act_data['percentage'])
            if act_key == 'act3':
                act_chapters = num_chapters - chapter_num + 1  # Remaining chapters
            
            outline_lines.append(f"# ACT {act_key[-1]}: {act_data['name'].upper()}")
            outline_lines.append("")
            
            beats = act_data['beats']
            for i in range(act_chapters):
                beat = beats[i % len(beats)]
                
                chapters.append({
                    'number': chapter_num,
                    'title': beat['name'],
                    'beat': beat['name'],
                    'outline': beat['description'],
                    'act': int(act_key[-1]),
                    'target_words': 2000
                })
                
                outline_lines.extend([
                    f"## Chapter {chapter_num}: {beat['name']}",
                    f"**Focus:** {beat['description']}",
                    ""
                ])
                
                chapter_num += 1
                if chapter_num > num_chapters:
                    break
        
        return {
            'success': True,
            'outline': "\n".join(outline_lines),
            'chapters': chapters,
            'beats': [{'beat': ch['beat'], 'act': ch['act']} for ch in chapters],
            'chapter_count': len(chapters),
            'framework': "Three-Act Structure"
        }


class OutlineContextExtractorHandler:
    """
    Extract context from project for outline generation
    
    Input:
    - project_id: int
    
    Output:
    - project_context: dict
    - character_context: dict
    - world_context: dict
    """
    
    @staticmethod
    def handle(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract context from project"""
        project_id = data.get('project_id')
        
        if not project_id:
            return {'success': False, 'error': 'project_id required'}
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return {'success': False, 'error': f'Project {project_id} not found'}
        
        from ..services.context_builder import ContextBuilder
        
        project_context = ContextBuilder.build_project_context(project)
        character_context = ContextBuilder.build_character_context(project)
        world_context = ContextBuilder.build_world_context(project)
        
        return {
            'success': True,
            'project_context': project_context,
            'character_context': character_context,
            'world_context': world_context
        }
