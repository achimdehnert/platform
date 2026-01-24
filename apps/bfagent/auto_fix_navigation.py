"""
Auto-Fix Navigation Items - Fix common URL errors
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.control_center.models import NavigationItem

# URL fixes mapping
URL_FIXES = {
    # Handler Management - Move from control_center to bfagent
    "control_center:handler-management-dashboard": "bfagent:handler-management-dashboard",
    # Navigation Builder - These URLs don't exist, deactivate
    "control_center:navigation-builder-dashboard": None,
    "control_center:navigation-management-dashboard": None,
    # Data Sources - Some URLs don't exist
    "control_center:data-sources-import": None,
    "control_center:data-sources-import-history": None,
    "control_center:data-sources-dashboard": None,
    # Plugin Test - URL doesn't exist
    "control_center:plugin-test-dashboard": None,
    # Workflow/LLMs/Agents - These V2 URLs don't exist yet
    "control_center:workflow-list": None,
    "control_center:llms-v2-list": None,
    "control_center:agents-v2-list": None,
    "control_center:workflow-v2-dashboard": None,
    "control_center:templates-v2-list": None,
    "control_center:agent-actions-list": None,
    # Master Data - URL doesn't exist
    "control_center:master-data-dashboard": None,
    "control_center:navigation-sections-list": None,
    "control_center:navigation-items-list": None,
    "control_center:domains-list": None,
    # Sidebar Test - URL doesn't exist
    "control_center:sidebar-test": None,
    # Research API - Namespace doesn't exist
    "research_api:dashboard": None,
    "research_api:execute_research": None,
    "research_api:session_list": None,
    "research_api:session_create": None,
    "research_api:domain_list": None,
    "research_api:exschutz_dashboard": None,
    "research_api:source_list": None,
    "research_api:result_list": None,
    "research_api:api_docs": None,
    "research_api:settings": None,
    # Writing Hub V2 - URLs don't exist yet
    "writing_hub:book-projects-v2-list": None,
    "writing_hub:v2-dashboard": None,
    "writing_hub:chapter-v2-global-list": None,
    "writing_hub:character-v2-list": None,
    "writing_hub:character-v2-create": None,
    "writing_hub:world-v2-list": None,
    "writing_hub:world-v2-create": None,
    # Illustration - Namespace doesn't exist
    "illustration:gallery": None,
    # DSB - Namespace doesn't exist
    "dsb:dashboard": None,
}


def auto_fix_navigation():
    """Auto-fix navigation items with known issues"""

    print("\n" + "=" * 70)
    print("  AUTO-FIX NAVIGATION ITEMS")
    print("=" * 70 + "\n")

    fixed_count = 0
    deactivated_count = 0

    for old_url, new_url in URL_FIXES.items():
        items = NavigationItem.objects.filter(url_name=old_url)
        count = items.count()

        if count > 0:
            if new_url is None:
                # Deactivate items with non-existent URLs
                print(f"❌ Deactivating {count} item(s): '{old_url}'")
                items.update(is_active=False)
                deactivated_count += count
            else:
                # Update items with corrected URL
                print(f"🔧 Fixing {count} item(s):")
                print(f"   '{old_url}' → '{new_url}'")
                items.update(url_name=new_url)
                fixed_count += count
            print()

    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70 + "\n")
    print(f"🔧 Fixed: {fixed_count} items")
    print(f"❌ Deactivated: {deactivated_count} items")
    print(f"📊 Total: {fixed_count + deactivated_count} items processed\n")

    if fixed_count > 0 or deactivated_count > 0:
        print("=" * 70)
        print("  ✅ NEXT STEPS")
        print("=" * 70 + "\n")
        print("1. Refresh your browser (F5)")
        print("2. Navigate to: http://localhost:8000/control-center/")
        print("3. The NoReverseMatch errors should be gone!\n")
        print("💡 Deactivated items won't show in navigation anymore")
        print("   You can reactivate them later when the URLs are implemented\n")
    else:
        print("ℹ️  No items found to fix.\n")


if __name__ == "__main__":
    try:
        auto_fix_navigation()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
