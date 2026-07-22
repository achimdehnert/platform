"""Tests fuer tools/adr_evidence_paths.py — implementation_evidence-Pfad-Check (SUGGEST)."""

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "adr_evidence_paths",
    pathlib.Path(__file__).resolve().parents[1] / "adr_evidence_paths.py",
)
aep = importlib.util.module_from_spec(_SPEC)
sys.modules["adr_evidence_paths"] = aep  # noetig fuer @dataclass-Aufloesung
_SPEC.loader.exec_module(aep)


def _mk_repo(tmp_path, evidence_lines, *, extra_dirs=(), extra_files=()):
    """Mini-Repo: docs/adr/ADR-500 mit den gegebenen evidence-Eintraegen."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    for d in extra_dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    for f in extra_files:
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    body = "".join(f'  - "{line}"\n' for line in evidence_lines)
    (adr_dir / "ADR-500-test.md").write_text(
        "---\nstatus: accepted\nimplementation_status: implemented\n"
        f"implementation_evidence:\n{body}---\n\n# ADR-500\n\nBody.\n",
        encoding="utf-8",
    )
    return adr_dir


def test_should_report_dead_path_when_file_missing(tmp_path):
    adr_dir = _mk_repo(tmp_path, ["tools/gone.py: helper()"], extra_dirs=["tools"])
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1
    assert findings[0].category == "dead_path"
    assert findings[0].candidate == "tools/gone.py"


def test_should_report_archived_path_when_file_moved_to_archive(tmp_path):
    adr_dir = _mk_repo(
        tmp_path,
        ["packages/docs-agent/: generator"],
        extra_dirs=["packages"],
        extra_files=["_ARCHIVED/packages/docs-agent/main.py"],
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1
    assert findings[0].category == "archived_path"
    assert "_ARCHIVED" in findings[0].message


def test_should_pass_when_path_exists(tmp_path):
    adr_dir = _mk_repo(
        tmp_path, ["tools/live.py: helper()"], extra_files=["tools/live.py"]
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["checked"] == 1


def test_should_ignore_bare_filenames_without_directory(tmp_path):
    """Fallstrick 1 aus #1289: `tasks.py: sync_adrs` ist Prosa, kein aufloesbarer Pfad."""
    adr_dir = _mk_repo(tmp_path, ["tasks.py: sync_adrs (hourly), run_drift_detector"])
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["candidates"] == 0


def test_should_ignore_urls_and_domains(tmp_path):
    adr_dir = _mk_repo(
        tmp_path,
        [
            "Health: https://schutztat.de/healthz OK",
            "Prod schutztat.de/healthz OK (DB 0.6ms)",
        ],
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert findings == []


def test_should_skip_foreign_repo_root(tmp_path):
    """Fallstrick 2: `dev-hub/apps/portal/models.py` ist im platform-CI nicht aufloesbar.

    Je nach Verfuegbarkeit des Registry-Accessors faellt der Eintrag in
    skipped_cross_repo (dev-hub ist als Repo bekannt) oder skipped_unknown_root
    (Registry nicht lesbar → Regel 4 greift). Beides ist korrekt, entscheidend ist:
    kein Finding.
    """
    adr_dir = _mk_repo(tmp_path, ["dev-hub/apps/portal/models.py: AudienceConfig"])
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["skipped_cross_repo"] + stats["skipped_unknown_root"] == 1


def test_should_skip_unknown_root_without_registry(tmp_path, monkeypatch):
    """Regel 4 allein: `src/authoringfw/analysis/` hat kein Repo-Praefix und
    kein Top-Level-Pendant in platform."""
    monkeypatch.setattr(aep, "load_repo_names", lambda _root: set())
    adr_dir = _mk_repo(tmp_path, ["src/authoringfw/analysis/: StyleAnalysis"])
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["skipped_unknown_root"] == 1


def test_should_skip_partial_mirror_root(tmp_path):
    """orchestrator_mcp/ liegt in platform nur als Teilspiegel (ADR-256)."""
    adr_dir = _mk_repo(
        tmp_path,
        ["orchestrator_mcp/headless/: adapter"],
        extra_dirs=["orchestrator_mcp"],
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["skipped_partial_mirror"] == 1


def test_should_strip_platform_prefix_and_check_locally(tmp_path):
    adr_dir = _mk_repo(
        tmp_path, ["platform/tools/live.py: helper"], extra_files=["tools/live.py"]
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["checked"] == 1


def test_should_strip_trailing_suffix_before_existence_check(tmp_path):
    """Fallstrick 3: `cli.py: reference()` — Suffix muss vor dem Check weg."""
    adr_dir = _mk_repo(
        tmp_path, ["tools/cli.py: reference()"], extra_files=["tools/cli.py"]
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert findings == []


def test_should_resolve_adr_selfreference_without_filename(tmp_path):
    """`docs/adr/ADR-500` meint die Datei ADR-500-test.md — kein toter Pfad."""
    adr_dir = _mk_repo(tmp_path, ["platform/docs/adr/ADR-500 dokumentiert die Regel"])
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["checked"] == 1


def test_should_still_flag_adr_reference_without_matching_file(tmp_path):
    adr_dir = _mk_repo(tmp_path, ["platform/docs/adr/ADR-999 dokumentiert das"])
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1
    assert findings[0].category == "dead_path"


def test_should_expand_brace_lists(tmp_path):
    """`docs/gov/{a,b}.md` — ohne Expansion wuerde nur docs/gov/ geprueft."""
    adr_dir = _mk_repo(
        tmp_path,
        ["platform/docs/gov/{alive,gone}.md — Lookups"],
        extra_files=["docs/gov/alive.md"],
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1
    assert findings[0].candidate == "platform/docs/gov/gone.md"


def test_should_leave_entry_untouched_without_braces(tmp_path):
    assert aep.expand_braces("tools/a.py: helper") == ["tools/a.py: helper"]


def test_should_accept_entry_documenting_its_own_archival(tmp_path):
    """`X -> _ARCHIVED/X (Commit)` ist die gewuenschte Schreibweise, kein Defekt."""
    adr_dir = _mk_repo(
        tmp_path,
        [
            "TOT seit 2026-04-23 (2cc7289): packages/docs-agent/ -> _ARCHIVED/packages/docs-agent/"
        ],
        extra_dirs=["packages"],
        extra_files=["_ARCHIVED/packages/docs-agent/cli.py"],
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["documented_archival"] == 1


def test_should_still_flag_when_archive_target_does_not_exist(tmp_path):
    """Ein _ARCHIVED-Verweis ins Leere darf den Eintrag NICHT freistellen."""
    adr_dir = _mk_repo(
        tmp_path,
        ["packages/gone/ -> _ARCHIVED/packages/gone/"],
        extra_dirs=["packages"],
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings
    assert stats["documented_archival"] == 0


def test_should_accept_documented_removal_with_commit(tmp_path):
    """Geloescht statt archiviert: Marker-Wort + Commit-Hash ist der Beleg."""
    adr_dir = _mk_repo(
        tmp_path,
        ["packages/platform-search/ am 2026-03-25 als Orphan zurueckgebaut (4cd39b4)"],
        extra_dirs=["packages"],
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["documented_archival"] == 1


def test_should_flag_removal_marker_without_commit_hash(tmp_path):
    """Ein Marker-Wort allein ist kein Beleg — der Commit fehlt."""
    adr_dir = _mk_repo(
        tmp_path,
        ["packages/platform-search/ wurde zurueckgebaut"],
        extra_dirs=["packages"],
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1


def test_should_respect_ignore_file(tmp_path):
    adr_dir = _mk_repo(tmp_path, ["tools/gone.py: helper"], extra_dirs=["tools"])
    (adr_dir / ".adr-evidence-ignore").write_text(
        "# Kommentar\n\ntools/gone.py in ADR-500\n", encoding="utf-8"
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["ignored"] == 1


def test_should_report_correct_line_number(tmp_path):
    adr_dir = _mk_repo(
        tmp_path, ["tools/a.py: ok", "tools/gone.py: weg"], extra_files=["tools/a.py"]
    )
    findings, _ = aep.run(adr_dir, tmp_path)
    assert len(findings) == 1
    # Zeile 1 "---", 2 status, 3 implementation_status, 4 implementation_evidence,
    # 5 erster Eintrag, 6 zweiter Eintrag.
    assert findings[0].line == 6


def test_should_exit_zero_in_suggest_mode_despite_findings(tmp_path, monkeypatch):
    _mk_repo(tmp_path, ["tools/gone.py: helper"], extra_dirs=["tools"])
    monkeypatch.chdir(tmp_path)
    assert aep.main(["--adr-dir", "docs/adr", "--format", "github"]) == 0


def test_should_exit_one_with_gate_flag(tmp_path, monkeypatch):
    _mk_repo(tmp_path, ["tools/gone.py: helper"], extra_dirs=["tools"])
    monkeypatch.chdir(tmp_path)
    assert aep.main(["--adr-dir", "docs/adr", "--gate"]) == 1


def test_should_handle_adr_without_evidence_block(tmp_path):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-501-nofm.md").write_text(
        "---\nstatus: accepted\n---\n\n# ADR-501\n", encoding="utf-8"
    )
    findings, stats = aep.run(adr_dir, tmp_path)
    assert findings == []
    assert stats["adrs_with_evidence"] == 0
