"""
Django Management Command: Mark feature as completed
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bfagent.models import ComponentRegistry, ComponentStatus


class Command(BaseCommand):
    help = 'Mark a feature as completed'

    def add_arguments(self, parser):
        parser.add_argument(
            'feature_id',
            type=int,
            help='Feature ID to mark as completed'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='active',
            choices=['active', 'testing', 'completed'],
            help='Target status (default: active)'
        )

    def handle(self, *args, **options):
        feature_id = options['feature_id']
        target_status = options['status']

        try:
            feature = ComponentRegistry.objects.get(id=feature_id)
        except ComponentRegistry.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Feature #{feature_id} not found!"))
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"MARK FEATURE AS {target_status.upper()}")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Show feature info
        self.stdout.write(f"Feature: {feature.name}")
        self.stdout.write(f"Type: {feature.component_type}")
        self.stdout.write(f"Domain: {feature.domain}")
        self.stdout.write(f"Current Status: {feature.status}")
        self.stdout.write("")

        # Update status
        old_status = feature.status
        feature.status = target_status

        # Set timestamp based on status
        if target_status == 'active':
            feature.completed_at = timezone.now()
            self.stdout.write("✅ Marking as ACTIVE (deployed & running)")
        elif target_status == 'testing':
            feature.started_at = timezone.now() if not feature.started_at else feature.started_at
            self.stdout.write("🧪 Marking as TESTING")
        elif target_status == 'completed':
            feature.completed_at = timezone.now()
            self.stdout.write("✅ Marking as COMPLETED")

        feature.save()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Status updated: {old_status} → {target_status}"))
        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write(f"1. View at: http://localhost:8000/control-center/feature-planning/{feature.id}/")
        self.stdout.write("2. Add completion notes if needed")
        self.stdout.write("3. Link related documentation")
