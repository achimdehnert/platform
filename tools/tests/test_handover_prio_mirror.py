"""Golden-Tests fuer tools/hooks/handover_prio_mirror.sh (platform#1323).

Der Hook spiegelt die dokumentierte Prioritaet an den Session-Start. Er lief drei
Fehlerklassen lang still falsch (2026-07-22, ausschreibungs-hub):
  U1 eine ARCHIV-Ueberschrift ("### Prioritaeten vom … — erledigt") reaktivierte die
     Sektion, weil die Erkennung nur auf das Trigger-Wort schaut,
  U2 Tabellenspalten wurden positionsbasiert gelesen, eine "Prio"-Spalte an Position 2
     lieferte "hoch/mittel/niedrig" als Aufgabentitel,
  U3 in einem git-Worktree ist `.git` eine DATEI — `[ -d ]` liess den Hook dort stumm,
     ausgerechnet im von ADR-233 vorgeschriebenen Editier-Modus.
Alle drei sind hier als Golden-Test festgenagelt, damit sie nicht zurueckkehren.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "handover_prio_mirror.sh"

# Realer Dokumentstand, der den Bug ausgeloest hat (ausschreibungs-hub @ c7d2765).
BUGGY_HANDOVER = """# AGENT_HANDOVER · demo

## Prioritäten

| # | Prio | Item | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | hoch | Tunnel-Prozess starten | — | 🟢 offen |
| 2 | mittel | Migrationen auf Prod fahren | — | 🟢 offen |

### Prioritäten vom 2026-07-08 — erledigt

| # | Prio | Item | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | 🟢 | Referenz-Pflege-Erweiterung mergen | #147 | ✅ gemerged |
| 2 | 🟢 | Mandant-Onboarding-KD mergen | #148 | ✅ gemerged |
"""

CANONICAL_HANDOVER = """# AGENT_HANDOVER · demo

## Prioritäten

| # | Item | Tier | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | Preview-Tunnel starten | [Sonnet] | — | 🟢 offen |
| 2 | Migrationen auf Prod fahren | [Opus] | — | 🟢 offen |
"""


def _run(repo: Path) -> str:
    return subprocess.run(
        ["bash", str(HOOK)], cwd=repo, capture_output=True, text=True, timeout=30
    ).stdout


def _repo(tmp_path: Path, handover: str, *, git_as_file: bool = False) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    if git_as_file:
        # Worktree-Form: .git ist eine Datei mit gitdir-Zeiger, kein Verzeichnis.
        (repo / ".git").write_text("gitdir: /somewhere/.git/worktrees/x\n")
    else:
        (repo / ".git").mkdir()
    (repo / "AGENT_HANDOVER.md").write_text(handover, encoding="utf-8")
    return repo


def test_should_ignore_archived_priority_section(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path, BUGGY_HANDOVER))
    assert "Referenz-Pflege-Erweiterung" not in out
    assert "Mandant-Onboarding-KD" not in out


def test_should_read_task_text_when_prio_column_precedes_item(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path, BUGGY_HANDOVER))
    assert "Tunnel-Prozess starten" in out
    for vocab in ("1. hoch", "2. mittel"):
        assert vocab not in out


def test_should_still_read_canonical_table_with_tier(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path, CANONICAL_HANDOVER))
    assert "Preview-Tunnel starten" in out
    assert "[Sonnet]" in out


def test_should_emit_priorities_inside_a_git_worktree(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path, CANONICAL_HANDOVER, git_as_file=True))
    assert "Preview-Tunnel starten" in out


def test_should_stay_silent_outside_a_git_repo(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "AGENT_HANDOVER.md").write_text(CANONICAL_HANDOVER, encoding="utf-8")
    assert _run(plain) == ""


@pytest.mark.parametrize("heading", ["Archiv 2026-07-08", "Erledigt 2026-07-08"])
def test_should_not_reopen_section_on_archive_heading_variants(
    tmp_path: Path, heading: str
) -> None:
    doc = CANONICAL_HANDOVER + f"\n### {heading}\n\n| # | Item | Tier |\n|---|---|---|\n| 1 | Alt-Item | [Sonnet] |\n"
    out = _run(_repo(tmp_path, doc))
    assert "Alt-Item" not in out


# --- Retro 2026-07-22, Befund B1 -------------------------------------------------
# Ein Archiv-Marker, der als Teilstring irgendwo im Heading matchte, verschluckte auch
# Ueberschriften mit TEILerledigung. Offene Items verschwanden still. Die Faelle unten
# sind die Fallmatrix, gegen die Python- und awk-Implementierung gemeinsam geprueft
# werden (siehe test_next_sync_handover_parsing.py, gleiche Tabelle).

PARTIAL_HEADINGS = [
    "## Prioritäten — 2 von 5 erledigt",
    "## Prioritäten — teilweise erledigt",
    "## Prioritäten — 40 % erledigt",
    "## Prioritäten — 3/7 erledigt",
]

ARCHIVE_HEADINGS = [
    "### Prioritäten vom 2026-07-08 — erledigt",
    "### Archiv 2026-07-08 — abgeschlossen",
    "### Erledigt 2026-07-08",
]


def _doc(heading: str) -> str:
    return (
        "# AGENT_HANDOVER · demo\n\n"
        f"{heading}\n\n"
        "| # | Item | Tier |\n|---|------|------|\n"
        "| 1 | Item Alpha | [Sonnet] |\n"
    )


@pytest.mark.parametrize("heading", PARTIAL_HEADINGS)
def test_should_still_mirror_items_under_partially_done_heading(
    tmp_path: Path, heading: str
) -> None:
    """Teilerledigung ist KEIN Archiv — die offenen Items muessen sichtbar bleiben."""
    assert "Item Alpha" in _run(_repo(tmp_path, _doc(heading)))


@pytest.mark.parametrize("heading", ARCHIVE_HEADINGS)
def test_should_ignore_fully_archived_heading(tmp_path: Path, heading: str) -> None:
    """Regression zu platform#1323: echte Archiv-Sektionen bleiben unsichtbar."""
    assert "Item Alpha" not in _run(_repo(tmp_path, _doc(heading)))


# ─────────────────────────────────────────────────────────────────────────────
# Staleness-Warnung (platform#1378)
#
# Realfall 2026-07-23: der Haupt-Tree hing 11 Commits hinter origin/main, der Hook
# spiegelte die alte AGENT_HANDOVER.md — ohne jeden Hinweis. Die Session lief auf
# "12 offene PRs" los (real: einer) und wollte einen Testlauf vorbereiten, der am
# Vorabend bestanden worden war.
#
# Die Tests bauen ein echtes Repo und setzen refs/remotes/origin/main von Hand —
# kein Netz, kein fetch, deterministisch.
# ─────────────────────────────────────────────────────────────────────────────

WARN_MARKER = "VERALTET"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=30
    ).stdout.strip()


def _real_repo(tmp_path: Path, *, handover: str = CANONICAL_HANDOVER) -> Path:
    repo = tmp_path / "real"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.org")
    _git(repo, "config", "user.name", "T")
    (repo / "AGENT_HANDOVER.md").write_text(handover, encoding="utf-8")
    (repo / "other.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _advance_origin(repo: Path, *, touch: str, content: str) -> None:
    """Zweiten Commit bauen, origin/main darauf zeigen lassen, HEAD zurueckdrehen."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / touch).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "remote-side")
    ahead = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", ahead)
    _git(repo, "reset", "-q", "--hard", base)


def test_should_warn_when_handover_is_behind_origin_main(tmp_path: Path) -> None:
    repo = _real_repo(tmp_path)
    _advance_origin(
        repo,
        touch="AGENT_HANDOVER.md",
        content=CANONICAL_HANDOVER.replace("Preview-Tunnel starten", "Ganz andere Prio"),
    )
    out = _run(repo)
    assert WARN_MARKER in out
    assert "1 Commits hinter origin/main" in out
    # Die veraltete Prio wird trotzdem gezeigt — die Warnung ersetzt sie nicht.
    assert "Preview-Tunnel starten" in out


def test_should_stay_quiet_when_only_other_files_changed(tmp_path: Path) -> None:
    """"N Commits hinter" allein ist Alltag — sonst Alarm-Muedigkeit."""
    repo = _real_repo(tmp_path)
    _advance_origin(repo, touch="other.txt", content="v2\n")
    assert WARN_MARKER not in _run(repo)


def test_should_stay_quiet_when_up_to_date(tmp_path: Path) -> None:
    repo = _real_repo(tmp_path)
    _git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD"))
    assert WARN_MARKER not in _run(repo)


def test_should_stay_quiet_without_origin_main_ref(tmp_path: Path) -> None:
    """Frischer Klon ohne Remote-Ref: kein Rauschen, kein Fehler."""
    out = _run(_real_repo(tmp_path))
    assert WARN_MARKER not in out
    assert "Preview-Tunnel starten" in out
