"""
Management command to load prompt templates for new handlers
Run: python manage.py load_prompt_templates
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import PromptTemplate


class Command(BaseCommand):
    help = "Load prompt templates for Phase 1, 5, 6 handlers"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Loading prompt templates..."))

        templates = self.get_templates()
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for template_data in templates:
                template, created = PromptTemplate.objects.update_or_create(
                    name=template_data["name"],
                    defaults={
                        "template_type": template_data["template_type"],
                        "system_prompt": template_data["system_prompt"],
                        "user_prompt_template": template_data["user_prompt_template"],
                        "output_format_instructions": template_data.get(
                            "output_format_instructions", ""
                        ),
                        "version": template_data.get("version", 1),
                        "is_active": template_data.get("is_active", True),
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Created: {template.name}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"  🔄 Updated: {template.name}"))

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Done! Created: {created_count}, Updated: {updated_count}")
        )

    def get_templates(self):
        """Return all 7 template definitions"""
        return [
            # PHASE 1: CONCEPT & IDEA
            {
                "name": "premise_generator",
                "template_type": "concept",
                "system_prompt": "You are a professional story consultant helping an author develop their book concept.",
                "user_prompt_template": """# Task: Generate Story Premise

## Book Information:
- **Working Title:** {{ project.title }}
- **Genre:** {{ project.genre }}
- **Target Length:** {{ target_length|default('novel') }}
{% if description %}
- **Description:** {{ description }}
{% endif %}
{% if inspiration %}
- **Inspiration:** {{ inspiration }}
{% endif %}

## Your Task:

Generate a compelling story premise that includes:

1. **PREMISE** (2-3 paragraphs)
   - What is the story about?
   - What is the main conflict?
   - What are the stakes?
   - Why would readers care?

2. **PREMISE_SHORT** (1 sentence)
   - Distill the premise to its essence

3. **ELEVATOR_PITCH** (30 seconds)
   - 2-3 sentences maximum

4. **KEY_CONFLICT**
   - Central conflict of the story

5. **PROTAGONIST_SKETCH**
   - Brief sketch of main character

6. **ANTAGONIST_SKETCH**
   - Brief sketch of opposing force

Make the premise:
- Specific and vivid
- Emotionally engaging
- Clear about what makes this story unique
- Appropriate for the {{ project.genre }} genre
- Suitable for a {{ target_length|default('novel') }}""",
                "output_format_instructions": """## Output Format:

Return your response as JSON:

```json
{
  "premise": "Full 2-3 paragraph premise...",
  "premise_short": "One sentence version",
  "premise_elevator": "30 second pitch",
  "key_conflict": "Central conflict description",
  "protagonist_sketch": "Main character sketch",
  "antagonist_sketch": "Opposing force sketch"
}
```""",
                "version": 1,
                "is_active": True,
            },
            {
                "name": "theme_identifier",
                "template_type": "concept",
                "system_prompt": "You are a literary analyst helping an author identify the themes in their story.",
                "user_prompt_template": """# Task: Identify Story Themes

## Book Information:
- **Title:** {{ project.title }}
- **Genre:** {{ project.genre }}

## Premise:
{{ premise }}

{% if additional_context %}
## Additional Context:
{{ additional_context }}
{% endif %}

## Your Task:

Identify 3-5 themes that this story explores. For each theme:

1. **NAME** - What is the theme?
2. **DESCRIPTION** - What does this theme mean in this story?
3. **HOW_EXPLORED** - How will it be explored through plot and characters?

Focus on:
- Universal themes that resonate with readers
- Themes that naturally emerge from the premise
- Themes appropriate for the genre
- Clear primary theme (most important)
- 2-4 secondary themes (support primary)""",
                "output_format_instructions": """## Output Format:

Return your response as JSON:

```json
{
  "primary_theme": "Main theme name",
  "secondary_themes": ["Theme 2", "Theme 3"],
  "themes": [
    {
      "name": "Theme Name",
      "description": "What this theme means",
      "how_explored": "How it will be shown"
    }
  ]
}
```""",
                "version": 1,
                "is_active": True,
            },
            {
                "name": "logline_generator",
                "template_type": "concept",
                "system_prompt": "You are a professional pitch consultant helping an author create a compelling logline.",
                "user_prompt_template": """# Task: Generate Logline

A logline is a one-sentence summary that captures:
- WHO the protagonist is
- WHAT they want
- WHO/WHAT opposes them
- WHAT's at stake

## Book Information:
- **Title:** {{ project.title }}
- **Genre:** {{ project.genre }}

## Premise:
{{ premise }}

## Desired Style: {{ style|default('concise') }}

## Your Task:

Create a compelling logline that:
- Is ONE sentence (approximately 25 words)
- Includes protagonist, goal, opposition, and stakes
- Hooks the reader immediately
- Matches the {{ style|default('concise') }} style
- Avoids clichés

Also provide:
- 3 alternative versions (different angles)
- Analysis of what makes the main logline effective""",
                "output_format_instructions": """## Output Format:

Return your response as JSON:

```json
{
  "logline": "Main logline (one sentence, ~25 words)",
  "logline_variations": [
    "Alternative version 1",
    "Alternative version 2",
    "Alternative version 3"
  ],
  "hook_analysis": "What makes this logline compelling"
}
```""",
                "version": 1,
                "is_active": True,
            },
            # PHASE 5: CHAPTER PLANNING
            {
                "name": "chapter_structure",
                "template_type": "chapter_planning",
                "system_prompt": "You are a professional story consultant helping an author plan a chapter in detail.",
                "user_prompt_template": """# Task: Plan Chapter Structure

## Book Information:
- **Title:** {{ project.title }}
- **Genre:** {{ project.genre }}
- **Chapter Number:** {{ chapter_number }}

## Premise:
{{ premise }}

{% if outline %}
## Story Outline:
{{ outline }}
{% endif %}

{% if previous_chapters %}
## Previous Chapters:
{% for ch in previous_chapters %}
- Chapter {{ ch.chapter_number }}: {{ ch.title }}
{% endfor %}
{% endif %}

## Your Task:

Plan the structure for Chapter {{ chapter_number }}. Provide:

1. **OPENING** - Where/when chapter starts, opening hook
2. **MIDDLE** - What happens, conflicts, character development
3. **ENDING** - How chapter ends, tension/question left
4. **POV_CHARACTER** - Whose perspective
5. **SETTING** - Where it takes place
6. **TIME_PERIOD** - When/timing
7. **SCENE_COUNT** - How many scenes (2-5)
8. **ESTIMATED_WORD_COUNT** - Target (2000-5000)

Make it specific, actionable, and story-driven.""",
                "output_format_instructions": """## Output Format:

```json
{
  "structure": {
    "opening": "...",
    "middle": "...",
    "ending": "...",
    "pov_character": "...",
    "setting": "...",
    "time_period": "..."
  },
  "scene_count": 3,
  "estimated_word_count": 3000
}
```""",
                "version": 1,
                "is_active": True,
            },
            {
                "name": "chapter_hook",
                "template_type": "chapter_planning",
                "system_prompt": "You are a master storyteller crafting the perfect opening for a chapter.",
                "user_prompt_template": """# Task: Create Compelling Chapter Hook

## Chapter {{ chapter_number }}:
- **Book:** {{ project.title }}
- **Genre:** {{ project.genre }}
- **Hook Type:** {{ hook_type|default('action') }}

{% if chapter_structure %}
## Chapter Plan:
- **Opening:** {{ chapter_structure.opening }}
- **POV:** {{ chapter_structure.pov_character }}
- **Setting:** {{ chapter_structure.setting }}
{% endif %}

## Your Task:

Create a compelling opening hook (1-2 paragraphs, ~150 words) that immediately engages the reader.

Provide:
- Main hook text
- 3 alternative variations
- Analysis of effectiveness
- Opening visual image""",
                "output_format_instructions": """## Output Format:

```json
{
  "hook": "Main hook (1-2 paragraphs)",
  "hook_variations": ["Alt 1", "Alt 2", "Alt 3"],
  "hook_analysis": "Why effective",
  "opening_image": "Visual description"
}
```""",
                "version": 1,
                "is_active": True,
            },
            {
                "name": "chapter_goal",
                "template_type": "chapter_planning",
                "system_prompt": "You are a story consultant helping an author understand what this chapter needs to accomplish.",
                "user_prompt_template": """# Task: Define Chapter Goal & Purpose

## Book Information:
- **Title:** {{ project.title }}
- **Genre:** {{ project.genre }}
- **Chapter:** {{ chapter_number }}

## Premise:
{{ premise }}

{% if chapter_structure %}
## Chapter Structure:
- Opening: {{ chapter_structure.opening|truncate(200) }}
- Middle: {{ chapter_structure.middle|truncate(200) }}
- Ending: {{ chapter_structure.ending|truncate(200) }}
{% endif %}

## Your Task:

Define what Chapter {{ chapter_number }} must accomplish:

1. **CHAPTER_GOAL** - Specific objective
2. **PLOT_PROGRESSION** - How story advances
3. **CHARACTER_DEVELOPMENT** - How characters change
4. **CONFLICTS** - List 2-3 conflicts
5. **STAKES** - What's at risk
6. **NEXT_CHAPTER_SETUP** - What this sets up""",
                "output_format_instructions": """## Output Format:

```json
{
  "chapter_goal": "...",
  "plot_progression": "...",
  "character_development": "...",
  "conflicts": ["Conflict 1", "Conflict 2"],
  "stakes": "...",
  "next_chapter_setup": "..."
}
```""",
                "version": 1,
                "is_active": True,
            },
            # PHASE 6: QUALITY FEEDBACK
            {
                "name": "chapter_review",
                "template_type": "quality_feedback",
                "system_prompt": "You are an experienced editor reviewing a chapter for publication quality.",
                "user_prompt_template": """# Task: Review Chapter Quality

## Chapter Information:
- **Book:** {{ project.title }}
- **Genre:** {{ project.genre }}
- **Chapter:** {{ chapter.number }} - {{ chapter.title }}
- **Word Count:** {{ chapter.word_count }}
- **Review Type:** {{ review_type|upper }}

## Chapter Content:
```
{{ chapter.content|truncate(4000) }}
```

## Your Task:

Provide comprehensive chapter review:

1. **OVERALL_SCORE** - Rate 1-10
2. **STRENGTHS** - 3-5 key strengths
3. **WEAKNESSES** - 3-5 areas for improvement
4. **SUGGESTIONS** - 5-7 specific, actionable improvements with:
   - Issue identified
   - Location in chapter
   - Severity (low/medium/high)
   - How to fix
5. **DETAILED_FEEDBACK** by area:
   - Structure
   - Prose
   - Dialogue
   - Pacing
   - Consistency

Be constructive, specific, and actionable.""",
                "output_format_instructions": """## Output Format:

```json
{
  "overall_score": 7,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "suggestions": [
    {
      "issue": "...",
      "location": "...",
      "severity": "medium",
      "fix": "..."
    }
  ],
  "detailed_feedback": {
    "structure": "...",
    "prose": "...",
    "dialogue": "...",
    "pacing": "...",
    "consistency": "..."
  }
}
```""",
                "version": 1,
                "is_active": True,
            },
        ]
