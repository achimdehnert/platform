"""
Management Command: Show current feature development status
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.bfagent.models_registry import ComponentRegistry, ComponentStatus


class Command(BaseCommand):
    help = 'Show current feature development status'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            help='Filter by component type'
        )
        
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by status'
        )
        
        parser.add_argument(
            '--owner',
            type=str,
            help='Filter by owner username'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📊 Feature Development Status\n'))
        
        # Base query
        features = ComponentRegistry.objects.all()
        
        # Apply filters
        if options['type']:
            features = features.filter(component_type=options['type'])
        
        if options['status']:
            features = features.filter(status=options['status'])
        
        if options['owner']:
            features = features.filter(owner__username=options['owner'])
        
        # Status summary
        status_counts = features.values('status').annotate(count=Count('id')).order_by('-count')
        
        self.stdout.write('Status Summary:')
        for item in status_counts:
            icon = self._get_status_icon(item['status'])
            self.stdout.write(f'  {icon} {item["status"]:15} {item["count"]:3}')
        
        self.stdout.write('')
        
        # In Progress Features
        in_progress = features.filter(status=ComponentStatus.IN_PROGRESS).order_by('-started_at')
        
        if in_progress.exists():
            self.stdout.write(self.style.WARNING('🚧 IN PROGRESS:'))
            for feature in in_progress:
                owner_info = f" ({feature.owner.username})" if feature.owner else ""
                priority = self._get_priority_badge(feature.priority)
                days_active = (feature.started_at.date() - feature.started_at.date()).days if feature.started_at else 0
                self.stdout.write(
                    f'  • {feature.name:30} {priority} {owner_info}'
                )
            self.stdout.write('')
        
        # Proposed Features
        proposed = features.filter(status=ComponentStatus.PROPOSED).order_by('-proposed_at')[:10]
        
        if proposed.exists():
            self.stdout.write(self.style.SUCCESS('💡 PROPOSED:'))
            for feature in proposed:
                priority = self._get_priority_badge(feature.priority)
                self.stdout.write(f'  • {feature.name:30} {priority}')
            self.stdout.write('')
        
        # Planned Features
        planned = features.filter(status=ComponentStatus.PLANNED).order_by('priority', '-planned_at')[:10]
        
        if planned.exists():
            self.stdout.write('📋 PLANNED:')
            for feature in planned:
                priority = self._get_priority_badge(feature.priority)
                owner_info = f" (Owner: {feature.owner.username})" if feature.owner else ""
                self.stdout.write(f'  • {feature.name:30} {priority}{owner_info}')
            self.stdout.write('')
        
        # Active Features (recently)
        active = features.filter(status=ComponentStatus.ACTIVE).order_by('-completed_at')[:5]
        
        if active.exists():
            self.stdout.write('✅ RECENTLY ACTIVE:')
            for feature in active:
                self.stdout.write(f'  • {feature.name}')
            self.stdout.write('')
        
        # Summary
        total = features.count()
        self.stdout.write(f'Total features: {total}')
        self.stdout.write('')
    
    def _get_status_icon(self, status):
        """Get icon for status"""
        icons = {
            'proposed': '💡',
            'planned': '📋',
            'in_progress': '🚧',
            'in_review': '👀',
            'testing': '🧪',
            'active': '✅',
            'beta': '🔬',
            'experimental': '🧪',
            'deprecated': '⚠️',
            'disabled': '🚫',
            'rejected': '❌',
        }
        return icons.get(status, '❓')
    
    def _get_priority_badge(self, priority):
        """Get priority badge"""
        badges = {
            'critical': '🔥',
            'high': '🔴',
            'medium': '🟡',
            'low': '🔵',
            'backlog': '📦',
        }
        return badges.get(priority, '❓')
