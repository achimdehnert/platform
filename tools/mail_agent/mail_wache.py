#!/usr/bin/env python3
"""Mail-Wache — Weckruf bei neuer Mail (chat-hub#48 F4, Owner-Grant 2026-09-05).

Analog zur Chat-Wache (`chat-hub/deploy/chat_lotse.py cmd_watch`): eine
Dauer-Session, die keinen Vorgang bearbeitet, sondern nur meldet, dass sich
etwas getan hat — je neuer Mail EINE JSON-Zeile auf stdout, `flush=True`.
Die Raum-Session "Mail" setzt dieses Werkzeug als zweiten Monitor, um nicht
selbst pollen zu muessen.

**Zwei Wege, ein Prozess:**
- IMAP-Konten (hnu, ad, ggf. weitere aus `~/.claude/mail-<konto>.env`): je
  Konto ein eigener Thread (imaplib ist blockierend). Meldet der Server
  `IDLE` in CAPABILITY, wird IDLE genutzt (Long-Poll, Re-IDLE alle ~25 min);
  sonst Poll alle `--intervall` Sekunden.
- Graph (iil, `achim.dehnert@iil.gmbh`): kein IDLE im genutzten Scope — Poll
  alle `--intervall` Sekunden ueber denselben Client wie `graph_mail.py`.

**Strikt lesend.** Keine Nachricht wird als gelesen markiert, verschoben oder
geloescht (`readonly=True` / kein PATCH). Kein Body, keine Anhaenge in der
Ausgabe — nur Kopfdaten (Konto, Ordner, UID/Graph-ID, Absender, Betreff, Zeit,
optional ein Link).

**Konten ohne Zugangsdatei werden uebersprungen, nicht abgebrochen** — eine
Zeile auf stderr je fehlendes Konto, die Wache laeuft mit dem Rest weiter.

**Fehler je Konto** werden mit exponentiellem Backoff (5s...5min) erneut
versucht; die anderen Konten laufen unbeeinflusst weiter. Bleibt ein Konto
laenger als 15 Minuten unerreichbar, kommt zusaetzlich EINE JSON-Fehlerzeile
auf stdout (`{"konto": ..., "fehler": ...}`) — nicht stumm bleiben.

**Stopp:** SIGINT/SIGTERM beendet laufende IDLE-Zyklen und Verbindungen
saeuberlich, Exit 0.

**Selbsttest:** `--einmal` verbindet sich einmal je Konto, meldet auf stderr,
ob IDLE moeglich ist (IMAP) bzw. ob der Graph-Token gueltig ist, und beendet
sich ohne stdout-Ausgabe (kein "Neues seit Start", weil der Startpunkt der
hoechste vorhandene Stand ist).

Aufruf::

    python3 tools/mail_agent/mail_wache.py
    python3 tools/mail_agent/mail_wache.py --konten hnu,iil --ordner INBOX
    python3 tools/mail_agent/mail_wache.py --einmal --konten hnu
"""

from __future__ import annotations

import argparse
import imaplib
import json
import re
import signal
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_mail  # noqa: E402
from mail_view import slugify  # noqa: E402
from read_mail import (  # noqa: E402
    CONFIG_FILE,
    _mailbox_arg,
    bulk_kopfsaetze,
    connect,
    decode_hdr,
    ordner_klartext,
    parse_env,
)

#: Konten, die ohne --konten geprueft werden — "ad" ist der read_mail-Default
#: (~/.claude/mail.env), analog zur Zeile "AD (Default)" in mailcheck.md.
DEFAULT_KONTEN = ("hnu", "iil", "ad")

#: Wie lange ein IDLE-Zyklus hoechstens still haelt, bevor neu ge-IDLE-t wird
#: (RFC 2177 empfiehlt < 29 min; einige Server kappen frueher).
IDLE_TIMEOUT_S = 25 * 60

#: Ab wann ein dauerhaft unerreichbares Konto zusaetzlich auf stdout landet.
STUMM_GRENZE_S = 15 * 60

#: Absender-Hinweis, ueber den das IIL-Geschaeftskonto unter den
#: GRAPH_ACCOUNTS gefunden wird (mail_link_server.py nutzt dieselbe Adresse
#: als graph_konto-Default).
IIL_KONTO_HINWEIS = "iil.gmbh"


# ---------------------------------------------------------------------------
# Reine Logik — ohne Netz, direkt in tests/test_mail_wache.py geprueft.
# ---------------------------------------------------------------------------


def zugangsdatei(konto: str) -> Path:
    """Konto-Kuerzel -> Pfad der Zugangsdatei dieser Maschine.

    ``iil`` haengt an Graph (``calendar.env``, dieselbe Config wie
    ``graph_mail.py``), ``ad`` ist der read_mail-Default (``mail.env`` ohne
    Konto-Suffix), alles andere folgt dem Muster ``mail-<konto>.env``.
    """
    if konto == "iil":
        return graph_mail.CONFIG_FILE
    if konto == "ad":
        return CONFIG_FILE
    return CONFIG_FILE.parent / f"mail-{konto}.env"


def waehle_konten(gewuenscht: list[str], existiert=None) -> tuple[list[str], list[str]]:
    """(erreichbare Konten, stderr-Meldungen fuer uebersprungene).

    ``existiert`` ist austauschbar (Test ohne echtes Dateisystem); Default
    ist ``Path.exists``.
    """
    pruefen = existiert or (lambda p: p.exists())
    ok: list[str] = []
    meldungen: list[str] = []
    for konto in gewuenscht:
        pfad = zugangsdatei(konto)
        if pruefen(pfad):
            ok.append(konto)
        else:
            meldungen.append(
                f"Konto {konto}: keine Zugangsdatei ({pfad}), übersprungen"
            )
    return ok, meldungen


def idle_in_capability(capability_zeile: bytes | str) -> bool:
    """Steht ``IDLE`` in einer CAPABILITY-Antwortzeile (RFC 2177)?"""
    text = (
        capability_zeile.decode("ascii", "replace")
        if isinstance(capability_zeile, bytes)
        else capability_zeile
    )
    return "IDLE" in (text or "").upper().split()


_EXISTS_ZEILE = re.compile(rb"^\*\s+(\d+)\s+EXISTS\b", re.I)


def parse_exists_zeile(zeile: bytes | None) -> int | None:
    """IDLE-Antwortzeile ``* 12 EXISTS`` -> 12, sonst ``None``.

    Das ist die einzige IDLE-Zeile, die eine Ordner-Aenderung bedeutet — bloss
    aus dem Timeout zurueckkommen (``zeile is None``) heisst "nichts Neues".
    """
    if not zeile:
        return None
    m = _EXISTS_ZEILE.match(zeile)
    return int(m.group(1)) if m else None


def neue_uids(seit_uid: int, suche_antwort_bytes: bytes | None) -> list[int]:
    """``UID SEARCH``-Antwort (z.B. ``b'124 125 126'``) -> UIDs > seit_uid.

    Aufsteigend sortiert, damit der Aufrufer den neuen Hoechststand als
    letztes Element liest.
    """
    if not suche_antwort_bytes:
        return []
    alle = (int(x) for x in suche_antwort_bytes.split())
    return sorted(u for u in alle if u > seit_uid)


_ABSENDER_ADRESSE = re.compile(r"<([^<>]+)>")


def kurz_absender(anzeige: str) -> str:
    """``'Vorname Nachname <a@b.c>'`` -> ``'Vorname Nachname'``.

    Ohne erkennbaren Namen bleibt die Adresse selbst (kein leeres Feld).
    """
    anzeige = (anzeige or "").strip()
    m = _ABSENDER_ADRESSE.search(anzeige)
    if not m:
        return anzeige
    name = anzeige[: m.start()].strip().strip('"').strip()
    return name or m.group(1)


def zeile_aus_header(konto: str, ordner: str, uid: str, header: dict[str, str]) -> dict:
    """Kopfzeilen (roh, ggf. RFC-2047-kodiert) -> fertige Ausgabezeile ohne Link.

    Betreff/Absender laufen durch ``decode_hdr`` (dieselbe Dekodierung wie
    ``read_mail.py``) — ein roher ``=?UTF-8?B?...?=``-Betreff waere sonst
    unlesbar.
    """
    von = decode_hdr(header.get("From", ""))
    betreff = decode_hdr(header.get("Subject", "")) or "(kein Betreff)"
    return {
        "konto": konto,
        "ordner": ordner,
        "uid": str(uid),
        "von": kurz_absender(von),
        "betreff": betreff,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def link_fuer(konto: str, ordner: str, uid: str, slugs: dict[str, str]) -> str | None:
    """Lotsen-Link im Muster von ``mail_link_server.py``
    (``/m/<konto>/<ordner-slug>/<uid>``) — oder ``None``.

    ``slugs`` ist ``{IMAP-Ordnername: Klartext-Slug}`` fuer die tatsaechlich
    beobachteten Ordner dieses Laufs. Ein Ordner ohne Eintrag bekommt KEINEN
    Link (nie raten, Lesson ``feedback_lotsen_link_getippt_statt_erzeugt``) —
    das betrifft insbesondere Graph (iil): dort braucht ein Link erst eine
    Kurz-ID-Registrierung, die diese Wache nicht anlegt.
    """
    slug = slugs.get(ordner)
    if not slug:
        return None
    return f"https://mail.iil.pet/m/{konto}/{slug}/{uid}"


def slugs_fuer_ordner(ordner_roh: str) -> dict[str, str]:
    """``{roher IMAP-Ordnername: Klartext-Slug}`` fuer genau diesen einen Ordner."""
    return {ordner_roh: slugify(ordner_klartext(ordner_roh))}


def backoff_sekunden(versuch: int) -> int:
    """5s beim 1. Fehlversuch, danach je Versuch verdoppelt, Deckel 5 min.

    ``versuch`` zaehlt ab 1 (wie ``chat_lotse.backoff_seconds``, dieselbe
    Formel — nur mit hoeherem Deckel, weil ein Mail-Server seltener kurz
    aussetzt als ein Chat-Sync).
    """
    return min(5 * (2 ** (versuch - 1)), 300)


def iil_konto(accounts: list[str]) -> str:
    """Welches GRAPH_ACCOUNTS-Konto ist das IIL-Geschaeftspostfach?

    Erkannt am Adressbestandteil (wie ``mail_link_server.graph_konto``
    default) — kein geratener Index, aber ein Fallback auf das erste Konto,
    falls keins passt (fuer Test-/Einzelkonto-Setups).
    """
    for a in accounts:
        if IIL_KONTO_HINWEIS in a:
            return a
    return accounts[0]


# ---------------------------------------------------------------------------
# Netz — IMAP (Thread je Konto) und Graph (Poll).
# ---------------------------------------------------------------------------


def _stdout_zeile(lock: threading.Lock, obj: dict) -> None:
    with lock:
        print(json.dumps(obj, ensure_ascii=False), flush=True)


def _idle_capability(imap: imaplib.IMAP4_SSL) -> bytes:
    typ, data = imap.capability()
    return data[0] if typ == "OK" and data else b""


def _uid_search_all(imap: imaplib.IMAP4_SSL) -> list[int]:
    typ, data = imap.uid("SEARCH", None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return []
    return [int(x) for x in data[0].split()]


def _idle_once(imap: imaplib.IMAP4_SSL, timeout_s: int) -> bytes | None:
    """Ein IDLE-Zyklus: IDLE senden, bis zu ``timeout_s`` auf eine
    Server-Zeile warten, mit ``DONE`` sauber beenden.

    Kein imaplib-Standardbefehl (IDLE ist in RFC 2177, nicht in imaplib) —
    deshalb ueber das rohe Kommando/Socket der bestehenden Verbindung, wie es
    auch andere IDLE-Aufsaetze auf imaplib tun. Ein Timeout ist kein Fehler,
    sondern "nichts Neues in diesem Zyklus" -> ``None``.
    """
    tag = imap._new_tag()  # noqa: SLF001 - kein oeffentliches Aequivalent in imaplib
    imap.send(tag + b" IDLE\r\n")
    imap.readline()  # '+ idling' — Inhalt wird nicht weiter geprueft
    zeile: bytes | None = None
    imap.sock.settimeout(timeout_s)
    try:
        zeile = imap.readline()
    except (TimeoutError, socket.timeout):
        zeile = None
    finally:
        imap.sock.settimeout(None)
        imap.send(b"DONE\r\n")
        try:
            imap.readline()  # getaggtes OK zur DONE-Antwort
        except OSError:
            pass
    return zeile


def imap_wache(
    konto: str,
    ordner: str,
    stop: threading.Event,
    out_lock: threading.Lock,
    intervall: int,
    einmal: bool,
) -> None:
    """Ein IMAP-Konto dauerhaft beobachten (IDLE, sonst Poll) — laeuft in
    einem eigenen Thread, weil imaplib blockierend ist."""
    versuch = 0
    unerreichbar_seit: float | None = None
    while not stop.is_set():
        try:
            cfg = parse_env(zugangsdatei(konto))
            imap = connect(cfg)
        except (OSError, imaplib.IMAP4.error, KeyError) as exc:
            versuch += 1
            print(f"Konto {konto}: Verbindung fehlgeschlagen ({exc})", file=sys.stderr)
            if unerreichbar_seit is None:
                unerreichbar_seit = time.monotonic()
            elif time.monotonic() - unerreichbar_seit > STUMM_GRENZE_S:
                _stdout_zeile(out_lock, {"konto": konto, "fehler": str(exc)[:200]})
                unerreichbar_seit = time.monotonic()
            if stop.wait(backoff_sekunden(versuch)):
                return
            continue

        try:
            imap.select(_mailbox_arg(ordner), readonly=True)
            kann_idle = idle_in_capability(_idle_capability(imap))
            hoechste = max(_uid_search_all(imap), default=0)
            print(
                f"Konto {konto}: verbunden, Ordner '{ordner}', "
                f"IDLE={'ja' if kann_idle else 'nein'}, Start-UID {hoechste}",
                file=sys.stderr,
            )
            versuch = 0
            unerreichbar_seit = None
            if einmal:
                return

            slugs = slugs_fuer_ordner(ordner)
            while not stop.is_set():
                if kann_idle:
                    zeile = _idle_once(imap, min(IDLE_TIMEOUT_S, 24 * 60))
                    if parse_exists_zeile(zeile) is None:
                        continue
                elif stop.wait(intervall):
                    return

                typ, data = imap.uid("SEARCH", None, f"UID {hoechste + 1}:*")
                neue = neue_uids(hoechste, data[0] if typ == "OK" and data else None)
                if not neue:
                    continue
                hoechste = max(hoechste, max(neue))
                ids = [str(u).encode() for u in neue]
                for uid, msg in bulk_kopfsaetze(imap, ids):
                    header = {
                        "From": msg.get("From", ""),
                        "Subject": msg.get("Subject", ""),
                    }
                    zeile_obj = zeile_aus_header(konto, ordner, uid, header)
                    link = link_fuer(konto, ordner, uid, slugs)
                    if link:
                        zeile_obj["link"] = link
                    _stdout_zeile(out_lock, zeile_obj)
        except (imaplib.IMAP4.abort, OSError) as exc:
            versuch += 1
            print(f"Konto {konto}: Verbindung verloren ({exc})", file=sys.stderr)
            if unerreichbar_seit is None:
                unerreichbar_seit = time.monotonic()
            elif time.monotonic() - unerreichbar_seit > STUMM_GRENZE_S:
                _stdout_zeile(out_lock, {"konto": konto, "fehler": str(exc)[:200]})
                unerreichbar_seit = time.monotonic()
            if stop.wait(backoff_sekunden(versuch)):
                return
        finally:
            try:
                imap.logout()
            except OSError:
                pass


def graph_wache(
    konto: str,
    stop: threading.Event,
    out_lock: threading.Lock,
    intervall: int,
    einmal: bool,
) -> None:
    """Das IIL-Geschaeftspostfach per Poll beobachten (Graph, kein IDLE
    im genutzten Scope) — Start = jetzt, kein Bestand wird nachgeliefert."""
    cfg = graph_mail.load_cfg()
    acc = iil_konto(cfg["accounts"])
    seit = datetime.now(timezone.utc)
    versuch = 0
    unerreichbar_seit: float | None = None

    while not stop.is_set():
        tok = graph_mail.token(cfg, acc)
        if not tok:
            versuch += 1
            print(
                f"Konto {konto}: {acc} nicht angemeldet — graph_mail.py --login {acc}",
                file=sys.stderr,
            )
            if unerreichbar_seit is None:
                unerreichbar_seit = time.monotonic()
            elif time.monotonic() - unerreichbar_seit > STUMM_GRENZE_S:
                _stdout_zeile(out_lock, {"konto": konto, "fehler": "nicht angemeldet"})
                unerreichbar_seit = time.monotonic()
            if einmal or stop.wait(backoff_sekunden(versuch)):
                return
            continue

        try:
            since_str = seit.strftime("%Y-%m-%dT%H:%M:%SZ")
            url = (
                f"{graph_mail.GRAPH}/me/mailFolders/inbox/messages?$top=50"
                "&$select=id,subject,from,receivedDateTime"
                f"&$filter=receivedDateTime gt {since_str}"
                "&$orderby=receivedDateTime asc"
            )
            r = graph_mail._http("GET", url, headers=graph_mail._auth(tok))  # noqa: SLF001
            j = r.json()
            if isinstance(j, dict) and "error" in j:
                fehler = j["error"]
                raise RuntimeError(
                    fehler.get("message", str(fehler))
                    if isinstance(fehler, dict)
                    else str(fehler)
                )
            versuch = 0
            unerreichbar_seit = None
            if einmal:
                print(f"Konto {konto}: verbunden, Poll-Weg ({acc})", file=sys.stderr)
                return

            for m in j.get("value", []):
                header = {
                    "From": ((m.get("from") or {}).get("emailAddress") or {}).get(
                        "address", ""
                    ),
                    "Subject": m.get("subject", ""),
                }
                zeile_obj = zeile_aus_header(konto, "inbox", m.get("id", ""), header)
                # Kein Link: ein Graph-Link braucht erst eine Kurz-ID-Registrierung
                # (mail_link_server._graph_rendern) — die legt diese Wache nicht an.
                _stdout_zeile(out_lock, zeile_obj)
                empfangen = m.get("receivedDateTime")
                if empfangen:
                    ts = datetime.fromisoformat(empfangen.replace("Z", "+00:00"))
                    seit = max(seit, ts)
        except (RuntimeError, OSError, ValueError) as exc:
            versuch += 1
            print(f"Konto {konto}: Abfrage fehlgeschlagen ({exc})", file=sys.stderr)
            if unerreichbar_seit is None:
                unerreichbar_seit = time.monotonic()
            elif time.monotonic() - unerreichbar_seit > STUMM_GRENZE_S:
                _stdout_zeile(out_lock, {"konto": konto, "fehler": str(exc)[:200]})
                unerreichbar_seit = time.monotonic()

        if stop.wait(intervall):
            return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--konten",
        default=",".join(DEFAULT_KONTEN),
        help=f"Komma-Liste, Default: {','.join(DEFAULT_KONTEN)}",
    )
    p.add_argument("--ordner", default="INBOX", help="IMAP-Ordner (Default INBOX)")
    p.add_argument(
        "--einmal",
        action="store_true",
        help="Selbsttest: je Konto einmal verbinden, Verbindungsbeleg auf stderr, dann beenden",
    )
    p.add_argument(
        "--intervall",
        type=int,
        default=120,
        help="Poll-Abstand in Sekunden (Default 120)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gewuenscht = [k.strip() for k in args.konten.split(",") if k.strip()]
    ok, meldungen = waehle_konten(gewuenscht)
    for meldung in meldungen:
        print(meldung, file=sys.stderr)
    if not ok:
        print("Kein erreichbares Konto — nichts zu tun.", file=sys.stderr)
        return 1

    stop = threading.Event()

    def _auf_signal(_signum, _frame) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _auf_signal)
    signal.signal(signal.SIGTERM, _auf_signal)

    out_lock = threading.Lock()
    threads: list[threading.Thread] = []
    for konto in ok:
        ziel = graph_wache if konto == "iil" else imap_wache
        wache_args = (
            (konto, stop, out_lock, args.intervall, args.einmal)
            if konto == "iil"
            else (konto, args.ordner, stop, out_lock, args.intervall, args.einmal)
        )
        t = threading.Thread(target=ziel, args=wache_args, daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    print("Wache beendet", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
