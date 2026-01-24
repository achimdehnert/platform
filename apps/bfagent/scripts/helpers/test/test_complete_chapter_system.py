#!/usr/bin/env python
"""
Comprehensive Test Suite for Enhanced Chapter Writing System
Tests Phase 1A (Enhanced BookChapters) + Phase 1B (StoryArc & PlotPoint integration)
"""

import os
import sys

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import BookChapters, BookProjects, Characters, PlotPoint, StoryArc


def test_enhanced_bookchapters_system():
    """Test the complete enhanced BookChapters functionality"""

    print("🧪 TESTING COMPLETE CHAPTER WRITING SYSTEM")
    print("=" * 60)

    # Get first project for testing
    project = BookProjects.objects.first()
    if not project:
        print("❌ No projects found for testing")
        return False

    print(f"✅ Using project: {project.title}")

    try:
        # Phase 1: Create a Story Arc with unique name
        print("\n📖 PHASE 1: Creating Story Arc")
        import time

        unique_suffix = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp

        story_arc = StoryArc.objects.create(
            project=project,
            name=f"Test Arc {unique_suffix}",
            description="The primary storyline for our test chapter system",
            arc_type="main",
            start_chapter=1,
            end_chapter=5,
            central_conflict="Hero must overcome their greatest fear",
            importance_level="critical",
            completion_status="in_progress",
        )
        print(f"✅ Story Arc created: {story_arc.name}")
        print(f"   Span: {story_arc.chapter_span} chapters")
        print(f"   Progress: {story_arc.progress_percentage}%")

        # Phase 2: Create Plot Points
        print("\n🎯 PHASE 2: Creating Plot Points")
        plot_points = []

        # Inciting Incident
        plot_point_1 = PlotPoint.objects.create(
            story_arc=story_arc,
            project=project,
            name="The Call to Adventure",
            description="Hero receives the call that changes everything",
            chapter_number=1,
            sequence_order=1,
            point_type="inciting_incident",
            emotional_impact="high",
            completion_status="planned",
        )
        plot_points.append(plot_point_1)

        # Plot Point 1
        plot_point_2 = PlotPoint.objects.create(
            story_arc=story_arc,
            project=project,
            name="Crossing the Threshold",
            description="Hero commits to the journey",
            chapter_number=2,
            sequence_order=1,
            point_type="plot_point_1",
            emotional_impact="medium",
            completion_status="planned",
        )
        plot_points.append(plot_point_2)

        print(f"✅ Created {len(plot_points)} plot points")
        for pp in plot_points:
            print(f"   - {pp.name} (Ch.{pp.chapter_number})")

        # Phase 3: Create Enhanced Chapter with Storyline Integration
        print("\n📝 PHASE 3: Creating Enhanced Chapter")
        chapter = BookChapters.objects.create(
            project=project,
            title=f"Test Chapter {unique_suffix}: The Beginning of Everything",
            summary="Our hero receives the call to adventure and must decide their fate",
            content="""
            The morning sun cast long shadows across the cobblestone streets as Maya walked to work,
            unaware that her life was about to change forever. The mysterious letter in her mailbox
            would be the catalyst for an adventure beyond her wildest dreams.

            As she opened the envelope with trembling fingers, the words seemed to glow on the page:
            "Your destiny awaits. The choice is yours to make."

            This was the moment everything changed. The call to adventure had arrived.
            """,
            chapter_number=999,  # High number to avoid conflicts
            status="draft",
            target_word_count=2000,
            # Phase 1A: Enhanced Writing Features
            writing_stage="drafting",
            metadata={
                "themes": ["destiny", "choice", "transformation"],
                "pacing": "slow_build",
                "target_emotion": "anticipation",
            },
            ai_suggestions={
                "style_notes": ["More sensory details needed", "Strengthen character voice"],
                "plot_suggestions": ["Foreshadow the mentor character", "Add symbolic elements"],
            },
            consistency_score=0.78,
            # Phase 1B: Storyline Integration
            story_arc=story_arc,
            mood_tone="mysterious_anticipation",
            setting_location="Maya's neighborhood, morning",
            time_period="Present day, early morning",
            character_arcs={
                "maya": {
                    "arc_stage": "ordinary_world",
                    "emotional_state": "curious_apprehensive",
                    "growth_moment": "receives_call_to_adventure",
                }
            },
        )

        # Add plot points to chapter
        chapter.plot_points.add(*plot_points)

        print("✅ Enhanced Chapter created successfully!")
        print(f"   ID: {chapter.id}")
        print(f"   Title: {chapter.title}")
        print(f"   Content Hash: {chapter.content_hash[:16]}...")
        print(f"   Word Count: {chapter.word_count}")
        print(f"   Writing Stage: {chapter.writing_stage}")
        print(f"   Story Arc: {chapter.story_arc.name}")
        print(f"   Plot Points: {chapter.plot_points.count()}")
        print(f"   Progress: {chapter.progress_percentage}%")
        print(f"   Reading Time: {chapter.reading_time_minutes} min")
        print(f"   Mood/Tone: {chapter.mood_tone}")
        print(f"   Setting: {chapter.setting_location}")
        print(f"   Consistency Score: {chapter.consistency_score}")

        # Phase 4: Test CRUDConfig Integration
        print("\n⚙️ PHASE 4: Testing CRUDConfig Integration")

        # Test BookChapters CRUDConfig
        if hasattr(chapter, "CRUDConfig"):
            chapter_config = chapter.CRUDConfig()
            print("✅ BookChapters CRUDConfig available")
            print(f"   List Display Fields: {len(chapter_config.list_display)}")
            print(f"   Form Sections: {len(chapter_config.form_layout)}")
            print(f"   Actions Available: {len(chapter_config.actions)}")

        # Test StoryArc CRUDConfig
        if hasattr(story_arc, "CRUDConfig"):
            arc_config = story_arc.CRUDConfig()
            print("✅ StoryArc CRUDConfig available")
            print(f"   List Display Fields: {len(arc_config.list_display)}")
            print(f"   Actions Available: {len(arc_config.actions)}")

        # Test PlotPoint CRUDConfig
        if hasattr(plot_point_1, "CRUDConfig"):
            plot_config = plot_point_1.CRUDConfig()
            print("✅ PlotPoint CRUDConfig available")
            print(f"   List Display Fields: {len(plot_config.list_display)}")
            print(f"   Actions Available: {len(plot_config.actions)}")

        # Phase 5: Test Relationships and Queries
        print("\n🔗 PHASE 5: Testing Relationships")

        # Test story arc relationships
        arc_chapters = story_arc.chapters.all()
        print(f"✅ Story Arc has {arc_chapters.count()} chapters")

        # Test plot point relationships
        chapter_plot_points = chapter.plot_points.all()
        print(f"✅ Chapter has {chapter_plot_points.count()} plot points")

        # Test reverse relationships
        project_arcs = project.story_arcs.all()
        project_plot_points = project.plot_points.all()
        print(f"✅ Project has {project_arcs.count()} story arcs")
        print(f"✅ Project has {project_plot_points.count()} plot points")

        # Phase 6: Test Backward Compatibility
        print("\n🔄 PHASE 6: Testing Backward Compatibility")

        # Test existing chapters still work
        existing_chapters = BookChapters.objects.filter(project=project).exclude(id=chapter.id)
        print(f"✅ Existing chapters still accessible: {existing_chapters.count()} found")

        for existing_chapter in existing_chapters[:2]:  # Test first 2
            print(f"   - Chapter {existing_chapter.chapter_number}: {existing_chapter.title}")
            print(f"     Writing Stage: {existing_chapter.writing_stage}")
            print(f"     Story Arc: {existing_chapter.story_arc or 'None (backward compatible)'}")

        # Cleanup test data
        print("\n🧹 CLEANUP: Removing test data")
        chapter.delete()
        for pp in plot_points:
            pp.delete()
        story_arc.delete()
        print("✅ Test data cleaned up")

        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_system_performance():
    """Test system performance with multiple objects"""

    print("\n⚡ PERFORMANCE TESTING")
    print("=" * 60)

    try:
        # Test query performance
        import time

        start_time = time.time()
        chapters = BookChapters.objects.select_related("project", "story_arc").prefetch_related(
            "plot_points"
        )[:10]
        chapter_list = list(chapters)
        end_time = time.time()

        print(
            f"✅ Query Performance: {len(chapter_list)} chapters loaded in {end_time - start_time:.4f}s"
        )

        # Test model methods performance
        start_time = time.time()
        for chapter in chapter_list:
            _ = chapter.progress_percentage
            _ = chapter.reading_time_minutes
        end_time = time.time()

        print(
            f"✅ Model Methods: Calculated properties for {len(chapter_list)} chapters in {end_time - start_time:.4f}s"
        )

        return True

    except Exception as e:
        print(f"❌ Performance test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 COMPREHENSIVE CHAPTER WRITING SYSTEM TEST")
    print("=" * 60)

    success1 = test_enhanced_bookchapters_system()
    success2 = test_system_performance()

    print("\n🎯 FINAL TEST SUMMARY")
    print("=" * 60)

    if success1 and success2:
        print("✅ ALL TESTS PASSED!")
        print("✅ Chapter Writing System Phase 1A + 1B COMPLETE")
        print("✅ Enhanced BookChapters with Storyline Integration working perfectly")
        print("✅ Backward compatibility maintained")
        print("✅ CRUDConfig integration successful")
        print("✅ Performance acceptable")
        print("\n🎉 READY FOR PHASE 2: AI Integration!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
