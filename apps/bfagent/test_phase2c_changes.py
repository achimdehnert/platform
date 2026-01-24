"""
Test Phase 2c Code Changes

Tests that all code updates work correctly with new category_fk field.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.models import Handler, HandlerCategory


def test_handler_queries():
    """Test Handler queries work with new category_fk"""
    print("\n🧪 Test 1: Handler Query with category_fk")
    print("=" * 70)
    
    try:
        # Test order_by with category_fk__code
        handlers = Handler.objects.filter(is_active=True).order_by('category_fk__code', 'code')
        print(f"  ✅ Query successful: {handlers.count()} handlers found")
        
        # Show first few
        for h in handlers[:3]:
            print(f"     - {h.code} ({h.category_fk.code if h.category_fk else 'None'})")
        
        return True
    except Exception as e:
        print(f"  ❌ Query failed: {e}")
        return False


def test_category_filters():
    """Test category filters with FK lookup"""
    print("\n🧪 Test 2: Category Filters")
    print("=" * 70)
    
    try:
        categories = ['input', 'processing', 'output']
        for cat in categories:
            count = Handler.objects.filter(
                is_active=True,
                category_fk__code=cat
            ).count()
            print(f"  ✅ {cat}: {count} handlers")
        
        return True
    except Exception as e:
        print(f"  ❌ Filter failed: {e}")
        return False


def test_handler_loader():
    """Test handler_loader functions"""
    print("\n🧪 Test 3: Handler Loader")
    print("=" * 70)
    
    try:
        from apps.bfagent.services.handler_loader import list_handlers, get_handler_info
        
        # Test list_handlers
        all_handlers = list_handlers()
        print(f"  ✅ list_handlers(): {len(all_handlers)} handlers")
        
        # Test with category filter
        input_handlers = list_handlers(category='input')
        print(f"  ✅ list_handlers(category='input'): {len(input_handlers)} handlers")
        
        # Test get_handler_info
        if all_handlers:
            first_code = all_handlers[0]['handler_id']  # Uses property
            info = get_handler_info(first_code)
            if info:
                print(f"  ✅ get_handler_info('{first_code}'): {info['display_name']}")
            else:
                print(f"  ⚠️  get_handler_info('{first_code}'): Not found")
        
        return True
    except Exception as e:
        print(f"  ❌ Handler loader failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_handler_comparison():
    """Test handler category comparison"""
    print("\n🧪 Test 4: Handler Category Comparison")
    print("=" * 70)
    
    try:
        # Get two handlers from same category
        input_handlers = Handler.objects.filter(category_fk__code='input')[:2]
        
        if input_handlers.count() >= 2:
            h1, h2 = list(input_handlers)
            
            # Test comparison
            same_category = (h1.category_fk == h2.category_fk)
            print(f"  ✅ Category comparison: {h1.code} vs {h2.code}")
            print(f"     Same category: {same_category} (should be True)")
            
            # Test different category
            processing_handler = Handler.objects.filter(category_fk__code='processing').first()
            if processing_handler:
                different = (h1.category_fk != processing_handler.category_fk)
                print(f"  ✅ Different category: {h1.code} vs {processing_handler.code}")
                print(f"     Different: {different} (should be True)")
        else:
            print(f"  ⚠️  Not enough input handlers to test comparison")
        
        return True
    except Exception as e:
        print(f"  ❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_api():
    """Test workflow API functions"""
    print("\n🧪 Test 5: Workflow API")
    print("=" * 70)
    
    try:
        from apps.bfagent.api.workflow_api import list_handlers as api_list_handlers
        from django.test import RequestFactory
        
        # Create fake request
        factory = RequestFactory()
        request = factory.get('/api/workflow/handlers/')
        
        # Call API
        response = api_list_handlers(request)
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            print(f"  ✅ API call successful")
            print(f"     Total handlers: {data.get('count', 0)}")
            print(f"     Categories: {data.get('categories', {})}")
        else:
            print(f"  ❌ API returned status {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backwards_compatibility():
    """Test that helper properties still work"""
    print("\n🧪 Test 6: Backwards Compatibility")
    print("=" * 70)
    
    try:
        handler = Handler.objects.first()
        if not handler:
            print("  ⚠️  No handlers to test")
            return True
        
        # Test property access
        print(f"  ✅ handler.handler_id: {handler.handler_id} (property)")
        print(f"  ✅ handler.code: {handler.code} (field)")
        print(f"  ✅ handler.category: {handler.category} (helper property)")
        print(f"  ✅ handler.category_fk.code: {handler.category_fk.code if handler.category_fk else 'None'} (FK)")
        print(f"  ✅ handler.display_name: {handler.display_name} (property)")
        print(f"  ✅ handler.name: {handler.name} (field)")
        
        # Verify they match
        assert handler.handler_id == handler.code, "handler_id property mismatch!"
        assert handler.display_name == handler.name, "display_name property mismatch!"
        if handler.category_fk:
            assert handler.category == handler.category_fk.code, "category property mismatch!"
        
        print(f"  ✅ All properties match their underlying fields!")
        
        return True
    except Exception as e:
        print(f"  ❌ Backwards compatibility failed: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  🧪 PHASE 2C CODE CHANGES TEST SUITE")
    print("=" * 70)
    
    results = []
    
    results.append(("Handler Queries", test_handler_queries()))
    results.append(("Category Filters", test_category_filters()))
    results.append(("Handler Loader", test_handler_loader()))
    results.append(("Category Comparison", test_handler_comparison()))
    results.append(("Workflow API", test_workflow_api()))
    results.append(("Backwards Compatibility", test_backwards_compatibility()))
    
    print("\n" + "=" * 70)
    print("  📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print("\n" + "=" * 70)
    print(f"  Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED! Phase 2c changes successful!\n")
        sys.exit(0)
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed. Please review.\n")
        sys.exit(1)
