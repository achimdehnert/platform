#!/usr/bin/env python3
"""Auftragsraum-Sortierer — Stufe 1 (KONZ-platform-059, #3079).

Der Chat-Lotse (`chat_lotse.py sync`, iilgmbh/chat-hub) liefert Raumnachrichten
als JSON-Zeilen und fuehrt nichts aus (Lotsen-Charta Art. 1). Dieses Werkzeug
liest genau diese Zeilen und macht daraus — ohne Modell — Journaleintraege:

    Kurzbefehl (`#N erledigt`, `#N Frist YYYY-MM-DD`) -> Vorschlag im Journal,
        `anwenden` uebernimmt ihn in einem Kommando (D1, D3).
    Korrektur (beginnt mit nein/falsch/kuerzer/so:/!regel) -> `korrektur: true`,
        `regel <nachricht_id>` legt das Regel-Artefakt an (D4).
    Auftrag (laenger als 8 Woerter oder enthaelt bitte/mach/bau) -> Journalzeile,
        die Kapitaens-Sitzung legt je Auftrag ein Issue an (D1, R2).
    Notiz -> Journalzeile ohne Vorschlag (Art. 1.4).
    Fremd -> `sender` != OWNER_MXID; erzeugt weder Vorschlag noch Issue (D2).

Nur das Owner-Konto loest Artefakte aus (D2): `sender` wird gegen `--owner`
oder `OWNER_MXID` aus `~/.claude/auftragsraum.env` geprueft (Datei liegt
ausserhalb des Repos, wird vom Owner gepflegt). Fehlt OWNER_MXID ganz, gilt
jede Nachricht als `fremd` — keine Schreibung ohne Sichtung (Charta Art. 1.2).

**Nie Nachrichtentext im Journal.** `~/.claude/auftragsraum-journal.jsonl`
traegt `zeit, klasse, konto_hash (sha256-Kurzform des sender-MXID),
nachricht_id, vorschlag (Nummer + Aktion, kein Freitext), artefakt,
korrektur, bearbeitet_am, tokens (Stufe 1 immer null)` — nie den `sender`
selbst (der ein `@` traegt) und nie `body` (D7).

**Zustand hat eine Heimat (D8).** Das Journal fuehrt Ereignisse und Links,
nie Zustand: Kurzbefehle schreiben ueber `board.py`, Auftraege werden als
GitHub-Issue gefuehrt (`offen` fragt den Zustand live per `gh` ab, spiegelt
ihn nie), Korrekturen werden zum Regel-Artefakt.

Vier Unterbefehle::

    python3 tools/chat_agent/auftragsraum.py sortieren --eingabe sync.jsonl
    python3 tools/chat_agent/auftragsraum.py offen [--block] [--ohne-gh]
    python3 tools/chat_agent/auftragsraum.py anwenden [--trocken]
    python3 tools/chat_agent/auftragsraum.py regel <nachricht_id> [--why TEXT]

`sortieren` liest ohne `--eingabe` von stdin (fuer den echten Betrieb:
`chat_lotse.py sync | auftragsraum.py sortieren`); `--eingabe -` ist
gleichbedeutend mit stdin. `--eingabe DATEI` deckt jeden Befehl fuer Tests,
ganz ohne Chat-Lotse oder Netz.

`anwenden` uebernimmt offene Kurzbefehl-Vorschlaege ueber `board.py`:
`#N erledigt` -> `board.py --erledigt N` (wird erst mit #3049 gebaut — bis
dahin protokolliert `anwenden` das Kommando als "nicht angewendet" und
bricht nicht ab, Exit 0); `#N Frist D` -> `board.py --frist N --datum D
--grund 'Owner im Auftragsraum'` (existiert bereits).

`regel <nachricht_id>` legt den Memory-Kandidaten selbst an
(`~/.claude/auftragsraum-regeln/<datum>-<id>.md`, lokal, NICHT im Repo) und
schreibt dessen `file://`-Pfad als `artefakt` in die Journalzeile. Das
Journal selbst speichert nie den Nachrichtentext — `regel` nimmt ihn
deshalb ueber `--zitat` entgegen (die Kapitaens-Sitzung hat ihn beim Lesen
der Sync-Zeilen gesehen); ohne `--zitat` bleibt ein TODO-Platzhalter stehen.
`--why` bleibt ebenfalls ein Platzhalter, wenn nicht gegeben — die Sitzung
ergaenzt ihn (D4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BOARD_SKRIPT = REPO / "tools" / "mail_agent" / "board.py"

JOURNAL_DEFAULT = Path.home() / ".claude" / "auftragsraum-journal.jsonl"
OWNER_ENV_DEFAULT = Path.home() / ".claude" / "auftragsraum.env"
REGELN_DIR_DEFAULT = Path.home() / ".claude" / "auftragsraum-regeln"

TIMEOUT = 30

KLASSEN = ("notiz", "kurzbefehl", "auftrag", "korrektur", "fremd")

#: Nur diese zwei engen Muster sind ein Kurzbefehl (R1: eng halten, alles
#: andere bleibt Auftrag/Notiz ohne Schreibung).
_KURZBEFEHL_ERLEDIGT = re.compile(r"^#(\d+)\s+(erledigt|erl)$", re.IGNORECASE)
_KURZBEFEHL_FRIST = re.compile(r"^#(\d+)\s+frist\s+(\d{4}-\d{2}-\d{2})$", re.IGNORECASE)

#: "beginnt mit" (D4) — Wortgrenze geprueft, damit "neinerlei" nicht "nein" traegt.
_KORREKTUR_PRAEFIXE = ("nein", "falsch", "kürzer", "kuerzer", "so:", "!regel")

#: "enthaelt" (D1) — bewusst Teilstring, wie im Auftrag benannt.
_AUFTRAG_SCHLUESSEL = ("bitte", "mach", "bau")

_AUFTRAG_MIN_WOERTER = 8


# --- Zeit/Text-Helfer -------------------------------------------------


def _jetzt_iso() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _zeit_parsen(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        wert = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if wert.tzinfo is None:
        wert = wert.replace(tzinfo=timezone.utc)
    return wert


def _alter_stunden(text: Any, jetzt: datetime) -> float | None:
    zeit = _zeit_parsen(text)
    if zeit is None:
        return None
    return (jetzt - zeit).total_seconds() / 3600


def sha256_kurz(sender: str) -> str:
    """sha256-Kurzform (12 Hex-Zeichen) — nie der Klartext-MXID im Journal."""
    return hashlib.sha256(sender.encode("utf-8")).hexdigest()[:12]


def _run(args: list[str], timeout: int = TIMEOUT) -> tuple[str, str, int | None]:
    try:
        lauf = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, cwd=REPO
        )
        return lauf.stdout, lauf.stderr, lauf.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout nach {timeout}s", None
    except OSError as exc:
        return "", str(exc), None


# --- Owner-Konto --------------------------------------------------------


def owner_mxid_aus_env(pfad: Path) -> str | None:
    """`~/.claude/auftragsraum.env` (Owner-gepflegt, nicht im Repo): Zeile
    `OWNER_MXID=@achim:chat.iil.pet`. Fehlt die Datei oder der Schluessel,
    liefert diese Funktion `None` — der Aufrufer behandelt dann JEDE
    Nachricht als `fremd` (D2, Charta Art. 1.2: keine Schreibung ohne
    Sichtung)."""
    if not pfad.exists():
        return None
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return None
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, _, wert = zeile.partition("=")
        if schluessel.strip() == "OWNER_MXID":
            wert = wert.strip().strip('"').strip("'")
            return wert or None
    return None


# --- Klassifikation (D1) -------------------------------------------------


def _beginnt_mit_korrektur(text_lower: str) -> bool:
    for praefix in _KORREKTUR_PRAEFIXE:
        if text_lower.startswith(praefix):
            rest = text_lower[len(praefix) :]
            if not rest or not rest[0].isalnum():
                return True
    return False


def klassifiziere(
    sender: str, body: str, owner_mxid: str | None
) -> tuple[str, dict[str, Any] | None, bool]:
    """Rueckgabe (klasse, vorschlag, korrektur). `vorschlag` ist nur bei
    `kurzbefehl` gesetzt (Nummer + Aktion, nie Freitext, D5/D7)."""
    if not owner_mxid or sender != owner_mxid:
        return "fremd", None, False

    text = (body or "").strip()

    treffer = _KURZBEFEHL_ERLEDIGT.match(text)
    if treffer:
        return (
            "kurzbefehl",
            {"nummer": int(treffer.group(1)), "aktion": "erledigt"},
            False,
        )

    treffer = _KURZBEFEHL_FRIST.match(text)
    if treffer:
        return (
            "kurzbefehl",
            {
                "nummer": int(treffer.group(1)),
                "aktion": "frist",
                "datum": treffer.group(2),
            },
            False,
        )

    lower = text.lower()
    if _beginnt_mit_korrektur(lower):
        return "korrektur", None, True

    woerter = text.split()
    if len(woerter) > _AUFTRAG_MIN_WOERTER or any(
        schluessel in lower for schluessel in _AUFTRAG_SCHLUESSEL
    ):
        return "auftrag", None, False

    return "notiz", None, False


# --- Journal --------------------------------------------------------------


def _journal_lesen(pfad: Path) -> list[dict[str, Any]]:
    if not pfad.exists():
        return []
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return []
    eintraege: list[dict[str, Any]] = []
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue
        if isinstance(eintrag, dict):
            eintraege.append(eintrag)
    return eintraege


def _journal_schreiben(pfad: Path, eintraege: list[dict[str, Any]]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        json.dumps(e, ensure_ascii=False, sort_keys=True) for e in eintraege
    )
    pfad.write_text(text + ("\n" if eintraege else ""), encoding="utf-8")


def _journal_anhaengen(pfad: Path, eintraege: list[dict[str, Any]]) -> None:
    if not eintraege:
        return
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        for eintrag in eintraege:
            datei.write(json.dumps(eintrag, ensure_ascii=False, sort_keys=True) + "\n")


# --- sortieren --------------------------------------------------------


def _sync_zeilen_lesen(quelle: str | None) -> list[dict[str, Any]]:
    """Sync-JSON-Zeilen von stdin oder Datei (`chat_lotse.py sync`-Format:
    room_id, room_name, sender, ts, event_id, body[, undecryptable, audio])."""
    if quelle is None or quelle == "-":
        text = sys.stdin.read()
    else:
        text = Path(quelle).expanduser().read_text(encoding="utf-8")
    zeilen: list[dict[str, Any]] = []
    for roh in text.splitlines():
        roh = roh.strip()
        if not roh:
            continue
        try:
            obj = json.loads(roh)
        except ValueError:
            continue
        if isinstance(obj, dict):
            zeilen.append(obj)
    return zeilen


def sortieren(
    sync_zeilen: list[dict[str, Any]], journal_pfad: Path, owner_mxid: str | None
) -> dict[str, int]:
    """Idempotent: `nachricht_id` (= `event_id`), die schon im Journal steht,
    wird nie zweimal geschrieben. Zeilen ohne `event_id` werden uebersprungen
    (kein stabiler Schluessel fuer Idempotenz)."""
    bestehende_ids = {
        e.get("nachricht_id")
        for e in _journal_lesen(journal_pfad)
        if e.get("nachricht_id")
    }
    stats = {klasse: 0 for klasse in KLASSEN}
    stats["neu"] = 0
    stats["uebersprungen"] = 0
    stats["ohne_id"] = 0

    neue_eintraege: list[dict[str, Any]] = []
    for roh in sync_zeilen:
        nachricht_id = roh.get("event_id")
        if not nachricht_id:
            stats["ohne_id"] += 1
            continue
        if nachricht_id in bestehende_ids:
            stats["uebersprungen"] += 1
            continue

        sender = str(roh.get("sender") or "")
        body = roh.get("body") or ""
        klasse, vorschlag, korrektur = klassifiziere(sender, body, owner_mxid)

        eintrag = {
            "zeit": roh.get("ts") or _jetzt_iso(),
            "klasse": klasse,
            "konto_hash": sha256_kurz(sender),
            "nachricht_id": nachricht_id,
            "vorschlag": vorschlag,
            "artefakt": None,
            "korrektur": korrektur,
            "bearbeitet_am": None,
            "tokens": None,
        }
        neue_eintraege.append(eintrag)
        bestehende_ids.add(nachricht_id)
        stats[klasse] += 1
        stats["neu"] += 1

    _journal_anhaengen(journal_pfad, neue_eintraege)
    return stats


# --- offen --------------------------------------------------------------


_ISSUE_MUSTER = re.compile(r"/issues/(\d+)\b")


def _issue_nummer(artefakt: str | None) -> str | None:
    if not artefakt:
        return None
    treffer = _ISSUE_MUSTER.search(artefakt)
    return treffer.group(1) if treffer else None


def _gh_issue_zustand(nummer: str) -> str | None:
    out, _err, rc = _run(["gh", "issue", "view", nummer, "--json", "state"])
    if rc != 0:
        return None
    try:
        return json.loads(out).get("state")
    except ValueError:
        return None


def offen(journal_pfad: Path, *, block: bool, ohne_gh: bool) -> tuple[str, int]:
    eintraege = _journal_lesen(journal_pfad)
    jetzt = datetime.now(timezone.utc)

    vorschlaege = [
        e
        for e in eintraege
        if e.get("klasse") == "kurzbefehl" and not e.get("bearbeitet_am")
    ]
    auftraege = [
        e
        for e in eintraege
        if e.get("klasse") == "auftrag" and not e.get("bearbeitet_am")
    ]
    korrekturen = [
        e for e in eintraege if e.get("korrektur") and not e.get("bearbeitet_am")
    ]

    zeilen: list[str] = []
    zeilen.append(f"Vorschlaege offen: {len(vorschlaege)}")
    for e in vorschlaege:
        v = e.get("vorschlag") or {}
        text = f"#{v.get('nummer')} {v.get('aktion')}"
        if v.get("datum"):
            text += f" {v['datum']}"
        zeilen.append(f"  {e.get('nachricht_id')}: {text}")

    zeilen.append(f"Auftraege offen: {len(auftraege)}")
    for e in auftraege:
        artefakt = e.get("artefakt")
        nummer = _issue_nummer(artefakt)
        if artefakt and nummer and not ohne_gh:
            zustand = _gh_issue_zustand(nummer) or "unbekannt (gh)"
        elif artefakt:
            zustand = artefakt
        else:
            zustand = "kein Issue — Kapitaens-Sitzung legt eines an"
        zeilen.append(f"  {e.get('nachricht_id')}: {zustand}")

    zeilen.append(f"Korrekturen offen: {len(korrekturen)}")
    ueberfaellig = 0
    for e in korrekturen:
        alter_h = _alter_stunden(e.get("zeit"), jetzt)
        ohne_artefakt = not e.get("artefakt")
        markiert = ""
        if ohne_artefakt and alter_h is not None and alter_h > 24:
            ueberfaellig += 1
            markiert = " -- > 24h ohne Regel-Artefakt"
        alter_text = f"{alter_h:.1f}h" if alter_h is not None else "unbekannt"
        zeilen.append(
            f"  {e.get('nachricht_id')}: alter={alter_text} "
            f"artefakt={e.get('artefakt') or '-'}{markiert}"
        )

    text = "\n".join(zeilen)
    exit_code = 1 if (block and ueberfaellig > 0) else 0
    return text, exit_code


# --- anwenden -------------------------------------------------------------


def _kommando_fuer_vorschlag(vorschlag: dict[str, Any]) -> list[str] | None:
    aktion = vorschlag.get("aktion")
    nummer = vorschlag.get("nummer")
    if nummer is None:
        return None
    if aktion == "erledigt":
        return [sys.executable, str(BOARD_SKRIPT), "--erledigt", str(nummer)]
    if aktion == "frist":
        return [
            sys.executable,
            str(BOARD_SKRIPT),
            "--frist",
            str(nummer),
            "--datum",
            str(vorschlag.get("datum") or ""),
            "--grund",
            "Owner im Auftragsraum",
        ]
    return None


def anwenden(journal_pfad: Path, *, trocken: bool) -> list[dict[str, str]]:
    eintraege = _journal_lesen(journal_pfad)
    ergebnisse: list[dict[str, str]] = []
    geaendert = False

    for eintrag in eintraege:
        if eintrag.get("klasse") != "kurzbefehl" or eintrag.get("bearbeitet_am"):
            continue
        vorschlag = eintrag.get("vorschlag") or {}
        kommando = _kommando_fuer_vorschlag(vorschlag)
        if kommando is None:
            ergebnisse.append(
                {
                    "nachricht_id": eintrag.get("nachricht_id", ""),
                    "kommando": "",
                    "status": "nicht anwendbar (Vorschlag ohne Nummer/Aktion)",
                }
            )
            continue

        kommando_text = " ".join(kommando)
        if trocken:
            ergebnisse.append(
                {
                    "nachricht_id": eintrag.get("nachricht_id", ""),
                    "kommando": kommando_text,
                    "status": "trocken",
                }
            )
            continue

        out, err, rc = _run(kommando)
        text = f"{out}\n{err}".lower()
        if rc == 0:
            eintrag["bearbeitet_am"] = _jetzt_iso()
            geaendert = True
            status = "angewendet"
        elif (
            rc == 2 or "unrecognized argument" in text or "unbekanntes argument" in text
        ):
            status = (
                "nicht angewendet (board.py kennt dieses Argument noch nicht — #3049)"
            )
        else:
            status = f"fehlgeschlagen (rc={rc})"
        ergebnisse.append(
            {
                "nachricht_id": eintrag.get("nachricht_id", ""),
                "kommando": kommando_text,
                "status": status,
            }
        )

    if geaendert:
        _journal_schreiben(journal_pfad, eintraege)
    return ergebnisse


# --- regel ------------------------------------------------------------


_REGEL_TEMPLATE = """---
name: auftragsraum-korrektur-{datum}-{safe_id}
description: Owner-Korrektur vom {datum} im Auftragsraum
metadata:
  type: feedback
---

# Owner-Korrektur vom {datum} im Auftragsraum

> {zitat}

Nachricht-ID: {nachricht_id}
Raum: Auftragsraum (KONZ-platform-059)

## Why

{why}
"""


def regel(
    nachricht_id: str,
    *,
    why: str | None,
    zitat: str | None,
    journal_pfad: Path,
    regeln_dir: Path,
) -> Path:
    eintraege = _journal_lesen(journal_pfad)
    treffer = next(
        (e for e in eintraege if e.get("nachricht_id") == nachricht_id), None
    )
    if treffer is None:
        raise SystemExit(
            f"FEHLER: nachricht_id {nachricht_id!r} nicht im Journal {journal_pfad}"
        )

    datum = date.today().isoformat()
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", nachricht_id)[:60] or "unbekannt"
    regeln_dir.mkdir(parents=True, exist_ok=True)
    pfad = regeln_dir / f"{datum}-{safe_id}.md"

    inhalt = _REGEL_TEMPLATE.format(
        datum=datum,
        safe_id=safe_id,
        zitat=zitat or "TODO: Zitat der Owner-Nachricht hier einfuegen (--zitat)",
        nachricht_id=nachricht_id,
        why=why or "TODO: warum gilt diese Regel? (--why)",
    )
    pfad.write_text(inhalt, encoding="utf-8")

    treffer["artefakt"] = f"file://{pfad.resolve()}"
    _journal_schreiben(journal_pfad, eintraege)
    return pfad


# --- CLI --------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0].replace("\n", " ") if __doc__ else ""
    )
    sub = ap.add_subparsers(dest="befehl", required=True)

    p_sortieren = sub.add_parser(
        "sortieren", help="Sync-Zeilen lesen, klassifizieren, Journal anhaengen"
    )
    p_sortieren.add_argument(
        "--eingabe",
        help="Datei mit Sync-JSON-Zeilen oder '-' (Default: stdin)",
    )
    p_sortieren.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    p_sortieren.add_argument(
        "--owner", help="OWNER_MXID direkt (sonst aus --owner-env)"
    )
    p_sortieren.add_argument("--owner-env", default=str(OWNER_ENV_DEFAULT))

    p_offen = sub.add_parser(
        "offen", help="Offene Vorschlaege/Auftraege/Korrekturen zeigen"
    )
    p_offen.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    p_offen.add_argument(
        "--block",
        action="store_true",
        help="Exit 1, wenn eine Korrektur >24h ohne Artefakt offen ist",
    )
    p_offen.add_argument(
        "--ohne-gh", action="store_true", help="keine `gh issue view`-Abfragen"
    )

    p_anwenden = sub.add_parser(
        "anwenden", help="Offene Kurzbefehl-Vorschlaege ueber board.py uebernehmen"
    )
    p_anwenden.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    p_anwenden.add_argument(
        "--trocken", action="store_true", help="nur zeigen, nichts ausfuehren/schreiben"
    )

    p_regel = sub.add_parser(
        "regel", help="Regel-Artefakt aus einer Korrektur-Nachricht anlegen"
    )
    p_regel.add_argument("nachricht_id")
    p_regel.add_argument("--why", help="warum diese Regel gilt (sonst TODO)")
    p_regel.add_argument(
        "--zitat", help="Nachrichtentext zum Zitieren (Journal speichert ihn nie)"
    )
    p_regel.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    p_regel.add_argument("--regeln-dir", default=str(REGELN_DIR_DEFAULT))

    args = ap.parse_args(argv)

    if args.befehl == "sortieren":
        journal_pfad = Path(args.journal).expanduser()
        owner = args.owner or owner_mxid_aus_env(Path(args.owner_env).expanduser())
        if not owner:
            print(
                "WARNUNG: OWNER_MXID nicht gesetzt (--owner oder --owner-env) — "
                "alle Nachrichten gelten als 'fremd'.",
                file=sys.stderr,
            )
        zeilen = _sync_zeilen_lesen(args.eingabe)
        stats = sortieren(zeilen, journal_pfad, owner)
        print(
            f"sortiert: {stats['neu']} neu, {stats['uebersprungen']} bereits im "
            f"Journal, {stats['ohne_id']} ohne event_id uebersprungen"
        )
        for klasse in KLASSEN:
            print(f"  {klasse}: {stats[klasse]}")
        return 0

    if args.befehl == "offen":
        journal_pfad = Path(args.journal).expanduser()
        text, code = offen(journal_pfad, block=args.block, ohne_gh=args.ohne_gh)
        print(text)
        return code

    if args.befehl == "anwenden":
        journal_pfad = Path(args.journal).expanduser()
        ergebnisse = anwenden(journal_pfad, trocken=args.trocken)
        if not ergebnisse:
            print("keine offenen Kurzbefehl-Vorschlaege")
        for r in ergebnisse:
            print(f"  {r['nachricht_id']}: {r['status']} — {r['kommando']}")
        return 0

    if args.befehl == "regel":
        journal_pfad = Path(args.journal).expanduser()
        regeln_dir = Path(args.regeln_dir).expanduser()
        pfad = regel(
            args.nachricht_id,
            why=args.why,
            zitat=args.zitat,
            journal_pfad=journal_pfad,
            regeln_dir=regeln_dir,
        )
        print(f"Regel-Artefakt angelegt: {pfad}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
