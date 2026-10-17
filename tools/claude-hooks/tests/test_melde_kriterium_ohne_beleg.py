"""Drill fuer melde_kriterium_ohne_beleg.py (Gate kriterium-teilerfuellt-als-erfuellt-gemeldet).

Realfall: Retro 5c34f2 Befund 1. Kommentar 6218686626 im Ledger
achimdehnert/platform#4018 (2026-10-16 15:20 UTC) empfahl S7 als bestanden;
Teil 2 des Kill-Kriteriums war ungemessen. REALFALL ist dieser Kommentar ohne
die Fusszeile (Kontrollprobe: roh 2 Kennungen, Link und Host der Fusszeile →
bereinigt 0; keine Projekt-IDs, Konten oder Adressen).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

_HOOK = Path(__file__).resolve().parent.parent / "melde_kriterium_ohne_beleg.py"
_spec = importlib.util.spec_from_file_location("melde_kriterium_ohne_beleg", _HOOK)
hook = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hook  # dataclass sucht sein Modul in sys.modules
_spec.loader.exec_module(hook)

REGELN = hook.lade()
MANDAT = "gh issue comment 4018 --repo achimdehnert/platform"

REALFALL = """**S7 Nachtrag: TestPyPI erkennt das Google-Token als gültig (2026-10-16)**

Ein dritter Lauf gibt jetzt auch den Fehlertext von TestPyPI aus:

> `invalid-publisher`: valid token, but no corresponding publisher (Publisher with matching claims was not found)

TestPyPI hat das Token also geprüft und angenommen. Gescheitert ist der Lauf nur, weil kein Publisher-Eintrag zur Dienstkonto-Adresse existiert. Der Zuordnungsschritt ist der normale Google-Weg der Trusted Publishers und hängt nicht mehr an Forgejo.

Korrektur zu meinem letzten Vorschlag: Ich hatte unterstellt, dass der Owner ein TestPyPI-Konto hat. Das hatte ich nicht geprüft, und es trifft nicht zu. TestPyPI ist ein eigenes Konto, unabhängig von PyPI.

Empfehlung: S7 gilt bis zur Publisher-Zuordnung als bestanden. Den Rest (Eintrag + Upload) holt der erste echte Stufe-2-Release nach, falls es eine Stufe 2 gibt. Die Owner-Entscheidung läuft als „SG go“."""

KRITERIUM = """Kill-Kriterium S7 (Einsatzkonzept §2), im Wortlaut:

> - Upload per Trusted Publishing ohne gespeichertes Token
> - Upload nur von einem geschützten Tag
"""

BELEGT = KRITERIUM + """
| Teil | Messung |
|---|---|
| Teil 1 | Token-Tausch STS 200, Lauf https://example.invalid/run/7 |
| Teil 2 | `ref_protected` 'true' in 2 von 2 Läufen, STS 200 |

Empfehlung: S7 bestanden, Owner-Entscheidung als „SG go“."""

TEILERFUELLT = KRITERIUM + """
- Teil 1: Token-Tausch STS 200, Lauf https://example.invalid/run/7
- Teil 2: noch nicht gemessen

Empfehlung: S7 gilt als bestanden."""


def _daten(kommando: str, cwd: str = "/tmp") -> dict:
    return {"tool_input": {"command": kommando}, "cwd": cwd}


def _mcp(name: str, **eingabe) -> dict:
    return {"tool_name": f"mcp__github__{name}", "tool_input": eingabe}


def _hinweis(daten: dict) -> str | None:
    return hook.befund(daten, REGELN)[0]


def test_should_keep_realfall_fixture_free_of_identifiers():
    """Invariante zur Kontrollprobe: keine Mailadresse, kein Host, keine lange Nummer, kein Link."""
    for muster in (r"[\w.+-]+@[\w-]+\.\w", r"https?://", r"\b\d{6,}\b", r"\.(?:localhost|pet|com|de)\b"):
        assert not re.search(muster, REALFALL), muster


def test_should_report_the_real_recommendation_from_body_file(tmp_path):
    """Positivkontrolle: Realfall, gepostet wie damals per -F datei."""
    (tmp_path / "c.md").write_text(REALFALL)
    hinweis = _hinweis(_daten(f"{MANDAT} -F c.md", str(tmp_path)))
    assert hinweis is not None
    assert "achimdehnert/platform#4018" in hinweis
    assert "nicht im Wortlaut zitiert" in hinweis


def test_should_stay_silent_on_correctly_evidenced_comment(tmp_path):
    """Gegenprobe: Kriterium zitiert, je Teil ein Beleg."""
    (tmp_path / "c.md").write_text(BELEGT)
    assert _hinweis(_daten(f"{MANDAT} -F c.md", str(tmp_path))) is None


def test_should_report_quoted_criterion_with_unmeasured_part():
    """Der namensgebende Fall: Zitat da, Teil 2 ohne Beleg, trotzdem „bestanden“."""
    hinweis = _hinweis(_daten(f"{MANDAT} --body {shlex.quote(TEILERFUELLT)}"))
    assert hinweis is not None
    assert "Teil 2 ohne Beleg" in hinweis and "Teil 1 ohne Beleg" not in hinweis


def test_should_accept_single_part_inline_quote_with_measurement():
    text = "Kriterium K5: „0 Nachläufe wegen hinter main je Bot-Welle“ — gemessen 0 von 4 Wellen, K5 erfüllt."
    assert _hinweis(_daten(f"{MANDAT} --body {shlex.quote(text)}")) is None
    ohne = "Kriterium K5: „0 Nachläufe wegen hinter main je Bot-Welle“ — K5 erfüllt."
    assert "kein Beleg" in _hinweis(_daten(f"{MANDAT} --body {shlex.quote(ohne)}"))


def test_should_stay_silent_without_signal_or_on_negation():
    """Gegenproben aus der Zielpopulation (154 Kommentare der Mandats-Issues, 2026-10-17)."""
    for text in (
        "S7 Teil 2 ist rot, Ersatz folgt.",
        "S7 gilt nicht als bestanden.",
        "K2 nicht erfüllt.",
        "K7 gemergt, CI 15 bestanden, 2 übersprungen.",
        "Vorbedingung je Repo erfüllt, Liste folgt.",
        "Freigabe erst, bis Kriterien 6–7 bestanden sind.",
    ):
        assert _hinweis(_daten(f"{MANDAT} --body {shlex.quote(text)}")) is None, text


def test_should_ignore_issues_outside_the_mandate_list():
    kommando = f"gh issue comment 4017 --repo achimdehnert/platform --body {shlex.quote(REALFALL)}"
    assert _hinweis(_daten(kommando)) is None
    fremd = f"gh issue comment 4018 --repo achimdehnert/dev-hub --body {shlex.quote(REALFALL)}"
    assert _hinweis(_daten(fremd)) is None


def test_should_ignore_reading_and_create_commands():
    for kommando in (
        "gh issue view 4018 --repo achimdehnert/platform --comments",
        f"gh issue create --repo achimdehnert/platform --title t --body {shlex.quote(REALFALL)}",
    ):
        assert _hinweis(_daten(kommando)) is None, kommando


def test_should_resolve_issue_url_and_cwd_remote(tmp_path):
    url = f"gh issue comment https://github.com/achimdehnert/platform/issues/4018 --body {shlex.quote(REALFALL)}"
    assert _hinweis(_daten(url)) is not None
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "git@github.com:achimdehnert/platform.git"],
        check=True,
    )
    assert _hinweis(_daten(f"gh issue comment 4018 --body {shlex.quote(REALFALL)}", str(tmp_path))) is not None


def test_should_read_heredoc_for_stdin_body():
    kommando = f"{MANDAT} -F - <<'EOF'\n{REALFALL}\nEOF"
    assert _hinweis(_daten(kommando)) is not None
    gegen = f"{MANDAT} -F - <<'EOF'\n{BELEGT}\nEOF"
    assert _hinweis(_daten(gegen)) is None


def test_should_report_mcp_comment_and_body_edit():
    for name in ("add_issue_comment", "update_issue"):
        daten = _mcp(name, owner="achimdehnert", repo="platform", issue_number=4018, body=REALFALL)
        assert _hinweis(daten) is not None, name
    gegen = _mcp("add_issue_comment", owner="achimdehnert", repo="platform", issue_number=4018, body=BELEGT)
    assert _hinweis(gegen) is None
    fremd = _mcp("add_issue_comment", owner="achimdehnert", repo="platform", issue_number=1, body=REALFALL)
    assert _hinweis(fremd) is None


def _lauf(eingabe: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=eingabe, capture_output=True, text=True, env=env, timeout=30
    )


def test_should_emit_advisory_hint_never_deny_end_to_end(tmp_path):
    """Echter Prozess: Hinweis auf stdout, keine permissionDecision, Exit 0."""
    (tmp_path / "c.md").write_text(REALFALL)
    res = _lauf(json.dumps(_daten(f"{MANDAT} -F {tmp_path / 'c.md'}")))
    assert res.returncode == 0
    antwort = json.loads(res.stdout)
    assert "permissionDecision" not in antwort["hookSpecificOutput"]
    assert hook.SLUG in antwort["systemMessage"]
    assert hook.SLUG in antwort["hookSpecificOutput"]["additionalContext"]


def test_should_log_hint_failure_and_unchecked_text_separately(tmp_path):
    """Echter Prozess: Parse-Fehler -> `fehler`, `-F -` ohne Quelle -> `ungeprueft`, Treffer -> `meldung`."""
    log = tmp_path / "hits.jsonl"
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    env["GATE_HITS_DATEI"] = str(log)
    (tmp_path / "c.md").write_text(REALFALL)
    for eingabe in (
        "kein json",
        json.dumps(_daten(f"{MANDAT} -F -")),
        json.dumps(_daten(f"{MANDAT} -F {tmp_path / 'c.md'}")),
    ):
        assert _lauf(eingabe, env).returncode == 0
    zeilen = [json.loads(z) for z in log.read_text().splitlines()]
    assert [z.get("marker") for z in zeilen] == ["fehler", "ungeprueft", "meldung"]
    assert all(z.get("slug") == hook.SLUG and z.get("modus") == "advisory" for z in zeilen[1:])


def test_should_count_broken_rules_file_as_failure(tmp_path, monkeypatch):
    """Kaputte Regeldatei: gezaehlt und gemeldet, nicht still (platform#3862 Fund 5)."""
    kaputt = tmp_path / "regeln.json"
    kaputt.write_text("{")
    monkeypatch.setattr(hook, "REGELN", kaputt)
    monkeypatch.setattr(hook, "lade", lambda pfad=kaputt: json.loads(pfad.read_text()))
    gemeldet = []
    monkeypatch.setattr(hook, "_notiere", lambda marker, daten, beleg="": gemeldet.append(marker))
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(_daten(f"{MANDAT} --body x"))))
    assert hook.main() == 0
    assert gemeldet == ["fehler"]
