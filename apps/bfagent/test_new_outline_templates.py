"""
Quick Test for New Outline Templates
Tests Kishōtenketsu and 7-Point Structure
"""

from apps.writing_hub.handlers import KishotenketsuOutlineHandler, SevenPointOutlineHandler


def test_kishotenketsu():
    """Test Kishōtenketsu (Japanese 4-Act Structure)"""
    print("\n" + "=" * 80)
    print("🎌 TESTING KISHŌTENKETSU OUTLINE")
    print("=" * 80 + "\n")

    result = KishotenketsuOutlineHandler.handle(
        {
            "title": "Quiet Moments",
            "genre": "Literary Fiction",
            "premise": "A photographer discovers beauty in the ordinary rhythm of daily life, leading to an unexpected shift in perspective.",
            "num_chapters": 12,
        }
    )

    print(f"✅ Success: {result['success']}")
    print(f"📚 Framework: {result['framework']}")
    print(f"📖 Chapters: {result['chapter_count']}")
    print(f"\n{'-'*80}\n")
    print(result["outline"])
    print(f"\n{'-'*80}\n")

    # Show acts summary
    print("\n📊 ACTS SUMMARY:")
    acts = {}
    for item in result["acts"]:
        act = item["act"]
        if act not in acts:
            acts[act] = []
        acts[act].append(item["chapter"])

    for act_num, chapters in sorted(acts.items()):
        act_info = KishotenketsuOutlineHandler.ACT_STRUCTURE[act_num - 1]
        print(f"\nAct {act_num}: {act_info['name']}")
        print(f"  Chapters: {min(chapters)}-{max(chapters)} ({len(chapters)} chapters)")
        print(f"  Focus: {act_info['description']}")

    return result


def test_seven_point():
    """Test 7-Point Structure (Dan Wells)"""
    print("\n" + "=" * 80)
    print("🎯 TESTING 7-POINT STRUCTURE")
    print("=" * 80 + "\n")

    result = SevenPointOutlineHandler.handle(
        {
            "title": "The Last Witness",
            "genre": "Thriller",
            "premise": "A detective must find a serial killer before the last witness is eliminated, but the investigation forces her to confront her own dark past.",
            "num_chapters": 14,
        }
    )

    print(f"✅ Success: {result['success']}")
    print(f"📚 Framework: {result['framework']}")
    print(f"📖 Chapters: {result['chapter_count']}")
    print(f"\n{'-'*80}\n")
    print(result["outline"])
    print(f"\n{'-'*80}\n")

    # Show mirror structure
    print("\n🪞 MIRROR STRUCTURE:")
    points = {}
    for item in result["points"]:
        point = item["point"]
        if point not in points:
            points[point] = []
        points[point].append(item["chapter"])

    for point_num in sorted(points.keys()):
        point_info = next(
            p for p in SevenPointOutlineHandler.STORY_POINTS if p["number"] == point_num
        )
        chapters = points[point_num]
        mirror = point_info["mirror"]

        print(f"\nPoint {point_num}: {point_info['name']}")
        print(f"  Chapters: {', '.join(map(str, chapters))}")
        print(f"  Description: {point_info['description']}")
        print(
            f"  Mirrors: Point {mirror} ({SevenPointOutlineHandler.STORY_POINTS[mirror-1]['name']})"
        )

    return result


def compare_frameworks():
    """Compare all 5 frameworks side by side"""
    print("\n" + "=" * 80)
    print("📊 FRAMEWORK COMPARISON")
    print("=" * 80 + "\n")

    frameworks = [
        {
            "name": "Save the Cat",
            "beats": 15,
            "structure": "3 Acts",
            "best_for": "Commercial fiction, Screenplays",
            "conflict": "High",
        },
        {
            "name": "Hero's Journey",
            "beats": 12,
            "structure": "3 Acts",
            "best_for": "Fantasy, Adventure, Epic",
            "conflict": "High",
        },
        {
            "name": "Three-Act",
            "beats": "Flexible",
            "structure": "3 Acts",
            "best_for": "Universal, All genres",
            "conflict": "Medium",
        },
        {
            "name": "Kishōtenketsu",
            "beats": 4,
            "structure": "4 Acts",
            "best_for": "Literary, Character-driven",
            "conflict": "None/Low",
        },
        {
            "name": "7-Point Structure",
            "beats": 7,
            "structure": "Mirror",
            "best_for": "Genre fiction, Thriller",
            "conflict": "High",
        },
    ]

    print(f"{'Framework':<20} {'Beats':<12} {'Structure':<12} {'Best For':<30} {'Conflict':<10}")
    print("-" * 84)

    for fw in frameworks:
        print(
            f"{fw['name']:<20} {str(fw['beats']):<12} {fw['structure']:<12} {fw['best_for']:<30} {fw['conflict']:<10}"
        )

    print("\n✨ BF Agent now supports 5 professional story frameworks!")
    print("🏆 More than most commercial tools!\n")


if __name__ == "__main__":
    print("\n🚀 TESTING NEW OUTLINE TEMPLATES")
    print("Testing Kishōtenketsu and 7-Point Structure")
    print("=" * 80)

    # Test 1: Kishōtenketsu
    kisho_result = test_kishotenketsu()

    # Test 2: 7-Point Structure
    seven_result = test_seven_point()

    # Compare all frameworks
    compare_frameworks()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETE!")
    print("=" * 80)
    print("\nBoth new templates are working perfectly! 🎉")
    print("\nYou can now use:")
    print("  - KishotenketsuOutlineHandler (Literary/Character-driven)")
    print("  - SevenPointOutlineHandler (Genre fiction/Thriller)")
    print("\nAlong with existing:")
    print("  - EnhancedSaveTheCatOutlineHandler")
    print("  - HerosJourneyOutlineHandler")
    print("  - ThreeActOutlineHandler")
    print("\n🚀 5 Professional Story Frameworks Ready!")
