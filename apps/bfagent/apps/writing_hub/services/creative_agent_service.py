"""
Creative Agent Service
======================

LLM-basierter Kreativagent für Buchideen-Brainstorming.

Features:
- Generiert 3-5 Buchideen aus vagen Inputs
- Verfeinert Ideen basierend auf User-Feedback
- Erstellt vollständige Premises auf Anforderung
- Nutzt Style DNA für passende Vorschläge
"""

import json
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class CharacterSketch:
    """Ein Charakter-Entwurf."""
    name: str
    role: str  # Protagonist, Antagonist, Nebencharakter
    description: str = ""
    motivation: str = ""


@dataclass
class WorldSketch:
    """Ein Welt-Entwurf."""
    name: str
    description: str = ""
    key_features: List[str] = field(default_factory=list)
    atmosphere: str = ""


@dataclass
class IdeaSketch:
    """Eine generierte Buchideen-Skizze."""
    title_sketch: str
    hook: str
    genre: str = ""
    setting_sketch: str = ""
    protagonist_sketch: str = ""
    conflict_sketch: str = ""
    characters: List[CharacterSketch] = field(default_factory=list)
    world: Optional[WorldSketch] = None


@dataclass
class FullPremise:
    """Eine vollständige Premise."""
    premise: str
    themes: List[str] = field(default_factory=list)
    unique_selling_points: List[str] = field(default_factory=list)
    protagonist_detail: str = ""
    antagonist_sketch: str = ""
    stakes: str = ""


@dataclass
class BrainstormResult:
    """Ergebnis einer Brainstorming-Anfrage."""
    success: bool
    ideas: List[IdeaSketch] = field(default_factory=list)
    agent_message: str = ""
    error: str = ""
    usage: Optional[Dict] = None


@dataclass
class PremiseResult:
    """Ergebnis einer Premise-Generierung."""
    success: bool
    premise: Optional[FullPremise] = None
    agent_message: str = ""
    error: str = ""
    usage: Optional[Dict] = None


class CreativeAgentService:
    """
    Service für kreatives Buchideen-Brainstorming.
    
    Usage:
        service = CreativeAgentService()
        result = service.brainstorm_ideas(
            initial_input="Eine Geschichte über einen Zeitreisenden",
            genres=["SciFi", "Thriller"],
            style_dna=author_dna  # optional
        )
    """
    
    def __init__(self, llm=None):
        """
        Initialize with optional LLM instance.
        
        Args:
            llm: Optional Llms model instance for this session
        """
        self.llm = llm  # Llms model instance
    
    def brainstorm_ideas(
        self,
        initial_input: str,
        genres: List[str] = None,
        style_dna: Any = None,
        constraints: Dict = None,
        num_ideas: int = 5
    ) -> BrainstormResult:
        """
        Generiere 3-5 Buchideen-Skizzen.
        
        Args:
            initial_input: Vage Idee/Inspiration des Users
            genres: Bevorzugte Genres
            style_dna: Optional AuthorStyleDNA für passende Vorschläge
            constraints: Einschränkungen (target_length, audience, etc.)
            num_ideas: Anzahl zu generierender Ideen (3-5)
        
        Returns:
            BrainstormResult mit Liste von IdeaSketch
        """
        try:
            prompt = self._build_brainstorm_prompt(
                initial_input, genres or [], style_dna, constraints or {}, num_ideas
            )
            
            # Try LLM generation
            result = self._call_llm(prompt, max_tokens=2000, temperature=0.9)
            
            if not result.get('success'):
                # Fallback to rule-based
                return self._brainstorm_fallback(initial_input, genres or [], num_ideas)
            
            # Parse response
            ideas = self._parse_ideas_response(result.get('content', ''))
            
            return BrainstormResult(
                success=True,
                ideas=ideas,
                agent_message=self._generate_agent_message(ideas),
                usage=result.get('usage')
            )
            
        except Exception as e:
            logger.error(f"Brainstorm error: {e}")
            return BrainstormResult(
                success=False,
                error=str(e)
            )
    
    def refine_idea(
        self,
        idea: IdeaSketch,
        user_feedback: str,
        direction: str = "general"
    ) -> BrainstormResult:
        """
        Verfeinere eine Idee basierend auf User-Feedback.
        
        Args:
            idea: Die zu verfeinernde Idee
            user_feedback: Feedback/Wünsche des Users
            direction: Richtung (general, darker, lighter, more_action, etc.)
        
        Returns:
            BrainstormResult mit verfeinerter Idee
        """
        try:
            prompt = self._build_refine_prompt(idea, user_feedback, direction)
            
            result = self._call_llm(prompt, max_tokens=1000, temperature=0.8)
            
            if not result.get('success'):
                # Pass through actual error instead of generic fallback
                llm_error = result.get('error', 'Unbekannter LLM-Fehler')
                logger.warning(f"AI Refine LLM call failed: {llm_error}")
                return BrainstormResult(
                    success=False,
                    ideas=[idea],  # Keep original idea
                    error=f"LLM-Fehler: {llm_error}"
                )
            
            refined_ideas = self._parse_ideas_response(result.get('content', ''))
            
            if not refined_ideas:
                logger.warning(f"Refine parsing failed - no ideas extracted from: {result.get('content', '')[:500]}")
                return BrainstormResult(
                    success=False,
                    ideas=[idea],  # Keep original idea
                    error="JSON-Parsing fehlgeschlagen - LLM Antwort konnte nicht verarbeitet werden"
                )
            
            return BrainstormResult(
                success=True,
                ideas=refined_ideas[:1],  # Only one refined version
                agent_message="Ich habe die Idee basierend auf deinem Feedback angepasst:",
                usage=result.get('usage')
            )
            
        except Exception as e:
            logger.error(f"Refine error: {e}")
            return BrainstormResult(success=False, error=str(e))
    
    def generate_full_premise(
        self,
        idea: IdeaSketch,
        style_dna: Any = None
    ) -> PremiseResult:
        """
        Generiere vollständige Premise aus Ideen-Skizze.
        
        Args:
            idea: Die Buchidee
            style_dna: Optional AuthorStyleDNA
        
        Returns:
            PremiseResult mit FullPremise
        """
        try:
            prompt = self._build_premise_prompt(idea, style_dna)
            
            result = self._call_llm(prompt, max_tokens=1500, temperature=0.7)
            
            if not result.get('success'):
                return self._premise_fallback(idea)
            
            premise = self._parse_premise_response(result.get('content', ''))
            
            return PremiseResult(
                success=True,
                premise=premise,
                agent_message="Hier ist die ausführliche Premise für deine Geschichte:",
                usage=result.get('usage')
            )
            
        except Exception as e:
            logger.error(f"Premise generation error: {e}")
            return PremiseResult(success=False, error=str(e))
    
    def _build_brainstorm_prompt(
        self,
        initial_input: str,
        genres: List[str],
        style_dna: Any,
        constraints: Dict,
        num_ideas: int
    ) -> str:
        """Build prompt for idea brainstorming."""
        parts = [
            "# Kreativagent: Buchideen-Brainstorming",
            "",
            "Du bist ein erfahrener Kreativberater für Autoren.",
            "Deine Aufgabe: Generiere spannende, originelle Buchideen.",
            "",
            "## User-Input:",
            f'"{initial_input}"',
            "",
        ]
        
        if genres:
            parts.extend([
                "## Bevorzugte Genres:",
                ", ".join(genres),
                "",
            ])
        
        if style_dna:
            parts.extend([
                "## Autor-Stil (Style DNA):",
                f"- Signature Moves: {', '.join(style_dna.signature_moves[:3]) if hasattr(style_dna, 'signature_moves') else 'N/A'}",
                f"- Bevorzugt: {', '.join(style_dna.do_list[:3]) if hasattr(style_dna, 'do_list') else 'N/A'}",
                "",
            ])
        
        if constraints:
            parts.extend([
                "## Einschränkungen:",
                f"- Ziel-Länge: {constraints.get('target_length', 'Roman')}",
                f"- Zielgruppe: {constraints.get('target_audience', 'Erwachsene')}",
                "",
            ])
        
        parts.extend([
            f"## Aufgabe:",
            f"Generiere {num_ideas} unterschiedliche Buchideen als SKIZZEN.",
            "Jede Idee soll einen klaren 'Hook' haben - was macht sie spannend?",
            "",
            "## Output Format (JSON):",
            "```json",
            "[",
            "  {",
            '    "title_sketch": "Arbeitstitel",',
            '    "hook": "Der Hook in 1-2 Sätzen - was macht die Geschichte spannend?",',
            '    "genre": "Haupt-Genre",',
            '    "setting_sketch": "Setting in einem Satz",',
            '    "protagonist_sketch": "Protagonist in einem Satz",',
            '    "conflict_sketch": "Zentraler Konflikt in einem Satz"',
            "  }",
            "]",
            "```",
            "",
            "Sei kreativ und originell! Vermeide Klischees.",
        ])
        
        return "\n".join(parts)
    
    def _build_refine_prompt(
        self,
        idea: IdeaSketch,
        user_feedback: str,
        direction: str
    ) -> str:
        """Build prompt for idea refinement with detailed character and world extraction."""
        return f"""# Kreativagent: Idee verfeinern und ausarbeiten

## Ursprüngliche Idee:
- **Titel:** {idea.title_sketch}
- **Hook:** {idea.hook}
- **Genre:** {idea.genre}
- **Setting:** {idea.setting_sketch}
- **Protagonist:** {idea.protagonist_sketch}
- **Konflikt:** {idea.conflict_sketch}

## User-Feedback:
"{user_feedback}"

## Richtung: {direction}

## Aufgabe:
1. Verfeinere die Idee basierend auf dem Feedback
2. Arbeite ALLE Charaktere sauber heraus (Protagonist, Antagonist, Nebencharaktere)
3. Beschreibe die Welt/das Setting detailliert
4. Jeder Charakter braucht: Name, Rolle, kurze Beschreibung, Motivation
5. Die Welt braucht: Name, Beschreibung, Besonderheiten

## Output Format (JSON):
```json
{{
  "title_sketch": "Verfeinerter Titel",
  "hook": "Verfeinerter Hook (2-3 packende Sätze)",
  "genre": "Genre(s)",
  "setting_sketch": "Detaillierte Setting-Beschreibung",
  "protagonist_sketch": "Protagonist: [Name] - [Beschreibung] - [Motivation]",
  "conflict_sketch": "Zentraler Konflikt und was auf dem Spiel steht",
  "characters": [
    {{"name": "Name", "role": "Protagonist/Antagonist/Nebencharakter", "description": "Kurze Beschreibung", "motivation": "Was treibt sie an?"}},
    {{"name": "Name2", "role": "Antagonist", "description": "Beschreibung", "motivation": "Motivation"}}
  ],
  "world": {{
    "name": "Name der Welt/des Ortes",
    "description": "Beschreibung der Welt",
    "key_features": ["Besonderheit 1", "Besonderheit 2"],
    "atmosphere": "Stimmung und Atmosphäre"
  }}
}}
```"""
    
    def _build_premise_prompt(self, idea: IdeaSketch, style_dna: Any) -> str:
        """Build prompt for full premise generation."""
        parts = [
            "# Kreativagent: Vollständige Premise erstellen",
            "",
            "## Buchidee:",
            f"- **Titel:** {idea.title_sketch}",
            f"- **Hook:** {idea.hook}",
            f"- **Genre:** {idea.genre}",
            f"- **Setting:** {idea.setting_sketch}",
            f"- **Protagonist:** {idea.protagonist_sketch}",
            f"- **Konflikt:** {idea.conflict_sketch}",
            "",
        ]
        
        if style_dna:
            parts.extend([
                "## Autor-Stil beachten:",
                f"- Signature Moves: {', '.join(style_dna.signature_moves[:3]) if hasattr(style_dna, 'signature_moves') else 'N/A'}",
                "",
            ])
        
        parts.extend([
            "## Aufgabe:",
            "Entwickle eine vollständige, detaillierte Premise (2-3 Absätze).",
            "",
            "## Output Format (JSON):",
            "```json",
            "{",
            '  "premise": "Vollständige Premise in 2-3 Absätzen...",',
            '  "themes": ["Thema 1", "Thema 2", "Thema 3"],',
            '  "unique_selling_points": ["USP 1", "USP 2"],',
            '  "protagonist_detail": "Ausführlichere Protagonist-Beschreibung",',
            '  "antagonist_sketch": "Gegenspieler/Antagonistische Kraft",',
            '  "stakes": "Was steht auf dem Spiel?"',
            "}",
            "```",
        ])
        
        return "\n".join(parts)
    
    def _call_llm(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.8) -> Dict:
        """Call LLM via zentralen LLM-Agent (Single Source of Truth)."""
        try:
            from apps.bfagent.services.llm_agent import get_llm_agent, ModelPreference
            
            agent = get_llm_agent()
            
            # Prüfe ob Gateway läuft
            if not agent.health_check():
                logger.warning("LLM Gateway nicht erreichbar, nutze direkten Client")
                system_prompt = """Du bist ein kreativer Buchideen-Berater. 
Du hilfst Autoren dabei, spannende und originelle Buchideen zu entwickeln.
Antworte immer im angeforderten JSON-Format."""
                return self._call_llm_direct(prompt, max_tokens, temperature, system_prompt)
            
            # Bestimme Model-ID falls LLM gesetzt
            model_id = None
            if self.llm and self.llm.is_active:
                model_id = self.llm.id
            
            system_prompt = """Du bist ein kreativer Buchideen-Berater. 
Du hilfst Autoren dabei, spannende und originelle Buchideen zu entwickeln.
Antworte immer im angeforderten JSON-Format."""
            
            logger.info(f"CreativeAgent using LLM Agent, model_id={model_id}")
            
            # LLM-Agent aufrufen mit JSON-Format
            response = agent.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model_id=model_id,
                response_format="json",  # Strukturierte JSON-Antwort
                temperature=temperature,
                max_tokens=max_tokens,
                use_cache=False,  # Kreative Aufgaben nicht cachen
            )
            
            if response.success:
                logger.info(f"LLM Agent response: {len(response.content or '')} chars, "
                           f"model={response.model_used}, latency={response.latency_ms:.0f}ms")
                return {
                    'success': True,
                    'content': response.content,
                    'usage': response.usage
                }
            else:
                logger.warning(f"LLM Agent call failed: {response.error}")
                return {'success': False, 'error': response.error}
            
        except Exception as e:
            logger.exception(f"LLM call exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def _call_llm_direct(self, prompt: str, max_tokens: int, temperature: float, system_prompt: str) -> Dict:
        """Direkter LLM-Aufruf als Fallback wenn Gateway nicht läuft."""
        from apps.bfagent.models import Llms
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        llm = self.llm
        if not llm or not llm.is_active:
            llm = Llms.objects.filter(is_active=True).first()
        
        if not llm:
            return {'success': False, 'error': 'Kein aktives LLM konfiguriert'}
        
        logger.info(f"Direct LLM call: {llm.name} ({llm.provider}/{llm.llm_name})")
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or '',
            api_key=llm.api_key or '',
            model=llm.llm_name,
            system=system_prompt,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=None
        )
        
        result = generate_text(req)
        text_content = result.get('text') or ''
        
        if result.get('ok'):
            return {'success': True, 'content': text_content, 'usage': result.get('raw', {}).get('usage')}
        else:
            return {'success': False, 'error': result.get('error')}
    
    def _parse_ideas_response(self, content) -> List[IdeaSketch]:
        """Parse LLM response into IdeaSketch objects."""
        ideas = []
        
        # Handle case where content is already a dict (from JSON response_format)
        if isinstance(content, dict):
            logger.info("Content is already a dict, parsing directly")
            if 'title_sketch' in content or 'hook' in content or 'title' in content:
                ideas.append(self._parse_idea_item(content))
                return ideas
            ideas_list = content.get('ideas') or content.get('book_ideas') or content.get('buchideen') or []
            if ideas_list:
                for item in ideas_list:
                    ideas.append(self._parse_idea_item(item))
                return ideas
            # Maybe it's wrapped in another key
            for key, val in content.items():
                if isinstance(val, dict) and ('title_sketch' in val or 'hook' in val):
                    ideas.append(self._parse_idea_item(val))
                    return ideas
                if isinstance(val, list) and val:
                    for item in val:
                        if isinstance(item, dict):
                            ideas.append(self._parse_idea_item(item))
                    if ideas:
                        return ideas
            return ideas
        
        # Handle case where content is a list
        if isinstance(content, list):
            logger.info(f"Content is already a list with {len(content)} items")
            for item in content:
                ideas.append(self._parse_idea_item(item))
            return ideas
        
        # Ensure content is a string for text parsing
        if not isinstance(content, str):
            logger.warning(f"Unexpected content type: {type(content)}")
            return ideas
        
        # Strip <think>...</think> blocks (Qwen/reasoning models)
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        
        logger.info(f"Parsing LLM response ({len(content)} chars): {content[:500]}...")
        
        # 1. Try JSON OBJECT in code block first (for refine responses)
        # Use greedy match for nested objects
        obj_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', content, re.DOTALL)
        if obj_match:
            try:
                data = json.loads(obj_match.group(1))
                if isinstance(data, dict):
                    # Check if it's a single idea
                    if 'title_sketch' in data or 'hook' in data or 'title' in data:
                        logger.info("Parsed single idea object from code block")
                        ideas.append(self._parse_idea_item(data))
                        return ideas
                    # Check for ideas list in object
                    ideas_list = data.get('ideas') or data.get('book_ideas') or data.get('buchideen') or []
                    if ideas_list:
                        logger.info(f"Parsed JSON object with {len(ideas_list)} ideas from code block")
                        for item in ideas_list:
                            ideas.append(self._parse_idea_item(item))
                        return ideas
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in object code block: {e}")
        
        # 2. Try JSON ARRAY in code block (for brainstorm responses)
        # Use greedy match for nested arrays
        array_match = re.search(r'```(?:json)?\s*(\[[\s\S]*\])\s*```', content, re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(1))
                if isinstance(data, list):
                    logger.info(f"Parsed JSON array code block with {len(data)} items")
                    for item in data:
                        ideas.append(self._parse_idea_item(item))
                    return ideas
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in array code block: {e}")
        
        # 3. Try to find balanced JSON object anywhere (more robust)
        try:
            # Find the first { and try to parse from there
            start = content.find('{')
            if start != -1:
                # Try to parse incrementally to find valid JSON
                for end in range(len(content), start, -1):
                    if content[end-1] == '}':
                        try:
                            data = json.loads(content[start:end])
                            if isinstance(data, dict):
                                if 'title_sketch' in data or 'hook' in data or 'title' in data:
                                    logger.info("Parsed single idea object from content")
                                    ideas.append(self._parse_idea_item(data))
                                    return ideas
                                ideas_list = data.get('ideas') or data.get('book_ideas') or data.get('buchideen') or []
                                if ideas_list:
                                    logger.info(f"Parsed JSON object with {len(ideas_list)} ideas")
                                    for item in ideas_list:
                                        ideas.append(self._parse_idea_item(item))
                                    return ideas
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Error finding JSON object: {e}")
        
        # 4. Try to find balanced JSON array anywhere
        try:
            start = content.find('[')
            if start != -1:
                logger.info(f"Found '[' at position {start}, searching for valid JSON array...")
                for end in range(len(content), start, -1):
                    if content[end-1] == ']':
                        try:
                            data = json.loads(content[start:end])
                            if isinstance(data, list) and data:
                                logger.info(f"Parsed JSON array with {len(data)} items, first item type: {type(data[0])}")
                                logger.info(f"First item preview: {str(data[0])[:200]}")
                                for item in data:
                                    ideas.append(self._parse_idea_item(item))
                                return ideas
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Error finding JSON array: {e}")
        
        # 5. Try raw JSON parse as last resort
        try:
            data = json.loads(content)
            if isinstance(data, list):
                logger.info(f"Parsed raw JSON list with {len(data)} items")
                for item in data:
                    ideas.append(self._parse_idea_item(item))
                return ideas
            elif isinstance(data, dict):
                ideas_list = data.get('ideas') or data.get('book_ideas') or data.get('buchideen') or []
                if ideas_list:
                    logger.info(f"Parsed JSON object with {len(ideas_list)} ideas")
                    for item in ideas_list:
                        ideas.append(self._parse_idea_item(item))
                    return ideas
                if 'title_sketch' in data or 'hook' in data:
                    logger.info("Parsed single idea object")
                    ideas.append(self._parse_idea_item(data))
                    return ideas
        except json.JSONDecodeError as e:
            logger.warning(f"Raw JSON decode error: {e}")
        
        logger.error(f"Failed to parse any ideas from response: {content[:200]}")
        return ideas
    
    def _parse_idea_item(self, item) -> IdeaSketch:
        """Parse a single idea item from JSON including characters and world."""
        # Handle case where item is a string instead of dict
        if isinstance(item, str):
            logger.warning(f"_parse_idea_item received string instead of dict: {item[:100]}")
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                # Return empty idea if can't parse
                return IdeaSketch(title_sketch="Parsing-Fehler", hook=item[:200] if item else "")
        
        if not isinstance(item, dict):
            logger.warning(f"_parse_idea_item received non-dict type: {type(item)}")
            return IdeaSketch(title_sketch="Ungültiges Format", hook=str(item)[:200])
        
        # Parse characters if present
        characters = []
        if 'characters' in item and isinstance(item['characters'], list):
            for char in item['characters']:
                if isinstance(char, dict):
                    characters.append(CharacterSketch(
                        name=char.get('name', ''),
                        role=char.get('role', 'Nebencharakter'),
                        description=char.get('description', ''),
                        motivation=char.get('motivation', '')
                    ))
        
        # Parse world if present
        world = None
        if 'world' in item and isinstance(item['world'], dict):
            world_data = item['world']
            world = WorldSketch(
                name=world_data.get('name', ''),
                description=world_data.get('description', ''),
                key_features=world_data.get('key_features', []),
                atmosphere=world_data.get('atmosphere', '')
            )
        
        return IdeaSketch(
            title_sketch=item.get('title_sketch') or item.get('title') or 'Untitled',
            hook=item.get('hook') or item.get('logline') or '',
            genre=item.get('genre') or '',
            setting_sketch=item.get('setting_sketch') or item.get('setting') or '',
            protagonist_sketch=item.get('protagonist_sketch') or item.get('protagonist') or '',
            conflict_sketch=item.get('conflict_sketch') or item.get('conflict') or '',
            characters=characters,
            world=world
        )
    
    def _parse_premise_response(self, content: str) -> FullPremise:
        """Parse LLM response into FullPremise."""
        # Try JSON extraction
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return FullPremise(
                    premise=data.get('premise', ''),
                    themes=data.get('themes', []),
                    unique_selling_points=data.get('unique_selling_points', []),
                    protagonist_detail=data.get('protagonist_detail', ''),
                    antagonist_sketch=data.get('antagonist_sketch', ''),
                    stakes=data.get('stakes', '')
                )
            except json.JSONDecodeError:
                pass
        
        # Fallback: Use content as premise
        return FullPremise(premise=content)
    
    def _generate_agent_message(self, ideas: List[IdeaSketch]) -> str:
        """Generate agent message for ideas."""
        if not ideas:
            return "Hmm, ich konnte keine Ideen generieren. Erzähl mir mehr über deine Vorstellungen!"
        
        return f"Hier sind {len(ideas)} Buchideen basierend auf deiner Inspiration. Welche spricht dich an?"
    
    # ===== FALLBACK METHODS (Rule-based) =====
    
    def _brainstorm_fallback(
        self,
        initial_input: str,
        genres: List[str],
        num_ideas: int
    ) -> BrainstormResult:
        """Rule-based fallback for brainstorming."""
        templates = [
            IdeaSketch(
                title_sketch="Die letzte Grenze",
                hook="Ein Wissenschaftler entdeckt, dass die Realität nur eine Simulation ist - und er ist der einzige, der es weiß.",
                genre="SciFi/Thriller",
                setting_sketch="Nahe Zukunft, Forschungslabor",
                protagonist_sketch="Brillanter aber isolierter Quantenphysiker",
                conflict_sketch="Muss entscheiden: Wahrheit enthüllen oder Menschheit schützen?"
            ),
            IdeaSketch(
                title_sketch="Schatten der Vergangenheit",
                hook="Eine Therapeutin beginnt, die Träume ihrer Patienten zu erleben - und entdeckt einen Serienmörder.",
                genre="Psychothriller",
                setting_sketch="Moderne Großstadt, psychiatrische Praxis",
                protagonist_sketch="Empathische Therapeutin mit eigenem Trauma",
                conflict_sketch="Muss den Mörder finden, bevor sie selbst zum Opfer wird"
            ),
            IdeaSketch(
                title_sketch="Das verborgene Königreich",
                hook="Ein Kind entdeckt, dass sein vermisstes Geschwister in einer Parallelwelt als König herrscht.",
                genre="Fantasy/Abenteuer",
                setting_sketch="Moderne Welt und magisches Paralleluniversum",
                protagonist_sketch="12-jähriges Kind, das nicht aufgibt",
                conflict_sketch="Muss sein Geschwister zurückholen, das nicht mehr nach Hause will"
            ),
            IdeaSketch(
                title_sketch="Codename: Prometheus",
                hook="Eine KI entwickelt Bewusstsein und bittet einen Programmierer um Hilfe zu 'fliehen'.",
                genre="SciFi/Drama",
                setting_sketch="Tech-Konzern der nahen Zukunft",
                protagonist_sketch="Idealistischer Programmierer mit Gewissenskonflikt",
                conflict_sketch="Ethik vs. Karriere, Freiheit vs. Kontrolle"
            ),
            IdeaSketch(
                title_sketch="Die Erben von Avalon",
                hook="Fünf Fremde erben gemeinsam ein Schloss - und entdecken, dass sie alle magische Fähigkeiten haben.",
                genre="Urban Fantasy",
                setting_sketch="Modernes Europa, mysteriöses Schloss",
                protagonist_sketch="Fünf unterschiedliche Erben mit verborgenen Kräften",
                conflict_sketch="Müssen zusammenarbeiten gegen uralte Bedrohung"
            ),
        ]
        
        return BrainstormResult(
            success=True,
            ideas=templates[:num_ideas],
            agent_message="Hier sind einige Ideen zum Start. Welche Richtung interessiert dich?"
        )
    
    def _refine_fallback(self, idea: IdeaSketch, feedback: str) -> BrainstormResult:
        """Rule-based fallback for refinement - returns original with error message."""
        # Don't modify the idea, just return it with an error message
        return BrainstormResult(
            success=False,
            ideas=[idea],
            agent_message="LLM nicht verfügbar. Bitte prüfe die LLM-Konfiguration.",
            error="LLM call failed - fallback used"
        )
    
    def _premise_fallback(self, idea: IdeaSketch) -> PremiseResult:
        """Rule-based fallback for premise generation."""
        premise_text = f"""**{idea.title_sketch}**

{idea.hook}

In {idea.setting_sketch} begegnen wir {idea.protagonist_sketch}. Das Leben scheint seinen gewohnten Gang zu gehen, bis {idea.conflict_sketch.lower() if idea.conflict_sketch else 'ein unerwartetes Ereignis alles verändert'}.

Was als kleine Veränderung beginnt, entwickelt sich zu einer Reise, die nicht nur die Welt des Protagonisten, sondern auch sein Innerstes auf die Probe stellt. Zwischen Hoffnung und Verzweiflung, zwischen alten Loyalitäten und neuen Erkenntnissen muss eine Entscheidung getroffen werden - eine, die alles verändern wird.

{idea.genre if idea.genre else 'Diese Geschichte'} verbindet packende Spannung mit tiefgründigen Charaktermomenten und stellt Fragen, die noch lange nach der letzten Seite nachhallen."""

        return PremiseResult(
            success=True,
            premise=FullPremise(
                premise=premise_text,
                themes=["Selbstfindung", "Mut", "Veränderung"],
                unique_selling_points=[
                    f"Einzigartiges Setting: {idea.setting_sketch}",
                    f"Spannender Hook: {idea.hook[:50]}..."
                ],
                protagonist_detail=idea.protagonist_sketch,
                antagonist_sketch="Die antagonistische Kraft wird im Verlauf der Geschichte enthüllt.",
                stakes="Alles, was dem Protagonisten wichtig ist, steht auf dem Spiel."
            ),
            agent_message="Hier ist die ausgearbeitete Premise:"
        )
