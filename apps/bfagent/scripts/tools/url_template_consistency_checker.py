#!/usr/bin/env python
"""
URL-Template-View Consistency Checker
Prevents NoReverseMatch errors by validating complete URL coverage

ROOT CAUSE: Templates reference URLs that don't exist in urls.py
SOLUTION: Scan all templates, extract URL patterns, verify they exist
"""

# ============================================================================
# UTF-8 ENCODING FIX FOR WINDOWS
# This MUST be at the top before any other imports to ensure UTF-8 is used
# ============================================================================
import os
import sys

# Force UTF-8 mode globally (Python 3.7+)
os.environ.setdefault("PYTHONUTF8", "1")

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass  # Silently fail if reconfigure not available

# ============================================================================

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.urls import URLPattern, URLResolver, get_resolver


# Windows-safe console output (no Rich dependency for stability)
class SimpleConsole:
    """Windows-safe console with basic formatting"""

    @staticmethod
    def print(text):
        # Strip Rich markup for plain output
        clean_text = text.replace("[cyan]", "").replace("[/cyan]", "")
        clean_text = clean_text.replace("[yellow]", "").replace("[/yellow]", "")
        clean_text = clean_text.replace("[green]", "").replace("[/green]", "")
        clean_text = clean_text.replace("[red]", "").replace("[/red]", "")
        clean_text = clean_text.replace("[bold cyan]", "").replace("[/bold cyan]", "")
        clean_text = clean_text.replace("[bold red]", "").replace("[/bold red]", "")
        clean_text = clean_text.replace("[bold green]", "").replace("[/bold green]", "")
        clean_text = clean_text.replace("[/]", "")
        print(clean_text)


console = SimpleConsole()


class URLTemplateValidator:
    """Validates that all template URL references have corresponding URL patterns"""

    def __init__(self):
        self.template_dir = BASE_DIR / "templates"
        self.url_patterns: Set[str] = set()
        self.template_urls: Dict[str, List[Tuple[str, int]]] = {}
        self.missing_urls: List[Dict] = []
        self.orphan_urls: List[str] = []

    def extract_url_patterns(self):
        """Extract all URL patterns from Django URLconf"""
        console.print("\n[cyan]📊 Extracting URL patterns from urls.py...[/cyan]")

        resolver = get_resolver()

        def extract_patterns(urlpatterns, namespace=""):
            patterns = set()
            for pattern in urlpatterns:
                if isinstance(pattern, URLResolver):
                    # Nested URLconf
                    nested_namespace = (
                        f"{namespace}:{pattern.namespace}" if pattern.namespace else namespace
                    )
                    patterns.update(extract_patterns(pattern.url_patterns, nested_namespace))
                elif isinstance(pattern, URLPattern):
                    # URL pattern
                    if pattern.name:
                        full_name = f"{namespace}:{pattern.name}" if namespace else pattern.name
                        patterns.add(full_name)
            return patterns  # FIXED: Moved outside for loop

        self.url_patterns = extract_patterns(resolver.url_patterns)
        console.print(f"  ✅ Found {len(self.url_patterns)} URL patterns")

        # Debug: Print first 10 patterns to verify namespace handling
        if self.url_patterns:
            console.print("\n[yellow]🔍 Sample URL patterns (first 10):[/yellow]")
            for pattern in sorted(list(self.url_patterns)[:10]):
                console.print(f"    - {pattern}")

    def extract_template_urls(self):
        """Extract all {% url %} references from templates"""
        console.print("\n[cyan]🔍 Scanning templates for URL references...[/cyan]")

        # Pattern to match {% url 'name' %} or {% url "name" %}
        url_pattern = re.compile(r"{%\s*url\s+['\"]([^'\"]+)['\"]")

        template_count = 0
        url_count = 0

        for template_file in self.template_dir.rglob("*.html"):
            try:
                content = template_file.read_text(encoding="utf-8")
                matches = url_pattern.findall(content)

                if matches:
                    template_count += 1
                    relative_path = template_file.relative_to(self.template_dir)

                    for match in matches:
                        url_count += 1
                        # Get line number
                        lines = content.split("\n")
                        line_num = 0
                        for i, line in enumerate(lines, 1):
                            if match in line:
                                line_num = i
                                break

                        if match not in self.template_urls:
                            self.template_urls[match] = []
                        self.template_urls[match].append((str(relative_path), line_num))

            except Exception as e:
                console.print(f"  [yellow]⚠️  Error reading {template_file}: {e}[/yellow]")

        console.print(f"  ✅ Scanned {template_count} templates")
        console.print(f"  ✅ Found {url_count} URL references")

        # Debug: Print first 10 template URLs
        if self.template_urls:
            console.print("\n[yellow]🔍 Sample template URLs (first 10):[/yellow]")
            for url_name in sorted(list(self.template_urls.keys())[:10]):
                console.print(f"    - {url_name}")

    def validate_consistency(self):
        """Validate that all template URLs exist in URLconf"""
        console.print("\n[cyan]🔍 Validating URL consistency...[/cyan]")
        for url_name, locations in self.template_urls.items():
            if url_name not in self.url_patterns:
                self.missing_urls.append({"url_name": url_name, "locations": locations})

        # Find orphan URLs (defined but never used)
        used_urls = set(self.template_urls.keys())
        self.orphan_urls = list(self.url_patterns - used_urls)

        console.print(f"  ✅ Validation complete")

    def generate_report(self):
        """Generate detailed report"""
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]📊 URL-TEMPLATE CONSISTENCY REPORT[/bold cyan]")
        console.print("=" * 80)

        # Summary
        total_template_urls = len(self.template_urls)
        total_url_patterns = len(self.url_patterns)
        missing_count = len(self.missing_urls)
        orphan_count = len(self.orphan_urls)

        console.print(f"\n📈 SUMMARY:")
        console.print(f"  - Template URL references: {total_template_urls}")
        console.print(f"  - Defined URL patterns: {total_url_patterns}")
        console.print(
            f"  - Missing URLs: [{'red' if missing_count > 0 else 'green'}]{missing_count}[/]"
        )
        console.print(f"  - Orphan URLs: [yellow]{orphan_count}[/yellow]")

        # Missing URLs (CRITICAL)
        if self.missing_urls:
            console.print("\n" + "=" * 80)
            console.print("[bold red]❌ CRITICAL: MISSING URL PATTERNS[/bold red]")
            console.print("=" * 80)

            for missing in self.missing_urls:
                console.print(f"\n🚨 URL: [bold red]{missing['url_name']}[/bold red]")
                console.print(f"   Referenced in:")
                for template, line_num in missing["locations"]:
                    console.print(f"     - {template}:{line_num}")

                # Generate fix suggestion
                url_name = missing["url_name"]
                if ":" in url_name:
                    namespace, name = url_name.split(":", 1)
                    console.print(f"\n   💡 FIX: Add to apps/{namespace}/urls.py:")
                else:
                    console.print(f"\n   💡 FIX: Add to urls.py:")

                # Generate URL pattern suggestion
                view_name = (
                    name.replace("-", "_") if ":" in url_name else url_name.replace("-", "_")
                )
                console.print(
                    f'   [green]path("{name}/", views.{view_name}, name="{name}")[/green]'
                )

        # Orphan URLs (WARNING)
        if self.orphan_urls and len(self.orphan_urls) < 20:
            console.print("\n" + "=" * 80)
            console.print("[yellow]⚠️  ORPHAN URL PATTERNS (defined but never used)[/yellow]")
            console.print("=" * 80)
            console.print("\nThese URLs are defined but not referenced in any template:")
            for orphan in sorted(self.orphan_urls)[:10]:
                console.print(f"  - {orphan}")

        # Success
        if not self.missing_urls:
            console.print("\n" + "=" * 80)
            console.print(
                "[bold green]✅ ALL TEMPLATE URLS HAVE CORRESPONDING URL PATTERNS![/bold green]"
            )
            console.print("=" * 80)

        return len(self.missing_urls) == 0

    def generate_fix_script(self):
        """Generate automatic fix script"""
        if not self.missing_urls:
            return

        console.print("\n" + "=" * 80)
        console.print("[cyan]🔧 AUTO-FIX SUGGESTIONS[/cyan]")
        console.print("=" * 80)

        # Group by namespace
        fixes_by_app = {}
        for missing in self.missing_urls:
            url_name = missing["url_name"]
            if ":" in url_name:
                namespace, name = url_name.split(":", 1)
            else:
                namespace = "root"
                name = url_name

            if namespace not in fixes_by_app:
                fixes_by_app[namespace] = []

            fixes_by_app[namespace].append(
                {"name": name, "url_name": url_name, "view_name": name.replace("-", "_")}
            )

        for namespace, fixes in fixes_by_app.items():
            if namespace == "root":
                console.print(f"\n📝 Add to config/urls.py:")
            else:
                console.print(f"\n📝 Add to apps/{namespace}/urls.py:")

            for fix in fixes:
                console.print(
                    f"    path(\"{fix['name']}/\", views.{fix['view_name']}, name=\"{fix['name']}\"),"
                )

    def run(self) -> bool:
        """Run complete validation"""
        console.print("=" * 80)
        console.print("[bold cyan]URL-Template Consistency Checker[/bold cyan]")
        console.print("Validates that all template URL references exist in urls.py")
        console.print("=" * 80)

        self.extract_url_patterns()
        self.extract_template_urls()
        self.validate_consistency()
        success = self.generate_report()

        if not success:
            self.generate_fix_script()

        return success


def main():
    validator = URLTemplateValidator()
    success = validator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
