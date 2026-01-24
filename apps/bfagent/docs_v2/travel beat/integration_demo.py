"""
Travel Story - Integration Demo
===============================
Zeigt die vollständige Integration von:
- Location Database (PostgreSQL)
- On-Demand Location Generation
- User World (Personalisierung)
- Story Generation

SETUP:
    export POSTGRES_HOST=localhost
    export POSTGRES_DB=travel_story
    export POSTGRES_USER=postgres
    export POSTGRES_PASSWORD=xxx
    
    # Für echte Story-Generierung:
    export ANTHROPIC_API_KEY=sk-ant-xxx

USAGE:
    python integration_demo.py              # Mock-Generierung
    python integration_demo.py --real       # Echte LLM-Generierung
    python integration_demo.py --chapter 1  # Nur Kapitel 1 generieren
"""

import sys
import os
from datetime import datetime

from location_models import LayerType, PlaceType, PersonalPlace, StoryCharacter, LocationMemory
from location_repository import LocationRepository, DatabaseConfig
from location_generator import LocationGenerator
from integrated_generator import (
    IntegratedStoryGenerator, 
    StoryContext, 
    ChapterSpec,
    create_story_generator,
)

# Prüfe ob User World existiert (aus location_demo.py)
try:
    from location_demo import seed_barcelona, seed_rom, seed_user_world
    HAS_SEED = True
except ImportError:
    HAS_SEED = False


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


# ═══════════════════════════════════════════════════════════════
# EXAMPLE STORY SETUP
# ═══════════════════════════════════════════════════════════════

def create_example_story_context() -> StoryContext:
    """Erstelle Beispiel-Story-Kontext"""
    
    return StoryContext(
        title="Schatten über dem Mittelmeer",
        genre="romantic_suspense",
        
        protagonist_name="Elena Berger",
        protagonist_background="32, Kunsthistorikerin aus Berlin. Kürzlich geschieden, auf der Suche nach einem Neuanfang. Spezialisiert auf spanische Barockmalerei.",
        
        love_interest_name="Marco Conti",
        love_interest_background="35, italienischer Investigativ-Journalist. Arbeitet an einer Story über Kunstfälschungen. Charmant, aber verschlossen über seine Vergangenheit.",
        
        antagonist_name="Der Kurator",
        antagonist_background="Geheimnisvoller Leiter eines Kunstfälschungsrings. Seine Identität ist unbekannt.",
        
        primary_location="Barcelona",
        time_period="Gegenwart, Spätsommer",
        
        central_conflict="Elena entdeckt bei einer Ausstellung eine Fälschung und gerät ins Visier eines Kunstfälschungsrings. Marco, der an derselben Story arbeitet, wird ihr Verbündeter - doch kann sie ihm trauen?",
        
        spice_level="moderate",
    )


def create_example_chapter_specs() -> list:
    """Erstelle Beispiel-Kapitel-Spezifikationen"""
    
    return [
        ChapterSpec(
            chapter_number=1,
            title="Der Fund",
            beat_name="HOOK",
            beat_description="Elena entdeckt bei einer Vernissage im Picasso-Museum eine Unstimmigkeit in einem Gemälde.",
            story_location="Barcelona",
            pacing="atmospheric",
            target_words=2500,
            emotional_tone="neugierig, leicht beunruhigt",
            hook_hint="Ende mit dem Moment, als Elena merkt, dass sie beobachtet wird.",
        ),
        ChapterSpec(
            chapter_number=2,
            title="Der Fremde",
            beat_name="INCITING INCIDENT",
            beat_description="Marco spricht Elena an. Er scheint mehr über das Gemälde zu wissen.",
            story_location="Barcelona",
            pacing="action",
            target_words=2500,
            emotional_tone="Misstrauen, Anziehung",
            special_instructions=[
                "Erste Begegnung zwischen Elena und Marco",
                "Tension aufbauen - beide haben Geheimnisse",
            ],
        ),
        ChapterSpec(
            chapter_number=3,
            title="Schatten in der Nacht",
            beat_name="FIRST PLOT POINT",
            beat_description="Elena wird verfolgt. Marco rettet sie - aber war das Zufall?",
            story_location="Barcelona",
            pacing="action",
            target_words=3000,
            emotional_tone="Angst, Adrenalin, wachsendes Vertrauen",
            special_instructions=[
                "Verfolgungsjagd durch das Gotische Viertel",
                "Erste physische Nähe zwischen Elena und Marco",
            ],
        ),
    ]


# ═══════════════════════════════════════════════════════════════
# DEMO FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def demo_location_integration(repo: LocationRepository):
    """Demo: Location-System Integration"""
    
    print_section("Location-System Integration")
    
    # Generator mit Mock-LLM
    generator = LocationGenerator(repo, use_real_llm=False)
    
    # Hole Barcelona (sollte aus DB kommen wenn geseedet)
    print("  Loading Barcelona...")
    barcelona = generator.get_base_location("Barcelona", "Spanien")
    print(f"  ✓ {barcelona.name}: {len(barcelona.districts)} Viertel")
    
    # Hole Romance Layer
    print("  Loading Romance Layer...")
    romance = generator.get_location_layer("barcelona", LayerType.ROMANCE, "Barcelona")
    print(f"  ✓ {len(romance.places)} romantische Orte")
    
    # Hole User World
    print("  Loading User World...")
    user_world = repo.get_user_world("demo_user")
    if user_world:
        print(f"  ✓ User: {user_world.user_id}")
        print(f"    Charaktere: {[c.name for c in user_world.characters]}")
        print(f"    Ausschlüsse: {user_world.get_excluded_places('barcelona')}")
    else:
        print("  ⚠ Keine User World. Führe location_demo.py --seed aus.")
        user_world = None
    
    # Merged Location
    print("  Creating Merged Location...")
    merged = generator.get_merged_location(
        "Barcelona", "Spanien", LayerType.ROMANCE, user_world
    )
    print(f"  ✓ Merged: {len(merged.places)} Orte (nach Ausschlüssen)")
    
    return generator, user_world


def demo_story_generation(
    repo: LocationRepository, 
    user_world,
    use_real_llm: bool = False,
    chapter_number: int = None,
):
    """Demo: Story Generation"""
    
    print_section("Story Generation")
    
    # Story Context
    context = create_example_story_context()
    print(f"  Story: {context.title}")
    print(f"  Genre: {context.genre}")
    print(f"  Protagonist: {context.protagonist_name}")
    print(f"  Love Interest: {context.love_interest_name}")
    
    # Chapter Specs
    all_specs = create_example_chapter_specs()
    
    if chapter_number:
        specs = [s for s in all_specs if s.chapter_number == chapter_number]
        if not specs:
            print(f"  ⚠ Kapitel {chapter_number} nicht gefunden")
            return
    else:
        specs = all_specs
    
    print(f"\n  Generiere {len(specs)} Kapitel...")
    
    # Generator
    generator = IntegratedStoryGenerator(
        repository=repo,
        use_real_llm=use_real_llm,
    )
    
    if use_real_llm:
        print("  Mode: ECHTE LLM-Generierung (Anthropic API)")
    else:
        print("  Mode: Mock-Generierung")
    
    # Progress callback
    def on_progress(current, total):
        print(f"  [{current}/{total}] Generiere Kapitel {specs[current-1].chapter_number}...")
    
    # Generieren
    chapters = generator.generate_story(
        chapter_specs=specs,
        story_context=context,
        user_world=user_world,
        location_country="Spanien",
        progress_callback=on_progress,
    )
    
    # Ergebnis
    print_section("Generierte Kapitel")
    
    total_words = 0
    for chapter in chapters:
        print(f"\n  Kapitel {chapter.chapter_number}: {chapter.title}")
        print(f"  Wörter: {chapter.word_count}")
        print(f"  Location: {chapter.story_location}")
        print(f"  Model: {chapter.model_used}")
        
        # Vorschau
        preview = chapter.content[:300].replace("\n", " ")
        print(f"\n  Vorschau: {preview}...")
        
        total_words += chapter.word_count
    
    print(f"\n  ─────────────────────────────")
    print(f"  Gesamt: {len(chapters)} Kapitel, {total_words} Wörter")
    
    # Export
    if len(chapters) > 0:
        output_path = "/tmp/generated_story.md"
        generator.export_markdown(chapters, context, output_path)
        print(f"\n  ✓ Exportiert: {output_path}")
    
    return chapters


def demo_full_pipeline(use_real_llm: bool = False, chapter: int = None):
    """Vollständige Demo-Pipeline"""
    
    print_header("🚀 INTEGRATED STORY GENERATION DEMO")
    
    # Config
    config = DatabaseConfig()
    print(f"  DB: {config.host}:{config.port}/{config.database}" if not config.connection_string else "  DB: via DATABASE_URL")
    
    if use_real_llm:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        print(f"  API Key: {'✓ gesetzt' if api_key else '✗ nicht gesetzt'}")
    
    # Repository
    try:
        repo = LocationRepository(config)
        repo.connect()
        print("  ✓ Database connected")
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return
    
    # Stats
    stats = repo.get_stats()
    print(f"  Locations: {stats['base_locations']}, Layers: {stats['location_layers']}, Users: {stats['user_worlds']}")
    
    if stats['base_locations'] == 0:
        print("\n  ⚠ Keine Locations in DB. Führe zuerst aus:")
        print("    python location_demo.py --init")
        print("    python location_demo.py --seed")
        repo.close()
        return
    
    # Location Integration
    generator, user_world = demo_location_integration(repo)
    
    # Story Generation
    chapters = demo_story_generation(repo, user_world, use_real_llm, chapter)
    
    # Cleanup
    repo.close()
    
    print_header("✅ DEMO COMPLETE")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    use_real = "--real" in sys.argv
    
    chapter = None
    if "--chapter" in sys.argv:
        idx = sys.argv.index("--chapter")
        if idx + 1 < len(sys.argv):
            chapter = int(sys.argv[idx + 1])
    
    demo_full_pipeline(use_real_llm=use_real, chapter=chapter)
