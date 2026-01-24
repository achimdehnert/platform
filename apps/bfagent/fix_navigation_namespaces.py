"""
Fix Navigation Items - Add missing namespaces to url_name fields
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.control_center.models import NavigationItem

# Mapping of url_name patterns to their namespaces
NAMESPACE_FIXES = {
    "customer_dashboard": "expert_hub:customer_dashboard",
    "hazmat_enrichment": "expert_hub:hazmat_enrichment",
    "substance_search": "expert_hub:substance_search",
}


def fix_navigation_items():
    """Fix navigation items with missing namespaces"""

    print("\n" + "=" * 60)
    print("  FIXING NAVIGATION ITEMS - NAMESPACE PREFIXES")
    print("=" * 60 + "\n")

    fixed_count = 0

    for old_url, new_url in NAMESPACE_FIXES.items():
        items = NavigationItem.objects.filter(url_name=old_url)
        count = items.count()

        if count > 0:
            print(f"📝 Found {count} item(s) with url_name='{old_url}'")
            print(f"   Updating to: '{new_url}'")

            items.update(url_name=new_url)
            fixed_count += count
            print(f"   ✅ Updated!\n")

    if fixed_count > 0:
        print(f"\n{'='*60}")
        print(f"  ✅ FIXED {fixed_count} NAVIGATION ITEMS!")
        print(f"{'='*60}\n")
        print("🎯 Next Step: Refresh your browser (F5)")
        print("   URL: http://localhost:8000/control-center/\n")
    else:
        print("ℹ️  No items found to fix.\n")
        print(
            "🔍 Checking all navigation items with 'expert', 'customer', 'hazmat' or 'substance'..."
        )

        all_items = (
            NavigationItem.objects.filter(url_name__icontains="expert")
            | NavigationItem.objects.filter(url_name__icontains="customer")
            | NavigationItem.objects.filter(url_name__icontains="hazmat")
            | NavigationItem.objects.filter(url_name__icontains="substance")
        )

        if all_items.exists():
            print(f"\nFound {all_items.count()} related items:")
            for item in all_items:
                print(f"  - {item.code}: {item.url_name}")
        else:
            print("\n⚠️  No related navigation items found in database!")
            print("   The navigation might be coming from a different source.")


if __name__ == "__main__":
    try:
        fix_navigation_items()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
