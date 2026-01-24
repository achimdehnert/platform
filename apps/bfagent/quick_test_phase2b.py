"""
Quick Test - Phase 2b Migration
Schneller Check ob die Migration erfolgreich war
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.models import Handler, HandlerCategory


def quick_test():
    """Schneller Status-Check"""
    
    print("\n🔍 QUICK TEST - Phase 2b Status\n")
    
    # 1. Categories
    cat_count = HandlerCategory.objects.count()
    print(f"📊 HandlerCategory: {cat_count} records")
    
    if cat_count == 0:
        print("   ❌ PROBLEM: Keine Kategorien!")
        print("   → Führe aus: python manage.py load_handler_categories\n")
        return False
    
    for cat in HandlerCategory.objects.all():
        handler_count = cat.handlers.count()
        print(f"   - {cat.code}: {handler_count} handlers")
    
    # 2. Handlers
    total_handlers = Handler.objects.count()
    print(f"\n📊 Handler: {total_handlers} records")
    
    if total_handlers == 0:
        print("   ℹ️  Keine Handler in DB (normal wenn noch nicht erstellt)")
        print("\n✅ QUICK TEST PASSED (keine Daten = OK)\n")
        return True
    
    # 3. Migration Status
    migrated = Handler.objects.exclude(category_fk=None).count()
    not_migrated = Handler.objects.filter(category_fk=None).count()
    
    print(f"\n📊 Migration Status:")
    print(f"   ✅ Migrated: {migrated}/{total_handlers}")
    print(f"   ❌ Not Migrated: {not_migrated}/{total_handlers}")
    
    if not_migrated > 0:
        print(f"\n   ⚠️  WARNING: {not_migrated} handlers not migrated!")
        print("   → Führe aus: python manage.py migrate core")
        print()
        return False
    
    # 4. Check for mismatches
    mismatches = 0
    for h in Handler.objects.exclude(category_fk=None):
        if h.category != h.category_fk.code:
            mismatches += 1
            if mismatches <= 3:  # Show first 3
                print(f"   ⚠️  Mismatch: {h.code} - '{h.category}' != '{h.category_fk.code}'")
    
    if mismatches > 0:
        print(f"\n   ❌ PROBLEM: {mismatches} mismatches found!")
        print()
        return False
    
    print("\n✅ QUICK TEST PASSED!")
    print("   All handlers migrated correctly\n")
    return True


if __name__ == '__main__':
    try:
        success = quick_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
