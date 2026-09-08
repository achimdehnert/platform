"""Drill fuer die Ausweitung des Gates ``built-but-never-called`` (Retro 61c35d §5a).

Der namensgebende Fall: ``tools/melder_ergebnis.py`` bekam am 2026-09-08 ein Paar
``schreibe()``/``lies()``. Vier Produzenten riefen ``schreibe()``, ``lies()`` rief
niemand ausser zwei Tests.

Zwei Fallen wurden beim Bau der Probe nacheinander sichtbar; beide stehen hier als
Test, damit sie nicht zurueckkehren:

1. **Namenskollision.** Ein Zaehler ohne Modulaufloesung sieht ``gate_hits.lies``
   und ``rotation.log.lies`` produktiv gerufen — und entlastet ``melder_ergebnis.lies``
   gleich mit. Die Probe haette ihren eigenen Anlass nicht gefunden.
2. **Weitergabe als Wert.** ``("Drill", pruefe_drill)`` in einer Pruefliste und
   ``set_defaults(func=cmd_age)`` an einem Unterbefehl sind Verdrahtungen ohne
   namentlichen Aufruf. Eine Probe, die nur Aufrufe zaehlt, meldet vier
   funktionierende Werkzeuge als tot.

Positivkontrolle und Gegenprobe in beiden Richtungen: ohne Verwendung rot, mit
Verwendung still.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "aufruferlose_funktionen.py"
_spec = importlib.util.spec_from_file_location("aufruferlose_funktionen", _QUELLE)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def _baue(tmp_path: Path, dateien: dict[str, str]) -> Path:
    wurzel = tmp_path / "tools"
    for rel, inhalt in dateien.items():
        p = wurzel / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(inhalt), encoding="utf-8")
    return wurzel


def _namen(befunde) -> set[str]:
    return {s.split("::")[-1] for s, _ in befunde}


# --- Positivkontrolle: der Realfall wird gefunden --------------------------


def test_should_lesefunktion_ohne_leser_melden(tmp_path) -> None:
    wurzel = _baue(
        tmp_path,
        {
            "melder_ergebnis.py": """
                def schreibe(ziel, daten): ...
                def lies(ziel): ...
                """,
            "backup_meter.py": """
                import melder_ergebnis
                def lauf():
                    melder_ergebnis.schreibe("a", {})
                """,
            "tests/test_backup_meter.py": """
                import melder_ergebnis
                def test_x():
                    melder_ergebnis.lies("a")
                """,
        },
    )
    assert _namen(probe.scanne(wurzel)) == {"lies"}


def test_should_gleichnamige_funktion_in_anderem_modul_nicht_entlasten(
    tmp_path,
) -> None:
    """Falle 1: ``lies`` gibt es mehrfach — die Probe darf sie nicht verwechseln."""
    wurzel = _baue(
        tmp_path,
        {
            "melder_ergebnis.py": "def lies(ziel): ...\n",
            "gate_hits.py": """
                def lies(pfad): ...
                def bericht():
                    return lies("x")
                """,
            "tests/test_melder.py": """
                import melder_ergebnis
                def test_x():
                    melder_ergebnis.lies("a")
                """,
        },
    )
    assert _namen(probe.scanne(wurzel)) == {"lies"}
    treffer = [s for s, _ in probe.scanne(wurzel)]
    assert any("melder_ergebnis" in s for s in treffer)
    assert not any("gate_hits" in s for s in treffer)


# --- Gegenprobe: Verwendung entwaffnet, in beiden Formen ------------------


def test_should_bei_echtem_aufruf_still_bleiben(tmp_path) -> None:
    wurzel = _baue(
        tmp_path,
        {
            "melder_ergebnis.py": "def lies(ziel): ...\n",
            "auswertung.py": """
                import melder_ergebnis
                def lauf():
                    return melder_ergebnis.lies("a")
                """,
            "tests/test_melder.py": """
                import melder_ergebnis
                def test_x():
                    melder_ergebnis.lies("a")
                """,
        },
    )
    assert probe.scanne(wurzel) == []


def test_should_weitergabe_als_wert_als_verwendung_zaehlen(tmp_path) -> None:
    """Falle 2: verdrahtet, aber nie namentlich gerufen."""
    wurzel = _baue(
        tmp_path,
        {
            "gate_verankerung_check.py": """
                def pruefe_drill(e): ...
                PRUEFUNGEN = [("Drill", pruefe_drill)]
                """,
            "iil_cohort.py": """
                def cmd_age(a): ...
                def baue(p):
                    p.set_defaults(func=cmd_age)
                """,
            "tests/test_beide.py": """
                import gate_verankerung_check, iil_cohort
                def test_x():
                    gate_verankerung_check.pruefe_drill({})
                    iil_cohort.cmd_age(None)
                """,
        },
    )
    assert probe.scanne(wurzel) == []


# --- Verengungen: was die Probe bewusst NICHT meldet ----------------------


def test_should_private_funktionen_und_main_auslassen(tmp_path) -> None:
    wurzel = _baue(
        tmp_path,
        {
            "werkzeug.py": """
                def _hilfe(): ...
                def main(): ...
                """,
            "tests/test_werkzeug.py": """
                import werkzeug
                def test_x():
                    werkzeug._hilfe()
                    werkzeug.main()
                """,
        },
    )
    assert probe.scanne(wurzel) == []


def test_should_dekorierte_funktionen_auslassen(tmp_path) -> None:
    """Vom Rahmenwerk gerufen — der Quelltext nennt sie zu Recht nirgends."""
    wurzel = _baue(
        tmp_path,
        {
            "dienst.py": """
                import app
                @app.route("/x")
                def zeige(): ...
                """,
            "tests/test_dienst.py": """
                import dienst
                def test_x():
                    dienst.zeige()
                """,
        },
    )
    assert probe.scanne(wurzel) == []


def test_should_funktion_ganz_ohne_test_nicht_melden(tmp_path) -> None:
    """Die Probe zielt auf gebaut-und-getestet-aber-unbenutzt, nicht auf ungetestet."""
    wurzel = _baue(tmp_path, {"werkzeug.py": "def unbenutzt(): ...\n"})
    assert probe.scanne(wurzel) == []


# --- Ausnahmeliste --------------------------------------------------------


def test_should_ausnahmen_nur_mit_grund_uebernehmen() -> None:
    ausnahmen = probe.lade_ausnahmen()
    assert ausnahmen, "Ausnahmeliste ist leer — dann fehlt der Realfall"
    assert "tools/melder_ergebnis.py::lies" in ausnahmen
    for schluessel, grund in ausnahmen.items():
        assert "#" in grund, f"Ausnahme ohne Anker: {schluessel}"
