"""
Quick Test Script for Handler Generator API
Tests the newly added URL routing
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.urls import reverse, resolve


def test_url_routing():
    """Test that all Handler Generator API URLs are properly routed"""
    
    print("🔍 Testing Handler Generator API URL Routing\n")
    
    # Test all expected URLs
    test_cases = [
        ('handler-generator-generate', '/api/handler-generator/generate/'),
        ('handler-generator-deploy', '/api/handler-generator/deploy/'),
        ('handler-generator-regenerate', '/api/handler-generator/regenerate/'),
        ('handler-generator-status', '/api/handler-generator/status/'),
    ]
    
    all_passed = True
    
    for url_name, expected_path in test_cases:
        try:
            # Test reverse URL lookup
            url = reverse(f'bfagent:{url_name}')
            
            # Test URL resolution
            resolved = resolve(url)
            
            # Check if path matches
            if url == expected_path:
                print(f"✅ {url_name:30} -> {url}")
                print(f"   View: {resolved.func.__name__}")
            else:
                print(f"❌ {url_name:30} -> Expected: {expected_path}, Got: {url}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {url_name:30} -> ERROR: {e}")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED - URL Routing is working!")
    else:
        print("❌ SOME TESTS FAILED - Check URLs")
    print("="*60)
    
    return all_passed


def test_api_views_importable():
    """Test that API views can be imported"""
    
    print("\n🔍 Testing API Views Import\n")
    
    try:
        from apps.bfagent.api.handler_generator_api import (
            generate_handler,
            deploy_handler,
            regenerate_handler,
            generator_status
        )
        
        print("✅ generate_handler imported")
        print("✅ deploy_handler imported")
        print("✅ regenerate_handler imported")
        print("✅ generator_status imported")
        
        # Test that they're callable
        assert callable(generate_handler), "generate_handler is not callable"
        assert callable(deploy_handler), "deploy_handler is not callable"
        assert callable(regenerate_handler), "regenerate_handler is not callable"
        assert callable(generator_status), "generator_status is not callable"
        
        print("\n✅ All API views are callable!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        return False


def test_views_package_export():
    """Test that views are exported from views package"""
    
    print("\n🔍 Testing Views Package Export\n")
    
    try:
        from apps.bfagent import views
        
        # Check if all Handler Generator API views are accessible
        assert hasattr(views, 'generate_handler'), "generate_handler not in views"
        assert hasattr(views, 'deploy_handler'), "deploy_handler not in views"
        assert hasattr(views, 'regenerate_handler'), "regenerate_handler not in views"
        assert hasattr(views, 'generator_status'), "generator_status not in views"
        
        print("✅ generate_handler accessible from views package")
        print("✅ deploy_handler accessible from views package")
        print("✅ regenerate_handler accessible from views package")
        print("✅ generator_status accessible from views package")
        
        print("\n✅ Views package exports are working!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Export check failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("HANDLER GENERATOR API - URL ROUTING TEST")
    print("="*60)
    
    # Run all tests
    results = []
    results.append(test_url_routing())
    results.append(test_api_views_importable())
    results.append(test_views_package_export())
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    if all(results):
        print("🎉 ALL TESTS PASSED! Handler Generator API is ready!")
        print("\n📝 Next Steps:")
        print("   1. Start server: make dev")
        print("   2. Test API endpoint: curl http://localhost:8000/api/handler-generator/status/")
        print("   3. Generate your first handler!")
    else:
        print("⚠️  SOME TESTS FAILED - Please check the output above")
    
    print("="*60)
