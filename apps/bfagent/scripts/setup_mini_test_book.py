#!/usr/bin/env python
"""
Setup Mini Test Book Workflow
Creates a simple 3-phase book type for testing the complete workflow.
"""
import os
import sys
import django

# Setup Django FIRST
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

# NOW import models AFTER Django is initialized
from apps.bfagent.models import (
    Agents,
    AgentAction,
    BookTypes,
    BookTypePhase,
    PhaseActionConfig,
    PromptTemplate,
    WorkflowPhase,
)


def create_mini_test_workflow():
    """Create Mini Story Book workflow with 3 phases"""
    
    print("\n" + "="*60)
    print("🎯 CREATING MINI TEST BOOK WORKFLOW")
    print("="*60 + "\n")
    
    # =========================================================================
    # STEP 1: Get or Create Agents
    # =========================================================================
    print("📝 Step 1: Setting up Agents...")
    
    story_agent, _ = Agents.objects.get_or_create(
        name="Story Planning Agent",
        defaults={
            "agent_type": "outline",
            "description": "Creates story outlines",
            "status": "active",
        }
    )
    
    character_agent, _ = Agents.objects.get_or_create(
        name="Character Design Agent",
        defaults={
            "agent_type": "character",
            "description": "Designs characters",
            "status": "active",
        }
    )
    
    writing_agent, _ = Agents.objects.get_or_create(
        name="Story Writing Agent",
        defaults={
            "agent_type": "writing",
            "description": "Writes complete stories",
            "status": "active",
        }
    )
    
    print(f"  ✅ Story Agent: {story_agent.name}")
    print(f"  ✅ Character Agent: {character_agent.name}")
    print(f"  ✅ Writing Agent: {writing_agent.name}")
    
    # =========================================================================
    # STEP 2: Get or Create Workflow Phases
    # =========================================================================
    print("\n📊 Step 2: Setting up Workflow Phases...")
    
    phase_planning, _ = WorkflowPhase.objects.get_or_create(
        name="Story Planning",
        defaults={
            "description": "Plan the story outline",
            "icon": "file-text",
            "color": "info",
        }
    )
    
    phase_character, _ = WorkflowPhase.objects.get_or_create(
        name="Character Design",
        defaults={
            "description": "Design main character",
            "icon": "person",
            "color": "warning",
        }
    )
    
    phase_writing, _ = WorkflowPhase.objects.get_or_create(
        name="Story Writing",
        defaults={
            "description": "Write the complete story",
            "icon": "pen",
            "color": "success",
        }
    )
    
    print(f"  ✅ Phase 1: {phase_planning.name}")
    print(f"  ✅ Phase 2: {phase_character.name}")
    print(f"  ✅ Phase 3: {phase_writing.name}")
    
    # =========================================================================
    # STEP 3: Create Templates
    # =========================================================================
    print("\n📄 Step 3: Creating Prompt Templates...")
    
    # Template 1: Story Outline
    template_outline, created = PromptTemplate.objects.get_or_create(
        name="Mini Story Outline Generator",
        defaults={
            "description": "Generates a simple 3-5 sentence story outline for children",
            "agent": story_agent,
            "template_text": """You are a children's story planner.

Create a simple, magical story outline (3-5 sentences) for a children's book about:
- A child discovering something magical
- A simple problem to solve
- A happy ending with a lesson

Make it fun, age-appropriate (6-8 years), and engaging!

OUTPUT FORMAT:
Return ONLY the story outline, no extra text.""",
            "version": 1,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {template_outline.name}")
    
    # Template 2: Character Design
    template_character, created = PromptTemplate.objects.get_or_create(
        name="Mini Character Designer",
        defaults={
            "description": "Creates a simple main character profile",
            "agent": character_agent,
            "template_text": """You are a character designer for children's books.

Create a simple main character for the story with:
- Name (fun and memorable)
- Age (6-10 years old)
- One special personality trait
- One magical ability or special item

Make the character relatable and exciting for young readers!

OUTPUT FORMAT:
Name: [character name]
Age: [age]
Trait: [one personality trait]
Special: [magical ability or item]
Brief Description: [2-3 sentences about the character]""",
            "version": 1,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {template_character.name}")
    
    # Template 3: Story Writing
    template_story, created = PromptTemplate.objects.get_or_create(
        name="Mini Story Writer",
        defaults={
            "description": "Writes a complete short story (200-300 words)",
            "agent": writing_agent,
            "template_text": """You are a children's story writer.

Using the following information, write a complete short story (200-300 words):

**Story Outline:**
{story_outline}

**Main Character:**
{main_character}

Write an engaging, age-appropriate story (6-8 years) with:
- Clear beginning, middle, and end
- Simple, vivid language
- Dialogue between characters
- A positive message or lesson

OUTPUT FORMAT:
Return ONLY the complete story, no extra text or explanations.""",
            "version": 1,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {template_story.name}")
    
    # =========================================================================
    # STEP 4: Create Actions
    # =========================================================================
    print("\n⚡ Step 4: Creating Agent Actions...")
    
    # Action 1: Create Outline
    action_outline, created = AgentAction.objects.get_or_create(
        name="create_story_outline",
        defaults={
            "display_name": "Create Story Outline",
            "description": "Generate a simple story outline",
            "agent": story_agent,
            "prompt_template": template_outline,
            "target_model": "project",
            "target_fields": ["synopsis"],  # Using existing field
            "is_active": True,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {action_outline.display_name}")
    print(f"     → Saves to: project.{action_outline.target_fields[0]}")
    
    # Action 2: Design Character
    action_character, created = AgentAction.objects.get_or_create(
        name="design_main_character",
        defaults={
            "display_name": "Design Main Character",
            "description": "Create the protagonist",
            "agent": character_agent,
            "prompt_template": template_character,
            "target_model": "project",
            "target_fields": ["unique_elements"],  # Using existing field
            "is_active": True,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {action_character.display_name}")
    print(f"     → Saves to: project.{action_character.target_fields[0]}")
    
    # Action 3: Write Story
    action_story, created = AgentAction.objects.get_or_create(
        name="write_complete_story",
        defaults={
            "display_name": "Write Complete Story",
            "description": "Write the final story using outline and character",
            "agent": writing_agent,
            "prompt_template": template_story,
            "target_model": "project",
            "target_fields": ["story_content"],  # Using existing field (or create new)
            "is_active": True,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {action_story.display_name}")
    print(f"     → Saves to: project.{action_story.target_fields[0]}")
    
    # =========================================================================
    # STEP 5: Create BookType
    # =========================================================================
    print("\n📚 Step 5: Creating BookType...")
    
    book_type, created = BookTypes.objects.get_or_create(
        name="Mini Story Book (Test)",
        defaults={
            "description": "Simple 3-phase workflow for testing - creates a complete short story",
            "complexity": "beginner",
            "estimated_duration_hours": 1,
            "target_word_count_min": 200,
            "target_word_count_max": 300,
            "is_active": True,
        }
    )
    print(f"  {'✨ Created' if created else '✅ Found'}: {book_type.name}")
    
    # =========================================================================
    # STEP 6: Link Phases to BookType
    # =========================================================================
    print("\n🔗 Step 6: Linking Phases to BookType...")
    
    bt_phase1, created = BookTypePhase.objects.get_or_create(
        book_type=book_type,
        phase=phase_planning,
        defaults={"order": 1}
    )
    print(f"  {'✨ Added' if created else '✅ Found'}: Phase 1 - {phase_planning.name}")
    
    bt_phase2, created = BookTypePhase.objects.get_or_create(
        book_type=book_type,
        phase=phase_character,
        defaults={"order": 2}
    )
    print(f"  {'✨ Added' if created else '✅ Found'}: Phase 2 - {phase_character.name}")
    
    bt_phase3, created = BookTypePhase.objects.get_or_create(
        book_type=book_type,
        phase=phase_writing,
        defaults={"order": 3}
    )
    print(f"  {'✨ Added' if created else '✅ Found'}: Phase 3 - {phase_writing.name}")
    
    # =========================================================================
    # STEP 7: Assign Actions to Phases
    # =========================================================================
    print("\n🎯 Step 7: Assigning Actions to Phases...")
    
    # Phase 1 → Action 1
    config1, created = PhaseActionConfig.objects.get_or_create(
        phase=phase_planning,
        action=action_outline,
        defaults={"order": 1, "is_required": True}
    )
    print(f"  {'✨ Configured' if created else '✅ Found'}: {phase_planning.name} → {action_outline.display_name}")
    
    # Phase 2 → Action 2
    config2, created = PhaseActionConfig.objects.get_or_create(
        phase=phase_character,
        action=action_character,
        defaults={"order": 1, "is_required": True}
    )
    print(f"  {'✨ Configured' if created else '✅ Found'}: {phase_character.name} → {action_character.display_name}")
    
    # Phase 3 → Action 3
    config3, created = PhaseActionConfig.objects.get_or_create(
        phase=phase_writing,
        action=action_story,
        defaults={"order": 1, "is_required": True}
    )
    print(f"  {'✨ Configured' if created else '✅ Found'}: {phase_writing.name} → {action_story.display_name}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*60)
    print("✅ MINI TEST BOOK WORKFLOW READY!")
    print("="*60)
    print(f"""
📚 BookType: {book_type.name}

📋 WORKFLOW:
   Phase 1: {phase_planning.name}
   └─ ⚡ {action_outline.display_name}
      → Saves to: project.synopsis
   
   Phase 2: {phase_character.name}
   └─ ⚡ {action_character.display_name}
      → Saves to: project.unique_elements
   
   Phase 3: {phase_writing.name}
   └─ ⚡ {action_story.display_name}
      → Saves to: project.story_content

🎯 NEXT STEPS:
   1. Create a new project using "Mini Story Book (Test)"
   2. Execute actions in each phase
   3. Check output fields:
      - synopsis (outline)
      - unique_elements (character)
      - story_content (final story)
   
🌐 URL: http://localhost:8000/projects/create/
""")


if __name__ == "__main__":
    create_mini_test_workflow()
