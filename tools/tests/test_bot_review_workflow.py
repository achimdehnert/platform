"""Tests fuer .github/workflows/bot-review.yml (#2442).

Der Defekt war lautlos: bei genau EINEM Kandidaten schrieb der Filter
`2441` ohne Zeilenende, und `while read -r n` gibt bei EOF-ohne-Trenner 1
zurueck — die Schleife laeuft dann gar nicht. Im Log standen acht
Skip-Zeilen mit Grund und danach nichts; der PR fiel aus dem Werkzeug,
ohne dass irgendwer es sehen konnte.

Deshalb wird hier nicht die Schreibweise geprueft, sondern beides
ausgefuehrt: der echte Filter aus dem Workflow gegen eine Ein-Kandidat-Lage,
und die echte Schleifen-Zeile ueber die Datei, die er schreibt.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "bot-review.yml"


def _run_script() -> str:
    doc = yaml.safe_load(WF.read_text(encoding="utf-8"))
    for step in doc["jobs"]["review"]["steps"]:
        if "Kandidaten" in (step.get("name") or ""):
            return step["run"]
    raise AssertionError("Schritt 'Kandidaten pruefen und approven' nicht gefunden")


def _filter_kommando() -> list[str]:
    """Der Aufruf der Auswahl, wie er WIRKLICH im Workflow steht.

    Bis 2026-09-02 stand die Auswahl als Heredoc im Schritt und wurde hier
    herausgeschnitten. Seit #2676 liegt sie in `tools/bot_review_kandidaten.py`
    (testbar, siehe test_bot_review_kandidaten.py). Dieser Test bleibt, weil er
    etwas anderes prueft: dass der Workflow das Modul auch aufruft und die
    Shell-Schleife dahinter mit dessen Ausgabe umgehen kann.
    """
    for zeile in _run_script().split("\n"):
        s = zeile.strip()
        if s.startswith("python3 ") and "bot_review_kandidaten.py" in s:
            return s.split()
    raise AssertionError("Aufruf von bot_review_kandidaten.py im Workflow nicht gefunden")


def _schleifen_kopf() -> str:
    for zeile in _run_script().split("\n"):
        if zeile.strip().startswith("while read"):
            return zeile.strip()
    raise AssertionError("while-read-Schleife im Workflow nicht gefunden")


BOT_LOGIN = "IIL-Lotse"


def _pr(nummer: int, reviews: list | None = None) -> dict:
    return {
        "number": nummer,
        "isDraft": False,
        "author": {"login": "achimdehnert"},
        "mergeStateStatus": "BLOCKED",
        "reviewDecision": "",
        "reviews": reviews or [],
        "files": [{"path": "registry/canonical.yaml"}],
        "statusCheckRollup": [
            {"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}
        ],
        "url": f"https://github.com/achimdehnert/platform/pull/{nummer}",
    }


def _filter_lauf(tmp_path: Path, prs: list) -> tuple[str, Path]:
    """Fuehrt den ECHTEN Filter aus dem Workflow aus, nur mit umgelenkten Pfaden."""
    prs_datei = tmp_path / "prs.json"
    kandidaten = tmp_path / "kandidaten"
    prs_datei.write_text(json.dumps(prs), encoding="utf-8")
    argv = [
        str(prs_datei)
        if teil == "/tmp/prs.json"
        else str(kandidaten)
        if teil == "/tmp/kandidaten"
        else teil
        for teil in _filter_kommando()[1:]  # ohne das fuehrende "python3"
    ]
    argv[0] = str(WF.parents[2] / argv[0])  # Skriptpfad relativ zur Repo-Wurzel
    umgebung = {**os.environ, "BOT_LOGIN": BOT_LOGIN}
    p = subprocess.run(
        [sys.executable, *argv], capture_output=True, text=True, env=umgebung
    )
    assert p.returncode == 0, p.stderr
    return p.stdout, kandidaten


def test_should_write_candidate_file_with_trailing_newline(tmp_path):
    """Ein einzelner Kandidat muss als vollstaendige Zeile herauskommen."""
    _, kandidaten = _filter_lauf(tmp_path, [_pr(2441)])
    assert kandidaten.read_text() == "2441\n"


def test_should_enter_loop_body_for_a_single_candidate(tmp_path):
    """Der Fall #2441: eine Datei, ein Kandidat — die Schleife MUSS laufen."""
    _, kandidaten = _filter_lauf(tmp_path, [_pr(2441)])
    skript = f'{_schleifen_kopf()}\n  echo "gesehen:$n"\ndone < {kandidaten}\n'
    p = subprocess.run(["bash", "-c", skript], capture_output=True, text=True)
    assert "gesehen:2441" in p.stdout, p.stdout + p.stderr


def test_should_not_lose_the_last_of_several_candidates(tmp_path):
    """Gegenprobe: auch der letzte von mehreren darf nicht verschwinden."""
    _, kandidaten = _filter_lauf(tmp_path, [_pr(2441), _pr(2452)])
    skript = f'{_schleifen_kopf()}\n  echo "gesehen:$n"\ndone < {kandidaten}\n'
    p = subprocess.run(["bash", "-c", skript], capture_output=True, text=True)
    assert "gesehen:2441" in p.stdout and "gesehen:2452" in p.stdout, p.stdout


def test_should_name_every_pr_it_saw_before_filtering(tmp_path):
    """Ohne die Liste VOR dem Filter ist die naechste Luecke wieder stumm."""
    stdout, _ = _filter_lauf(tmp_path, [_pr(2441), _pr(2452)])
    assert "2441" in stdout.splitlines()[0] and "2452" in stdout.splitlines()[0]
    assert "Kandidaten:" in stdout


def test_should_still_skip_a_tabu_path_with_a_reason(tmp_path):
    """Positivkontrolle in die andere Richtung — der Filter darf nicht
    plötzlich alles durchlassen."""
    pr = _pr(2038)
    pr["files"] = [{"path": "policies/nur-fuer-diesen-test.md"}]
    stdout, kandidaten = _filter_lauf(tmp_path, [pr])
    assert "Tabu-Pfad" in stdout
    assert kandidaten.read_text() == ""


# --- Wiederholungs-Sperre (platform#2660) ------------------------------------
# Der 20-Minuten-Cron approvte denselben Stand endlos nach, weil `reviewDecision`
# leer bleibt, solange ein menschliches Code-Owner-Review aussteht: #2482 sammelte
# 70 Bot-Approvals, #2478 69. Massgeblich ist die EIGENE Review-Liste.


def test_should_not_approve_a_pr_it_already_approved(tmp_path):
    pr = _pr(2482, reviews=[{"author": {"login": BOT_LOGIN}, "state": "APPROVED"}])
    stdout, kandidaten = _filter_lauf(tmp_path, [pr])
    assert f"bereits von {BOT_LOGIN} approved" in stdout
    assert kandidaten.read_text() == ""


def test_should_still_approve_when_only_someone_else_approved(tmp_path):
    """Gegenprobe: ein fremdes Approve darf den Bot nicht aussperren — sonst
    wuerde die Sperre still alles blockieren statt nur die Wiederholung."""
    pr = _pr(2483, reviews=[{"author": {"login": "wirdigital"}, "state": "APPROVED"}])
    stdout, kandidaten = _filter_lauf(tmp_path, [pr])
    assert "bereits von" not in stdout
    assert kandidaten.read_text().strip() == "2483"


def test_should_ignore_its_own_non_approving_review(tmp_path):
    """Ein eigener Kommentar-Review ist keine Freigabe."""
    pr = _pr(2484, reviews=[{"author": {"login": BOT_LOGIN}, "state": "COMMENTED"}])
    _, kandidaten = _filter_lauf(tmp_path, [pr])
    assert kandidaten.read_text().strip() == "2484"
