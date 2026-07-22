"""Tests für tools/next-sync/claude-next-sync (Prio-Sektions-Erkennung, platform#1323).

Hintergrund: `~/.claude/hooks/handover_prio_mirror.sh` (AUSSERHALB dieses Repos, wird hier
NICHT geändert) und `claude-next-sync` lesen beide die `## Prioritäten`-Sektion aus
AGENT_HANDOVER.md. iilgmbh/ausschreibungs-hub#165 fand zwei generische Bugs, live
verifiziert am 2026-07-22:

Ursache 1 — ein archivierter Abschnitt wie `### Prioritäten vom 2026-07-08 — erledigt`
matcht dieselbe Trigger-Regex wie eine aktive Prio-Überschrift ("Prioritäten..." steht
unter den ersten zwei Wörtern) und kann die Sektions-Erkennung reaktivieren, wenn er vor
der echten Sektion im Dokument steht bzw. keine exakte '## Prioritäten'-Überschrift
existiert. Fix: Überschriften mit `erledigt|abgeschlossen|Archiv|✅` werden von der
Erkennung ausgenommen.

Ursache 2 — die Tabellenspalten wurden positionsbasiert gelesen (`cells[1]` = Aufgabentext,
`cells[2]` = Tier). Eine optisch identische Tabelle mit einer zusätzlichen Spalte vor
`Item` (z.B. `| # | Prio | Item | … |`) lieferte still die Prio-Vokabel ("hoch"/"mittel"/
"niedrig") statt des Aufgabentexts. Fix: Header-Zeile auswerten, Spalte `Item`/`Task`
case-insensitiv per Name suchen, Position nur als Fallback.

Alle Fixtures unten sind wörtliche Auszüge aus der echten Historie von
iilgmbh/ausschreibungs-hub/AGENT_HANDOVER.md (vor und nach PR #165), nicht synthetisch
erfunden — Beleg per `gh pr diff 165 --repo iilgmbh/ausschreibungs-hub` (2026-07-22).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_loader(
    "claude_next_sync",
    importlib.machinery.SourceFileLoader(
        "claude_next_sync",
        str(Path(__file__).resolve().parents[1] / "next-sync" / "claude-next-sync"),
    ),
)
cns = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cns)


def _write_handover(tmp_path: Path, content: str) -> Path:
    (tmp_path / "AGENT_HANDOVER.md").write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Fixture 1 (Ursache 1): echter Archiv-Block vom 2026-07-08 VOR der echten
# aktiven Sektion — genau das reale Muster, das den Bug live reproduziert
# (die Archiv-Überschrift matcht den Prio-Trigger und steht im Dokument vor
# der Überschrift der aktiven Sektion).
# ---------------------------------------------------------------------------
FIXTURE_ARCHIVE_BEFORE_ACTIVE = """\
# AGENT_HANDOVER · ausschreibungs-hub

## Vorheriger Stand — 2026-07-08 (Ende)

### Prioritäten vom 2026-07-08 — erledigt

| # | Prio | Item | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | 🟢 | Referenz-Pflege-Erweiterung mergen | #147 | ✅ gemerged 2026-07-08 |
| 2 | 🟢 | Mandant-Onboarding-KD mergen | #148 | ✅ gemerged 2026-07-08 |

> **Erledigt (nachgezogen 2026-07-21):** Beide PRs waren bereits am 2026-07-08 gemerged,
> die Tabelle stand seither veraltet im Handover — geprüft per `gh pr view 147/148`.

## Nächste Schritte

| # | Item | Tier | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | Preview-Tunnel starten (Befehl unten) | [Sonnet] | — | 🟢 offen |
"""

# ---------------------------------------------------------------------------
# Fixture 2 (Ursache 2): wörtliche aktive Prioritäten-Tabelle VOR PR #165 —
# `Item` steht an Position 3 (Spalte 2 ist `Prio` mit "hoch/mittel/niedrig").
# ---------------------------------------------------------------------------
FIXTURE_ITEM_AT_POSITION_3 = """\
# AGENT_HANDOVER · ausschreibungs-hub

## Prioritäten

| # | Prio | Item | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | hoch | Tunnel-Prozess starten (Befehl unten) | — | 🟢 offen |
| 2 | mittel | Migrationen 0005/0006 auf Prod fahren | — | 🟢 offen |
| 3 | niedrig | Reboot-Festigkeit Preview (systemd) | — | 🟢 offen |
| 4 | niedrig | Struktur-Fix Session-Start 0.7 mergen | platform#1321 | 🔵 CI grün, Review offen |
"""

# ---------------------------------------------------------------------------
# Fixture 3 (Regression): alter Vertrag NACH PR #165 — `| # | Item | Tier | … |`,
# Item an Position 2, Tier an Position 3 (identisch zur ursprünglichen
# positionsbasierten Annahme). Muss weiterhin funktionieren.
# ---------------------------------------------------------------------------
FIXTURE_OLD_CONTRACT = """\
# AGENT_HANDOVER · ausschreibungs-hub

## Prioritäten

| # | Item | Tier | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | Preview-Tunnel starten (Befehl unten) | [Sonnet] | — | 🟢 offen |
| 2 | Migrationen 0005/0006 auf Prod fahren | [Opus] | — | 🟢 offen |
| 3 | Reboot-Festigkeit Preview (systemd) | [Sonnet] | — | 🟢 offen |
| 4 | Struktur-Fix Session-Start 0.7 mergen | [Sonnet] | platform#1321 | 🔵 Review offen |
"""

# ---------------------------------------------------------------------------
# Fixture 4 (Fallback): kein Prioritäten-/Trigger-Heading im Dokument.
# ---------------------------------------------------------------------------
FIXTURE_NO_PRIORITY_SECTION = """\
# AGENT_HANDOVER · irgendein-repo

## Aktueller Stand — 2026-07-22

Alles synced, keine Restarbeit dokumentiert. Nur Fließtext, keine Tabelle.

## Konventionen (Kurz)

- Editieren nur via `repo-session.sh`-Worktree.
"""


def test_should_not_resurface_archived_items_when_archive_heading_precedes_active_section(tmp_path):
    """Ursache 1: Archiv-Heading '... — erledigt' darf die Sektion nicht reaktivieren."""
    repo = _write_handover(tmp_path, FIXTURE_ARCHIVE_BEFORE_ACTIVE)

    items = cns._read_handover(repo)

    assert items is not None, "aktive Sektion '## Nächste Schritte' muss gefunden werden"
    joined = " ".join(items)
    assert "Referenz-Pflege-Erweiterung" not in joined
    assert "Mandant-Onboarding-KD" not in joined
    assert any("Preview-Tunnel starten" in i for i in items)


def test_should_skip_archive_marked_headings_in_section_start_detection(tmp_path):
    """Weißbox-Ergänzung: _find_section_start selbst überspringt Archiv-Überschriften."""
    lines = FIXTURE_ARCHIVE_BEFORE_ACTIVE.splitlines()
    start = cns._find_section_start(lines)
    assert start is not None
    assert "Nächste Schritte" in lines[start]


def test_should_resolve_item_column_by_header_name_when_item_is_at_position_3(tmp_path):
    """Ursache 2: Tabelle mit `Prio` vor `Item` — Aufgabentext, nicht die Prio-Vokabel."""
    repo = _write_handover(tmp_path, FIXTURE_ITEM_AT_POSITION_3)

    items = cns._read_handover(repo)

    assert items is not None
    top = items[0]
    assert "Tunnel-Prozess starten (Befehl unten)" in top
    # Die alte, kaputte Ausgabe war exakt die Prio-Vokabel ("hoch") als Aufgabentitel.
    assert top.strip() not in ("hoch", "mittel", "niedrig")
    assert items[1].strip() != "mittel"
    assert "Migrationen 0005/0006 auf Prod fahren" in items[1]


def test_should_keep_working_with_old_item_tier_positional_contract(tmp_path):
    """Regression: `| # | Item | Tier | … |` (Item Pos 2, Tier Pos 3) funktioniert weiter."""
    repo = _write_handover(tmp_path, FIXTURE_OLD_CONTRACT)

    items = cns._read_handover(repo)

    assert items is not None
    assert items[0] == "[Sonnet] Preview-Tunnel starten (Befehl unten)"
    assert items[1] == "[Opus] Migrationen 0005/0006 auf Prod fahren"
    assert items[2] == "[Sonnet] Reboot-Festigkeit Preview (systemd)"


def test_should_leave_fallback_behavior_unchanged_when_no_priorities_section_exists(tmp_path):
    """Kein Prioritäten-Abschnitt vorhanden → _read_handover liefert None (git-Fallback greift)."""
    repo = _write_handover(tmp_path, FIXTURE_NO_PRIORITY_SECTION)

    items = cns._read_handover(repo)

    assert items is None


def test_should_extract_real_active_items_end_to_end_from_pre_fix_full_handover(tmp_path):
    """Golden-Path mit dem echten, vollständigen Vor-Fix-Dokument (vor iilgmbh#165):
    beide Ursachen gleichzeitig wirksam — Item-Spalte an Position 3 UND ein Archiv-
    Block weiter unten im Dokument. Erwartung: die drei echten Aufgabentexte, keine
    Prio-Vokabeln, keine archivierten #147/#148-Items.
    """
    full_document = (
        "# AGENT_HANDOVER · ausschreibungs-hub\n\n"
        "## Prioritäten\n\n"
        "| # | Prio | Item | PR/Issue | Status |\n"
        "|---|------|------|----------|--------|\n"
        "| 1 | hoch | Tunnel-Prozess starten (Befehl unten) | — | 🟢 offen |\n"
        "| 2 | mittel | Migrationen 0005/0006 auf Prod fahren | — | 🟢 offen |\n"
        "| 3 | niedrig | Reboot-Festigkeit Preview (systemd) | — | 🟢 offen |\n\n"
        "## Vorheriger Stand — 2026-07-08 (Ende)\n\n"
        "### Prioritäten vom 2026-07-08 — erledigt\n\n"
        "| # | Prio | Item | PR/Issue | Status |\n"
        "|---|------|------|----------|--------|\n"
        "| 1 | 🟢 | Referenz-Pflege-Erweiterung mergen | #147 | ✅ gemerged 2026-07-08 |\n"
        "| 2 | 🟢 | Mandant-Onboarding-KD mergen | #148 | ✅ gemerged 2026-07-08 |\n"
    )
    repo = _write_handover(tmp_path, full_document)

    items = cns._read_handover(repo)

    assert items is not None
    joined = " ".join(items)
    assert "Tunnel-Prozess starten (Befehl unten)" in joined
    assert "Migrationen 0005/0006 auf Prod fahren" in joined
    assert "Reboot-Festigkeit Preview (systemd)" in joined
    for vocab in ("hoch", "mittel", "niedrig"):
        assert vocab not in [i.strip() for i in items]
    assert "Referenz-Pflege-Erweiterung" not in joined
    assert "Mandant-Onboarding-KD" not in joined
