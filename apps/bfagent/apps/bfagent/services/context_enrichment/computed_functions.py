"""
Computed Functions for Context Enrichment

Registry of Python functions that can be called by ComputedResolver.
Functions must accept keyword arguments and return any JSON-serializable value.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_story_position(chapter_number: int, total_chapters: int = 15) -> str:
    """
    Calculate story position as percentage.

    Args:
        chapter_number: Current chapter number
        total_chapters: Total number of chapters in story

    Returns:
        String like "3/15 (20%)"
    """
    if total_chapters == 0:
        return "0/0 (0%)"

    percentage = (chapter_number / total_chapters) * 100
    return f"{chapter_number}/{total_chapters} ({percentage:.0f}%)"


def get_beat_info(beat_type: str, chapter_number: int) -> Optional[Dict[str, Any]]:
    """
    Get beat sheet information for a specific chapter.

    Args:
        beat_type: Type of beat sheet (e.g., 'save_the_cat')
        chapter_number: Chapter number

    Returns:
        Dict with beat information or None if not found
    """
    beat_sheets = {
        'save_the_cat': _get_save_the_cat_beats(),
        # Add more beat sheet types here
    }

    beats = beat_sheets.get(beat_type, [])

    for beat in beats:
        if beat.get('chapter') == chapter_number:
            return beat

    return None


def _get_save_the_cat_beats() -> list:
    """
    Get Save the Cat beat sheet mapping.

    Returns:
        List of beat dictionaries
    """
    return [
        {
            "chapter": 1,
            "beat": "Set-Up",
            "position": "0-10%",
            "description": "Zeige die Welt des Helden und was fehlt",
            "focus": "Etabliere alle wichtigen Charaktere und die Welt",
            "emotional_arc": "Routine, wachsende Unzufriedenheit"
        },
        {
            "chapter": 2,
            "beat": "Catalyst",
            "position": "10%",
            "description": "Lebensveränderndes Ereignis",
            "focus": "Ein Ereignis, das alles verändert - kein Zurück mehr",
            "emotional_arc": "Schock, Aufruhr"
        },
        {
            "chapter": 3,
            "beat": "Debate",
            "position": "10-20%",
            "description": "Soll der Held handeln? Zweifel und Ängste",
            "focus": "Der Held zögert, überlegt Optionen, zeigt Angst",
            "emotional_arc": "Unsicherheit, innerer Konflikt"
        },
        {
            "chapter": 4,
            "beat": "Break into Two",
            "position": "20%",
            "description": "Der Held entscheidet sich für Handlung",
            "focus": "Entscheidung getroffen, Eintritt in Akt 2",
            "emotional_arc": "Entschlossenheit, Aufregung"
        },
        {
            "chapter": 5,
            "beat": "B Story",
            "position": "22%",
            "description": "Neue Beziehung, die das Thema erforscht",
            "focus": "Einführung des Mentors oder Liebesinteresses",
            "emotional_arc": "Neue Verbindungen, Hoffnung"
        },
        {
            "chapter": 6,
            "beat": "Fun and Games",
            "position": "20-50%",
            "description": "Das Versprechen der Prämisse",
            "focus": "Der Held erforscht die neue Welt",
            "emotional_arc": "Entdeckung, Aufregung, erste Erfolge"
        },
        {
            "chapter": 7,
            "beat": "Midpoint",
            "position": "50%",
            "description": "Falscher Sieg oder falsche Niederlage",
            "focus": "Scheint großartig oder alles verloren",
            "emotional_arc": "Höhepunkt der Hoffnung oder Verzweiflung"
        },
        {
            "chapter": 8,
            "beat": "Midpoint",
            "position": "50%",
            "description": "Falscher Sieg oder falsche Niederlage",
            "focus": "Scheint großartig oder alles verloren",
            "emotional_arc": "Höhepunkt der Hoffnung oder Verzweiflung"
        },
        {
            "chapter": 9,
            "beat": "Bad Guys Close In",
            "position": "50-75%",
            "description": "Antagonisten gewinnen Oberhand",
            "focus": "Probleme häufen sich, Team zerfällt",
            "emotional_arc": "Zunehmende Spannung, Druck"
        },
        {
            "chapter": 10,
            "beat": "Bad Guys Close In",
            "position": "50-75%",
            "description": "Antagonisten gewinnen Oberhand",
            "focus": "Probleme häufen sich, Team zerfällt",
            "emotional_arc": "Zunehmende Spannung, Druck"
        },
        {
            "chapter": 11,
            "beat": "All Is Lost",
            "position": "75%",
            "description": "Tiefster Punkt",
            "focus": "Der schlimmste Moment, symbolischer Tod",
            "emotional_arc": "Verzweiflung, totale Niederlage"
        },
        {
            "chapter": 12,
            "beat": "Dark Night of the Soul",
            "position": "75-80%",
            "description": "Der Held ist am Boden",
            "focus": "Moment der Dunkelheit vor Erleuchtung",
            "emotional_arc": "Hoffnungslosigkeit, letzte Zweifel"
        },
        {
            "chapter": 13,
            "beat": "Break into Three",
            "position": "80%",
            "description": "Lösung wird gefunden",
            "focus": "Der Held findet die Antwort",
            "emotional_arc": "Erkenntnis, neue Entschlossenheit"
        },
        {
            "chapter": 14,
            "beat": "Finale",
            "position": "80-99%",
            "description": "Der Held wendet Gelerntes an",
            "focus": "Finale Konfrontation, Held beweist Wachstum",
            "emotional_arc": "Triumph, Katharsis"
        },
        {
            "chapter": 15,
            "beat": "Final Image",
            "position": "100%",
            "description": "Spiegelbild des Opening Image",
            "focus": "Zeige Transformation, Gegenteil von Anfang",
            "emotional_arc": "Neue Normalität, Erfüllung"
        },
    ]


# Registry for custom functions (advanced use)
_custom_functions = {}


def register_function(name: str, func: callable) -> None:
    """
    Register a custom computed function.

    Args:
        name: Function name (used in ContextSource.function_name)
        func: Function to register (must accept **kwargs)

    Example:
        def my_function(param1, param2):
            return {"result": param1 + param2}

        register_function("my_function", my_function)
    """
    _custom_functions[name] = func
    logger.info(f"Registered computed function: {name}")


def get_custom_function(name: str) -> Optional[callable]:
    """Get custom function by name"""
    return _custom_functions.get(name)
