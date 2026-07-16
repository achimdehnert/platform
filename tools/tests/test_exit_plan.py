"""Tests fuer tools/exit-plan.py (Gov-Exit-Firedrill-Tool, ADR-236 / KONZ-platform-002).

Issue #1199 TEST-3 (H, SURVIVES, eher unterschaetzt): 0 Tests und 0 CI-Exercise
auf einem Tool, das als Kill-Criteria-Beweis in ADR-236 und KONZ-platform-002
referenziert wird. Alle Netzwerk-/GitHub-API-Calls werden hier gemockt
(monkeypatch auf `api()`) -- niemals live gegen echte Repos.

Golden-Path: main() laeuft end-to-end gegen eine gemockte API-Antwortmenge fuer
eine kleine Fake-Org mit einem Repo, erzeugt einen Report ueber --out und
prueft die Kernstruktur (Sections, Repo-Eintrag, keine falschen Gaps).
Fehlerpfad: nicht lesbare Org (401/403 auf /orgs/{org}) fuehrt zu Exit 1 und
einer Fehlermeldung, ohne dass irgendein Netzwerk-Call stattfindet.

Modul heisst `exit-plan.py` (Bindestrich) -- kein normaler Python-Modulname,
daher importlib.util.spec_from_file_location wie bei den Schwester-Tests
(test_repo_checker.py, test_check_publish_gate.py).
"""

from __future__ import annotations

import importlib.util
import io
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "exit_plan",
    pathlib.Path(__file__).resolve().parents[1] / "exit-plan.py",
)
ep = importlib.util.module_from_spec(_SPEC)
sys.modules["exit_plan"] = ep
_SPEC.loader.exec_module(ep)


# ---------------------------------------------------------------------------
# Fake-API: (status, payload) je Pfad, damit main() end-to-end ohne Netzwerk
# laeuft. paged() ruft dieselbe api()-Funktion mit &page=N -- wir liefern
# fuer Listen-Endpunkte nur auf Seite 1 Daten, ab Seite 2 eine leere Liste
# (analog echtem GitHub-Verhalten: leere Seite beendet Pagination).
# ---------------------------------------------------------------------------

def _make_fake_api(responses: dict[str, tuple[int, object]], default=(200, [])):
    def _strip_paging(path: str) -> tuple[str, int]:
        if "page=" not in path:
            return path, 1
        base, _, tail = path.partition("?")
        params = dict(p.split("=") for p in tail.split("&") if "=" in p)
        page = int(params.get("page", "1"))
        # rekonstruiere den Pfad ohne die von paged() angehaengten Query-Parameter
        return base, page

    def fake_api(path: str, raw: bool = False):
        base, page = _strip_paging(path)
        if base in responses:
            st, payload = responses[base]
            if page > 1 and isinstance(payload, list):
                return st, []
            return st, payload
        return default

    return fake_api


_ORG = "fakeorg"


def _base_responses() -> dict[str, tuple[int, object]]:
    return {
        f"/repos/{_ORG}": (200, {"name": _ORG}),
        f"/orgs/{_ORG}": (200, {"public_repos": 1, "owned_private_repos": 0}),
        f"/orgs/{_ORG}/actions/secrets": (200, {"secrets": [{"name": "DEPLOY_KEY"}]}),
        f"/orgs/{_ORG}/actions/variables": (200, {"variables": []}),
        f"/orgs/{_ORG}/hooks": (200, []),
        f"/orgs/{_ORG}/installations": (200, {"installations": []}),
        f"/orgs/{_ORG}/packages": (200, []),
        f"/orgs/{_ORG}/repos": (200, [{"name": "widget", "private": False}]),
        f"/repos/{_ORG}/widget/actions/secrets": (200, {"secrets": []}),
        f"/repos/{_ORG}/widget/actions/variables": (200, {"variables": []}),
        f"/repos/{_ORG}/widget/environments": (200, {"environments": []}),
        f"/repos/{_ORG}/widget/hooks": (200, []),
        f"/repos/{_ORG}/widget/keys": (200, []),
        f"/repos/{_ORG}/widget/rulesets": (200, []),
        f"/repos/{_ORG}/widget/pages": (404, None),
        f"/repos/{_ORG}/widget/code-scanning/default-setup": (200, {"state": "not-configured"}),
        f"/repos/{_ORG}/widget/contents/.github/workflows": (404, None),
    }


def test_should_generate_full_runbook_golden_path(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "TOKEN", "fake-token")
    monkeypatch.setattr(ep, "api", _make_fake_api(_base_responses()))
    # exit-classes.yaml SSoT absichtlich nicht vorhanden -> das ist ein
    # deklarierter Gap-Pfad (siehe load_exit_classes), nicht Testgegenstand hier.
    monkeypatch.setattr(ep, "EXIT_CLASSES", tmp_path / "does-not-exist.yaml")

    out_path = tmp_path / "runbook.md"
    monkeypatch.setattr(sys, "argv", ["exit-plan.py", _ORG, "--out", str(out_path)])

    rc = ep.main()

    assert rc == 0
    report = out_path.read_text(encoding="utf-8")
    assert f"Exit-Plan / Portability Runbook — `{_ORG}`" in report
    assert "## 1. Org-level" in report
    assert "### `widget` (public)" in report
    assert "DEPLOY_KEY" in report
    # exit-classes SSoT fehlt -> muss als Gap sichtbar sein, nicht stillschweigend
    assert "## ⚠️ Coverage gaps" in report
    assert "exit-classes SSoT not found" in report


def test_should_flag_owner_ref_hint_in_workflow_file(tmp_path, monkeypatch):
    """Hardcoded owner-Referenz in einem Workflow-File muss als Warnung erscheinen (OOTB-5)."""
    responses = _base_responses()
    responses[f"/repos/{_ORG}/widget/contents/.github/workflows"] = (
        200,
        [{"name": "deploy.yml", "path": ".github/workflows/deploy.yml"}],
    )
    responses[f"/repos/{_ORG}/widget/contents/.github/workflows/deploy.yml"] = (
        200,
        b"uses: achimdehnert/platform/.github/workflows/_deploy.yml@v1\n",
    )
    monkeypatch.setattr(ep, "TOKEN", "fake-token")
    monkeypatch.setattr(ep, "api", _make_fake_api(responses))
    monkeypatch.setattr(ep, "EXIT_CLASSES", tmp_path / "does-not-exist.yaml")

    out_path = tmp_path / "runbook.md"
    monkeypatch.setattr(sys, "argv", ["exit-plan.py", _ORG, "--out", str(out_path)])

    rc = ep.main()

    assert rc == 0
    report = out_path.read_text(encoding="utf-8")
    assert "hardcoded" in report
    assert "deploy.yml" in report


def test_should_fail_when_org_unreadable(monkeypatch, capsys):
    """401/403 auf /orgs/{org} -> Exit 1 mit stderr-Fehlermeldung, kein Traceback."""
    def fake_api(path: str, raw: bool = False):
        if path.startswith(f"/orgs/{_ORG}"):
            return 403, None
        return 200, {}

    monkeypatch.setattr(ep, "TOKEN", "fake-token")
    monkeypatch.setattr(ep, "api", fake_api)
    monkeypatch.setattr(sys, "argv", ["exit-plan.py", _ORG])

    rc = ep.main()

    assert rc == 1
    captured = capsys.readouterr()
    assert "not readable" in captured.err


def test_should_require_gh_token():
    """Ohne GH_TOKEN (leerer TOKEN) darf main() nicht gegen die echte API laufen."""
    # TOKEN wird modul-global aus os.environ gelesen; direkt am Modul patchen
    # simuliert den fehlenden-Token-Zustand ohne echtes Environment anzufassen.
    import contextlib

    old = ep.TOKEN
    try:
        ep.TOKEN = ""
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = ep.main()
        assert rc == 2
        assert "GH_TOKEN not set" in buf.getvalue()
    finally:
        ep.TOKEN = old
