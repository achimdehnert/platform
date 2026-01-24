# -*- coding: utf-8 -*-
"""
Setup navigation for Usage Tracking section.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.control_center.models import NavigationSection, NavigationItem


class Command(BaseCommand):
    help = 'Create or update Usage Tracking navigation items'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Get or create the CONTROLLING section
            section, created = NavigationSection.objects.update_or_create(
                code='CONTROLLING',
                defaults={
                    'name': 'Controlling',
                    'order': 80,
                    'icon': 'bi-bar-chart-line',
                    'is_collapsed_default': False,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created section: {section.name}'))
            else:
                self.stdout.write(f'Updated section: {section.name}')

            # Navigation items for Usage Tracking
            items = [
                {
                    'code': 'controlling_dashboard',
                    'name': 'LLM Controlling',
                    'url_name': 'control_center:controlling-dashboard',
                    'icon': 'bi-cpu',
                    'order': 10,
                },
                {
                    'code': 'usage_dashboard',
                    'name': 'Usage Dashboard',
                    'url_name': 'control_center:usage_tracking:usage_dashboard',
                    'icon': 'bi-activity',
                    'order': 20,
                },
                {
                    'code': 'error_list',
                    'name': 'Django Errors',
                    'url_name': 'control_center:usage_tracking:error_list',
                    'icon': 'bi-bug',
                    'order': 30,
                },
                {
                    'code': 'tool_usage',
                    'name': 'Tool Usage',
                    'url_name': 'control_center:usage_tracking:tool_usage_list',
                    'icon': 'bi-tools',
                    'order': 40,
                },
                {
                    'code': 'tool_stats',
                    'name': 'Tool Statistics',
                    'url_name': 'control_center:usage_tracking:tool_statistics',
                    'icon': 'bi-graph-up',
                    'order': 50,
                },
                {
                    'code': 'error_patterns',
                    'name': 'Error Patterns',
                    'url_name': 'control_center:usage_tracking:error_patterns',
                    'icon': 'bi-puzzle',
                    'order': 60,
                },
            ]

            for item_data in items:
                item, created = NavigationItem.objects.update_or_create(
                    section=section,
                    code=item_data['code'],
                    defaults={
                        'name': item_data['name'],
                        'url_name': item_data['url_name'],
                        'icon': item_data['icon'],
                        'order': item_data['order'],
                    }
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'  {status}: {item.name}')

        self.stdout.write(self.style.SUCCESS('\nUsage Tracking navigation setup complete!'))
        self.stdout.write('\nAccess at: /control-center/usage-tracking/')
