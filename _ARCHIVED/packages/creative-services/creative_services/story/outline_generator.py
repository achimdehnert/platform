"""Story outline generation handler."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler
from creative_services.core.context import StoryContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.story.schemas import Outline, OutlineSection, StoryResult


class OutlineGenerator(BaseHandler[StoryContext, StoryResult]):
    """
    Generate story outlines with various structures.
    
    Supports:
    - Three-Act Structure
    - Hero's Journey
    - Save the Cat
    - Travel narrative arc
    """
    
    SERVICE_NAME = "outline_generator"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert story architect creating compelling narrative structures.
Design outlines with strong dramatic arcs and character development.
Ensure each section serves the overall story and character growth.
Always respond with valid JSON matching the requested schema."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
        structure_type: str = "three_act",
    ):
        super().__init__(llm_client, llm_config)
        self.structure_type = structure_type
    
    def build_prompt(self, context: StoryContext) -> str:
        """Build outline generation prompt."""
        
        parts = ["Generate a story outline with the following specifications:\n"]
        
        if context.title:
            parts.append(f"Title: {context.title}")
        
        if context.premise:
            parts.append(f"Premise: {context.premise}")
        
        if context.genre:
            parts.append(f"Genre: {context.genre}")
        
        if context.tone:
            parts.append(f"Tone: {context.tone}")
        
        if context.characters:
            parts.append("\nMain Characters:")
            for char in context.characters:
                parts.append(f"  - {char.get('name', 'Unknown')}: {char.get('description', '')}")
        
        if context.world_summary:
            parts.append(f"\nSetting: {context.world_summary}")
        
        parts.append(f"\nStructure Type: {self.structure_type}")
        parts.append(f"Output Language: {context.language}")
        
        # Structure-specific guidance
        if self.structure_type == "three_act":
            parts.append(self._get_three_act_guidance())
        elif self.structure_type == "heros_journey":
            parts.append(self._get_heros_journey_guidance())
        elif self.structure_type == "travel":
            parts.append(self._get_travel_guidance())
        
        parts.append("""

Respond with a JSON object containing:
{
    "title": "Story title",
    "logline": "One-sentence hook",
    "premise": "Story premise paragraph",
    "structure_type": "three_act",
    "themes": ["Theme 1", "Theme 2"],
    "protagonist_arc": "How the protagonist changes",
    "central_conflict": "The main conflict",
    "sections": [
        {
            "number": 1,
            "title": "Section title",
            "summary": "What happens",
            "key_events": ["Event 1", "Event 2"],
            "characters_involved": ["Character 1"],
            "location": "Where it happens",
            "emotional_beat": "The emotional tone"
        }
    ]
}""")
        
        return "\n".join(parts)
    
    def _get_three_act_guidance(self) -> str:
        return """
        
Structure the outline in three acts:
- Act 1 (Setup ~25%): Introduce world, characters, inciting incident
- Act 2 (Confrontation ~50%): Rising action, complications, midpoint shift
- Act 3 (Resolution ~25%): Climax, falling action, resolution"""
    
    def _get_heros_journey_guidance(self) -> str:
        return """
        
Follow the Hero's Journey stages:
1. Ordinary World
2. Call to Adventure
3. Refusal of the Call
4. Meeting the Mentor
5. Crossing the Threshold
6. Tests, Allies, Enemies
7. Approach to Inmost Cave
8. Ordeal
9. Reward
10. The Road Back
11. Resurrection
12. Return with Elixir"""
    
    def _get_travel_guidance(self) -> str:
        return """
        
Structure as a travel narrative arc:
1. Departure - Why they're leaving, what they seek
2. Early Journey - First impressions, culture shock
3. Deepening - Going beneath surface, real connections
4. Challenge - The difficult moment, questioning
5. Transformation - The shift in perspective
6. Return/Forward - Changed by the journey"""
    
    def parse_response(self, response: LLMResponse, context: StoryContext) -> StoryResult:
        """Parse LLM response into StoryResult with Outline."""
        
        try:
            data = self.extract_json(response.content)
            
            # Parse sections
            sections = []
            for s in data.get("sections", []):
                sections.append(OutlineSection(**s))
            
            outline = Outline(
                title=data.get("title", context.title or "Untitled"),
                logline=data.get("logline", ""),
                premise=data.get("premise", context.premise or ""),
                structure_type=data.get("structure_type", self.structure_type),
                sections=sections,
                themes=data.get("themes", []),
                protagonist_arc=data.get("protagonist_arc"),
                central_conflict=data.get("central_conflict"),
            )
            
            return StoryResult(outline=outline)
            
        except Exception as e:
            return StoryResult(
                outline=Outline(
                    title=context.title or "Untitled",
                    premise=response.content[:500],
                ),
                generation_notes=f"Parsing failed: {e}",
            )
