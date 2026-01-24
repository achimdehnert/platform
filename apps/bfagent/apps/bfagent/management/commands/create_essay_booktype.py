"""
Management command to create Essay BookType
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import BookTypes


class Command(BaseCommand):
    help = 'Create Essay BookType with 3-chapter structure'

    def handle(self, *args, **options):
        # Check if Essay booktype exists
        essay_type, created = BookTypes.objects.get_or_create(
            name='Essay',
            defaults={
                'description': 'Short essay format with 3 chapters: Introduction, Body, and Conclusion. Approximately 1000 words total.',
                'complexity': 'Simple',
                'estimated_duration_hours': 2,
                'target_word_count_min': 800,
                'target_word_count_max': 1200,
                'is_active': True,
                'configuration': '''{
                    "chapters": 3,
                    "structure": [
                        {
                            "order": 1,
                            "name": "Introduction",
                            "target_words": 150,
                            "purpose": "Hook, context, thesis statement"
                        },
                        {
                            "order": 2,
                            "name": "Body",
                            "target_words": 700,
                            "purpose": "Three main arguments with evidence"
                        },
                        {
                            "order": 3,
                            "name": "Conclusion",
                            "target_words": 150,
                            "purpose": "Summary, implications, final thought"
                        }
                    ]
                }'''
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created Essay BookType (ID: {essay_type.id})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️ Essay BookType already exists (ID: {essay_type.id})')
            )

        self.stdout.write(
            self.style.SUCCESS('\n📚 Essay BookType Configuration:')
        )
        self.stdout.write(f'  Name: {essay_type.name}')
        self.stdout.write(f'  Complexity: {essay_type.complexity}')
        self.stdout.write(f'  Word Count: {essay_type.target_word_count_min}-{essay_type.target_word_count_max}')
        self.stdout.write(f'  Duration: {essay_type.estimated_duration_hours}h')
