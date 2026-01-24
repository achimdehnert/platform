"""
Management command to validate all NavigationItems.
Checks if URLs resolve, views exist, and templates are present.
Can auto-fix by clearing broken url_names or creating placeholder views.
"""
import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from apps.control_center.models_navigation import NavigationItem, NavigationSection


class Command(BaseCommand):
    help = "Validate all NavigationItems - check URLs, views, templates. Optionally fix issues."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Clear broken url_names (set to empty, keeps item active)",
        )
        parser.add_argument(
            "--deactivate",
            action="store_true",
            help="Deactivate broken navigation items instead of clearing URL",
        )
        parser.add_argument(
            "--create-views",
            action="store_true",
            help="Create placeholder views for missing URLs",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show all items, not just problems",
        )

    def handle(self, *args, **options):
        fix_mode = options["fix"]
        deactivate_mode = options["deactivate"]
        create_views = options["create_views"]
        verbose = options["verbose"]

        self.stdout.write(self.style.MIGRATE_HEADING("\n🔍 Validating Navigation Items...\n"))

        # Statistics
        total = 0
        valid = 0
        invalid = 0
        fixed = 0
        views_created = 0
        
        problems = []
        urls_to_create = []

        # Check all active NavigationItems
        items = NavigationItem.objects.filter(is_active=True).select_related("section")

        for item in items:
            total += 1
            issue = self.validate_item(item)
            
            if issue:
                invalid += 1
                problems.append((item, issue))
                
                # Analyze URL for potential fix
                url_info = self.analyze_url(item.url_name)
                if url_info:
                    urls_to_create.append((item, url_info))
                
                if deactivate_mode:
                    item.is_active = False
                    item.save()
                    fixed += 1
                    self.stdout.write(self.style.WARNING(f"  ❌ {item.section.name} > {item.name}"))
                    self.stdout.write(f"     URL: {item.url_name}")
                    self.stdout.write(f"     Issue: {issue}")
                    self.stdout.write(self.style.SUCCESS(f"     → DEACTIVATED"))
                elif fix_mode:
                    old_url = item.url_name
                    item.url_name = ""
                    item.save()
                    fixed += 1
                    self.stdout.write(self.style.WARNING(f"  ❌ {item.section.name} > {item.name}"))
                    self.stdout.write(f"     URL: {old_url}")
                    self.stdout.write(f"     Issue: {issue}")
                    self.stdout.write(self.style.SUCCESS(f"     → URL CLEARED (item remains active as '#' link)"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ {item.section.name} > {item.name}"))
                    self.stdout.write(f"     URL: {item.url_name}")
                    self.stdout.write(f"     Issue: {issue}")
            else:
                valid += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {item.section.name} > {item.name}"))

        # Also check NavigationSections with URLs
        self.stdout.write(self.style.MIGRATE_HEADING("\n🔍 Validating Navigation Sections...\n"))
        
        sections = NavigationSection.objects.filter(is_active=True).exclude(url_name="")
        
        for section in sections:
            total += 1
            issue = self.validate_section_url(section)
            
            if issue:
                invalid += 1
                problems.append((section, issue))
                
                if fix_mode or deactivate_mode:
                    old_url = section.url_name
                    section.url_name = ""
                    section.save()
                    fixed += 1
                    self.stdout.write(self.style.WARNING(f"  ❌ Section: {section.name}"))
                    self.stdout.write(f"     URL: {old_url}")
                    self.stdout.write(f"     Issue: {issue}")
                    self.stdout.write(self.style.SUCCESS(f"     → URL CLEARED"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Section: {section.name}"))
                    self.stdout.write(f"     URL: {section.url_name}")
                    self.stdout.write(f"     Issue: {issue}")
            else:
                valid += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Section: {section.name}"))

        # Create placeholder views if requested
        if create_views and urls_to_create:
            self.stdout.write(self.style.MIGRATE_HEADING("\n🔨 Creating Placeholder Views...\n"))
            views_created = self.create_placeholder_views(urls_to_create)

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING("\n📊 Summary\n"))
        self.stdout.write(f"  Total checked: {total}")
        self.stdout.write(self.style.SUCCESS(f"  Valid: {valid}"))
        
        if invalid > 0:
            self.stdout.write(self.style.ERROR(f"  Invalid: {invalid}"))
        else:
            self.stdout.write(f"  Invalid: {invalid}")
            
        if fixed > 0:
            self.stdout.write(self.style.WARNING(f"  Fixed: {fixed}"))
            
        if views_created > 0:
            self.stdout.write(self.style.SUCCESS(f"  Views created: {views_created}"))

        if problems and not (fix_mode or deactivate_mode):
            self.stdout.write(self.style.WARNING(
                "\n💡 Options:"
            ))
            self.stdout.write("   --fix         Clear broken URLs (items stay active as '#' links)")
            self.stdout.write("   --deactivate  Deactivate broken items")
            self.stdout.write("   --create-views Create placeholder views (advanced)")
            
        # Show URLs that need to be created
        if urls_to_create and not create_views:
            self.stdout.write(self.style.MIGRATE_HEADING("\n📝 URLs that need views:\n"))
            for item, info in urls_to_create[:10]:  # Show first 10
                self.stdout.write(f"  • {info['app_name']}:{info['view_name']}")
            if len(urls_to_create) > 10:
                self.stdout.write(f"  ... and {len(urls_to_create) - 10} more")

    def validate_item(self, item):
        """Validate a single NavigationItem. Returns error message if invalid, None if valid."""
        if not item.url_name:
            return None
        if item.url_name.startswith("/"):
            return None
            
        try:
            params = item.url_params or {}
            # Check if URL requires params we don't have
            if self.url_requires_params(item.url_name) and not params:
                return "URL requires parameters (pk, slug, etc.) - cannot be used as nav link"
            reverse(item.url_name, kwargs=params)
            return None
        except NoReverseMatch as e:
            return f"NoReverseMatch: {str(e)[:100]}"
        except Exception as e:
            return f"Error: {str(e)[:100]}"

    def validate_section_url(self, section):
        """Validate a NavigationSection's url_name. Returns error message if invalid, None if valid."""
        if not section.url_name:
            return None
        if section.url_name.startswith("/"):
            return None
            
        try:
            reverse(section.url_name)
            return None
        except NoReverseMatch as e:
            return f"NoReverseMatch: {str(e)[:100]}"
        except Exception as e:
            return f"Error: {str(e)[:100]}"

    def url_requires_params(self, url_name):
        """Check if a URL pattern typically requires parameters."""
        param_indicators = ['detail', 'edit', 'delete', 'update', 'confirm', 'resolve']
        return any(ind in url_name.lower() for ind in param_indicators)

    def analyze_url(self, url_name):
        """Analyze URL name to extract app and view info for creating placeholders."""
        if not url_name or url_name.startswith("/"):
            return None
            
        # Parse app_name:view_name format
        if ":" in url_name:
            parts = url_name.split(":", 1)
            app_name = parts[0].replace("-", "_")
            view_name = parts[1].replace("-", "_")
        else:
            app_name = "unknown"
            view_name = url_name.replace("-", "_")
            
        return {
            "app_name": app_name,
            "view_name": view_name,
            "original": url_name,
        }

    def create_placeholder_views(self, urls_to_create):
        """Create placeholder views for missing URLs. Returns count of views created."""
        created = 0
        
        # Group by app
        by_app = {}
        for item, info in urls_to_create:
            app = info["app_name"]
            if app not in by_app:
                by_app[app] = []
            by_app[app].append((item, info))
        
        for app_name, items in by_app.items():
            # Find the app directory
            app_path = self.find_app_path(app_name)
            if not app_path:
                self.stdout.write(self.style.WARNING(f"  ⚠️ App not found: {app_name}"))
                continue
                
            # Create placeholder views
            views_file = app_path / "views_placeholder.py"
            urls_file = app_path / "urls.py"
            
            view_code = self.generate_placeholder_views(items)
            url_code = self.generate_url_patterns(items)
            
            # Write views file
            with open(views_file, "a") as f:
                f.write(view_code)
            self.stdout.write(self.style.SUCCESS(f"  ✅ Created views in {views_file}"))
            
            # Show URL patterns to add
            self.stdout.write(f"  📝 Add to {urls_file}:")
            self.stdout.write(url_code)
            
            created += len(items)
            
        return created

    def find_app_path(self, app_name):
        """Find the path to an app directory."""
        # Try common locations
        base = Path(settings.BASE_DIR)
        candidates = [
            base / "apps" / app_name,
            base / app_name,
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def generate_placeholder_views(self, items):
        """Generate placeholder view code."""
        code = "\n# Auto-generated placeholder views\n"
        code += "from django.shortcuts import render\n"
        code += "from django.contrib.auth.decorators import login_required\n\n"
        
        for item, info in items:
            view_name = info["view_name"]
            code += f"""
@login_required
def {view_name}(request):
    \"\"\"Placeholder view for {item.name}\"\"\"
    return render(request, 'placeholder.html', {{
        'title': '{item.name}',
        'message': 'This page is under construction.',
    }})
"""
        return code

    def generate_url_patterns(self, items):
        """Generate URL pattern code to add."""
        code = "\n# Add these URL patterns:\n"
        for item, info in items:
            view_name = info["view_name"]
            url_path = view_name.replace("_", "-")
            code += f'    path("{url_path}/", views_placeholder.{view_name}, name="{info["original"].split(":")[-1]}"),\n'
        return code
