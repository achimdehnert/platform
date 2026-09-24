#!/usr/bin/env python3
"""session_start_delta.py — WARN-Zeilen des Session-Start-Runners gegen das Befund-Journal legen.

Warum es das gibt (#3495 V3, Kriterium 3):
    Der Runner meldete jede Sitzung jede WARN-Zeile in voller Lautstaerke — auch
    die, die laengst verankert sind (Issue, Verzicht, laufender Fix). Gemessen am
    2026-09-24: 14 WARN-Zeilen, davon nur ~2 ohne Entscheidung. Der Skill wertet
    jede WARN-Zeile als Befund; zwoelf davon waren Wiederholungen einer Entscheidung,
    die schon gefallen war. Wer 14 Zeilen liest, um 2 zu finden, liest irgendwann
    keine mehr.

Was diese Datei tut — und nur das:
    Jede WARN-Zeile bekommt eine Delta-Klasse gegen den Journalstand VOR diesem
    Lauf. Laut bleiben nur Zeilen, zu denen es etwas Neues zu entscheiden gibt;
    der Rest wird zu EINER Summenzeile ``k verankert (naechste Faelligkeit X)``.

    NEU                        Schluessel ``phase::repo`` steht nicht im Journal.
    GEAENDERT                  Note weicht von der letzten Journal-Note ab (Zahlen
                               normalisiert, siehe ``zustand``).
    OHNE-ANKER                 im Journal, aber weder Artefakt noch Verzicht noch
                               Urteil ``falsch`` — die Entscheidung fehlt noch.
    ANKER-ABGELAUFEN           Anker gesetzt, seine Wiedervorlage ist verstrichen.
    FIX-MESSUNG-UEBERFAELLIG   laufender Fix, Messdatum verstrichen, Befund steht noch.
    WIEDERVORLAGE              [INFRA]-Befund ruht laenger als ``INFRA_RUHE_MAX_TAGE``.
    VERANKERT                  alles andere — geht in die Summenzeile.

Abgrenzung:
    Kein Unterdruecken. Die Phasen, ihr Status und ``RESULT:`` bleiben unveraendert;
    die Klassifikation kommt DAZU. Nur ``SESSION_CHECKS_DELTA=nur`` blendet
    VERANKERT-Zeilen in der Summary-Tabelle aus — und auch dann stehen sie in der
    Summenzeile, nicht im Nichts. Kein Schreiben ins Journal: gelesen wird es
    ausschliesslich ueber ``befund_journal.py --bericht --json``.

Zustand (``~/.claude/state/session-start-delta.json``, per
``SESSION_START_DELTA_ZUSTAND`` ueberschreibbar):
    Das Journal traegt kein Datum, seit wann ein Anker gilt — ``--verankert`` setzt
    nur die Wiedervorlage. Fuer die [INFRA]-Ruheregel haelt diese Datei je
    Schluessel die Anker-Signatur (Artefakt, Verzicht, Wiedervorlage, Fix-Datum)
    und den Tag, an dem sie zuerst gesehen wurde. Aendert sich die Signatur (neu
    verankert, Fix gesetzt), beginnt die Ruhe neu. Ohne Zustand zaehlt der juengste
    bekannte Anker-Tag (Verzicht ``am``, Fix ``gesetzt_am``), sonst ``erstmals`` —
    im Zweifel frueher laut als zu lange still.

Nie werfend: ein nicht lesbares Journal ergibt eine UNGEPRUEFT-Zeile und keine
Klassen — der Runner zeigt dann die Summary wie bisher.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

#: Maximale Ruhedauer eines verankerten [INFRA]-Befunds (#3495 Kriterium 5).
#: Anlass #3486: ein Backup-Befund schlief 17 Naechte hinter seinem Anker, waehrend
#: die Sicherung nicht lief. Sieben Tage = dieselbe Frist wie ``entscheiden_bis``
#: und ``fix.messung`` im Journal — ein Rhythmus, nicht drei.
INFRA_RUHE_MAX_TAGE = 7

NEU = "NEU"
GEAENDERT = "GEAENDERT"
OHNE_ANKER = "OHNE-ANKER"
ANKER_ABGELAUFEN = "ANKER-ABGELAUFEN"
FIX_UEBERFAELLIG = "FIX-MESSUNG-UEBERFAELLIG"
WIEDERVORLAGE = "WIEDERVORLAGE"
VERANKERT = "VERANKERT"

#: Rangfolge fuer Zeilen mit mehreren Repos: die lauteste Klasse gewinnt.
RANG = (
    NEU,
    GEAENDERT,
    OHNE_ANKER,
    ANKER_ABGELAUFEN,
    FIX_UEBERFAELLIG,
    WIEDERVORLAGE,
    VERANKERT,
)
LAUT = frozenset(RANG) - {VERANKERT}

ZUSTAND = Path(
    os.environ.get(
        "SESSION_START_DELTA_ZUSTAND",
        Path.home() / ".claude" / "state" / "session-start-delta.json",
    )
)
_JOURNAL_CLI = Path(__file__).resolve().parent / "befund_journal.py"
_ZAHL = re.compile(r"\d+")
_LEER = re.compile(r"\s+")


def _heute() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def schluessel(phase: str, repo: str) -> str:
    """Derselbe Fingerabdruck wie ``befund_journal.fingerabdruck`` (phase::repo)."""
    return f"{phase.strip()}::{repo.strip() or '-'}"


def zustand(note: str | None) -> str:
    """Die Note ohne ihre Zaehler — der Zustand, nicht der Messwert.

    Melder-Notizen tragen Zaehler, die jeden Lauf wandern (``10x seit …``,
    ``risk-hub(13d)``, Datumsangaben). Verglichen im Wortlaut waere fast jede
    Zeile jeden Tag GEAENDERT und die Klasse so laut wie vorher die WARN-Zeile.
    Gezaehlt wird deshalb die Form: welche Repos, welche Pruefung, welche Aussage.
    Preis: ``2 Lease(s)`` -> ``5 Lease(s)`` gilt als unveraendert; das faengt die
    Wiedervorlage des Ankers auf, nicht diese Klasse.
    """
    text = (note or "").replace("|", "/").strip()
    return _LEER.sub(" ", _ZAHL.sub("#", text))


def zeilen_lesen(text: str) -> list[dict]:
    """Runner-TSV (phase, status, repo(s), note, …) — dasselbe Format wie fuers Journal."""
    zeilen = []
    for roh in text.splitlines():
        if not roh.strip():
            zeilen.append({"phase": "", "status": "", "repos": [], "note": ""})
            continue
        teile = roh.split("\t")
        zeilen.append(
            {
                "phase": teile[0].strip(),
                "status": teile[1].strip().upper() if len(teile) > 1 else "",
                "repos": teile[2].split() if len(teile) > 2 else [],
                "note": teile[3].strip() if len(teile) > 3 else "",
            }
        )
    return zeilen


def _datum(text: str | None) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10]) if text else None
    except ValueError:
        return None


def _signatur(eintrag: dict) -> str:
    fix = eintrag.get("fix") or {}
    return json.dumps(
        [
            eintrag.get("artefakt"),
            eintrag.get("verzicht"),
            eintrag.get("wiedervorlage"),
            fix.get("gesetzt_am"),
        ],
        sort_keys=True,
        ensure_ascii=False,
    )


def anker_seit(eintrag: dict, gespeichert: dict | None, heute: str) -> str:
    """Seit wann ruht dieser Befund hinter seinem jetzigen Anker?"""
    sig = _signatur(eintrag)
    if gespeichert is not None:
        if gespeichert.get("signatur") == sig and gespeichert.get("seit"):
            return str(gespeichert["seit"])
        return heute  # Anker erneuert — die Ruhe beginnt neu
    bekannte = [
        d
        for d in (
            _datum((eintrag.get("verzicht") or {}).get("am")),
            _datum((eintrag.get("fix") or {}).get("gesetzt_am")),
        )
        if d
    ]
    if bekannte:
        return max(bekannte).isoformat()
    return str(eintrag.get("erstmals") or heute)


def klassifiziere(
    note: str, eintrag: dict | None, heute: str, gespeichert: dict | None = None
) -> dict:
    """Delta-Klasse EINES Schluessels. Rueckgabe: klasse, grund, faellig, seit."""
    if eintrag is None:
        return {"klasse": NEU, "grund": "nicht im Journal"}
    if zustand(eintrag.get("note")) != zustand(note):
        return {"klasse": GEAENDERT, "grund": "Note anders als im letzten Lauf"}
    urteil_falsch = eintrag.get("urteil") == "falsch"
    if not (eintrag.get("artefakt") or eintrag.get("verzicht") or urteil_falsch):
        frist = eintrag.get("entscheiden_bis") or "?"
        return {"klasse": OHNE_ANKER, "grund": f"kein Anker, Frist {frist}"}
    wv = eintrag.get("wiedervorlage")
    if wv and heute > str(wv):
        return {"klasse": ANKER_ABGELAUFEN, "grund": f"Wiedervorlage {wv} verstrichen"}
    fix = eintrag.get("fix") or {}
    if eintrag.get("fix_ueberfaellig"):
        return {
            "klasse": FIX_UEBERFAELLIG,
            "grund": f"Messdatum {fix.get('messung')} verstrichen",
        }
    faellig = [str(d) for d in (wv, fix.get("messung")) if d]
    ergebnis: dict = {"klasse": VERANKERT, "grund": ""}
    if eintrag.get("infra"):
        seit = anker_seit(eintrag, gespeichert, heute)
        ergebnis["seit"] = seit
        start = _datum(seit) or _datum(heute)
        grenze = (start + timedelta(days=INFRA_RUHE_MAX_TAGE)).isoformat()
        if heute > grenze:
            ergebnis.update(
                klasse=WIEDERVORLAGE,
                grund=f"[INFRA] ruht seit {seit}, > {INFRA_RUHE_MAX_TAGE} Tage",
            )
            return ergebnis
        faellig.append(grenze)
    ergebnis["faellig"] = min(faellig) if faellig else None
    return ergebnis


def delta(
    zeilen: list[dict],
    journal: list[dict],
    heute: str | None = None,
    zustand_alt: dict | None = None,
) -> tuple[list[dict], dict]:
    """Klassifikation je Runner-Zeile + neuer Zustand (Anker-Signaturen der [INFRA]-Befunde).

    Nur WARN-Zeilen werden klassifiziert; alle anderen bekommen ``klasse = ""``.
    """
    heute = heute or _heute()
    je_id = {e.get("id"): e for e in journal if isinstance(e, dict)}
    anker_alt = (zustand_alt or {}).get("anker", {})
    anker_neu: dict[str, dict] = {}
    ergebnis = []
    for i, z in enumerate(zeilen):
        zeile = {"index": i, **z, "klasse": "", "grund": "", "faellig": None}
        if z.get("status") == "WARN":
            urteile = []
            for repo in z.get("repos") or ["-"]:
                sid = schluessel(z["phase"], repo)
                eintrag = je_id.get(sid)
                u = klassifiziere(z.get("note", ""), eintrag, heute, anker_alt.get(sid))
                if eintrag is not None and eintrag.get("infra") and u.get("seit"):
                    anker_neu[sid] = {"signatur": _signatur(eintrag), "seit": u["seit"]}
                urteile.append(u)
            lautestes = min(urteile, key=lambda u: RANG.index(u["klasse"]))
            zeile["klasse"] = lautestes["klasse"]
            zeile["grund"] = lautestes["grund"]
            if lautestes["klasse"] == VERANKERT:
                fristen = [u["faellig"] for u in urteile if u.get("faellig")]
                zeile["faellig"] = min(fristen) if fristen else None
        ergebnis.append(zeile)
    return ergebnis, {"anker": anker_neu}


def summenzeile(ergebnis: list[dict]) -> str:
    verankert = [z for z in ergebnis if z["klasse"] == VERANKERT]
    fristen = [z["faellig"] for z in verankert if z.get("faellig")]
    naechste = min(fristen) if fristen else "—"
    return f"{len(verankert)} verankert (naechste Faelligkeit {naechste})"


def tabelle(ergebnis: list[dict]) -> str:
    laut = [z for z in ergebnis if z["klasse"] in LAUT]
    aus = ["Delta gegen Journal (tools/session_start_delta.py · #3495 V3):"]
    if laut:
        aus += ["| Phase | Repo | Delta | Grund |", "|---|---|---|---|"]
        for z in laut:
            repos = " ".join(z.get("repos") or ["-"])
            aus.append(f"| {z['phase']} | {repos} | {z['klasse']} | {z['grund']} |")
    else:
        aus.append("  keine neue, geaenderte oder faellige WARN-Zeile")
    aus.append(summenzeile(ergebnis))
    return "\n".join(aus)


def journal_lesen(pfad: str | None, repo: str) -> list[dict] | None:
    """Journal-Bericht als Liste — aus Datei (Tests) oder ueber die CLI. ``None`` = unlesbar."""
    try:
        if pfad:
            roh = Path(pfad).read_text(encoding="utf-8")
        else:
            roh = subprocess.run(
                [
                    sys.executable,
                    str(_JOURNAL_CLI),
                    "--bericht",
                    "--json",
                    "--repo",
                    repo,
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            ).stdout
        daten = json.loads(roh)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return daten if isinstance(daten, list) else None


def zustand_lesen(pfad: Path) -> dict:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def zustand_sichern(pfad: Path, daten: dict) -> None:
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(
            json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default="platform", help="Zielrepo des Laufs")
    p.add_argument("--journal", default=None, help="Journal-Bericht als JSON-Datei")
    p.add_argument(
        "--zustand", default=None, help="Zustandsdatei (Default: ~/.claude/state/…)"
    )
    p.add_argument("--heute", default=None, help="Stichtag YYYY-MM-DD (Tests)")
    p.add_argument(
        "--klassen-datei",
        default=None,
        help="je Eingabezeile eine Zeile mit der Klasse (leer = keine WARN-Zeile)",
    )
    a = p.parse_args(argv)

    zeilen = zeilen_lesen(sys.stdin.read())
    journal = journal_lesen(a.journal, a.repo)
    if journal is None:
        print("Delta gegen Journal: UNGEPRUEFT — Journal-Bericht nicht lesbar")
        return 0
    zpfad = Path(a.zustand) if a.zustand else ZUSTAND
    ergebnis, neu = delta(zeilen, journal, a.heute, zustand_lesen(zpfad))
    zustand_sichern(zpfad, neu)
    if a.klassen_datei:
        try:
            Path(a.klassen_datei).write_text(
                "".join(f"{z['klasse']}\n" for z in ergebnis), encoding="utf-8"
            )
        except OSError:
            pass
    print(tabelle(ergebnis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
