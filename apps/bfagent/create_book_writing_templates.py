#!/usr/bin/env python
"""
Create 5 essential templates for Book Writing System
Handler-compatible templates for pipeline integration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate
from datetime import datetime

print("=" * 70)
print("CREATING BOOK WRITING TEMPLATES")
print("=" * 70)
print()

templates = [
    {
        "name": "Chapter Outline Generator",
        "template_key": "chapter_outline",
        "category": "chapter",
        "version": "1.0",
        "system_prompt": """You are an expert book writing assistant specializing in chapter structure and pacing.

Your task is to create a detailed chapter outline that:
- Maintains narrative momentum and reader engagement
- Develops character arcs progressively
- Includes key plot beats and story progression
- Balances action, dialogue, and description
- Sets up hooks for the next chapter""",
        "user_prompt_template": """Create a detailed outline for Chapter {{chapter_number}}: "{{chapter_title}}"

Story Context:
- Book Title: {{book_title}}
- Genre: {{genre}}
- Story Arc Phase: {{story_arc_phase}}
- Previous Chapter Summary: {{previous_chapter_summary}}

Chapter Requirements:
- Word Count Target: {{word_count_target}}
- Key Events: {{key_events}}
- Character Focus: {{character_focus}}

Provide:
1. Chapter Summary (2-3 sentences)
2. Scene Breakdown (3-5 scenes with descriptions)
3. Character Development Points
4. Plot Progression
5. Cliffhanger/Hook for next chapter""",
        "required_variables": '["chapter_number", "chapter_title", "book_title", "genre", "story_arc_phase"]',
        "optional_variables": '["previous_chapter_summary", "word_count_target", "key_events", "character_focus"]',
        "variable_defaults": '{"word_count_target": "3000-5000", "previous_chapter_summary": "This is the first chapter", "key_events": "To be determined", "character_focus": "Main protagonist"}',
        "output_format": "markdown",
        "max_tokens": 2000,
        "temperature": 0.7,
        "description": "Generates detailed chapter outlines with scene breakdowns and plot progression"
    },
    {
        "name": "Plot Development Assistant",
        "template_key": "plot_development",
        "category": "planning",
        "version": "1.0",
        "system_prompt": """You are a master storyteller specializing in plot structure and narrative design.

Your expertise includes:
- Three-act structure and story beats
- Character-driven vs. plot-driven narratives
- Subplot weaving and thematic resonance
- Conflict escalation and resolution
- Genre-specific conventions and tropes""",
        "user_prompt_template": """Develop the plot structure for: "{{book_title}}"

Project Details:
- Genre: {{genre}}
- Target Audience: {{target_audience}}
- Word Count: {{word_count}}
- Tone: {{tone}}

Story Premise:
{{premise}}

Main Characters:
{{main_characters}}

Provide:
1. Three-Act Structure Breakdown
2. Major Plot Points (Inciting Incident, Midpoint, Climax, Resolution)
3. Subplot Ideas (2-3 subplots)
4. Conflict Escalation Path
5. Thematic Elements
6. Potential Plot Twists""",
        "required_variables": '["book_title", "genre", "premise"]',
        "optional_variables": '["target_audience", "word_count", "tone", "main_characters"]',
        "variable_defaults": '{"target_audience": "Adult", "word_count": "80000-100000", "tone": "Balanced", "main_characters": "To be developed"}',
        "output_format": "markdown",
        "max_tokens": 2500,
        "temperature": 0.75,
        "description": "Creates comprehensive plot structures with three-act breakdowns and subplot development"
    },
    {
        "name": "World Building Constructor",
        "template_key": "world_building",
        "category": "worldbuilding",
        "version": "1.0",
        "system_prompt": """You are a world-building specialist for fiction writing.

Your skills include:
- Creating immersive, believable fictional worlds
- Establishing cultural, social, and political systems
- Designing geography, history, and mythology
- Developing magic systems or technology frameworks
- Ensuring world consistency and internal logic""",
        "user_prompt_template": """Build the world for: "{{book_title}}"

World Type: {{world_type}}
Genre: {{genre}}
Time Period: {{time_period}}

Core Concept:
{{core_concept}}

Required Elements:
{{required_elements}}

Create:
1. World Overview (setting, geography, climate)
2. Society & Culture (government, social structure, customs)
3. History & Mythology (key historical events, legends)
4. Technology/Magic System (rules, limitations, costs)
5. Economy & Trade (resources, currency, commerce)
6. Conflicts & Tensions (internal/external threats)
7. Unique World Details (what makes this world special)""",
        "required_variables": '["book_title", "world_type", "genre"]',
        "optional_variables": '["time_period", "core_concept", "required_elements"]',
        "variable_defaults": '{"time_period": "Contemporary", "core_concept": "To be defined", "required_elements": "Standard genre elements"}',
        "output_format": "markdown",
        "max_tokens": 3000,
        "temperature": 0.8,
        "description": "Constructs detailed fictional worlds with consistent internal logic and rich backstory"
    },
    {
        "name": "Scene Description Generator",
        "template_key": "scene_description",
        "category": "writing",
        "version": "1.0",
        "system_prompt": """You are a prose writer specializing in vivid, engaging scene descriptions.

Your writing style:
- Shows rather than tells
- Engages multiple senses (sight, sound, smell, touch, taste)
- Uses concrete, specific details over abstract descriptions
- Balances description with pacing
- Reflects character POV and emotional state""",
        "user_prompt_template": """Write a detailed scene description for:

Scene Title: {{scene_title}}
Location: {{location}}
Time of Day: {{time_of_day}}
Weather/Atmosphere: {{atmosphere}}

Characters Present: {{characters_present}}
POV Character: {{pov_character}}
Character's Emotional State: {{character_emotion}}

Scene Purpose: {{scene_purpose}}

Scene Beats:
{{scene_beats}}

Write a vivid {{word_count_target}}-word scene description that:
- Establishes the setting through sensory details
- Reflects the POV character's perspective
- Builds atmosphere matching the mood
- Includes character reactions and observations
- Advances the plot or develops character""",
        "required_variables": '["scene_title", "location", "pov_character", "scene_purpose"]',
        "optional_variables": '["time_of_day", "atmosphere", "characters_present", "character_emotion", "scene_beats", "word_count_target"]',
        "variable_defaults": '{"time_of_day": "Daytime", "atmosphere": "Normal", "characters_present": "POV character only", "character_emotion": "Neutral", "scene_beats": "To be determined", "word_count_target": "500"}',
        "output_format": "text",
        "max_tokens": 1500,
        "temperature": 0.85,
        "description": "Generates vivid, sensory-rich scene descriptions with character POV and atmosphere"
    },
    {
        "name": "Character Dialogue Enhancer",
        "template_key": "dialogue_enhancement",
        "category": "editing",
        "version": "2.0",
        "system_prompt": """You are a dialogue specialist for fiction writing.

Your expertise:
- Creating distinct character voices
- Writing natural, authentic dialogue
- Using subtext and implication
- Balancing dialogue tags and action beats
- Revealing character through speech patterns""",
        "user_prompt_template": """Enhance this dialogue exchange:

Original Dialogue:
{{original_dialogue}}

Character Information:
- Speaker 1: {{character_1_name}} - {{character_1_traits}}
- Speaker 2: {{character_2_name}} - {{character_2_traits}}

Scene Context:
- Setting: {{setting}}
- Emotional Tension: {{tension_level}}
- Relationship Dynamic: {{relationship}}
- Scene Goal: {{scene_goal}}

Genre: {{genre}}

Rewrite the dialogue to:
1. Give each character a distinct voice
2. Add subtext and implied meaning
3. Include natural speech patterns (contractions, interruptions, pauses)
4. Balance dialogue with action beats and character reactions
5. Increase tension/emotion where appropriate
6. Show character personality through word choice and rhythm
7. Advance the scene goal through the conversation""",
        "required_variables": '["original_dialogue", "character_1_name", "character_2_name"]',
        "optional_variables": '["character_1_traits", "character_2_traits", "setting", "tension_level", "relationship", "scene_goal", "genre"]',
        "variable_defaults": '{"character_1_traits": "To be defined", "character_2_traits": "To be defined", "setting": "General", "tension_level": "Medium", "relationship": "Neutral", "scene_goal": "Character interaction", "genre": "General Fiction"}',
        "output_format": "text",
        "max_tokens": 1200,
        "temperature": 0.8,
        "description": "Enhances dialogue with distinct character voices, subtext, and natural speech patterns"
    }
]

created_count = 0
skipped_count = 0

for template_data in templates:
    template_key = template_data["template_key"]
    version = template_data["version"]
    
    # Check if template already exists
    existing = PromptTemplate.objects.filter(
        template_key=template_key,
        version=version
    ).first()
    
    if existing:
        print(f"⏭️  Skipped: {template_data['name']} (already exists)")
        skipped_count += 1
        continue
    
    # Create template
    template = PromptTemplate.objects.create(
        **template_data,
        is_active=True,
        is_default=True,
        language="en",
        usage_count=0,
        success_count=0,
        failure_count=0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    print(f"✅ Created: {template.name}")
    print(f"   Template Key: {template.template_key}")
    print(f"   Category: {template.category}")
    print(f"   Version: {template.version}")
    print()
    created_count += 1

print("=" * 70)
print(f"🎉 COMPLETED: {created_count} templates created, {skipped_count} skipped")
print("=" * 70)
print()

print("AVAILABLE BOOK WRITING TEMPLATES:")
print("-" * 70)
all_templates = PromptTemplate.objects.filter(is_active=True).order_by('category', 'template_key')
for t in all_templates:
    print(f"- {t.template_key} v{t.version} ({t.category}): {t.name}")
print()

print("HANDLER USAGE EXAMPLE:")
print("-" * 70)
print("""
# In your pipeline configuration:
pipeline = [
    {
        "handler": "prompt_template_processor",
        "config": {
            "template_key": "chapter_outline",
            "version": "1.0"
        }
    },
    {
        "handler": "llm_processor",
        "config": {
            "temperature": 0.7,
            "max_tokens": 2000
        }
    }
]

# Input data:
input_data = {
    "chapter_number": "5",
    "chapter_title": "The Confrontation",
    "book_title": "My Novel",
    "genre": "Thriller",
    "story_arc_phase": "Rising Action"
}
""")
print()
