"""Tests für tools/pr_bestand.py (#3812 K4: PR-Bestand wiederholbar messen).

`--eingabe` ersetzt `gh search prs` durch eine Fixture, `--jetzt` die Uhr —
damit laufen Alter und Trend offline und deterministisch.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "pr_bestand.py"
sys.path.insert(0, str(SCRIPT.parent))

import pr_bestand  # noqa: E402


def _pr(n: int, erstellt: str, login: str = "achimdehnert", titel: str = "fix: x", bot: bool = False) -> dict:
    return {
        "number": n,
        "title": titel,
        "author": {"login": login, "is_bot": bot},
        "createdAt": erstellt,
        "repository": {"nameWithOwner": "achimdehnert/demo"},
    }


def _run(tmp_path: Path, prs: list[dict], jetzt: str, journal: Path | None = None):
    eingabe = tmp_path / "prs.json"
    eingabe.write_text(json.dumps(prs), encoding="utf-8")
    cmd = [sys.executable, str(SCRIPT), "--eingabe", str(eingabe), "--jetzt", jetzt]
    cmd += ["--journal", str(journal)] if journal else ["--kein-journal"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def test_should_assign_each_pr_to_its_generator():
    assert pr_bestand.erzeuger(_pr(1, "2026-10-01T00:00:00Z", titel="chore: project-facts sync")) == "project-facts"
    assert pr_bestand.erzeuger(_pr(2, "2026-10-01T00:00:00Z", login="app/dependabot", bot=True)) == "dependabot"
    assert pr_bestand.erzeuger(_pr(3, "2026-10-01T00:00:00Z", login="app/renovate", bot=True)) == "renovate"
    assert pr_bestand.erzeuger(_pr(4, "2026-10-01T00:00:00Z", login="app/github-actions", bot=True)) == "bot-sonstige"
    assert pr_bestand.erzeuger(_pr(5, "2026-10-01T00:00:00Z")) == "mensch"


def test_should_count_only_prs_older_than_threshold_as_alt(tmp_path):
    prs = [_pr(1, "2026-08-01T00:00:00Z"), _pr(2, "2026-10-01T00:00:00Z")]
    res = _run(tmp_path, prs, "2026-10-06T12:00:00+00:00")
    assert res.returncode == 0, res.stderr
    assert "| **Summe** | **2** | **1** |" in res.stdout


def test_should_report_sammelphase_without_journal_history(tmp_path):
    res = _run(tmp_path, [_pr(1, "2026-10-01T00:00:00Z")], "2026-10-06T12:00:00+00:00")
    assert res.stdout.strip().splitlines()[-1].startswith("SAMMELPHASE:")


def test_should_warn_when_alt_exceeds_threshold_even_without_history(tmp_path):
    prs = [_pr(n, "2026-01-01T00:00:00Z") for n in range(pr_bestand.SCHWELLE_ALT + 1)]
    res = _run(tmp_path, prs, "2026-10-06T12:00:00+00:00")
    assert res.stdout.strip().splitlines()[-1].startswith("WARN:")


def test_should_warn_and_name_driver_when_backlog_grows_over_a_week(tmp_path):
    journal = tmp_path / "journal.jsonl"
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z")], "2026-09-29T12:00:00+00:00", journal)
    prs = [_pr(1, "2026-09-28T00:00:00Z")] + [
        _pr(n, "2026-10-05T00:00:00Z", login="app/dependabot", bot=True) for n in (2, 3)
    ]
    res = _run(tmp_path, prs, "2026-10-06T12:00:00+00:00", journal)
    letzte = res.stdout.strip().splitlines()[-1]
    assert letzte.startswith("WARN:"), letzte
    assert "dependabot +2" in letzte
    assert len(journal.read_text(encoding="utf-8").splitlines()) == 2


def test_should_report_ok_when_backlog_shrinks(tmp_path):
    journal = tmp_path / "journal.jsonl"
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z"), _pr(2, "2026-09-28T00:00:00Z")], "2026-09-29T12:00:00+00:00", journal)
    res = _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z")], "2026-10-06T12:00:00+00:00", journal)
    assert res.stdout.strip().splitlines()[-1].startswith("OK:")


def test_should_stay_advisory_when_input_unreadable(tmp_path):
    kaputt = tmp_path / "prs.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--eingabe", str(kaputt), "--kein-journal"],
        capture_output=True, text=True, timeout=15,
    )
    assert res.returncode == 0
    assert res.stdout.startswith("nicht pruefbar:")


def _lesen(journal: Path, jetzt: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--lesen", "--journal", str(journal), "--jetzt", jetzt],
        capture_output=True, text=True, timeout=15,
    )


def test_should_read_journal_without_measuring_and_warn_on_growth(tmp_path):
    """#3823 K2: der Sitzungsstart liest nur, eine Zeile, Exit 1 bei WARN."""
    journal = tmp_path / "journal.jsonl"
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z")], "2026-09-29T12:00:00+00:00", journal)
    prs = [_pr(1, "2026-09-28T00:00:00Z"), _pr(2, "2026-10-05T00:00:00Z", login="app/renovate", bot=True)]
    _run(tmp_path, prs, "2026-10-06T12:00:00+00:00", journal)
    res = _lesen(journal, "2026-10-07T08:00:00+00:00")
    assert res.returncode == 1, res.stdout
    assert len(res.stdout.strip().splitlines()) == 1
    assert res.stdout.startswith("WARN:") and "renovate +1" in res.stdout
    assert len(journal.read_text(encoding="utf-8").splitlines()) == 2


def test_should_pass_reading_when_backlog_shrinks(tmp_path):
    journal = tmp_path / "journal.jsonl"
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z"), _pr(2, "2026-09-28T00:00:00Z")], "2026-09-29T12:00:00+00:00", journal)
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z")], "2026-10-06T12:00:00+00:00", journal)
    res = _lesen(journal, "2026-10-07T08:00:00+00:00")
    assert res.returncode == 0 and res.stdout.startswith("OK:"), res.stdout


def test_should_flag_missing_or_stale_journal_as_timer_down(tmp_path):
    journal = tmp_path / "journal.jsonl"
    assert _lesen(journal, "2026-10-07T08:00:00+00:00").returncode == 2
    _run(tmp_path, [_pr(1, "2026-09-28T00:00:00Z")], "2026-09-29T12:00:00+00:00", journal)
    res = _lesen(journal, "2026-10-08T12:00:00+00:00")
    assert res.returncode == 2 and "Timer steht" in res.stdout


def test_should_read_orgs_from_data_file(tmp_path):
    """Retro 3b46a0 M8: die Org-Liste steht in einer Datendatei, nicht im Modul."""
    datei = tmp_path / "orgs.json"
    datei.write_text(json.dumps({"orgs": ["org-a", "org-b"]}), encoding="utf-8")
    assert pr_bestand.lade_orgs(datei) == ("org-a", "org-b")


def test_should_ship_a_non_empty_org_list_in_the_registry():
    orgs = pr_bestand.lade_orgs()
    assert orgs and len(set(orgs)) == len(orgs)


def test_should_report_unverifiable_when_org_file_is_empty(tmp_path):
    datei = tmp_path / "orgs.json"
    datei.write_text(json.dumps({"orgs": []}), encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--orgs-datei", str(datei), "--kein-journal"],
        capture_output=True, text=True, timeout=15,
    )
    assert res.returncode == 0 and res.stdout.startswith("nicht pruefbar: ValueError"), res.stdout
