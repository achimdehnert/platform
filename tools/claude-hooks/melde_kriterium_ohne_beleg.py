#!/usr/bin/env python3
"""PreToolUse(Bash|mcp__github__.*) — meldet „bestanden“/„go“ zu einem Kriterium ohne Zitat und Beleg je Teil.

GATE_HEADER (KONZ-038 D8):
  "slug": "kriterium-teilerfuellt-als-erfuellt-gemeldet"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-17"
  "evidence": "tools/claude-hooks/tests/test_melde_kriterium_ohne_beleg.py"

Anlass Retro 5c34f2 Befund 1 (§6 M5, Mandat #4018 „KG go“): Im Ledger #4018
empfahl ein Kommentar S7 als bestanden; die Owner-Entscheidung fiel darauf.
Teil 2 des Kill-Kriteriums (Upload nur von geschuetztem Tag) war ungemessen und
wurde danach rot. Die Korrektur kam erst nach der Entscheidung. Dieser Haken
sitzt deshalb an der EMPFEHLUNG, also beim Schreiben des Kommentars.

Er meldet einen Text an ein Mandats-Issue, wenn der Text ein Kriterium als
bestanden oder erfuellt meldet oder „go“ empfiehlt (in einer Zeile mit
Kriteriumsbezug: Kuerzel wie K4/G1/S7, „Kriterium“ oder „Teil N“) und dabei
  * das Kriterium nicht im Wortlaut zitiert (Blockzitat `> …` direkt unter der
    Zeile mit „Kriterium“, oder „…“ in derselben Zeile), oder
  * nicht je Teil einen Beleg nennt: Teile sind die Listenpunkte im Zitat; je
    Teil N braucht es ausserhalb des Zitats eine Zeile mit „Teil N“ und einem
    Link oder Messwert. Ein Zitat ohne Liste ist ein Teil, dann genuegt ein
    Beleg irgendwo im Text.

Mandats-Issues, Signalwoerter und Beleg-Muster stehen in
`kriterium_meldung_regeln.json` neben diesem Haken, nicht im Code.

Texterfassung aus `block_aufschub_ohne_anker` (`--body`, `-F datei`, `-F -`
mit Heredoc/Pipe/Umleitung, `$(cat datei)`, MCP `body`) — kein zweiter Parser.

MODUS advisory: Hinweis als systemMessage + additionalContext, nie deny. Neue
Gates starten so (platform#4061); scharf schaltet ein eigener PR nach der
Auswertung der Meldungen.

FAIL-Verhalten: fail-open, aber gezaehlt. Kaputte Regeldatei oder Ausnahme ⇒
Marker `fehler` in gate_hits plus Hinweis; nicht lesbarer Text ⇒ `ungeprueft`.

GRENZEN: Ziel ohne `--repo` wird ueber `git remote` des cwd bestimmt. Eine
Kette mit mehreren gh-Befehlen gilt als Ganzes: zielt einer auf ein
Mandats-Issue, werden alle Texte der Kette geprueft. Ob ein Beleg den Teil
wirklich traegt, prueft der Haken nicht — nur, dass einer genannt ist.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from block_aufschub_ohne_anker import _MCP_GITHUB, _SCHREIBEN, erhebe, mcp_texte  # noqa: E402

SLUG = "kriterium-teilerfuellt-als-erfuellt-gemeldet"
REGELN = Path(__file__).with_name("kriterium_meldung_regeln.json")

#: Nur Kommentar und Bearbeitung zielen auf ein bestehendes Issue.
_ZIEL_BEFEHLE = {"comment", "edit"}
_URL_ZIEL = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)")
_REMOTE = re.compile(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")
_TRENNER = {"&&", "||", ";", "|", "&"}

#: None = Standardprotokoll von gate_hits; Drills setzen GATE_HITS_DATEI.
PROTOKOLL: Path | None = None


@dataclass(frozen=True)
class Regeln:
    mandate: frozenset[str]
    signal: tuple[re.Pattern, ...]
    bezug: re.Pattern
    kriterium: re.Pattern
    zitat_inline: re.Pattern
    teil_im_zitat: re.Pattern
    teil: re.Pattern
    beleg: tuple[re.Pattern, ...]


def lade(pfad: Path = REGELN) -> Regeln:
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    return Regeln(
        mandate=frozenset(m.lower() for m in roh["mandats_issues"]),
        signal=tuple(re.compile(m) for m in roh["signal_muster"]),
        bezug=re.compile(roh["bezug_muster"]),
        kriterium=re.compile(roh["kriterium_muster"]),
        zitat_inline=re.compile(roh["zitat_inline_muster"]),
        teil_im_zitat=re.compile(roh["teil_im_zitat_muster"]),
        teil=re.compile(roh["teil_muster"]),
        beleg=tuple(re.compile(m) for m in roh["beleg_muster"]),
    )


# --- Ziel bestimmen -----------------------------------------------------------


def _repo_aus_cwd(cwd: str | None) -> str | None:
    if not cwd:
        return None
    try:
        url = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=3,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = _REMOTE.search(url)
    return m.group(1) if m else None


def bash_ziele(kommando: str, cwd: str | None) -> set[str]:
    """`owner/repo#nr` je `gh issue|pr comment|edit` im Befehl."""
    ziele: set[str] = set()
    for treffer in _SCHREIBEN.finditer(kommando):
        if treffer.group(2) not in _ZIEL_BEFEHLE:
            continue
        try:
            woerter = shlex.split(kommando[treffer.end() :])
        except ValueError:
            continue
        repo = nummer = None
        for i, wort in enumerate(woerter):
            if wort in _TRENNER:
                break
            if wort in ("-R", "--repo") and i + 1 < len(woerter):
                repo = woerter[i + 1]
            elif wort.startswith("--repo="):
                repo = wort.split("=", 1)[1]
            elif nummer is None and (m := _URL_ZIEL.search(wort)):
                repo, nummer = m.group(1), m.group(2)
            elif nummer is None and re.fullmatch(r"#?\d+", wort):
                nummer = wort.lstrip("#")
        if nummer is None:
            continue
        repo = repo or _repo_aus_cwd(cwd)
        if repo:
            ziele.add(f"{repo}#{nummer}".lower())
    return ziele


def mcp_ziel(eingabe: dict) -> str | None:
    owner, repo, nr = eingabe.get("owner"), eingabe.get("repo"), eingabe.get("issue_number")
    if not (owner and repo and nr):
        return None
    return f"{owner}/{repo}#{nr}".lower()


# --- Text pruefen -------------------------------------------------------------


def _ist_zitat(zeile: str) -> bool:
    return zeile.lstrip().startswith(">")


def kriterium_teile(zeilen: list[str], r: Regeln) -> list[str] | None:
    """Teile des zitierten Kriteriums, oder None ohne Zitat."""
    for i, zeile in enumerate(zeilen):
        if not r.kriterium.search(zeile):
            continue
        if not _ist_zitat(zeile):
            m = r.zitat_inline.search(zeile)
            if m:
                return [m.group(1)]
            j = i + 1
            if j < len(zeilen) and not zeilen[j].strip():
                j += 1
        else:
            j = i
        block = []
        while j < len(zeilen) and _ist_zitat(zeilen[j]):
            block.append(zeilen[j])
            j += 1
        if block:
            teile = [z for z in block if r.teil_im_zitat.search(z)]
            return teile or ["\n".join(block)]
    return None


def _hat_beleg(text: str, r: Regeln) -> bool:
    return any(m.search(text) for m in r.beleg)


def luecken(text: str, r: Regeln) -> list[str]:
    """Was der Text schuldet; leer = in Ordnung oder kein Signal."""
    zeilen = text.splitlines()
    if not any(r.bezug.search(z) and any(m.search(z) for m in r.signal) for z in zeilen):
        return []
    teile = kriterium_teile(zeilen, r)
    if teile is None:
        return ["Kriterium nicht im Wortlaut zitiert"]
    # Der Wortlaut selbst ist kein Beleg: Blockzitat und Inline-Zitat fallen weg.
    aussen = [r.zitat_inline.sub("", z) for z in zeilen if not _ist_zitat(z)]
    if len(teile) == 1:
        return [] if any(_hat_beleg(z, r) for z in aussen) else ["kein Beleg (Link oder Messwert)"]
    fehlt = []
    for nr in range(1, len(teile) + 1):
        belegt = any(
            _hat_beleg(r.teil.sub("", z), r)
            for z in aussen
            if any(int(m.group(1)) == nr for m in r.teil.finditer(z))
        )
        if not belegt:
            fehlt.append(f"Teil {nr} ohne Beleg")
    return fehlt


def befund(daten: dict, r: Regeln) -> tuple[str | None, list[str]]:
    """(Hinweistext oder None, nicht pruefbare Herkuenfte)."""
    name = str(daten.get("tool_name") or "Bash")
    eingabe = daten.get("tool_input") or {}
    if name.startswith(_MCP_GITHUB):
        ziel = mcp_ziel(eingabe)
        ziele = {ziel} if ziel else set()
        stoff, ungeprueft = mcp_texte(name, eingabe), []
    else:
        kommando = eingabe.get("command") or ""
        if not _SCHREIBEN.search(kommando):
            return None, []
        ziele = bash_ziele(kommando, daten.get("cwd"))
        if not ziele & r.mandate:
            return None, []
        stoff, ungeprueft = erhebe(kommando, daten.get("cwd"))
    treffer = sorted(ziele & r.mandate)
    if not treffer:
        return None, ungeprueft
    stellen = [f"{herkunft}: {', '.join(fehlt)}" for herkunft, text in stoff if (fehlt := luecken(text, r))]
    if not stellen:
        return None, ungeprueft
    return (
        f"📣 {SLUG} (Meldephase, Retro 5c34f2 Befund 1): Der Text an {', '.join(treffer)} "
        f"meldet ein Kriterium als bestanden/erfuellt oder empfiehlt „go“ — "
        f"{'; '.join(stellen)}.\n"
        "Kriterium im Wortlaut als Blockzitat voranstellen (Zeile mit „Kriterium“, darunter "
        "`> - …` je Teil) und je Teil eine Zeile „Teil N: …“ mit Link oder Messwert. "
        "Ungemessene Teile als offen melden, nicht als bestanden. Hinweis, keine Sperre."
    ), ungeprueft


def _notiere(marker: str, daten: dict, beleg: str = "") -> None:
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            marker,
            beleg=beleg[:200],
            session=str(daten.get("session_id") or ""),
            modus="advisory",
            pfad=PROTOKOLL,
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass


def _ausgabe(text: str) -> None:
    print(
        json.dumps(
            {
                "systemMessage": text,
                "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text},
            },
            ensure_ascii=False,
        )
    )


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _notiere("fehler", {}, "kein JSON auf stdin")
        return 0
    try:
        hinweis, ungeprueft = befund(daten, lade())
    except Exception as exc:  # noqa: BLE001 — fail-open, aber gezaehlt und gemeldet
        _notiere("fehler", daten, f"{type(exc).__name__}: {exc}")
        _ausgabe(f"⚠ {SLUG}: Pruefung fehlgeschlagen ({type(exc).__name__}) — `{REGELN}` pruefen.")
        return 0
    for quelle in ungeprueft:
        _notiere("ungeprueft", daten, quelle)
    if hinweis is None:
        return 0
    eingabe = daten.get("tool_input") or {}
    _notiere("meldung", daten, str(eingabe.get("command") or daten.get("tool_name") or ""))
    _ausgabe(hinweis)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — Hook darf nie die Sitzung blockieren
        _notiere("fehler", {}, "Ausnahme ausserhalb von main")
        sys.exit(0)
