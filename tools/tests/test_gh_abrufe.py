"""Mitschreiber vor gh (dev-hub#404): protokolliert knapp, reicht alles durch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
MITSCHREIBER = WURZEL / "tools" / "gh_abrufe" / "gh"
sys.path.insert(0, str(WURZEL / "tools" / "gh_abrufe"))

import auswertung  # noqa: E402


def _lauf(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    echt = tmp_path / "echt-gh"
    echt.write_text('#!/usr/bin/env bash\necho "ECHT $*"\nexit 3\n')
    echt.chmod(0o755)
    log = tmp_path / "abrufe.tsv"
    env = {**os.environ, "GH_ABRUF_ECHT": str(echt), "GH_ABRUF_LOG": str(log)}
    fertig = subprocess.run(
        ["bash", str(MITSCHREIBER), *args], capture_output=True, text=True, env=env
    )
    zeilen = log.read_text().splitlines() if log.exists() else []
    return fertig, zeilen


def test_should_pass_args_output_and_exit_code_through(tmp_path):
    fertig, _ = _lauf(tmp_path, "pr", "view", "12", "--json", "state")
    assert fertig.stdout.strip() == "ECHT pr view 12 --json state"
    assert fertig.returncode == 3


def test_should_log_one_line_with_subcommand_and_repo(tmp_path):
    _, zeilen = _lauf(tmp_path, "pr", "list", "-R", "org/repo", "--state", "merged")
    assert len(zeilen) == 1
    spalten = zeilen[0].split("\t")
    assert len(spalten) == len(auswertung.SPALTEN)
    assert spalten[3] == "pr list"
    assert spalten[5] == "org/repo"


def test_should_log_api_endpoint_without_query(tmp_path):
    _, zeilen = _lauf(tmp_path, "api", "repos/o/r/issues?per_page=100", "--jq", ".[]")
    spalten = zeilen[0].split("\t")
    assert spalten[3].strip() == "api"
    assert spalten[4] == "repos/o/r/issues"


def test_should_never_log_free_text_arguments(tmp_path):
    geheim = "Inhalt-der-nie-ins-Log-darf"
    _, zeilen = _lauf(tmp_path, "issue", "create", "--title", geheim, "--body", geheim)
    assert geheim not in "\n".join(zeilen)


def test_should_not_log_parent_arguments(tmp_path):
    # platform#3599: vom Aufrufer nur Programm und Skriptpfad, nie seine Argumente
    geheim = "tok-das-nie-ins-Log-darf"
    echt = tmp_path / "echt-gh"
    echt.write_text("#!/usr/bin/env bash\nexit 0\n")
    echt.chmod(0o755)
    aufrufer = tmp_path / "aufrufer.sh"
    aufrufer.write_text(f'bash "{MITSCHREIBER}" pr list\ntrue\n')
    log = tmp_path / "abrufe.tsv"
    env = {**os.environ, "GH_ABRUF_ECHT": str(echt), "GH_ABRUF_LOG": str(log)}
    subprocess.run(["bash", str(aufrufer), "--token", geheim], env=env, check=True)
    spalten = log.read_text().splitlines()[0].split("\t")
    assert geheim not in spalten[1]
    assert spalten[1] == f"bash {aufrufer}"


def test_should_still_run_gh_when_log_is_unwritable(tmp_path):
    echt = tmp_path / "echt-gh"
    echt.write_text('#!/usr/bin/env bash\necho ok\n')
    echt.chmod(0o755)
    env = {**os.environ, "GH_ABRUF_ECHT": str(echt), "GH_ABRUF_LOG": "/proc/nicht/da.tsv"}
    fertig = subprocess.run(["bash", str(MITSCHREIBER)], capture_output=True, text=True, env=env)
    assert fertig.stdout.strip() == "ok"
    assert fertig.stderr == ""


def test_should_rank_callers_and_skip_broken_lines(tmp_path, capsys):
    log = tmp_path / "abrufe.tsv"
    jetzt = "2099-01-01T00:00:00Z"
    log.write_text(
        f"{jetzt}\thook-a\t/x\tpr list\t\to/r\n"
        f"{jetzt}\thook-a\t/x\tpr view\t\to/r\n"
        f"{jetzt}\tschleife\t/y\tapi \trepos/o/r\t\n"
        "kaputt\tzeile\n"
        "2000-01-01T00:00:00Z\talt\t/z\tpr list\t\t\n"
    )
    assert auswertung.main(["--log", str(log), "--stunden", "1"]) == 0
    aus = capsys.readouterr().out
    assert aus.startswith("3 gh-Aufrufe")
    assert "     2  hook-a" in aus
    assert "alt" not in aus
