#!/usr/bin/env python
"""
Test Media Hub API endpoints.
Run: python scripts/test_media_hub_api.py
"""
import os
import sys
import json
import requests

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')


def test_list_presets():
    """Test listing available presets."""
    print("\n📋 Testing: List Presets")
    print("-" * 40)
    
    resp = requests.get(f"{BASE_URL}/media-hub/api/presets/")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Style presets: {len(data.get('style', []))}")
        print(f"✅ Format presets: {len(data.get('format', []))}")
        print(f"✅ Quality presets: {len(data.get('quality', []))}")
        print(f"✅ Voice presets: {len(data.get('voice', []))}")
        return True
    else:
        print(f"❌ Failed: {resp.status_code} - {resp.text}")
        return False


def test_submit_job():
    """Test submitting a render job."""
    print("\n🎨 Testing: Submit Render Job")
    print("-" * 40)
    
    job_data = {
        "job_type": "illustration",
        "prompt": "A magical forest with glowing mushrooms and fairy lights, fantasy art",
        "style_preset": "cinematic",
        "format_preset": "square-1-1",
        "quality_preset": "draft",
        "priority": 5,
    }
    
    resp = requests.post(
        f"{BASE_URL}/media-hub/api/jobs/submit/",
        json=job_data,
        headers={"Content-Type": "application/json"}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Job submitted!")
        print(f"   Job ID: {data.get('job_id')}")
        print(f"   UUID: {data.get('uuid')}")
        print(f"   Status: {data.get('status')}")
        return data.get('job_id')
    else:
        print(f"❌ Failed: {resp.status_code} - {resp.text}")
        return None


def test_job_status(job_id):
    """Test getting job status."""
    print(f"\n📊 Testing: Job Status (ID: {job_id})")
    print("-" * 40)
    
    resp = requests.get(f"{BASE_URL}/media-hub/api/jobs/{job_id}/status/")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Job Status:")
        print(f"   ID: {data.get('id')}")
        print(f"   Type: {data.get('job_type')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Attempts: {data.get('attempt_count')}/{data.get('max_attempts')}")
        if data.get('asset'):
            print(f"   Asset: {data['asset']}")
        return True
    else:
        print(f"❌ Failed: {resp.status_code} - {resp.text}")
        return False


def test_list_jobs():
    """Test listing jobs."""
    print("\n📃 Testing: List Jobs")
    print("-" * 40)
    
    resp = requests.get(f"{BASE_URL}/media-hub/api/jobs/?limit=5")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Found {data.get('count', 0)} jobs")
        for job in data.get('jobs', [])[:3]:
            print(f"   - Job #{job['id']}: {job['job_type']} ({job['status']})")
        return True
    else:
        print(f"❌ Failed: {resp.status_code} - {resp.text}")
        return False


def main():
    print("=" * 50)
    print("🎬 Media Hub API Test Suite")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    
    results = []
    
    # Test 1: List presets
    results.append(("List Presets", test_list_presets()))
    
    # Test 2: Submit job
    job_id = test_submit_job()
    results.append(("Submit Job", job_id is not None))
    
    # Test 3: Job status
    if job_id:
        results.append(("Job Status", test_job_status(job_id)))
    
    # Test 4: List jobs
    results.append(("List Jobs", test_list_jobs()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if job_id:
        print(f"\n💡 To process the job, run:")
        print(f"   python manage.py test_render_worker --process-job {job_id}")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
