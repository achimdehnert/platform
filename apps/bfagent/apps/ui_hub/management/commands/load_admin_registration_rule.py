"""Load admin registration guardrail rule."""

from django.core.management.base import BaseCommand

from apps.ui_hub.models import GuardrailCategory, GuardrailRule


class Command(BaseCommand):
    """Load admin registration guardrail rule."""

    help = "Load admin registration best practice rule"

    def handle(self, *args, **options):
        """Load the rule."""

        # Get or create structure category
        category, created = GuardrailCategory.objects.get_or_create(
            code="structure",
            defaults={
                "name": "Project Structure",
                "description": "Rules for project structure and configuration",
                "display_order": 40,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created category: {category.name}"))
        else:
            self.stdout.write(f"Category already exists: {category.name}")

        # Create admin registration rule
        rule, created = GuardrailRule.objects.get_or_create(
            category=category,
            name="admin_registration",
            defaults={
                "description": "Ensure Django admin is properly registered in AppConfig.ready()",
                "pattern": r"def ready\(self\):.*from \. import admin",
                "message": "Admin registration must be imported in AppConfig.ready() method",
                "suggestion": 'Add "from . import admin" in the ready() method of your AppConfig',
                "severity": "warning",
                "is_builtin": True,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created rule: {rule.name}"))

            # Add examples
            from apps.ui_hub.models import RuleExample

            # Valid example
            RuleExample.objects.create(
                rule=rule,
                is_valid=True,
                code='''# apps.py - CORRECT
class MyAppConfig(AppConfig):
    name = 'apps.myapp'
    label = 'myapp'

    def ready(self):
        """Initialize app on startup."""
        from . import admin  # ✅ Admin imported
''',
                explanation="Admin is imported in ready() method to ensure models are registered",
            )

            # Invalid example
            RuleExample.objects.create(
                rule=rule,
                is_valid=False,
                code='''# apps.py - WRONG
class MyAppConfig(AppConfig):
    name = 'apps.myapp'

    def ready(self):
        """Initialize app on startup."""
        pass  # ❌ Admin NOT imported
''',
                explanation="Missing admin import causes admin registration to fail",
            )

            self.stdout.write(self.style.SUCCESS("✅ Created 2 examples"))
        else:
            self.stdout.write("Rule already exists: admin_registration")

        # Create app label rule
        rule2, created2 = GuardrailRule.objects.get_or_create(
            category=category,
            name="app_config_label",
            defaults={
                "description": "AppConfig must have explicit label attribute",
                "pattern": r'class \w+Config\(AppConfig\):.*label = [\'"][\w_]+[\'"]',
                "message": "AppConfig must define explicit label attribute",
                "suggestion": "Add \"label = 'app_name'\" to your AppConfig class",
                "severity": "error",
                "is_builtin": True,
                "is_active": True,
            },
        )

        if created2:
            self.stdout.write(self.style.SUCCESS(f"✅ Created rule: {rule2.name}"))

            from apps.ui_hub.models import RuleExample

            # Valid example
            RuleExample.objects.create(
                rule=rule2,
                is_valid=True,
                code="""# apps.py - CORRECT
class UiHubConfig(AppConfig):
    name = 'apps.ui_hub'
    label = 'ui_hub'  # ✅ Explicit label
    verbose_name = 'UI Hub'
""",
                explanation="Explicit label ensures Django can find the app correctly",
            )

            # Invalid example
            RuleExample.objects.create(
                rule=rule2,
                is_valid=False,
                code="""# apps.py - WRONG
class UiHubConfig(AppConfig):
    name = 'apps.ui_hub'  # ❌ No explicit label
    verbose_name = 'UI Hub'
""",
                explanation="Missing label can cause app registration issues",
            )

            self.stdout.write(self.style.SUCCESS("✅ Created 2 examples"))
        else:
            self.stdout.write("Rule already exists: app_config_label")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ Admin Registration Rules Loaded"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
        self.stdout.write("Rules created:")
        self.stdout.write(f"  1. {rule.name} (severity: {rule.severity})")
        self.stdout.write(f"  2. {rule2.name} (severity: {rule2.severity})")
        self.stdout.write("")
        self.stdout.write("Problem solved:")
        self.stdout.write("  ❌ /admin/ui_hub/ returned 404")
        self.stdout.write("  ✅ Admin properly registered in AppConfig.ready()")
        self.stdout.write("  ✅ Explicit label prevents registration issues")
        self.stdout.write("")
