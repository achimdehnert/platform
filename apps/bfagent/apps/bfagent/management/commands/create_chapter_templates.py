"""
Management command to create chapter generation prompt templates
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import PromptTemplate


class Command(BaseCommand):
    help = 'Create prompt templates for chapter generation'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("📝 Creating Chapter Generation Prompt Templates")
        self.stdout.write("=" * 80)

        templates = [
            {
                'name': 'Chapter Outline Generator',
                'template_key': 'chapter_outline_generation',
                'category': 'chapter',
                'system_prompt': '''You are a professional fiction writing assistant specialized in story structure and chapter planning.
Your task is to create detailed chapter outlines that serve as blueprints for compelling narrative chapters.''',
                'user_prompt_template': '''Create a detailed outline for Chapter {{chapter_number}}: "{{chapter_title}}"

PROJECT CONTEXT:
- Title: {{title}}
- Genre: {{genre}}
- Premise: {{premise}}
- Themes: {{themes}}
- Target Audience: {{target_audience}}

MAIN CHARACTERS:
- Protagonist: {{protagonist_name}}
  {{protagonist_description}}
- Antagonist: {{antagonist_name}}
  {{antagonist_description}}

STORY POSITION:
- Chapter {{chapter_number}} of the story
- Story Position: {{story_position}}
- Current Beat: {{current_beat_name}}

CHAPTER REQUIREMENTS:
- Chapter Number: {{chapter_number}}
- Title: {{chapter_title}}
- Target Word Count: {{word_count}}
- Plot Points to Address: {{plot_points}}

Please provide a structured outline with:
1. 3-4 main sections with headings
2. Brief description for each section
3. Key elements to include
4. Estimated word count per section

IMPORTANT: Follow the established character roles and descriptions exactly. Pay close attention to the premise and character backgrounds.

Format your response as a clear, structured outline.''',
                'required_variables': ['chapter_number', 'chapter_title', 'title', 'genre'],
                'optional_variables': ['premise', 'themes', 'target_audience', 'protagonist_name', 
                                      'protagonist_description', 'antagonist_name', 'antagonist_description',
                                      'story_position', 'current_beat_name', 'word_count', 'plot_points'],
                'variable_defaults': {
                    'word_count': 3000,
                    'plot_points': 'General story progression',
                    'premise': 'N/A',
                    'themes': 'N/A',
                    'target_audience': 'Adult',
                    'protagonist_name': 'the protagonist',
                    'protagonist_description': 'Main character',
                    'antagonist_name': 'the antagonist',
                    'antagonist_description': 'Opposition force',
                    'story_position': 'N/A',
                    'current_beat_name': 'N/A',
                },
                'max_tokens': 1000,
                'temperature': 0.7,
                'is_active': True,
                'is_default': True,
                'description': 'Generates detailed chapter outlines based on project context and story position',
            },
            {
                'name': 'Chapter Content Generator',
                'template_key': 'chapter_content_generation',
                'category': 'chapter',
                'system_prompt': '''You are a professional fiction writer with expertise in crafting compelling narrative prose.
Your task is to write engaging chapter content based on a detailed outline, maintaining consistent character voices and story themes.
Write in a vivid, immersive style that draws readers into the story.''',
                'user_prompt_template': '''Write Chapter {{chapter_number}} based on the following outline and context.

PROJECT CONTEXT:
- Title: {{title}}
- Genre: {{genre}}
- Premise: {{premise}}
- Themes: {{themes}}
- Target Audience: {{target_audience}}

MAIN CHARACTERS:
- Protagonist: {{protagonist_name}}
  {{protagonist_description}}
- Antagonist: {{antagonist_name}}

CHAPTER OUTLINE:
{{outline}}

WRITING REQUIREMENTS:
- Write in third person limited perspective, focusing on {{protagonist_name}}
- Target length: Approximately {{word_count}} words for the complete chapter
- Include dialogue: {{include_dialogue}}
- Style: {{style_notes}}
- Maintain consistency with the premise: the story explores themes of {{themes}}

IMPORTANT:
- Follow the outline structure closely
- Show don't tell - use vivid sensory details
- Develop characters through actions and dialogue
- Create emotional resonance with readers
- Maintain proper pacing throughout

Write the complete chapter now, following the outline sections:''',
                'required_variables': ['chapter_number', 'title', 'genre', 'outline', 'protagonist_name'],
                'optional_variables': ['premise', 'themes', 'target_audience', 'protagonist_description',
                                      'antagonist_name', 'word_count', 'include_dialogue', 'style_notes'],
                'variable_defaults': {
                    'premise': 'N/A',
                    'themes': 'N/A',
                    'target_audience': 'Adult',
                    'protagonist_description': 'Main character',
                    'antagonist_name': 'the antagonist',
                    'word_count': 2500,
                    'include_dialogue': 'Yes, include natural, character-appropriate dialogue',
                    'style_notes': 'Engaging literary fiction style with vivid descriptions and emotional depth',
                },
                'max_tokens': 4000,
                'temperature': 0.8,
                'is_active': True,
                'is_default': True,
                'description': 'Generates full chapter content in prose form based on outline and project context',
            },
            {
                'name': 'Chapter Section Expander',
                'template_key': 'chapter_section_expansion',
                'category': 'chapter',
                'system_prompt': '''You are a professional fiction writer specializing in descriptive prose and scene development.
Your task is to expand brief section outlines into rich, detailed narrative prose that immerses readers in the story world.''',
                'user_prompt_template': '''Expand the following chapter section into detailed prose.

PROJECT CONTEXT:
- Title: {{title}}
- Genre: {{genre}}
- Themes: {{themes}}

CHARACTER FOCUS:
- {{protagonist_name}}: {{protagonist_description}}

SECTION TO EXPAND:
{{section_outline}}

REQUIREMENTS:
- Target length: {{section_word_count}} words
- Perspective: Third person limited, focusing on {{protagonist_name}}
- Include dialogue: {{include_dialogue}}
- Tone: {{tone}}

IMPORTANT:
- Use vivid sensory details
- Show character emotions through actions and body language
- Maintain the story's themes: {{themes}}
- Keep pacing appropriate for the scene

Write the expanded section now:''',
                'required_variables': ['section_outline', 'protagonist_name', 'title', 'genre'],
                'optional_variables': ['themes', 'protagonist_description', 'section_word_count',
                                      'include_dialogue', 'tone'],
                'variable_defaults': {
                    'themes': 'N/A',
                    'protagonist_description': 'Main character',
                    'section_word_count': 750,
                    'include_dialogue': 'Yes',
                    'tone': 'Engaging and immersive',
                },
                'max_tokens': 2000,
                'temperature': 0.8,
                'is_active': True,
                'is_default': False,
                'description': 'Expands individual chapter sections with rich descriptive prose',
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = PromptTemplate.objects.update_or_create(
                template_key=template_data['template_key'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created: {template.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated: {template.name}'))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(
            f'✅ Complete! Created: {created_count}, Updated: {updated_count}'
        ))
        self.stdout.write("=" * 80)
