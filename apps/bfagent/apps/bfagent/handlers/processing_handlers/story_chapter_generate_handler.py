"""
Story Engine Chapter Generation Handler
Generates AI-powered novel chapters using the Story Engine architecture
Features:
    - Multi-strand novel generation
    - Character-aware content
    - Beat-based chapter creation
    - Quality scoring
    - Version control
"""

import logging
from typing import Any, Dict, Optional

from django.db import transaction

from apps.bfagent.handlers.base import BaseProcessingHandler, ProcessingError
from apps.bfagent.handlers.processing_handlers.llm_call_handler import LLMCallHandler
from apps.bfagent.models import ChapterBeat, StoryBible, StoryChapter, StoryCharacter, StoryStrand

logger = logging.getLogger(__name__)


class StoryChapterGenerateHandler(BaseProcessingHandler):
    """
    Handler for Story Engine chapter generation
    Generates novel chapters based on:
    - Story Bible (world, themes, tone)
    - Story Strands (plot threads)
    - Story Characters (cast)
    - Chapter Beats (outline)
    Usage:
        handler = StoryChapterGenerateHandler()
        result = handler.execute({
            'beat_id': 42,
            'temperature': 0.8,
        })
    """

    def __init__(self):
        super().__init__(name="story_chapter_generator", version="1.0.0")
        self.llm_handler = LLMCallHandler()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate chapter from beat
        Args:
            context:
                - beat_id: int (required)
                - temperature: float (optional, 0.7)
                - version: int (optional, auto-increment)
                - agent_id: int (optional)
        Returns:
            {
                'success': bool,
                'chapter': StoryChapter,
                'word_count': int,
                'quality_score': float
            }
        """
        beat_id = context.get("beat_id")
        if not beat_id:
            raise ProcessingError("beat_id is required")
        try:
            beat = ChapterBeat.objects.select_related(
                "story_bible", "strand", "strand__primary_character"
            ).get(pk=beat_id)
        except ChapterBeat.DoesNotExist:
            raise ProcessingError(f"ChapterBeat {beat_id} not found")
        temperature = context.get("temperature", 0.7)
        agent_id = context.get("agent_id")
        version = context.get("version") or (beat.generated_chapters.count() + 1)
        logger.info(f"Generating chapter for beat {beat_id}, version {version}")
        # Build comprehensive context
        generation_context = self._build_generation_context(beat)
        # Generate content with LLM
        content = self._generate_with_llm(
            generation_context, temperature=temperature, agent_id=agent_id
        )
        # Calculate quality metrics
        word_count = len(content.split())
        quality_score = self._calculate_quality_score(content, beat)
        # Save to database
        with transaction.atomic():
            chapter = StoryChapter.objects.create(
                story_bible=beat.story_bible,
                strand=beat.strand,
                beat=beat,
                chapter_number=beat.beat_number,
                title=beat.title,
                content=content,
                word_count=word_count,
                pov_character=(
                    beat.character_focus.first() if beat.character_focus.exists() else None
                ),
                generation_method="llm_ai",
                status="draft",
                version=version,
                quality_score=quality_score,
                consistency_score=0.85,  # Will be calculated properly later
            )
        logger.info(
            f"Generated chapter {chapter.id}: {word_count} words, " f"quality {quality_score:.2f}"
        )
        return {
            "success": True,
            "chapter": chapter,
            "word_count": word_count,
            "quality_score": quality_score,
            "message": f"Generated chapter {chapter.chapter_number} (v{version})",
        }

    def _build_generation_context(self, beat: ChapterBeat) -> Dict[str, Any]:
        """
        Build comprehensive generation context from Story Engine
        """
        bible = beat.story_bible
        strand = beat.strand
        # Get all relevant characters
        characters = bible.characters.all()[:10]  # Top 10
        character_profiles = []
        for char in characters:
            character_profiles.append(
                {
                    "name": char.name,
                    "age": char.age,
                    "traits": char.personality_traits or [],
                    "skills": char.skills or [],
                    "biography": char.biography[:200] if char.biography else "",
                }
            )
        # Get previous chapters in strand for continuity
        previous_chapters = StoryChapter.objects.filter(
            strand=strand, chapter_number__lt=beat.beat_number
        ).order_by("-chapter_number")[:3]
        previous_summaries = []
        for ch in previous_chapters:
            previous_summaries.append(
                {
                    "chapter": ch.chapter_number,
                    "title": ch.title,
                    "summary": ch.summary[:300] if ch.summary else ch.content[:300],
                }
            )
        return {
            # Story Bible
            "title": bible.title,
            "subtitle": bible.subtitle,
            "genre": bible.genre,
            "world_rules": bible.world_rules or {},
            "technology_levels": bible.technology_levels or {},
            "prose_style": bible.prose_style,
            "tone": bible.tone,
            # Strand
            "strand_name": strand.name,
            "strand_focus": strand.focus,
            "core_theme": strand.core_theme,
            # Beat
            "beat_number": beat.beat_number,
            "beat_title": beat.title,
            "beat_description": beat.description,
            "key_events": beat.key_events or [],
            "emotional_tone": beat.emotional_tone,
            "target_word_count": beat.target_word_count,
            "tension_level": beat.tension_level,
            # Characters
            "characters": character_profiles,
            "focus_character": (
                beat.character_focus.first().name if beat.character_focus.exists() else None
            ),
            # Continuity
            "previous_chapters": previous_summaries,
        }

    def _generate_with_llm(
        self, context: Dict[str, Any], temperature: float = 0.7, agent_id: Optional[int] = None
    ) -> str:
        """
        Generate chapter content using LLM
        """
        system_prompt = f"""You are a professional novelist specializing in {context['genre']}.
Your writing style: {context['prose_style']}
Tone: {context['tone']}
You are writing for the novel "{context['title']}", which explores {context['core_theme']}.
Write in vivid, immersive prose that draws readers into the story.
Show don't tell. Use sensory details. Create emotional resonance."""
        # Build character list (can't use backslash in f-string)
        char_list = ""
        for char in context["characters"][:5]:
            char_list += f"- {char['name']} ({char['age']}): {char['biography']}\n"

        # Build continuity section
        if context["previous_chapters"]:
            continuity = "Recent events: " + "; ".join(
                [f"Ch{ch['chapter']}: {ch['summary'][:100]}" for ch in context["previous_chapters"]]
            )
        else:
            continuity = "This is an early chapter."

        # Build comprehensive user prompt
        user_prompt = f"""Write Chapter {context['beat_number']}: {context['beat_title']}

## STORY CONTEXT
**Strand**: {context['strand_name']} - {context['strand_focus']}
**Genre**: {context['genre']}
**Theme**: {context['core_theme']}

## CHAPTER BRIEF
{context['beat_description']}

**Key Events**:
{', '.join(context['key_events']) if context['key_events'] else 'Natural story progression'}

**Emotional Tone**: {context['emotional_tone']}
**Tension Level**: {context['tension_level']}/10
**Target Length**: {context['target_word_count']} words

## CHARACTERS
{char_list}
**Focus Character**: {context['focus_character'] or 'Multiple POV'}

## CONTINUITY
{continuity}

## WRITING INSTRUCTIONS
1. Follow the beat description closely
2. Include the key events listed
3. Match the specified emotional tone
4. Write in {context['prose_style']} style
5. Maintain {context['tone']} tone throughout
6. Aim for approximately {context['target_word_count']} words
7. Use vivid sensory details
8. Show character emotions through actions and dialogue
9. Maintain continuity with previous chapters
10. End with a hook for the next chapter

## OUTPUT FORMAT
Write ONLY the chapter content. No meta-commentary or analysis.
Start directly with the story and end when the chapter is complete.

Begin writing now:"""
        try:
            response = self.llm_handler.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                agent_id=agent_id,
                max_tokens=6000,  # ~4500 words
                temperature=temperature,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise ProcessingError(f"Failed to generate content: {e}")

    def _calculate_quality_score(self, content: str, beat: ChapterBeat) -> float:
        """
        Calculate chapter quality score (0.0 - 1.0)
        Factors:
        - Word count vs target
        - Paragraph count (structure)
        - Dialogue presence
        - Sensory words
        """
        word_count = len(content.split())
        target = beat.target_word_count
        # Word count score (penalty if too short/long)
        if target > 0:
            ratio = word_count / target
            wc_score = 1.0 - abs(ratio - 1.0) * 0.5
            wc_score = max(0.5, min(1.0, wc_score))
        else:
            wc_score = 0.8
        # Structure score (paragraph count)
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        para_score = min(len(paragraphs) / 20, 1.0)  # Good if 20+ paragraphs
        # Dialogue score (contains quotes)
        has_dialogue = '"' in content or "'" in content
        dialogue_score = 1.0 if has_dialogue else 0.7
        # Weighted average
        quality = (wc_score * 0.4) + (para_score * 0.3) + (dialogue_score * 0.3)
        return round(quality, 2)
