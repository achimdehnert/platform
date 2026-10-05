"""Tests fuer tools/sandbox/zustand.py (platform#3784 SB5) — Rechnung auf Fixtures, kein Netz."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SANDBOX = Path(__file__).resolve().parents[1] / "sandbox"
_spec = importlib.util.spec_from_file_location("zustand", _SANDBOX / "zustand.py")
z = importlib.util.module_from_spec(_spec)
sys.modules["zustand"] = z
_spec.loader.exec_module(z)

HEUTE = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
KOPF = "a" * 40


def _gh(antworten: dict):
    """Ersetzt den Aufruf: Antwort je API-Pfad, fehlender Pfad = Fehler wie bei HTTP 404."""

    def aufruf(*befehl, env=None):
        pfad = befehl[-1]
        if pfad not in antworten:
            raise subprocess.CalledProcessError(1, befehl)
        return json.dumps(antworten[pfad])

    return aufruf


def _spiegel(**abweichung) -> dict:
    antworten = {
        "repos/iilsandbox/x": {"default_branch": "main", "visibility": "private"},
        "repos/iilsandbox/x/actions/permissions": {"enabled": False},
        "repos/iilsandbox/x/branches": [{"name": "main"}],
        "repos/iilsandbox/x/pulls?state=open": [],
        "repos/iilsandbox/x/commits/main": {"sha": KOPF},
        f"repos/o/x/compare/{KOPF}...HEAD": {"ahead_by": 7},
    }
    antworten.update(abweichung)
    return {pfad: wert for pfad, wert in antworten.items() if wert is not None}


def test_should_report_backlog_without_warning_for_healthy_mirror():
    ergebnis = z.spiegel_zustand("o/x", _gh(_spiegel()))
    assert ergebnis == {
        "spiegel": "iilsandbox/x",
        "kopf": "aaaaaaaa",
        "rueckstand_commits": 7,
        "warnungen": [],
    }


def test_should_warn_when_mirror_invariants_are_broken():
    antworten = _spiegel(
        **{
            "repos/iilsandbox/x": {"default_branch": "main", "visibility": "public"},
            "repos/iilsandbox/x/actions/permissions": {"enabled": True},
            "repos/iilsandbox/x/branches": [{"name": "main"}, {"name": "lauf-1"}],
            "repos/iilsandbox/x/pulls?state=open": [{"number": 3}],
        }
    )
    assert z.spiegel_zustand("o/x", _gh(antworten))["warnungen"] == [
        "nicht privat",
        "Actions an",
        "weitere Branches: lauf-1",
        "offene PRs: 1",
    ]


def test_should_warn_when_mirror_head_is_unknown_to_source():
    antworten = _spiegel(**{f"repos/o/x/compare/{KOPF}...HEAD": None})
    ergebnis = z.spiegel_zustand("o/x", _gh(antworten))
    assert ergebnis["rueckstand_commits"] is None
    assert ergebnis["warnungen"] == ["Spiegel weicht vom Original ab"]


def test_should_count_unreadable_mirror_as_warning_not_as_green():
    ergebnis = z.spiegel_zustand("o/x", _gh({}))
    assert ergebnis["warnungen"] == ["nicht messbar: CalledProcessError"]


def test_should_read_token_expiry_from_response_header():
    koepfe = "HTTP/2.0 200 OK\nGithub-Authentication-Token-Expiration: 2027-01-02 23:00:00 UTC\n"
    assert z.token_zustand(koepfe, HEUTE) == {
        "ablauf": "2027-01-02",
        "tage": 89,
        "warnungen": [],
    }


def test_should_warn_when_token_expires_within_threshold():
    koepfe = "github-authentication-token-expiration: 2026-10-20 00:00:00 UTC\n"
    assert z.token_zustand(koepfe, HEUTE)["warnungen"] == [
        "Token laeuft in 14 Tagen ab"
    ]


def test_should_warn_when_token_expiry_is_missing():
    assert z.token_zustand("HTTP/2.0 200 OK\n", HEUTE)["warnungen"] == [
        "nicht messbar: kein Ablaufdatum in der Antwort"
    ]


def test_should_warn_only_when_pinned_cli_is_old_and_superseded():
    zeiten = {"2.1.0": "2026-08-01T00:00:00.000Z", "2.2.0": "2026-10-01T00:00:00.000Z"}
    alt = z.cli_zustand("2.1.0", zeiten, "2.2.0", HEUTE)
    assert alt["alter_tage"] == 65
    assert alt["warnungen"] == ["CLI 2.1.0 ist 65 Tage alt, aktuell 2.2.0"]
    assert z.cli_zustand("2.2.0", zeiten, "2.2.0", HEUTE)["warnungen"] == []
    assert z.cli_zustand("2.1.0", zeiten, "2.1.0", HEUTE)["warnungen"] == []


def test_should_warn_when_pinned_cli_version_is_unknown():
    assert z.cli_zustand("9.9.9", {}, None, HEUTE)["warnungen"] == [
        "nicht messbar: Version 9.9.9 unbekannt"
    ]


def test_should_read_cli_pin_from_real_dockerfile():
    assert z.cli_pin() and z.cli_pin()[0].isdigit()


def test_should_list_pilot_repos_without_comments():
    repos = z.pilot_repos()
    assert len(repos) == 5
    assert all("/" in repo and not repo.startswith("#") for repo in repos)


def test_should_collect_warnings_from_all_parts():
    ergebnis = {
        "stand": "2026-10-05T12:00+00:00",
        "spiegel": [{"spiegel": "iilsandbox/x", "warnungen": ["Actions an"]}],
        "token": {"warnungen": ["Token laeuft in 3 Tagen ab"]},
        "cli": {"pin": "2.1.0", "warnungen": []},
        "selbstpruefung": {"warnungen": []},
        "laeufe": {"B2": {"laeufe": 0, "fertig": 0}, "B6": {"summe_usd": 0}},
    }
    assert z.warnungen(ergebnis) == [
        "iilsandbox/x: Actions an",
        "Token laeuft in 3 Tagen ab",
    ]
    assert "- iilsandbox/x: Actions an" in z.als_markdown(ergebnis)
