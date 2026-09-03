"""Tests fuer tools/welle_security_notices.py (platform#2787, Zug A).

Synthetische Fixtures, KEIN Netz — PyPI-Abfragen laufen ueber eine injizierbare
PypiLookup mit fest verdrahtetem fetcher.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import welle_security_notices as wsn  # noqa: E402


TEMPLATE_TEXT = """# Sicherheitshinweise

{{MELDEWEG}}

Stand: {{DEFAULT_BRANCH}}{{RELEASE_HINWEIS}}
"""


# --------------------------------------------------------------------------
# normalize_name
# --------------------------------------------------------------------------


def test_should_normalize_name_per_pep503():
    assert wsn.normalize_name("Django_Extensions") == "django-extensions"
    assert wsn.normalize_name("psycopg.binary") == "psycopg-binary"
    assert wsn.normalize_name("Flask") == "flask"


# --------------------------------------------------------------------------
# Manifest-Parser
# --------------------------------------------------------------------------


def test_should_parse_extras_and_version_spec():
    req = wsn.parse_requirement_line("psycopg[binary]==3.3.3", "requirements.txt")
    assert req is not None
    assert req.name == "psycopg"
    assert req.extras == "[binary]"
    assert req.spec == "==3.3.3"


def test_should_keep_marker_verbatim_in_spec():
    req = wsn.parse_requirement_line(
        'requests>=2.31,<3; python_version >= "3.9"', "requirements.txt"
    )
    assert req is not None
    assert req.name == "requests"
    assert req.spec == '>=2.31,<3; python_version >= "3.9"'


def test_should_skip_comments_options_editable_and_local_paths(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "# Kommentar",
                "flask==3.0.0  # inline Kommentar",
                "-i https://pypi.org/simple",
                "--extra-index-url https://example.invalid/simple",
                "-e .",
                "./local-lib",
                "git+https://example.invalid/repo.git",
                "",
                "requests>=2.31",
            ]
        ),
        encoding="utf-8",
    )
    reqs = wsn.parse_requirements_file(tmp_path / "requirements.txt", tmp_path)
    names = {r.name for r in reqs}
    assert names == {"flask", "requests"}
    flask_req = next(r for r in reqs if r.name == "flask")
    assert flask_req.spec == "==3.0.0"


def test_should_resolve_dash_r_includes_recursively(tmp_path: Path):
    (tmp_path / "requirements-base.txt").write_text("click==8.1.7\n", encoding="utf-8")
    (tmp_path / "requirements-dev.txt").write_text(
        "-r requirements-base.txt\npytest==8.0.0\n", encoding="utf-8"
    )
    (tmp_path / "requirements.txt").write_text(
        "-r requirements-dev.txt\nflask==3.0.0\n", encoding="utf-8"
    )
    reqs = wsn.parse_requirements_file(tmp_path / "requirements.txt", tmp_path)
    by_name = {r.name: r for r in reqs}
    assert set(by_name) == {"click", "pytest", "flask"}
    assert by_name["click"].source == "requirements-base.txt"
    assert by_name["pytest"].source == "requirements-dev.txt"
    assert by_name["flask"].source == "requirements.txt"


def test_should_not_loop_forever_on_circular_includes(tmp_path: Path):
    (tmp_path / "a.txt").write_text("-r b.txt\nflask==3.0.0\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("-r a.txt\nrequests==2.31.0\n", encoding="utf-8")
    reqs = wsn.parse_requirements_file(tmp_path / "a.txt", tmp_path)
    names = {r.name for r in reqs}
    assert names == {"flask", "requests"}


def test_should_parse_pyproject_dependencies_and_optional(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo"
dependencies = [
    "requests>=2.31",
    "psycopg[binary]==3.3.3",
]

[project.optional-dependencies]
dev = ["pytest==8.0.0", "ruff==0.16.5"]
""",
        encoding="utf-8",
    )
    reqs = wsn.parse_pyproject(tmp_path / "pyproject.toml")
    names = {r.name for r in reqs}
    assert names == {"requests", "psycopg", "pytest", "ruff"}
    assert all(r.source == "pyproject.toml" for r in reqs)


def test_should_report_no_manifest_files_when_absent(tmp_path: Path):
    reqs, files = wsn.collect_requirements(tmp_path)
    assert reqs == []
    assert files == []


# --------------------------------------------------------------------------
# Lizenz-Aufloesung
# --------------------------------------------------------------------------


def test_should_prefer_license_expression():
    info = {"license_expression": "MIT", "license": "a very long license text " * 5}
    assert wsn.resolve_license(info) == "MIT"


def test_should_fall_back_to_short_license_field():
    info = {"license_expression": None, "license": "BSD-3-Clause"}
    assert wsn.resolve_license(info) == "BSD-3-Clause"


def test_should_ignore_long_license_field_and_use_classifier():
    long_license = (
        "This is a full license text " * 10
    )  # > 60 chars, no license_expression
    info = {
        "license_expression": None,
        "license": long_license,
        "classifiers": ["License :: OSI Approved :: MIT License"],
    }
    assert wsn.resolve_license(info) == "MIT License"


def test_should_default_to_unbekannt_without_any_signal():
    info = {"license_expression": None, "license": None, "classifiers": []}
    assert wsn.resolve_license(info) == "unbekannt"


def test_should_mark_not_on_pypi_when_info_is_none():
    assert wsn.resolve_license(None) == "nicht auf PyPI"
    assert (
        wsn.resolve_url("iil-secret-pkg", None)
        == "https://pypi.org/project/iil-secret-pkg/"
    )


def test_should_use_direct_url_as_project_for_url_requirements():
    spec = "@ git+https://github.com/example/mono.git#subdirectory=packages/core"
    assert wsn.resolve_url("core", None, spec) == spec[2:]
    assert (
        wsn.resolve_url("core", None, spec + " ; python_version >= '3.12'") == spec[2:]
    )


def test_should_resolve_url_precedence():
    info = {
        "project_urls": {
            "Homepage": "https://home.example",
            "Source": "https://src.example",
        },
    }
    assert wsn.resolve_url("pkg", info) == "https://home.example"
    info2 = {"project_urls": {"Source": "https://src.example"}}
    assert wsn.resolve_url("pkg", info2) == "https://src.example"
    info3 = {"project_urls": {}, "home_page": "https://homepage.example"}
    assert wsn.resolve_url("pkg", info3) == "https://homepage.example"
    info4 = {"project_urls": {}}
    assert wsn.resolve_url("pkg", info4) == "https://pypi.org/project/pkg/"


# --------------------------------------------------------------------------
# Determinismus (K2)
# --------------------------------------------------------------------------


def _fake_fetcher(raw_name: str) -> dict | None:
    fixtures = {
        "flask": {
            "license_expression": None,
            "license": "BSD-3-Clause",
            "classifiers": [],
            "project_urls": {"Homepage": "https://flask.palletsprojects.com"},
            "home_page": None,
        },
        "iil-internal-pkg": None,  # nicht auf PyPI
    }
    return fixtures.get(wsn.normalize_name(raw_name))


def test_should_produce_identical_output_across_two_runs(tmp_path: Path):
    requirements = [
        wsn.Requirement("flask", "flask", "", "==3.0.0", "requirements.txt"),
        wsn.Requirement(
            "iil-internal-pkg", "iil-internal-pkg", "", "==1.0.0", "requirements.txt"
        ),
    ]
    cache_dir = tmp_path / "cache"
    lookup1 = wsn.PypiLookup(cache_dir=cache_dir, fetcher=_fake_fetcher)
    table1 = wsn.build_notices_table(requirements, ["requirements.txt"], lookup1)

    # Zweiter Lauf: Cache existiert bereits, Fetcher wuerde bei Aufruf einen Fehler werfen.
    def _boom(_name: str):
        raise AssertionError("Fetcher haette aus dem Cache bedient werden muessen")

    lookup2 = wsn.PypiLookup(cache_dir=cache_dir, fetcher=_boom)
    table2 = wsn.build_notices_table(requirements, ["requirements.txt"], lookup2)

    assert table1 == table2
    assert "generated_at" not in table1
    assert "iil-internal-pkg" in table1
    assert "nicht auf PyPI" in table1
    assert "flask" in table1
    assert "BSD-3-Clause" in table1


def test_should_dedupe_exact_duplicate_requirements():
    requirements = [
        wsn.Requirement("flask", "flask", "", "==3.0.0", "requirements.txt"),
        wsn.Requirement("flask", "flask", "", "==3.0.0", "requirements.txt"),
    ]
    lookup = wsn.PypiLookup(fetcher=_fake_fetcher)
    table = wsn.build_notices_table(requirements, ["requirements.txt"], lookup)
    assert table.count("| flask |") == 1


# --------------------------------------------------------------------------
# SECURITY.md — Meldeweg je PVR-Zustand (K1)
# --------------------------------------------------------------------------


def test_should_use_pvr_text_when_enabled():
    text = wsn.meldeweg_text("achimdehnert", pvr_enabled=True)
    assert "Private vulnerability reporting" in text
    assert "@" not in text  # keine erfundene Kontaktadresse
    assert "Stunden" not in text and "Tage" not in text  # keine Reaktionszeit-Zusage


def test_should_use_owner_and_label_text_when_pvr_disabled():
    text = wsn.meldeweg_text("achimdehnert", pvr_enabled=False)
    assert "achimdehnert" in text
    assert "`security`" in text
    assert "@" not in text


def test_should_render_release_hinweis_only_with_tags():
    assert wsn.determine_release_hinweis(True) == wsn.RELEASE_HINWEIS_TEXT
    assert wsn.determine_release_hinweis(False) == ""


def test_should_render_security_md_with_placeholders_filled():
    rendered = wsn.render_security_md(
        TEMPLATE_TEXT,
        owner="achimdehnert",
        pvr_enabled=True,
        default_branch="main",
        release_hinweis=wsn.RELEASE_HINWEIS_TEXT,
    )
    assert "{{" not in rendered
    assert "Private vulnerability reporting" in rendered
    assert "Stand: main und auf die jeweils letzte veröffentlichte Version" in rendered


# --------------------------------------------------------------------------
# CLI/run — existierende SECURITY.md bleibt unangetastet
# --------------------------------------------------------------------------


def test_should_not_overwrite_existing_security_md(tmp_path: Path, monkeypatch, capsys):
    template_path = tmp_path / "SECURITY.template.md"
    template_path.write_text(TEMPLATE_TEXT, encoding="utf-8")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    existing = "# Eigene SECURITY.md\n\nBleibt so.\n"
    (workdir / "SECURITY.md").write_text(existing, encoding="utf-8")
    (workdir / "requirements.txt").write_text("flask==3.0.0\n", encoding="utf-8")

    monkeypatch.setattr(wsn, "fetch_repo_meta", lambda repo: {"default_branch": "main"})
    monkeypatch.setattr(wsn, "fetch_pvr_enabled", lambda repo: True)
    monkeypatch.setattr(wsn, "fetch_has_version_tags", lambda wd: False)
    real_pypi_lookup = wsn.PypiLookup
    monkeypatch.setattr(
        wsn,
        "PypiLookup",
        lambda cache_dir=None: real_pypi_lookup(fetcher=_fake_fetcher),
    )

    exit_code = wsn.run(
        "achimdehnert/demo", workdir, template_path, None, dry_run=False
    )

    assert exit_code == 0
    assert (workdir / "SECURITY.md").read_text(encoding="utf-8") == existing
    out = capsys.readouterr().out
    assert "existiert bereits" in out
    assert (workdir / "THIRD_PARTY_NOTICES.md").exists()


def test_should_report_and_write_nothing_on_dry_run_without_manifest(
    tmp_path: Path, monkeypatch, capsys
):
    template_path = tmp_path / "SECURITY.template.md"
    template_path.write_text(TEMPLATE_TEXT, encoding="utf-8")

    workdir = tmp_path / "repo"
    workdir.mkdir()

    monkeypatch.setattr(wsn, "fetch_repo_meta", lambda repo: {"default_branch": "main"})
    monkeypatch.setattr(wsn, "fetch_pvr_enabled", lambda repo: False)
    monkeypatch.setattr(wsn, "fetch_has_version_tags", lambda wd: False)

    exit_code = wsn.run("achimdehnert/demo", workdir, template_path, None, dry_run=True)

    assert exit_code == 0
    assert not (workdir / "SECURITY.md").exists()
    assert not (workdir / "THIRD_PARTY_NOTICES.md").exists()
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "Kein Abhängigkeits-Manifest" in out
