"""Tests fuer tools/adr_citation_lint.py — ADR-Body-Zitate-Lint (SUGGEST)."""

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "adr_citation_lint",
    pathlib.Path(__file__).resolve().parents[1] / "adr_citation_lint.py",
)
acl = importlib.util.module_from_spec(_SPEC)
sys.modules["adr_citation_lint"] = acl  # noetig fuer @dataclass-Aufloesung
_SPEC.loader.exec_module(acl)


def _mk_corpus(tmp_path):
    """Mini-Korpus: 2 aktive ADRs, 1 archive/, 1 _archive/superseded/."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "archive").mkdir()
    (adr_dir / "_archive" / "superseded").mkdir(parents=True)

    (adr_dir / "ADR-100-foo-service.md").write_text(
        "---\nstatus: accepted\n---\n\n# ADR-100 Foo\n\nBody.\n", encoding="utf-8"
    )
    (adr_dir / "ADR-101-bar-pattern.md").write_text(
        "---\nstatus: accepted\n---\n\n# ADR-101 Bar\n\nBody.\n", encoding="utf-8"
    )
    (adr_dir / "archive" / "ADR-050-old-thing.md").write_text(
        "---\nstatus: superseded\n---\n\n# ADR-050 Old\n", encoding="utf-8"
    )
    (adr_dir / "_archive" / "superseded" / "ADR-040-ancient.md").write_text(
        "# ADR-040 Ancient\n", encoding="utf-8"
    )
    return adr_dir


def _lint(tmp_path, body):
    """Schreibt body in ADR-100 und lintet den Korpus."""
    adr_dir = _mk_corpus(tmp_path)
    (adr_dir / "ADR-100-foo-service.md").write_text(body, encoding="utf-8")
    return acl.run(adr_dir, tmp_path)


def test_should_pass_clean_reference_to_active_adr(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nSiehe ADR-101 und [ADR-101](ADR-101-bar-pattern.md).\n")
    assert findings == []


def test_should_skip_self_reference(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nDieses ADR-100 referenziert sich selbst.\n")
    assert findings == []


def test_should_flag_dead_ref_with_archive_hint(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nBasiert auf ADR-050.\n")
    assert len(findings) == 1
    f = findings[0]
    assert f.category == "dead_ref"
    assert "ADR-050" in f.message
    assert "archive" in f.message  # Archiv-Pfad als Hinweis
    assert f.line == 3


def test_should_flag_dead_ref_for_nonexistent_number(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nSiehe ADR-999.\n")
    assert [f.category for f in findings] == ["dead_ref"]
    assert "weder aktiv noch archiviert" in findings[0].message


def test_should_flag_stale_filename_link_slug(tmp_path):
    findings = _lint(
        tmp_path, "# ADR-100\n\nSiehe [ADR-101](ADR-101-wrong-old-slug.md).\n"
    )
    assert [f.category for f in findings] == ["stale_filename"]
    assert "ADR-101-bar-pattern.md" in findings[0].message


def test_should_flag_external_target_outside_adr_dir(tmp_path):
    findings = _lint(
        tmp_path,
        "# ADR-100\n\nSiehe [ADR-160](../../mcp-hub/docs/ADR-160-standardized-hub-deployment.md).\n",
    )
    assert [f.category for f in findings] == ["external_target"]
    assert "mcp-hub" in findings[0].message


def test_should_not_flag_non_adr_links(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nSiehe [Readme](../../README.md).\n")
    assert findings == []


def test_should_honor_inline_ignore_marker(tmp_path):
    body = (
        "# ADR-100\n\n"
        "<!-- adr-lint: ignore-next-line -->\n"
        "Bekannter Alt-Fund: ADR-050.\n"
        "Aber dieser hier zaehlt: ADR-999.\n"
    )
    findings = _lint(tmp_path, body)
    assert len(findings) == 1
    assert "ADR-999" in findings[0].message


def test_should_honor_ignore_file(tmp_path):
    adr_dir = _mk_corpus(tmp_path)
    (adr_dir / "ADR-100-foo-service.md").write_text(
        "# ADR-100\n\nSiehe ADR-050 und ADR-999.\n", encoding="utf-8"
    )
    (adr_dir / ".adr-lint-ignore").write_text(
        "# geparkte Alt-Funde\nADR-050 in ADR-100\n", encoding="utf-8"
    )
    findings = acl.run(adr_dir, tmp_path)
    assert len(findings) == 1
    assert "ADR-999" in findings[0].message


def test_should_check_link_text_numbers_for_url_targets(tmp_path):
    findings = _lint(
        tmp_path,
        "# ADR-100\n\nSiehe [ADR-999](https://github.com/x/y/blob/main/docs/adr/INDEX.md).\n",
    )
    assert [f.category for f in findings] == ["dead_ref"]


def test_should_dedupe_same_finding_per_line(tmp_path):
    findings = _lint(tmp_path, "# ADR-100\n\nADR-999 und nochmal ADR-999.\n")
    assert len(findings) == 1


def test_should_exit_zero_in_suggest_mode_despite_findings(tmp_path, monkeypatch, capsys):
    adr_dir = _mk_corpus(tmp_path)
    (adr_dir / "ADR-100-foo-service.md").write_text(
        "# ADR-100\n\nSiehe ADR-999.\n", encoding="utf-8"
    )
    rc = acl.main(["--adr-dir", str(adr_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dead_ref=1" in out


def test_should_exit_one_with_gate_flag_on_findings(tmp_path, capsys):
    adr_dir = _mk_corpus(tmp_path)
    (adr_dir / "ADR-100-foo-service.md").write_text(
        "# ADR-100\n\nSiehe ADR-999.\n", encoding="utf-8"
    )
    assert acl.main(["--adr-dir", str(adr_dir), "--gate"]) == 1


def test_should_emit_github_annotations(tmp_path, capsys):
    adr_dir = _mk_corpus(tmp_path)
    (adr_dir / "ADR-100-foo-service.md").write_text(
        "# ADR-100\n\nSiehe ADR-999.\n", encoding="utf-8"
    )
    rc = acl.main(["--adr-dir", str(adr_dir), "--format", "github"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "::warning file=" in out
    assert "title=adr-citation-lint dead_ref" in out
    assert "::warning title=adr-citation-lint summary" in out
