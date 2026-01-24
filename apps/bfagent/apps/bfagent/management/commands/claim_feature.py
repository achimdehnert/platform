"""
Management Command: Claim a proposed feature and start working on it
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.bfagent.models_registry import ComponentRegistry, ComponentStatus


User = get_user_model()


class Command(BaseCommand):
    help = 'Claim a feature and mark it as in-progress'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'feature_id',
            type=int,
            help='Feature ID to claim'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='Username of person claiming (optional)'
        )
    
    def handle(self, *args, **options):
        feature_id = options['feature_id']
        username = options.get('user')
        
        try:
            feature = ComponentRegistry.objects.get(pk=feature_id)
        except ComponentRegistry.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Feature {feature_id} not found\n'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n🚧 Claiming Feature: {feature.name}\n'))
        
        # Check current status
        if feature.status == ComponentStatus.ACTIVE:
            self.stdout.write(self.style.WARNING('⚠️  This feature is already active!'))
            proceed = input('Mark as in-progress anyway? (y/n): ')
            if proceed.lower() != 'y':
                return
        
        if feature.status == ComponentStatus.IN_PROGRESS and feature.owner:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Already in progress by: {feature.owner.username}')
            )
            proceed = input('Take over anyway? (y/n): ')
            if proceed.lower() != 'y':
                return
        
        # Set owner if specified
        owner = None
        if username:
            try:
                owner = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'⚠️  User {username} not found'))
        
        # Update feature
        feature.status = ComponentStatus.IN_PROGRESS
        feature.started_at = timezone.now()
        
        if owner:
            feature.owner = owner
        
        # Auto-plan if it was proposed
        if feature.planned_at is None and feature.status in [ComponentStatus.PROPOSED, ComponentStatus.PLANNED]:
            feature.planned_at = timezone.now()
        
        feature.save()
        
        self.stdout.write(self.style.SUCCESS('✅ Feature claimed!'))
        self.stdout.write(f'   Status: {feature.status}')
        if feature.owner:
            self.stdout.write(f'   Owner: {feature.owner.username}')
        self.stdout.write(f'   Started: {feature.started_at.strftime("%Y-%m-%d %H:%M")}')
        
        self.stdout.write('\n📋 Next steps:')
        self.stdout.write(f'   1. Implement the feature')
        self.stdout.write(f'   2. Run: python manage.py scan_components')
        self.stdout.write(f'   3. Status will auto-update to "active"')
        self.stdout.write('')
