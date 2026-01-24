"""
Management command to create chapters for existing Essays
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import BookProjects


class Command(BaseCommand):
    help = 'Create chapters for existing Essays that have no chapters'

    def handle(self, *args, **options):
        # Find all Essays
        essays = BookProjects.objects.filter(book_type__name='Essay')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📚 Found {essays.count()} Essay(s)\n')
        )
        
        fixed_count = 0
        
        for essay in essays:
            chapter_count = essay.chapters.count()
            
            self.stdout.write(f'📘 {essay.title} (ID: {essay.id})')
            self.stdout.write(f'   Current chapters: {chapter_count}')
            
            if chapter_count == 0:
                # Create chapters
                try:
                    essay._create_essay_chapters()
                    new_count = essay.chapters.count()
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ Created {new_count} chapters!')
                    )
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ Error: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠️  Already has chapters, skipping')
                )
            
            self.stdout.write('')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Fixed {fixed_count} Essay(s)')
        )
