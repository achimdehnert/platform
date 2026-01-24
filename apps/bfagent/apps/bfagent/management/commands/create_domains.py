"""
Management command to create basic DomainArt entries
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models_domains import DomainArt


class Command(BaseCommand):
    help = 'Create basic DomainArt entries for navigation'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📋 Creating DomainArt entries\n'))
        
        domains = [
            {
                'name': 'control_center',
                'slug': 'control-center',
                'display_name': 'Control Center',
                'description': 'System management and control center',
                'icon': 'bi-gear-fill',
                'color': 'primary',
                'is_active': True,
            },
            {
                'name': 'expert_hub',
                'slug': 'expert-hub',
                'display_name': 'Expert Hub',
                'description': 'Expert management and assignments',
                'icon': 'bi-people-fill',
                'color': 'success',
                'is_active': True,
            },
            {
                'name': 'format_hub',
                'slug': 'format-hub',
                'display_name': 'Format Hub',
                'description': 'Document formatting and templates',
                'icon': 'bi-file-earmark-text-fill',
                'color': 'info',
                'is_active': True,
            },
            {
                'name': 'writing_hub',
                'slug': 'writing-hub',
                'display_name': 'Writing Hub',
                'description': 'Book and content writing',
                'icon': 'bi-book-fill',
                'color': 'warning',
                'is_active': True,
            },
            {
                'name': 'illustration_hub',
                'slug': 'illustration-hub',
                'display_name': 'Illustration Hub',
                'description': 'Image generation and management',
                'icon': 'bi-image-fill',
                'color': 'danger',
                'is_active': True,
            },
            {
                'name': 'research_hub',
                'slug': 'research-hub',
                'display_name': 'Research Hub',
                'description': 'Research and analysis tools',
                'icon': 'bi-search',
                'color': 'secondary',
                'is_active': True,
            },
        ]
        
        created_count = 0
        existing_count = 0
        
        for domain_data in domains:
            existing = DomainArt.objects.filter(slug=domain_data['slug']).first()
            
            if existing:
                self.stdout.write(f'  ⏭️  Domain "{domain_data["display_name"]}" already exists')
                existing_count += 1
            else:
                DomainArt.objects.create(**domain_data)
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {domain_data["display_name"]}'))
                created_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✅ COMPLETE:'))
        self.stdout.write(f'  Created: {created_count} domains')
        self.stdout.write(f'  Existing: {existing_count} domains')
        self.stdout.write(f'\n💡 Access domains at: http://localhost:8000/hub/domains/')
