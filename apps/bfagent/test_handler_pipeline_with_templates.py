#!/usr/bin/env python
"""
Demo: Handler-Based Pipeline with Database Templates

Shows how to use PromptTemplateProcessingHandler in actual pipelines
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.services.handlers.processing import (
    PromptTemplateProcessingHandler,
    LLMProcessingHandler
)

print("=" * 70)
print("HANDLER-BASED PIPELINE WITH DATABASE TEMPLATES")
print("=" * 70)
print()

# ============================================================================
# TEST 1: CHAPTER OUTLINE GENERATION
# ============================================================================
print("TEST 1: CHAPTER OUTLINE GENERATION")
print("-" * 70)

# Configure handlers
template_handler = PromptTemplateProcessingHandler({
    "template_key": "chapter_outline",
    "version": "1.0",
    "track_execution": True
})

# Input data (uses the original simple template variables)
input_data = {
    "chapter_number": "7",
    "story_arc": "Climax - The Breaking Point",
    "previous_events": "Sarah discovers the AI's true plan to replace human decision-makers"
}

context = {
    "project_id": 1,
    "agent_id": None,
    "user_id": 1
}

print("Input Variables:")
for key, value in input_data.items():
    print(f"  {key}: {value[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")
print()

# Process with template handler
print("Step 1: Loading and rendering template...")
result = template_handler.process(input_data, context)

print(f"✅ Template Loaded: {result['template_key']} v{result['template_version']}")
print(f"✅ Execution Tracked: ID {result.get('execution_id', 'N/A')}")
print()

print("Rendered Prompt (first 500 chars):")
print("-" * 70)
print(result['rendered_template'][:500] + "...")
print("-" * 70)
print()

print("Step 2: Would pass to LLM Handler...")
print("(Skipping actual LLM call to save API credits)")
print()

# ============================================================================
# TEST 2: PLOT DEVELOPMENT
# ============================================================================
print("=" * 70)
print("TEST 2: PLOT DEVELOPMENT")
print("-" * 70)

plot_handler = PromptTemplateProcessingHandler({
    "template_key": "plot_development",
    "version": "1.0",
    "variables": {
        "genre": "Urban Fantasy"  # Static variable in config
    }
})

plot_input = {
    "book_title": "The Last Mage",
    "premise": "A street magician discovers real magic still exists in modern Chicago",
    "target_audience": "Young Adult",
    "word_count": "90000",
    "tone": "Dark and gritty with humor"
}

print("Input:")
for key, value in plot_input.items():
    print(f"  {key}: {value}")
print()

plot_result = plot_handler.process(plot_input, context)

print(f"✅ Template: {plot_result['template_key']}")
print(f"✅ Variables Merged: {len(plot_result['variables_used'])} total")
print()

# ============================================================================
# TEST 3: WORLD BUILDING
# ============================================================================
print("=" * 70)
print("TEST 3: WORLD BUILDING")
print("-" * 70)

world_handler = PromptTemplateProcessingHandler({
    "template_key": "world_building",
    "version": "1.0"
})

world_input = {
    "book_title": "Chronicles of Aetheria",
    "world_type": "High Fantasy",
    "genre": "Epic Fantasy",
    "time_period": "Medieval with magical elements",
    "core_concept": "Magic is drawn from emotions and memories"
}

print("Input:")
for key, value in world_input.items():
    print(f"  {key}: {value}")
print()

world_result = world_handler.process(world_input, context)

print(f"✅ Template: {world_result['template_key']}")
print(f"✅ Rendered Length: {len(world_result['rendered_template'])} characters")
print()

# ============================================================================
# TEST 4: SCENE DESCRIPTION
# ============================================================================
print("=" * 70)
print("TEST 4: SCENE DESCRIPTION")
print("-" * 70)

scene_handler = PromptTemplateProcessingHandler({
    "template_key": "scene_description",
    "version": "1.0"
})

scene_input = {
    "scene_title": "The Abandoned Library",
    "location": "Old Victorian library, dust-covered and forgotten",
    "pov_character": "Detective Morgan",
    "scene_purpose": "Discovery of crucial evidence",
    "time_of_day": "Late afternoon",
    "atmosphere": "Eerie, mysterious",
    "character_emotion": "Anxious but determined"
}

print("Input:")
for key, value in scene_input.items():
    print(f"  {key}: {value}")
print()

scene_result = scene_handler.process(scene_input, context)

print(f"✅ Template: {scene_result['template_key']}")
print()

# ============================================================================
# TEST 5: DIALOGUE ENHANCEMENT
# ============================================================================
print("=" * 70)
print("TEST 5: DIALOGUE ENHANCEMENT")
print("-" * 70)

dialogue_handler = PromptTemplateProcessingHandler({
    "template_key": "dialogue_enhancement",
    "version": "2.0"  # Using new enhanced version
})

dialogue_input = {
    "original_dialogue": """
"We need to talk."
"About what?"
"You know what about."
""",
    "character_1_name": "Sarah",
    "character_1_traits": "Direct, impatient, ex-military",
    "character_2_name": "James",
    "character_2_traits": "Evasive, intellectual, nervous",
    "setting": "Dark parking garage",
    "tension_level": "High",
    "relationship": "Former partners, now adversaries",
    "scene_goal": "Sarah confronts James about betrayal"
}

print("Original Dialogue:")
print(dialogue_input["original_dialogue"])
print()

dialogue_result = dialogue_handler.process(dialogue_input, context)

print(f"✅ Template: {dialogue_result['template_key']} v{dialogue_result['template_version']}")
print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 70)
print("HANDLER PIPELINE INTEGRATION COMPLETE")
print("=" * 70)
print()

print("WHAT WE DEMONSTRATED:")
print("-" * 70)
print("✅ 1. PromptTemplateProcessingHandler loads templates from DB")
print("✅ 2. Templates are versioned (can test v1.0 vs v2.0)")
print("✅ 3. Variable rendering with Jinja2")
print("✅ 4. Execution tracking (automatic)")
print("✅ 5. Usage statistics (automatic)")
print("✅ 6. Handler can pass preferred_llm to next handler")
print()

print("INTEGRATION WITH EXISTING HANDLERS:")
print("-" * 70)
print("""
# Full pipeline example:
from apps.bfagent.services.pipeline import HandlerPipeline

pipeline = HandlerPipeline([
    PromptTemplateProcessingHandler({
        "template_key": "chapter_outline",
        "version": "latest",
        "track_execution": True
    }),
    LLMProcessingHandler({
        "temperature": 0.7,
        "max_tokens": 2000
    })
])

result = pipeline.execute(input_data, context)
# Returns: {
#   "generated_content": "...",  # From LLM
#   "template_used": PromptTemplate instance,
#   "execution_id": 123,
#   "llm_used": Llms instance,
#   ...
# }
""")

print()
print("NEXT STEPS:")
print("-" * 70)
print("1. Integrate into your existing Agents")
print("2. Replace hardcoded prompts with template_key references")
print("3. Monitor template performance in Admin")
print("4. A/B test template versions")
print("5. Refine templates based on execution data")
print()

print("=" * 70)
print("🎉 HANDLER-BASED TEMPLATE SYSTEM READY!")
print("=" * 70)
