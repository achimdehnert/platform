"""Chapter writing handler."""

from typing import Optional

from creative_services.core.base_handler import BaseHandler
from creative_services.core.context import StoryContext
from creative_services.core.llm_client import LLMClient, LLMConfig, LLMResponse
from creative_services.story.schemas import Chapter, StoryResult


class ChapterWriter(BaseHandler[StoryContext, StoryResult]):
    """
    Write story chapters with context awareness.
    
    Features:
    - Maintains continuity from previous content
    - Follows established character voices
    - Creates engaging prose with scene breaks
    - Supports multiple genres (fiction, travel)
    """
    
    SERVICE_NAME = "chapter_writer"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert fiction writer creating engaging story chapters.
Write vivid, immersive prose with strong characterization and pacing.
Maintain consistency with established characters and plot.
Create natural dialogue and atmospheric descriptions."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        super().__init__(llm_client, llm_config)
    
    def build_prompt(self, context: StoryContext) -> str:
        """Build chapter writing prompt."""
        
        parts = ["Write a story chapter with the following context:\n"]
        
        if context.title:
            parts.append(f"Story Title: {context.title}")
        
        if context.chapter_number:
            parts.append(f"Chapter Number: {context.chapter_number}")
        
        if context.premise:
            parts.append(f"\nPremise: {context.premise}")
        
        if context.world_summary:
            parts.append(f"\nSetting: {context.world_summary}")
        
        if context.characters:
            parts.append("\nCharacters:")
            for char in context.characters:
                name = char.get("name", "Unknown")
                role = char.get("role", "")
                desc = char.get("description", "")
                parts.append(f"  - {name} ({role}): {desc}")
        
        if context.previous_summary:
            parts.append(f"\nPrevious Events: {context.previous_summary}")
        
        if context.genre:
            parts.append(f"\nGenre: {context.genre}")
        
        if context.tone:
            parts.append(f"Tone: {context.tone}")
        
        parts.append(f"\nTarget Word Count: {context.target_word_count}")
        parts.append(f"Output Language: {context.language}")
        
        if context.style_notes:
            parts.append(f"\nStyle Notes: {context.style_notes}")
        
        parts.append("""

Write the chapter now. Include:
1. An engaging opening that hooks the reader
2. Well-paced scenes with vivid descriptions
3. Natural dialogue that reveals character
4. Sensory details that immerse the reader
5. A compelling ending that propels the story forward

Begin the chapter with a title, then the prose.""")
        
        return "\n".join(parts)
    
    def get_system_prompt(self, context: StoryContext) -> str:
        """Get system prompt with genre-specific additions."""
        base = self.DEFAULT_SYSTEM_PROMPT
        
        if context.genre == "travel":
            base += """

For travel stories:
- Bring locations to life with sensory details
- Show cultural encounters and local flavor
- Balance external journey with internal growth
- Include authentic travel moments (food, language, surprises)"""
        elif context.genre == "fantasy":
            base += """

For fantasy:
- Weave magic naturally into the narrative
- Create wonder through worldbuilding details
- Balance action with character moments"""
        
        return base
    
    def parse_response(self, response: LLMResponse, context: StoryContext) -> StoryResult:
        """Parse LLM response into StoryResult with Chapter."""
        
        content = response.content.strip()
        
        # Extract title if present
        lines = content.split("\n")
        title = f"Chapter {context.chapter_number or 1}"
        prose_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith("#"):
                if i == 0 and len(line) < 100:
                    title = line.replace("# ", "").replace("## ", "")
                    prose_start = i + 1
                break
            elif line.startswith("#"):
                title = line.replace("# ", "").replace("## ", "")
                prose_start = i + 1
                break
        
        prose = "\n".join(lines[prose_start:]).strip()
        word_count = len(prose.split())
        
        chapter = Chapter(
            number=context.chapter_number or 1,
            title=title,
            content=prose,
            word_count=word_count,
            characters=[c.get("name", "") for c in context.characters if c.get("name")],
        )
        
        return StoryResult(chapter=chapter)


class TravelChapterWriter(ChapterWriter):
    """Specialized chapter writer for travel stories."""
    
    SERVICE_NAME = "travel_chapter_writer"
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert travel writer creating immersive journey narratives.
Bring destinations to life through vivid sensory details.
Show the traveler's growth through their experiences.
Balance external adventure with internal reflection.
Include authentic cultural encounters and local flavor."""
    
    def build_prompt(self, context: StoryContext) -> str:
        """Build travel-specific chapter prompt."""
        
        if not context.genre:
            context.genre = "travel"
        
        base = super().build_prompt(context)
        
        travel_additions = """

For this travel chapter, especially focus on:
- The specific sensory experience of the location
- Cultural encounters and moments of connection
- Local food, sounds, smells, textures
- The traveler's emotional response to new experiences
- Small moments that feel authentically travel"""
        
        return base + travel_additions
