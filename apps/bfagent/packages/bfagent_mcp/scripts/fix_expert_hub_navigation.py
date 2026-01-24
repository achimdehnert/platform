"""
Fix expert_hub Navigation Error
================================

Deaktiviert oder entfernt Navigation Items, die auf nicht-existierende
Namespaces verweisen.

Usage:
    python packages/bfagent_mcp/scripts/fix_expert_hub_navigation.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationItem


def fix_expert_hub_navigation():
    """Fix expert_hub navigation items."""
    
    print("🔍 Searching for expert_hub navigation items...")
    
    # Find all items with expert_hub in URL
    items = NavigationItem.objects.filter(url_name__icontains='expert_hub')
    
    if not items.exists():
        print("✅ No expert_hub items found in url_name")
        
        # Check external_url
        items = NavigationItem.objects.filter(external_url__icontains='expert_hub')
        if not items.exists():
            print("✅ No expert_hub items found in external_url")
            print("\n⚠️  The error might be in a template or somewhere else.")
            return True
    
    print(f"📋 Found {items.count()} expert_hub navigation items:\n")
    
    for item in items:
        print(f"   🔗 {item.name}")
        print(f"      Code: {item.code}")
        print(f"      URL: {item.url_name or item.external_url}")
        print(f"      Active: {item.is_active}")
        print(f"      Section: {item.section.name if item.section else 'None'}")
        
        # Deactivate it
        if item.is_active:
            item.is_active = False
            item.save()
            print(f"      ✅ Deactivated")
        else:
            print(f"      ℹ️  Already inactive")
        
        print()
    
    print("🎉 All expert_hub items deactivated!")
    return True


if __name__ == '__main__':
    try:
        fix_expert_hub_navigation()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
