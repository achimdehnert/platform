"""Tests fuer tools/sandbox/geheimnis_scan.py (platform#3685).

Die Faelle mit echtem gitleaks laufen nur, wo das Werkzeug installiert ist; der
Scan selbst ist fail-closed (Exit 2 ohne gitleaks), das prueft der letzte Test.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "geheimnis_scan.py"
_spec = importlib.util.spec_from_file_location("geheimnis_scan", _SCRIPT)
gs = importlib.util.module_from_spec(_spec)
sys.modules["geheimnis_scan"] = gs
_spec.loader.exec_module(gs)

mit_gitleaks = pytest.mark.skipif(
    shutil.which("gitleaks") is None, reason="gitleaks fehlt"
)


def _repo_mit_altlast(ziel: Path) -> Path:
    """Geheimnis nur in der Historie: eingecheckt, dann wieder geloescht."""
    gs.lege_kanarienrepo_an(ziel)
    git = ["git", "-C", str(ziel), "-c", "user.name=t", "-c", "user.email=t@t.invalid"]
    subprocess.run([*git, "rm", "-q", "konfig.py"], check=True)
    subprocess.run([*git, "commit", "-qm", "weg"], check=True)
    return ziel


def test_should_generate_a_fresh_canary_in_github_pat_shape():
    a, b = gs.kanarien_token(), gs.kanarien_token()
    assert a != b
    assert re.fullmatch(r"ghp_[A-Za-z0-9]{36}", a)


def test_should_keep_exceptions_one_fingerprint_per_line_with_comment_lines_only():
    for zeile in gs.AUSNAHMEN.read_text().splitlines():
        if zeile.startswith("#") or not zeile:
            continue
        assert "#" not in zeile, zeile
        assert re.fullmatch(r"[0-9a-f]{40}:[^:]+:[a-z0-9-]+:\d+", zeile), zeile


@mit_gitleaks
def test_should_find_a_secret_that_only_lives_in_history(tmp_path):
    funde = gs.scanne(_repo_mit_altlast(tmp_path / "r"), tmp_path / "b.json")
    assert [(f["regel"], f["datei"]) for f in funde] == [("github-pat", "konfig.py")]
    assert set(funde[0]) == {"regel", "datei", "zeile", "commit"}


@mit_gitleaks
def test_should_ignore_the_scanned_repos_own_gitleaks_allowlist(tmp_path):
    repo = _repo_mit_altlast(tmp_path / "r")
    (repo / ".gitleaks.toml").write_text('[allowlist]\npaths = [".*"]\n')
    assert gs.scanne(repo, tmp_path / "b.json") != []


@mit_gitleaks
def test_should_block_findings_and_pass_clean_repos(tmp_path, capsys):
    sauber = tmp_path / "sauber"
    subprocess.run(["git", "init", "-q", str(sauber)], check=True)
    (sauber / "README.md").write_text("nichts Geheimes\n")
    git = [
        "git",
        "-C",
        str(sauber),
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t.invalid",
    ]
    subprocess.run([*git, "add", "README.md"], check=True)
    subprocess.run([*git, "commit", "-qm", "start"], check=True)
    assert gs.main([str(sauber)]) == 0
    assert gs.main([str(sauber), str(_repo_mit_altlast(tmp_path / "r"))]) == 1
    fehler = capsys.readouterr().err
    assert "github-pat in konfig.py" in fehler and "ghp_" not in fehler


def test_should_fail_closed_without_gitleaks(monkeypatch, tmp_path):
    monkeypatch.setattr(gs.shutil, "which", lambda _: None)
    assert gs.main([str(tmp_path)]) == 2


def test_should_fail_closed_when_positive_control_sees_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(gs.shutil, "which", lambda _: "/bin/gitleaks")
    monkeypatch.setattr(gs, "scanne", lambda repo, bericht: [])
    assert gs.main([str(tmp_path)]) == 2
