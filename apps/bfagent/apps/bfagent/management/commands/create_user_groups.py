"""
Management command to create user groups for app-level permissions
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create user groups for all BF Agent domain apps'

    def handle(self, *args, **options):
        # Create Book Writing group
        book_writing_group, created = Group.objects.get_or_create(name='BookWriting')
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created group: BookWriting'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Group already exists: BookWriting'))

        # Create Medical Translation group
        medtrans_group, created = Group.objects.get_or_create(name='MedicalTranslation')
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created group: MedicalTranslation'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Group already exists: MedicalTranslation'))

        # Create GenAgent group
        genagent_group, created = Group.objects.get_or_create(name='GenAgent')
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created group: GenAgent'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Group already exists: GenAgent'))

        self.stdout.write(self.style.SUCCESS('\n🎉 User groups setup complete!'))
        self.stdout.write('\nUsage:')
        self.stdout.write('  - Assign users to groups via Django Admin')
        self.stdout.write('  - Users in BookWriting group can access Book Writing Studio')
        self.stdout.write('  - Users in MedicalTranslation group can access Medical Translation')
        self.stdout.write('  - Users in GenAgent group can access GenAgent Framework')
