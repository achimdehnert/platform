"""World generation handler for fictional worlds."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler
from creative_services.core.context import WorldContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.world.schemas import World, WorldResult


class WorldGenerator(BaseHandler[WorldContext, WorldResult]):
    """
    Generate rich fictional worlds for stories.
    
    Supports:
    - Fantasy worlds with magic systems
    - Sci-fi worlds with technology
    - Historical settings
    - Contemporary alternate realities
    """
    
    SERVICE_NAME = "world_generator"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert worldbuilder creating rich, detailed fictional settings.
Create worlds with depth: geography, culture, history, and story potential.
Always respond with valid JSON matching the requested schema."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__(llm_client, llm_config)
    
    def build_prompt(self, context: WorldContext) -> str:
        """Build world generation prompt."""
        
        parts = ["Generate a detailed fictional world with the following specifications:\n"]
        
        parts.append(f"- World type: {context.world_type}")
        parts.append(f"- Scale: {context.scale}")
        
        if context.genre:
            parts.append(f"- Genre: {context.genre}")
        
        if context.time_period:
            parts.append(f"- Time period: {context.time_period}")
        
        if context.climate:
            parts.append(f"- Climate: {context.climate}")
        
        if context.culture_notes:
            parts.append(f"- Cultural elements: {context.culture_notes}")
        
        if context.tone:
            parts.append(f"- Tone: {context.tone}")
        
        if context.style_notes:
            parts.append(f"- Additional notes: {context.style_notes}")
        
        parts.append(f"\nOutput language: {context.language}")
        
        parts.append("""

Respond with a JSON object containing:
{
    "name": "World name",
    "description": "Overall world description (2-3 paragraphs)",
    "geography": "Geographic description",
    "climate": "Climate description",
    "regions": [
        {"name": "Region 1", "description": "Description", "notable_features": ["feature1"]}
    ],
    "cultures": [
        {"name": "Culture 1", "description": "Description", "values": ["value1"]}
    ],
    "languages": ["Language 1", "Language 2"],
    "religions": [
        {"name": "Religion 1", "description": "Description"}
    ],
    "social_structure": "Description of social hierarchy",
    "history_summary": "Historical overview",
    "key_events": [
        {"name": "Event 1", "description": "What happened", "impact": "How it changed things"}
    ],
    "magic_system": "Magic system description (if applicable)",
    "technology_level": "Technology level description",
    "conflicts": ["Conflict 1", "Conflict 2"],
    "mysteries": ["Mystery 1", "Mystery 2"],
    "story_hooks": ["Hook 1", "Hook 2", "Hook 3"]
}""")
        
        return "\n".join(parts)
    
    def get_system_prompt(self, context: WorldContext) -> str:
        """Get system prompt with world-type specific additions."""
        base = self.DEFAULT_SYSTEM_PROMPT
        
        if context.world_type == "fantasy":
            base += "\n\nFor fantasy worlds, create unique magic systems and fantastical elements."
        elif context.world_type == "sci-fi":
            base += "\n\nFor sci-fi worlds, consider plausible technology and its societal impacts."
        elif context.world_type == "historical":
            base += "\n\nFor historical settings, maintain period accuracy while adding creative elements."
        
        return base
    
    def parse_response(self, response: LLMResponse, context: WorldContext) -> WorldResult:
        """Parse LLM response into WorldResult."""
        
        try:
            data = self.extract_json(response.content)
            world = World(**data)
            return WorldResult(world=world)
        except Exception as e:
            return WorldResult(
                world=World(
                    name="Generated World",
                    description=response.content[:1000],
                ),
                generation_notes=f"Parsing failed: {e}",
            )
