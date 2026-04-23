"""Character generation handler."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler, HandlerResult
from creative_services.core.context import CharacterContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.character.schemas import Character, CharacterResult


class CharacterGenerator(BaseHandler[CharacterContext, CharacterResult]):
    """
    Generate rich, detailed characters for stories.
    
    Supports:
    - Fiction characters (fantasy, sci-fi, etc.)
    - Travel story characters (travelers, locals, guides)
    - Various roles (protagonist, antagonist, supporting)
    """
    
    SERVICE_NAME = "character_generator"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert character creator for fiction and travel stories.
Create rich, believable characters with depth, motivation, and distinctive traits.
Always respond with valid JSON matching the requested schema."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__(llm_client, llm_config)
    
    def build_prompt(self, context: CharacterContext) -> str:
        """Build character generation prompt."""
        
        parts = ["Generate a detailed character with the following specifications:\n"]
        
        if context.genre:
            parts.append(f"- Genre: {context.genre}")
        
        parts.append(f"- Role: {context.role}")
        
        if context.traits:
            parts.append(f"- Required traits: {', '.join(context.traits)}")
        
        if context.age_range:
            parts.append(f"- Age range: {context.age_range}")
        
        if context.gender:
            parts.append(f"- Gender: {context.gender}")
        
        if context.occupation:
            parts.append(f"- Occupation: {context.occupation}")
        
        if context.backstory_hints:
            parts.append(f"- Backstory elements: {context.backstory_hints}")
        
        if context.tone:
            parts.append(f"- Tone: {context.tone}")
        
        if context.style_notes:
            parts.append(f"- Additional notes: {context.style_notes}")
        
        parts.append(f"\nOutput language: {context.language}")
        
        parts.append("""
        
Respond with a JSON object containing:
{
    "name": "Full name",
    "age": 30,
    "gender": "male/female/other",
    "role": "protagonist/antagonist/supporting/mentor/etc",
    "personality": "Detailed personality description",
    "traits": ["trait1", "trait2", "trait3"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "backstory": "Character backstory paragraph",
    "motivation": "Core motivation driving the character",
    "goals": ["goal1", "goal2"],
    "fears": ["fear1", "fear2"],
    "appearance": "Physical appearance description",
    "distinctive_features": ["feature1", "feature2"],
    "speech_pattern": "How they speak",
    "mannerisms": ["mannerism1", "mannerism2"],
    "portrait_prompt": "Detailed prompt for generating character portrait"
}""")
        
        return "\n".join(parts)
    
    def get_system_prompt(self, context: CharacterContext) -> str:
        """Get system prompt with genre-specific additions."""
        base = self.DEFAULT_SYSTEM_PROMPT
        
        if context.genre == "travel":
            base += "\n\nFor travel stories, create characters that feel authentic to their location and culture."
        elif context.genre == "fantasy":
            base += "\n\nFor fantasy, create characters with unique magical or fantastical elements."
        elif context.genre == "sci-fi":
            base += "\n\nFor sci-fi, consider technological and futuristic elements in the character."
        
        return base
    
    def parse_response(self, response: LLMResponse, context: CharacterContext) -> CharacterResult:
        """Parse LLM response into CharacterResult."""
        
        try:
            data = self.extract_json(response.content)
            character = Character(**data)
            return CharacterResult(character=character)
        except Exception as e:
            # Fallback: create basic character from text
            return CharacterResult(
                character=Character(
                    name="Generated Character",
                    role=context.role,
                    personality=response.content[:500],
                    traits=context.traits or ["mysterious"],
                ),
                generation_notes=f"Parsing failed, used fallback: {e}",
            )


class TravelCharacterGenerator(CharacterGenerator):
    """
    Specialized generator for travel story characters.
    
    Creates:
    - Travelers with realistic motivations
    - Local guides and residents
    - Fellow tourists and companions
    """
    
    SERVICE_NAME = "travel_character_generator"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert character creator for travel stories.
Create characters that feel authentic to travel experiences:
- Travelers seeking adventure, escape, or self-discovery
- Locals with rich cultural knowledge
- Fellow travelers with interesting backgrounds
Always respond with valid JSON."""
    
    def build_prompt(self, context: CharacterContext) -> str:
        """Build travel-specific character prompt."""

        # Use a copy with travel genre if not specified
        if not context.genre:
            context = context.model_copy(update={"genre": "travel"})

        base_prompt = super().build_prompt(context)
        
        travel_additions = """

For travel characters, also consider:
- Their travel style (backpacker, luxury, adventure, cultural)
- What they're seeking from travel (escape, growth, connection, adventure)
- Their relationship with their home culture
- Languages they speak
- Travel experiences that shaped them"""
        
        return base_prompt + travel_additions
