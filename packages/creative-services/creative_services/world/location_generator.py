"""Location profile generator for real-world places (Travel Beat)."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler
from creative_services.core.context import LocationContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.world.schemas import Location, LocationResult


class LocationGenerator(BaseHandler[LocationContext, LocationResult]):
    """
    Generate rich profiles for real-world locations.
    
    Designed for Travel Beat to create:
    - Atmospheric descriptions of places
    - Cultural and culinary highlights
    - Story opportunities for travel narratives
    """
    
    SERVICE_NAME = "location_generator"
    
    DEFAULT_SYSTEM_PROMPT = """You are a travel writer and cultural expert.
Create vivid, authentic profiles of real-world locations that inspire travel stories.
Include practical details alongside atmospheric descriptions.
Focus on elements that make great travel narrative moments.
Always respond with valid JSON matching the requested schema."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__(llm_client, llm_config)
    
    def build_prompt(self, context: LocationContext) -> str:
        """Build location profile prompt."""
        
        parts = [f"Generate a detailed travel profile for: {context.location_name}\n"]
        
        if context.country:
            parts.append(f"- Country: {context.country}")
        
        if context.region:
            parts.append(f"- Region: {context.region}")
        
        if context.season:
            parts.append(f"- Season: {context.season}")
        
        if context.tone:
            parts.append(f"- Tone: {context.tone}")
        
        include_sections = []
        if context.include_food:
            include_sections.append("culinary highlights")
        if context.include_culture:
            include_sections.append("local culture and customs")
        if context.include_activities:
            include_sections.append("activities and experiences")
        
        if include_sections:
            parts.append(f"- Focus on: {', '.join(include_sections)}")
        
        parts.append(f"\nOutput language: {context.language}")
        
        parts.append("""

Respond with a JSON object containing:
{
    "name": "Location name",
    "country": "Country",
    "region": "Region/State",
    "description": "Vivid description of the location (2-3 paragraphs)",
    "atmosphere": "The feel and vibe of the place",
    "highlights": ["Must-see 1", "Must-see 2", "Must-see 3"],
    "hidden_gems": ["Hidden gem 1", "Hidden gem 2"],
    "local_culture": "Description of local culture and people",
    "customs": ["Custom to know 1", "Custom to know 2"],
    "local_phrases": [
        {"phrase": "Local phrase", "meaning": "English meaning", "usage": "When to use"}
    ],
    "culinary_highlights": [
        {"name": "Dish name", "description": "What it is", "where_to_try": "Best places"}
    ],
    "restaurant_types": ["Type 1", "Type 2"],
    "activities": [
        {"name": "Activity", "description": "What you do", "best_for": "Type of traveler"}
    ],
    "best_time_to_visit": "Season or time recommendation",
    "story_opportunities": [
        "A chance encounter at the morning market",
        "Getting lost leads to discovery",
        "Sharing a meal with locals"
    ],
    "character_encounters": [
        "The friendly vendor who shares local secrets",
        "A fellow traveler with an interesting story"
    ],
    "visual_elements": ["Cobblestone streets", "Colorful facades", "Mountain backdrop"],
    "illustration_prompts": [
        "Sunset over the harbor with fishing boats",
        "Busy morning market with fresh produce"
    ]
}""")
        
        return "\n".join(parts)
    
    def parse_response(self, response: LLMResponse, context: LocationContext) -> LocationResult:
        """Parse LLM response into LocationResult."""
        
        try:
            data = self.extract_json(response.content)
            location = Location(**data)
            return LocationResult(location=location)
        except Exception as e:
            return LocationResult(
                location=Location(
                    name=context.location_name,
                    country=context.country,
                    description=response.content[:1000],
                ),
                generation_notes=f"Parsing failed: {e}",
            )
