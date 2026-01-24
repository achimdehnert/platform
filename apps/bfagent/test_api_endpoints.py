"""
Test API endpoints for domain-aware workflow builder
Run: python test_api_endpoints.py (while Django server is running)
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/workflow"

print("="*60)
print("TESTING DOMAIN-AWARE API ENDPOINTS")
print("="*60)

# Test 1: Domains List
print("\n[TEST 1] GET /api/workflow/domains/")
try:
    response = requests.get(f"{BASE_URL}/domains/")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: 200 OK")
        print(f"  Domains found: {data['count']}")
        for domain in data['domains']:
            print(f"    - {domain['display_name']}: {domain['template_count']} templates")
        print("  ✅ PASS")
    else:
        print(f"  ❌ FAIL: Status {response.status_code}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# Test 2: Workflow Templates List
print("\n[TEST 2] GET /api/workflow/workflows/templates/")
try:
    response = requests.get(f"{BASE_URL}/workflows/templates/")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: 200 OK")
        print(f"  Templates found: {data['count']}")
        for template in data['templates']:
            print(f"    - {template['name']}")
            print(f"      Domain: {template['domain']['display_name']} {template['domain']['icon']}")
            print(f"      Phases: {template['phase_count']}, Handlers: {template['handler_count']}")
        print("  ✅ PASS")
    else:
        print(f"  ❌ FAIL: Status {response.status_code}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# Test 3: Template Detail
print("\n[TEST 3] GET /api/workflow/workflows/templates/chapter_gen/")
try:
    response = requests.get(f"{BASE_URL}/workflows/templates/chapter_gen/")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: 200 OK")
        print(f"  Template: {data['name']}")
        print(f"  Domain: {data['domain']['display_name']}")
        print(f"  Phases: {len(data['phases'])}")
        for phase in data['phases']:
            print(f"    Phase: {phase['name']} - {len(phase['handlers'])} handlers")
        print(f"  Has pipeline (backward compat): {bool(data.get('pipeline'))}")
        print("  ✅ PASS")
    else:
        print(f"  ❌ FAIL: Status {response.status_code}")
        print(f"  Response: {response.text}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# Test 4: Domain Filter
print("\n[TEST 4] GET /api/workflow/workflows/templates/?domain=book_writing")
try:
    response = requests.get(f"{BASE_URL}/workflows/templates/?domain=book_writing")
    if response.status_code == 200:
        data = response.json()
        print(f"  Status: 200 OK")
        print(f"  Filtered templates: {data['count']}")
        all_book_writing = all(
            t['domain']['domain_id'] == 'book_writing' 
            for t in data['templates']
        )
        print(f"  All from book_writing domain: {all_book_writing}")
        print("  ✅ PASS" if all_book_writing else "  ❌ FAIL")
    else:
        print(f"  ❌ FAIL: Status {response.status_code}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print("\n" + "="*60)
print("API TESTING COMPLETE!")
print("="*60)
print("\n📚 Domain-Aware Workflow API is LIVE!")
