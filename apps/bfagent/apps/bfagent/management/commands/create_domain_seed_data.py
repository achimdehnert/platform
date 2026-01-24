"""
Management command to create seed data for Multi-Hub Framework
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models_domains import DomainArt, DomainType


class Command(BaseCommand):
    help = 'Create seed data for Multi-Hub Framework domains'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating Multi-Hub Framework seed data...')
        
        # Define the 5 hubs
        hubs_data = [
            {
                'name': 'book_creation',
                'slug': 'book-creation', 
                'display_name': 'Bücher-Hub',
                'description': 'Buchentwicklung und -management',
                'icon': 'book',
                'color': 'primary'
            },
            {
                'name': 'expertise_management',
                'slug': 'expertise-management',
                'display_name': 'Experten-Hub', 
                'description': 'Expertenverwaltung und -zuweisung',
                'icon': 'people',
                'color': 'success'
            },
            {
                'name': 'customer_support',
                'slug': 'customer-support',
                'display_name': 'Support-Hub',
                'description': 'Kundensupport und Helpdesk',
                'icon': 'headset',
                'color': 'info'
            },
            {
                'name': 'content_formatting',
                'slug': 'content-formatting', 
                'display_name': 'Format-Hub',
                'description': 'Content-Formatierung und -Konvertierung',
                'icon': 'file-earmark-text',
                'color': 'warning'
            },
            {
                'name': 'research_management',
                'slug': 'research-management',
                'display_name': 'Research-Hub',
                'description': 'Forschung und Analytics',
                'icon': 'graph-up',
                'color': 'secondary'
            }
        ]
        
        # Create DomainArts
        created_domains = 0
        for hub_data in hubs_data:
            domain_art, created = DomainArt.objects.get_or_create(
                name=hub_data['name'],
                defaults=hub_data
            )
            if created:
                created_domains += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created domain: {domain_art.display_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Domain already exists: {domain_art.display_name}')
                )
        
        # Create DomainTypes for book_creation
        book_domain = DomainArt.objects.get(name='book_creation')
        book_types_data = [
            {
                'name': 'fiction',
                'slug': 'fiction',
                'display_name': 'Fiction',
                'description': 'Fictional books and novels',
                'sort_order': 10
            },
            {
                'name': 'non_fiction',
                'slug': 'non-fiction',
                'display_name': 'Non-Fiction',
                'description': 'Non-fictional books and guides',
                'sort_order': 20
            },
            {
                'name': 'technical',
                'slug': 'technical',
                'display_name': 'Technical',
                'description': 'Technical documentation and manuals',
                'sort_order': 30
            },
            {
                'name': 'children',
                'slug': 'children',
                'display_name': 'Children',
                'description': 'Children and young adult books',
                'sort_order': 40
            }
        ]
        
        created_types = 0
        for type_data in book_types_data:
            domain_type, created = DomainType.objects.get_or_create(
                domain_art=book_domain,
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                created_types += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created type: {domain_type.display_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Seed data creation complete! '
                f'Created {created_domains} domains and {created_types} types.'
            )
        )
