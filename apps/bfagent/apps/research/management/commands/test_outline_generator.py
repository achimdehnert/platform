"""
Test Outline Generator
======================

Management command to test the outline generator.
"""

from django.core.management.base import BaseCommand
from apps.research.services.outline_generator import get_outline_generator


class Command(BaseCommand):
    help = 'Test the outline generator with sample inputs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='book',
            choices=['book', 'paper', 'article'],
            help='Project type'
        )
        parser.add_argument(
            '--framework',
            type=str,
            default='',
            help='Framework to use'
        )
        parser.add_argument(
            '--title',
            type=str,
            default='Test Outline',
            help='Project title'
        )
        parser.add_argument(
            '--genre',
            type=str,
            default='fantasy',
            help='Genre (for books)'
        )
        parser.add_argument(
            '--words',
            type=int,
            default=80000,
            help='Target word count'
        )
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Disable AI enhancement'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🚀 Testing Outline Generator\n'))
        
        generator = get_outline_generator()
        
        project_type = options['type']
        framework = options['framework'] or None
        title = options['title']
        genre = options['genre']
        word_count = options['words']
        use_ai = not options['no_ai']
        
        self.stdout.write(f"Project Type: {project_type}")
        self.stdout.write(f"Framework: {framework or 'auto'}")
        self.stdout.write(f"Title: {title}")
        self.stdout.write(f"Word Count: {word_count:,}")
        self.stdout.write(f"AI Enhancement: {'ON' if use_ai else 'OFF'}")
        self.stdout.write("")
        
        # Build context
        context = {}
        if project_type == 'book':
            context = {
                'genre': genre,
                'protagonist': 'A young hero',
                'setting': 'A magical world',
                'theme': 'Good vs Evil'
            }
        elif project_type == 'paper':
            context = {
                'research_question': 'What is the effect of X on Y?',
                'methodology': 'Mixed methods'
            }
        
        # Generate outline
        self.stdout.write(self.style.WARNING('Generating outline...'))
        
        outline = generator.generate_sync(
            project_type=project_type,
            title=title,
            framework=framework,
            context=context,
            constraints={'word_count': word_count},
            rules=[genre] if genre and project_type == 'book' else [],
            use_ai=use_ai
        )
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f'\n✅ Outline Generated!\n'))
        
        self.stdout.write(f"ID: {outline.id}")
        self.stdout.write(f"Framework Used: {outline.framework_used}")
        self.stdout.write(f"Total Sections: {outline.total_sections}")
        self.stdout.write(f"Word Target: {outline.total_word_target:,}")
        self.stdout.write(f"Estimated Duration: {outline.estimated_duration}")
        self.stdout.write(f"Completeness: {outline.completeness_score:.0%}")
        
        if outline.warnings:
            self.stdout.write(self.style.WARNING(f"\nWarnings: {', '.join(outline.warnings)}"))
        
        self.stdout.write(self.style.WARNING('\n📋 Sections:\n'))
        
        for section in outline.sections:
            self.stdout.write(f"  {section.number}. {section.name}")
            self.stdout.write(f"     Words: {section.word_target:,}")
            if section.beat:
                self.stdout.write(f"     Beat: {section.beat}")
            if section.key_points:
                self.stdout.write(f"     Key Points: {len(section.key_points)}")
            if section.writing_guidance:
                self.stdout.write(f"     Guidance: {section.writing_guidance[:50]}...")
            self.stdout.write("")
        
        # Export markdown
        self.stdout.write(self.style.WARNING('\n📄 Markdown Export (first 1000 chars):\n'))
        md = outline.to_markdown()
        self.stdout.write(md[:1000])
        if len(md) > 1000:
            self.stdout.write(f"\n... ({len(md) - 1000} more characters)")
        
        self.stdout.write(self.style.SUCCESS('\n✅ Test Complete!\n'))
