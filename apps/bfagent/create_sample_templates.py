#!/usr/bin/env python
"""
Create sample templates for Prompt Management System v2.0
Demonstrates new features: template_key, semantic versioning, execution tracking
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import PromptTemplate
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("CREATING SAMPLE TEMPLATES FOR PROMPT SYSTEM V2.0")
print("=" * 70)
print()

# Get or create user
user = User.objects.first()
if not user:
    print("Creating demo user...")
    user = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )

# Sample Template 1: Character Generation
print("1️⃣  Creating Character Generation Template...")
char_template = PromptTemplate.objects.create(
    template_key="character_generation",
    version="1.0",
    name="Character Generation - Standard",
    description="Generates detailed character profiles for fiction writing",
    category="character",
    system_prompt="You are an expert character development assistant for fiction writers.",
    user_prompt_template="""Create a detailed character profile with the following elements:
- Name: {{character_name}}
- Role: {{character_role}}
- Genre: {{genre}}

Include: personality traits, background, motivations, conflicts, and unique characteristics.""",
    required_variables='["character_name", "character_role", "genre"]',
    optional_variables='["age", "gender", "occupation"]',
    variable_defaults='{"age": "30-35", "gender": "not specified"}',
    output_format="json",
    output_schema='{"name": "string", "personality": "string", "background": "string", "motivations": "array", "conflicts": "array"}',
    temperature=0.8,
    max_tokens=1000,
    top_p=0.9,
    is_active=True,
    is_default=True,
    created_by=user
)
print(f"   ✅ Created: {char_template.template_key} v{char_template.version}")

# Sample Template 2: Chapter Outline
print("2️⃣  Creating Chapter Outline Template...")
chapter_template = PromptTemplate.objects.create(
    template_key="chapter_outline",
    version="1.0",
    name="Chapter Outline Generator",
    description="Creates structured chapter outlines with story beats",
    category="chapter",
    system_prompt="You are an expert story structure consultant.",
    user_prompt_template="""Generate a chapter outline for:
- Chapter Number: {{chapter_number}}
- Story Arc: {{story_arc}}
- Previous Events: {{previous_events}}

Create 5-7 story beats with emotional arcs and character development.""",
    required_variables='["chapter_number", "story_arc"]',
    optional_variables='["previous_events", "target_word_count"]',
    variable_defaults='{"target_word_count": "3000"}',
    output_format="json",
    temperature=0.7,
    max_tokens=800,
    top_p=0.85,
    is_active=True,
    created_by=user
)
print(f"   ✅ Created: {chapter_template.template_key} v{chapter_template.version}")

# Sample Template 3: Dialogue Enhancement
print("3️⃣  Creating Dialogue Enhancement Template...")
dialogue_template = PromptTemplate.objects.create(
    template_key="dialogue_enhancement",
    version="1.1.0",  # Semantic versioning!
    name="Dialogue Enhancement - Natural Speech",
    description="Improves dialogue to sound more natural and character-specific",
    category="editing",
    system_prompt="You are a dialogue coach specializing in natural, character-driven conversation.",
    user_prompt_template="""Enhance this dialogue:
{{original_dialogue}}

Character Voice Guidelines:
- Character: {{character_name}}
- Personality: {{personality_traits}}
- Background: {{background}}

Make it sound natural and true to the character.""",
    required_variables='["original_dialogue", "character_name"]',
    optional_variables='["personality_traits", "background", "dialect"]',
    temperature=0.75,
    max_tokens=500,
    is_active=True,
    created_by=user
)
print(f"   ✅ Created: {dialogue_template.template_key} v{dialogue_template.version}")

# Sample Template 4: Beta Version (A/B Testing)
print("4️⃣  Creating Beta Template (for A/B testing)...")
char_template_beta = PromptTemplate.objects.create(
    template_key="character_generation",  # Same key!
    version="2.0-beta",  # Semantic version with pre-release
    name="Character Generation - Enhanced (Beta)",
    description="Enhanced version with psychological depth analysis",
    category="character",
    system_prompt="You are an expert character psychologist and fiction consultant.",
    user_prompt_template="""Create an in-depth character profile:
- Name: {{character_name}}
- Role: {{character_role}}
- Genre: {{genre}}

Include: personality (Myers-Briggs), psychological depth, character arc potential, 
relationship dynamics, and unique voice characteristics.""",
    required_variables='["character_name", "character_role", "genre"]',
    optional_variables='["age", "gender", "occupation", "myers_briggs"]',
    variable_defaults='{"age": "30-35"}',
    output_format="json",
    temperature=0.85,
    max_tokens=1500,
    top_p=0.92,
    is_active=True,
    ab_test_group="character_gen_enhanced",
    ab_test_weight=0.2,  # 20% of traffic
    created_by=user
)
print(f"   ✅ Created: {char_template_beta.template_key} v{char_template_beta.version} (A/B Test)")

print()
print("=" * 70)
print("✅ SAMPLE TEMPLATES CREATED!")
print("=" * 70)
print()
print("CREATED:")
print(f"  • {PromptTemplate.objects.count()} templates")
print()
print("NEXT STEPS:")
print("1. Test template lookup by key:")
print("   template = PromptTemplate.objects.get(template_key='character_generation')")
print()
print("2. Use semantic versioning:")
print("   stable = PromptTemplate.objects.get(template_key='character_generation', version='1.0')")
print("   beta = PromptTemplate.objects.get(template_key='character_generation', version='2.0-beta')")
print()
print("3. Start tracking executions with PromptExecution model")
print("4. Set up A/B testing with PromptTemplateTest")
print()
