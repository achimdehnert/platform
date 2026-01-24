"""
Test MCP Orchestration API

Tests all endpoints of the new MCP orchestration layer.
"""

import json
from typing import Any, Dict

import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/mcp"


def test_list_servers():
    """Test listing all MCP servers"""
    print("\n" + "=" * 70)
    print("TEST 1: List MCP Servers")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/servers")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total']} servers:")
        for server in data["servers"]:
            print(f"   • {server['name']} ({server['id']}) - {server['tools_count']} tools")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_list_tools():
    """Test listing tools for specific server"""
    print("\n" + "=" * 70)
    print("TEST 2: List Tools for book-writing-mcp")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/tools?server=book-writing-mcp")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total']} tools:")
        for tool in data["tools"][:5]:  # Show first 5
            print(f"   • {tool['name']} - {tool['description']}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_list_all_tools():
    """Test listing all tools from all servers"""
    print("\n" + "=" * 70)
    print("TEST 3: List All Tools (all servers)")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/tools")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total']} total tools across all servers")

        # Group by server
        by_server = {}
        for tool in data["tools"]:
            server = tool["server"]
            if server not in by_server:
                by_server[server] = []
            by_server[server].append(tool)

        for server, tools in by_server.items():
            print(f"   • {server}: {len(tools)} tools")

        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_get_tool_info():
    """Test getting detailed info for specific tool"""
    print("\n" + "=" * 70)
    print("TEST 4: Get Tool Info (book_create_project)")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/tool/book-writing-mcp/book_create_project")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        tool = data["tool"]
        print(f"✅ Tool: {tool['name']}")
        print(f"   Description: {tool['description']}")
        print(f"   Category: {tool['category']}")
        print(f"   Input Schema: {json.dumps(tool['input_schema'], indent=2)}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_create_workflow_context():
    """Test creating workflow context"""
    print("\n" + "=" * 70)
    print("TEST 5: Create Workflow Context")
    print("=" * 70)

    context_id = "test_workflow_123"
    initial_data = {"workflow_name": "Test Book Workflow", "user_email": "test@example.com"}

    response = requests.post(
        f"{API_BASE}/context",
        json={"context_id": context_id, "initial_data": initial_data},
        headers={"Content-Type": "application/json"},
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Context created: {data['context_id']}")
        return context_id
    else:
        print(f"❌ Failed: {response.text}")
        return None


def test_execute_tool(context_id: str = None):
    """Test executing a tool"""
    print("\n" + "=" * 70)
    print("TEST 6: Execute Tool (book_create_project)")
    print("=" * 70)

    body = {
        "server": "book-writing-mcp",
        "tool": "book_create_project",
        "params": {
            "title": "Test Fantasy Novel",
            "genre": "Fantasy",
            "premise": "A young wizard discovers a hidden power",
        },
    }

    if context_id:
        body["context_id"] = context_id

    response = requests.post(
        f"{API_BASE}/execute", json=body, headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Tool executed successfully")
        print(f"   Execution time: {data['execution_time_ms']}ms")
        print(f"   Result: {json.dumps(data['result'], indent=2)}")
        return data["result"]
    else:
        print(f"❌ Failed: {response.text}")
        return None


def test_get_workflow_context(context_id: str):
    """Test getting workflow context"""
    print("\n" + "=" * 70)
    print("TEST 7: Get Workflow Context")
    print("=" * 70)

    response = requests.get(f"{API_BASE}/context/{context_id}")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Context retrieved:")
        print(f"   {json.dumps(data['context'], indent=2)}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_delete_workflow_context(context_id: str):
    """Test deleting workflow context"""
    print("\n" + "=" * 70)
    print("TEST 8: Delete Workflow Context")
    print("=" * 70)

    response = requests.delete(f"{API_BASE}/context/{context_id}/delete")

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_execute_cad_tool():
    """Test executing a CAD tool"""
    print("\n" + "=" * 70)
    print("TEST 9: Execute CAD Tool (cad_parse_dwg)")
    print("=" * 70)

    body = {
        "server": "cad-mcp",
        "tool": "cad_parse_dwg",
        "params": {"file_path": "/path/to/test.dxf", "format": "dxf"},
        "context_id": "cad_test_456",
    }

    response = requests.post(
        f"{API_BASE}/execute", json=body, headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ CAD tool executed successfully")
        print(f"   Execution time: {data['execution_time_ms']}ms")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("MCP ORCHESTRATION API TEST SUITE")
    print("=" * 80)

    results = []

    # Test 1-4: Discovery
    results.append(("List Servers", test_list_servers()))
    results.append(("List Tools (specific server)", test_list_tools()))
    results.append(("List All Tools", test_list_all_tools()))
    results.append(("Get Tool Info", test_get_tool_info()))

    # Test 5-8: Context Management
    context_id = test_create_workflow_context()
    if context_id:
        results.append(("Create Context", True))
        results.append(("Execute Tool", test_execute_tool(context_id) is not None))
        results.append(("Get Context", test_get_workflow_context(context_id)))
        results.append(("Delete Context", test_delete_workflow_context(context_id)))
    else:
        results.append(("Create Context", False))
        results.append(("Execute Tool", False))
        results.append(("Get Context", False))
        results.append(("Delete Context", False))

    # Test 9: CAD Tool
    results.append(("Execute CAD Tool", test_execute_cad_tool()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
