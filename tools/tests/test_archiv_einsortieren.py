"""Entscheidungslogik des Jahrgangs-Einsortierers.

Geprüft wird die reine Logik — welche Nachricht wird verschoben, welche nicht und
mit welcher Begründung. Die Graph-Aufrufe bleiben außen vor; entscheidend ist, dass
**kein Posten stillschweigend** aus dem Plan fällt: Jeder übersprungene Fall trägt
einen Grund, sonst entsteht genau der stille Rest, den das Werkzeug vermeiden soll.

Die Zahlen stammen aus der Messung vom 2026-07-28 (IIL-Postfach, Ordner 'Archiv').
"""

import importlib.util
import pathlib

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "archiv_einsortieren.py"
)
_spec = importlib.util.spec_from_file_location("archiv_einsortieren", _SRC)
ae = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ae)

VORHANDEN = {"2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"}


def _ent(jahr, bis=2024, jetzt=2026, ordner=None):
    return ae.entscheide(jahr, bis, jetzt, VORHANDEN if ordner is None else ordner)


# --- Datumsauswertung ------------------------------------------------------


def test_should_extract_year_from_iso_timestamp():
    assert ae.jahr_aus("2021-03-04T09:15:00Z") == "2021"


def test_should_return_none_for_unusable_date():
    for wert in (None, "", "abc", "20"):
        assert ae.jahr_aus(wert) is None


# --- Kernentscheidung ------------------------------------------------------


def test_should_file_message_into_matching_year():
    ziel, grund = _ent("2021")
    assert ziel == "2021"
    assert grund == "einsortieren"


def test_should_keep_current_year_untouched():
    ziel, grund = _ent("2026")
    assert ziel is None
    assert "laufendes Jahr" in grund


def test_should_keep_year_after_cutoff():
    """2025 liegt nach --bis 2024 und bleibt liegen, obwohl es Vergangenheit ist."""
    ziel, grund = _ent("2025")
    assert ziel is None
    assert "nach --bis" in grund


def test_should_skip_when_target_folder_is_missing():
    """Fehlt der Jahrgangsordner, wird uebersprungen — nicht angelegt.

    Ein Werkzeug, das im selben Lauf Ordner erfindet und befuellt, macht einen
    Tippfehler im Quellpfad unbemerkbar.
    """
    ziel, grund = _ent("2015", ordner=VORHANDEN)
    assert ziel is None
    assert "fehlt" in grund


def test_should_skip_message_without_date():
    ziel, grund = _ent(None)
    assert ziel is None
    assert "Empfangsdatum" in grund


def test_should_always_give_a_reason_when_skipping():
    for jahr in (None, "2015", "2025", "2026"):
        ziel, grund = _ent(jahr)
        assert ziel is None
        assert grund and grund.strip(), jahr


# --- gemessene Verteilung 2026-07-28 --------------------------------------


def test_should_match_the_measured_distribution():
    """Die reale Jahresverteilung des IIL-Archivs, gegen die Entscheidung gehalten.

    22.599 von 22.623 sind einzusortieren; 17 aus 2025 liegen nach der Grenze,
    7 aus 2026 sind das laufende Jahr.
    """
    gemessen = {
        "2016": 3853, "2017": 7466, "2018": 3969, "2019": 4306, "2020": 2275,
        "2021": 518, "2022": 145, "2023": 20, "2024": 47, "2025": 17, "2026": 7,
    }
    einsortieren = liegen_bleiben = 0
    for jahr, anzahl in gemessen.items():
        ziel, _ = _ent(jahr)
        if ziel:
            einsortieren += anzahl
        else:
            liegen_bleiben += anzahl

    assert einsortieren == 22599
    assert liegen_bleiben == 24
    assert einsortieren + liegen_bleiben == sum(gemessen.values()) == 22623


def test_should_narrow_to_a_single_year_for_the_pilot_run():
    """2022 (145 Stueck) ist der Kandidat fuer den ersten echten Lauf."""
    assert _ent("2022")[0] == "2022"
    assert _ent("2021")[0] == "2021"  # --nur-jahr filtert spaeter, nicht hier
