"""Tests fuer tools/adr_draft_guard.py — Gate: Entwurf darf main nie erreichen (ADR-228).

Beide Richtungen geprueft (rot UND gruen), synthetische ADR-Verzeichnisse in
tmp_path, keine echten Netz-/gh-Calls.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "adr_draft_guard.py"
_spec = importlib.util.spec_from_file_location("adr_draft_guard", _SCRIPT)
adg = importlib.util.module_from_spec(_spec)
sys.modules["adr_draft_guard"] = adg
_spec.loader.exec_module(adg)


def _mk_adr_dir(tmp_path: Path) -> Path:
    d = tmp_path / "docs" / "adr"
    d.mkdir(parents=True)
    return d


def _clean_adr(adr_dir: Path, number: int, slug: str) -> Path:
    f = adr_dir / f"ADR-{number:03d}-{slug}.md"
    f.write_text(
        f"---\nid: ADR-{number:03d}\nstatus: accepted\n---\n\n# ADR-{number:03d}: x\n",
        encoding="utf-8",
    )
    return f


# --- rot: Entwurfsdatei vorhanden --------------------------------------------


def test_should_find_draft_file_as_finding(tmp_path):
    adr_dir = _mk_adr_dir(tmp_path)
    (adr_dir / "ADR-DRAFT-my-thing.md").write_text(
        "---\nid: ADR-000\n---\n\n# ADR-DRAFT: My Thing\n", encoding="utf-8"
    )

    findings = adg.find_findings(adr_dir)

    assert len(findings) == 1
    assert "ADR-DRAFT-my-thing.md" in findings[0]


def test_should_exit_nonzero_with_gate_when_draft_present(tmp_path, capsys):
    adr_dir = _mk_adr_dir(tmp_path)
    (adr_dir / "ADR-DRAFT-my-thing.md").write_text(
        "---\nid: ADR-000\n---\n\n# ADR-DRAFT: My Thing\n", encoding="utf-8"
    )

    orig_argv = sys.argv
    try:
        sys.argv = ["adr_draft_guard.py", "--adr-dir", str(adr_dir), "--gate"]
        rc = adg.main()
    finally:
        sys.argv = orig_argv

    assert rc == 1
    out = capsys.readouterr().out
    assert "python3 tools/adr_allocate.py --apply" in out


# --- rot: id: ADR-000 liegen geblieben, auch unter numeriertem Dateinamen ----


def test_should_find_leftover_placeholder_id_in_numbered_file(tmp_path):
    adr_dir = _mk_adr_dir(tmp_path)
    (adr_dir / "ADR-001-half-migrated.md").write_text(
        "---\nid: ADR-000\nstatus: proposed\n---\n\n# ADR-001: Half Migrated\n",
        encoding="utf-8",
    )

    findings = adg.find_findings(adr_dir)

    assert len(findings) == 1
    assert "ADR-001-half-migrated.md" in findings[0]


def test_should_exit_nonzero_with_gate_when_placeholder_id_leftover(tmp_path):
    adr_dir = _mk_adr_dir(tmp_path)
    (adr_dir / "ADR-001-half-migrated.md").write_text(
        "---\nid: ADR-000\n---\n\n# ADR-001: x\n", encoding="utf-8"
    )

    orig_argv = sys.argv
    try:
        sys.argv = ["adr_draft_guard.py", "--adr-dir", str(adr_dir), "--gate"]
        rc = adg.main()
    finally:
        sys.argv = orig_argv

    assert rc == 1


# --- gruen: sauberer Baum -----------------------------------------------------


def test_should_find_no_findings_on_clean_tree(tmp_path):
    adr_dir = _mk_adr_dir(tmp_path)
    _clean_adr(adr_dir, 1, "first-thing")
    _clean_adr(adr_dir, 2, "second-thing")

    assert adg.find_findings(adr_dir) == []


def test_should_exit_zero_with_gate_on_clean_tree(tmp_path):
    adr_dir = _mk_adr_dir(tmp_path)
    _clean_adr(adr_dir, 1, "first-thing")

    orig_argv = sys.argv
    try:
        sys.argv = ["adr_draft_guard.py", "--adr-dir", str(adr_dir), "--gate"]
        rc = adg.main()
    finally:
        sys.argv = orig_argv

    assert rc == 0


# --- SUGGEST-Modus (kein --gate): niemals rot, auch bei Funden --------------


def test_should_exit_zero_without_gate_even_with_draft_present(tmp_path, capsys):
    adr_dir = _mk_adr_dir(tmp_path)
    (adr_dir / "ADR-DRAFT-wip.md").write_text(
        "---\nid: ADR-000\n---\n\n# ADR-DRAFT: WIP\n", encoding="utf-8"
    )

    orig_argv = sys.argv
    try:
        sys.argv = ["adr_draft_guard.py", "--adr-dir", str(adr_dir)]
        rc = adg.main()
    finally:
        sys.argv = orig_argv

    assert rc == 0
    out = capsys.readouterr().out
    assert "SUGGEST-Modus" in out


def test_should_gate_in_the_pull_request_run_not_only_on_push():
    """Das Tor muss VOR dem Merge greifen, nicht danach.

    Erste Fassung gatete nur beim `push` auf `main` — da ist der Entwurf aber
    schon gelandet; CI meldet dann nur noch, dass es passiert ist. Ohne
    Merge-Queue ist der PR-Lauf der einzige Hebel vor dem Merge.

    Geprueft wird der Workflow-Text selbst, weil die Bedingung dort steht und
    nicht im Skript: ein Skript-Test kann diesen Fehler nicht finden.
    """
    import pathlib

    wf = (
        pathlib.Path(__file__).resolve().parents[2]
        / ".github/workflows/adr-validate.yml"
    )
    text = wf.read_text(encoding="utf-8")
    block = text.split("ADR-Entwurf darf main nicht erreichen", 1)[1][:1200]

    # Gegenprobe zuerst: der Block muss ueberhaupt Bedingungen enthalten,
    # sonst belegt der Rest nichts.
    assert "--gate" in block
    assert "github.event_name" in block

    assert "pull_request" in block, (
        "PR-Lauf gatet nicht — Tor greift erst nach dem Merge"
    )
    assert "github.base_ref" in block, "PR-Lauf prueft das Ziel nicht"
    assert "refs/heads/main" in block, "push-Lauf auf main fehlt als Netz"
