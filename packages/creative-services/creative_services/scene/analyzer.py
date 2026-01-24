"""Scene analysis handler for illustration extraction."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler
from creative_services.core.context import SceneContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.scene.schemas import Scene, SceneAnalysisResult


class SceneAnalyzer(BaseHandler[SceneContext, SceneAnalysisResult]):
    """
    Analyze text to extract scenes suitable for illustration.
    
    Features:
    - Identifies visually compelling moments
    - Generates illustration prompts
    - Ranks scenes by illustration potential
    """
    
    SERVICE_NAME = "scene_analyzer"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert at visual storytelling and illustration direction.
Analyze text to identify the most visually compelling scenes.
Create detailed illustration prompts that capture the essence of each scene.
Consider composition, mood, lighting, and visual impact.
Always respond with valid JSON matching the requested schema."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__(llm_client, llm_config)
    
    def build_prompt(self, context: SceneContext) -> str:
        """Build scene analysis prompt."""
        
        parts = [f"Analyze the following text and extract up to {context.max_scenes} scenes suitable for illustration:\n"]
        
        parts.append(f"---\n{context.text}\n---\n")
        
        if context.genre:
            parts.append(f"Genre: {context.genre}")
        
        if context.characters:
            parts.append(f"Known characters: {', '.join(context.characters)}")
        
        if context.locations:
            parts.append(f"Known locations: {', '.join(context.locations)}")
        
        parts.append(f"\nOutput language: {context.language}")
        
        if context.for_illustration:
            parts.append("\nFocus on scenes that would make compelling illustrations.")
        
        parts.append("""

Respond with a JSON object containing:
{
    "scenes": [
        {
            "title": "Scene title",
            "description": "What's happening in this scene",
            "location": "Where it takes place",
            "time_of_day": "morning/afternoon/evening/night",
            "weather": "Weather or atmosphere",
            "characters": ["Character 1", "Character 2"],
            "character_actions": ["What Character 1 is doing", "What Character 2 is doing"],
            "mood": "The emotional mood",
            "tension_level": "low/medium/high",
            "key_visual_elements": ["Element 1", "Element 2"],
            "colors": ["Dominant color 1", "Dominant color 2"],
            "lighting": "Lighting description",
            "illustration_prompt": "Detailed prompt for generating an illustration of this scene. Include composition, style, mood, and specific visual details.",
            "style_suggestions": ["Art style 1", "Art style 2"],
            "importance_score": 0.8
        }
    ],
    "best_scene_index": 0
}

Order scenes by importance_score (highest first).
The best_scene_index should point to the most illustration-worthy scene.""")
        
        return "\n".join(parts)
    
    def parse_response(self, response: LLMResponse, context: SceneContext) -> SceneAnalysisResult:
        """Parse LLM response into SceneAnalysisResult."""
        
        try:
            data = self.extract_json(response.content)
            
            scenes = []
            for s in data.get("scenes", [])[:context.max_scenes]:
                scenes.append(Scene(**s))
            
            # Sort by importance score
            scenes.sort(key=lambda x: x.importance_score, reverse=True)
            
            return SceneAnalysisResult(
                scenes=scenes,
                best_scene_index=data.get("best_scene_index", 0),
            )
            
        except Exception as e:
            return SceneAnalysisResult(
                scenes=[],
                analysis_notes=f"Parsing failed: {e}",
            )
