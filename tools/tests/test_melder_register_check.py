"""Tests für tools/melder_register_check.py (#2690 K3 — Vorausschauende Wartung).

Reine Funktionen ueberall dort, wo befund_journal.py sonst per subprocess gerufen
wuerde: `herabstufungen()` und `ohne_entscheidung_liste()` bekommen bereits
geparste JSON-Listen uebergeben (Aufrufer in `main()` fuehrt den Subprocess aus,
die Tests nicht — Fixtures fuer Register, Runner-Ausschnitt und Journal-JSON).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "melder_register_check.py"
_spec = importlib.util.spec_from_file_location("melder_register_check", _SRC)
mrc = importlib.util.module_from_spec(_spec)
sys.modules["melder_register_check"] = mrc
_spec.loader.exec_module(mrc)


RUNNER_AUSSCHNITT = """
record "0.0 env+banner" "PASS" "..."
record "0.7.4 prio-referenzen" "WARN" "..." "$TARGET_REPO"
record "0.7.6 leseflaeche" "PASS" "..."
record "0.7.7 gate-wirkung" "WARN" "..."
"""


def _register(**overrides):
    basis = {
        "phase": "0.7.4 prio-referenzen",
        "leser": "Agent selbst, vor Arbeitsbeginn",
        "wiedervorlage_tage": 14,
        "praezision_min": 0.6,
        "mindest_laeufe": 5,
        "runbook": "0.R#0.7.4",
    }
    basis.update(overrides)
    return basis


# --- lade_register / lade_runner_phasen -------------------------------------


def test_should_load_register_entries_from_yaml(tmp_path):
    pfad = tmp_path / "melder-register.yaml"
    pfad.write_text(
        "melder:\n"
        "  - phase: \"0.0 env+banner\"\n"
        "    leser: UNBENANNT\n"
        "    wiedervorlage_tage: 14\n"
        "    praezision_min: 0.6\n"
        "    mindest_laeufe: 5\n"
        "    runbook: \"0.R#0.0\"\n",
        encoding="utf-8",
    )
    register = mrc.lade_register(pfad)
    assert len(register) == 1
    assert register[0]["phase"] == "0.0 env+banner"
    assert register[0]["leser"] == "UNBENANNT"


def test_should_extract_phase_ids_from_runner_excerpt(tmp_path):
    pfad = tmp_path / "runner.sh"
    pfad.write_text(RUNNER_AUSSCHNITT, encoding="utf-8")
    phasen = mrc.lade_runner_phasen(pfad)
    assert phasen == {
        "0.0 env+banner",
        "0.7.4 prio-referenzen",
        "0.7.6 leseflaeche",
        "0.7.7 gate-wirkung",
    }


def test_should_return_empty_set_when_runner_missing(tmp_path):
    assert mrc.lade_runner_phasen(tmp_path / "nicht-da.sh") == set()


# --- register_pruefen / kurz_bericht -----------------------------------------


def test_should_detect_runner_phase_without_register_entry():
    """Positivkontrolle: eine Runner-Phase OHNE Register-Zeile MUSS als fehlend auftauchen."""
    register = [_register(phase="0.7.6 leseflaeche", leser="Agent selbst")]
    runner_phasen = {"0.7.6 leseflaeche", "0.7.7 gate-wirkung"}
    fehlend, unbenannt, karteileiche = mrc.register_pruefen(register, runner_phasen)
    assert fehlend == ["0.7.7 gate-wirkung"]
    assert unbenannt == []
    assert karteileiche == []


def test_should_count_unbenannt_entries():
    """Positivkontrolle: ein Eintrag mit leser: UNBENANNT MUSS gezaehlt werden."""
    register = [
        _register(phase="0.7.6 leseflaeche", leser="Agent selbst"),
        _register(phase="0.7.7 gate-wirkung", leser="UNBENANNT"),
    ]
    runner_phasen = {"0.7.6 leseflaeche", "0.7.7 gate-wirkung"}
    fehlend, unbenannt, karteileiche = mrc.register_pruefen(register, runner_phasen)
    assert fehlend == []
    assert unbenannt == ["0.7.7 gate-wirkung"]
    assert karteileiche == []


def test_should_detect_orphaned_register_entry_as_karteileiche():
    """Positivkontrolle: ein Register-Eintrag ohne Runner-Phase MUSS als Karteileiche auftauchen."""
    register = [
        _register(phase="0.7.6 leseflaeche", leser="Agent selbst"),
        _register(phase="0.7.99 abgeschafft", leser="Agent selbst"),
    ]
    runner_phasen = {"0.7.6 leseflaeche"}
    fehlend, unbenannt, karteileiche = mrc.register_pruefen(register, runner_phasen)
    assert fehlend == []
    assert unbenannt == []
    assert karteileiche == ["0.7.99 abgeschafft"]


def test_should_report_ok_when_register_and_runner_match():
    register = [_register(phase="0.7.6 leseflaeche", leser="Agent selbst")]
    runner_phasen = {"0.7.6 leseflaeche"}
    text, rc = mrc.kurz_bericht(register, runner_phasen)
    assert text == ""
    assert rc == 0


def test_should_combine_missing_and_unbenannt_in_kurz_bericht_with_nonzero_exit():
    register = [_register(phase="0.7.6 leseflaeche", leser="UNBENANNT")]
    runner_phasen = {"0.7.6 leseflaeche", "0.7.7 gate-wirkung"}
    text, rc = mrc.kurz_bericht(register, runner_phasen)
    assert rc == 1
    assert "2 Melder ohne Leser" in text
    assert "0.7.6 leseflaeche" in text
    assert "0.7.7 gate-wirkung" in text


def test_should_report_karteileiche_separately_in_kurz_bericht():
    register = [
        _register(phase="0.7.6 leseflaeche", leser="Agent selbst"),
        _register(phase="0.7.99 abgeschafft", leser="Agent selbst"),
    ]
    runner_phasen = {"0.7.6 leseflaeche"}
    text, rc = mrc.kurz_bericht(register, runner_phasen)
    assert rc == 1
    assert "Karteileiche" in text
    assert "0.7.99 abgeschafft" in text
    assert "0 Melder ohne Leser" in text


# --- herabstufungen -----------------------------------------------------------


def test_should_downgrade_melder_below_threshold_with_enough_runs():
    """Positivkontrolle: >= mindest_laeufe UND < praezision_min MUSS herabgestuft werden."""
    register = [_register(mindest_laeufe=5, praezision_min=0.6)]
    praez = [
        {
            "phase": "0.7.4 prio-referenzen",
            "echt": 2,
            "falsch": 3,
            "urteile": 5,
            "praezision": 0.4,
            "bewertbar": True,
        }
    ]
    gefunden = mrc.herabstufungen(register, praez, "2026-09-02")
    assert len(gefunden) == 1
    assert gefunden[0]["phase"] == "0.7.4 prio-referenzen"
    assert gefunden[0]["quote"] == 0.4
    assert gefunden[0]["laeufe"] == 5


def test_should_not_downgrade_below_threshold_with_too_few_runs():
    """3 Urteile bei mindest_laeufe=5: nicht herabstufen, auch wenn die Quote niedrig ist."""
    register = [_register(mindest_laeufe=5, praezision_min=0.6)]
    praez = [
        {
            "phase": "0.7.4 prio-referenzen",
            "echt": 1,
            "falsch": 2,
            "urteile": 3,
            "praezision": 0.3333333333333333,
            "bewertbar": True,
        }
    ]
    assert mrc.herabstufungen(register, praez, "2026-09-02") == []


def test_should_not_downgrade_melder_at_or_above_threshold():
    register = [_register(mindest_laeufe=5, praezision_min=0.6)]
    praez = [
        {
            "phase": "0.7.4 prio-referenzen",
            "echt": 4,
            "falsch": 1,
            "urteile": 5,
            "praezision": 0.8,
            "bewertbar": True,
        }
    ]
    assert mrc.herabstufungen(register, praez, "2026-09-02") == []


def test_should_write_and_clear_downgrade_tsv(tmp_path):
    ziel = tmp_path / "state" / "melder-herabgestuft.tsv"
    mrc.schreibe_herabstufung_tsv(
        [{"phase": "0.7.4 prio-referenzen", "quote": 0.4, "laeufe": 5, "datum": "2026-09-02"}],
        ziel,
    )
    zeile = ziel.read_text(encoding="utf-8").strip()
    assert zeile == "0.7.4 prio-referenzen\t0.4000\t5\t2026-09-02"

    # Geheilter Melder: Datei wird beim naechsten Lauf geleert, nicht angehaengt.
    mrc.schreibe_herabstufung_tsv([], ziel)
    assert ziel.read_text(encoding="utf-8") == ""


# --- ohne_entscheidung_liste --------------------------------------------------


def test_should_exclude_verankerte_and_verzichtete_findings():
    """Positivkontrolle: ein OHNE Artefakt/Verzicht UND altes Finding MUSS auftauchen —
    ein verankertes und ein mit Verzicht abgelegtes gleich altes Finding NICHT."""
    heute = date(2026, 9, 2)
    daten = [
        {
            "id": "a::platform", "phase": "a", "repo": "platform",
            "erstmals": "2026-08-01", "artefakt": None, "verzicht": None,
        },
        {
            "id": "b::platform", "phase": "b", "repo": "platform",
            "erstmals": "2026-08-01", "artefakt": "https://example.invalid/1", "verzicht": None,
        },
        {
            "id": "c::platform", "phase": "c", "repo": "platform",
            "erstmals": "2026-08-01", "artefakt": None,
            "verzicht": {"grund": "bewusst", "am": "2026-08-05"},
        },
    ]
    gefunden = mrc.ohne_entscheidung_liste(daten, 14, heute)
    assert [e["id"] for e in gefunden] == ["a::platform"]
    assert gefunden[0]["alter_tage"] == 32


def test_should_exclude_findings_within_the_grace_period():
    heute = date(2026, 9, 2)
    daten = [
        {
            "id": "frisch::platform", "phase": "x", "repo": "platform",
            "erstmals": "2026-08-30", "artefakt": None, "verzicht": None,
        }
    ]
    assert mrc.ohne_entscheidung_liste(daten, 14, heute) == []


def test_should_render_block_header_with_count_and_empty_case():
    assert mrc.ohne_entscheidung_block([], 14) == "⏳ ohne Entscheidung > 14 d: keiner"
    text = mrc.ohne_entscheidung_block(
        [{"phase": "a", "repo": "platform", "alter_tage": 32, "erstmals": "2026-08-01"}], 14
    )
    assert "⏳ ohne Entscheidung > 14 d (1):" in text
    assert "a [platform] — 32 d alt, erstmals 2026-08-01" in text
