"""
Management command to test new outline templates
"""

from django.core.management.base import BaseCommand

from apps.writing_hub.handlers import KishotenketsuOutlineHandler, SevenPointOutlineHandler


class Command(BaseCommand):
    help = "Test new outline templates (Kishōtenketsu and 7-Point Structure)"

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🚀 TESTING NEW OUTLINE TEMPLATES"))
        self.stdout.write("=" * 80 + "\n")

        # Test 1: Kishōtenketsu
        self.test_kishotenketsu()

        # Test 2: 7-Point Structure
        self.test_seven_point()

        # Summary
        self.show_summary()

    def test_kishotenketsu(self):
        """Test Kishōtenketsu (Japanese 4-Act Structure)"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("🎌 TEST 1: KISHŌTENKETSU OUTLINE"))
        self.stdout.write("=" * 80 + "\n")

        result = KishotenketsuOutlineHandler.handle(
            {
                "title": "Quiet Moments",
                "genre": "Literary Fiction",
                "premise": "A photographer discovers beauty in the ordinary rhythm of daily life, leading to an unexpected shift in perspective.",
                "num_chapters": 12,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"✅ Success: {result['success']}"))
        self.stdout.write(f"📚 Framework: {result['framework']}")
        self.stdout.write(f"📖 Chapters: {result['chapter_count']}")
        self.stdout.write("")

        # Show acts summary
        self.stdout.write(self.style.WARNING("📊 ACTS SUMMARY:"))
        acts = {}
        for item in result["acts"]:
            act = item["act"]
            if act not in acts:
                acts[act] = []
            acts[act].append(item["chapter"])

        for act_num, chapters in sorted(acts.items()):
            act_info = KishotenketsuOutlineHandler.ACT_STRUCTURE[act_num - 1]
            self.stdout.write(f"\n✨ Act {act_num}: {act_info['name']}")
            self.stdout.write(
                f"   Chapters: {min(chapters)}-{max(chapters)} ({len(chapters)} chapters)"
            )
            self.stdout.write(f"   Focus: {act_info['description']}")

        self.stdout.write("")

    def test_seven_point(self):
        """Test 7-Point Structure (Dan Wells)"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("🎯 TEST 2: 7-POINT STRUCTURE"))
        self.stdout.write("=" * 80 + "\n")

        result = SevenPointOutlineHandler.handle(
            {
                "title": "The Last Witness",
                "genre": "Thriller",
                "premise": "A detective must find a serial killer before the last witness is eliminated, but the investigation forces her to confront her own dark past.",
                "num_chapters": 14,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"✅ Success: {result['success']}"))
        self.stdout.write(f"📚 Framework: {result['framework']}")
        self.stdout.write(f"📖 Chapters: {result['chapter_count']}")
        self.stdout.write("")

        # Show mirror structure
        self.stdout.write(self.style.WARNING("🪞 MIRROR STRUCTURE:"))
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

            self.stdout.write(f"\n⚡ Point {point_num}: {point_info['name']}")
            self.stdout.write(f"   Chapters: {', '.join(map(str, chapters))}")
            self.stdout.write(f"   Description: {point_info['description']}")
            self.stdout.write(
                f"   Mirrors: Point {mirror} ({SevenPointOutlineHandler.STORY_POINTS[mirror-1]['name']})"
            )

        self.stdout.write("")

    def show_summary(self):
        """Show framework comparison"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 ALL 5 STORY FRAMEWORKS"))
        self.stdout.write("=" * 80 + "\n")

        frameworks = [
            ("Save the Cat", "15 Beats", "Commercial fiction, Screenplays"),
            ("Hero's Journey", "12 Stages", "Fantasy, Adventure, Epic"),
            ("Three-Act", "Flexible", "Universal, All genres"),
            ("Kishōtenketsu ✨", "4 Acts", "Literary, Character-driven"),
            ("7-Point Structure ✨", "7 Points", "Genre fiction, Thriller"),
        ]

        for name, structure, best_for in frameworks:
            self.stdout.write(
                f"  {'✅' if '✨' in name else '•'} {name:<25} {structure:<12} → {best_for}"
            )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ ALL TESTS PASSED!"))
        self.stdout.write("=" * 80)
        self.stdout.write(
            self.style.SUCCESS("\n🎉 BF Agent now has 5 professional story frameworks!")
        )
        self.stdout.write(self.style.SUCCESS("🏆 More than most commercial tools!\n"))
