"""
ROLLBACK: Restore Deleted Navigation Items
===========================================

Stellt die gelöschten Navigation Items wieder her.

WICHTIG: Führe dieses Script NUR aus wenn du die Items wiederhaben willst!

Usage:
    python packages/bfagent_mcp/scripts/ROLLBACK_navigation_deletions.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationItem, NavigationSection


# Die gelöschten Items (aus dem Log)
DELETED_ITEMS = [
    # expert_hub Items
    {'code': 'hazmat_enrichment', 'name': 'Hazmat Enrichment', 'url_name': 'expert_hub:hazmat_enrichment', 'section': 'Expert Hub'},
    {'code': 'substance_search', 'name': 'Substance Search', 'url_name': 'expert_hub:substance_search', 'section': 'Expert Hub'},
    {'code': 'control_center_customers', 'name': 'Customers', 'url_name': 'expert_hub:customer_dashboard', 'section': 'Control Center'},
    
    # illustration Items
    {'code': 'illustration_management', 'name': 'Illustration Management', 'url_name': 'illustration:dashboard', 'section': 'Illustration Hub'},
    
    # format_hub Items
    {'code': 'powerpoint_dashboard', 'name': 'PowerPoint Dashboard', 'url_name': 'format_hub:powerpoint_dashboard', 'section': 'Format Hub'},
    {'code': 'powerpoint_library', 'name': 'PowerPoint Library', 'url_name': 'format_hub:powerpoint_library', 'section': 'Format Hub'},
    {'code': 'powerpoint_generator', 'name': 'PowerPoint Generator', 'url_name': 'format_hub:powerpoint_generator', 'section': 'Format Hub'},
    {'code': 'powerpoint_settings', 'name': 'PowerPoint Settings', 'url_name': 'format_hub:powerpoint_settings', 'section': 'Format Hub'},
    {'code': 'powerpoint_api', 'name': 'PowerPoint API', 'url_name': 'format_hub:powerpoint_api', 'section': 'Format Hub'},
    {'code': 'api_documentation', 'name': 'API Documentation', 'url_name': 'format_hub:api_documentation', 'section': 'Format Hub'},
    
    # research_hub Items
    {'code': 'research_settings', 'name': 'Research Settings', 'url_name': 'research_hub:settings', 'section': 'Research Hub'},
    
    # image_gen Items (geschätzt - nicht alle Details bekannt)
    {'code': 'image_gen_1', 'name': 'Image Generator', 'url_name': 'image_gen:dashboard', 'section': 'Illustration Hub'},
]


def restore_navigation_items():
    """Restore deleted navigation items."""
    
    print("🔄 ROLLBACK: Restoring deleted navigation items...\n")
    print("⚠️  ACHTUNG: Items werden als INACTIVE wiederhergestellt!")
    print("   So verursachen sie keine Fehler, sind aber unsichtbar.\n")
    
    restored = 0
    skipped = 0
    
    for item_data in DELETED_ITEMS:
        code = item_data['code']
        
        # Check if already exists
        if NavigationItem.objects.filter(code=code).exists():
            print(f"⏭️  Skipped: {item_data['name']} (already exists)")
            skipped += 1
            continue
        
        # Get section
        try:
            section = NavigationSection.objects.get(name=item_data['section'])
        except NavigationSection.DoesNotExist:
            print(f"❌ Section not found: {item_data['section']}")
            continue
        
        # Create item (INACTIVE!)
        NavigationItem.objects.create(
            section=section,
            code=code,
            name=item_data['name'],
            url_name=item_data['url_name'],
            is_active=False,  # INACTIVE to prevent errors
            icon='🔗',
            order=999,
        )
        
        print(f"✅ Restored (INACTIVE): {item_data['name']}")
        restored += 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Restored: {restored}")
    print(f"   ⏭️  Skipped: {skipped}")
    
    if restored > 0:
        print("\n⚠️  Items sind INACTIVE (is_active=False)")
        print("   Sie sind im Admin sichtbar aber in der Navigation versteckt.")
        print("   Aktiviere sie im Admin wenn du sie brauchst!")


if __name__ == '__main__':
    try:
        restore_navigation_items()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
