"""Repro-Test für SEC-4 (Issue #1198, `/repo-optimize` 2026-07-16).

Befund: `.github/workflows/secret-prevention-audit.yml` enumeriert alle Repos des
Owners über `/user/repos` (Primärpfad) mit Fallback auf `/users/{owner}/repos`
(Token ohne User-Scope). Wenn BEIDE Endpunkte fehlschlagen (Auth-Fehler,
API-Ausfall) — also die Enumeration selbst nicht funktioniert, nicht "0 Repos
gefunden, weil der Filter zu eng ist" — loggte das Skript `::error::` und rief
danach trotzdem `sys.exit(0)` auf. CI zeigte grün, obwohl nichts geprüft wurde
("run-conclusion ≠ tool-health"-Muster).

Dieser Test extrahiert das eingebettete Python (`python3 - <<'PY' ... PY`) direkt
aus der YAML (kein Duplikat/keine Abschrift) und führt es im selben Prozess via
`exec()` aus, mit einem monkeygepatchten `urllib.request.urlopen`, das für
`/user/repos` UND den `/users/{owner}/repos`-Fallback einen HTTP-500 simuliert.
Vor dem Fix (SEC-4) hätte `test_should_exit_nonzero_on_total_enumeration_failure`
fehlgeschlagen, weil das Skript trotz simuliertem Totalausfall `SystemExit(0)`
geworfen hätte (bzw. gar kein `SystemExit` — der alte Code rief `sys.exit(0)`,
was `SystemExit(0)` ist).

Eine zweite Testfunktion belegt die Gegenprobe: "0 Repos, weil erste Seite leer
zurückkommt" (kein API-Fehler) bleibt legitim ein sauberer Lauf ohne
`SystemExit` — der Fix darf diesen Pfad nicht anfassen.

Run: `python3 -m pytest tools/tests/test_secret_prevention_audit_enumeration_gate.py -q`
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "secret-prevention-audit.yml"


def _extract_embedded_python() -> str:
    """Zieht den Python-Code aus `python3 - <<'PY' ... PY` im 'audit'-Job."""
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    run = wf["jobs"]["audit"]["steps"][0]["run"]
    assert "<<'PY'" in run, "erwartetes Heredoc-Muster nicht gefunden — Workflow umstrukturiert?"
    body = run.split("<<'PY'\n", 1)[1]
    assert body.rstrip().endswith("PY"), "Heredoc-Ende 'PY' nicht gefunden"
    return body.rstrip()[: -len("PY")]


def _http_error(url: str, code: int, payload: bytes = b"{}") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "simulated failure", {}, io.BytesIO(payload))


class _FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _run(monkeypatch, tmp_path, urlopen_fn) -> None:
    code = _extract_embedded_python()
    monkeypatch.setattr(urllib.request, "urlopen", urlopen_fn)
    monkeypatch.setenv("OWNER", "achimdehnert")
    monkeypatch.setenv("GH_TOKEN", "fake-token-for-test")
    monkeypatch.setenv("MARKER_LABEL", "adr-235-audit")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    monkeypatch.delenv("FAIL_ON_GAP", raising=False)
    exec(compile(code, str(WORKFLOW), "exec"), {"__name__": "__main__"})


def test_should_exit_nonzero_on_total_enumeration_failure(monkeypatch, tmp_path):
    def fake_urlopen(req, *a, **kw):
        # Sowohl /user/repos (Primärpfad) als auch der /users/{owner}/repos
        # Fallback schlagen fehl -> Enumeration ist ein Totalausfall.
        assert "/user/repos" in req.full_url or "/users/achimdehnert/repos" in req.full_url
        raise _http_error(req.full_url, 500)

    with pytest.raises(SystemExit) as exc_info:
        _run(monkeypatch, tmp_path, fake_urlopen)

    assert exc_info.value.code != 0, (
        "SEC-4 Regression: Totalausfall der Enumeration meldet Exit 0 "
        f"(SystemExit.code={exc_info.value.code!r}) statt eines Fehlers."
    )


def test_should_not_raise_when_zero_repos_is_a_legitimate_empty_result(monkeypatch, tmp_path):
    """Gegenprobe: leere erste Seite (kein Fehler) darf NICHT als Totalausfall gelten."""

    def fake_urlopen(req, *a, **kw):
        url = req.full_url
        if "/user/repos" in url:
            return _FakeResponse(200, b"[]")
        if "/issues?state=open" in url:
            return _FakeResponse(200, b"[]")
        raise AssertionError(f"unerwarteter Call im Leer-Ergebnis-Pfad: {url}")

    # Kein SystemExit erwartet -> normales Skript-Ende.
    _run(monkeypatch, tmp_path, fake_urlopen)
