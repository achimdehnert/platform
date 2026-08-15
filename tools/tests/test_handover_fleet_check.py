"""Tests für tools/handover_fleet_check.py (Flotten-Messung, platform#1945 Kriterium 1).

Getestet wird die reine Logik ohne Netz: Auswahl der aktiven Repos, Datums-Erkennung im
Stand-Block, Owner-Auflösung über `full_name` (Redirect-Falle), Erkennung der Gate-
Verdrahtung und die deterministische Ausgabe. Die HTTP-Schicht (`gh_api`) wird gemockt —
ein Test gegen die echte API wäre weder deterministisch noch offline lauffähig.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import handover_fleet_check as hfc  # noqa: E402


# ── aktive Repos ──────────────────────────────────────────────────────────────


def test_should_skip_archived_frozen_and_decommissioned_repos():
    canon = {
        "decommissioned": [{"name": "bfagent"}],
        "repos": {
            "risk-hub": {"lifecycle": "production"},
            "research-hub": {"lifecycle": "frozen"},
            "wedding-hub": {"lifecycle": "archived"},
            "bfagent": {"lifecycle": "production"},  # trotzdem raus: stillgelegt
            "promptfw": {},  # kein lifecycle = aktiv
        },
    }
    assert hfc.active_repos(canon) == ["promptfw", "risk-hub"]


def test_should_read_lifecycle_from_rich_block_when_toplevel_missing():
    """bfagent trägt lifecycle historisch nur unter `rich` — dieselbe Fallback-Regel
    wie in registry_api._lifecycle, sonst zählt ein archiviertes Repo als aktiv."""
    canon = {"repos": {"altlast": {"rich": {"lifecycle": "archived"}}}}
    assert hfc.active_repos(canon) == []


# ── Datum des Stand-Blocks ────────────────────────────────────────────────────


def test_should_find_newest_dated_heading():
    text = "# Titel\n\n## ⚡ Aktueller Stand (2026-08-11 — irgendwas)\n\n## ⚡ Vorheriger Stand (2026-08-10)\n"
    assert hfc.heading_date_from_text(text) == date(2026, 8, 11)


def test_should_accept_the_other_dialect():
    """Zweiter etablierter Dialekt der Flotte — die Messung darf nicht auf einen festlegen."""
    assert hfc.heading_date_from_text(
        "## Current state (observed 2026-07-07)\n"
    ) == date(2026, 7, 7)


def test_should_ignore_dates_outside_the_head_window():
    text = "\n" * (hfc.HEAD_LINES + 1) + "## Aktueller Stand (2026-08-11)\n"
    assert hfc.heading_date_from_text(text) is None


def test_should_ignore_date_that_is_not_in_a_heading():
    assert hfc.heading_date_from_text("Stand vom 2026-08-11, siehe unten\n") is None


def test_should_ignore_unparsable_date():
    assert hfc.heading_date_from_text("## Stand (2026-13-45)\n") is None


# ── Owner-Auflösung ───────────────────────────────────────────────────────────


def test_should_take_owner_from_full_name_not_from_requested_path(monkeypatch):
    """GitHub folgt nach einem Transfer still einem Redirect: die Anfrage an die FALSCHE
    Org liefert 200. Der Owner muss deshalb aus `full_name` der Antwort kommen — sonst
    schreibt die Messung eine Fehlzuordnung fest (🌀 github_redirect_masks_org_hardcode)."""

    def fake(path, token, raw=False):
        if path == "/repos/achimdehnert/meiki-hub":  # Redirect-Antwort
            return {"full_name": "meiki-lra/meiki-hub", "default_branch": "main"}
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)
    assert hfc.resolve_repo("meiki-hub", "t")["full_name"] == "meiki-lra/meiki-hub"


def test_should_return_none_when_repo_is_in_no_known_org(monkeypatch):
    monkeypatch.setattr(hfc, "gh_api", lambda *a, **k: None)
    assert hfc.resolve_repo("gibtsnicht", "t") is None


# ── Gate-Verdrahtung ──────────────────────────────────────────────────────────


def _gate_env(monkeypatch, listing, files):
    def fake(path, token, raw=False):
        if path.endswith("/contents/.github/workflows"):
            return listing
        for name, text in files.items():
            if path.endswith(f"/workflows/{name}"):
                return text
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)


def test_should_detect_gate_wired_via_shared_ci(monkeypatch):
    """Der Gate-Workflow ist von platform nach iilgmbh/shared-ci gewandert. Eine Regex
    nur auf `platform` meldete die verdrahtete Hälfte der Flotte als „unklar"."""
    _gate_env(
        monkeypatch,
        [{"name": "handoff-banner-gate.yml"}],
        {
            "handoff-banner-gate.yml": "jobs:\n  g:\n    uses: iilgmbh/shared-ci/.github/workflows/handoff-banner-gate.yml@v1.1.1\n"
        },
    )
    assert hfc.gate_state("achimdehnert/apo-hub", "t") == "ja@v1.1.1"


def test_should_detect_gate_wired_via_platform(monkeypatch):
    _gate_env(
        monkeypatch,
        [{"name": "handover-gate.yaml"}],
        {
            "handover-gate.yaml": "uses: achimdehnert/platform/.github/workflows/handoff-banner-gate.yml@main\n"
        },
    )
    assert hfc.gate_state("achimdehnert/x", "t") == "ja@main"


def test_should_not_count_a_reference_that_only_appears_in_a_comment(monkeypatch):
    """platform trägt die Referenz im Kopf-Kommentar seiner eigenen Gate-Definition
    (Beispielaufruf für Caller). Ohne die `uses:`-Bedingung meldete die Messung das
    definierende Repo als „verdrahtet" — auf Basis von Prosa. Falsch-Grün ist in einer
    Bestandsaufnahme der teuerste Fehler, weil danach niemand mehr hinsieht."""
    _gate_env(
        monkeypatch,
        [{"name": "handoff-banner-gate.yml"}],
        {
            "handoff-banner-gate.yml": (
                "# Andere Repos können\n"
                "# `uses: achimdehnert/platform/.github/workflows/handoff-banner-gate.yml@main` aufrufen\n"
                "on:\n  workflow_call: {}\n"
            )
        },
    )
    assert hfc.gate_state("achimdehnert/platform", "t") == "unklar"


def test_should_report_nativ_when_repo_runs_the_check_itself(monkeypatch):
    _gate_env(
        monkeypatch,
        [{"name": "handoff-banner-gate.yml"}],
        {
            "handoff-banner-gate.yml": (
                "# `uses: platform/.github/workflows/handoff-banner-gate.yml@main` (Beispiel)\n"
                "    - run: python3 scripts/checks/agent_handover_freshness_check.py AGENT_HANDOVER.md\n"
            )
        },
    )
    assert hfc.gate_state("achimdehnert/platform", "t") == "nativ"


def test_should_count_nativ_as_wired():
    assert hfc._gate_ok("nativ") and hfc._gate_ok("ja@v1.1.1")
    assert not hfc._gate_ok("unklar") and not hfc._gate_ok("nein")


def test_should_report_unklar_when_named_workflow_lacks_the_reference(monkeypatch):
    _gate_env(
        monkeypatch,
        [{"name": "handoff-something.yml"}],
        {"handoff-something.yml": "jobs:\n  x:\n    runs-on: ubuntu-latest\n"},
    )
    assert hfc.gate_state("achimdehnert/x", "t") == "unklar"


def test_should_report_nein_without_candidate_workflow(monkeypatch):
    _gate_env(monkeypatch, [{"name": "ci.yml"}], {})
    assert hfc.gate_state("achimdehnert/x", "t") == "nein"


def test_should_report_na_when_workflow_dir_unreadable(monkeypatch):
    monkeypatch.setattr(hfc, "gh_api", lambda *a, **k: None)
    assert hfc.gate_state("achimdehnert/x", "t") == "n/a"


# ── Messung + Ausgabe ─────────────────────────────────────────────────────────


def test_should_record_missing_repo_as_result_not_as_crash(monkeypatch):
    monkeypatch.setattr(hfc, "resolve_repo", lambda *a, **k: None)
    row = hfc.measure_repo("gibtsnicht", "t", with_gate=True)
    assert (
        row["gefunden"] is False and row["handover"] is False and row["gate"] == "n/a"
    )


def test_should_measure_repo_with_handover_and_log(monkeypatch):
    monkeypatch.setattr(
        hfc,
        "resolve_repo",
        lambda *a, **k: {
            "full_name": "achimdehnert/platform",
            "default_branch": "main",
            "gh_archived": False,
        },
    )

    def fake(path, token, raw=False):
        if path.endswith("/AGENT_HANDOVER.md"):
            return "## ⚡ Aktueller Stand (2026-08-11)\n"
        if path.endswith("/AGENT_HANDOVER_LOG.md"):
            return "### 2026-08-11 · Session\n"
        return None

    monkeypatch.setattr(hfc, "gh_api", fake)
    row = hfc.measure_repo("platform", "t", with_gate=False)
    assert (row["handover"], row["log"], row["stand"]) == (True, True, "2026-08-11")
    assert "gate" not in row  # ohne --gate keine Spalte


@pytest.mark.parametrize("with_gate", [False, True])
def test_should_render_table_identically_for_identical_input(with_gate):
    """Kriterium 1 verlangt zwei identische Läufe: die Ausgabe darf keinen Zeitstempel
    und keine unsortierte Menge enthalten."""
    rows = [
        {
            "repo": "b-hub",
            "owner": "achimdehnert",
            "gefunden": True,
            "handover": True,
            "log": False,
            "stand": "2026-08-11",
            "gate": "ja@v1.1.1",
        },
        {
            "repo": "a-hub",
            "owner": None,
            "gefunden": False,
            "handover": False,
            "log": False,
            "stand": None,
            "gate": "n/a",
        },
    ]
    assert hfc.render_table(rows, with_gate) == hfc.render_table(rows, with_gate)
    assert "nicht gefunden" in hfc.render_table(rows, with_gate)


def test_should_not_print_a_date_column_for_repo_without_handover_file():
    rows = [
        {
            "repo": "x",
            "owner": "achimdehnert",
            "gefunden": True,
            "handover": False,
            "log": False,
            "stand": None,
        }
    ]
    # ohne Datei ist "kein Datum" keine Aussage über den Stand, sondern Rauschen
    assert "kein Datum" not in hfc.render_table(rows, False)


# ── Aktivitäts-Messung (Weg 1, platform#1945) ─────────────────────────────────


def test_should_count_session_branch_prs_not_all_prs(monkeypatch):
    """Das Sitzungs-Signal ist die `head:session/`-Suche, nicht die PR-Gesamtzahl.

    Nach der reinen PR-Zahl waren 29 von 31 handover-losen Repos „aktiv" — Weg 1 und
    Weg 2 der Ausnahmeliste waren damit ununterscheidbar. Erst die Session-Branches
    trennen (infra-deploy: PRs ja, Sitzungen null)."""
    gesehen = {}

    def fake(path, token, raw=False):
        gesehen["q"] = path
        return {"total_count": 7}

    monkeypatch.setattr(hfc, "gh_api", fake)
    assert hfc.sessions_seit("achimdehnert/dev-hub", "2026-05-15", "t") == 7
    assert "head%3Asession/" in gesehen["q"]


def test_should_return_none_when_search_is_unavailable(monkeypatch):
    """Ein Rate-Limit ist kein leeres Ergebnis: None darf nicht als 0 durchgehen, sonst
    steht ein aktives Repo als ruhend im Bericht (real passiert: mcp-hub, 50 Sitzungen)."""
    monkeypatch.setattr(hfc, "gh_api", lambda *a, **k: None)
    assert hfc.sessions_seit("achimdehnert/mcp-hub", "2026-05-15", "t") is None
    assert hfc.prs_seit("achimdehnert/mcp-hub", "2026-05-15", "t") is None


def test_should_retry_on_rate_limit_and_then_succeed(monkeypatch):
    import urllib.error

    antworten = [
        urllib.error.HTTPError("u", 403, "rate limit", {"Retry-After": "0"}, None),
        _FakeResponse('{"total_count": 3}'),
    ]

    def fake_urlopen(req, timeout=0):
        a = antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return a

    monkeypatch.setattr(hfc.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(hfc.time, "sleep", lambda _s: None)
    assert hfc.gh_api("/search/issues?q=x", "t") == {"total_count": 3}


class _FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
