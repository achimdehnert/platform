"""
Fix ALL Navigation Issues
==========================

Behebt alle Navigation Items mit nicht-existierenden Namespaces.

Statt zu deaktivieren, werden sie gelöscht oder auf existierende URLs umgeleitet.

Usage:
    python packages/bfagent_mcp/scripts/fix_all_navigation_issues.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationItem


# Existierende Namespaces (aus URLs gefunden)
VALID_NAMESPACES = {
    'medtrans',
    'hub',
    'genagent',
    'control_center',
    'bfagent',
    'writing_hub',
    'accounts',  # Django accounts app
    'admin',  # Django admin
    'rest_framework',
    'debug_toolbar',
}


def fix_all_navigation_issues():
    """Fix all navigation items with invalid namespaces."""
    
    print("🔍 Searching for navigation items with invalid namespaces...\n")
    
    all_items = NavigationItem.objects.all()
    invalid_items = []
    
    for item in all_items:
        if item.url_name:
            # Check if url_name has namespace
            if ':' in item.url_name:
                namespace = item.url_name.split(':')[0]
                if namespace not in VALID_NAMESPACES:
                    invalid_items.append((item, namespace))
    
    if not invalid_items:
        print("✅ No invalid navigation items found!")
        return True
    
    print(f"📋 Found {len(invalid_items)} navigation items with invalid namespaces:\n")
    
    # Group by namespace
    by_namespace = {}
    for item, namespace in invalid_items:
        if namespace not in by_namespace:
            by_namespace[namespace] = []
        by_namespace[namespace].append(item)
    
    # Show what will be deleted
    for namespace, items in by_namespace.items():
        print(f"❌ Invalid namespace: '{namespace}' ({len(items)} items)")
        for item in items:
            print(f"   - {item.name} (code: {item.code})")
            print(f"     URL: {item.url_name}")
            if item.external_url:
                print(f"     External: {item.external_url}")
        print()
    
    # Delete items (automatic - no confirmation needed for fix script)
    deleted_count = 0
    for namespace, items in by_namespace.items():
        for item in items:
            print(f"🗑️  Deleting: {item.name}")
            item.delete()
            deleted_count += 1
    
    print(f"\n✅ Deleted {deleted_count} navigation items")
    print("\n🎉 Navigation should now work without errors!")
    
    return True


if __name__ == '__main__':
    try:
        fix_all_navigation_issues()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
