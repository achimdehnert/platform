#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt unbelegte Bescheinigungen in GitHub-Kommentaren.

GATE_HEADER (KONZ-038 D8):
  "slug": "claim-before-cheapest-check"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-01"
  "evidence": "tools/claude-hooks/tests/test_block_unbelegte_bescheinigung.py"

Hintergrund: platform#3656 (Retro 2c84188c §5a). Das Gate
`claim-before-cheapest-check` lief bis dahin nur als Stop-Hook
(`evidence_claim_scanner.py`) am Zugende — also NACH `gh pr comment` bzw.
`gh issue comment`. Zwei Rückfälle hat er gefangen, aber erst, als der Text
schon öffentlich stand:

  1. Ein Kommentar bescheinigte „Freigabe Merge … nach Vier-Augen-Review durch
     den Owner“. Belegt war nur ein knappes „go“ des Owners — kein Review.
  2. Ein Kommentar meldete „K1 ist erfüllt“ — ohne Kriterien-Abgleich.

Dieser Hook sitzt deshalb VOR dem Call. Er prüft `gh pr comment`,
`gh issue comment` und `gh pr review` (Body inline über `--body`/`-b`, als
Datei über `--body-file`/`-F`, auch von stdin per Heredoc) auf Bescheinigungen:
Review abgeschlossen, Vier-Augen, Freigabe, „erfüllt“, „geprüft“, Approve.
Steht im selben Text kein Beleg, wird der Call mit Begründung abgelehnt.

Als Beleg zählt (eins genügt):
  - Link auf einen GitHub-Kommentar oder ein Review
    (`#issuecomment-…`, `#pullrequestreview-…`, `#discussion_r…`),
  - eine Review-ID (`pullrequestreview-123`, `Review-ID 123`, `PRR_…`),
  - ein Link auf eine Nachricht außerhalb von GitHub (Owner-Nachricht),
  - ein Link auf einen CI-Lauf (`/actions/runs/…`) — trägt „geprüft“,
  - ein Kriterien-Abgleich: eine Tabelle mit Spalten „Kriterium“ und „Beleg“,
    oder je bescheinigter Kennung (K1, K2, …) eine Zeile mit Beleg-Marker
    (`Beleg`, `→`, `->`) und konkreter Referenz (URL, `#123`, `Code`, SHA).

Nicht als Bescheinigung gilt ein Satz, der verneint, bittet oder offen lässt
(„Review steht aus“, „bitte um Freigabe“, „noch nicht geprüft“, Fragesatz).

GRENZE, bewusst benannt: der Hook prüft, ob ein Beleg im Text STEHT, nicht ob er
die Bescheinigung TRÄGT — ein Link auf einen beliebigen Kommentar kommt durch.
Der Realfall war aber das Fehlen jedes Belegs, und das macht der Hook sichtbar,
bevor der Text öffentlich ist. Die inhaltliche Prüfung bleibt beim Stop-Hook.

FAIL-OPEN: kein JSON, kein passender gh-Aufruf, unlesbare Body-Datei ohne
Erzeugung im selben Befehl, jede unerwartete Ausnahme → exit 0 ohne Ausgabe.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "claim-before-cheapest-check"
#: Obergrenze für gelesene Body-Dateien — ein Kommentar ist kein Datensatz.
MAX_BODY_BYTES = 200_000

_GH_CALL = re.compile(
    r"(?:^|[;&|(\n]|\$\()\s*gh\s+(?:(?:pr|issue)\s+comment|pr\s+review)\b"
)
_TRENNER = {";", "&&", "||", "|", "&", "(", ")", "\n"}

# --- Bescheinigungen -------------------------------------------------------
_U = r"(?:ü|ue)"
BESCHEINIGUNG_RE = re.compile(
    r"vier-augen"
    r"|\bfreigabe\b|\bfreigegeben\b"
    rf"|\berf{_U}llt\b"
    rf"|\b(?:gegen)?gepr{_U}ft\b"
    r"|\breviewt\b|\breviewed\b|\bapproved\b|\blgtm\b"
    r"|\breview\s+(?:durch|von|erfolgt|abgeschlossen|bestanden|ok|ohne\s+befund)"
    rf"|\breview\s+(?:ist\s+)?durchgef{_U}hrt",
    re.I,
)
#: Satz verneint, bittet, fragt oder lässt offen — dann keine Bescheinigung.
_OFFEN_RE = re.compile(
    r"\bnicht\b|\bnoch\s+kein|\bkein(?:e|en)?\b|steht\s+(?:noch\s+)?aus|ausstehend"
    r"|\boffen\b|\bbitte\b|\bwartet\b|\bangefragt\b|\berbeten\b|\bsobald\b|\bfalls\b"
    r"|\?",
    re.I,
)
_SATZ_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_K_LABEL = re.compile(r"\bK(\d{1,2})\b")

# --- Belege ----------------------------------------------------------------
_URL = re.compile(r"https?://[^\s)>\]\"'`]+", re.I)
_GH_ANKER = re.compile(r"#(?:issuecomment-\d+|pullrequestreview-\d+|discussion_r\d+)")
_REVIEW_ID = re.compile(
    r"\bpullrequestreview-\d+|\breview-id\s*[:#]?\s*\d+|\bPRR_\w{6,}", re.I
)
_RUN_LINK = re.compile(r"github\.com/[^\s]+/actions/runs/\d+", re.I)
_REFERENZ = re.compile(r"https?://\S+|#\d+\b|`[^`\n]+`|\b[0-9a-f]{7,40}\b")
_BELEG_MARKER = re.compile(r"beleg|→|->", re.I)
_TABELLEN_KOPF = re.compile(r"^\s*\|.*kriteri.*\|.*beleg.*\|", re.I | re.M)


def _ist_github(url: str) -> bool:
    return bool(re.match(r"https?://(?:[\w-]+\.)*github(?:usercontent)?\.com/", url, re.I))


def bescheinigungen(text: str) -> list[str]:
    """Sätze, die etwas bescheinigen und es nicht offen lassen."""
    treffer = []
    for satz in _SATZ_SPLIT.split(text or ""):
        satz = satz.strip()
        if satz and BESCHEINIGUNG_RE.search(satz) and not _OFFEN_RE.search(satz):
            treffer.append(satz)
    return treffer


def _kriterien_abgleich(text: str, kennungen: set[str]) -> bool:
    if _TABELLEN_KOPF.search(text):
        return True
    if not kennungen:
        return False
    gedeckt = set()
    for zeile in text.splitlines():
        if _BELEG_MARKER.search(zeile) and _REFERENZ.search(zeile):
            gedeckt |= set(_K_LABEL.findall(zeile))
    return kennungen <= gedeckt


def hat_beleg(text: str, saetze: list[str]) -> bool:
    if _GH_ANKER.search(text) or _REVIEW_ID.search(text) or _RUN_LINK.search(text):
        return True
    if any(not _ist_github(u) for u in _URL.findall(text)):
        return True
    kennungen = {k for s in saetze for k in _K_LABEL.findall(s)}
    return _kriterien_abgleich(text, kennungen)


# --- Befehl zerlegen -------------------------------------------------------
def _lies_datei(pfad: str) -> str:
    if "$" in pfad:
        return ""
    p = Path(os.path.expanduser(pfad))
    try:
        if p.is_file():
            return p.read_bytes()[:MAX_BODY_BYTES].decode("utf-8", "replace")
    except OSError:
        pass
    return ""


def _datei_body(pfad: str, kommando: str, gh_start: int) -> str:
    """Inhalt der Body-Datei; wird sie im selben Befehl erzeugt, zählt der
    Befehlstext davor mit (zum Zeitpunkt von PreToolUse liegt sie noch alt oder
    gar nicht auf Platte)."""
    teile = [_lies_datei(pfad)]
    name = os.path.basename(pfad)
    if name and kommando.rfind(name, 0, gh_start) >= 0:
        teile.append(kommando[:gh_start])
    return "\n".join(t for t in teile if t)


def _aufrufe_shlex(kommando: str):
    """(tokens nach `gh … comment|review`) je Aufruf, oder None bei Parse-Fehler."""
    try:
        lex = shlex.shlex(kommando, posix=True, punctuation_chars=";&|()")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None
    aufrufe = []
    for i, tok in enumerate(tokens):
        if tok != "gh" or (i > 0 and tokens[i - 1] not in _TRENNER and not tokens[i - 1].endswith("$(")):
            continue
        rest = tokens[i + 1 : i + 3]
        if rest in (["pr", "comment"], ["issue", "comment"], ["pr", "review"]):
            args = []
            for t in tokens[i + 3 :]:
                if t in _TRENNER:
                    break
                args.append(t)
            aufrufe.append(args)
    return aufrufe


def _body_aus_args(args: list[str], kommando: str, gh_start: int, tail: str) -> tuple[str, bool]:
    """(Body-Text, approve?) aus den Argumenten eines Aufrufs."""
    teile, approve = [], False
    it = iter(range(len(args)))
    for i in it:
        a = args[i]
        if a in ("--approve", "-a"):
            approve = True
        wert = None
        for flag in ("--body", "-b", "--body-file", "-F"):
            if a == flag and i + 1 < len(args):
                wert = (flag, args[i + 1])
                next(it, None)
            elif a.startswith(flag + "=") and flag.startswith("--"):
                wert = (flag, a[len(flag) + 1 :])
        if not wert:
            continue
        flag, v = wert
        if flag in ("--body", "-b"):
            teile.append(v)
        elif v == "-":
            teile.append(tail)
        else:
            teile.append(_datei_body(v, kommando, gh_start))
    return "\n".join(teile), approve


def bodies(kommando: str) -> list[tuple[str, bool]]:
    """Je gh-Kommentar/Review-Aufruf: (Body-Text, approve?)."""
    starts = [m.start() for m in _GH_CALL.finditer(kommando)]
    if not starts:
        return []
    aufrufe = _aufrufe_shlex(kommando)
    ergebnis = []
    if aufrufe is not None and len(aufrufe) == len(starts):
        for start, args in zip(starts, aufrufe):
            ergebnis.append(_body_aus_args(args, kommando, start, kommando[start:]))
        return ergebnis
    # Rückfall (Shell-Text nicht zerlegbar, z. B. Apostroph im Heredoc): der
    # Rohtext ab dem Aufruf ist der Body, eine genannte Datei wird gelesen.
    for start in starts:
        roh = kommando[start:]
        teile = [roh]
        for datei in re.findall(r"(?:--body-file|-F)(?:\s+|=)(\"[^\"]*\"|'[^']*'|\S+)", roh):
            datei = datei.strip("\"'")
            if datei != "-":
                teile.append(_datei_body(datei, kommando, start))
        ergebnis.append(("\n".join(teile), bool(re.search(r"--approve\b|\s-a\b", roh))))
    return ergebnis


def entscheide(kommando: str) -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    for text, approve in bodies(kommando):
        saetze = bescheinigungen(text)
        if approve:
            saetze.append("gh pr review --approve")
        if saetze and not hat_beleg(text, saetze):
            return saetze[0][:120]
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(daten, dict):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _GH_CALL.search(kommando):
        return 0
    grund = entscheide(kommando)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "pretooluse bescheinigung",
            beleg=grund,
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Unbelegte Bescheinigung (Gate {SLUG}, platform#3656): „{grund}“. "
                "Ein öffentlicher Kommentar, der Review, Vier-Augen, Freigabe, "
                "„erfüllt“ oder „geprüft“ bescheinigt, braucht den Beleg im selben "
                "Text: Link auf den Kommentar bzw. die Owner-Nachricht, eine Review-ID "
                "oder einen Kriterien-Abgleich (je Kennung eine Zeile mit Beleg und "
                "Referenz). Ohne Beleg die Aussage abschwächen auf das, was belegt ist "
                "— etwa „Owner: go“ statt „nach Vier-Augen-Review“."
            ),
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


def main_sicher() -> int:
    """Hook-Vertrag: Exit 0 immer, außer bewusstes Blocken (das läuft über JSON)."""
    try:
        return main()
    except Exception:  # noqa: BLE001 — fail-open, ein toter Hook blockt jeden Call
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
