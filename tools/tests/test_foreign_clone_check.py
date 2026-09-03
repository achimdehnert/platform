"""Drill fuer das Gate `stale-local-clone-as-ground-truth`, Zweig 'fremde Quelle'.

Positivkontrolle und Negativkontrolle in einem: derselbe Hook muss bei einem
zurueckliegenden fremden Klon melden und bei einem aktuellen schweigen. Ein
Drill, der nur die Stille prueft, belegt nichts (Lehre: eine Null ist erst ein
Beleg, wenn dasselbe Verfahren nachweislich auch etwas finden kann).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / "tools/hooks/foreign_clone_check.sh"


def _git(pfad: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(pfad), *args], check=True,
                   capture_output=True, text=True)


def _repo_bauen(wurzel: Path, name: str, commits_voraus: int) -> Path:
    """Legt <wurzel>/<name> als Klon an, dessen origin <commits_voraus> weiter ist."""
    quelle = wurzel / f"{name}.git-quelle"
    quelle.mkdir(parents=True)
    _git(quelle, "init", "--initial-branch=main", "-q")
    _git(quelle, "config", "user.email", "drill@example.invalid")
    _git(quelle, "config", "user.name", "Drill")
    (quelle / "datei.txt").write_text("start\n", encoding="utf-8")
    _git(quelle, "add", "datei.txt")
    _git(quelle, "commit", "-qm", "start")

    klon = wurzel / name
    subprocess.run(["git", "clone", "-q", str(quelle), str(klon)],
                   check=True, capture_output=True, text=True)

    for i in range(commits_voraus):
        (quelle / "datei.txt").write_text(f"stand {i}\n", encoding="utf-8")
        _git(quelle, "add", "datei.txt")
        _git(quelle, "commit", "-qm", f"weiter {i}")
    return klon


def _hook_laufen(wurzel: Path, kommando: str, eigenes_repo: Path) -> str:
    umgebung = dict(os.environ)
    umgebung["GITHUB_DIR"] = str(wurzel)
    umgebung["CLAUDE_PROJECT_DIR"] = str(eigenes_repo)
    umgebung["CLAUDE_SESSION_ID"] = "drill"
    umgebung["TMPDIR"] = str(wurzel / "tmp")
    (wurzel / "tmp").mkdir(exist_ok=True)
    eingabe = json.dumps({"tool_input": {"command": kommando}})
    ergebnis = subprocess.run(["bash", str(HOOK)], input=eingabe,
                              capture_output=True, text=True, env=umgebung)
    assert ergebnis.returncode == 0, "Der Hook darf niemals blockieren"
    return ergebnis.stdout


@pytest.mark.parametrize("commits_voraus,soll_melden", [(3, True), (0, False)])
def test_should_melden_wenn_fremder_klon_zurueckliegt(
    tmp_path: Path, commits_voraus: int, soll_melden: bool
) -> None:
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 0)
    fremdes = _repo_bauen(tmp_path, "fremdes-hub", commits_voraus)

    ausgabe = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes)

    if soll_melden:
        assert "FREMDER KLON VERALTET" in ausgabe
        assert "fremdes-hub" in ausgabe
        assert str(commits_voraus) in ausgabe
    else:
        assert ausgabe.strip() == ""


def test_should_das_eigene_repo_nicht_melden(tmp_path: Path) -> None:
    """Das Sitzungs-Repo hat seinen eigenen Melder — doppelt waere Laerm."""
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 5)

    ausgabe = _hook_laufen(tmp_path, f"cat {eigenes}/datei.txt", eigenes)

    assert ausgabe.strip() == ""


def test_should_je_repo_nur_einmal_melden(tmp_path: Path) -> None:
    """Wiederholte Lesezugriffe duerfen nicht wiederholt fetchen und melden."""
    eigenes = _repo_bauen(tmp_path, "eigenes-hub", 0)
    fremdes = _repo_bauen(tmp_path, "fremdes-hub", 2)

    erste = _hook_laufen(tmp_path, f"cat {fremdes}/datei.txt", eigenes)
    zweite = _hook_laufen(tmp_path, f"grep x {fremdes}/datei.txt", eigenes)

    assert "FREMDER KLON VERALTET" in erste
    assert zweite.strip() == ""
