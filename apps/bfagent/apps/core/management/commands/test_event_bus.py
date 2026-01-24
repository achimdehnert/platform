"""
Test Event Bus - Verify Event-Driven Architecture
Usage: python manage.py test_event_bus
"""
from django.core.management.base import BaseCommand

from apps.core.feature_flags import FEATURES, is_feature_enabled, enable_feature, disable_feature
from apps.core.event_bus import event_bus
from apps.core.events import Events
from apps.core.hub_registry import hub_registry


class Command(BaseCommand):
    help = "Test the Event Bus and Hub Registry"

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Temporarily enable USE_EVENT_BUS for testing'
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🔧 BF Agent Event-Driven Architecture Test")
        self.stdout.write("=" * 60 + "\n")
        
        # 1. Test Feature Flags
        self.stdout.write(self.style.HTTP_INFO("1️⃣ Feature Flags Status:"))
        for flag, value in FEATURES.items():
            status = "✅ ON" if value else "⚪ OFF"
            self.stdout.write(f"   {flag}: {status}")
        
        # 2. Test Hub Registry
        self.stdout.write(self.style.HTTP_INFO("\n2️⃣ Hub Registry:"))
        hubs = hub_registry.get_all_hubs()
        for hub_id, info in hubs.items():
            status = "✅" if info.is_active else "⚪"
            self.stdout.write(f"   {status} {info.manifest.name} ({hub_id}) - {info.manifest.status.value}")
        
        # 3. Test Event Bus (disabled)
        self.stdout.write(self.style.HTTP_INFO("\n3️⃣ Event Bus Test (Feature OFF):"))
        result = event_bus.publish(Events.CHAPTER_CREATED, chapter_id=999, project_id=1)
        self.stdout.write(f"   Publish result: {result} (expected: False)")
        
        # 4. Test Event Bus (enabled if --enable flag)
        if options['enable']:
            self.stdout.write(self.style.HTTP_INFO("\n4️⃣ Event Bus Test (Feature ON):"))
            
            # Register a test handler
            received_events = []
            
            @event_bus.subscribe(Events.CHAPTER_CREATED)
            def test_handler(chapter_id, project_id, **kwargs):
                received_events.append({'chapter_id': chapter_id, 'project_id': project_id})
                return True
            
            # Enable feature temporarily
            enable_feature("USE_EVENT_BUS")
            
            # Publish event
            result = event_bus.publish(
                Events.CHAPTER_CREATED,
                source="test_event_bus",
                chapter_id=123,
                project_id=1
            )
            self.stdout.write(f"   Publish result: {result} (expected: True)")
            self.stdout.write(f"   Events received: {len(received_events)}")
            
            if received_events:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Handler received: {received_events[0]}"))
            
            # Check recent events
            recent = event_bus.get_recent_events(limit=5)
            self.stdout.write(f"   Recent events in log: {len(recent)}")
            
            # Disable feature again
            disable_feature("USE_EVENT_BUS")
            self.stdout.write("   Feature disabled again")
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Event-Driven Architecture Test Complete"))
        self.stdout.write("=" * 60)
        self.stdout.write("\nTo enable events in production:")
        self.stdout.write("  1. Set FEATURE_FLAG_USE_EVENT_BUS=true in .env")
        self.stdout.write("  2. Or: from apps.core.feature_flags import enable_feature")
        self.stdout.write("         enable_feature('USE_EVENT_BUS')")
        self.stdout.write("")
