"""
Management command to add Test Studio navigation item to Control Center.
"""
from django.core.management.base import BaseCommand
from apps.control_center.models_navigation import NavigationSection, NavigationItem


class Command(BaseCommand):
    help = 'Add Test Studio navigation item to Control Center'

    def handle(self, *args, **options):
        # Find or create Development Tools section
        section, created = NavigationSection.objects.get_or_create(
            code='development',
            defaults={
                'name': 'Development Tools',
                'icon': 'bi-code-slash',
                'order': 60,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created section: {section.name}'))
        
        # Create Test Studio navigation item
        item, created = NavigationItem.objects.get_or_create(
            code='test_studio',
            defaults={
                'name': 'Test Studio',
                'url_name': 'control_center:test-studio-dashboard',
                'icon': 'bi-clipboard-check',
                'section': section,
                'order': 50,
                'is_active': True,
                'badge_text': 'Cross-Domain',
                'badge_color': 'success',
                'description': 'Requirements & Test Management für alle Domains',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created navigation item: {item.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Navigation item already exists: {item.name}'))
        
        # Also add Fix Plans sub-item
        fix_plans, created = NavigationItem.objects.get_or_create(
            code='test_studio_fix_plans',
            defaults={
                'name': 'Fix Plans',
                'url_name': 'control_center:test-studio-fix-plans',
                'icon': 'bi-wrench-adjustable',
                'section': section,
                'order': 51,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created navigation item: {fix_plans.name}'))
        
        self.stdout.write(self.style.SUCCESS('Test Studio navigation setup complete!'))
