"""Drill für tools/handover_stale_reference_check.py — Gate `handover-prio-zeigt-auf-erledigtes`.

Der wichtigste Test ist `test_should_catch_the_real_case_from_2026_08_12`: er baut den
Handover-Stand nach, der den Auftrag platform#1945 überhaupt ausgelöst hat (Prio 1 zeigte
auf das geschlossene #1650). Ein Melder, der diesen Fall nicht fängt, ist gebaut und nutzlos.

Die Netz-Schicht (`state_of`) ist gemockt — sonst hinge der Drill an GitHub und wäre weder
offline noch deterministisch lauffähig.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import handover_stale_reference_check as hsrc  # noqa: E402

GH = "https://github.com/achimdehnert/platform"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "AGENT_HANDOVER.md"
    p.write_text(body, encoding="utf-8")
    return p


def _states(monkeypatch, mapping: dict[int, str]):
    monkeypatch.setattr(hsrc, "state_of", lambda ref: mapping.get(ref["number"]))


# ── der Realfall ──────────────────────────────────────────────────────────────


def test_should_catch_the_real_case_from_2026_08_12(tmp_path, monkeypatch):
    """Prio 1 zeigte auf das geschlossene Gate-Audit #1650 — gefangen hatte das nur ein
    Mensch im manuellen Diskrepanz-Check. Genau dafür existiert dieser Melder."""
    doc = _write(
        tmp_path,
        "# Handover\n\n## Nächste Schritte (kompakt)\n\n"
        f"1. **[#1650]({GH}/issues/1650) — Gate-Audit abschließen.** Drei Abnahme-Kriterien,\n"
        "   Registry-Abgleich und Drill-Lauf stehen noch aus.\n",
    )
    _states(monkeypatch, {1650: "closed"})
    result = hsrc.check(doc)
    assert len(result["findings"]) == 1
    assert result["findings"][0]["ref"] == "achimdehnert/platform#1650"
    assert result["findings"][0]["state"] == "closed"


def test_should_report_merged_pr_as_stale(tmp_path, monkeypatch):
    doc = _write(
        tmp_path,
        f"## Offene Punkte\n\n1. **Nachziehen:** [#1948]({GH}/pull/1948) fertigstellen.\n",
    )
    _states(monkeypatch, {1948: "merged"})
    assert len(hsrc.check(doc)["findings"]) == 1


# ── was ausdrücklich KEIN Befund ist ──────────────────────────────────────────


def test_should_not_flag_a_reference_that_is_described_as_settled(
    tmp_path, monkeypatch
):
    """„die Wurzel unter dem am 2026-08-10 geschlossenen #1845" ist Kontext, kein Zeiger."""
    doc = _write(
        tmp_path,
        "## Nächste Schritte\n\n"
        f"1. **[#1078]({GH}/issues/1078) Befund 4 — tote Credential.** Das ist die Wurzel\n"
        f"   unter dem am 2026-08-10 geschlossenen [#1845]({GH}/issues/1845): der Pin nimmt\n"
        "   der Klasse den Auslöser, heilt sie aber nicht.\n",
    )
    _states(monkeypatch, {1078: "open", 1845: "closed"})
    result = hsrc.check(doc)
    assert result["findings"] == []
    assert result["geprueft"] == 1  # nur #1078 wurde überhaupt abgefragt


def test_should_not_let_a_far_away_word_suppress_a_real_finding(tmp_path, monkeypatch):
    """Die Erledigt-Erkennung schaut in ein Fenster um die Referenz, nicht auf die Zeile.

    Auf Zeilenebene fiel im Echtlauf JEDE der drei platform-Prios aus der Prüfung, weil
    Prio-Items 300+ Zeichen lang sind und fast immer irgendwo ein „erledigt" tragen — der
    Melder meldete „0 geprüft" und sah dabei grün aus."""
    doc = _write(
        tmp_path,
        "## Nächste Schritte\n\n"
        f"1. **[#1650]({GH}/issues/1650) — Gate-Audit.** " + "Fülltext. " * 20 + "\n"
        "   Kriterium 4 ist mit dem letzten PR erledigt.\n",
    )
    _states(monkeypatch, {1650: "closed"})
    assert len(hsrc.check(doc)["findings"]) == 1


def test_should_ignore_context_outside_the_numbered_list(tmp_path, monkeypatch):
    """Blockquote-Kontext nennt gemergte PRs zu Recht. Auf der ganzen Sektion meldete der
    Check im Echtlauf 18 Treffer, 16 davon Kontext — Fehlalarmquote 89 %."""
    doc = _write(
        tmp_path,
        "## Nächste Schritte\n\n"
        f"1. **[#1945]({GH}/issues/1945) — Auftrag.** Läuft.\n\n"
        f"> Alt-Prio 3 ist mit [#1854]({GH}/pull/1854) abgeräumt.\n"
        f"> Ebenso [#1865]({GH}/pull/1865).\n",
    )
    _states(monkeypatch, {1945: "open", 1854: "merged", 1865: "merged"})
    result = hsrc.check(doc)
    assert result["findings"] == []
    assert result["geprueft"] == 1


def test_should_skip_document_without_priority_section(tmp_path, monkeypatch):
    doc = _write(
        tmp_path, "# Handover\n\n## Aktueller Stand (2026-08-13)\n\nAlles ruhig.\n"
    )
    _states(monkeypatch, {})
    assert hsrc.check(doc)["status"].startswith("keine_prio")


# ── Ehrlichkeit bei fehlender Auskunft ────────────────────────────────────────


def test_should_not_claim_green_when_state_is_unavailable(tmp_path, monkeypatch):
    """Kein Netz/Token darf nicht als „keine Diskrepanz" durchgehen — ein Fetch-Fehler
    ist kein grüner Zustand."""
    doc = _write(
        tmp_path, f"## Offene Punkte\n\n1. **[#1650]({GH}/issues/1650)** offen?\n"
    )
    _states(monkeypatch, {})  # state_of liefert None
    result = hsrc.check(doc)
    assert result["findings"] == []
    assert result["geprueft"] == 0
    assert result["unpruefbar"] == ["achimdehnert/platform#1650"]


def test_should_count_each_reference_only_once(tmp_path, monkeypatch):
    doc = _write(
        tmp_path,
        "## Offene Punkte\n\n"
        f"1. **[#1650]({GH}/issues/1650)** und nochmal [#1650]({GH}/issues/1650).\n",
    )
    _states(monkeypatch, {1650: "closed"})
    assert len(hsrc.check(doc)["findings"]) == 1


# ── Bausteine ─────────────────────────────────────────────────────────────────


def test_should_stop_the_item_list_at_the_first_blockquote():
    section = ["1. erstes Item", "   Fortsetzung", "", "> Kontext", "2. nicht mehr"]
    assert [line for _o, line in hsrc.prio_items(section)] == [
        "1. erstes Item",
        "   Fortsetzung",
    ]


def test_should_ignore_lines_before_the_first_numbered_item():
    section = ["> Vorspann mit Link", "1. Item"]
    assert [line for _o, line in hsrc.prio_items(section)] == ["1. Item"]


def test_should_parse_owner_and_kind_from_url():
    refs = hsrc.refs_in(["siehe [#7](https://github.com/meiki-lra/meiki-hub/pull/7)"])
    assert (refs[0]["owner"], refs[0]["repo"], refs[0]["kind"], refs[0]["number"]) == (
        "meiki-lra",
        "meiki-hub",
        "pr",
        7,
    )


def test_should_register_the_gate_header_slug_in_the_registry():
    """KONZ-038 D8: der Kopf gehört ins Modul, und sein Slug muss der registrierte sein."""
    import json

    reg = json.loads(
        (REPO_ROOT / "docs" / "governance" / "gate-registry.json").read_text("utf-8")
    )
    slugs = {g["slug"] for g in reg["gates"]}
    assert hsrc.GATE_HEADER["slug"] in slugs


# --- Prio-Tabellen (Regression 2026-08-23, KONZ-platform-050) -----------------
# Der Parser kannte nur nummerierte Listen. `iil-klickdummy` fuehrt seine Prios als
# Markdown-Tabelle — der Check meldete dort `keine_prio_items`, der Runner verbuchte
# das als PASS. Grün stand fuer "konnte nicht lesen", nicht fuer "nichts gefunden".


def test_should_read_prio_items_from_a_markdown_table():
    section = [
        "| Prio | Task | Tier |",
        "|---|---|---|",
        "| 0 | Erstes Item | `[Sonnet]` |",
        "| 1 | Zweites Item | `[Opus]` |",
    ]
    zeilen = [line for _o, line in hsrc.prio_items(section)]
    assert zeilen == [
        "| 0 | Erstes Item | `[Sonnet]` |",
        "| 1 | Zweites Item | `[Opus]` |",
    ]


def test_should_not_mistake_table_head_or_separator_for_items():
    """Kopf- und Trennzeile sind Struktur, keine Prioritaeten."""
    section = ["| Prio | Task |", "|:---|---:|"]
    assert hsrc.prio_items(section) == []


def test_should_find_a_settled_reference_inside_a_table_row():
    """Gegenprobe zur Abwesenheit: der Check muss in Tabellen auch WIRKLICH finden.

    Ohne diesen Fall belegt ein leeres Ergebnis nichts — es koennte der Filter sein
    statt der Befund (evidence-discipline, Realfall 2026-07-31).
    """
    section = [
        "| Prio | Task |",
        "|---|---|",
        "| 0 | [#7](https://github.com/meiki-lra/meiki-hub/pull/7) nachziehen |",
    ]
    items = hsrc.prio_items(section)
    refs = hsrc.refs_in([line for _o, line in items])
    assert len(refs) == 1
    assert (refs[0]["repo"], refs[0]["number"]) == ("meiki-hub", 7)
