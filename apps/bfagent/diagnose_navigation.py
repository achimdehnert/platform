"""
Diagnose Navigation Items - Find all invalid URL names
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.urls import NoReverseMatch, reverse

from apps.control_center.models import NavigationItem


def diagnose_navigation_items():
    """Check all navigation items for valid URLs"""

    print("\n" + "=" * 70)
    print("  NAVIGATION ITEMS - URL VALIDATION")
    print("=" * 70 + "\n")

    # Get all navigation items with url_name
    items = (
        NavigationItem.objects.filter(item_type="link", url_name__isnull=False)
        .exclude(url_name="")
        .order_by("section__order", "order", "name")
    )

    total_count = items.count()
    print(f"📊 Found {total_count} navigation items with URL names\n")

    valid_items = []
    invalid_items = []

    for item in items:
        url_name = item.url_name

        # Try to reverse the URL
        try:
            url = reverse(url_name)
            valid_items.append(
                {
                    "code": item.code,
                    "name": item.name,
                    "url_name": url_name,
                    "url": url,
                    "section": item.section.name if item.section else "No Section",
                }
            )
        except NoReverseMatch as e:
            invalid_items.append(
                {
                    "code": item.code,
                    "name": item.name,
                    "url_name": url_name,
                    "section": item.section.name if item.section else "No Section",
                    "error": str(e),
                }
            )

    # Print results
    print(f"✅ VALID URLs: {len(valid_items)}")
    print(f"❌ INVALID URLs: {len(invalid_items)}\n")

    if invalid_items:
        print("=" * 70)
        print("  ❌ INVALID NAVIGATION ITEMS")
        print("=" * 70 + "\n")

        for item in invalid_items:
            print(f"📍 Code: {item['code']}")
            print(f"   Name: {item['name']}")
            print(f"   Section: {item['section']}")
            print(f"   URL Name: {item['url_name']}")
            print(f"   Error: {item['error']}")
            print()

    if valid_items:
        print("=" * 70)
        print("  ✅ VALID NAVIGATION ITEMS")
        print("=" * 70 + "\n")

        for item in valid_items[:10]:  # Show first 10
            print(f"✅ {item['code']}: {item['name']}")
            print(f"   URL: {item['url_name']} → {item['url']}")
            print()

        if len(valid_items) > 10:
            print(f"   ... and {len(valid_items) - 10} more valid items\n")

    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70 + "\n")
    print(f"Total Items: {total_count}")
    print(f"✅ Valid: {len(valid_items)} ({len(valid_items)*100//total_count}%)")
    print(f"❌ Invalid: {len(invalid_items)} ({len(invalid_items)*100//total_count}%)")

    if invalid_items:
        print("\n" + "=" * 70)
        print("  🔧 RECOMMENDED ACTIONS")
        print("=" * 70 + "\n")
        print("1. Create missing URL patterns in Django")
        print("2. OR: Update navigation items with correct URL names")
        print("3. OR: Deactivate invalid navigation items")
        print("\nInvalid URL names found:")
        for item in invalid_items:
            print(f"   - {item['url_name']}")
    else:
        print("\n🎉 All navigation items have valid URLs!")


if __name__ == "__main__":
    try:
        diagnose_navigation_items()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
