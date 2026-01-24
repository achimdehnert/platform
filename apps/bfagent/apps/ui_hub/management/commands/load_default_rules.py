"""Management command to load default guardrail rules."""

from django.core.management.base import BaseCommand

from apps.ui_hub.models import GuardrailCategory, GuardrailRule


class Command(BaseCommand):
    """Load default guardrail rules into database."""

    help = "Load default UI Hub guardrail rules"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing rules before loading"
        )

    def handle(self, *args, **options):
        """Execute command."""
        clear = options.get("clear", False)

        if clear:
            self.stdout.write("Clearing existing rules...")
            GuardrailRule.objects.all().delete()
            GuardrailCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING("✅ Existing rules cleared"))

        # Create categories
        self.stdout.write("\nCreating categories...")

        categories = {
            "naming": self.create_category("naming", "Naming Conventions", 1),
            "separation": self.create_category("separation", "Separation of Concerns", 2),
            "htmx": self.create_category("htmx", "HTMX Patterns", 3),
            "structure": self.create_category("structure", "Project Structure", 4),
        }

        # Create naming rules
        self.stdout.write("\nCreating naming rules...")

        self.create_rule(
            category=categories["naming"],
            name="view_naming",
            description="Views must follow entity_action_view pattern",
            pattern=r"^[a-z][a-z0-9_]*_(list|detail|create|update|delete|htmx_[a-z]+)_view$",
            message="Views must follow pattern: entity_action_view (e.g., client_list_view)",
            suggestion="Use: {entity}_{action}_view",
            severity="error",
        )

        self.create_rule(
            category=categories["naming"],
            name="url_naming",
            description="URL names must use hyphens",
            pattern=r"^[a-z][a-z0-9-]*$",
            message="URL names must use hyphens, not underscores (e.g., client-list, not client_list)",
            suggestion="Use: {entity}-{action}",
            severity="warning",
        )

        self.create_rule(
            category=categories["naming"],
            name="htmx_url_prefix",
            description="HTMX endpoints must have htmx- prefix",
            pattern=r"^htmx-[a-z][a-z0-9-]*$",
            message="HTMX URL names must start with htmx- prefix",
            suggestion="Use: htmx-{entity}-{action}",
            severity="warning",
        )

        # Create separation rules
        self.stdout.write("\nCreating separation of concerns rules...")

        self.create_rule(
            category=categories["separation"],
            name="no_queries_in_templates",
            description="No database queries in templates",
            pattern=r"\{\{.*\.objects\.",
            message="Database queries should not be in templates. Use views or context processors.",
            suggestion="Move queries to view or selector",
            severity="error",
        )

        self.create_rule(
            category=categories["separation"],
            name="no_business_logic_in_views",
            description="No complex business logic in views",
            pattern=r"(if .* and .* and .*:|for .* in .* if .*:)",
            message="Complex logic should be in services, not views",
            suggestion="Move to service function",
            severity="warning",
        )

        # Create HTMX rules
        self.stdout.write("\nCreating HTMX rules...")

        self.create_rule(
            category=categories["htmx"],
            name="htmx_swap_default",
            description="Do not specify default hx-swap value",
            pattern=r'hx-swap=["\']innerHTML["\']',
            message="innerHTML is the default hx-swap, omit it",
            suggestion='Remove hx-swap="innerHTML"',
            severity="info",
        )

        self.create_rule(
            category=categories["htmx"],
            name="htmx_query_params",
            description="Use hx-vals instead of query params",
            pattern=r'hx-get=["\'][^"\']*\?',
            message="Use hx-vals for parameters instead of query string",
            suggestion='Use hx-vals=\'{"key": "value"}\'',
            severity="warning",
        )

        self.create_rule(
            category=categories["htmx"],
            name="htmx_form_post",
            description="Put hx-post on button, not form",
            pattern=r"<form[^>]*hx-post",
            message="Use hx-post on submit button, not form element",
            suggestion="Move hx-post to button inside form",
            severity="warning",
        )

        # Create structure rules
        self.stdout.write("\nCreating structure rules...")

        self.create_rule(
            category=categories["structure"],
            name="partial_naming",
            description="Partials must start with underscore",
            pattern=r"^_[a-z][a-z0-9_]*\.html$",
            message="Partial templates must start with underscore",
            suggestion="Rename to _{name}.html",
            severity="warning",
        )

        self.create_rule(
            category=categories["structure"],
            name="partials_directory",
            description="Partials must be in partials/ subdirectory",
            pattern=r"/partials/_[a-z][a-z0-9_]*\.html$",
            message="Partial templates must be in partials/ subdirectory",
            suggestion="Move to templates/{app}/{entity}/partials/",
            severity="warning",
        )

        self.stdout.write(self.style.SUCCESS(f"\n✅ Loaded {GuardrailRule.objects.count()} rules"))
        self.stdout.write(
            self.style.SUCCESS(f"✅ Created {GuardrailCategory.objects.count()} categories")
        )

    def create_category(self, code, name, order):
        """Create or get category."""
        category, created = GuardrailCategory.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": f"{name} guardrail rules",
                "display_order": order,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(f"  ✅ Created category: {name}")
        else:
            self.stdout.write(f"  ℹ️  Category exists: {name}")

        return category

    def create_rule(self, category, name, description, pattern, message, suggestion, severity):
        """Create or update rule."""
        rule, created = GuardrailRule.objects.update_or_create(
            category=category,
            name=name,
            defaults={
                "description": description,
                "pattern": pattern,
                "message": message,
                "suggestion": suggestion,
                "severity": severity,
                "is_builtin": True,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(f"  ✅ Created rule: {category.code}.{name}")
        else:
            self.stdout.write(f"  ♻️  Updated rule: {category.code}.{name}")

        return rule
