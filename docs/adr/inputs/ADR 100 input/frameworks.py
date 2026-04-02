"""
outlinefw/src/outlinefw/frameworks.py

Complete, versioned story framework definitions for iil-outlinefw v0.1.0.

Fixes:
  - HOCH H-4: Each framework has an explicit version string.
    Bumping a beat definition = bumping the framework version.
  - ADR-100: All 5 frameworks from the v0.1.0 table fully defined
    (dan_harmon was missing from the Package-Struktur section).
  - KRITISCH K-2: All frameworks validated on import via FrameworkDefinition.

Registry is immutable (frozen Pydantic models).
"""

from __future__ import annotations

from schemas import ActPhase, BeatDefinition, FrameworkDefinition, TensionLevel

# ---------------------------------------------------------------------------
# 1. Three-Act Structure  (7 beats)
# ---------------------------------------------------------------------------

THREE_ACT = FrameworkDefinition(
    key="three_act",
    name="Drei-Akt-Struktur",
    description=(
        "Die klassische Drei-Akt-Struktur nach Aristoteles. "
        "Akt 1: Exposition und Aufbruch. Akt 2: Konfrontation und Komplikation. "
        "Akt 3: Klimax und Auflösung."
    ),
    version="1.0.0",
    beats=[
        BeatDefinition(
            name="exposition",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Vorstellung der Welt, der Figuren und des Status Quo.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="inciting_incident",
            position=0.12,
            act=ActPhase.ACT_1,
            description="Das auslösende Ereignis, das die Geschichte in Gang setzt.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="first_turning_point",
            position=0.25,
            act=ActPhase.ACT_1,
            description="Der Protagonist trifft eine unwiderrufliche Entscheidung und tritt in Akt 2 ein.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="midpoint",
            position=0.50,
            act=ActPhase.ACT_2A,
            description="Falsche Niederlage oder falscher Sieg — dreht die innere Reise des Protagonisten.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="second_turning_point",
            position=0.75,
            act=ActPhase.ACT_2B,
            description="Tiefpunkt: Alles scheint verloren. Der Protagonist muss seine Ressourcen neu ordnen.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="climax",
            position=0.88,
            act=ActPhase.ACT_3,
            description="Der finale Konflikt. Der Protagonist stellt sich der ultimativen Herausforderung.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="resolution",
            position=1.0,
            act=ActPhase.ACT_3,
            description="Die neue Normalität. Konsequenzen der Klimax und emotionale Auflösung.",
            tension=TensionLevel.LOW,
        ),
    ],
)

# ---------------------------------------------------------------------------
# 2. Save the Cat (Blake Snyder, 15 beats)
# ---------------------------------------------------------------------------

SAVE_THE_CAT = FrameworkDefinition(
    key="save_the_cat",
    name="Save the Cat (Blake Snyder)",
    description=(
        "Blake Snyders 15-Beat-Sheet für kommerziell erfolgreiche Drehbücher. "
        "Präzise Positionsangaben orientieren sich an einem 110-seitigen Drehbuch."
    ),
    version="1.0.0",
    beats=[
        BeatDefinition(
            name="opening_image",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Ein Schnappschuss der Welt vor der Geschichte. Kontrapunkt zur Schlussszene.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="theme_stated",
            position=0.05,
            act=ActPhase.ACT_1,
            description="Jemand (nicht der Protagonist) formuliert das Thema der Geschichte — er versteht es noch nicht.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="setup",
            position=0.09,
            act=ActPhase.ACT_1,
            description="Vorstellung von Welt, Figuren und Status Quo. Etablierung der Schwächen.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="catalyst",
            position=0.12,
            act=ActPhase.ACT_1,
            description="Das auslösende Ereignis. Schlägt in die stabile Welt ein und verlangt Reaktion.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="debate",
            position=0.18,
            act=ActPhase.ACT_1,
            description="Der Protagonist zögert. Letzte Chance, umzukehren. Interne Frage der Geschichte.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="break_into_two",
            position=0.25,
            act=ActPhase.ACT_2A,
            description="Der Protagonist wählt aktiv — tritt in die umgekehrte Welt von Akt 2 ein.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="b_story",
            position=0.30,
            act=ActPhase.ACT_2A,
            description="Einführung der B-Story (oft Love Interest). Trägt das Thema.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="fun_and_games",
            position=0.38,
            act=ActPhase.ACT_2A,
            description="Die Prämise des Films wird eingelöst. Der Protagonist erkundet die neue Welt.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="midpoint",
            position=0.50,
            act=ActPhase.ACT_2A,
            description="Falscher Sieg oder falsche Niederlage. Einsätze erhöhen sich. Der Protagonist muss wachsen.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="bad_guys_close_in",
            position=0.60,
            act=ActPhase.ACT_2B,
            description="Antagonistische Kräfte schließen sich zusammen. Innere Schwächen kehren zurück.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="all_is_lost",
            position=0.75,
            act=ActPhase.ACT_2B,
            description="Das Gegenteil von Akt-2-Einstieg. Whiff of death — jemand oder etwas stirbt.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="dark_night_of_the_soul",
            position=0.80,
            act=ActPhase.ACT_2B,
            description="Der tiefste Moment. Der Protagonist hadert. Noch dunklerer Moment vor dem Licht.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="break_into_three",
            position=0.85,
            act=ActPhase.ACT_3,
            description="A- und B-Story konvergieren. Der Protagonist findet die Lösung — dank erlerntem Thema.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="finale",
            position=0.92,
            act=ActPhase.ACT_3,
            description="Der Protagonist stürmt die Burg. Beweis, dass er sich verändert hat. Alte Welt stirbt.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="final_image",
            position=1.0,
            act=ActPhase.ACT_3,
            description="Spiegel zum Opening Image. Zeigt Transformation durch Kontrast.",
            tension=TensionLevel.LOW,
        ),
    ],
)

# ---------------------------------------------------------------------------
# 3. Hero's Journey (Campbell, 12 beats)
# ---------------------------------------------------------------------------

HEROS_JOURNEY = FrameworkDefinition(
    key="heros_journey",
    name="Heldenreise (Joseph Campbell)",
    description=(
        "Joseph Campbells Monomythos, popularisiert durch Christopher Vogler. "
        "12 Stationen der transformativen Reise des Helden."
    ),
    version="1.0.0",
    beats=[
        BeatDefinition(
            name="ordinary_world",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Die gewöhnliche Welt des Helden. Status Quo vor der Reise.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="call_to_adventure",
            position=0.09,
            act=ActPhase.ACT_1,
            description="Der Ruf zur Reise. Eine Herausforderung oder ein Problem erscheint.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="refusal_of_call",
            position=0.16,
            act=ActPhase.ACT_1,
            description="Der Held verweigert zunächst. Angst vor Veränderung.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="meeting_the_mentor",
            position=0.22,
            act=ActPhase.ACT_1,
            description="Der Mentor erscheint. Gibt dem Helden Rat, Ausrüstung oder Vertrauen.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="crossing_the_threshold",
            position=0.28,
            act=ActPhase.ACT_2A,
            description="Der Held betritt die besondere Welt. Kein Zurück.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="tests_allies_enemies",
            position=0.38,
            act=ActPhase.ACT_2A,
            description="Der Held wird getestet, findet Verbündete und erkennt Feinde.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="approach_to_inmost_cave",
            position=0.48,
            act=ActPhase.ACT_2A,
            description="Annäherung an das Heiligtum. Vorbereitung auf die Prüfung.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="ordeal",
            position=0.55,
            act=ActPhase.ACT_2B,
            description="Die zentrale Krise. Der Held konfrontiert Tod oder Schlimmstes.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="reward",
            position=0.65,
            act=ActPhase.ACT_2B,
            description="Der Held überlebt und gewinnt den Preis: Wissen, Elixier oder Schwert.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="road_back",
            position=0.75,
            act=ActPhase.ACT_3,
            description="Aufbruch zur Heimreise. Oft ein Wendepunkt mit Verfolgung.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="resurrection",
            position=0.88,
            act=ActPhase.ACT_3,
            description="Zweite Krise. Der Held muss erneut sterben (im übertragenen Sinne) und wiedergeboren werden.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="return_with_elixir",
            position=1.0,
            act=ActPhase.ACT_3,
            description="Heimkehr mit dem Elixier. Der Held bereichert die gewöhnliche Welt.",
            tension=TensionLevel.LOW,
        ),
    ],
)

# ---------------------------------------------------------------------------
# 4. Five-Act Structure (Shakespeare, 5 beats)
# ---------------------------------------------------------------------------

FIVE_ACT = FrameworkDefinition(
    key="five_act",
    name="Fünf-Akt-Struktur (Shakespeare)",
    description=(
        "Gustav Freytags Pyramide, basierend auf Shakespeares Tragödienstruktur. "
        "5 Akte: Exposition, Steigerung, Klimax, Wendung, Katastrophe."
    ),
    version="1.0.0",
    beats=[
        BeatDefinition(
            name="exposition",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Einführung der Figuren, der Welt und des dramatischen Konflikts.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="rising_action",
            position=0.22,
            act=ActPhase.ACT_2A,
            description="Zunehmende Komplikationen. Der Held bewegt sich auf den Klimax zu.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="climax",
            position=0.50,
            act=ActPhase.ACT_2B,
            description="Wendepunkt. Der entscheidende Moment, der das Schicksal des Helden besiegelt.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="falling_action",
            position=0.72,
            act=ActPhase.ACT_3,
            description="Die Konsequenzen des Klimax entfalten sich. Auflösung der Nebenhandlungen.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="denouement",
            position=1.0,
            act=ActPhase.ACT_3,
            description="Katastrophe (Tragödie) oder Apotheose (Komödie). Finale Ordnung der Welt.",
            tension=TensionLevel.LOW,
        ),
    ],
)

# ---------------------------------------------------------------------------
# 5. Dan Harmon Story Circle (8 beats)
# Fixes: dan_harmon missing from Package-Struktur section in ADR
# ---------------------------------------------------------------------------

DAN_HARMON = FrameworkDefinition(
    key="dan_harmon",
    name="Dan Harmon Story Circle",
    description=(
        "Dan Harmons Vereinfachung der Heldenreise in 8 Stationen, "
        "die sich wie ein Kreis schließen. Ideal für Episodenformat und TV."
    ),
    version="1.0.0",
    beats=[
        BeatDefinition(
            name="you",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Eine Figur in ihrer Komfortzone. Etablierung des Status Quo.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="need",
            position=0.14,
            act=ActPhase.ACT_1,
            description="Die Figur will etwas oder braucht etwas. Bewusste oder unbewusste Sehnsucht.",
            tension=TensionLevel.LOW,
        ),
        BeatDefinition(
            name="go",
            position=0.25,
            act=ActPhase.ACT_2A,
            description="Die Figur verlässt die Komfortzone, um das Bedürfnis zu erfüllen.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="search",
            position=0.38,
            act=ActPhase.ACT_2A,
            description="Suche nach dem Ziel in der unbekannten Welt. Anpassung und Kampf.",
            tension=TensionLevel.MEDIUM,
        ),
        BeatDefinition(
            name="find",
            position=0.50,
            act=ActPhase.ACT_2B,
            description="Die Figur findet, was sie gesucht hat — aber zu einem Preis.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="take",
            position=0.63,
            act=ActPhase.ACT_2B,
            description="Das Gefundene wird genommen. Konsequenzen werden sichtbar.",
            tension=TensionLevel.PEAK,
        ),
        BeatDefinition(
            name="return",
            position=0.75,
            act=ActPhase.ACT_3,
            description="Rückkehr in die vertraute Welt — aber verändert.",
            tension=TensionLevel.HIGH,
        ),
        BeatDefinition(
            name="change",
            position=1.0,
            act=ActPhase.ACT_3,
            description="Die Figur hat sich verändert. Neuer Status Quo durch die Erfahrung.",
            tension=TensionLevel.LOW,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Framework Registry
# Fixes HOCH H-4: immutable dict, version accessible per framework
# ---------------------------------------------------------------------------

FRAMEWORKS: dict[str, FrameworkDefinition] = {
    "three_act": THREE_ACT,
    "save_the_cat": SAVE_THE_CAT,
    "heros_journey": HEROS_JOURNEY,
    "five_act": FIVE_ACT,
    "dan_harmon": DAN_HARMON,
}


def get_framework(key: str) -> FrameworkDefinition:
    """
    Returns the FrameworkDefinition for the given key.
    Raises KeyError with a helpful message listing available frameworks.
    """
    if key not in FRAMEWORKS:
        available = ", ".join(sorted(FRAMEWORKS))
        raise KeyError(
            f"Unknown framework key: {key!r}. Available: {available}"
        )
    return FRAMEWORKS[key]


def list_frameworks() -> list[dict[str, str]]:
    """
    Returns a list of dicts suitable for Django form choices or API responses.
    Each dict: {key, name, description, version, beat_count}
    """
    return [
        {
            "key": fw.key,
            "name": fw.name,
            "description": fw.description,
            "version": fw.version,
            "beat_count": str(len(fw.beats)),
        }
        for fw in FRAMEWORKS.values()
    ]
