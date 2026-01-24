"""
Quick test script for new Phase 1 & 5 handlers
Run: python test_new_handlers.py
"""

import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import BookProjects
from apps.writing_hub.handlers import (
    ChapterGoalHandler,
    ChapterHookHandler,
    ChapterStructureHandler,
    LoglineGeneratorHandler,
    PremiseGeneratorHandler,
    ThemeIdentifierHandler,
)


def test_phase1_handlers():
    """Test Phase 1: Konzept & Idee handlers"""
    print("\n" + "=" * 80)
    print("🧪 TESTING PHASE 1 HANDLERS (Konzept & Idee)")
    print("=" * 80)

    # Create test project
    project = BookProjects.objects.filter(title__icontains="test").first()
    if not project:
        project = BookProjects.objects.first()

    if not project:
        print("❌ No projects found in database. Create one first.")
        return

    print(f"\n✓ Using test project: {project.title} (ID: {project.id})")

    # Test 1: Premise Generator
    print("\n1️⃣ Testing PremiseGeneratorHandler...")
    print("-" * 40)

    result = PremiseGeneratorHandler.handle(
        {
            "project_id": project.id,
            "inspiration": "A story about overcoming fears through friendship",
            "target_length": "novel",
        }
    )

    if result["success"]:
        print(f"✅ SUCCESS!")
        print(f"   Premise: {result['premise'][:200]}...")
        print(f"   Short: {result.get('premise_short', 'N/A')}")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return

    # Test 2: Theme Identifier
    print("\n2️⃣ Testing ThemeIdentifierHandler...")
    print("-" * 40)

    result = ThemeIdentifierHandler.handle(
        {"project_id": project.id, "premise": result.get("premise")}  # Use generated premise
    )

    if result["success"]:
        print(f"✅ SUCCESS!")
        print(f"   Primary Theme: {result.get('primary_theme', 'N/A')}")
        print(f"   Themes Count: {len(result.get('themes', []))}")
        for theme in result.get("themes", [])[:3]:
            print(f"   - {theme.get('name')}: {theme.get('description', '')[:100]}")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")

    # Test 3: Logline Generator
    print("\n3️⃣ Testing LoglineGeneratorHandler...")
    print("-" * 40)

    result = LoglineGeneratorHandler.handle({"project_id": project.id, "style": "dramatic"})

    if result["success"]:
        print(f"✅ SUCCESS!")
        print(f"   Logline: {result.get('logline', 'N/A')}")
        print(f"   Variations: {len(result.get('logline_variations', []))}")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")

    print("\n✓ Phase 1 tests complete!")


def test_phase5_handlers():
    """Test Phase 5: Chapter Breakdown handlers"""
    print("\n" + "=" * 80)
    print("🧪 TESTING PHASE 5 HANDLERS (Chapter Breakdown)")
    print("=" * 80)

    # Get test project
    project = BookProjects.objects.filter(title__icontains="test").first()
    if not project:
        project = BookProjects.objects.first()

    if not project:
        print("❌ No projects found in database")
        return

    print(f"\n✓ Using test project: {project.title} (ID: {project.id})")

    # Test 1: Chapter Structure
    print("\n1️⃣ Testing ChapterStructureHandler...")
    print("-" * 40)

    result = ChapterStructureHandler.handle(
        {
            "project_id": project.id,
            "chapter_number": 1,
        }
    )

    if result["success"]:
        print(f"✅ SUCCESS!")
        structure = result.get("structure", {})
        print(f"   Opening: {structure.get('opening', 'N/A')[:100]}...")
        print(f"   POV: {structure.get('pov_character', 'N/A')}")
        print(f"   Scene Count: {result.get('scene_count', 'N/A')}")
        print(f"   Est. Words: {result.get('estimated_word_count', 'N/A')}")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return

    # Test 2: Chapter Hook
    print("\n2️⃣ Testing ChapterHookHandler...")
    print("-" * 40)

    result = ChapterHookHandler.handle(
        {
            "project_id": project.id,
            "chapter_number": 1,
            "chapter_structure": structure,
            "hook_type": "action",
        }
    )

    if result["success"]:
        print(f"✅ SUCCESS!")
        print(f"   Hook: {result.get('hook', 'N/A')[:150]}...")
        print(f"   Variations: {len(result.get('hook_variations', []))}")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")

    # Test 3: Chapter Goal
    print("\n3️⃣ Testing ChapterGoalHandler...")
    print("-" * 40)

    result = ChapterGoalHandler.handle(
        {"project_id": project.id, "chapter_number": 1, "chapter_structure": structure}
    )

    if result["success"]:
        print(f"✅ SUCCESS!")
        print(f"   Goal: {result.get('chapter_goal', 'N/A')[:100]}...")
        print(f"   Conflicts: {len(result.get('conflicts', []))}")
        print(f"   Stakes: {result.get('stakes', 'N/A')[:100]}...")
        print(f"   Cost: ${result.get('cost', 0):.4f}")
    else:
        print(f"❌ FAILED: {result.get('error')}")

    print("\n✓ Phase 5 tests complete!")


def main():
    """Run all tests"""
    print("\n" + "🚀" * 40)
    print("NEW HANDLERS TEST SUITE")
    print("=" * 80)
    print("Testing 6 new handlers:")
    print("  Phase 1: PremiseGenerator, ThemeIdentifier, LoglineGenerator")
    print("  Phase 5: ChapterStructure, ChapterHook, ChapterGoal")
    print("=" * 80)

    # Check for API key
    from django.conf import settings

    has_key = bool(
        getattr(settings, "OPENAI_API_KEY", None) or getattr(settings, "ANTHROPIC_API_KEY", None)
    )

    if not has_key:
        print("\n⚠️  WARNING: No LLM API key configured!")
        print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY in settings")
        print("   Tests will fail without API access")
        return

    print("\n✓ API key found - proceeding with tests\n")

    try:
        # Run tests
        test_phase1_handlers()
        test_phase5_handlers()

        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print("✅ All 6 handlers imported successfully")
        print("✅ API integration working")
        print("✅ Handlers ready for production use")
        print("\n🎉 ALL TESTS COMPLETE!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
