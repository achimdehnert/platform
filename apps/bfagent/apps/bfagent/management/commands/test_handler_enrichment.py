"""
Management command to test ChapterGenerateHandler with DatabaseContextEnricher
"""
from django.core.management.base import BaseCommand
from apps.bfagent.handlers.processing_handlers.chapter_generate_handler import ChapterGenerateHandler
import json


class Command(BaseCommand):
    help = 'Test ChapterGenerateHandler with DatabaseContextEnricher integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            default=3,
            help='Project ID to test (default: 3 - Hugo & Luise)'
        )
        parser.add_argument(
            '--chapter-number',
            type=int,
            default=1,
            help='Chapter number to test (default: 1)'
        )

    def handle(self, *args, **options):
        project_id = options['project_id']
        chapter_number = options['chapter_number']

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(
            "Testing ChapterGenerateHandler with DatabaseContextEnricher"
        ))
        self.stdout.write("=" * 80)

        handler = ChapterGenerateHandler()

        test_context = {
            'action': 'generate_chapter_outline',
            'project_id': project_id,
            'chapter_number': chapter_number,
            'parameters': {
                'chapter_title': f'Chapter {chapter_number}',
                'word_count_target': 3000
            }
        }

        self.stdout.write("\n📋 Test Context:")
        self.stdout.write(json.dumps(test_context, indent=2))

        try:
            self.stdout.write("\n⚙️  Executing handler...")
            result = handler.execute(test_context)

            self.stdout.write(self.style.SUCCESS("\n✅ SUCCESS!"))
            self.stdout.write("\n📊 Result:")
            self.stdout.write(json.dumps(result, indent=2, default=str))

            # Check if enriched context is present
            if 'data' in result and 'project_context' in result['data']:
                context = result['data']['project_context']
                self.stdout.write("\n🎯 Enriched Context Keys:")
                self.stdout.write(f"   - Total Keys: {len(context)}")
                self.stdout.write(f"   - Keys: {', '.join(list(context.keys())[:10])}...")

                # Check for database-enriched fields
                enriched_fields = []
                if 'story_position' in context:
                    enriched_fields.append('✅ story_position (computed)')
                if 'current_beat' in context:
                    enriched_fields.append('✅ current_beat (beat_sheet)')
                if 'previous_chapters' in context:
                    enriched_fields.append('✅ previous_chapters (related_query)')
                if '_schema' in context:
                    enriched_fields.append(f'✅ _schema: {context["_schema"]}')

                if enriched_fields:
                    self.stdout.write(self.style.SUCCESS(
                        "\n🎉 Database-Enriched Fields Found:"
                    ))
                    for field in enriched_fields:
                        self.stdout.write(f"   {field}")
                else:
                    self.stdout.write(self.style.WARNING(
                        "\n⚠️  Using fallback context (enrichment may have failed)"
                    ))

                # Show project title if available
                if 'title' in context:
                    self.stdout.write(f"\n📚 Project: {context['title']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

        self.stdout.write(self.style.SUCCESS("\n✅ Test completed successfully!"))
