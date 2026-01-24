"""
Story Structure Frameworks for Book Generation

Provides templates and guidance based on proven story structures:
- Hero's Journey (Joseph Campbell)
- Save the Cat Beat Sheet (Blake Snyder)
- Three-Act Structure
- Dan Harmon's Story Circle
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class StoryBeat:
    """A single beat/point in a story structure"""
    name: str
    description: str
    typical_position: float  # 0.0 to 1.0 in story
    chapter_guidance: str
    emotional_arc: str


class StoryFramework:
    """Base class for story frameworks"""
    
    name: str = ""
    description: str = ""
    beats: List[StoryBeat] = []
    
    def get_beat_for_position(self, position: float) -> StoryBeat:
        """Get the appropriate beat for a position in the story"""
        for beat in self.beats:
            if abs(beat.typical_position - position) < 0.1:
                return beat
        return self.beats[0]  # Default to first beat
    
    def generate_outline(self, title: str, genre: str, premise: str, num_chapters: int = 10) -> str:
        """Generate a structured outline based on this framework"""
        outline_lines = []
        
        for i in range(1, num_chapters + 1):
            position = i / num_chapters
            beat = self.get_beat_for_position(position)
            
            outline_lines.append(f"Chapter {i}: {beat.name}")
            outline_lines.append(f"  Position: {position:.0%} through story")
            outline_lines.append(f"  Focus: {beat.chapter_guidance}")
            outline_lines.append(f"  Emotional Arc: {beat.emotional_arc}")
            outline_lines.append("")
        
        return "\n".join(outline_lines)


class HerosJourney(StoryFramework):
    """Hero's Journey (Joseph Campbell's Monomyth)"""
    
    name = "Hero's Journey"
    description = "The classic monomyth structure with 12 stages"
    
    beats = [
        StoryBeat(
            name="Gewöhnliche Welt",
            description="Der Held in seiner normalen Welt vor dem Abenteuer",
            typical_position=0.0,
            chapter_guidance="Stelle den Protagonisten vor, zeige sein normales Leben und was ihm fehlt",
            emotional_arc="Routine, leichte Unzufriedenheit"
        ),
        StoryBeat(
            name="Ruf zum Abenteuer",
            description="Etwas stört die gewöhnliche Welt",
            typical_position=0.08,
            chapter_guidance="Präsentiere das Problem oder die Chance, die alles verändert",
            emotional_arc="Neugier, erste Aufregung"
        ),
        StoryBeat(
            name="Verweigerung des Rufs",
            description="Der Held zögert oder lehnt ab",
            typical_position=0.12,
            chapter_guidance="Zeige Zweifel, Ängste und Gründe, warum der Held zögert",
            emotional_arc="Angst, Unsicherheit"
        ),
        StoryBeat(
            name="Treffen mit dem Mentor",
            description="Jemand gibt Rat, Training oder magische Hilfe",
            typical_position=0.17,
            chapter_guidance="Führe einen weisen Mentor ein, der hilft und ermutigt",
            emotional_arc="Hoffnung, Entschlossenheit"
        ),
        StoryBeat(
            name="Überschreiten der Schwelle",
            description="Der Held begeht sich zum Abenteuer",
            typical_position=0.25,
            chapter_guidance="Der Held verlässt die bekannte Welt, kein Zurück mehr",
            emotional_arc="Aufregung, Angst, Entschlossenheit"
        ),
        StoryBeat(
            name="Bewährungsproben, Verbündete, Feinde",
            description="Tests, Freunde finden, Feinde kennenlernen",
            typical_position=0.38,
            chapter_guidance="Der Held lernt die Regeln der neuen Welt, trifft Freunde und Feinde",
            emotional_arc="Wachstum, Kameradschaft, erste Konflikte"
        ),
        StoryBeat(
            name="Vordringen zur tiefsten Höhle",
            description="Annäherung an den gefährlichsten Ort",
            typical_position=0.50,
            chapter_guidance="Der Held nähert sich dem Zentrum der Gefahr, Vorbereitung auf große Prüfung",
            emotional_arc="Spannung, Furcht, Entschlossenheit"
        ),
        StoryBeat(
            name="Entscheidende Prüfung",
            description="Die größte Krise, Konfrontation mit dem Tod",
            typical_position=0.60,
            chapter_guidance="Der Held steht vor dem größten Test, scheinbares Scheitern oder 'Tod'",
            emotional_arc="Verzweiflung, Kampf, Wandlung"
        ),
        StoryBeat(
            name="Belohnung",
            description="Der Held überlebt und gewinnt die Belohnung",
            typical_position=0.67,
            chapter_guidance="Nach der Prüfung gewinnt der Held etwas Wertvolles (Schatz, Wissen, Versöhnung)",
            emotional_arc="Triumph, Erleichterung, kurze Freude"
        ),
        StoryBeat(
            name="Rückweg",
            description="Der Held muss mit der Belohnung zurückkehren",
            typical_position=0.75,
            chapter_guidance="Die Reise nach Hause beginnt, aber neue Gefahren lauern",
            emotional_arc="Dringlichkeit, neue Herausforderungen"
        ),
        StoryBeat(
            name="Auferstehung",
            description="Finale Prüfung, bei der alles auf dem Spiel steht",
            typical_position=0.88,
            chapter_guidance="Letzte große Konfrontation, der Held muss alles Gelernte anwenden",
            emotional_arc="Höchste Spannung, ultimativer Einsatz"
        ),
        StoryBeat(
            name="Rückkehr mit dem Elixier",
            description="Der Held kehrt verwandelt zurück",
            typical_position=1.0,
            chapter_guidance="Der Held bringt Weisheit/Schatz nach Hause, beide Welten sind besser",
            emotional_arc="Erfüllung, Weisheit, neuer Anfang"
        ),
    ]


class SaveTheCat(StoryFramework):
    """Save the Cat Beat Sheet (Blake Snyder)"""
    
    name = "Save the Cat"
    description = "15-Beat structure optimized for page-turners"
    
    beats = [
        StoryBeat(
            name="Opening Image",
            description="Snapshot des Protagonisten vor der Transformation",
            typical_position=0.0,
            chapter_guidance="Zeige den Protagonisten in seiner aktuellen, unvollkommenen Welt",
            emotional_arc="Status Quo, Routine"
        ),
        StoryBeat(
            name="Theme Stated",
            description="Jemand stellt die Frage oder das Thema der Geschichte",
            typical_position=0.05,
            chapter_guidance="Ein Nebencharakter deutet das Thema/die Lektion an",
            emotional_arc="Leichtes Unbehagen"
        ),
        StoryBeat(
            name="Set-Up",
            description="Zeige die Welt des Helden und was fehlt",
            typical_position=0.08,
            chapter_guidance="Etabliere alle wichtigen Charaktere und die Welt",
            emotional_arc="Routine, wachsende Unzufriedenheit"
        ),
        StoryBeat(
            name="Catalyst",
            description="Lebensveränderndes Ereignis (gut oder schlecht)",
            typical_position=0.10,
            chapter_guidance="Ein Ereignis, das alles verändert - der Held kann nicht mehr zurück",
            emotional_arc="Schock, Aufruhr"
        ),
        StoryBeat(
            name="Debate",
            description="Soll der Held handeln? Zweifel und Ängste",
            typical_position=0.17,
            chapter_guidance="Der Held zögert, überlegt Optionen, zeigt Angst vor Veränderung",
            emotional_arc="Unsicherheit, innerer Konflikt"
        ),
        StoryBeat(
            name="Break into Two",
            description="Der Held entscheidet sich für Handlung",
            typical_position=0.25,
            chapter_guidance="Entscheidung ist getroffen, Eintritt in die 'verkehrte Welt' (Akt 2)",
            emotional_arc="Entschlossenheit, Aufregung"
        ),
        StoryBeat(
            name="B Story",
            description="Neue Beziehung, die das Thema erforscht",
            typical_position=0.30,
            chapter_guidance="Einführung des 'Liebes'-Interesses oder Mentors, der Thema verkörpert",
            emotional_arc="Neue Verbindungen, Hoffnung"
        ),
        StoryBeat(
            name="Fun and Games",
            description="Das Versprechen der Prämisse",
            typical_position=0.40,
            chapter_guidance="Der Held erforscht die neue Welt, das macht die Geschichte 'spaßig'",
            emotional_arc="Entdeckung, Aufregung, erste Erfolge"
        ),
        StoryBeat(
            name="Midpoint",
            description="Falscher Sieg oder falsche Niederlage",
            typical_position=0.50,
            chapter_guidance="Entweder scheint alles großartig (falscher Sieg) oder alles verloren (falsche Niederlage)",
            emotional_arc="Höhepunkt der Hoffnung oder Verzweiflung"
        ),
        StoryBeat(
            name="Bad Guys Close In",
            description="Äußere oder innere Antagonisten gewinnen Oberhand",
            typical_position=0.60,
            chapter_guidance="Die Probleme häufen sich, Team zerfällt, äußere/innere Feinde stärker",
            emotional_arc="Zunehmende Spannung, Druck"
        ),
        StoryBeat(
            name="All Is Lost",
            description="Tiefster Punkt, scheinbar ist alles vorbei",
            typical_position=0.75,
            chapter_guidance="Der schlimmste Moment, oft stirbt jemand oder etwas (symbolisch)",
            emotional_arc="Verzweiflung, totale Niederlage"
        ),
        StoryBeat(
            name="Dark Night of the Soul",
            description="Der Held ist am Boden, scheint aufzugeben",
            typical_position=0.80,
            chapter_guidance="Moment der Dunkelheit, bevor die Erleuchtung kommt",
            emotional_arc="Hoffnungslosigkeit, letzte Zweifel"
        ),
        StoryBeat(
            name="Break into Three",
            description="Lösung wird gefunden (durch A + B Story)",
            typical_position=0.83,
            chapter_guidance="Der Held findet die Antwort, kombiniert Gelerntes aus A und B Story",
            emotional_arc="Erkenntnis, neue Entschlossenheit"
        ),
        StoryBeat(
            name="Finale",
            description="Der Held wendet alles Gelernte an",
            typical_position=0.92,
            chapter_guidance="Finale Konfrontation, Held nutzt neue Weisheit und Fähigkeiten",
            emotional_arc="Ultimative Konfrontation, Triumph"
        ),
        StoryBeat(
            name="Final Image",
            description="Gegenteil zum Opening Image",
            typical_position=1.0,
            chapter_guidance="Zeige die Transformation - wie anders ist der Held jetzt?",
            emotional_arc="Erfüllung, Wandlung, neuer Status Quo"
        ),
    ]


class ThreeActStructure(StoryFramework):
    """Classic Three-Act Structure"""
    
    name = "Drei-Akt-Struktur"
    description = "Klassische dramatische Struktur (Setup, Confrontation, Resolution)"
    
    beats = [
        StoryBeat(
            name="Akt 1: Setup - Ausgangssituation",
            description="Einführung der Welt und Charaktere",
            typical_position=0.05,
            chapter_guidance="Stelle die Welt, den Protagonisten und seinen Status Quo vor",
            emotional_arc="Normalität, leichte Spannung"
        ),
        StoryBeat(
            name="Akt 1: Inciting Incident",
            description="Auslösendes Ereignis",
            typical_position=0.15,
            chapter_guidance="Das Ereignis, das die Geschichte in Gang setzt",
            emotional_arc="Störung, Neugier"
        ),
        StoryBeat(
            name="Akt 1: Plot Point 1",
            description="Eintritt in neue Welt/Situation",
            typical_position=0.25,
            chapter_guidance="Der Protagonist trifft eine Entscheidung und betritt die neue Welt",
            emotional_arc="Commitment, Point of No Return"
        ),
        StoryBeat(
            name="Akt 2: Rising Action",
            description="Steigende Handlung und Komplikationen",
            typical_position=0.38,
            chapter_guidance="Hindernisse, Konflikte eskalieren, Protagonist lernt und kämpft",
            emotional_arc="Wachsende Spannung, Herausforderungen"
        ),
        StoryBeat(
            name="Akt 2: Midpoint",
            description="Mittelpunkt - große Veränderung",
            typical_position=0.50,
            chapter_guidance="Große Offenbarung oder Wendung, alles ändert sich",
            emotional_arc="Schock, Neuausrichtung"
        ),
        StoryBeat(
            name="Akt 2: Plot Point 2",
            description="Tiefster Punkt vor Akt 3",
            typical_position=0.75,
            chapter_guidance="Alles scheint verloren, Protagonist am Boden",
            emotional_arc="Verzweiflung, scheinbare Niederlage"
        ),
        StoryBeat(
            name="Akt 3: Pre-Climax",
            description="Vorbereitung auf finale Konfrontation",
            typical_position=0.83,
            chapter_guidance="Protagonist sammelt sich, findet neue Kraft/Lösung",
            emotional_arc="Erneute Entschlossenheit"
        ),
        StoryBeat(
            name="Akt 3: Climax",
            description="Höhepunkt und Konfrontation",
            typical_position=0.92,
            chapter_guidance="Finale Schlacht/Konfrontation, alles steht auf dem Spiel",
            emotional_arc="Höchste Spannung, ultimativer Kampf"
        ),
        StoryBeat(
            name="Akt 3: Resolution",
            description="Auflösung und neuer Zustand",
            typical_position=1.0,
            chapter_guidance="Konsequenzen werden gezeigt, neue Normalität etabliert",
            emotional_arc="Abschluss, Reflexion, Zufriedenheit"
        ),
    ]


# Registry of available frameworks
STORY_FRAMEWORKS = {
    "heros_journey": HerosJourney(),
    "save_the_cat": SaveTheCat(),
    "three_act": ThreeActStructure(),
}


def get_framework(framework_name: str) -> StoryFramework:
    """Get a story framework by name"""
    return STORY_FRAMEWORKS.get(framework_name, ThreeActStructure())


def list_frameworks() -> List[Dict[str, str]]:
    """List all available frameworks"""
    return [
        {
            "id": key,
            "name": framework.name,
            "description": framework.description,
            "beats": len(framework.beats)
        }
        for key, framework in STORY_FRAMEWORKS.items()
    ]


def generate_outline_from_framework(
    framework_name: str,
    title: str,
    genre: str,
    premise: str,
    num_chapters: int = 10
) -> str:
    """Generate a structured outline based on a story framework"""
    framework = get_framework(framework_name)
    return framework.generate_outline(title, genre, premise, num_chapters)
