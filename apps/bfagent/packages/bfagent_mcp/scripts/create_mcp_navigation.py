"""
Create MCP Dashboard Navigation Item
=====================================

Django script to add MCP Dashboard to Control Center navigation.

Usage:
    python packages/bfagent_mcp/scripts/create_mcp_navigation.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem


def create_mcp_navigation():
    """Create MCP Dashboard navigation item."""
    
    print("🚀 Creating MCP Dashboard navigation item...")
    
    try:
        # Get Control Center section (try multiple codes)
        section = None
        for code in ['control_center_dashboard', 'control_center', 'DEVELOPER_TOOLS']:
            try:
                section = NavigationSection.objects.get(code=code)
                print(f"✅ Found section: {section.name} (code: {code})")
                break
            except NavigationSection.DoesNotExist:
                continue
        
        if not section:
            raise NavigationSection.DoesNotExist("No Control Center section found")
        
        # Check if already exists
        existing = NavigationItem.objects.filter(code='mcp_dashboard').first()
        if existing:
            print(f"ℹ️  Navigation item already exists: {existing.name}")
            
            # Update it
            existing.name = 'MCP Dashboard'
            existing.url_name = 'control_center:mcp-dashboard'
            existing.icon = '🎯'
            existing.order = 15
            existing.is_active = True
            existing.description = 'MCP Refactoring Tools & Domain Management'
            existing.save()
            
            print("✅ Updated existing navigation item")
            return existing
        
        # Create new
        nav_item = NavigationItem.objects.create(
            section=section,
            code='mcp_dashboard',
            name='MCP Dashboard',
            url_name='control_center:mcp-dashboard',
            icon='🎯',
            description='MCP Refactoring Tools & Domain Management',
            order=15,
            is_active=True,
        )
        
        print(f"✅ Created navigation item: {nav_item.name}")
        print(f"   URL: {nav_item.url_name}")
        print(f"   Icon: {nav_item.icon}")
        print(f"   Order: {nav_item.order}")
        
        return nav_item
        
    except NavigationSection.DoesNotExist:
        print("❌ Control Center section not found!")
        print("   Please create it first or check the section code.")
        return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    result = create_mcp_navigation()
    if result:
        print("\n🎉 SUCCESS! MCP Dashboard is now in the navigation.")
        print(f"   Access it at: /control-center/mcp/")
    else:
        print("\n❌ FAILED to create navigation item.")
        sys.exit(1)
