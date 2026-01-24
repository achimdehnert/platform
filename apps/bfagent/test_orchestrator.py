#!/usr/bin/env python
"""Test the Multi-Hub Framework Orchestrator"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.services import get_orchestrator, WorkflowContext

def test_orchestrator():
    """Test orchestrator functionality"""
    print("🧪 Testing Multi-Hub Framework Orchestrator\n")
    print("=" * 60)
    
    # Get orchestrator instance
    print("\n1️⃣ Initializing orchestrator...")
    orch = get_orchestrator()
    print(f"   ✅ Loaded {len(orch.hubs)} hubs: {', '.join(orch.hubs.keys())}")
    
    # Test workflow building
    print("\n2️⃣ Building workflow for Fiction book...")
    try:
        steps = orch.build_workflow("book_creation", "fiction")
        print(f"   ✅ Built {len(steps)} workflow steps:")
        for i, step in enumerate(steps, 1):
            required = "✳️" if step.is_required else "  "
            print(f"      {required} {i:2d}. {step.phase_name:20s} (order: {step.order})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test workflow execution (dry-run)
    print("\n3️⃣ Testing workflow execution (dry-run)...")
    try:
        context = WorkflowContext(
            domain_art="book_creation",
            domain_type="fiction",
            project_id=1,
            user_id=1
        )
        results = orch.execute_workflow(context, steps)
        
        print(f"   Status: {results['status']}")
        print(f"   ✅ Completed: {len(results['completed_steps'])} steps")
        print(f"   ⏭️  Skipped: {len(results['skipped_steps'])} steps")
        print(f"   ❌ Failed: {len(results['failed_steps'])} steps")
        
        if results['completed_steps']:
            print("\n   Completed steps:")
            for step in results['completed_steps']:
                print(f"      • {step}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test other domain types
    print("\n4️⃣ Testing other domain types...")
    test_cases = [
        ("book_creation", "non_fiction"),
        ("book_creation", "children"),
        ("book_creation", "academic"),
    ]
    
    for domain_art, domain_type in test_cases:
        try:
            steps = orch.build_workflow(domain_art, domain_type)
            print(f"   ✅ {domain_type:15s}: {len(steps)} steps")
        except Exception as e:
            print(f"   ❌ {domain_type:15s}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Orchestrator test complete!")
    return True

if __name__ == "__main__":
    success = test_orchestrator()
    sys.exit(0 if success else 1)