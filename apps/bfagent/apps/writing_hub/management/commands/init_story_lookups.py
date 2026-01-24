"""
Management command to initialize story element lookup tables
Populates EmotionalTone, ConflictLevel, BeatType, SceneConnectionType
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.writing_hub.models.story_elements import (
    BeatType,
    ConflictLevel,
    EmotionalTone,
    SceneConnectionType,
)


class Command(BaseCommand):
    help = "Initialize story element lookup tables with default values"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🎭 Initializing Story Element Lookup Tables"))
        self.stdout.write("=" * 80 + "\n")

        with transaction.atomic():
            emotional_created = self.init_emotional_tones()
            conflict_created = self.init_conflict_levels()
            beat_created = self.init_beat_types()
            connection_created = self.init_scene_connection_types()

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Done! Created: {emotional_created} emotional tones, "
                f"{conflict_created} conflict levels, {beat_created} beat types, "
                f"{connection_created} connection types\n"
            )
        )

    def init_emotional_tones(self):
        """Initialize emotional tone lookup table"""
        self.stdout.write("\n📊 Initializing Emotional Tones...")

        tones = [
            {
                "code": "hopeful",
                "name_en": "Hopeful",
                "name_de": "Hoffnungsvoll",
                "description": "Optimistic, looking forward to positive outcomes",
                "color": "#2ecc71",
                "order": 10,
            },
            {
                "code": "joyful",
                "name_en": "Joyful",
                "name_de": "Freudig",
                "description": "Happy, celebratory, uplifting",
                "color": "#f39c12",
                "order": 20,
            },
            {
                "code": "peaceful",
                "name_en": "Peaceful",
                "name_de": "Friedlich",
                "description": "Calm, serene, tranquil",
                "color": "#3498db",
                "order": 30,
            },
            {
                "code": "mysterious",
                "name_en": "Mysterious",
                "name_de": "Geheimnisvoll",
                "description": "Enigmatic, intriguing, unknown",
                "color": "#9b59b6",
                "order": 40,
            },
            {
                "code": "tense",
                "name_en": "Tense",
                "name_de": "Angespannt",
                "description": "Nervous, anxious, anticipatory",
                "color": "#e67e22",
                "order": 50,
            },
            {
                "code": "fearful",
                "name_en": "Fearful",
                "name_de": "Ängstlich",
                "description": "Scared, terrified, dreading",
                "color": "#e74c3c",
                "order": 60,
            },
            {
                "code": "angry",
                "name_en": "Angry",
                "name_de": "Wütend",
                "description": "Furious, enraged, confrontational",
                "color": "#c0392b",
                "order": 70,
            },
            {
                "code": "melancholic",
                "name_en": "Melancholic",
                "name_de": "Melancholisch",
                "description": "Sad, sorrowful, reflective",
                "color": "#34495e",
                "order": 80,
            },
            {
                "code": "desperate",
                "name_en": "Desperate",
                "name_de": "Verzweifelt",
                "description": "Hopeless, at wit's end, in crisis",
                "color": "#7f8c8d",
                "order": 90,
            },
            {
                "code": "triumphant",
                "name_en": "Triumphant",
                "name_de": "Triumphierend",
                "description": "Victorious, successful, accomplished",
                "color": "#16a085",
                "order": 100,
            },
        ]

        created = 0
        for tone_data in tones:
            tone, created_flag = EmotionalTone.objects.update_or_create(
                code=tone_data["code"], defaults=tone_data
            )
            if created_flag:
                created += 1
                self.stdout.write(f"  ✅ Created: {tone.name_en}")
            else:
                self.stdout.write(f"  ⏭️  Updated: {tone.name_en}")

        return created

    def init_conflict_levels(self):
        """Initialize conflict level lookup table"""
        self.stdout.write("\n⚔️  Initializing Conflict Levels...")

        levels = [
            {
                "code": "none",
                "name_en": "None",
                "name_de": "Kein Konflikt",
                "description": "No conflict, peaceful scene",
                "intensity": 0,
                "color": "#ecf0f1",
                "order": 10,
            },
            {
                "code": "low",
                "name_en": "Low",
                "name_de": "Niedrig",
                "description": "Minor tension or disagreement",
                "intensity": 2,
                "color": "#3498db",
                "order": 20,
            },
            {
                "code": "medium",
                "name_en": "Medium",
                "name_de": "Mittel",
                "description": "Significant conflict, raising stakes",
                "intensity": 5,
                "color": "#f39c12",
                "order": 30,
            },
            {
                "code": "high",
                "name_en": "High",
                "name_de": "Hoch",
                "description": "Intense conflict, major confrontation",
                "intensity": 8,
                "color": "#e67e22",
                "order": 40,
            },
            {
                "code": "climax",
                "name_en": "Climax",
                "name_de": "Höhepunkt",
                "description": "Peak intensity, decisive moment",
                "intensity": 10,
                "color": "#e74c3c",
                "order": 50,
            },
        ]

        created = 0
        for level_data in levels:
            level, created_flag = ConflictLevel.objects.update_or_create(
                code=level_data["code"], defaults=level_data
            )
            if created_flag:
                created += 1
                self.stdout.write(f"  ✅ Created: {level.name_en} (intensity: {level.intensity})")
            else:
                self.stdout.write(f"  ⏭️  Updated: {level.name_en}")

        return created

    def init_beat_types(self):
        """Initialize beat type lookup table"""
        self.stdout.write("\n🎬 Initializing Beat Types...")

        types = [
            {
                "code": "action",
                "name_en": "Action",
                "name_de": "Handlung",
                "description": "Physical action, movement, events",
                "icon": "fa-running",
                "color": "#e74c3c",
                "order": 10,
            },
            {
                "code": "dialogue",
                "name_en": "Dialogue",
                "name_de": "Dialog",
                "description": "Conversation between characters",
                "icon": "fa-comments",
                "color": "#3498db",
                "order": 20,
            },
            {
                "code": "description",
                "name_en": "Description",
                "name_de": "Beschreibung",
                "description": "Setting, atmosphere, sensory details",
                "icon": "fa-eye",
                "color": "#95a5a6",
                "order": 30,
            },
            {
                "code": "emotion",
                "name_en": "Emotion",
                "name_de": "Emotion",
                "description": "Internal feelings, reactions",
                "icon": "fa-heart",
                "color": "#e91e63",
                "order": 40,
            },
            {
                "code": "revelation",
                "name_en": "Revelation",
                "name_de": "Enthüllung",
                "description": "Discovery, realization, reveal",
                "icon": "fa-lightbulb",
                "color": "#f39c12",
                "order": 50,
            },
            {
                "code": "decision",
                "name_en": "Decision",
                "name_de": "Entscheidung",
                "description": "Character makes a choice",
                "icon": "fa-arrows-split-up-and-left",
                "color": "#9b59b6",
                "order": 60,
            },
            {
                "code": "conflict",
                "name_en": "Conflict",
                "name_de": "Konflikt",
                "description": "Confrontation, argument, fight",
                "icon": "fa-fire",
                "color": "#c0392b",
                "order": 70,
            },
            {
                "code": "reflection",
                "name_en": "Reflection",
                "name_de": "Reflexion",
                "description": "Internal thought, contemplation",
                "icon": "fa-brain",
                "color": "#34495e",
                "order": 80,
            },
        ]

        created = 0
        for type_data in types:
            beat_type, created_flag = BeatType.objects.update_or_create(
                code=type_data["code"], defaults=type_data
            )
            if created_flag:
                created += 1
                self.stdout.write(f"  ✅ Created: {beat_type.name_en}")
            else:
                self.stdout.write(f"  ⏭️  Updated: {beat_type.name_en}")

        return created

    def init_scene_connection_types(self):
        """Initialize scene connection type lookup table"""
        self.stdout.write("\n🔗 Initializing Scene Connection Types...")

        types = [
            {
                "code": "foreshadowing",
                "name_en": "Foreshadowing",
                "name_de": "Vorahnung",
                "description": "Hints at future events",
                "icon": "fa-crystal-ball",
                "order": 10,
            },
            {
                "code": "callback",
                "name_en": "Callback",
                "name_de": "Rückruf",
                "description": "References earlier events (payoff)",
                "icon": "fa-reply",
                "order": 20,
            },
            {
                "code": "parallel",
                "name_en": "Parallel",
                "name_de": "Parallel",
                "description": "Similar situations, themes, or events",
                "icon": "fa-equals",
                "order": 30,
            },
            {
                "code": "contrast",
                "name_en": "Contrast",
                "name_de": "Kontrast",
                "description": "Opposite situations for comparison",
                "icon": "fa-not-equal",
                "order": 40,
            },
            {
                "code": "cause_effect",
                "name_en": "Cause & Effect",
                "name_de": "Ursache & Wirkung",
                "description": "One scene directly causes another",
                "icon": "fa-arrow-right",
                "order": 50,
            },
            {
                "code": "mirror",
                "name_en": "Mirror",
                "name_de": "Spiegelung",
                "description": "Scenes mirror each other (beginning/end)",
                "icon": "fa-reflect-horizontal",
                "order": 60,
            },
        ]

        created = 0
        for type_data in types:
            conn_type, created_flag = SceneConnectionType.objects.update_or_create(
                code=type_data["code"], defaults=type_data
            )
            if created_flag:
                created += 1
                self.stdout.write(f"  ✅ Created: {conn_type.name_en}")
            else:
                self.stdout.write(f"  ⏭️  Updated: {conn_type.name_en}")

        return created
