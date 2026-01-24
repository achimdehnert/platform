"""
Universal Auto-Setup Command.

Generic Guardrail Rule #4: Automatically setup ALL apps in the system.
Works for any app - no hardcoding required.
"""

import os
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """
    Universal auto-setup command for ALL Django apps.

    Automatically:
    - Creates missing database tables
    - Generates missing templates
    - Creates basic views and URLs
    - Works for ANY app without hardcoding
    """

    help = "Auto-setup ALL apps: migrations, templates, views"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only check, do not auto-fix",
        )
        parser.add_argument(
            "--app",
            type=str,
            help="Setup specific app only",
        )
        parser.add_argument(
            "--skip-migrations",
            action="store_true",
            help="Skip database migrations",
        )
        parser.add_argument(
            "--skip-templates",
            action="store_true",
            help="Skip template generation",
        )

    def handle(self, *args, **options):
        """Auto-setup all apps."""
        dry_run = options.get("dry_run", False)
        app_label = options.get("app")
        skip_migrations = options.get("skip_migrations", False)
        skip_templates = options.get("skip_templates", False)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🚀 Generic Guardrail Rule #4: Universal Auto-Setup"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        # Get apps to check
        if app_label:
            try:
                app_config = apps.get_app_config(app_label)
                apps_to_check = [app_config]
            except LookupError:
                self.stdout.write(self.style.ERROR(f'❌ App "{app_label}" not found'))
                return
        else:
            apps_to_check = self._get_local_apps()

        issues = {
            "missing_tables": [],
            "missing_templates": [],
            "missing_urls": [],
        }

        # Check all apps
        for app_config in apps_to_check:
            self.stdout.write(f"📦 Checking app: {app_config.label}")

            # Check tables
            if not skip_migrations:
                missing_tables = self._check_tables(app_config)
                if missing_tables:
                    issues["missing_tables"].extend(missing_tables)
                    for table in missing_tables:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️  Missing table: {table["table"]}')
                        )

            # Check templates
            if not skip_templates:
                if self._check_templates(app_config):
                    issues["missing_templates"].append(app_config)
                    self.stdout.write(self.style.WARNING(f"  ⚠️  Missing templates directory"))

            # Check URLs
            if self._check_urls(app_config):
                issues["missing_urls"].append(app_config)
                self.stdout.write(self.style.WARNING(f"  ⚠️  Missing urls.py"))

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("📊 Summary:"))
        self.stdout.write(f"  Apps checked: {len(apps_to_check)}")
        self.stdout.write(f'  Missing tables: {len(issues["missing_tables"])}')
        self.stdout.write(f'  Missing templates: {len(issues["missing_templates"])}')
        self.stdout.write(f'  Missing URLs: {len(issues["missing_urls"])}')
        self.stdout.write("")

        if not any(issues.values()):
            self.stdout.write(self.style.SUCCESS("✅ All apps properly configured!"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 Dry-run mode - no changes made"))
            self.stdout.write("")
            self.stdout.write("To auto-fix, run: python manage.py auto_setup_all")
            return

        # Auto-fix
        self._auto_fix(issues)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ Universal Auto-Setup Complete"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

    def _get_local_apps(self):
        """Get all local apps."""
        return [
            app
            for app in apps.get_app_configs()
            if app.name.startswith("apps.") or app.name.startswith("bfagent.")
        ]

    def _check_tables(self, app_config):
        """Check for missing tables."""
        missing = []
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if not self._table_exists(table_name):
                missing.append(
                    {
                        "app": app_config.label,
                        "model": model.__name__,
                        "table": table_name,
                    }
                )
        return missing

    def _check_templates(self, app_config):
        """Check if templates directory is missing."""
        app_path = Path(app_config.path)
        views_file = app_path / "views.py"
        templates_path = app_path / "templates"

        return views_file.exists() and not templates_path.exists()

    def _check_urls(self, app_config):
        """Check if urls.py is missing."""
        app_path = Path(app_config.path)
        views_file = app_path / "views.py"
        urls_file = app_path / "urls.py"

        return views_file.exists() and not urls_file.exists()

    def _table_exists(self, table_name):
        """Check if a table exists."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = %s
                    )
                """,
                    [table_name],
                )
                return cursor.fetchone()[0]
        except Exception:
            return False

    def _auto_fix(self, issues):
        """Auto-fix all issues."""
        # Fix missing tables
        if issues["missing_tables"]:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🔧 Fixing missing tables..."))
            try:
                call_command("makemigrations", interactive=False)
                call_command("migrate", interactive=False)
                self.stdout.write(self.style.SUCCESS("  ✅ Migrations applied"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Migration failed: {e}"))

        # Fix missing templates
        if issues["missing_templates"]:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🔧 Creating missing templates..."))
            for app_config in issues["missing_templates"]:
                self._create_templates(app_config)

        # Fix missing URLs
        if issues["missing_urls"]:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🔧 Creating missing URLs..."))
            for app_config in issues["missing_urls"]:
                self._create_urls(app_config)

    def _create_templates(self, app_config):
        """Create basic templates directory and files."""
        app_path = Path(app_config.path)
        templates_path = app_path / "templates" / app_config.label

        try:
            templates_path.mkdir(parents=True, exist_ok=True)

            # Create base.html
            base_html = templates_path / "base.html"
            base_html.write_text(self._get_base_template(app_config))

            # Create dashboard.html
            dashboard_html = templates_path / "dashboard.html"
            dashboard_html.write_text(self._get_dashboard_template(app_config))

            self.stdout.write(self.style.SUCCESS(f"  ✅ Created templates for {app_config.label}"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Template creation failed for {app_config.label}: {e}")
            )

    def _create_urls(self, app_config):
        """Create basic urls.py."""
        app_path = Path(app_config.path)
        urls_file = app_path / "urls.py"

        try:
            urls_file.write_text(self._get_urls_template(app_config))
            self.stdout.write(self.style.SUCCESS(f"  ✅ Created urls.py for {app_config.label}"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ URLs creation failed for {app_config.label}: {e}")
            )

    def _get_base_template(self, app_config):
        """Generate base.html template."""
        app_name = app_config.verbose_name or app_config.label.title()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{% block title %}}{app_name}{{% endblock %}}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{% url '{app_config.label}:dashboard' %}}">
                {app_name}
            </a>
        </div>
    </nav>

    <main class="container my-4">
        {{% block content %}}{{% endblock %}}
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {{% block extra_js %}}{{% endblock %}}
</body>
</html>
"""

    def _get_dashboard_template(self, app_config):
        """Generate dashboard.html template."""
        app_name = app_config.verbose_name or app_config.label.title()
        return f"""{{% extends '{app_config.label}/base.html' %}}

{{% block title %}}{app_name} Dashboard{{% endblock %}}

{{% block content %}}
<h1>{app_name} Dashboard</h1>
<p class="lead">Welcome to {app_name}</p>

<div class="row mt-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Getting Started</h5>
            </div>
            <div class="card-body">
                <p>This dashboard was auto-generated by Generic Guardrail Rule #4.</p>
                <p>Customize it in: <code>apps/{app_config.label}/templates/{app_config.label}/dashboard.html</code></p>
            </div>
        </div>
    </div>
</div>
{{% endblock %}}
"""

    def _get_urls_template(self, app_config):
        """Generate urls.py template."""
        return f'''"""URL configuration for {app_config.label}."""

from django.urls import path
from . import views

app_name = '{app_config.label}'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
]
'''
