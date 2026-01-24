#!/usr/bin/env python
"""
Quick Test: bfagent_mcp Refactoring Tools
"""
import os
import sys
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from bfagent_mcp.refactor_service import MCPRefactorService


async def test_tools():
    service = MCPRefactorService()
    
    print("\n" + "="*70)
    print("  bfagent_mcp Refactoring Tools - Quick Test")
    print("="*70)
    
    # Test 1: Naming Convention
    print("\n📝 TEST 1: Get Naming Convention (bfagent_mcp)")
    print("-" * 70)
    result = await service.get_naming_convention("bfagent_mcp", "markdown")
    print(result)
    
    # Test 2: List All Naming Conventions
    print("\n📝 TEST 2: List All Naming Conventions")
    print("-" * 70)
    result = await service.list_naming_conventions("markdown")
    print(result)
    
    # Test 3: List Component Types
    print("\n📝 TEST 3: List Component Types")
    print("-" * 70)
    result = await service.list_component_types("markdown")
    print(result)
    
    # Test 4: Check Path Protection (Mock)
    print("\n📝 TEST 4: Check Path Protection")
    print("-" * 70)
    result = await service.check_path_protection(
        "packages/bfagent_mcp/server.py",
        "markdown"
    )
    print(result)
    
    # Test 5: Get Refactor Options (Mock - no domain config yet)
    print("\n📝 TEST 5: Get Refactor Options (writing_hub)")
    print("-" * 70)
    result = await service.get_refactor_options("writing_hub", "markdown")
    print(result[:500] + "..." if len(result) > 500 else result)
    
    print("\n" + "="*70)
    print("  ✅ ALL TESTS COMPLETED!")
    print("="*70)
    print("\n💡 Next Steps:")
    print("   1. Create MCPDomainConfig entries for your domains")
    print("   2. Add MCPProtectedPath entries for critical files")
    print("   3. Use the tools in Windsurf!\n")


if __name__ == "__main__":
    asyncio.run(test_tools())
