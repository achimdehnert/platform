"""
Chapter Context Builder
Builds comprehensive context for AI-assisted chapter development
"""

from typing import Any, Dict, Optional

from apps.bfagent.models import BookChapters, BookProjects, PlotPoint, StoryArc


def build_enrichment_context(
    project: BookProjects,
    chapter: Optional[BookChapters] = None,
    plot_point: Optional[PlotPoint] = None,
    story_arc: Optional[StoryArc] = None,
) -> Dict[str, Any]:
    """
    Build comprehensive context for AI enrichment

    Args:
        project: BookProject instance (required)
        chapter: Optional BookChapters instance for chapter-specific context
        plot_point: Optional PlotPoint instance for plot-point-specific context
        story_arc: Optional StoryArc instance for arc-specific context

    Returns:
        Dict with structured context data for AI processing
    """

    # Base project context (always included)
    context = {"project": build_project_context(project)}

    # Add chapter-specific context if provided
    if chapter:
        context["chapter"] = build_chapter_context(chapter, project)

        # Add story arc context if chapter is linked to an arc
        if chapter.story_arc:
            context["story_arc"] = build_story_arc_context(chapter.story_arc, chapter)

        # Add plot points context
        if chapter.plot_points.exists():
            context["plot_points"] = build_plot_points_context(chapter)

        # Add featured characters context
        if chapter.featured_characters.exists():
            context["characters"] = build_characters_context(chapter)

        # Add previous chapter for continuity
        prev_chapter = get_previous_chapter(project, chapter)
        if prev_chapter:
            context["previous_chapter"] = build_previous_chapter_context(prev_chapter)

        # Add next chapter for planning
        next_chapter = get_next_chapter(project, chapter)
        if next_chapter:
            context["next_chapter"] = build_next_chapter_context(next_chapter)

    # Add plot point specific context if provided
    if plot_point:
        context["target_plot_point"] = build_single_plot_point_context(plot_point)

    # Add story arc specific context if provided (and not already added via chapter)
    if story_arc and "story_arc" not in context:
        context["story_arc"] = build_story_arc_context(story_arc)

    return context


def build_project_context(project: BookProjects) -> Dict[str, Any]:
    """Build project-level context"""

    return {
        "title": project.title,
        "genre": project.genre,
        "content_rating": project.content_rating,
        "description": project.description,
        "tagline": project.tagline,
        "story_premise": project.story_premise,
        "target_audience": project.target_audience,
        "story_themes": project.story_themes,
        "setting_time": project.setting_time,
        "setting_location": project.setting_location,
        "atmosphere_tone": project.atmosphere_tone,
        "main_conflict": project.main_conflict,
        "stakes": project.stakes,
        "protagonist_concept": project.protagonist_concept,
        "antagonist_concept": project.antagonist_concept,
        "unique_elements": project.unique_elements,
        "genre_settings": project.genre_settings,
        "target_word_count": project.target_word_count,
        "current_word_count": project.current_word_count,
        "status": project.status,
    }


def build_chapter_context(chapter: BookChapters, project: BookProjects) -> Dict[str, Any]:
    """Build chapter-specific context"""

    # Calculate total chapters for position context
    total_chapters = project.chapters.count()

    return {
        "id": chapter.id,
        "number": chapter.chapter_number,
        "title": chapter.title,
        "summary": chapter.summary,
        "outline": chapter.outline,
        "content": chapter.content,
        "status": chapter.status,
        "writing_stage": chapter.writing_stage,
        "word_count": chapter.word_count,
        "target_word_count": chapter.target_word_count,
        "progress_percentage": chapter.progress_percentage,
        "reading_time_minutes": chapter.reading_time_minutes,
        "notes": chapter.notes,
        # Phase 1B: Storyline fields
        "mood_tone": chapter.mood_tone,
        "setting_location": chapter.setting_location,
        "time_period": chapter.time_period,
        "character_arcs": chapter.character_arcs,
        "consistency_score": chapter.consistency_score,
        # Metadata
        "metadata": chapter.metadata,
        "ai_suggestions": chapter.ai_suggestions,
        # Position in book
        "position_in_book": f"{chapter.chapter_number}/{total_chapters}",
        "is_first_chapter": chapter.chapter_number == 1,
        "is_last_chapter": chapter.chapter_number == total_chapters,
    }


def build_story_arc_context(
    story_arc: StoryArc, chapter: Optional[BookChapters] = None
) -> Dict[str, Any]:
    """Build story arc context"""

    arc_context = {
        "id": story_arc.id,
        "name": story_arc.name,
        "description": story_arc.description,
        "type": story_arc.arc_type,
        "central_conflict": story_arc.central_conflict,
        "resolution": story_arc.resolution,
        "importance_level": story_arc.importance_level,
        "completion_status": story_arc.completion_status,
        "start_chapter": story_arc.start_chapter,
        "end_chapter": story_arc.end_chapter,
        "chapter_span": story_arc.chapter_span,
        "progress_percentage": story_arc.progress_percentage,
    }

    # Add position in arc if chapter is provided
    if chapter:
        position_in_arc = chapter.chapter_number - story_arc.start_chapter + 1
        arc_context["chapter_position_in_arc"] = f"{position_in_arc}/{story_arc.chapter_span}"
        arc_context["arc_progress_at_this_chapter"] = (
            position_in_arc / story_arc.chapter_span
        ) * 100

        # Determine story phase
        progress = position_in_arc / story_arc.chapter_span
        if progress <= 0.25:
            arc_context["arc_phase"] = "setup"
        elif progress <= 0.5:
            arc_context["arc_phase"] = "rising_action"
        elif progress <= 0.75:
            arc_context["arc_phase"] = "climax_approach"
        else:
            arc_context["arc_phase"] = "resolution"

    return arc_context


def build_plot_points_context(chapter: BookChapters) -> list:
    """Build plot points context for a chapter"""

    plot_points = []
    for pp in chapter.plot_points.all().order_by("sequence_order"):
        plot_points.append(
            {
                "id": pp.id,
                "name": pp.name,
                "description": pp.description,
                "sequence_order": pp.sequence_order,
                "type": pp.point_type,
                "emotional_impact": pp.emotional_impact,
                "completion_status": pp.completion_status,
                "notes": pp.notes,
                "involved_character_names": [char.name for char in pp.involved_characters.all()],
            }
        )

    return plot_points


def build_single_plot_point_context(plot_point: PlotPoint) -> Dict[str, Any]:
    """Build context for a specific plot point"""

    return {
        "id": plot_point.id,
        "name": plot_point.name,
        "description": plot_point.description,
        "chapter_number": plot_point.chapter_number,
        "sequence_order": plot_point.sequence_order,
        "type": plot_point.point_type,
        "emotional_impact": plot_point.emotional_impact,
        "completion_status": plot_point.completion_status,
        "notes": plot_point.notes,
        "story_arc_name": plot_point.story_arc.name if plot_point.story_arc else None,
        "involved_characters": [
            {"name": char.name, "role": char.role, "description": char.description}
            for char in plot_point.involved_characters.all()
        ],
    }


def build_characters_context(chapter: BookChapters) -> list:
    """Build featured characters context"""

    characters = []
    for char in chapter.featured_characters.all():
        char_data = {
            "id": char.id,
            "name": char.name,
            "role": char.role,
            "description": char.description,
            "age": char.age,
            "background": char.background,
            "personality": char.personality,
            "appearance": char.appearance,
            "goals": char.goals,
            "fears": char.fears,
            "strengths": char.strengths,
            "weaknesses": char.weaknesses,
        }

        # Add character arc for this chapter if exists
        if chapter.character_arcs and char.name in chapter.character_arcs:
            char_data["arc_in_this_chapter"] = chapter.character_arcs[char.name]

        characters.append(char_data)

    return characters


def build_previous_chapter_context(prev_chapter: BookChapters) -> Dict[str, Any]:
    """Build context for previous chapter (for continuity)"""

    # Get last 500 characters of content for continuity
    ending_snippet = None
    if prev_chapter.content:
        ending_snippet = (
            prev_chapter.content[-500:] if len(prev_chapter.content) > 500 else prev_chapter.content
        )

    return {
        "number": prev_chapter.chapter_number,
        "title": prev_chapter.title,
        "summary": prev_chapter.summary,
        "ending_snippet": ending_snippet,
        "mood_tone": prev_chapter.mood_tone,
        "setting_location": prev_chapter.setting_location,
    }


def build_next_chapter_context(next_chapter: BookChapters) -> Dict[str, Any]:
    """Build context for next chapter (for planning)"""

    return {
        "number": next_chapter.chapter_number,
        "title": next_chapter.title,
        "summary": next_chapter.summary,
        "outline": next_chapter.outline,
        "mood_tone": next_chapter.mood_tone,
    }


def get_previous_chapter(project: BookProjects, chapter: BookChapters) -> Optional[BookChapters]:
    """Get the previous chapter in the book"""

    if chapter.chapter_number == 1:
        return None

    return project.chapters.filter(chapter_number=chapter.chapter_number - 1).first()


def get_next_chapter(project: BookProjects, chapter: BookChapters) -> Optional[BookChapters]:
    """Get the next chapter in the book"""

    return project.chapters.filter(chapter_number=chapter.chapter_number + 1).first()


def format_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format context dictionary into a human-readable string for LLM prompts

    Args:
        context: Context dictionary from build_enrichment_context

    Returns:
        Formatted string for inclusion in LLM prompts
    """

    lines = []

    # Project information
    if "project" in context:
        proj = context["project"]
        lines.append("=== BOOK PROJECT ===")
        lines.append(f"Title: {proj.get('title', 'N/A')}")
        lines.append(f"Genre: {proj.get('genre', 'N/A')}")
        lines.append(f"Premise: {proj.get('story_premise', 'N/A')}")
        lines.append(f"Target Audience: {proj.get('target_audience', 'N/A')}")
        lines.append(f"Themes: {proj.get('story_themes', 'N/A')}")
        lines.append(f"Main Conflict: {proj.get('main_conflict', 'N/A')}")
        lines.append(f"Stakes: {proj.get('stakes', 'N/A')}")
        lines.append("")

    # Chapter information
    if "chapter" in context:
        chap = context["chapter"]
        lines.append("=== CURRENT CHAPTER ===")
        lines.append(f"Chapter {chap.get('number')}: {chap.get('title', 'Untitled')}")
        lines.append(f"Position: {chap.get('position_in_book')}")
        lines.append(f"Writing Stage: {chap.get('writing_stage', 'N/A')}")
        lines.append(f"Mood/Tone: {chap.get('mood_tone', 'N/A')}")
        lines.append(f"Setting: {chap.get('setting_location', 'N/A')}")
        lines.append(f"Time Period: {chap.get('time_period', 'N/A')}")

        if chap.get("summary"):
            lines.append(f"Summary: {chap['summary']}")
        if chap.get("outline"):
            lines.append(f"Outline: {chap['outline']}")

        lines.append("")

    # Story arc information
    if "story_arc" in context:
        arc = context["story_arc"]
        lines.append("=== STORY ARC ===")
        lines.append(f"Arc: {arc.get('name', 'N/A')}")
        lines.append(f"Type: {arc.get('type', 'N/A')}")
        lines.append(f"Central Conflict: {arc.get('central_conflict', 'N/A')}")
        lines.append(f"Position in Arc: {arc.get('chapter_position_in_arc', 'N/A')}")
        lines.append(f"Arc Phase: {arc.get('arc_phase', 'N/A')}")
        lines.append("")

    # Plot points
    if "plot_points" in context and context["plot_points"]:
        lines.append("=== PLOT POINTS ===")
        for pp in context["plot_points"]:
            lines.append(f"{pp['sequence_order']}. {pp['name']} ({pp['type']})")
            lines.append(f"   {pp['description']}")
            lines.append(f"   Emotional Impact: {pp['emotional_impact']}")
        lines.append("")

    # Characters
    if "characters" in context and context["characters"]:
        lines.append("=== FEATURED CHARACTERS ===")
        for char in context["characters"]:
            lines.append(f"- {char['name']} ({char['role']})")
            lines.append(f"  {char['description']}")
            if "arc_in_this_chapter" in char:
                arc_data = char["arc_in_this_chapter"]
                lines.append(f"  Arc Stage: {arc_data.get('arc_stage', 'N/A')}")
                lines.append(f"  Emotional State: {arc_data.get('emotional_state', 'N/A')}")
        lines.append("")

    # Previous chapter (for continuity)
    if "previous_chapter" in context:
        prev = context["previous_chapter"]
        lines.append("=== PREVIOUS CHAPTER ===")
        lines.append(f"Chapter {prev['number']}: {prev['title']}")
        if prev.get("summary"):
            lines.append(f"Summary: {prev['summary']}")
        if prev.get("ending_snippet"):
            lines.append(f"Ending: ...{prev['ending_snippet']}")
        lines.append("")

    return "\n".join(lines)
