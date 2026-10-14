"""Tests fuer tools/review_engine.py (KONZ-platform-070 Z2 Stufe 1, #3903 WP2).

Die Engine liest Regeln nur ueber review_regeln (K1) und wertet pfad/regex/umfang
gegen einen echten Git-Diff aus. Fixture: Mini-Repo mit zwei Commits.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review_engine as re_  # noqa: E402
import review_regeln as rr  # noqa: E402

REGELN = {
    "version": 1,
    "beschreibung": "Testregeln",
    "generiert": [],
    "reviewer_md": {
        "frontmatter": {"trigger": "manual"},
        "titel": "Test",
        "rolle": "t",
    },
    "regeln": [
        {
            "id": "RR-901",
            "titel": "Policies bleiben Mensch",
            "klasse": "BLOCK",
            "geltung": {"pfade": ["policies/*"], "profile": ["default", "deployed"]},
            "detektor": {"typ": "pfad", "muster": ["policies/*"]},
            "begruendung": {
                "quelle": "test",
                "text": "Policy-Aenderung braucht Mensch.",
            },
            "konsumenten": ["bot-tabu"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
        {
            "id": "RR-902",
            "titel": "Kein os.environ in Views",
            "klasse": "WARN",
            "geltung": {"pfade": ["*views.py"], "profile": ["default", "deployed"]},
            "detektor": {
                "typ": "regex",
                "ziel": "hinzugefuegt",
                "muster": [r"os\.environ"],
            },
            "begruendung": {"quelle": "test", "text": "Config via decouple."},
            "konsumenten": ["reviewer-md"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
        {
            "id": "RR-903",
            "titel": "Kein Klartext-Token",
            "klasse": "BLOCK",
            "geltung": {"pfade": ["*"], "profile": ["default", "deployed"]},
            "detektor": {
                "typ": "regex",
                "ziel": "inhalt",
                "muster": [r"ghp_[A-Za-z0-9]{10,}"],
            },
            "begruendung": {"quelle": "test", "text": "Secret im Code."},
            "konsumenten": ["reviewer-md"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
        {
            "id": "RR-904",
            "titel": "Minimal Diff",
            "klasse": "HINT",
            "geltung": {"pfade": ["*"], "profile": ["default", "deployed"]},
            "detektor": {"typ": "umfang", "max_zeilen": 3},
            "begruendung": {"quelle": "test", "text": "Grosse PRs aufteilen."},
            "ausgabe": {"kategorie": "Prinzip", "referenz": "P-004", "konfidenz": 0.7},
            "konsumenten": ["context-reviewer"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
        {
            "id": "RR-905",
            "titel": "Service-Layer",
            "klasse": "WARN",
            "geltung": {"pfade": ["*views.py"], "profile": ["default"]},
            "detektor": {"typ": "llm", "frage": "Businesslogik in der View?"},
            "begruendung": {"quelle": "test", "text": "Kette views → services."},
            "konsumenten": ["advocatus"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
        {
            "id": "RR-906",
            "titel": "Nur library",
            "klasse": "WARN",
            "geltung": {"pfade": ["*"], "profile": ["library"]},
            "detektor": {"typ": "pfad", "muster": ["*"]},
            "begruendung": {"quelle": "test", "text": "gilt nicht im Default-Profil."},
            "konsumenten": ["bot-tabu"],
            "seit": "2026-10-13",
            "praezision": None,
            "status": "aktiv",
        },
    ],
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, msg: str) -> str:
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-q",
        "-m",
        msg,
        "--allow-empty",
    )
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def regeln(tmp_path: Path) -> Path:
    p = tmp_path / "review-regeln.yaml"
    p.write_text(yaml.safe_dump(REGELN, allow_unicode=True), encoding="utf-8")
    assert rr.pruefe_schema(yaml.safe_load(p.read_text())) == []
    return p


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str, str]:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "app").mkdir()
    (r / "app" / "views.py").write_text("import os\n\n\ndef v():\n    return 1\n")
    (r / "policies").mkdir()
    (r / "policies" / "gates.md").write_text("# alt\n")
    (r / "README.md").write_text("hallo\n")
    basis = _commit(r, "basis")
    (r / "app" / "views.py").write_text(
        "import os\n\n\ndef v():\n    return os.environ['X']\n"
    )
    (r / "policies" / "gates.md").write_text("# neu\n")
    (r / "README.md").unlink()
    # Pseudo-Token zur Laufzeit zusammengesetzt, damit kein Secret-Scanner (gitleaks)
    # im Repo-Text anschlaegt — die Regel RR-903 trifft ihn trotzdem.
    (r / "token.txt").write_text("key = " + "ghp_" + "x" * 20 + "\n")
    kopf = _commit(r, "kopf")
    return r, basis, kopf


def _doc(regeln: Path) -> dict:
    return rr.lade_regeln(regeln)


def test_should_parse_added_lines_with_numbers_from_unified_diff():
    text = (
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
        "@@ -1,2 +1,3 @@\n-alt\n+neu1\n+neu2\n"
        "@@ -10 +11,2 @@\n+spaet\n"
        "diff --git a/w.py b/w.py\n--- a/w.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-weg\n"
    )
    d = re_.parse_unified_diff(text)
    assert d.hinzugefuegt["x.py"] == [(1, "neu1"), (2, "neu2"), (11, "spaet")]
    assert "w.py" not in d.hinzugefuegt
    assert d.geaenderte_zeilen == 5


def test_should_find_path_regex_and_size_findings(repo, regeln):
    r, basis, kopf = repo
    liste, kz = re_.befunde(r, basis, kopf, "default", _doc(regeln))
    ids = sorted((b.regel_id, b.locator) for b in liste)
    assert ("RR-901", "policies/gates.md") in ids
    assert ("RR-902", "app/views.py:5") in ids
    assert ("RR-903", "token.txt:1") in ids
    assert ("RR-904", re_.LOKATOR_PR) in ids
    assert kz["regeln_llm"] == 1 and kz["regeln_mechanisch"] == 4
    assert kz["dateien"] == 4  # README.md geloescht zaehlt als geaenderte Datei


def test_should_treat_path_block_as_human_review_not_as_failure(repo, regeln):
    r, basis, kopf = repo
    liste, _ = re_.befunde(r, basis, kopf, "default", _doc(regeln))
    policy = next(b for b in liste if b.regel_id == "RR-901")
    assert policy.mensch_noetig is True
    assert re_.annotation(policy).startswith(
        "::notice file=policies/gates.md,title=RR-901"
    )
    harte = re_.blockierende(liste)
    assert [b.regel_id for b in harte] == ["RR-903"]


def test_should_respect_profile_scope(repo, regeln):
    r, basis, kopf = repo
    liste, _ = re_.befunde(r, basis, kopf, "default", _doc(regeln))
    assert not any(b.regel_id == "RR-906" for b in liste)
    liste_lib, _ = re_.befunde(r, basis, kopf, "library", _doc(regeln))
    assert {b.regel_id for b in liste_lib} == {"RR-906"}


def test_should_render_annotation_with_file_and_line():
    b = re_.Befund(
        "RR-902", "WARN", "app/views.py:5", 1.0, "T", "Grund", "regex", False
    )
    assert (
        re_.annotation(b) == "::warning file=app/views.py,line=5,title=RR-902 T::Grund"
    )
    pr = re_.Befund("RR-904", "HINT", re_.LOKATOR_PR, 0.7, "T", "G", "umfang", False)
    assert re_.annotation(pr) == "::notice,title=RR-904 T::G"


def test_should_exit_nonzero_only_with_blockieren_switch(
    repo, regeln, tmp_path, capsys
):
    r, basis, kopf = repo
    out = tmp_path / "befunde.json"
    args = [
        "--repo-pfad",
        str(r),
        "--basis",
        basis,
        "--kopf",
        kopf,
        "--regeln",
        str(regeln),
        "--json",
        str(out),
        "--github",
    ]
    assert re_.main(args) == 0
    daten = json.loads(out.read_text())
    assert {b["regel_id"] for b in daten["befunde"]} == {
        "RR-901",
        "RR-902",
        "RR-903",
        "RR-904",
    }
    assert set(daten["befunde"][0]) >= {"regel_id", "klasse", "locator", "konfidenz"}
    assert "::error file=token.txt,line=1" in capsys.readouterr().out
    assert re_.main(args + ["--blockieren"]) == 1


def test_should_run_committed_rules_on_empty_diff_without_findings(repo):
    r, basis, _ = repo
    liste, kz = re_.befunde(r, basis, basis, "deployed")
    assert liste == []
    assert kz["regeln_mechanisch"] > 0
