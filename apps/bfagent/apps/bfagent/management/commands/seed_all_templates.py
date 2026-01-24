"""
Master seeding command - Seeds all template data in correct order
1. PromptTemplates
2. ActionTemplate mappings
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Seed all template data (PromptTemplates + ActionTemplates)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all template data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("🚀 Master Template Seeding"))
        self.stdout.write("=" * 60 + "\n")

        reset = options.get('reset', False)

        # Step 1: Seed PromptTemplates
        self.stdout.write(self.style.SUCCESS("\n📝 Step 1: Seeding PromptTemplates...\n"))
        call_command('seed_prompt_templates', reset=reset)

        # Step 2: Seed ActionTemplate mappings
        self.stdout.write(self.style.SUCCESS("\n🔗 Step 2: Seeding ActionTemplate Mappings...\n"))
        call_command('seed_action_templates', reset=reset)

        # Final summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("🎉 MASTER SEEDING COMPLETED!"))
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n✅ All template data seeded successfully!\n"))
        self.stdout.write("💡 Next steps:")
        self.stdout.write("   - View templates: /prompt-templates/")
        self.stdout.write("   - View mappings: /action-templates/")
        self.stdout.write("   - Test in enrichment panel\n")
