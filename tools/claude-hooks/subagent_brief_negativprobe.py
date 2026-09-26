#!/usr/bin/env python3
"""Claude Code PreToolUse(Agent) hook — Sicherheits-/Datenschutz-Kriterium im
Delegations-Brief ohne Negativ-Probe (Slug `check-ohne-positivkontrolle`).

Realfall (Retro `docs/retros/session-retro-2026-09-17-meiki-hub-8185e1.md`,
Befund #1): der Delegations-Brief post-hub#22 Ziel 3 verlangte "Projektion
strikt auf die Vertragsfelder; alles andere wird verworfen und nie geloggt".
Der Sonnet-Subagent baute stattdessen `raw.update(fachlich)`
(post-hub#23 `be10bda`) — `tenant_id`/`source` waren damit ueberschreibbar,
Klartext-Fremdfelder liefen ungefiltert durch — und meldete "alle sechs Ziele
erfuellt". Gefangen wurde es NICHT vom eigenen Test des Subagenten, sondern
erst per Review (`9a3c085`). Dritte Zaehlung von `check-ohne-positivkontrolle`
in `tools/retro_kpis.py` (Sessions 40c069, a397a5, 8185e1), bisher OHNE
registriertes Gate.

Derselbe Musterfehler wie tags zuvor (Melder ohne Positivkontrolle,
`eigene-melder-brauchen-positivkontrolle`): ein Kriterium, das nur den
Happy-Path prueft, kann den Happy-Path immer "erfuellt" melden. Ein
Sicherheits-/Datenschutz-KRITERIUM im Brief hat dasselbe Problem eine Ebene
frueher — ohne eine vorgeschriebene Negativ-Probe ("Test zeigt, dass X NICHT
ankommt") kann der Subagent dieselbe Selbstauskunft geben, ohne den
schaedlichen Fall je durchgespielt zu haben.

WAS DER HOOK PRUEFT
--------------------
1. Findet **Schutz-Kriterien** im Brief: Zeilen/Saetze mit `strikt`, `nie`,
   `niemals`, `kein(e) Schreib-/Upload-/Delete-/Loesch-…`, `nicht
   durchreichen`, `nur lesend`, `verworfen`, `nie geloggt`, `ohne
   Schreibfunktion`, `Allowlist`, `Projektion` (Liste in `SCHUTZ_MUSTER`,
   Wortgrenzen, bewusst eng — lieber ein uebersehenes Kriterium als viele
   Fehlalarme).
2. Prueft, ob DERSELBE Brief irgendwo eine **Negativ-Probe** verlangt: eine
   Zeile mit `Test` UND einer Verneinung (`nicht ankommt`/`durchkommt`/
   `moeglich`, `nichts … kommt an`, `abgewiesen`, `verworfen wird`, `keine …
   (ab)gesetzt`, `rot wird`, `Mutationstest`).
3. Fehlt sie bei mindestens einem gefundenen Schutz-Kriterium: advisory
   Meldung auf stdout, Exit 0 — nie blockieren.

FAIL-OPEN (bewusste Grenze, wie `subagent_brief_gate.py`): kein JSON, kein
Brief, Lese-Agenten (`Explore`, `Plan`, `claude-code-guide`). Der Hook liest
den BRIEF, nicht das ERGEBNIS: er erzwingt die FORDERUNG nach einer
Negativ-Probe, nicht dass der Subagent sie tatsaechlich schreibt oder dass
sie rot wird, bevor sie gruen wird. Ein Brief, der die Probe nur behauptet
("Test: alles gut") ohne echten Verneinungs-Bezug, faellt weiterhin durch
dieses Netz — dagegen hilft nur Review, nicht dieser Hook.

GATE-HEADER (KONZ-038 D8, maschinenlesbar):
mode=advisory BEWUSST: neue Musterfamilie ohne False-Positive-Baseline
(dieselbe SUGGEST-first-Disziplin wie bei den uebrigen `*_scanner.py`).

Contract: PreToolUse(Agent/Task)-Event-JSON auf stdin, IMMER Exit 0. Modus
**advisory**: Klartext auf stdout, KEIN `hookSpecificOutput`/JSON — PreToolUse
kennt `additionalContext` nicht, nur `permissionDecision`
(`allow`=stumm/`ask`=haelt an/`deny`=blockt); keine der drei Formen ist "Hinweis
ohne Anhalten". Derselbe bereits belegte Weg wie
`cd_fehlschlag_ketten_scanner.py` und `tools/hooks/foreign_clone_check.sh`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

GATE_HEADER = {
    "slug": "check-ohne-positivkontrolle",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-17",
    "evidence": "tools/claude-hooks/tests/test_subagent_brief_negativprobe.py",
}

SLUG = GATE_HEADER["slug"]

#: Tool-Namen, unter denen Claude Code Subagenten startet (alt: Task) —
#: identisch zu subagent_brief_gate.py, derselbe Delegationspunkt.
TOOL_NAMEN = {"Agent", "Task"}
#: Subagent-Typen, die nicht schreiben — kein Umsetzungs-Brief, fail-open.
LESE_TYPEN = {"explore", "plan", "claude-code-guide"}

#: Schutz-Kriterien: (Label, Muster). Bewusst eng, Wortgrenzen ueberall —
#: eine breite Liste erraeten natuersprachlicher Synonyme wuerde die
#: Fehlalarmquote treiben, ohne den Realfall besser zu treffen. Jeder Eintrag
#: ist ein Wort/eine Wendung, die im Realfall post-hub#22 Ziel 3 ODER in den
#: ueblichen Sicherheits-/Datenschutz-Formulierungen dieses Repos vorkommt
#: (vgl. `block_env_cat.sh`-Reasons: "nur lesend", "Allowlist").
SCHUTZ_MUSTER: list[tuple[str, re.Pattern[str]]] = [
    ("strikt", re.compile(r"\bstrikt\b", re.IGNORECASE)),
    ("niemals", re.compile(r"\bniemals\b", re.IGNORECASE)),
    ("nie", re.compile(r"\bnie\b", re.IGNORECASE)),
    (
        "kein-schreib-upload-delete-loesch",
        re.compile(
            r"\bkeine?\b[^\n.;]{0,20}\b"
            r"(Schreib\w*|Upload\w*|Delete\b|L(?:ö|oe)sch\w*)\b",
            re.IGNORECASE,
        ),
    ),
    ("nicht-durchreichen", re.compile(r"nicht\s+durchreichen", re.IGNORECASE)),
    ("nur-lesend", re.compile(r"\bnur\s+lesend\b", re.IGNORECASE)),
    ("verworfen", re.compile(r"\bverworfen\b", re.IGNORECASE)),
    ("nie-geloggt", re.compile(r"\bnie\s+geloggt\b", re.IGNORECASE)),
    ("ohne-schreibfunktion", re.compile(r"\bohne\s+Schreibfunktion\b", re.IGNORECASE)),
    ("allowlist", re.compile(r"\ballowlist\b", re.IGNORECASE)),
    ("projektion", re.compile(r"\bprojektion\b", re.IGNORECASE)),
]

#: Negativ-Probe: eine VERNEINUNG, wie sie ein Test benennt, der einen
#: schaedlichen Fall abweist. Absichtlich mehrere Formen, weil ein einzelnes
#: Wortmuster (z.B. nur "nicht ankommt") den Realfall-Gegenbeweis der
#: Retro (Zeile "Test: … — nichts davon kommt an") nicht getroffen haette.
NEGATIVPROBE_MUSTER = re.compile(
    r"nicht\s+\w*(?:ankomm|durchkomm|m(?:ö|oe)glich)\w*"
    r"|nichts\b.{0,60}\bkommt\s+an\b"
    r"|\babgewiesen\b"
    r"|verworfen\s+wird"
    r"|keine\b.{0,40}\b(?:ab)?gesetzt\b"
    r"|\brot\s+wird\b"
    r"|\bMutationstest\b",
    re.IGNORECASE,
)

#: Zeilen, die ueberhaupt als "Test-Zeile" zaehlen — nur dort wird nach der
#: Verneinung gesucht (sonst wuerde z.B. "niemals absetzt" im Fliesstext ohne
#: Testbezug faelschlich als Probe gelten).
_TEST_ZEILE = re.compile(r"\btest(?:s|et|et\s+werden)?\b", re.IGNORECASE)


def finde_schutz_kriterien(prompt: str) -> list[tuple[str, str]]:
    """Alle (Label, Zeile) mit einem Schutz-Kriterium — Reihenfolge des Briefs."""
    treffer: list[tuple[str, str]] = []
    for zeile in prompt.splitlines():
        zeile_ohne_ws = zeile.strip()
        if not zeile_ohne_ws:
            continue
        for label, muster in SCHUTZ_MUSTER:
            if muster.search(zeile_ohne_ws):
                treffer.append((label, zeile_ohne_ws))
                break  # eine Zeile zaehlt einmal, auch bei mehreren Treffern
    return treffer


def hat_negativprobe(prompt: str) -> bool:
    """Verlangt der Brief IRGENDWO eine Negativ-Probe (Test + Verneinung)?"""
    for zeile in prompt.splitlines():
        if not _TEST_ZEILE.search(zeile):
            continue
        if NEGATIVPROBE_MUSTER.search(zeile):
            return True
    return False


def entscheide(prompt: str) -> str | None:
    """Meldungstext oder None. Reiner Text-Check, keine Seiteneffekte."""
    if not prompt or not prompt.strip():
        return None
    kriterien = finde_schutz_kriterien(prompt)
    if not kriterien:
        return None  # kein Schutz-Kriterium im Brief — nichts zu verlangen
    if hat_negativprobe(prompt):
        return None
    _label, satz = kriterien[0]
    zitat = satz if len(satz) <= 160 else satz[:157] + "…"
    return (
        "Brief nennt Schutz-Kriterium '" + zitat + "' ohne Negativ-Probe — "
        'verlange: "Test zeigt, dass <schädlicher Fall> NICHT ankommt" und den '
        "Testnamen in der Rückmeldung (Gate check-ohne-positivkontrolle, "
        "Retro 8185e1 #1)."
    )


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(daten, dict):
        return 0
    tool_name = daten.get("tool_name")
    if tool_name and tool_name not in TOOL_NAMEN:
        return 0
    eingabe = daten.get("tool_input")
    if not isinstance(eingabe, dict):
        return 0
    if str(eingabe.get("subagent_type") or "").lower() in LESE_TYPEN:
        return 0
    prompt = eingabe.get("prompt")
    if not isinstance(prompt, str):
        return 0

    grund = entscheide(prompt)
    if grund is None:
        return 0

    session = str(daten.get("session_id") or "")
    gate_hits.notiere(
        SLUG, grund[:200], turn=prompt[:400], session=session, modus="advisory"
    )

    print(f"🛡 {SLUG}: {grund} (advisory, blockiert diesen Aufruf nicht.)")
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer, ausser bewusstes Blocken.

    Bewusst dupliziert statt geteilt, siehe `cd_fehlschlag_ketten_scanner.
    main_sicher` — der Auffangbogen soll keinen Import brauchen.
    """
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(
            f"subagent_brief_negativprobe: {type(exc).__name__}: {exc}"[:400],
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
