"""
Management Command to populate domain_arts table with Hub configuration
"""
from django.core.management.base import BaseCommand
from django.db import connection
from apps.bfagent.models_domains import DomainArt


class Command(BaseCommand):
    help = 'Populate domain_arts table with Hub configurations for dynamic landing page'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Populating Domain Hubs...'))
        
        # Hub configurations
        hubs = [
            {
                'name': 'control_center',
                'slug': 'control-center',
                'display_name': 'Control Center',
                'description': 'System tools, monitoring, and development utilities. Manage your BF Agent instance.',
                'icon': 'gear',
                'color': 'info',
                'dashboard_url': '/control-center/',
                'display_order': 1,
                'is_active': True,
                'is_experimental': False,
                'config': {
                    'subtitle': 'System & Development',
                    'statistics': {'enabled': True},
                    'features': ['Tools', 'Monitoring', 'Master Data', 'Workflow Config'],
                }
            },
            {
                'name': 'writing_hub',
                'slug': 'writing-hub',
                'display_name': 'Writing Hub',
                'description': 'Modern project management for novel series. Story Engine with AI chapter generation.',
                'icon': 'pen',
                'color': 'primary',
                'dashboard_url': '/writing-hub/v2/',
                'display_order': 2,
                'is_active': True,
                'is_experimental': False,
                'config': {
                    'subtitle': 'Novel Series & Story Engine',
                    'badge': 'NEW',
                    'statistics': {'enabled': True},
                    'features': ['Projects', 'Characters', 'Chapters', 'AI Generation'],
                }
            },
            {
                'name': 'format_hub',
                'slug': 'format-hub',
                'display_name': 'Format Hub',
                'description': 'Professional format conversions: Medical Translation (PPTX + DeepL) and PPTX Studio (AI Enhancement).',
                'icon': 'file-earmark-slides',
                'color': 'warning',
                'dashboard_url': '/format-hub/',  # Will need to create this
                'display_order': 3,
                'is_active': True,
                'is_experimental': False,
                'config': {
                    'subtitle': 'Translation & Enhancement',
                    'statistics': {'enabled': True},
                    'features': ['Medical Translation', 'PPTX Studio', 'Format Conversion'],
                    'sub_apps': [
                        {'name': 'Medical Translation', 'url': '/medtrans/'},
                        {'name': 'PPTX Studio', 'url': '/pptx-studio/'},
                    ]
                }
            },
            {
                'name': 'expert_hub',
                'slug': 'expert-hub',
                'display_name': 'Experten-Hub',
                'description': 'Expert management and consultation services. Manage specialists, consultants, and expert reviews.',
                'icon': 'people',
                'color': 'success',
                'dashboard_url': '/expert-hub/',
                'display_order': 4,
                'is_active': False,  # Coming soon
                'is_experimental': True,
                'config': {
                    'subtitle': 'Expert Management',
                    'badge': 'SOON',
                    'statistics': {'enabled': False},
                    'features': ['Consultants', 'Specialists', 'Reviews'],
                }
            },
            {
                'name': 'support_hub',
                'slug': 'support-hub',
                'display_name': 'Support-Hub',
                'description': 'Customer support and service management. Ticket system, knowledge base, and help desk.',
                'icon': 'headset',
                'color': 'danger',
                'dashboard_url': '/support-hub/',
                'display_order': 5,
                'is_active': False,  # Coming soon
                'is_experimental': True,
                'config': {
                    'subtitle': 'Customer Support',
                    'badge': 'SOON',
                    'statistics': {'enabled': False},
                    'features': ['Tickets', 'Knowledge Base', 'Help Desk'],
                }
            },
            {
                'name': 'research_hub',
                'slug': 'research-hub',
                'display_name': 'Research-Hub',
                'description': 'Research management and documentation. Literature review, data collection, and analysis.',
                'icon': 'search',
                'color': 'secondary',
                'dashboard_url': '/research-hub/',
                'display_order': 6,
                'is_active': False,  # Coming soon
                'is_experimental': True,
                'config': {
                    'subtitle': 'Research Management',
                    'badge': 'SOON',
                    'statistics': {'enabled': False},
                    'features': ['Literature', 'Data Collection', 'Analysis'],
                }
            },
            {
                'name': 'coaching_hub',
                'slug': 'coaching-hub',
                'display_name': 'Coaching-Hub',
                'description': 'Coaching and training management. Course delivery, progress tracking, and feedback.',
                'icon': 'mortarboard',
                'color': 'info',
                'dashboard_url': '/coaching-hub/',
                'display_order': 7,
                'is_active': False,  # Coming soon
                'is_experimental': True,
                'config': {
                    'subtitle': 'Coaching & Training',
                    'badge': 'SOON',
                    'statistics': {'enabled': False},
                    'features': ['Courses', 'Progress Tracking', 'Feedback'],
                }
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for hub_data in hubs:
            try:
                domain_art, created = DomainArt.objects.update_or_create(
                    slug=hub_data['slug'],
                    defaults=hub_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {domain_art.display_name}'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'  🔄 Updated: {domain_art.display_name}'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Error with {hub_data["display_name"]}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Done! Created: {created_count}, Updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total Hub Domains: {DomainArt.objects.count()}'))
