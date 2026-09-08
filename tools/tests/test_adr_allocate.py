"""Tests fuer tools/adr_allocate.py — Merge-Time-Nummernvergabe (ADR-228).

Synthetische ADR-Verzeichnisse in tmp_path, echte git-Repos (git init) darin,
damit `git mv` real getestet wird statt nur simuliert. Keine echten
Netz-/gh-Calls.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "adr_allocate.py"
_spec = importlib.util.spec_from_file_location("adr_allocate", _SCRIPT)
aa = importlib.util.module_from_spec(_spec)
sys.modules["adr_allocate"] = aa
_spec.loader.exec_module(aa)


def _init_repo(tmp_path: Path) -> Path:
    """Initialisiert ein Wegwerf-git-Repo mit docs/adr/ darunter, gibt adr_dir zurueck."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    return adr_dir


def _commit_all(tmp_path: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)


_DRAFT_TEMPLATE = """\
---
id: ADR-000
status: proposed
---

# ADR-DRAFT: {title}

<!-- ADR-DRAFT — Platzhalter, Nummer faellt beim Merge (ADR-228). -->

Body referenziert sich selbst als ADR-DRAFT-{slug}.md.
"""


def _write_draft(adr_dir: Path, slug: str, title: str) -> Path:
    f = adr_dir / f"ADR-DRAFT-{slug}.md"
    f.write_text(_DRAFT_TEMPLATE.format(title=title, slug=slug), encoding="utf-8")
    return f


def _write_numbered(adr_dir: Path, number: int, slug: str) -> Path:
    f = adr_dir / f"ADR-{number:03d}-{slug}.md"
    f.write_text(
        f"---\nstatus: accepted\n---\n\n# ADR-{number:03d}: {slug}\n",
        encoding="utf-8",
    )
    return f


# --- find_drafts -------------------------------------------------------------


def test_should_find_no_drafts_in_empty_dir(tmp_path):
    adr_dir = _init_repo(tmp_path)
    assert aa.find_drafts(adr_dir) == []


def test_should_find_drafts_sorted_by_slug(tmp_path):
    adr_dir = _init_repo(tmp_path)
    _write_draft(adr_dir, "zeta-thing", "Zeta")
    _write_draft(adr_dir, "alpha-thing", "Alpha")

    names = [p.name for p in aa.find_drafts(adr_dir)]
    assert names == ["ADR-DRAFT-alpha-thing.md", "ADR-DRAFT-zeta-thing.md"]


# --- Trockenlauf ---------------------------------------------------------


def test_should_write_nothing_on_dry_run(tmp_path):
    adr_dir = _init_repo(tmp_path)
    draft = _write_draft(adr_dir, "my-decision", "My Decision")
    _commit_all(tmp_path)
    before = draft.read_text(encoding="utf-8")

    results = aa.allocate_drafts(adr_dir, apply=False)

    assert len(results) == 1
    assert results[0].number == 1
    # Datei liegt unveraendert und unter altem Namen weiter vor
    assert draft.exists()
    assert draft.read_text(encoding="utf-8") == before
    assert not (adr_dir / "ADR-001-my-decision.md").exists()


def test_should_exit_zero_with_no_change_when_no_drafts(tmp_path, capsys):
    adr_dir = _init_repo(tmp_path)
    _write_numbered(adr_dir, 1, "existing-thing")
    _commit_all(tmp_path)

    orig_argv = sys.argv
    try:
        sys.argv = ["adr_allocate.py", "--adr-dir", str(adr_dir)]
        rc = aa.main()
    finally:
        sys.argv = orig_argv

    assert rc == 0
    out = capsys.readouterr().out
    assert "nichts zu tun" in out
    # nichts im Verzeichnis veraendert
    assert {p.name for p in adr_dir.glob("*.md")} == {"ADR-001-existing-thing.md"}


# --- --apply: Umbenennung, id, H1, Selbstverweise ----------------------------


def test_should_rename_set_id_h1_and_self_refs_on_apply(tmp_path):
    adr_dir = _init_repo(tmp_path)
    draft = _write_draft(adr_dir, "my-decision", "My Decision")
    _commit_all(tmp_path)

    results = aa.allocate_drafts(adr_dir, apply=True)

    assert len(results) == 1
    r = results[0]
    assert r.number == 1
    new_path = adr_dir / "ADR-001-my-decision.md"
    assert new_path.exists()
    assert not draft.exists()

    text = new_path.read_text(encoding="utf-8")
    assert "id: ADR-001" in text
    assert "id: ADR-000" not in text
    assert "# ADR-001: My Decision" in text
    assert "ADR-DRAFT" not in text  # auch der Selbstverweis im Kommentar/Body ist weg
    assert "ADR-001-my-decision.md" in text  # Selbstverweis korrekt umgeschrieben

    # git mv hat die Historie mitgenommen (Datei ist im Index als rename/tracked)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "ADR-001-my-decision.md" in status


def test_should_give_two_drafts_two_different_numbers(tmp_path):
    adr_dir = _init_repo(tmp_path)
    _write_draft(adr_dir, "first-thing", "First Thing")
    _write_draft(adr_dir, "second-thing", "Second Thing")
    _commit_all(tmp_path)

    results = aa.allocate_drafts(adr_dir, apply=True)

    numbers = sorted(r.number for r in results)
    assert len(results) == 2
    assert numbers == [1, 2]
    assert (adr_dir / "ADR-001-first-thing.md").exists()
    assert (adr_dir / "ADR-002-second-thing.md").exists()


def test_should_allocate_a_number_that_is_really_free(tmp_path):
    """Belegte Nummer im selben Verzeichnis darf nicht erneut vergeben werden."""
    adr_dir = _init_repo(tmp_path)
    _write_numbered(adr_dir, 1, "already-taken")
    _write_draft(adr_dir, "new-thing", "New Thing")
    _commit_all(tmp_path)

    results = aa.allocate_drafts(adr_dir, apply=True)

    assert len(results) == 1
    assert results[0].number == 2  # nicht 1 — das ist schon belegt
    assert (adr_dir / "ADR-002-new-thing.md").exists()


def test_should_process_drafts_in_deterministic_slug_order(tmp_path):
    adr_dir = _init_repo(tmp_path)
    _write_draft(adr_dir, "zeta-thing", "Zeta")
    _write_draft(adr_dir, "alpha-thing", "Alpha")
    _commit_all(tmp_path)

    results = aa.allocate_drafts(adr_dir, apply=True)

    by_slug = {r.slug: r.number for r in results}
    assert by_slug["alpha-thing"] < by_slug["zeta-thing"]
