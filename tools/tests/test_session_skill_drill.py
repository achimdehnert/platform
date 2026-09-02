"""Kaltstart-Drill fuer die Session-Skills (K1, Issue #2690).

Deckt: Ueberschriften-/Checklisten-Parsing (inkl. Fenced-Code-Ignorierung),
Pflicht-/NEU-Erkennung, Vorlagen-Erzeugung, Protokoll-Bewertung (still
uebersprungen vs. bewusst uebersprungen mit hinreichendem Grund), Vergleich
zweier Protokolle, und den Sonderfall "Checkliste fehlt" (Exit 2, kein
Absturz). Fixtures sind klein und unabhaengig vom echten Skill-Inhalt; nur
ein Smoke-Test parst die drei echten Dateien.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "session_skill_drill.py"
_spec = importlib.util.spec_from_file_location("session_skill_drill", _SRC)
drill = importlib.util.module_from_spec(_spec)
sys.modules["session_skill_drill"] = drill  # dataclass-Typaufloesung braucht sys.modules-Eintrag
_spec.loader.exec_module(drill)

REPO_ROOT = _SRC.parents[1]


# --- Fixtures ---------------------------------------------------------

SKILL_MIT_CHECKLISTE = """\
## Phase 0: Start (IMMER zuerst)

Text ohne Marker im ersten Absatz hier.

### 0.4.3 Editier-Modus (ADR-233)

Beliebiger Text.

## Phase 2.7: Zielzustand (NEU 2026-08-07, PFLICHT für Arbeits-Sessions)

Text.

## Beispiel-Codeblock

Ein Beispiel, das eine Heredoc-Zeile enthaelt, die wie eine Ueberschrift aussieht:

```bash
cat > /tmp/x.md <<'EOF'
## Das ist keine echte Ueberschrift
EOF
```

## Abschluss-Checkliste

| # | Check | Status |
|---|-------|--------|
| 1 | Erster Check | ☐ |
| 2a | Zweiter Check mit Buchstaben-ID | ☐ |
"""

SKILL_OHNE_CHECKLISTE = """\
## Phase 0 — Right-Sizing

Text.

## Phase 1 — Collect

Text, keine Tabelle mit Check/Status hier.

| Spalte A | Spalte B |
|---|---|
| x | y |
"""


@pytest.fixture()
def skill_datei(tmp_path):
    p = tmp_path / "session-fixture.md"
    p.write_text(SKILL_MIT_CHECKLISTE, encoding="utf-8")
    return p


@pytest.fixture()
def skill_ohne_checkliste_datei(tmp_path):
    p = tmp_path / "session-ohne-checkliste.md"
    p.write_text(SKILL_OHNE_CHECKLISTE, encoding="utf-8")
    return p


# --- Parsing: Ueberschriften -------------------------------------------


def test_should_parse_all_headings_and_ignore_fenced_code(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    # 5 echte Ueberschriften: Phase 0, 0.4.3, Phase 2.7, Beispiel-Codeblock,
    # Abschluss-Checkliste — NICHT die "## Das ist keine echte Ueberschrift"
    # im Fenced-Code-Block.
    assert len(sp.headings) == 5
    texte = [h.text for h in sp.headings]
    assert not any("keine echte Ueberschrift" in t for t in texte)


def test_should_derive_phase_number_id_when_heading_starts_with_one(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    ids = {h.id: h for h in sp.headings}
    assert "0.4.3" in ids
    assert "2.7" in ids
    assert "0" in ids  # "Phase 0: Start ..." -> "0"


def test_should_normalize_text_id_when_no_phase_number(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    ids = [h.id for h in sp.headings]
    assert "beispiel-codeblock" in ids
    assert "abschluss-checkliste" in ids


def test_should_flag_pflicht_from_heading_or_first_paragraph(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    by_id = {h.id: h for h in sp.headings}
    assert by_id["0"].pflicht is True  # "IMMER" im Titel
    assert by_id["2.7"].pflicht is True  # "PFLICHT" im Titel
    assert by_id["0.4.3"].pflicht is False  # kein Marker in Titel/erstem Absatz


def test_should_flag_neu_marker(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    by_id = {h.id: h for h in sp.headings}
    assert by_id["2.7"].neu is True
    assert by_id["0"].neu is False


# --- Parsing: Checkliste -------------------------------------------------


def test_should_parse_checklist_rows_with_check_status_columns(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    assert sp.checklist_present is True
    assert len(sp.checklist) == 2
    ids = [c.id for c in sp.checklist]
    assert ids == ["checkliste-1", "checkliste-2a"]


def test_should_treat_checklist_rows_as_pflicht(skill_datei):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    assert all(c.pflicht for c in sp.checklist)


def test_should_flag_missing_checklist(skill_ohne_checkliste_datei):
    sp = drill.parse_skill(skill_ohne_checkliste_datei, skill="fixture")
    assert sp.checklist_present is False
    assert sp.checklist == []
    # die fremde Tabelle (Spalte A/Spalte B) darf NICHT als Checkliste zaehlen
    assert len(sp.headings) == 2


# --- CLI: --erwartung -----------------------------------------------------


def test_should_exit_2_without_traceback_when_checklist_missing(skill_ohne_checkliste_datei, capsys):
    rc = drill.main(["--erwartung", "--datei", str(skill_ohne_checkliste_datei)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "CHECKLISTE FEHLT" in out


def test_should_report_erwartung_counts_as_json(skill_datei):
    rc = drill.main(["--erwartung", "--datei", str(skill_datei), "--json"])
    assert rc == 0


def test_should_print_expected_json_fields(skill_datei, capsys):
    drill.main(["--erwartung", "--datei", str(skill_datei), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["ueberschriften"] == 5
    assert data["pflicht"] == 2
    assert data["checklisten_zeilen"] == 2
    assert data["checkliste_vorhanden"] is True


# --- CLI: --vorlage ---------------------------------------------------


def test_should_include_all_ids_in_vorlage(skill_datei, capsys):
    drill.main(["--vorlage", "--datei", str(skill_datei)])
    out = capsys.readouterr().out
    sp = drill.parse_skill(skill_datei, skill="fixture")
    for e in sp.einheiten():
        assert f"| {e.id} |" in out


def test_should_produce_parseable_vorlage_table(skill_datei, tmp_path):
    out_path = tmp_path / "vorlage.md"
    result = subprocess.run(
        [sys.executable, str(_SRC), "--vorlage", "--datei", str(skill_datei)],
        capture_output=True,
        text=True,
        check=True,
    )
    out_path.write_text(result.stdout, encoding="utf-8")
    rows = drill.parse_protokoll(out_path)
    sp = drill.parse_skill(skill_datei, skill="fixture")
    assert set(rows.keys()) == {e.id for e in sp.einheiten()}


# --- classify_status ----------------------------------------------------


def test_should_classify_erfuellt():
    assert drill.classify_status("erfüllt") == "erfuellt"


def test_should_classify_bewusst_uebersprungen_with_enough_reason():
    assert (
        drill.classify_status("bewusst übersprungen: kein Zugriff auf Prod moeglich hier")
        == "bewusst_uebersprungen"
    )


def test_should_classify_bewusst_uebersprungen_with_short_reason_as_still():
    assert drill.classify_status("bewusst übersprungen: zu kurz") == "still"


def test_should_classify_empty_or_placeholder_as_still():
    assert drill.classify_status("") == "still"
    assert drill.classify_status("<erfüllt|bewusst übersprungen: <grund>|fehlt>") == "still"


def test_should_classify_fehlt_as_still():
    assert drill.classify_status("fehlt") == "still"


# --- CLI: --protokoll -----------------------------------------------------


def _schreibe_protokoll(pfad, zeilen):
    lines = ["| ID | Status | Beleg |", "|---|---|---|"]
    for uid, status, beleg in zeilen:
        lines.append(f"| {uid} | {status} | {beleg} |")
    pfad.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_should_exit_1_when_pflicht_unit_silently_skipped(skill_datei, tmp_path):
    proto = tmp_path / "proto.md"
    sp = drill.parse_skill(skill_datei, skill="fixture")
    zeilen = [(e.id, "erfüllt", "ok") for e in sp.einheiten() if e.id != "2.7"]
    # "2.7" (PFLICHT) fehlt im Protokoll komplett -> still uebersprungen
    _schreibe_protokoll(proto, zeilen)
    rc = drill.main(["--protokoll", str(proto), "--datei", str(skill_datei)])
    assert rc == 1


def test_should_exit_0_when_pflicht_unit_consciously_skipped_with_reason(skill_datei, tmp_path):
    proto = tmp_path / "proto.md"
    sp = drill.parse_skill(skill_datei, skill="fixture")
    zeilen = []
    for e in sp.einheiten():
        if e.id == "2.7":
            zeilen.append((e.id, "bewusst übersprungen: Arbeits-Session nicht zutreffend hier", "Begruendung im Text"))
        else:
            zeilen.append((e.id, "erfüllt", "ok"))
    _schreibe_protokoll(proto, zeilen)
    rc = drill.main(["--protokoll", str(proto), "--datei", str(skill_datei)])
    assert rc == 0


def test_should_count_still_uebersprungen_in_json(skill_datei, tmp_path):
    proto = tmp_path / "proto.md"
    sp = drill.parse_skill(skill_datei, skill="fixture")
    zeilen = [(e.id, "fehlt", "") for e in sp.einheiten()]
    _schreibe_protokoll(proto, zeilen)
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        drill.main(["--protokoll", str(proto), "--datei", str(skill_datei), "--json"])
    data = json.loads(buf.getvalue())
    assert data["still_uebersprungen"] == len(sp.einheiten())
    assert data["still_uebersprungen_pflicht"] == sum(1 for e in sp.einheiten() if e.pflicht)


# --- CLI: --vergleich -----------------------------------------------------


def test_should_report_no_deviation_for_identical_protocols(skill_datei, tmp_path):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    zeilen = [(e.id, "erfüllt", "ok") for e in sp.einheiten()]
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    _schreibe_protokoll(a, zeilen)
    _schreibe_protokoll(b, zeilen)
    rc = drill.main(["--vergleich", str(a), str(b)])
    assert rc == 0


def test_should_exit_1_on_status_deviation_between_protocols(skill_datei, tmp_path):
    sp = drill.parse_skill(skill_datei, skill="fixture")
    zeilen_a = [(e.id, "erfüllt", "ok") for e in sp.einheiten()]
    zeilen_b = list(zeilen_a)
    zeilen_b[0] = (zeilen_b[0][0], "fehlt", "")
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    _schreibe_protokoll(a, zeilen_a)
    _schreibe_protokoll(b, zeilen_b)
    rc = drill.main(["--vergleich", str(a), str(b)])
    assert rc == 1


# --- CLI: --kurz ------------------------------------------------------


def test_should_produce_one_line_summary_for_all_three_skills(monkeypatch, capsys):
    rc = drill.main(["--kurz"])
    out = capsys.readouterr().out.strip()
    assert out.startswith("K1: start ")
    assert " · ende " in out
    assert " · retro " in out
    assert rc in (0, 2)


# --- Smoke: echte Skill-Dateien -----------------------------------------


@pytest.mark.parametrize("name", ["start", "ende", "retro"])
def test_should_parse_real_skill_with_more_than_zero_headings(name):
    path = drill.SKILL_FILES[name]
    assert path.exists(), f"Skill-Datei fehlt: {path}"
    sp = drill.parse_skill(path, skill=name)
    assert len(sp.headings) > 0


def test_should_flag_checklist_missing_for_real_session_retro():
    sp = drill.parse_skill(drill.SKILL_FILES["retro"], skill="retro")
    assert sp.checklist_present is False


@pytest.mark.parametrize("name", ["start", "ende"])
def test_should_find_checklist_for_real_session_start_and_ende(name):
    sp = drill.parse_skill(drill.SKILL_FILES[name], skill=name)
    assert sp.checklist_present is True
    assert len(sp.checklist) > 0
