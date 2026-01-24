"""
Scene Analyzer Handler - Uses BaseLLMHandler for standardized LLM access.
"""

from typing import Any, Dict, List, Optional

from apps.bfagent.handlers.base_llm_handler import BaseLLMHandler
from apps.bfagent.models import BookChapters


class SceneAnalyzerHandler(BaseLLMHandler):
    """Extracts visual scenes from text using LLM."""
    
    phase_name = 'illustration'  # For WorkflowPhaseLLMConfig
    
    SYSTEM_PROMPT = "Du extrahierst visuelle Szenen aus Text. Antworte nur mit JSON."
    
    USER_PROMPT = """Analysiere den Text und finde 2-4 visuell starke Szenen für Illustration.

TITEL: {title}
GENRE: {genre}
CHARAKTERE: {characters}

TEXT:
{content}

Antworte NUR mit JSON:
{{
  "scenes": [
    {{
      "title": "Szenen-Titel",
      "description": "Visuelle Beschreibung (was man SIEHT)",
      "characters": ["Name1"],
      "location": "Ort",
      "time_of_day": "day|night|morning|evening",
      "mood": "peaceful|dramatic|tense|romantic|action|dark|joyful",
      "composition": "Wide shot|Close-up|Medium shot"
    }}
  ],
  "best_scene_index": 0,
  "best_scene_reason": "Warum diese Szene am besten ist",
  "color_mood": "Farbstimmung",
  "atmosphere": "Atmosphäre"
}}"""
    
    def analyze_chapter(self, chapter_id: int) -> Dict[str, Any]:
        """Analyze a chapter by ID."""
        try:
            chapter = BookChapters.objects.select_related('project').get(id=chapter_id)
        except BookChapters.DoesNotExist:
            return {'success': False, 'error': 'Kapitel nicht gefunden'}
        
        project = chapter.project
        genre = getattr(project, 'genre', '') or ''
        characters = self._get_characters(project)
        
        return self.analyze(
            text=chapter.content or '',
            title=chapter.title or f"Kapitel {chapter.chapter_number}",
            genre=genre,
            characters=characters
        )
    
    def analyze(self, text: str, title: str = "", genre: str = "", 
                characters: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze text and extract visual scenes."""
        if len(text) < 100:
            return {'success': False, 'error': 'Text zu kurz (min. 100 Zeichen)'}
        
        prompt = self.USER_PROMPT.format(
            title=title or "Unbekannt",
            genre=genre or "Unbekannt",
            characters=', '.join(characters) if characters else "Keine",
            content=text[:8000]
        )
        
        result = self.call_llm(
            system=self.SYSTEM_PROMPT,
            prompt=prompt,
            parse_json=True
        )
        
        if result.get('success') and 'data' in result:
            # Flatten: move 'data' contents to top level
            data = result['data']
            data['success'] = True
            return data
        
        return result
    
    def _get_characters(self, project) -> List[str]:
        """Get character names from project."""
        try:
            from apps.writing_hub.models_prompt_system import PromptCharacter
            return list(PromptCharacter.objects.filter(
                project=project, is_active=True
            ).values_list('name', flat=True))
        except Exception:
            return []
