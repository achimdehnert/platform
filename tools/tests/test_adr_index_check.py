"""Tests fuer tools/adr_index_check.py — INDEX.md ↔ Dateibestand-Konsistenz (SUGGEST)."""

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "adr_index_check",
    pathlib.Path(__file__).resolve().parents[1] / "adr_index_check.py",
)
aic = importlib.util.module_from_spec(_SPEC)
sys.modules["adr_index_check"] = aic  # noetig fuer @dataclass-Aufloesung
_SPEC.loader.exec_module(aic)

_TABLE_HEADER = "| # | Title | Status | Impl | Link |\n|---|-------|--------|------|------|\n"


def _mk_corpus(tmp_path):
    """Mini-Korpus: 2 aktive ADRs, 1 archive/, 1 _archive/superseded/."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "archive").mkdir()
    (adr_dir / "_archive" / "superseded").mkdir(parents=True)

    (adr_dir / "ADR-100-foo-service.md").write_text(
        "---\nstatus: accepted\n---\n\n# ADR-100 Foo\n", encoding="utf-8"
    )
    (adr_dir / "ADR-101-bar-pattern.md").write_text(
        "---\nstatus: proposed\n---\n\n# ADR-101 Bar\n", encoding="utf-8"
    )
    (adr_dir / "archive" / "ADR-050-old-thing.md").write_text(
        "---\nstatus: superseded\n---\n\n# ADR-050 Old\n", encoding="utf-8"
    )
    (adr_dir / "_archive" / "superseded" / "ADR-040-ancient.md").write_text(
        "# ADR-040 Ancient (kein Frontmatter)\n", encoding="utf-8"
    )
    return adr_dir


def _write_index(adr_dir, rows, next_free=102):
    (adr_dir / "INDEX.md").write_text(
        f"# Index\n\n> **Next free ADR number:** {next_free}\n\n"
        + _TABLE_HEADER
        + "".join(rows),
        encoding="utf-8",
    )


_ROW_040 = "| 040 | Ancient | `Archived` | — | [ADR-040](_archive/superseded/ADR-040-ancient.md) |\n"
_ROW_050 = "| 050 | Old Thing | `Superseded` | — | [ADR-050](archive/ADR-050-old-thing.md) |\n"
_ROW_100 = "| 100 | Foo Service | `Accepted` | ✅ | [ADR-100](ADR-100-foo-service.md) |\n"
_ROW_101 = "| 101 | Bar Pattern | `Proposed` | ⬜ | [ADR-101](ADR-101-bar-pattern.md) |\n"


def test_should_pass_consistent_index(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, _ROW_101], next_free=102)
    assert aic.run(adr_dir, tmp_path) == []


def test_should_flag_missing_row_for_active_file(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100], next_free=102)  # 101 fehlt
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["missing_row"]
    assert "ADR-101" in findings[0].message


def test_should_flag_ghost_row_without_any_file(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    ghost = "| 666 | Phantom | `Accepted` | ✅ | [ADR-666](ADR-666-phantom.md) |\n"
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, _ROW_101, ghost], next_free=102)
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["ghost_row"]
    assert "ADR-666" in findings[0].message


def test_should_flag_status_drift_case_insensitive(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    drifted = "| 101 | Bar Pattern | `Accepted` | ⬜ | [ADR-101](ADR-101-bar-pattern.md) |\n"
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, drifted], next_free=102)
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["status_drift"]
    assert "'accepted'" in findings[0].message and "'proposed'" in findings[0].message


def test_should_accept_archived_status_for_underscore_archive_file(tmp_path):
    # INDEX `Archived` matcht _archive/ — auch ohne Frontmatter-Status (Zeile _ROW_040)
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, _ROW_101], next_free=102)
    assert [f for f in aic.run(adr_dir, tmp_path) if f.category == "status_drift"] == []


def test_should_flag_archived_status_when_file_is_active(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    wrong = "| 100 | Foo Service | `Archived` | — | [ADR-100](ADR-100-foo-service.md) |\n"
    _write_index(adr_dir, [_ROW_040, _ROW_050, wrong, _ROW_101], next_free=102)
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["status_drift"]
    assert "aktive Datei existiert" in findings[0].message


def test_should_flag_broken_link_target(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    broken = "| 100 | Foo Service | `Accepted` | ✅ | [ADR-100](ADR-100-renamed-elsewhere.md) |\n"
    _write_index(adr_dir, [_ROW_040, _ROW_050, broken, _ROW_101], next_free=102)
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["broken_link"]
    assert "ADR-100-renamed-elsewhere.md" in findings[0].message


def test_should_flag_stale_next_free_number(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, _ROW_101], next_free=99)
    findings = aic.run(adr_dir, tmp_path)
    assert [f.category for f in findings] == ["stale_next_free"]
    assert "Soll: 102" in findings[0].message


def test_should_exit_zero_in_suggest_mode_despite_findings(tmp_path, capsys):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100], next_free=99)
    rc = aic.main(["--adr-dir", str(adr_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "missing_row=1" in out and "stale_next_free=1" in out


def test_should_exit_one_with_gate_flag_on_findings(tmp_path, capsys):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100], next_free=99)
    assert aic.main(["--adr-dir", str(adr_dir), "--gate"]) == 1


def test_should_emit_github_annotations(tmp_path, capsys):
    adr_dir = _mk_corpus(tmp_path)
    _write_index(adr_dir, [_ROW_040, _ROW_050, _ROW_100, _ROW_101], next_free=99)
    rc = aic.main(["--adr-dir", str(adr_dir), "--format", "github"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "::warning file=" in out
    assert "title=adr-index-check stale_next_free" in out
    assert "::warning title=adr-index-check summary" in out
