"""
List Navigation Sections
========================

Shows all available navigation sections.

Usage:
    python packages/bfagent_mcp/scripts/list_navigation_sections.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem


def list_sections():
    """List all navigation sections."""
    
    print("📋 Available Navigation Sections:\n")
    
    sections = NavigationSection.objects.all().order_by('order')
    
    if not sections:
        print("   ❌ No navigation sections found!")
        print("   The navigation system may not be initialized yet.")
        return False
    
    for section in sections:
        print(f"   {section.icon} {section.name}")
        print(f"      Code: {section.code}")
        print(f"      Order: {section.order}")
        print(f"      Active: {'✅' if section.is_active else '❌'}")
        
        # Count items (try different related names)
        try:
            item_count = NavigationItem.objects.filter(section=section).count()
            print(f"      Items: {item_count}")
            
            if item_count > 0:
                items = NavigationItem.objects.filter(
                    section=section,
                    is_visible=True
                ).order_by('order')[:5]
                for item in items:
                    print(f"         - {item.icon} {item.name}")
                if item_count > 5:
                    print(f"         ... and {item_count - 5} more")
        except Exception as e:
            print(f"      Items: (unable to count: {e})")
        
        print()
    
    return True


if __name__ == '__main__':
    try:
        list_sections()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
