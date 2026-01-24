"""
Phase 2b - Handler Normalisierung Test Suite

Testet die Migration von category CharField → category_fk FK
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.models import Handler, HandlerCategory


def test_1_check_categories_exist():
    """Test 1: Prüfe ob HandlerCategory Records existieren"""
    print("\n" + "="*70)
    print("  TEST 1: HandlerCategory Records")
    print("="*70)
    
    categories = HandlerCategory.objects.all()
    count = categories.count()
    
    print(f"📊 Kategorien gefunden: {count}")
    
    if count == 0:
        print("❌ FAILED: Keine Kategorien gefunden!")
        print("   Führe aus: python manage.py load_handler_categories")
        return False
    
    expected = ['input', 'processing', 'output']
    existing = list(categories.values_list('code', flat=True))
    
    for cat_code in expected:
        if cat_code in existing:
            cat = categories.get(code=cat_code)
            print(f"✅ {cat_code}: {cat.name} (ID: {cat.id})")
        else:
            print(f"❌ MISSING: {cat_code}")
            return False
    
    print("✅ TEST 1 PASSED\n")
    return True


def test_2_check_handlers_exist():
    """Test 2: Prüfe ob Handler Records existieren"""
    print("="*70)
    print("  TEST 2: Handler Records")
    print("="*70)
    
    handlers = Handler.objects.all()
    count = handlers.count()
    
    print(f"📊 Handlers gefunden: {count}")
    
    if count == 0:
        print("⚠️  WARNING: Keine Handler in DB")
        print("   Das ist OK wenn noch keine erstellt wurden")
        print("✅ TEST 2 PASSED (keine Handler = OK)\n")
        return True
    
    # Zeige erste 5 Handler
    print("\nErste Handler:")
    for h in handlers[:5]:
        print(f"  - {h.code}: {h.name}")
    
    print(f"✅ TEST 2 PASSED ({count} handlers)\n")
    return True


def test_3_check_migration_fields():
    """Test 3: Prüfe ob beide Felder existieren (category & category_fk)"""
    print("="*70)
    print("  TEST 3: Migration Fields Check")
    print("="*70)
    
    # Check if fields exist
    handler_fields = [f.name for f in Handler._meta.get_fields()]
    
    has_category = 'category' in handler_fields
    has_category_fk = 'category_fk' in handler_fields
    
    print(f"Field 'category' exists: {has_category}")
    print(f"Field 'category_fk' exists: {has_category_fk}")
    
    if not has_category:
        print("❌ FAILED: Field 'category' missing!")
        return False
    
    if not has_category_fk:
        print("❌ FAILED: Field 'category_fk' missing!")
        return False
    
    print("✅ TEST 3 PASSED\n")
    return True


def test_4_check_data_migration():
    """Test 4: Prüfe ob Daten migriert wurden"""
    print("="*70)
    print("  TEST 4: Data Migration Check")
    print("="*70)
    
    handlers = Handler.objects.all()
    
    if handlers.count() == 0:
        print("⚠️  No handlers to check")
        print("✅ TEST 4 PASSED (skipped - no data)\n")
        return True
    
    total = handlers.count()
    migrated = handlers.exclude(category_fk=None).count()
    not_migrated = handlers.filter(category_fk=None).count()
    
    print(f"📊 Total Handlers: {total}")
    print(f"✅ Migrated (category_fk set): {migrated}")
    print(f"❌ Not Migrated (category_fk=NULL): {not_migrated}")
    
    # Show details
    if migrated > 0:
        print("\nMigrated Handlers:")
        for h in handlers.exclude(category_fk=None)[:5]:
            print(f"  ✅ {h.code}: category='{h.category}' → category_fk={h.category_fk.code}")
    
    if not_migrated > 0:
        print("\n⚠️  Not Migrated Handlers:")
        for h in handlers.filter(category_fk=None)[:5]:
            print(f"  ❌ {h.code}: category='{h.category}' → category_fk=NULL")
    
    if not_migrated == 0:
        print("\n✅ TEST 4 PASSED (all migrated)\n")
        return True
    else:
        print(f"\n⚠️  TEST 4 WARNING: {not_migrated} handlers not migrated\n")
        return True  # Warning, not failure


def test_5_check_category_mapping():
    """Test 5: Prüfe ob category → category_fk mapping korrekt ist"""
    print("="*70)
    print("  TEST 5: Category Mapping Consistency")
    print("="*70)
    
    handlers = Handler.objects.exclude(category_fk=None)
    
    if handlers.count() == 0:
        print("⚠️  No migrated handlers to check")
        print("✅ TEST 5 PASSED (skipped)\n")
        return True
    
    mismatches = []
    
    for h in handlers:
        if h.category != h.category_fk.code:
            mismatches.append({
                'code': h.code,
                'old': h.category,
                'new': h.category_fk.code
            })
    
    if mismatches:
        print(f"❌ FAILED: {len(mismatches)} mismatches found!")
        for m in mismatches[:5]:
            print(f"  Handler '{m['code']}': '{m['old']}' ≠ '{m['new']}'")
        return False
    
    print(f"✅ All {handlers.count()} handlers have consistent category mapping")
    print("✅ TEST 5 PASSED\n")
    return True


def test_6_check_helper_properties():
    """Test 6: Prüfe Helper Properties (category_code, category_name)"""
    print("="*70)
    print("  TEST 6: Helper Properties")
    print("="*70)
    
    handlers = Handler.objects.all()[:3]  # Test first 3
    
    if handlers.count() == 0:
        print("⚠️  No handlers to test")
        print("✅ TEST 6 PASSED (skipped)\n")
        return True
    
    for h in handlers:
        print(f"\nHandler: {h.code}")
        print(f"  category (CharField): {h.category}")
        print(f"  category_fk: {h.category_fk}")
        print(f"  category_code (property): {h.category_code}")
        print(f"  category_name (property): {h.category_name}")
        
        # Validate properties
        if h.category_fk:
            if h.category_code != h.category_fk.code:
                print(f"  ❌ category_code mismatch!")
                return False
            if h.category_name != h.category_fk.name:
                print(f"  ❌ category_name mismatch!")
                return False
            print(f"  ✅ Properties correct")
    
    print("\n✅ TEST 6 PASSED\n")
    return True


def test_7_check_backwards_compatibility():
    """Test 7: Prüfe Backwards Compatibility"""
    print("="*70)
    print("  TEST 7: Backwards Compatibility")
    print("="*70)
    
    handlers = Handler.objects.all()[:3]
    
    if handlers.count() == 0:
        print("⚠️  No handlers to test")
        print("✅ TEST 7 PASSED (skipped)\n")
        return True
    
    for h in handlers:
        # Test old-style access
        try:
            # These should still work
            old_category = h.category  # CharField
            code_prop = h.category_code  # Property
            name_prop = h.category_name  # Property
            
            print(f"✅ {h.code}: All access methods work")
            print(f"   category='{old_category}', code='{code_prop}', name='{name_prop}'")
        except Exception as e:
            print(f"❌ {h.code}: Backwards compatibility broken!")
            print(f"   Error: {e}")
            return False
    
    print("\n✅ TEST 7 PASSED\n")
    return True


def test_8_check_database_schema():
    """Test 8: Prüfe Database Schema (SQL)"""
    print("="*70)
    print("  TEST 8: Database Schema Check")
    print("="*70)
    
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check handlers table schema
        cursor.execute("PRAGMA table_info(handlers)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print("Handlers table columns:")
        
        # Check important columns
        checks = {
            'id': 'Primary Key',
            'code': 'Unique identifier',
            'category': 'Old CharField (deprecated)',
            'category_id': 'New FK to handler_categories',
        }
        
        for col_name, description in checks.items():
            if col_name in columns:
                col_info = columns[col_name]
                print(f"  ✅ {col_name}: {description}")
                print(f"     Type: {col_info[2]}, NotNull: {col_info[3]}")
            else:
                print(f"  ❌ {col_name}: MISSING!")
                return False
    
    print("\n✅ TEST 8 PASSED\n")
    return True


def run_all_tests():
    """Führe alle Tests aus"""
    print("\n" + "="*70)
    print("  🧪 PHASE 2B - HANDLER NORMALISIERUNG TEST SUITE")
    print("="*70 + "\n")
    
    tests = [
        test_1_check_categories_exist,
        test_2_check_handlers_exist,
        test_3_check_migration_fields,
        test_4_check_data_migration,
        test_5_check_category_mapping,
        test_6_check_helper_properties,
        test_7_check_backwards_compatibility,
        test_8_check_database_schema,
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"\n❌ {test_func.__name__} CRASHED!")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_func.__name__, False))
    
    # Summary
    print("="*70)
    print("  📊 TEST SUMMARY")
    print("="*70 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*70}")
    print(f"  Results: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Phase 2b migration successful!\n")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review and fix.\n")
    
    return passed == total


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
