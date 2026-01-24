"""
Story Generator - Core LLM Integration

Generates stories using Anthropic Claude API:
1. Create story outline from trip data
2. Generate chapters sequentially
3. Maintain consistency across chapters
4. Handle errors and retries
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Generator

from django.conf import settings

try:
    import anthropic
except ImportError:
    anthropic = None

from apps.trips.models import Trip
from apps.stories.models import Story, Chapter
from apps.locations.models import BaseLocation, LocationLayer

from .prompts import PromptBuilder, StoryContext, ChapterContext
from .mapper import StoryMapper, StoryPlan

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of a generation operation."""
    success: bool
    content: str = ""
    error: str = ""
    tokens_used: int = 0


class StoryGenerator:
    """
    Generates personalized stories using Claude API.
    
    Flow:
    1. Map trip to story plan (StoryMapper)
    2. Generate story outline
    3. For each chapter:
       a. Get/generate location data
       b. Build chapter prompt
       c. Generate chapter content
       d. Save and update progress
    """
    
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS_OUTLINE = 4000
    MAX_TOKENS_CHAPTER = 8000
    
    def __init__(self, trip: Trip, user=None):
        self.trip = trip
        self.user = user or trip.user
        self.client = self._get_client()
        self.mapper = StoryMapper(trip, user)
    
    def _get_client(self):
        """Get Anthropic client."""
        if anthropic is None:
            logger.error("Anthropic package not installed")
            return None
        
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not configured")
            return None
        
        return anthropic.Anthropic(api_key=api_key)
    
    def generate_story(self, story: Story) -> Generator[dict, None, None]:
        """
        Generate complete story with progress updates.
        
        Yields progress updates:
        {"phase": "outline", "progress": 0-100, "message": "..."}
        {"phase": "chapter", "chapter": 1, "progress": 0-100, "message": "..."}
        {"phase": "complete", "progress": 100, "message": "..."}
        """
        
        if not self.client:
            yield {"phase": "error", "message": "LLM client not available"}
            return
        
        try:
            # Phase 1: Create story plan
            yield {"phase": "planning", "progress": 5, "message": "Analysiere Reisedaten..."}
            story_plan = self.mapper.map_to_story_plan()
            
            # Update story metadata
            story.total_chapters = story_plan.total_chapters
            story.total_words = story_plan.total_words
            story.status = Story.Status.GENERATING
            story.save()
            
            # Phase 2: Generate outline
            yield {"phase": "outline", "progress": 10, "message": "Erstelle Story-Outline..."}
            outline_result = self._generate_outline(story, story_plan)
            
            if not outline_result.success:
                story.status = Story.Status.FAILED
                story.save()
                yield {"phase": "error", "message": f"Outline-Fehler: {outline_result.error}"}
                return
            
            # Parse and store outline
            outline_data = self._parse_outline(outline_result.content)
            story.synopsis = outline_data.get('synopsis', '')
            story.save()
            
            yield {"phase": "outline", "progress": 20, "message": "Outline erstellt!"}
            
            # Phase 3: Generate chapters
            chapter_summaries = []
            
            for i, chapter_plan in enumerate(story_plan.chapters):
                progress = 20 + int((i / story_plan.total_chapters) * 75)
                
                yield {
                    "phase": "chapter",
                    "chapter": i + 1,
                    "total": story_plan.total_chapters,
                    "progress": progress,
                    "message": f"Schreibe Kapitel {i + 1}: {chapter_plan.location_city}..."
                }
                
                # Get location data
                location_data = self._get_location_data(
                    chapter_plan.location_city,
                    chapter_plan.location_country,
                    story.genre,
                )
                
                # Generate chapter
                chapter_result = self._generate_chapter(
                    story=story,
                    chapter_plan=chapter_plan,
                    location_data=location_data,
                    previous_summary=chapter_summaries[-1] if chapter_summaries else "",
                    outline_data=outline_data,
                )
                
                if not chapter_result.success:
                    logger.error(f"Chapter {i+1} failed: {chapter_result.error}")
                    # Continue with next chapter, don't fail entire story
                    continue
                
                # Create chapter record
                chapter = Chapter.objects.create(
                    story=story,
                    chapter_number=i + 1,
                    title=f"Kapitel {i + 1}: {chapter_plan.location_city}",
                    content=chapter_result.content,
                    word_count=len(chapter_result.content.split()),
                    location_city=chapter_plan.location_city,
                    location_country=chapter_plan.location_country,
                    story_date=chapter_plan.date,
                    pacing_type=chapter_plan.pacing_type,
                    status=Chapter.Status.READY,
                )
                
                # Create summary for next chapter
                chapter_summaries.append(self._summarize_chapter(chapter_result.content))
                
                yield {
                    "phase": "chapter",
                    "chapter": i + 1,
                    "total": story_plan.total_chapters,
                    "progress": progress + 5,
                    "message": f"Kapitel {i + 1} fertig!"
                }
            
            # Phase 4: Complete
            story.status = Story.Status.READY
            story.generated_chapters = story.chapters.count()
            story.save()
            
            yield {
                "phase": "complete",
                "progress": 100,
                "message": f"Story fertig! {story.generated_chapters} Kapitel generiert."
            }
            
        except Exception as e:
            logger.exception("Story generation failed")
            story.status = Story.Status.FAILED
            story.save()
            yield {"phase": "error", "message": str(e)}
    
    def _generate_outline(self, story: Story, story_plan: StoryPlan) -> GenerationResult:
        """Generate story outline using LLM."""
        
        context = StoryContext(
            genre=story.genre,
            spice_level=story.spice_level,
            ending_type=story.ending_type,
            protagonist_gender=story.protagonist_gender,
            protagonist_name=story.protagonist_name or "Die Protagonistin",
            total_chapters=story_plan.total_chapters,
            total_words=story_plan.total_words,
            triggers_avoid=story.triggers_avoid or [],
            user_notes=story.user_notes or "",
        )
        
        locations = self.mapper.get_locations_for_story()
        prompt = PromptBuilder.build_story_outline_prompt(context, locations)
        
        return self._call_llm(prompt, self.MAX_TOKENS_OUTLINE)
    
    def _generate_chapter(
        self,
        story: Story,
        chapter_plan,
        location_data: dict,
        previous_summary: str,
        outline_data: dict,
    ) -> GenerationResult:
        """Generate single chapter using LLM."""
        
        story_context = StoryContext(
            genre=story.genre,
            spice_level=story.spice_level,
            ending_type=story.ending_type,
            protagonist_gender=story.protagonist_gender,
            protagonist_name=story.protagonist_name or "Die Protagonistin",
            total_chapters=story.total_chapters,
            total_words=story.total_words,
            triggers_avoid=story.triggers_avoid or [],
        )
        
        chapter_context = ChapterContext(
            chapter_number=chapter_plan.chapter_number,
            location_name=location_data.get('name', chapter_plan.location_city),
            location_city=chapter_plan.location_city,
            location_country=chapter_plan.location_country,
            location_atmosphere=location_data.get('atmosphere', 'neutral'),
            location_details=location_data,
            date=chapter_plan.date.strftime("%d. %B %Y") if chapter_plan.date else "",
            pacing_type=chapter_plan.pacing_type,
            story_beat=chapter_plan.story_beat,
            word_count=chapter_plan.word_count,
            previous_summary=previous_summary,
        )
        
        prompt = PromptBuilder.build_chapter_prompt(story_context, chapter_context)
        
        return self._call_llm(prompt, self.MAX_TOKENS_CHAPTER)
    
    def _call_llm(self, prompt: str, max_tokens: int) -> GenerationResult:
        """Call Claude API."""
        
        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                system=PromptBuilder.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text if message.content else ""
            tokens = message.usage.input_tokens + message.usage.output_tokens
            
            return GenerationResult(
                success=True,
                content=content,
                tokens_used=tokens,
            )
            
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return GenerationResult(success=False, error=str(e))
        except Exception as e:
            logger.exception("LLM call failed")
            return GenerationResult(success=False, error=str(e))
    
    def _get_location_data(self, city: str, country: str, genre: str) -> dict:
        """Get or generate location data."""
        
        # Try to find existing location
        base_location = BaseLocation.objects.filter(
            city__iexact=city,
            country__iexact=country,
        ).first()
        
        if base_location:
            # Check for genre layer
            layer = LocationLayer.objects.filter(
                base_location=base_location,
                genre=genre,
            ).first()
            
            if layer:
                return {
                    'name': base_location.name,
                    'city': base_location.city,
                    'country': base_location.country,
                    'atmosphere': layer.atmosphere_tags,
                    'story_hooks': layer.story_hooks,
                    'sensory_details': layer.sensory_details,
                    'local_culture': base_location.local_culture,
                }
        
        # Fallback: basic data
        return {
            'name': city,
            'city': city,
            'country': country,
            'atmosphere': 'vibrant',
            'story_hooks': [],
            'sensory_details': {},
            'local_culture': {},
        }
    
    def _parse_outline(self, content: str) -> dict:
        """Parse outline from LLM response."""
        try:
            # Try to extract JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in content:
                # Try to find JSON object
                start = content.index("{")
                end = content.rindex("}") + 1
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: extract text sections
        return {
            'synopsis': content[:500] if content else "",
            'chapters': [],
        }
    
    def _summarize_chapter(self, content: str, max_length: int = 200) -> str:
        """Create brief summary of chapter for context."""
        # Simple extraction: first paragraph or first N characters
        paragraphs = content.split('\n\n')
        if paragraphs:
            summary = paragraphs[0][:max_length]
            if len(paragraphs[0]) > max_length:
                summary += "..."
            return summary
        return content[:max_length] + "..."
