"""
Chapter AI Actions
Handlers for AI-assisted chapter development
"""

from typing import Any, Dict, List

from .chapter_context import format_context_for_prompt


def handle_chapter_action(
    action: str, context: Dict[str, Any], llm_service
) -> List[Dict[str, Any]]:
    """
    Handle chapter-specific AI actions

    Args:
        action: Action identifier (e.g., 'generate_outline')
        context: Context dictionary from build_enrichment_context
        llm_service: LLM service instance for API calls

    Returns:
        List of enrichment results in standard format
    """

    handlers = {
        "generate_outline": generate_outline_handler,
        "write_draft": write_draft_handler,
        "expand_scene": expand_scene_handler,
        "summarize": summarize_handler,
        "improve_prose": improve_prose_handler,
        "add_dialogue": add_dialogue_handler,
    }

    handler = handlers.get(action)
    if not handler:
        raise ValueError(f"Unknown chapter action: {action}")

    return handler(context, llm_service)


def generate_outline_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Generate AI outline for chapter

    Creates a structured outline based on story arc, plot points, and characters
    """

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Generate a detailed chapter outline for the current chapter.

The outline should include:
1. **Opening Scene**: How the chapter begins, setting the stage
2. **Key Events**: Major events that must occur (aligned with plot points)
3. **Character Development**: Specific moments where characters grow or change
4. **Rising Tension**: How conflict builds throughout the chapter
5. **Closing Scene**: How the chapter ends and hooks to the next chapter

Requirements:
- Stay consistent with the story arc and its current phase
- Incorporate all plot points naturally into the flow
- Show character development for featured characters
- Match the specified mood/tone
- Create natural transitions between scenes
- End with a compelling hook or cliffhanger

Format the outline clearly with section headers and bullet points.
"""

    # Call LLM
    result = llm_service.generate(prompt)

    return [
        {
            "field_name": "ai_generated_outline",
            "new_value": result,
            "confidence": "0.90",
            "rationale": "AI-generated outline based on story arc, plot points, and character development requirements",
        }
    ]


def write_draft_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Write full chapter draft

    Generates complete chapter content based on outline and context
    """

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Get chapter details
    chapter = context.get("chapter", {})
    outline = chapter.get("outline", "")
    target_words = chapter.get("target_word_count", 2000)

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Write a complete draft for this chapter.

Chapter Outline:
{outline if outline else "No outline provided. Create the chapter based on the plot points and story arc."}

Requirements:
- Target word count: approximately {target_words} words
- Follow the story arc phase and incorporate all plot points
- Show character development for featured characters
- Maintain consistent mood/tone: {chapter.get('mood_tone', 'appropriate to the story')}
- Set scenes in: {chapter.get('setting_location', 'appropriate locations')}
- Create vivid, engaging prose that matches the genre
- Include dialogue that reveals character and advances plot
- Use sensory details to immerse the reader
- Build tension and emotional engagement
- End with a compelling hook to the next chapter

Write the complete chapter content now:
"""

    # Call LLM (may need higher token limit)
    result = llm_service.generate(prompt, max_tokens=4000)

    return [
        {
            "field_name": "ai_generated_draft",
            "new_value": result,
            "confidence": "0.85",
            "rationale": f"AI-generated chapter draft (~{target_words} words) based on outline and story context",
        }
    ]


def expand_scene_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Expand a specific plot point into a full scene

    Takes a plot point and creates detailed scene content
    """

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Get plot point to expand
    target_plot_point = context.get("target_plot_point")
    if not target_plot_point:
        # Use first plot point from chapter if no specific target
        plot_points = context.get("plot_points", [])
        if not plot_points:
            return [
                {
                    "field_name": "content",
                    "new_value": "Error: No plot point specified for scene expansion",
                    "confidence": "0.0",
                    "rationale": "Cannot expand scene without a plot point",
                }
            ]
        target_plot_point = plot_points[0]

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Expand the following plot point into a full, detailed scene:

Plot Point: {target_plot_point['name']}
Type: {target_plot_point['type']}
Description: {target_plot_point['description']}
Emotional Impact: {target_plot_point['emotional_impact']}
Involved Characters: {', '.join(target_plot_point.get('involved_character_names', []))}

Requirements:
- Write 500-800 words for this scene
- Show, don't tell - use action, dialogue, and sensory details
- Build to the emotional impact level specified
- Develop involved characters through their actions and dialogue
- Match the chapter's mood/tone
- Create a scene that flows naturally from previous content
- Use vivid, engaging prose
- Include internal character thoughts if appropriate
- Build tension appropriately for the plot point type

Write the complete scene now:
"""

    # Call LLM
    result = llm_service.generate(prompt, max_tokens=1500)

    return [
        {
            "field_name": "ai_scene_expansions",
            "new_value": {"plot_point": target_plot_point["name"], "expansion": result},
            "confidence": "0.88",
            "rationale": f"Expanded scene from plot point: {target_plot_point['name']}",
            "merge_mode": True,  # Merge with existing scene expansions
        }
    ]


def summarize_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Generate chapter summary

    Creates a concise summary of chapter content
    """

    # Get chapter content
    chapter = context.get("chapter", {})
    content = chapter.get("content", "")

    if not content:
        return [
            {
                "field_name": "summary",
                "new_value": "Error: No content available to summarize",
                "confidence": "0.0",
                "rationale": "Cannot summarize empty chapter",
            }
        ]

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Write a concise summary of this chapter's content.

Chapter Content:
{content}

Requirements:
- 2-4 paragraphs
- Capture the main events and developments
- Highlight character development moments
- Note how plot points were addressed
- Mention the emotional arc of the chapter
- Be clear and engaging
- Avoid spoiling too much detail while capturing essence

Write the summary now:
"""

    # Call LLM
    result = llm_service.generate(prompt, max_tokens=500)

    return [
        {
            "field_name": "ai_generated_summary",
            "new_value": result,
            "confidence": "0.92",
            "rationale": "AI-generated summary based on chapter content",
        }
    ]


def improve_prose_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Improve chapter prose

    Enhances writing style, flow, and readability
    """

    # Get chapter content
    chapter = context.get("chapter", {})
    content = chapter.get("content", "")

    if not content:
        return [
            {
                "field_name": "content",
                "new_value": "Error: No content available to improve",
                "confidence": "0.0",
                "rationale": "Cannot improve empty chapter",
            }
        ]

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Improve the prose of this chapter while maintaining its core content and events.

Current Content:
{content}

Focus on:
- **Show, don't tell**: Convert exposition to action and sensory details
- **Stronger verbs**: Replace weak verbs with vivid alternatives
- **Varied sentence structure**: Mix short and long sentences for rhythm
- **Sensory details**: Add sight, sound, smell, touch, taste
- **Character voice**: Strengthen dialogue and internal thoughts
- **Pacing**: Improve flow and tension building
- **Clarity**: Remove confusion while maintaining mystery where appropriate
- **Genre consistency**: Match the prose style to {context['project']['genre']}

Requirements:
- Keep all major plot points and events intact
- Maintain character consistency
- Preserve the chapter's emotional arc
- Match the specified mood/tone
- Do NOT change the story fundamentally, only improve how it's told

Write the improved version now:
"""

    # Call LLM (may need higher token limit)
    result = llm_service.generate(prompt, max_tokens=4000)

    return [
        {
            "field_name": "ai_prose_improvements",
            "new_value": result,
            "confidence": "0.83",
            "rationale": "Prose improved for style, flow, and readability while maintaining core content",
            "creates_version": True,  # Suggest creating a version backup
        }
    ]


def add_dialogue_handler(context: Dict[str, Any], llm_service) -> List[Dict[str, Any]]:
    """
    Add dialogue suggestions

    Generates dialogue options for key scenes
    """

    # Get chapter context
    chapter = context.get("chapter", {})
    outline = chapter.get("outline", "")
    content = chapter.get("content", "")

    # Get characters
    characters = context.get("characters", [])
    if not characters:
        return [
            {
                "field_name": "ai_suggestions",
                "new_value": {"dialogue": "No featured characters found"},
                "confidence": "0.0",
                "rationale": "Cannot generate dialogue without characters",
            }
        ]

    # Format context for prompt
    context_text = format_context_for_prompt(context)

    # Build prompt
    prompt = """
{context_text}

=== TASK ===
Generate dialogue suggestions for key scenes in this chapter.

Current Outline:
{outline if outline else "No outline available"}

Current Content Excerpt:
{content[:500] if content else "No content yet"}

For each featured character, provide:
1. **Voice Guidelines**: How they speak (formal/casual, verbose/terse, etc.)
2. **Key Lines**: 3-5 dialogue examples for important moments
3. **Character Relationships**: How they address other characters

Requirements:
- Each character should have a distinct voice
- Dialogue should reveal character and advance plot
- Include subtext and conflict where appropriate
- Match the genre and tone
- Show character development through dialogue evolution
- Include dialogue tags and action beats as examples

Format as structured suggestions that can be adapted into the chapter.
"""

    # Call LLM
    result = llm_service.generate(prompt, max_tokens=1500)

    # Store in ai_suggestions field
    return [
        {
            "field_name": "ai_dialogue_suggestions",
            "new_value": {"dialogue_suggestions": result},
            "confidence": "0.87",
            "rationale": "AI-generated dialogue suggestions for featured characters",
            "merge_mode": True,  # Merge with existing dialogue suggestions
        }
    ]


def format_plot_points_for_prompt(plot_points: List[Dict[str, Any]]) -> str:
    """Format plot points for inclusion in prompts"""

    if not plot_points:
        return "No plot points specified"

    lines = []
    for pp in plot_points:
        lines.append(f"- {pp['name']} ({pp['type']})")
        lines.append(f"  {pp['description']}")
        lines.append(f"  Emotional Impact: {pp['emotional_impact']}")

    return "\n".join(lines)


def format_characters_for_prompt(characters: List[Dict[str, Any]]) -> str:
    """Format characters for inclusion in prompts"""

    if not characters:
        return "No featured characters specified"

    lines = []
    for char in characters:
        lines.append(f"- {char['name']} ({char['role']})")
        lines.append(f"  {char['description']}")

        if "arc_in_this_chapter" in char:
            arc = char["arc_in_this_chapter"]
            lines.append(f"  Arc Stage: {arc.get('arc_stage', 'N/A')}")
            lines.append(f"  Growth Moment: {arc.get('growth_moment', 'N/A')}")

    return "\n".join(lines)
