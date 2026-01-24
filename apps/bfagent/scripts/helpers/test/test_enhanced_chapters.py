#!/usr/bin/env python
"""
Test script for Enhanced BookChapters Model
Tests compatibility and new functionality after Phase 1A migration
"""

import os
import sys

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import BookChapters, BookProjects


def test_enhanced_chapters():
    """Test the enhanced BookChapters functionality"""

    print("🧪 TESTING ENHANCED BOOKCHAPTERS MODEL")
    print("=" * 50)

    # Get first project for testing
    project = BookProjects.objects.first()
    if not project:
        print("❌ No projects found for testing")
        return False

    print(f"✅ Using project: {project.title}")

    try:
        # Test creating a chapter with new fields
        chapter = BookChapters(
            project=project,
            title="Test Chapter - Enhanced System",
            summary="Testing the enhanced chapter system with new fields",
            content="This is test content for our enhanced chapter system. It includes new features for AI assistance and consistency tracking.",
            chapter_number=999,  # High number to avoid conflicts
            status="draft",
            writing_stage="drafting",
            metadata={"test": True, "enhanced_system": True},
            ai_suggestions={
                "outline_suggestions": ["Add character development", "Include plot twist"]
            },
            consistency_score=0.85,
        )

        # Test save method (should auto-generate content_hash and word_count)
        chapter.save()

        print("✅ Chapter created successfully!")
        print(f"   ID: {chapter.id}")
        print(f"   Content Hash: {chapter.content_hash[:16]}...")
        print(f"   Word Count: {chapter.word_count}")
        print(f"   Writing Stage: {chapter.writing_stage}")
        print(f"   Progress: {chapter.progress_percentage}%")
        print(f"   Reading Time: {chapter.reading_time_minutes} min")
        print(f"   Metadata: {chapter.metadata}")
        print(f"   AI Suggestions: {chapter.ai_suggestions}")
        print(f"   Consistency Score: {chapter.consistency_score}")

        # Test existing functionality still works
        existing_chapters = BookChapters.objects.filter(project=project).exclude(id=chapter.id)
        print(f"✅ Existing chapters still accessible: {existing_chapters.count()} found")

        # Test CRUDConfig
        if hasattr(chapter, "CRUDConfig"):
            config = chapter.CRUDConfig()
            print(f"✅ CRUDConfig available with {len(config.list_display)} display fields")

        # Clean up test data
        chapter.delete()
        print("✅ Test chapter cleaned up")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def test_backward_compatibility():
    """Test that existing chapters still work"""

    print("\n🔄 TESTING BACKWARD COMPATIBILITY")
    print("=" * 50)

    try:
        # Get existing chapters
        existing_chapters = BookChapters.objects.all()[:3]

        for chapter in existing_chapters:
            print(f"✅ Chapter {chapter.chapter_number}: {chapter.title}")
            print(f"   Writing Stage: {chapter.writing_stage}")
            print(f"   Content Hash: {chapter.content_hash or 'None (will be generated on save)'}")
            print(f"   Metadata: {chapter.metadata}")

        print(f"✅ All {existing_chapters.count()} existing chapters accessible")
        return True

    except Exception as e:
        print(f"❌ Backward compatibility test failed: {str(e)}")
        return False


if __name__ == "__main__":
    success1 = test_enhanced_chapters()
    success2 = test_backward_compatibility()

    print("\n🎯 TEST SUMMARY")
    print("=" * 50)

    if success1 and success2:
        print("✅ ALL TESTS PASSED - Enhanced BookChapters system is working!")
        print("✅ Migration successful and backward compatible")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
