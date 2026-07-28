#!/usr/bin/env python3
"""Vorgangs-Sicht auf ein IMAP-Postfach — STRIKT READ-ONLY.

Zwei Fragen, zwei Werkzeuge, weil es zwei verschiedene Dinge sind (ADR-286 §4.9):

**Leser (personenzentriert).** Ein Ordnerbaum wie `Betreuungen/<Person>` IST bereits
ein Vorgangs-System: der Ordnername ist die Vorgangskennung, die Lage im Baum der
Zustand (`.erledigt/` = abgeschlossen). Daraus laesst sich die Abbildung
Absender -> Vorgang **lesen**, statt sie in einer zweiten Datenhaltung zu
erfinden. Der Leser beantwortet damit „zeig mir Vorgang X" ueber Ordnerinhalt
UND die noch nicht einsortierten Posteingangs-Mails derselben Absender.

**Sachverhalt (themenzentriert).** Ein Ordnerbaum kodiert Zustaendigkeit, nicht
Thema. Ein Sachverhalt, an dem drei Organisationen beteiligt sind, liegt in drei
Ordnern und ist ueber die Ablage nicht auffindbar. Dafuer gibt es die
ordneruebergreifende Suche — anlassbezogen, auf eine konkrete Frage, ohne
Speicherung. Das ist RETRIEVAL, nicht die systematische Auswertung, die der
Art.-14-Nachtrag der DSFA ausschliesst; der Unterschied liegt in Anlass und
Verbleib, nicht in der Technik.

Grenzen, ausdruecklich:
- Es wird NICHTS geschrieben, verschoben, markiert oder gespeichert. Der Zustand
  bleibt im Postfach des Verantwortlichen.
- Zuordnungen aus dem Absender sind VORSCHLAEGE. Mehrdeutige werden als solche
  ausgewiesen, nie stillschweigend aufgeloest (ADR-284 §7 „nie stumm weg").
- Die Sachsuche findet, was den Begriff enthaelt. Wer das Thema umschreibt, faellt
  durch — eine echte Luecke, die sichtbar bleiben soll.

Kommandos:
  --list                       Vorgaenge auflisten (Anzahl, Zustand)
  --show "<Vorgang>"           Ordnerinhalt + nicht einsortierte Posteingangs-Mails
  --suggest                    Zuordnungsvorschlaege fuer den Posteingang
  --topic "<Begriff>"          Sachverhalt ueber ALLE Ordner zusammenstellen
"""

from __future__ import annotations

import argparse
import email
import re
import sys
import time
from datetime import datetime, timezone
from typing import NamedTuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import deckungsausweis as dz  # noqa: E402
import indexierung as ix  # noqa: E402
import organize_mail as om  # noqa: E402
import read_mail as rm  # noqa: E402

ADR_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
ERLEDIGT_MARKER = ".erledigt"
TOOL_VERSION = "vorgang.py/2"

#: Konfigurationen, die kein Postfach mit echter Korrespondenz beschreiben und deshalb
#: nicht in den Konten-Nenner gehören.
KEINE_KORRESPONDENZ = frozenset({"search", "folders"})


def _jetzt() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bekannte_konten(basis: Path | None = None) -> list[str]:
    """Alle konfigurierten Postfächer — der Nenner der Konten-Ebene (KONZ-035 §5.3 R-1).

    ``basis`` überschreibt das Konfigurationsverzeichnis, damit ein Test die Auswahl
    prüfen kann, ohne von der Maschine abzuhängen, auf der er läuft.

    Ohne diese Zählung kehrt der stille Scope eine Ebene höher wieder: ein Lauf über
    *alle* Ordner *eines* Kontos sieht vollständig aus und ist es nicht.

    Nicht mitgezählt werden Konfigurationen, die **kein echtes Postfach mit Korrespondenz**
    beschreiben: ``search`` ist das Referenzpostfach mit erfundenen Nachrichten, ``folders``
    eine Hilfs-Konfiguration. Im ersten Pilotlauf standen sie im Nenner und machten aus
    „1 von 3" ein „1 von 4" — ein Nenner, der zu groß ist, ist genauso falsch wie einer,
    der fehlt.
    """
    wurzel = basis or (Path.home() / ".claude")
    namen = ["default"] if (wurzel / "mail.env").exists() else []
    namen += sorted(p.stem.removeprefix("mail-") for p in wurzel.glob("mail-*.env"))
    namen += graph_konten(wurzel / "graph-mail-tokens")
    return [n for n in namen if n not in KEINE_KORRESPONDENZ]


def graph_konten(basis: Path | None = None) -> list[str]:
    """Postfächer, die über Microsoft Graph laufen — für dieses Werkzeug unerreichbar.

    ``basis`` überschreibt das Token-Verzeichnis. Nötig, damit ein Test die Funktion
    prüfen kann, ohne von der Maschine abzuhängen, auf der er läuft: die erste Fassung
    dieses Tests las das echte Home-Verzeichnis und war deshalb lokal grün und in der
    CI rot (Lauf 30295192917).

    Sie gehören trotzdem in den Nenner. Ein Konto, das ein Werkzeug nicht ansprechen
    kann, verschwindet sonst vollständig aus dem Blick: der Ausweis meldete „Konten 1/2"
    und sah damit vollständiger aus, als der Bestand hergibt. Ausgewiesen werden sie als
    `nicht_gedeckt` mit Grund — sichtbar fehlend statt unsichtbar fehlend.
    """
    verzeichnis = basis or (Path.home() / ".claude" / "graph-mail-tokens")
    if not verzeichnis.is_dir():
        return []
    return sorted(
        f"graph:{p.stem.replace('_at_', '@')}" for p in verzeichnis.glob("*.json")
    )


# ---------- reine Logik (ohne IMAP, damit testbar) ----------


class Vorgang(NamedTuple):
    """Ein Vorgang = ein Ordner eine Ebene unter der Wurzel.

    NamedTuple statt dataclass: die Testdateien dieses Repos laden Module ueber
    spec_from_file_location ohne sys.modules-Eintrag, und `dataclasses` schlaegt
    dabei beim Typ-Aufloesen fehl.
    """

    ordner: str
    name: str
    abgeschlossen: bool


def vorgaenge_aus_ordnern(ordner: list[str], wurzel: str) -> list[Vorgang]:
    """Ordnerpfade unterhalb der Wurzel zu Vorgaengen machen.

    `Betreuungen/Muster-Max`        -> offen
    `Betreuungen/.erledigt/Muster`  -> abgeschlossen
    Zwischenknoten wie `Betreuungen/Anfragen` sind Sammelordner, kein Vorgang —
    sie werden vom Aufrufer per --skip ausgeschlossen, nicht hier geraten.
    """
    praefix = wurzel.rstrip("/") + "/"
    out: list[Vorgang] = []
    for o in ordner:
        if not o.startswith(praefix):
            continue
        rest = o[len(praefix) :]
        abgeschlossen = rest.startswith(ERLEDIGT_MARKER + "/")
        name = rest[len(ERLEDIGT_MARKER) + 1 :] if abgeschlossen else rest
        if not name or "/" in name:
            continue  # nur eine Ebene je Vorgang
        if name == ERLEDIGT_MARKER:
            continue  # der Container selbst ist kein Vorgang
        out.append(Vorgang(o, name, abgeschlossen))
    return sorted(out, key=lambda v: (v.abgeschlossen, v.name.casefold()))


def zuordnung_bauen(
    absender_je_vorgang: dict[str, set[str]],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Absender -> Vorgang. Zweitrueckgabe: mehrdeutige Adressen mit ihren Vorgaengen.

    Mehrdeutig heisst NICHT „Fehler" — es sind typischerweise Dritte (Zweitgutachter,
    Sekretariat, Pruefungsamt), die in mehreren Vorgaengen vorkommen. Sie werden
    getrennt gefuehrt und nie automatisch einem Vorgang zugeschlagen.
    """
    treffer: dict[str, list[str]] = {}
    for vorgang, adressen in absender_je_vorgang.items():
        for a in adressen:
            treffer.setdefault(a.lower(), []).append(vorgang)
    eindeutig = {a: v[0] for a, v in treffer.items() if len(set(v)) == 1}
    mehrdeutig = {a: sorted(set(v)) for a, v in treffer.items() if len(set(v)) > 1}
    return eindeutig, mehrdeutig


def vorschlag_fuer(
    absender: str, eindeutig: dict[str, str], mehrdeutig: dict[str, list[str]]
) -> tuple[str, list[str]]:
    """('eindeutig', [v]) | ('mehrdeutig', [v1, v2]) | ('unbekannt', [])."""
    a = (absender or "").lower()
    if a in eindeutig:
        return "eindeutig", [eindeutig[a]]
    if a in mehrdeutig:
        return "mehrdeutig", mehrdeutig[a]
    return "unbekannt", []


def such_hinweis(begriff: str, feld: str) -> list[str]:
    """Warnungen zur Trefferqualitaet — VOR der Trefferliste, nicht als Fussnote.

    Die IMAP-Suche laeuft auf der Rohnachricht, nicht auf dekodiertem Text. Kurze
    Begriffe treffen deshalb in Base64-Bloecken, Message-IDs und URLs. Gemessen am
    2026-07-27 auf einem realen Postfach: derselbe Begriff lieferte 0 (SUBJECT),
    327 (BODY) und 678 (TEXT) Treffer — die Feldwahl entscheidet mehr als der Begriff.
    """
    hinweise = []
    if len(begriff.strip()) < 4:
        hinweise.append(
            f"Begriff '{begriff}' ist kurz (<4 Zeichen) — die Suche läuft auf der "
            f"Rohnachricht und trifft auch in Base64, Message-IDs und URLs. "
            f"Trefferzahl mit Vorsicht lesen."
        )
    if feld == "TEXT":
        hinweise.append(
            "Feld TEXT durchsucht Kopfzeilen UND Text. Für eine engere Menge "
            "--field BODY oder --field SUBJECT."
        )
    return hinweise


# ---------- IMAP-Anbindung ----------


def _absender(rohkopf: bytes) -> str | None:
    msg = email.message_from_bytes(rohkopf)
    t = ADR_RE.search(rm.decode_hdr(msg.get("From")) or "")
    return t.group(0).lower() if t else None


def _kopfzeilen(
    imap, ordner: str, felder: str, limit: int
) -> list[tuple[bytes, bytes]]:
    """UID + Rohkopf je Nachricht. Blockweises FETCH, sonst ein Round-Trip je Mail.

    ``UID`` wird **ausdrücklich mit angefordert**. RFC 3501 verlangt zwar, dass eine
    Antwort auf ``UID FETCH`` die UID enthält, aber der Exchange-Server des HNU-Kontos
    liefert nur die Sequenznummer (gemessen 2026-07-27: ``b'849 (BODY[HEADER.FIELDS …'``).
    Wer die UID dann aus dem Envelope liest, findet keine — und ein darauf aufbauender
    Filter meldet still **null Treffer**, während er die Nachrichten als „geprüft" zählt.
    Genau so war der Client-Filter im ersten Pilotlauf über 46.000 Nachrichten blind.
    """
    typ, _ = imap.select(f'"{ordner}"', readonly=True)
    if typ != "OK":
        return []
    typ, data = imap.uid("SEARCH", None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return []
    uids = data[0].split()[-limit:]
    out: list[tuple[bytes, bytes]] = []
    for i in range(0, len(uids), 200):
        block = b",".join(uids[i : i + 200]).decode()
        typ, resp = imap.uid(
            "FETCH", block, f"(UID BODY.PEEK[HEADER.FIELDS ({felder})])"
        )
        if typ != "OK":
            continue
        for teil in resp:
            if isinstance(teil, tuple) and teil[1]:
                out.append((teil[0], teil[1]))
    return out


def absender_im_ordner(imap, ordner: str, limit: int = 500) -> set[str]:
    return {
        a
        for _, kopf in _kopfzeilen(imap, ordner, "FROM", limit)
        if (a := _absender(kopf))
    }


def _zeile(kopf: bytes) -> str:
    msg = email.message_from_bytes(kopf)
    return (
        f"{rm.decode_hdr(msg.get('Date'))[:22]:<22}  "
        f"{rm.decode_hdr(msg.get('From'))[:34]:<34}  "
        f"{rm.decode_hdr(msg.get('Subject'))[:52]}"
    )


# ---------- Retrievalpfade (KONZ-035 §5.3 R-2) ----------
#
# Zwei Pfade, die sich in der IMPLEMENTIERUNG unterscheiden, nicht bloß im Parameter.
# Zwei Felder derselben Server-Suche teilen deren Blindstellen; erst der Kontrast
# Server-Suche gegen lokalen Filter macht eine Blindstelle sichtbar.


def pfad_server_suche(imap, begriff: str, feld: str) -> set[bytes]:
    """IMAP SEARCH — der Server entscheidet, was passt. Sieht auch Nachrichtentexte.

    Begriffe mit Umlauten müssen als UTF-8-Literal mit ``CHARSET UTF-8`` gehen.
    ``imaplib`` kodiert Argumente sonst als ASCII und wirft ``UnicodeEncodeError`` —
    im Ordner-Loop von ``cmd_topic`` sähe das aus wie ein unlesbarer Ordner, und eine
    Suche nach „Löschung" hätte in JEDEM Ordner still null Treffer gemeldet.
    Gefunden vom Referenzpostfach (KONZ-035 REC-10) beim ersten Lauf.
    """
    if begriff.isascii():
        typ, res = imap.uid("SEARCH", None, feld, begriff)
    else:
        imap.literal = begriff.encode("utf-8")
        typ, res = imap.uid("SEARCH", "CHARSET", "UTF-8", feld)
    if typ != "OK" or not res or not res[0]:
        return set()
    return set(res[0].split())


def pfad_client_filter(
    imap, ordner: str, begriff: str, limit: int
) -> tuple[set[bytes], int]:
    """Kopfzeilen holen, lokal vergleichen — die Gegenprobe zur Server-Suche.

    Deckt nur Absender und Betreff ab, nicht den Nachrichtentext. Diese Grenze ist der
    Grund, warum eine Differenz *in dieser Richtung* (Server findet mehr) normal ist,
    während die Gegenrichtung ein Befund über die Server-Suche ist.

    Gibt zusätzlich zurück, wie viele Nachrichten geprüft wurden — bei erreichtem
    Limit ist der Pfad abgeschnitten, und das gehört in den Ausweis statt in eine
    Fußnote.
    """
    kopfe = _kopfzeilen(imap, ordner, "FROM SUBJECT", limit)
    nadel = begriff.casefold()
    treffer = set()
    for roh_uid, kopf in kopfe:
        msg = email.message_from_bytes(kopf)
        heu = (
            f"{rm.decode_hdr(msg.get('From')) or ''} "
            f"{rm.decode_hdr(msg.get('Subject')) or ''}"
        ).casefold()
        if nadel in heu:
            if m := re.search(rb"UID (\d+)", roh_uid):
                treffer.add(m.group(1))
    return treffer, len(kopfe)


def nachrichten_laut_server(imap, ordner: str) -> int | None:
    """STATUS (MESSAGES) — die Zahl, die NICHT aus unserer eigenen Aufzählung stammt."""
    try:
        typ, res = imap.status(f'"{ordner}"', "(MESSAGES)")
    except Exception:  # noqa: BLE001 — ein Ordner ohne STATUS ist kein Grund zum Abbruch
        return None
    if typ != "OK" or not res or not res[0]:
        return None
    m = re.search(rb"MESSAGES\s+(\d+)", res[0])
    return int(m.group(1)) if m else None


def probekoerper(imap, ordner: list[str], limit: int) -> tuple[str, bytes, str] | None:
    """Erste Nachricht, mit der sich ein Pfad prüfen lässt — (Ordner, UID, Wort).

    Sucht über **mehrere** Ordner, nicht nur den ersten. Im HNU-Konto ist der erste
    Ordner alphabetisch `Archiv`, ein reiner Container ohne eigene Nachrichten: die
    Kalibrierung fand dort nichts und meldete „kein Probekörper" — für **beide** Pfade,
    obwohl beide funktionsfähig gewesen wären. Ein Kalibriertest, der am leeren Ordner
    scheitert, misst die Ordnerwahl, nicht die Suche.
    """
    for name in ordner:
        for roh_uid, kopf in _kopfzeilen(imap, name, "SUBJECT", min(limit, 50)):
            msg = email.message_from_bytes(kopf)
            betreff = rm.decode_hdr(msg.get("Subject")) or ""
            worte = re.findall(r"[A-Za-zÄÖÜäöüß]{5,}", betreff)
            m = re.search(rb"UID (\d+)", roh_uid)
            if worte and m:
                return name, m.group(1), worte[0]
    return None


def kalibriere_pfade(imap, ordner: list[str] | str, limit: int) -> dict[str, str]:
    """Findet jeder Pfad eine Nachricht wieder, von der bekannt ist, dass es sie gibt?

    Der Probekörper wird nicht mitgebracht, sondern aus dem Bestand selbst genommen:
    eine vorhandene Nachricht, ein hinreichend langes Wort aus ihrem Betreff, dann die
    Frage, ob der Pfad genau diese Nachricht zurückliefert.

    Das ist der Test, an dem der Fehlschlag vom 27.07. gescheitert wäre: ein Filter,
    der eine Nachricht nicht wiederfindet, die er gerade selbst gelesen hat, ist
    kaputt — und nicht Beleg dafür, dass es nichts gab.

    Rückgabe: Pfadname → "" bei Erfolg, sonst der Grund des Scheiterns.
    """
    kandidaten = [ordner] if isinstance(ordner, str) else list(ordner)
    ergebnis: dict[str, str] = {}
    probe = probekoerper(imap, kandidaten, limit)
    if not probe:
        grund = f"kein Probekörper in {len(kandidaten)} Ordner(n)"
        return {"server-suche": grund, "client-filter": grund}

    ordner, uid, wort = probe
    imap.select(f'"{ordner}"', readonly=True)
    gefunden = pfad_server_suche(imap, wort, "SUBJECT")
    ergebnis["server-suche"] = (
        "" if uid in gefunden else f"fand '{wort}' nicht in der eigenen Nachricht"
    )
    gefunden, _ = pfad_client_filter(imap, ordner, wort, limit)
    ergebnis["client-filter"] = (
        "" if uid in gefunden else f"fand '{wort}' nicht in der eigenen Nachricht"
    )
    return ergebnis


# ---------- Kommandos ----------


def cmd_list(imap, wurzel: str) -> None:
    vs = vorgaenge_aus_ordnern(om.list_folders(imap), wurzel)
    if not vs:
        print(f"Keine Vorgänge unterhalb '{wurzel}' gefunden.")
        return
    offen = [v for v in vs if not v.abgeschlossen]
    zu = [v for v in vs if v.abgeschlossen]
    print(
        f"Vorgänge unter '{wurzel}': {len(vs)} ({len(offen)} offen, {len(zu)} abgeschlossen)\n"
    )
    for v in vs:
        print(f"  {'abgeschlossen' if v.abgeschlossen else 'offen        '}  {v.name}")


def cmd_show(imap, wurzel: str, gesucht: str, posteingang: str) -> None:
    vs = vorgaenge_aus_ordnern(om.list_folders(imap), wurzel)
    treffer = [v for v in vs if gesucht.casefold() in v.name.casefold()]
    if not treffer:
        print(f"Kein Vorgang unter '{wurzel}' passt auf '{gesucht}'.")
        return
    if len(treffer) > 1:
        print(f"{len(treffer)} Vorgänge passen auf '{gesucht}' — bitte genauer:")
        for v in treffer:
            print(f"  {v.name}")
        return

    v = treffer[0]
    zustand = "abgeschlossen" if v.abgeschlossen else "offen"
    kopfe = _kopfzeilen(imap, v.ordner, "FROM DATE SUBJECT", 500)
    print(f"Vorgang: {v.name}  ({zustand}, {len(kopfe)} Nachricht(en) im Ordner)\n")
    for _, kopf in kopfe:
        print(f"  {_zeile(kopf)}")

    # Der eigentliche Zweck: was liegt noch UNSORTIERT im Posteingang?
    adressen = absender_im_ordner(imap, v.ordner)
    offen_im_eingang = [
        kopf
        for _, kopf in _kopfzeilen(imap, posteingang, "FROM DATE SUBJECT", 1000)
        if (a := _absender(kopf)) and a in adressen
    ]
    print(f"\n  Noch im Posteingang, nicht einsortiert: {len(offen_im_eingang)}")
    for kopf in offen_im_eingang:
        print(f"    {_zeile(kopf)}")
    if offen_im_eingang:
        print(
            "\n  (Einsortieren ist ein eigener, bestätigter Schritt — organize_mail --move.)"
        )


def cmd_suggest(imap, wurzel: str, posteingang: str, limit: int) -> None:
    vs = vorgaenge_aus_ordnern(om.list_folders(imap), wurzel)
    je_vorgang = {v.name: absender_im_ordner(imap, v.ordner) for v in vs}
    eindeutig, mehrdeutig = zuordnung_bauen(je_vorgang)

    kopfe = _kopfzeilen(imap, posteingang, "FROM DATE SUBJECT", limit)
    gruppen: dict[str, list[str]] = {"eindeutig": [], "mehrdeutig": [], "unbekannt": []}
    for _, kopf in kopfe:
        a = _absender(kopf) or ""
        art, vorgaenge = vorschlag_fuer(a, eindeutig, mehrdeutig)
        hinweis = (
            f"  -> {vorgaenge[0]}"
            if art == "eindeutig"
            else (
                f"  -> mehrdeutig: {', '.join(vorgaenge)}"
                if art == "mehrdeutig"
                else ""
            )
        )
        gruppen[art].append(f"{_zeile(kopf)}{hinweis}")

    print(
        f"Zuordnungs-Vorschläge für '{posteingang}' "
        f"({len(kopfe)} geprüft, {len(vs)} Vorgänge, {len(eindeutig)} bekannte Adressen)\n"
    )
    for art, titel in (
        ("eindeutig", "Eindeutig zuordenbar — VORSCHLAG, nicht ausgeführt"),
        ("mehrdeutig", "Mehrdeutig — Absender kommt in mehreren Vorgängen vor"),
    ):
        if gruppen[art]:
            print(f"{titel} ({len(gruppen[art])}):")
            for z in gruppen[art]:
                print(f"  {z}")
            print()
    # Restmenge ist die Kennzahl, nicht die Trefferzahl (ADR-284 §7a)
    print(f"Ohne Zuordnung (Restmenge): {len(gruppen['unbekannt'])} von {len(kopfe)}")


def cmd_topic(
    imap,
    begriff: str,
    feld: str,
    konto: str = "default",
    anlass: str = "",
    limit: int = 500,
    zweiter_pfad: bool = True,
    nenner_pruefen: bool = True,
) -> None:
    alle = om.list_folders(imap)
    # ADR-286 §4.10.7: ausgeschlossene Ordner werden NICHT durchsucht, bleiben aber
    # im Nenner (`ordner_vorhanden=len(alle)`) und erscheinen einzeln unter
    # "nicht gedeckt". Wer den Nenner mitverkleinert, baut genau die stille Luecke,
    # die der Ausweis sichtbar machen soll.
    zu_durchsuchen, ausgeschlossen = ix.aufteilen(alle)
    t0 = time.time()
    gestartet = _jetzt()
    gefunden: list[tuple[str, str]] = []
    durchsucht = 0
    fehlgeschlagen = 0
    abgeschnitten = 0
    # UIDs sind nur innerhalb eines Ordners eindeutig — für den Pfadvergleich also
    # (Ordner, UID) als Schlüssel, sonst verschmelzen fremde Nachrichten.
    treffer_je_pfad: dict[str, set[tuple[str, bytes]]] = {"server-suche": set()}
    if zweiter_pfad:
        treffer_je_pfad["client-filter"] = set()
    selbst_gezaehlt: dict[str, int] = {}
    laut_server: dict[str, int] = {}

    for name in zu_durchsuchen:
        try:
            typ, _ = imap.select(f'"{name}"', readonly=True)
            if typ != "OK":
                fehlgeschlagen += 1
                continue
            durchsucht += 1

            server_uids = pfad_server_suche(imap, begriff, feld)
            treffer_je_pfad["server-suche"] |= {(name, u) for u in server_uids}
            alle_uids = set(server_uids)

            if zweiter_pfad:
                client_uids, geprueft_hier = pfad_client_filter(
                    imap, name, begriff, limit
                )
                treffer_je_pfad["client-filter"] |= {(name, u) for u in client_uids}
                alle_uids |= client_uids
                if geprueft_hier >= limit:
                    # Abgeschnitten: die eigene Zahl ist dann das Limit, nicht der
                    # Bestand. Sie in die Nenner-Gegenprobe zu geben, meldete im ersten
                    # Pilotlauf 19 Ordner als „uneinig", obwohl nur trunkiert wurde —
                    # ein Fehlalarm, der die echte Divergenz unsichtbar macht.
                    abgeschnitten += 1
                else:
                    selbst_gezaehlt[name] = geprueft_hier
                    if nenner_pruefen and (n := nachrichten_laut_server(imap, name)):
                        laut_server[name] = n
                        imap.select(f'"{name}"', readonly=True)

            # R-4: Über-Einschluss vor Unter-Einschluss — angezeigt wird die
            # Vereinigung beider Pfade, nicht der Schnitt.
            uids = sorted(alle_uids)
            for i in range(0, len(uids), 200):
                block = b",".join(uids[i : i + 200]).decode()
                typ, resp = imap.uid(
                    "FETCH", block, "(BODY.PEEK[HEADER.FIELDS (FROM DATE SUBJECT)])"
                )
                if typ != "OK":
                    continue
                for teil in resp:
                    if isinstance(teil, tuple) and teil[1]:
                        gefunden.append((name, _zeile(teil[1])))
        except Exception:  # noqa: BLE001 — ein unlesbarer Ordner darf den Lauf nicht kippen
            fehlgeschlagen += 1
            continue

    kalibrierung: dict[str, str] = {}
    if durchsucht:
        try:
            kalibrierung = kalibriere_pfade(imap, alle, limit)
        except Exception as exc:  # noqa: BLE001
            kalibrierung = {
                p: f"Kalibrierung scheiterte: {exc}" for p in treffer_je_pfad
            }

    dauer = time.time() - t0
    beendet = _jetzt()

    for h in such_hinweis(begriff, feld):
        print(f"⚠ {h}", file=sys.stderr)

    # REC-2: der Ausweis steht VOR der Trefferliste. Als Fußnote wird er nach dreimal
    # Lesen unsichtbar, und genau dann wird die Trefferliste für vollständig gehalten.
    konten = bekannte_konten()
    andere = [k for k in konten if k != konto]
    nicht_gedeckt = [(f"Konto {k}", "in diesem Lauf nicht abgefragt") for k in andere]
    nicht_gedeckt += [(f"Ordner {o}", grund) for o, grund in ausgeschlossen]
    for pfad, grund in sorted(kalibrierung.items()):
        if grund:
            nicht_gedeckt.append((f"Pfad {pfad}", grund))
    if not zweiter_pfad:
        nicht_gedeckt.append(
            ("zweiter Retrievalpfad", "per --single-path abgeschaltet — R-2")
        )

    ausweis = dz.Ausweis(
        frage=f"{begriff} (Feld {feld})",
        anlass=anlass or "nicht angegeben",
        konten_vorhanden=len(konten) or 1,
        konten_durchsucht=1,
        ordner_vorhanden=len(alle),
        ordner_durchsucht=durchsucht,
        scan_started_at=gestartet,
        scan_finished_at=beendet,
        # Der Watermark ist das ENDE des Intervalls: alles, was danach eintraf, ist
        # nicht erfasst. Bei 10-77 s Laufzeit ist das kein theoretischer Fall.
        source_watermark=beendet,
        retrievalpfade=tuple(
            (pfad, len(menge)) for pfad, menge in sorted(treffer_je_pfad.items())
        ),
        kalibriert=tuple(p for p, grund in sorted(kalibrierung.items()) if not grund),
        ordner_fehlgeschlagen=fehlgeschlagen,
        seiten_unvollstaendig=abgeschnitten,
        nicht_gedeckt=tuple(nicht_gedeckt),
        nenner_divergenz=tuple(dz.nenner_pruefen(selbst_gezaehlt, laut_server)),
        query_fingerprint=dz.fingerprint(begriff, feld, sorted(alle)),
        tool_version=TOOL_VERSION,
    )
    print(dz.rendern(ausweis) + "\n")

    # R-2: der Wert der zwei Pfade liegt in der Differenz, nicht in der Summe.
    for a, b, anzahl in dz.divergenz(treffer_je_pfad):
        print(f"⚠ {anzahl} Nachricht(en) fand '{a}', '{b}' nicht.", file=sys.stderr)

    ordner_mit_treffern = len({o for o, _ in gefunden})
    print(
        f"Sachverhalt '{begriff}' (Feld {feld}) — {len(gefunden)} Nachricht(en) "
        f"in {ordner_mit_treffern} von {durchsucht} Ordnern ({dauer:.0f}s)\n"
    )
    aktuell = None
    for ordner, zeile in sorted(gefunden):
        if ordner != aktuell:
            print(f"  [{ordner}]")
            aktuell = ordner
        print(f"    {zeile}")
    print(
        "\n  Gefunden wird, was den Begriff enthält — wer das Thema umschreibt, fällt durch.\n"
        "  Nichts wurde gespeichert oder verändert."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="Vorgänge auflisten")
    g.add_argument("--show", metavar="VORGANG", help="einen Vorgang zusammenstellen")
    g.add_argument(
        "--suggest",
        action="store_true",
        help="Zuordnungsvorschläge für den Posteingang",
    )
    g.add_argument("--topic", metavar="BEGRIFF", help="Sachverhalt über ALLE Ordner")
    ap.add_argument("--root", default="Betreuungen", help="Wurzel des Vorgangsbaums")
    ap.add_argument("--inbox", default="INBOX", help="Posteingangs-Ordner")
    ap.add_argument("--field", default="TEXT", choices=["TEXT", "SUBJECT", "BODY"])
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--account", help="Postfach-Kürzel (z.B. hnu)")
    ap.add_argument(
        "--anlass",
        default="",
        help="warum gefragt wird — ohne Anlass ist die Verhältnismäßigkeit unprüfbar "
        "(KONZ-035 §5.2)",
    )
    ap.add_argument(
        "--single-path",
        action="store_true",
        help="nur die Server-Suche laufen lassen (schneller). Der Ausweis weist das "
        "als nicht gedeckt aus und sperrt die Vollständigkeitsaussage (R-2).",
    )
    ap.add_argument(
        "--no-verify-denominator",
        action="store_true",
        help="die Gegenprobe des Nenners gegen STATUS (MESSAGES) auslassen (REC-9)",
    )
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = rm.parse_env(rm._resolve_config(args.config, args.account))
    imap = rm.connect(cfg)
    try:
        if args.list:
            cmd_list(imap, args.root)
        elif args.show:
            cmd_show(imap, args.root, args.show, args.inbox)
        elif args.suggest:
            cmd_suggest(imap, args.root, args.inbox, args.limit)
        else:
            cmd_topic(
                imap,
                args.topic,
                args.field,
                konto=args.account or "default",
                anlass=args.anlass,
                limit=args.limit,
                zweiter_pfad=not args.single_path,
                nenner_pruefen=not args.no_verify_denominator,
            )
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
