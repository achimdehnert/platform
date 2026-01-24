"""
Management Command: Propose a new feature/component
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bfagent.models_registry import ComponentRegistry, ComponentType, ComponentStatus


class Command(BaseCommand):
    help = 'Propose a new feature or component'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Feature name (e.g., "CharacterEmotionAnalyzer")'
        )
        
        parser.add_argument(
            '--type',
            type=str,
            required=True,
            choices=[choice[0] for choice in ComponentType.choices],
            help='Component type'
        )
        
        parser.add_argument(
            '--description',
            type=str,
            required=True,
            help='What does this component do?'
        )
        
        parser.add_argument(
            '--priority',
            type=str,
            default='medium',
            choices=['critical', 'high', 'medium', 'low', 'backlog'],
            help='Priority level'
        )
        
        parser.add_argument(
            '--domain',
            type=str,
            default='',
            help='Domain (e.g., "book", "explosion", "shared")'
        )
    
    def handle(self, *args, **options):
        name = options['name']
        component_type = options['type']
        description = options['description']
        priority = options['priority']
        domain = options['domain']
        
        # Generate identifier
        identifier = f"proposed.{component_type}.{name.lower().replace(' ', '_')}"
        
        self.stdout.write(self.style.SUCCESS(f'\n💡 Proposing Feature: {name}\n'))
        
        # Check for similar existing/planned features
        similar = ComponentRegistry.find_similar(name, component_type)
        
        if similar:
            self.stdout.write(self.style.WARNING('⚠️  Similar features found:'))
            for comp in similar:
                status_icon = self._get_status_icon(comp.status)
                owner_info = f" (Owner: {comp.owner.username})" if comp.owner else ""
                self.stdout.write(
                    f'   {status_icon} {comp.name} - Status: {comp.status}{owner_info}'
                )
            
            self.stdout.write('')
            proceed = input('Continue anyway? (y/n): ')
            if proceed.lower() != 'y':
                self.stdout.write(self.style.WARNING('❌ Proposal cancelled\n'))
                return
        
        # Create proposal
        try:
            component = ComponentRegistry.objects.create(
                identifier=identifier,
                name=name,
                component_type=component_type,
                description=description,
                priority=priority,
                domain=domain,
                status=ComponentStatus.PROPOSED,
                proposed_at=timezone.now(),
                module_path='',  # Will be filled during implementation
                file_path='',    # Will be filled during implementation
            )
            
            self.stdout.write(self.style.SUCCESS('✅ Feature proposed successfully!'))
            self.stdout.write(f'   ID: {component.id}')
            self.stdout.write(f'   Identifier: {component.identifier}')
            self.stdout.write(f'   Status: {component.status}')
            self.stdout.write(f'   Priority: {component.priority}')
            
            self.stdout.write('\n📋 Next steps:')
            self.stdout.write(f'   1. Team votes on proposal')
            self.stdout.write(f'   2. If approved: python manage.py claim_feature {component.id}')
            self.stdout.write(f'   3. Implement the feature')
            self.stdout.write(f'   4. Status automatically updates to "active" via scan')
            self.stdout.write('')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}\n'))
    
    def _get_status_icon(self, status):
        """Get icon for status"""
        icons = {
            'proposed': '💡',
            'planned': '📋',
            'in_progress': '🚧',
            'in_review': '👀',
            'testing': '🧪',
            'active': '✅',
            'deprecated': '⚠️',
            'rejected': '❌',
        }
        return icons.get(status, '❓')
