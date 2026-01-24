#!/usr/bin/env python
"""
Quick Status Scanner for BF Agent
Scans for HTMX features, views, and templates
"""
import os
import re
from collections import defaultdict
from pathlib import Path


def scan_htmx_features():
    """Scan templates for HTMX attributes"""
    features = []
    htmx_patterns = {
        "hx-get": "HTMX GET requests",
        "hx-post": "HTMX POST requests",
        "hx-target": "HTMX targets",
        "hx-swap": "HTMX swap strategies",
        "hx-indicator": "HTMX loading indicators",
        "hx-ext": "HTMX extensions",
    }

    template_dir = Path("templates")
    if not template_dir.exists():
        print("❌ Templates directory not found")
        return

    print("\n🔍 SCANNING HTMX FEATURES...")

    for file in template_dir.rglob("*.html"):
        try:
            content = file.read_text(encoding="utf-8")
            htmx_attrs = []

            for pattern, description in htmx_patterns.items():
                matches = re.findall(rf'{pattern}="[^"]*"', content)
                if matches:
                    htmx_attrs.extend(
                        [f"{pattern}({len(matches)})" for _ in range(min(1, len(matches)))]
                    )

            if htmx_attrs:
                features.append(f"📄 {file.relative_to(template_dir)}: {', '.join(htmx_attrs[:3])}")
        except Exception as e:
            print(f"⚠️  Error reading {file}: {e}")

    print(f"\n✅ Found {len(features)} templates with HTMX:")
    for f in features[:10]:  # Show first 10
        print(f"  {f}")
    if len(features) > 10:
        print(f"  ... and {len(features) - 10} more")


def scan_views():
    """Scan views for HTMX-related patterns"""
    print("\n🔍 SCANNING VIEWS...")

    views_dir = Path("apps/bfagent")
    if not views_dir.exists():
        print("❌ Views directory not found")
        return

    patterns = {
        "request.htmx": "HTMX request detection",
        "hx-": "HTMX headers/responses",
        "render.*partial": "Partial template rendering",
    }

    view_files = []
    for pattern in ["views.py", "crud_views.py", "*_views.py"]:
        view_files.extend(views_dir.rglob(pattern))

    for file in view_files:
        try:
            content = file.read_text(encoding="utf-8")
            htmx_features = []

            for pattern, description in patterns.items():
                if re.search(pattern, content):
                    htmx_features.append(description)

            if htmx_features:
                print(f"  📄 {file.name}: {', '.join(htmx_features)}")
        except Exception as e:
            print(f"⚠️  Error reading {file}: {e}")


def scan_urls():
    """Scan URLs for HTMX endpoints"""
    print("\n🔍 SCANNING URL PATTERNS...")

    urls_file = Path("apps/bfagent/urls.py")
    if not urls_file.exists():
        print("❌ URLs file not found")
        return

    try:
        content = urls_file.read_text(encoding="utf-8")

        # Extract URL patterns
        url_patterns = re.findall(r"path\([^)]+\)", content)

        print(f"✅ Found {len(url_patterns)} URL patterns:")
        for pattern in url_patterns[:15]:  # Show first 15
            # Clean up the pattern for display
            clean_pattern = pattern.replace("path(", "").replace(")", "").replace("'", "")
            print(f"  🔗 {clean_pattern}")

        if len(url_patterns) > 15:
            print(f"  ... and {len(url_patterns) - 15} more")

    except Exception as e:
        print(f"⚠️  Error reading URLs: {e}")


def check_feature_registry():
    """Check if feature registry is being used"""
    print("\n🔍 CHECKING FEATURE REGISTRY...")

    registry_file = Path("apps/bfagent/utils/feature_registry.py")
    if registry_file.exists():
        print("✅ Feature registry system installed")

        # Scan for @feature decorators
        for file in Path("apps/bfagent").rglob("*.py"):
            try:
                content = file.read_text(encoding="utf-8")
                if "@feature(" in content:
                    matches = re.findall(r"@feature\([^)]+\)", content)
                    print(f"  📄 {file.name}: {len(matches)} registered features")
            except:
                pass
    else:
        print("❌ Feature registry not installed")


def main():
    print("🚀 BF AGENT - QUICK STATUS SCAN")
    print("=" * 50)

    scan_htmx_features()
    scan_views()
    scan_urls()
    check_feature_registry()

    print("\n✅ Scan complete! Check .ai_instructions.md for implementation status.")


if __name__ == "__main__":
    main()
