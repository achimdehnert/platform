#!/usr/bin/env python3
"""Vorgänge, die auf den Versand warten, gegen den Sendeordner abgleichen.

Warum es das gibt: Ein Vorgang steht im Bucket `owner`, solange der Mensch die
Mail noch senden muss. Sobald sie draußen ist, wartet nicht mehr der Versand,
sondern die Gegenseite — der Vorgang gehört nach `warten`. Diese Umstellung lief
bisher über Aufmerksamkeit: der Mensch sagt „ist raus", jemand schreibt es ins
Ledger. Am 2026-08-20 waren es fünf Vorgänge an einem Tag, alle von Hand.

Die Information steht im Sendeordner. Dieses Werkzeug holt sie und schlägt die
Umstellung vor; geschrieben wird nur mit `--apply`.

Konservativ by design — der Abgleich ist eine Heuristik über Betreff und
Empfänger, keine Zuordnung über Message-IDs:

* Vorschlag nur, wenn **genau eine** gesendete Mail zum Vorgang passt. Mehrere
  Treffer heißen „mehrdeutig", nicht „nimm den ersten".
* Nur Vorgänge im Bucket `owner`, deren Text den Versand als nächsten Schritt
  nennt (`senden`, `Entwurf`, `verschicken`).
* Nur Mails, die **nach** der letzten Prüfung des Vorgangs gesendet wurden.

Read-only gegenüber dem Postfach. Der Ledger-Pfad liegt unter ~/.claude, nie im
Repo (Charta Art. 2) — er trägt Namen und Betreffs.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from privat_datei import schreibe_privat  # noqa: E402

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
HIER = Path(__file__).resolve().parent

#: Wörter, die in jedem zweiten Betreff stehen und deshalb nichts unterscheiden.
STOPP = {
    "aw",
    "re",
    "fwd",
    "wg",
    "der",
    "die",
    "das",
    "und",
    "für",
    "fuer",
    "von",
    "mit",
    "zum",
    "zur",
    "gmbh",
    "herr",
    "frau",
    "prof",
    "dr",
    "mail",
    "info",
}

#: Ordner je Konto — IIL läuft über Graph, die übrigen über IMAP.
SENDEORDNER = {"iil": "Gesendete Elemente"}
SENDEORDNER_IMAP = "Gesendete Objekte"

#: Ein Vorgang wartet auf den Versand, wenn sein Text das sagt.
WARTET_AUF_VERSAND = re.compile(r"senden|versch(icken|ickt)|entwurf", re.I)

#: Zeitstempel wie board.py ihn ins Ledger schreibt, und seine Länge.
ZEITFORMAT = "%Y-%m-%d %H:%M"
MINUTE = len("YYYY-MM-DD HH:MM")


@dataclass(frozen=True)
class Gesendet:
    """Eine ausgehende Mail, reduziert auf das für den Abgleich Nötige.

    `datum` ist Ortszeit des Hosts wie `letzte_pruefung` im Ledger:
    'YYYY-MM-DD HH:MM', oder nur 'YYYY-MM-DD', wenn die Quelle keine Uhrzeit hat.
    """

    datum: str
    betreff: str
    empfaenger: str = ""

    def tag(self) -> str:
        return self.datum[:10]


def tokens(text: str) -> set[str]:
    """Unterscheidungskräftige Wörter aus einem Ledger-Feld oder Betreff."""
    roh = re.split(r"[^0-9A-Za-zÄÖÜäöüß]+", (text or "").lower())
    return {w for w in roh if len(w) >= 4 and w not in STOPP}


def passt_zusammen(vorgang: dict, mail: Gesendet) -> bool:
    """Trägt diese gesendete Mail den Vorgang?

    Kriterium: mindestens ein unterscheidungskräftiges Wort aus `thread_key` oder
    `gegenueber` steht im Betreff oder in der Empfängeradresse. Ein einzelnes Wort
    genügt bewusst — die Absicherung gegen Fehlzuordnung ist die
    Eindeutigkeitsregel in `vorschlaege()`, nicht eine höhere Schwelle hier.
    """
    quelle = tokens(vorgang.get("thread_key", "")) | tokens(
        vorgang.get("gegenueber", "")
    )
    if not quelle:
        return False
    ziel = tokens(mail.betreff) | tokens(mail.empfaenger)
    return bool(quelle & ziel)


def wartet_auf_versand(vorgang: dict) -> bool:
    if vorgang.get("bucket") != "owner":
        return False
    text = " ".join(
        str(vorgang.get(k, "")) for k in ("kurz", "next_trigger", "zustand")
    )
    return bool(WARTET_AUF_VERSAND.search(text))


def nach_letzter_pruefung(vorgang: dict, mail: Gesendet) -> bool:
    """Nur Mails, die nach der letzten Ledger-Prüfung rausgingen.

    Verglichen wird auf der Genauigkeit, die beide Seiten haben: Tragen Mail und
    Prüfung eine Uhrzeit, entscheidet die Minute, sonst gilt der ganze Tag.
    Früher wurde der Tag der Mail gegen den Zeitstempel der Prüfung verglichen —
    '2026-10-01' >= '2026-10-01 06:34' ist als Zeichenkette falsch, also fiel jede
    am Prüftag gesendete Mail heraus (platform#3658).
    """
    stand = str(vorgang.get("letzte_pruefung") or "")
    if not stand:
        return True
    if len(mail.datum) >= MINUTE and len(stand) >= MINUTE:
        return mail.datum[:MINUTE] >= stand[:MINUTE]
    return mail.tag() >= stand[:10]


def _kennwoerter(vorgang: dict) -> set[str]:
    return tokens(vorgang.get("thread_key", "")) | tokens(vorgang.get("gegenueber", ""))


def geteilte_woerter(ledger: dict) -> dict[str, set[str]]:
    """Je Konto die Wörter, die in mehr als einem offenen Vorgang stehen.

    Ein solches Wort (Ort, Projektname, Behörde) belegt keinen bestimmten Vorgang.
    Realfall 2026-10-01: Mit dem Datumsfix fand der Abgleich zwei Mails, die nur
    über 'guenzburg' bzw. 'meiki' passten — beide Wörter stehen in einem Dutzend
    offener Vorgänge, beide Zuordnungen waren falsch (platform#3659).
    """
    zaehler: dict[str, dict[str, int]] = {}
    for v in ledger.get("vorgaenge", []):
        if v.get("bucket") == "erledigt":
            continue
        konto = zaehler.setdefault(v.get("konto", ""), {})
        for w in _kennwoerter(v):
            konto[w] = konto.get(w, 0) + 1
    return {k: {w for w, n in z.items() if n > 1} for k, z in zaehler.items()}


def vorschlaege(ledger: dict, mails: dict[str, list[Gesendet]]) -> list[dict]:
    """→ je Vorgang ein Befund: `treffer`, `mehrdeutig` oder `offen`.

    `treffer` (wird mit --apply geschrieben) verlangt mindestens ein gemeinsames
    Wort, das nur diesem offenen Vorgang gehört. Passt eine Mail nur über
    geteilte Wörter, heißt das `mehrdeutig`: Vorschlag, kein Schreiben.
    """
    geteilt = geteilte_woerter(ledger)
    out = []
    for v in ledger.get("vorgaenge", []):
        if not wartet_auf_versand(v):
            continue
        konto = v.get("konto", "")
        kandidaten = [
            m
            for m in mails.get(konto, [])
            if passt_zusammen(v, m) and nach_letzter_pruefung(v, m)
        ]
        eigene = _kennwoerter(v) - geteilt.get(konto, set())
        eindeutig = [
            m for m in kandidaten if eigene & (tokens(m.betreff) | tokens(m.empfaenger))
        ]
        if not kandidaten:
            lage = "offen"
        elif not eindeutig:
            lage = "mehrdeutig"
        else:
            kandidaten = eindeutig
            # Mehrere Treffer waren bis 2026-08-21 ein Abbruch ("mehrdeutig").
            # Die Positivkontrolle zeigte, warum das zu streng war: bei einem
            # laufenden Strang passen naturgemaess mehrere gesendete Mails auf
            # DENSELBEN Vorgang — und der Bucket-Wechsel ist in jedem Fall
            # derselbe, egal welche davon der Beleg ist. Gefaehrlich waere
            # Mehrdeutigkeit ZWISCHEN Vorgaengen; die entsteht hier nicht, weil
            # jeder Vorgang fuer sich geprueft wird. Also: juengste Mail als
            # Beleg nehmen, statt den Fall liegen zu lassen.
            kandidaten = sorted(kandidaten, key=lambda m: m.datum, reverse=True)
            lage = "treffer"
        out.append({"nr": v.get("nr"), "vorgang": v, "lage": lage, "mails": kandidaten})
    return out


# ── Postfach-Zugriff (read-only) ────────────────────────────────────────────


def _imap_gesendet(konto: str, tage: int, limit: int) -> list[Gesendet]:
    roh = subprocess.run(
        [
            sys.executable,
            str(HIER / "read_mail.py"),
            "--account",
            konto,
            "--folder",
            SENDEORDNER_IMAP,
            "--list",
            str(limit),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if roh.returncode != 0:
        raise RuntimeError(f"read_mail ({konto}) fehlgeschlagen: {roh.stderr[:200]}")
    daten = json.loads(roh.stdout)
    grenze = datetime.now(timezone.utc) - timedelta(days=tage)
    out = []
    for t in daten.get("treffer", []):
        iso = _datum_iso(t.get("datum", ""))
        if iso and iso < grenze.strftime("%Y-%m-%d"):
            continue
        out.append(Gesendet(iso, t.get("betreff", ""), t.get("an", "")))
    return out


_GRAPH_ZEILE = re.compile(
    r"·\s+(?P<datum>\d{4}-\d{2}-\d{2}T\d{2}:\d{2})\s+(?P<rest>.+)"
)


def _graph_gesendet(tage: int) -> list[Gesendet]:
    roh = subprocess.run(
        [
            sys.executable,
            str(HIER / "graph_mail.py"),
            "--find",
            "--all",
            "--days",
            str(tage),
            "--source",
            SENDEORDNER["iil"],
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if roh.returncode != 0:
        raise RuntimeError(f"graph_mail fehlgeschlagen: {roh.stderr[:200]}")
    out = []
    for zeile in roh.stdout.splitlines():
        m = _GRAPH_ZEILE.search(zeile)
        if not m:
            continue
        rest = m.group("rest").split(None, 1)
        betreff = rest[1].strip() if len(rest) > 1 else ""
        out.append(Gesendet(_graph_zeit(m.group("datum")), betreff))
    return out


def _ortszeit(zeitpunkt: datetime) -> str:
    """Zeitpunkt → 'YYYY-MM-DD HH:MM' in Ortszeit, wie board.py das Ledger stempelt."""
    if zeitpunkt.tzinfo is not None:
        zeitpunkt = zeitpunkt.astimezone().replace(tzinfo=None)
    return zeitpunkt.strftime(ZEITFORMAT)


def _datum_iso(rfc: str) -> str:
    """'Wed, 19 Aug 2026 13:27:32 +0000' → '2026-08-19 13:27' auf UTC-Host (leer, wenn unparsbar)."""
    try:
        from email.utils import parsedate_to_datetime

        return _ortszeit(parsedate_to_datetime(rfc))
    except Exception:
        return ""


def _graph_zeit(utc: str) -> str:
    """Graph liefert UTC ('2026-10-01T10:18') → Ortszeit wie im Ledger."""
    try:
        return _ortszeit(datetime.fromisoformat(utc).replace(tzinfo=timezone.utc))
    except ValueError:
        return utc[:10]


def sammle(konten: set[str], tage: int, limit: int) -> dict[str, list[Gesendet]]:
    mails: dict[str, list[Gesendet]] = {}
    for k in sorted(konten):
        mails[k] = (
            _graph_gesendet(tage) if k == "iil" else _imap_gesendet(k, tage, limit)
        )
    return mails


# ── Schreiben ───────────────────────────────────────────────────────────────


def uebernehmen(vorgang: dict, mail: Gesendet, heute: str) -> None:
    """Vorgang auf `warten` stellen und den Beleg in die Notiz schreiben."""
    vorgang["bucket"] = "warten"
    vorgang["letzte_pruefung"] = heute
    vorgang["notiz"] = (vorgang.get("notiz", "") or "") + (
        f" | {heute} Sendeabgleich: '{mail.betreff[:80]}' liegt seit {mail.tag()} im "
        "Sendeordner — Bucket owner -> warten (es wartet die Gegenseite, nicht der Versand)."
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Vorgänge im Bucket 'owner' gegen den Sendeordner abgleichen."
    )
    ap.add_argument(
        "--tage", type=int, default=3, help="Rückblick in Tagen (Default 3)"
    )
    ap.add_argument(
        "--limit", type=int, default=40, help="Mails je IMAP-Konto (Default 40)"
    )
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Treffer ins Ledger schreiben (sonst nur Anzeige)",
    )
    args = ap.parse_args()

    pfad = Path(args.ledger)
    ledger = json.loads(pfad.read_text(encoding="utf-8"))
    konten = {
        v.get("konto", "")
        for v in ledger.get("vorgaenge", [])
        if wartet_auf_versand(v) and v.get("konto")
    }
    if not konten:
        print("Kein Vorgang wartet auf Versand.")
        return 0

    mails = sammle(konten, args.tage, args.limit)
    befunde = vorschlaege(ledger, mails)
    geschrieben = 0
    heute = date.today().isoformat()

    for b in befunde:
        v, lage = b["vorgang"], b["lage"]
        kopf = f"{b['nr']:>4}  {(v.get('kurz') or '')[:44]:<44}"
        if lage == "treffer":
            m = b["mails"][0]
            print(f"{kopf} TREFFER    {m.tag()}  {m.betreff[:52]}")
            if args.apply:
                uebernehmen(v, m, heute)
                geschrieben += 1
        elif lage == "mehrdeutig":
            print(
                f"{kopf} MEHRDEUTIG {len(b['mails'])} Mail(s) nur über Wörter anderer "
                "Vorgänge — bitte selbst zuordnen"
            )
        else:
            print(f"{kopf} offen      keine passende Mail im Sendeordner")

    if args.apply and geschrieben:
        schreibe_privat(pfad, json.dumps(ledger, ensure_ascii=False, indent=2))
        print(f"\n{geschrieben} Vorgang/Vorgaenge auf 'warten' gestellt.")
    elif not args.apply:
        print("\n(Anzeige — mit --apply werden die TREFFER ins Ledger geschrieben.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
