#!/usr/bin/env python
"""
Handler-View Test Script
Tests the new handler-based enrichment views
"""
import requests
import sys

# Configuration
BASE_URL = "http://localhost:8000"
PROJECT_ID = None  # Will be auto-detected

def find_first_project():
    """Find first available project"""
    print("🔍 Finding projects...")
    response = requests.get(f"{BASE_URL}/projects/projects/")
    if response.status_code == 200:
        # Try to extract project ID from HTML
        import re
        matches = re.findall(r'/projects/projects/(\d+)/', response.text)
        if matches:
            return int(matches[0])
    return None

def test_old_view(session, project_id, csrf_token):
    """Test OLD enrichment view (baseline)"""
    print("\n" + "="*60)
    print("📝 Testing OLD View: /enrich/run/")
    print("="*60)
    print("⚠️  OLD View uses project_enrichment.py (different actions)")
    
    url = f"{BASE_URL}/projects/projects/{project_id}/enrich/run/"
    
    # OLD system uses different actions from project_enrichment.py
    response = session.post(
        url,
        data={
            'agent_id': 1,
            'action': 'premise',  # project_enrichment action
            'requirements': 'Test from Python script',
            'context': ''
        },
        headers={'X-CSRFToken': csrf_token}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} chars")
    
    if response.status_code == 200:
        print("✅ OLD View works!")
        return True
    else:
        print("❌ OLD View failed!")
        print(f"Response: {response.text[:200]}")
        return False

def test_handler_view(session, project_id, csrf_token):
    """Test NEW handler-based view"""
    print("\n" + "="*60)
    print("🚀 Testing HANDLER View: /enrich/run/handler/")
    print("="*60)
    print("✅ HANDLER View uses EnrichmentHandler (handler-based actions)")
    
    url = f"{BASE_URL}/projects/projects/{project_id}/enrich/run/handler/"
    
    # HANDLER system uses actions from EnrichmentHandler
    response = session.post(
        url,
        data={
            'agent_id': 1,
            'action': 'enhance_description',  # EnrichmentHandler action
            'requirements': 'Test from Python script - Handler version',
            'context': ''
        },
        headers={'X-CSRFToken': csrf_token}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} chars")
    
    if response.status_code == 200:
        print("✅ HANDLER View works!")
        
        # Check for expected content
        if 'enrichment' in response.text.lower():
            print("✅ Response contains enrichment content")
        
        # Show first 300 chars
        print("\n📄 Response Preview:")
        print("-" * 60)
        print(response.text[:300])
        print("-" * 60)
        
        return True
    else:
        print("❌ HANDLER View failed!")
        print(f"\n🔍 Full Response:")
        print("-" * 60)
        print(response.text[:500])
        print("-" * 60)
        return False

def main():
    """Main test runner"""
    print("🧪 Handler-View Testing Script")
    print("="*60)
    
    # Create session
    session = requests.Session()
    
    # Find project
    project_id = find_first_project()
    
    if not project_id:
        print("❌ No projects found!")
        print("💡 Create a project first or check if server is running")
        return 1
    
    print(f"✅ Using Project ID: {project_id}")
    
    # Get CSRF token
    print("\n🔑 Getting CSRF token...")
    response = session.get(f"{BASE_URL}/projects/projects/{project_id}/")
    
    if response.status_code != 200:
        print(f"❌ Cannot access project! Status: {response.status_code}")
        return 1
    
    csrf_token = session.cookies.get('csrftoken')
    
    if not csrf_token:
        print("❌ No CSRF token found!")
        return 1
    
    print(f"✅ CSRF Token: {csrf_token[:20]}...")
    
    # Run tests
    old_ok = test_old_view(session, project_id, csrf_token)
    handler_ok = test_handler_view(session, project_id, csrf_token)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"OLD View:     {'✅ PASS' if old_ok else '❌ FAIL'}")
    print(f"HANDLER View: {'✅ PASS' if handler_ok else '❌ FAIL'}")
    
    if old_ok and handler_ok:
        print("\n🎉 SUCCESS! Both views work!")
        print("✅ Handler-First Architecture is functional!")
        return 0
    elif handler_ok:
        print("\n⚠️  Handler works but old view has issues")
        return 0
    else:
        print("\n❌ Handler view has problems!")
        print("\n🔍 Check:")
        print("  1. Is server running? (make dev)")
        print("  2. Are URLs correct in urls.py?")
        print("  3. Check server logs for errors")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
