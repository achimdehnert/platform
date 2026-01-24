#!/usr/bin/env python
"""
MINIMAL Handler-View Test Script
Tests the pure handler-first architecture with NO database dependencies
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
        import re
        matches = re.findall(r'/projects/projects/(\d+)/', response.text)
        if matches:
            return int(matches[0])
    return None


def test_minimal_handler(session, project_id, csrf_token):
    """Test MINIMAL pure handler-based view"""
    print("\n" + "="*60)
    print("🎯 Testing MINIMAL Handler View (Pure Architecture)")
    print("="*60)
    print("✅ NO database lookups for AgentAction")
    print("✅ NO PromptTemplate dependencies")
    print("✅ Direct EnrichmentHandler invocation")
    
    url = f"{BASE_URL}/projects/projects/{project_id}/enrich/run/minimal/"
    
    # Test with EnrichmentHandler actions
    for action in ['enhance_description', 'generate_character_cast', 'generate_outline']:
        print(f"\n🧪 Testing action: {action}")
        
        response = session.post(
            url,
            data={
                'action': action,
                'agent_id': 1,
                'requirements': f'Test {action} from minimal handler'
            },
            headers={'X-CSRFToken': csrf_token}
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Length: {len(response.text)} chars")
        
        if response.status_code == 200:
            print(f"   ✅ {action} SUCCESS!")
            # Show first 200 chars
            preview = response.text[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")
            return True
        else:
            print(f"   ❌ {action} FAILED")
            print(f"   Response: {response.text[:300]}")
    
    return False


def main():
    """Main test runner"""
    print("🎯 MINIMAL Handler-View Testing Script")
    print("="*60)
    print("Testing PURE handler-first architecture")
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
    
    # Run test
    success = test_minimal_handler(session, project_id, csrf_token)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Minimal Handler: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print("\n🎉 SUCCESS! Pure handler architecture works!")
        print("✅ Handler-First Architecture is functional!")
        print("\n📝 Next Steps:")
        print("  1. Add more handler actions")
        print("  2. Implement result persistence")
        print("  3. Add CharacterOutputHandler integration")
        print("  4. Build on this minimal foundation")
        return 0
    else:
        print("\n❌ Minimal handler has problems!")
        print("\n🔍 Check:")
        print("  1. Is server running? (make dev)")
        print("  2. Are handlers registered correctly?")
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
