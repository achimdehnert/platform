#!/usr/bin/env python3
"""
Beispiel-Skript: Demonstriert die Nutzung des Story Outline Tools.
"""

import sys
from pathlib import Path

# Für lokale Entwicklung
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import ConflictLevel, EmotionalTone, Status
from src.services import AnalysisService, NovelService, VisualizationService


def main():
    print("=" * 60)
    print("📚 Story Outline Tool - Beispiel")
    print("=" * 60)

    # Services initialisieren
    service = NovelService("/tmp/story-demo")
    analysis = AnalysisService()
    viz = VisualizationService()

    # =========================================================================
    # 1. Roman erstellen mit Heldenreise-Template
    # =========================================================================
    print("\n1️⃣  Roman erstellen...")

    novel = service.create_novel(
        title="Der verlorene Schlüssel",
        author="Maria Beispiel",
        genre="Mystery/Fantasy",
        template_id="heros-journey",
        target_word_count=75000,
    )

    novel.logline = "Ein Bibliothekar entdeckt, dass seine verstorbene Großmutter ihm einen Schlüssel zu einer anderen Welt hinterlassen hat."
    service.save_novel(novel)

    print(f"   ✓ '{novel.title}' erstellt")
    print(f"   ✓ Template: Heldenreise")
    print(f"   ✓ {len(novel.acts)} Akte mit {sum(len(a.chapters) for a in novel.acts)} Kapiteln")

    # =========================================================================
    # 2. Charaktere hinzufügen
    # =========================================================================
    print("\n2️⃣  Charaktere hinzufügen...")

    protagonist = service.add_character(
        novel,
        name="Elias Winter",
        role="protagonist",
        description="35-jähriger Bibliothekar, introvertiert, hat die Fähigkeit verloren zu träumen",
    )
    protagonist.arc = "Von Angst vor dem Unbekannten zu Mut und Akzeptanz"

    mentor = service.add_character(
        novel,
        name="Großmutter Helena",
        role="supporting",
        description="Verstorbene Großmutter, erscheint in Visionen",
    )

    antagonist = service.add_character(
        novel,
        name="Der Schatten",
        role="antagonist",
        description="Mysteriöse Entität, die den Schlüssel will",
    )

    ally = service.add_character(
        novel,
        name="Maya Chen",
        role="supporting",
        description="Antiquarin, wird zur Verbündeten und Liebesinteresse",
    )

    service.save_novel(novel)
    print(f"   ✓ {len(novel.characters)} Charaktere erstellt")

    # =========================================================================
    # 3. Handlungsstränge definieren
    # =========================================================================
    print("\n3️⃣  Handlungsstränge...")

    main_plot = service.add_plot_thread(
        novel,
        name="Die Suche nach dem Portal",
        description="Elias muss herausfinden, wozu der Schlüssel dient",
        thread_type="main",
    )

    subplot_love = service.add_plot_thread(
        novel,
        name="Liebe und Vertrauen",
        description="Die Beziehung zwischen Elias und Maya",
        thread_type="subplot",
    )

    subplot_past = service.add_plot_thread(
        novel,
        name="Großmutters Geheimnis",
        description="Die wahre Geschichte der Familie Winter",
        thread_type="subplot",
    )

    print(f"   ✓ {len(novel.plot_threads)} Handlungsstränge")

    # =========================================================================
    # 4. Szenen anreichern
    # =========================================================================
    print("\n4️⃣  Szenen konfigurieren...")

    scenes = novel.get_all_scenes()

    # Erste Szene konfigurieren
    if scenes:
        scene = scenes[0]
        scene.pov_character_id = protagonist.id
        scene.character_ids = [protagonist.id]
        scene.plot_thread_ids = [main_plot.id]
        scene.conflict_level = ConflictLevel.LOW
        scene.emotional_start = EmotionalTone.MELANCHOLIC
        scene.emotional_end = EmotionalTone.MYSTERIOUS
        scene.story_date_description = "Ein regnerischer Dienstagabend"
        scene.summary = "Elias erhält einen Brief vom Notar seiner verstorbenen Großmutter."
        scene.status = Status.OUTLINED

    # Weitere Szenen mit wachsendem Konflikt
    conflict_progression = [
        ConflictLevel.LOW,
        ConflictLevel.LOW,
        ConflictLevel.MEDIUM,
        ConflictLevel.MEDIUM,
        ConflictLevel.HIGH,
        ConflictLevel.HIGH,
        ConflictLevel.CLIMAX,
        ConflictLevel.HIGH,
        ConflictLevel.MEDIUM,
        ConflictLevel.LOW,
    ]

    for i, scene in enumerate(scenes[:10]):
        if i < len(conflict_progression):
            scene.conflict_level = conflict_progression[i]
        # Zufällig Status setzen für Demo
        scene.status = [Status.IDEA, Status.OUTLINED, Status.DRAFTED][i % 3]

    service.save_novel(novel)
    print(f"   ✓ {len(scenes)} Szenen konfiguriert")

    # =========================================================================
    # 5. Analyse
    # =========================================================================
    print("\n5️⃣  Analyse...")

    # Pacing
    pacing = analysis.analyze_pacing(novel)
    print(f"   Konflikt-Verteilung:")
    for level, count in pacing["conflict_distribution"].items():
        bar = "█" * count
        print(f"      {level:8}: {bar}")

    # Status
    status = analysis.get_status_summary(novel)
    print(f"\n   Fortschritt: {status['completion_percentage']:.1f}%")

    # =========================================================================
    # 6. Visualisierungen
    # =========================================================================
    print("\n6️⃣  Visualisierungen generieren...")

    # Struktur-Diagramm
    structure = viz.generate_structure_diagram(novel)

    # Outline als Text
    outline = viz.generate_outline_text(novel, include_details=False)

    # HTML Export
    html = viz.export_to_html(novel)

    # Speichern
    output_dir = Path("/tmp/story-demo-output")
    output_dir.mkdir(exist_ok=True)

    (output_dir / "struktur.md").write_text(structure)
    (output_dir / "outline.md").write_text(outline)
    (output_dir / "roman.html").write_text(html)

    print(f"   ✓ Struktur-Diagramm: {output_dir}/struktur.md")
    print(f"   ✓ Outline: {output_dir}/outline.md")
    print(f"   ✓ HTML Export: {output_dir}/roman.html")

    # =========================================================================
    # 7. Zusammenfassung
    # =========================================================================
    print("\n" + "=" * 60)
    print("✅ Demo abgeschlossen!")
    print("=" * 60)
    print(
        f"""
Roman: {novel.title}
ID: {novel.id}
Charaktere: {len(novel.characters)}
Handlungsstränge: {len(novel.plot_threads)}
Szenen: {len(scenes)}
Ziel-Wortanzahl: {novel.target_word_count:,}
    """
    )

    # Mermaid Diagramm ausgeben
    print("\n📊 Struktur-Diagramm (Mermaid):")
    print("-" * 40)
    print(structure[:500] + "...\n")

    return novel


if __name__ == "__main__":
    main()
