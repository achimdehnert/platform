"""
Management Command: Check if component exists
Searches the component registry for similar components before creating new ones
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models_registry import ComponentRegistry, ComponentType


class Command(BaseCommand):
    help = 'Check if similar component exists in registry'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'search_term',
            type=str,
            help='Search term (e.g., "character generation")'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=[t.value for t in ComponentType],
            help='Component type filter'
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Domain filter (e.g., book, explosion)'
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed information'
        )
    
    def handle(self, *args, **options):
        search_term = options['search_term']
        component_type = options.get('type')
        domain = options.get('domain')
        show_details = options.get('show_details', False)
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 Searching for: "{search_term}"\n'))
        
        # Search
        components = ComponentRegistry.find_similar(search_term, component_type)
        
        # Apply domain filter
        if domain:
            components = [c for c in components if c.domain == domain]
        
        if not components:
            self.stdout.write(self.style.SUCCESS('✅ No similar components found!'))
            self.stdout.write('💡 You can proceed with creating a new component.\n')
            return
        
        # Display results
        self.stdout.write(self.style.WARNING(f'⚠️  Found {len(components)} similar component(s):\n'))
        
        for i, comp in enumerate(components, 1):
            self.stdout.write(self.style.WARNING(f'{i}. {comp.name}'))
            self.stdout.write(f'   Type: {comp.component_type}')
            if comp.domain:
                self.stdout.write(f'   Domain: {comp.domain}')
            self.stdout.write(f'   📁 {comp.file_path}')
            
            if comp.usage_count > 0:
                self.stdout.write(
                    f'   📊 Usage: {comp.usage_count} times '
                    f'(Success rate: {comp.success_rate:.1f}%)'
                )
            
            if comp.description:
                desc = comp.description[:100]
                self.stdout.write(f'   📝 {desc}')
            
            if show_details:
                if comp.metadata:
                    self.stdout.write(f'   🔧 Methods: {", ".join(comp.metadata.get("methods", [])[:5])}')
                if comp.tags:
                    self.stdout.write(f'   🏷️  Tags: {", ".join(comp.tags[:5])}')
            
            self.stdout.write('')  # Blank line
        
        # Recommendation
        self.stdout.write(self.style.WARNING('💡 RECOMMENDATION:'))
        self.stdout.write('   Consider reusing or extending one of the above components.')
        self.stdout.write('   If you still want to create a new one, make sure it serves a different purpose.\n')
