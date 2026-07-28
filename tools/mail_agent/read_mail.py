#!/usr/bin/env python3
"""Mail-Lesen über den konfigurierten IMAP-Transport (Konsument: /read-mail Skill).

Konfiguration wie send_mail.py (~/.claude/mail.env + MAIL_CREDS_FILE) — nichts im Repo.
STRIKT READ-ONLY: select(readonly=True) + BODY.PEEK; markiert nie als gelesen,
löscht nie, verschiebt nie. Credentials werden niemals ausgegeben.

Entstanden, nachdem dieselbe IMAP-Logik 4x ad-hoc in Sessions gebaut wurde
(2026-07-17) — Wachstums-Pipeline Ad-hoc -> Skill. Capability-Profil: nutzbar
nur auf Maschinen mit ~/.claude/mail.env (Maschinen-Gate, kein Org-Default).
"""

from __future__ import annotations

import argparse
import email
import imaplib
import json
import re
import sys
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from pathlib import Path
from typing import NamedTuple

# Config-/Credentials-Parsing wird aus send_mail wiederverwendet (eine SSoT).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deckungsausweis as da  # noqa: E402
from indexierung import aufteilen  # noqa: E402
from send_mail import CONFIG_FILE, load_credentials, parse_env  # noqa: E402

#: Wird im Deckungsausweis mitgeführt — ein Ausweis ohne Werkzeug-Stand ist
#: später nicht mehr einzuordnen (KONZ-035 Pflichtfeld).
WERKZEUG = "read_mail.py/2026-07-28"


def _resolve_config(config: str | None, account: str | None) -> Path:
    """--config PFAD > --account NAME (→ ~/.claude/mail-<NAME>.env) > Default mail.env.
    --account hält jeden .env-Pfad aus der Kommandozeile (Secret-Leak-Guard-sicher)."""
    if config:
        return Path(config).expanduser()
    if account:
        return Path.home() / ".claude" / f"mail-{account}.env"
    return CONFIG_FILE


def _decode_chunk(chunk: bytes, charset: str | None) -> str:
    # Reale Mails tragen Charsets, die Python nicht kennt ("unknown-8bit",
    # "x-unknown", Tippfehler) — codecs.lookup wirft dann LookupError und riss
    # bisher den ganzen Header-Scan ab. latin-1 dekodiert jedes Byte.
    try:
        return chunk.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return chunk.decode("latin-1", errors="replace")


def decode_hdr(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(_decode_chunk(chunk, charset))
        else:
            parts.append(chunk)
    return "".join(parts).replace("\n", " ").replace("\r", "").strip()


def extract_text(msg: Message, max_chars: int = 4000) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and part.get_filename() is None:
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            text = payload.decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )
            if len(text) > max_chars:
                return text[:max_chars] + f"\n[... gekürzt, {len(text)} Zeichen gesamt]"
            return text
    return "(kein text/plain-Teil)"


def attachment_names(msg: Message) -> list[str]:
    return [decode_hdr(p.get_filename()) for p in msg.walk() if p.get_filename()]


def save_attachments(msg: Message, target: Path) -> list[tuple[str, int]]:
    target.mkdir(parents=True, exist_ok=True)
    saved = []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        name = Path(decode_hdr(fn)).name  # Pfad-Anteile strippen (kein Traversal)
        data = part.get_payload(decode=True) or b""
        (target / name).write_bytes(data)
        saved.append((name, len(data)))
    return saved


def matches_from(msg: Message, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in decode_hdr(msg.get("From")).lower()


def matches_to(msg: Message, needle: str | None) -> bool:
    """Substring-Match auf To **und** Cc — nötig, um im Gesendete-Ordner nach
    Empfänger zu filtern (dort ist der Absender immer man selbst)."""
    if not needle:
        return True
    hay = (decode_hdr(msg.get("To")) + " " + decode_hdr(msg.get("Cc"))).lower()
    return needle.lower() in hay


def matches_subject(msg: Message, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in decode_hdr(msg.get("Subject")).lower()


def _mailbox_arg(folder: str) -> str:
    """Ordnernamen mit Leerzeichen für IMAP quoten (z.B. 'Gesendete Objekte').
    imaplib quotet nicht selbst — ein unquoted Name mit Space bricht SELECT."""
    if " " in folder and not (folder.startswith('"') and folder.endswith('"')):
        return '"%s"' % folder
    return folder


def connect(cfg: dict[str, str]) -> imaplib.IMAP4_SSL:
    host = cfg.get("IMAP_HOST", cfg["SMTP_HOST"])
    port = int(cfg.get("IMAP_PORT", "993"))
    user, password = load_credentials(
        Path(cfg["MAIL_CREDS_FILE"]).expanduser(), cfg["MAIL_FROM"]
    )
    imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    imap.login(user, password)
    return imap


# LIST-Antwort: (flags) "trenner" name — der Name kann gequotet sein oder nicht.
# Naives Splitten am Trenner zerlegte Namen wie 'Sent-Archiv/2025' falsch und
# erzeugte Phantom-Ordner ('/" Notizen'), die dann beim SELECT die Verbindung rissen.
_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?P<sep>"[^"]*"|NIL)\s+(?P<name>.*)$')


def alle_ordner(imap: imaplib.IMAP4_SSL) -> tuple[list[str], list[str]]:
    """(selektierbare Ordner, unparsbare LIST-Zeilen).

    Die zweite Menge wird zurückgegeben statt verworfen: ein stillschweigend
    übersprungener Ordner ist genau die Lücke, die eine Vollerhebung wertlos macht.
    """
    typ, data = imap.list()
    ordner: list[str] = []
    unlesbar: list[str] = []
    for zeile in data or []:
        roh = zeile if isinstance(zeile, bytes) else str(zeile).encode()
        m = _LIST_RE.match(roh)
        if not m:
            unlesbar.append(roh.decode("utf-8", "replace"))
            continue
        if b"\\Noselect" in m.group("flags"):
            continue  # reiner Container, enthält per Definition keine Nachrichten
        name = m.group("name").decode("utf-8", "replace").strip()
        if len(name) >= 2 and name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        ordner.append(name)
    return ordner, unlesbar


def _such_kriterien(
    from_filter: str | None, to_filter: str | None, subject_filter: str | None
) -> list[str] | None:
    """IMAP-SEARCH-Kriterien, die denselben Treffer liefern wie die Matcher oben — oder None.

    Kalibriert am 2026-07-28 gegen den vollen client-seitigen Header-Scan (HNU,
    Exchange 2010): bei ASCII-Suchbegriffen deckungsgleich in 4 von 4 Fällen,
    u.a. 353/353 Treffer in einem Ordner mit 354 Nachrichten. Für Nicht-ASCII
    gibt imaplib den Begriff nicht über die Leitung ('ascii' codec ...) — dann
    None, und der Aufrufer scannt vollständig. Lieber langsam als still unvollständig.

    ``to_filter`` prüft To **oder** Cc, weil ``matches_to`` das auch tut — ein
    reines ``TO`` würde Cc-Empfänger verschweigen (falsch-negativ).
    """
    teile: list[str] = []
    for feld, needle in (("FROM", from_filter), ("SUBJECT", subject_filter)):
        if needle:
            teile += [feld, f'"{needle}"']
    if to_filter:
        teile += ["OR", "TO", f'"{to_filter}"', "CC", f'"{to_filter}"']
    if not teile:
        return None
    if not all(t.isascii() for t in teile):
        return None
    return teile


def _kandidaten(
    imap: imaplib.IMAP4_SSL, kriterien: list[str] | None
) -> tuple[list[bytes], bool]:
    """(zu prüfende IDs, server_vorgefiltert). Bei jedem Zweifel: alle IDs.

    Das Ergebnis ist ein **Vorschlag**, kein Treffer: Der Aufrufer prüft jede ID
    lokal gegen dieselben Matcher. Nötig, weil Exchange über den Header hinaus
    sucht — gemessen am 2026-07-28 im Ordner 'Kalender': ``TO "offner"`` lieferte
    6 IDs, ``CC "offner"`` eine weitere, und **keine** dieser 7 trug den Namen in
    einem Header. Ohne Gegenprobe wären das 7 erfundene Treffer gewesen.
    """
    if kriterien:
        try:
            typ, data = imap.search(None, *kriterien)
            if typ == "OK":
                return (data[0].split() if data and data[0] else []), True
        except (imaplib.IMAP4.error, UnicodeEncodeError):
            pass  # Server mag das Kriterium nicht -> voller Scan, nicht "0 Treffer"
    typ, data = imap.search(None, "ALL")
    return (data[0].split() if data and data[0] else []), False


class Treffer(NamedTuple):
    ordner: str
    nummer: str
    datum: str
    von: str
    an: str
    betreff: str


class Ergebnis(NamedTuple):
    """Was ein Lauf gefunden hat — **und** worüber er gelaufen ist.

    Beides in einem Objekt, weil die Trennung genau die Fehlerquelle ist: eine
    Trefferliste ohne ihren Nenner sieht aus wie eine Vollerhebung. Renderer
    (Text/JSON) bekommen deshalb nie nur ``treffer``.
    """

    treffer: tuple[Treffer, ...]
    konto: str
    filter: dict[str, str | None]
    limit: int
    gesamt_ordner: int
    geprueft_ordner: int
    nachrichten_gesehen: int
    nachrichten_vorhanden: int
    vorgefiltert: bool
    ausgeschlossen: tuple[tuple[str, str], ...] = ()
    fehler: tuple[tuple[str, str], ...] = ()
    unlesbar: tuple[str, ...] = ()
    einzelordner: str | None = None


def sammle_alle_ordner(
    imap: imaplib.IMAP4_SSL,
    neu_verbinden,
    count: int,
    from_filter: str | None,
    to_filter: str | None,
    subject_filter: str | None,
    auch_ausgeschlossen: bool = False,
    konto: str = "",
    gruendlich: bool = False,
) -> tuple[Ergebnis, imaplib.IMAP4_SSL]:
    """Alle Ordner durchsuchen statt nur INBOX — der Fall 'wo liegt die Mail von X?'.

    Ohne das musste man den Ordner vorher kennen; genau daran ist am 2026-07-28
    eine Suche gescheitert, die erst nach einem Dutzend Anläufen im richtigen
    Postfach ankam. Gibt neben dem Ergebnis die (ggf. neu aufgebaute) Verbindung
    zurück — der Aufrufer kann sie sonst nicht mehr schließen.

    ``gruendlich`` schaltet den server-seitigen Vorfilter ab: langsamer, aber ohne
    die Annahme, dass die SEARCH-Semantik des Servers der eigenen entspricht.
    """
    ordner, unlesbar = alle_ordner(imap)
    if auch_ausgeschlossen:
        zu_pruefen, ausgeschlossen = ordner, []
    else:
        zu_pruefen, ausgeschlossen = aufteilen(ordner)

    kriterien = (
        None if gruendlich else _such_kriterien(from_filter, to_filter, subject_filter)
    )
    treffer: list[Treffer] = []
    fehler: list[tuple[str, str]] = []
    geprueft = 0
    vorgefiltert = False
    nachrichten = 0

    for name in zu_pruefen:
        for versuch in (1, 2):
            try:
                typ, _ = imap.select(_mailbox_arg(name), readonly=True)
                if typ != "OK":
                    fehler.append((name, f"SELECT {typ}"))
                    break
                ids, war_vorgefiltert = _kandidaten(imap, kriterien)
                vorgefiltert = vorgefiltert or war_vorgefiltert
                nachrichten += len(ids)
                for i in reversed(ids):
                    typ2, md = imap.fetch(
                        i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])"
                    )
                    if typ2 != "OK" or not md or not md[0]:
                        continue
                    msg = email.message_from_bytes(md[0][1])
                    if not (
                        matches_from(msg, from_filter)
                        and matches_to(msg, to_filter)
                        and matches_subject(msg, subject_filter)
                    ):
                        continue
                    treffer.append(
                        Treffer(
                            ordner=name,
                            nummer=i.decode(),
                            datum=decode_hdr(msg.get("Date")),
                            von=decode_hdr(msg.get("From")),
                            an=decode_hdr(msg.get("To")),
                            betreff=decode_hdr(msg.get("Subject")),
                        )
                    )
                    if len(treffer) >= count:
                        break
                geprueft += 1
                break
            except (imaplib.IMAP4.abort, OSError) as e:
                # Lange Läufe verlieren die Verbindung (Exchange kappt Idle-Sockets).
                if versuch == 1 and neu_verbinden is not None:
                    try:
                        imap = neu_verbinden()
                        continue
                    except Exception as e2:  # noqa: BLE001
                        fehler.append((name, f"Neuverbindung: {e2}"))
                        break
                fehler.append((name, str(e)[:80]))
        if len(treffer) >= count:
            break

    return (
        Ergebnis(
            treffer=tuple(treffer),
            konto=konto,
            filter={
                "von": from_filter,
                "an": to_filter,
                "betreff": subject_filter,
            },
            limit=count,
            gesamt_ordner=len(ordner),
            geprueft_ordner=geprueft,
            nachrichten_gesehen=nachrichten,
            nachrichten_vorhanden=0,
            vorgefiltert=vorgefiltert,
            ausgeschlossen=tuple(ausgeschlossen),
            fehler=tuple(fehler),
            unlesbar=tuple(unlesbar),
        ),
        imap,
    )


def rendern_text(erg: Ergebnis) -> str:
    """Bilanz ZUERST, Trefferliste danach.

    Andersherum scrollt bei 27 ausgeschlossenen Ordnern der Beweis aus dem
    Terminal, und man liest die Liste ohne ihren Nenner (Realfall 2026-07-28:
    ``tail`` zeigte die Bilanz und verschluckte dabei den einzigen Treffer).
    """
    if erg.einzelordner is not None:
        bilanz = _bilanz(
            erg.einzelordner,
            erg.nachrichten_vorhanden,
            erg.nachrichten_gesehen,
            len(erg.treffer),
            erg.limit,
            erg.filter.get("von"),
            erg.filter.get("an"),
            erg.filter.get("betreff"),
        )
    else:
        bilanz = _bilanz_alle(
            gesamt_ordner=erg.gesamt_ordner,
            geprueft=erg.geprueft_ordner,
            gezeigt=len(erg.treffer),
            limit=erg.limit,
            nachrichten=erg.nachrichten_gesehen,
            vorgefiltert=erg.vorgefiltert,
            ausgeschlossen=list(erg.ausgeschlossen),
            fehler=list(erg.fehler),
            unlesbar=list(erg.unlesbar),
        )

    zeilen = [bilanz]
    if erg.treffer:
        zeilen.append("")
    for t in erg.treffer:
        if erg.einzelordner is not None:
            zeilen.append(
                f"#{t.nummer:>5}  {t.datum[:22]:<22}  {t.von[:38]:<38}  {t.betreff[:60]}"
            )
        else:
            zeilen.append(
                f"[{t.ordner}] #{t.nummer}  {t.datum[:22]}\n"
                f"    VON {t.von[:70]}\n"
                f"    AN  {t.an[:70]}\n"
                f"    BET {t.betreff[:70]}"
            )
    return "\n".join(zeilen)


def rendern_json(erg: Ergebnis) -> str:
    """Maschinenlesbar, damit niemand Treffer mit ``grep -c`` auf Fließtext zählt.

    Genau dabei entstand am 2026-07-28 eine falsche Trefferzahl (28 statt 21).
    """
    return json.dumps(
        {
            "konto": erg.konto,
            "filter": erg.filter,
            "limit": erg.limit,
            "bilanz": {
                "ordner_gesamt": erg.gesamt_ordner,
                "ordner_geprueft": erg.geprueft_ordner,
                "einzelordner": erg.einzelordner,
                "nachrichten_gesehen": erg.nachrichten_gesehen,
                "nachrichten_vorhanden": erg.nachrichten_vorhanden,
                "server_vorgefiltert": erg.vorgefiltert,
                "limit_erreicht": len(erg.treffer) >= erg.limit,
                "ausgeschlossen": [
                    {"ordner": o, "grund": g} for o, g in erg.ausgeschlossen
                ],
                "fehler": [{"ordner": o, "grund": g} for o, g in erg.fehler],
                "unlesbare_list_zeilen": list(erg.unlesbar),
            },
            "treffer": [t._asdict() for t in erg.treffer],
        },
        ensure_ascii=False,
        indent=2,
    )


def _bilanz_alle(
    *,
    gesamt_ordner: int,
    geprueft: int,
    gezeigt: int,
    limit: int,
    nachrichten: int,
    vorgefiltert: bool,
    ausgeschlossen: list[tuple[str, str]],
    fehler: list[tuple[str, str]],
    unlesbar: list[str],
) -> str:
    """Nenner des Ordner-Laufs — dieselbe Pflicht wie in ``_bilanz``, eine Ebene höher.

    Der Nenner ist die **volle** Ordnerzahl, nicht die um Ausschlüsse reduzierte
    (indexierung.py: Ausschluss verkleinert die Grundgesamtheit sichtbar, nicht still).
    """
    if gezeigt == 0:
        kopf = "keine Treffer\n"
    else:
        kopf = ""
    zeilen = [
        f"{kopf}— {gezeigt} Treffer · {geprueft} von {gesamt_ordner} Ordner(n) geprüft"
        + (f" · {nachrichten} Nachricht(en) angesehen" if not vorgefiltert else "")
    ]
    if vorgefiltert:
        zeilen.append(
            "  Server-seitig vorgefiltert (IMAP SEARCH), Treffer zusätzlich lokal "
            "gegengeprüft — deckungsgleich kalibriert für ASCII-Suchbegriffe."
        )
    if gezeigt >= limit and geprueft < gesamt_ordner:
        zeilen.append(
            f"⚠ Limit {limit} erreicht — {gesamt_ordner - geprueft} Ordner wurden gar "
            f"nicht erst angesehen. KEINE Vollerhebung; --list höher setzen."
        )
    if ausgeschlossen:
        zeilen.append(
            f"  {len(ausgeschlossen)} Ordner bewusst ausgeschlossen "
            f"(--auch-ausgeschlossen hebt das auf):"
        )
        zeilen += [f"    - {o}  →  {grund}" for o, grund in ausgeschlossen]
    if fehler:
        zeilen.append(
            f"⚠ {len(fehler)} Ordner NICHT geprüft — Ergebnis ist unvollständig:"
        )
        zeilen += [f"    - {o}: {grund}" for o, grund in fehler]
    if unlesbar:
        zeilen.append(
            f"⚠ {len(unlesbar)} unparsbare LIST-Zeile(n) — Ordner evtl. übersehen:"
        )
        zeilen += [f"    - {z}" for z in unlesbar]
    return "\n".join(zeilen)


def _bilanz(
    folder: str,
    gesamt: int,
    geprueft: int,
    gezeigt: int,
    limit: int,
    from_filter: str | None,
    to_filter: str | None,
    subject_filter: str | None = None,
) -> str:
    """Nenner sichtbar machen: eine Liste ohne Gesamtzahl sieht vollständig aus.

    Ohne diese Zeile ist `--list 25` von einer Vollerhebung nicht zu
    unterscheiden — man zählt die Zeilen und hält das Ergebnis für den Bestand.
    Genau dieser Trugschluss hat am 2026-07-27 einen falschen Befund erzeugt
    (platform#1480, dort die Graph-Variante desselben Musters).
    """
    filter_teile = []
    if from_filter:
        filter_teile.append(f"Absender~{from_filter!r}")
    if to_filter:
        filter_teile.append(f"Empfänger~{to_filter!r}")
    if subject_filter:
        filter_teile.append(f"Betreff~{subject_filter!r}")
    filter_txt = " UND ".join(filter_teile) if filter_teile else "kein Filter"

    zeile = (
        f"— {gezeigt} gezeigt · {geprueft} von {gesamt} Nachricht(en) in "
        f"'{folder}' geprüft · {filter_txt}"
    )
    if gezeigt >= limit and geprueft < gesamt:
        zeile += (
            f"\n⚠ Limit {limit} erreicht — {gesamt - geprueft} Nachricht(en) wurden "
            f"gar nicht erst angesehen. Diese Liste ist KEINE Vollerhebung; "
            f"--list höher setzen."
        )
    elif filter_teile and geprueft > gezeigt:
        zeile += (
            f"\n  ({geprueft - gezeigt} Nachricht(en) passten nicht auf den Filter — "
            f"für den Gesamtbestand ohne --from/--to-filter aufrufen.)"
        )
    return zeile


def sammle_einzelordner(
    imap: imaplib.IMAP4_SSL,
    folder: str,
    count: int,
    from_filter: str | None,
    to_filter: str | None = None,
    subject_filter: str | None = None,
    konto: str = "",
) -> Ergebnis:
    imap.select(_mailbox_arg(folder), readonly=True)
    typ, data = imap.search(None, "ALL")
    ids = data[0].split()
    gesamt = len(ids)
    treffer: list[Treffer] = []
    geprueft = 0
    for i in reversed(ids):
        geprueft += 1
        typ, md = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])")
        msg = email.message_from_bytes(md[0][1])
        if not (
            matches_from(msg, from_filter)
            and matches_to(msg, to_filter)
            and matches_subject(msg, subject_filter)
        ):
            continue
        treffer.append(
            Treffer(
                ordner=folder,
                nummer=i.decode(),
                datum=decode_hdr(msg.get("Date")),
                von=decode_hdr(msg.get("From")),
                an=decode_hdr(msg.get("To")),
                betreff=decode_hdr(msg.get("Subject")),
            )
        )
        if len(treffer) >= count:
            break
    return Ergebnis(
        treffer=tuple(treffer),
        konto=konto,
        filter={"von": from_filter, "an": to_filter, "betreff": subject_filter},
        limit=count,
        gesamt_ordner=1,
        geprueft_ordner=1,
        nachrichten_gesehen=geprueft,
        nachrichten_vorhanden=gesamt,
        vorgefiltert=False,
        einzelordner=folder,
    )


PFLICHT_KEYS = ("SMTP_HOST", "MAIL_FROM", "MAIL_CREDS_FILE")


def imap_konten() -> list[tuple[str, Path]]:
    """Alle IMAP-Konten dieser Maschine als (Kürzel, Config-Pfad).

    Erkannt wird an den Pflicht-Keys, nicht am Dateinamen: ``mail-folders.env``
    liegt im selben Verzeichnis, ist aber eine Ordner-Zuordnung und kein Konto.
    """
    gefunden: list[tuple[str, Path]] = []
    basis = CONFIG_FILE.parent
    kandidaten = sorted(basis.glob("mail-*.env"))
    if CONFIG_FILE.exists():
        kandidaten.insert(0, CONFIG_FILE)
    for pfad in kandidaten:
        try:
            cfg = parse_env(pfad)
        except OSError:
            continue
        if not all(k in cfg for k in PFLICHT_KEYS):
            continue
        kuerzel = (
            "default"
            if pfad == CONFIG_FILE
            else pfad.name.removeprefix("mail-").removesuffix(".env")
        )
        gefunden.append((kuerzel, pfad))
    return gefunden


def nicht_erreichbare_konten() -> list[tuple[str, str]]:
    """Postfächer, die dieses Werkzeug bauartbedingt NICHT abdeckt.

    Das IIL-Geschäftspostfach hängt an Microsoft Graph, nicht an IMAP. Ohne
    diesen Eintrag zählte ein Abwesenheitsbeweis nur die IMAP-Konten und sähe
    trotzdem vollständig aus — genau die stille Lücke, gegen die der Ausweis
    geschrieben ist.
    """
    token_dir = Path.home() / ".claude" / "graph-mail-tokens"
    return [
        (
            f"Konto {p.stem.replace('_at_', '@')}",
            "Graph-Transport, nicht über IMAP erreichbar — separat mit "
            "graph_mail.py --find prüfen",
        )
        for p in sorted(token_dir.glob("*.json"))
    ]


#: Stichprobengröße der Kalibriersonde. Groß genug für eine Aussage, klein genug,
#: um den Beweislauf nicht um Minuten zu verlängern.
SONDE_TIEFE = 50


def gesendet_ordner(imap: imaplib.IMAP4_SSL) -> str:
    """Name des \\Sent-Ordners laut LIST-Flags — nicht am Namen geraten.

    Die Ordner heißen je nach Server 'Gesendete Objekte', 'Sent', 'INBOX.Sent';
    das Flag ist die einzige verlässliche Auskunft.
    """
    typ, data = imap.list()
    for zeile in data or []:
        roh = zeile if isinstance(zeile, bytes) else str(zeile).encode()
        m = _LIST_RE.match(roh)
        if m and b"\\Sent" in m.group("flags"):
            return m.group("name").decode("utf-8", "replace").strip().strip('"')
    return ""


def kalibrierungssonde(
    imap: imaplib.IMAP4_SSL, eigene_adresse: str
) -> tuple[bool, str]:
    """Prüft den **tatsächlich genutzten** Pfad an einer Menge mit bekannter Antwort.

    KONZ-035 §5.3 R-3 verlangt genau das für jeden Retrievalpfad. Als bekannte
    Menge dient der Gesendet-Ordner: dort trägt per Konstruktion jede Nachricht
    den eigenen Absender.

    Geprüft wird nicht „findet der Server irgendetwas", sondern die Eigenschaft,
    auf die es ankommt: **verschweigt der server-seitige Vorfilter etwas, das der
    lokale Scan sieht?** Falsch-positive Server-Treffer sind harmlos (die lokale
    Gegenprobe wirft sie weg), falsch-negative wären der stille Beweisfehler.
    Deshalb ist das Kriterium ``client ⊆ server``, nicht Gleichheit.
    """
    gesendet = gesendet_ordner(imap)
    if not gesendet:
        return False, "kein \\Sent-Ordner im LIST — Sonde nicht durchführbar"
    try:
        typ, _ = imap.select(_mailbox_arg(gesendet), readonly=True)
        if typ != "OK":
            return False, f"{gesendet}: SELECT {typ}"
        typ, data = imap.search(None, "ALL")
        stichprobe = (data[0].split() if data and data[0] else [])[-SONDE_TIEFE:]
        if not stichprobe:
            return False, f"{gesendet}: leer — keine bekannte Menge zum Prüfen"

        client = set()
        for i in stichprobe:
            typ2, md = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
            if typ2 != "OK" or not md or not md[0]:
                continue
            if matches_from(email.message_from_bytes(md[0][1]), eigene_adresse):
                client.add(i)
        if not client:
            return (
                False,
                f"{gesendet}: eigener Absender in {len(stichprobe)} nicht gefunden",
            )

        kriterien = _such_kriterien(eigene_adresse, None, None)
        if kriterien is None:
            return True, f"{gesendet}: {len(client)}/{len(stichprobe)}, ohne Vorfilter"
        server, _ = _kandidaten(imap, kriterien)
        verfehlt = client - set(server)
        if verfehlt:
            return False, (
                f"{gesendet}: Vorfilter verschweigt {len(verfehlt)} von {len(client)} "
                "bekannten Nachrichten"
            )
        return (
            True,
            f"{gesendet}: Vorfilter deckt {len(client)}/{len(client)} bekannte ab",
        )
    except (imaplib.IMAP4.error, OSError) as e:
        return False, f"{gesendet}: {str(e)[:60]}"


def abwesenheitsbeweis(
    from_filter: str | None,
    to_filter: str | None,
    subject_filter: str | None,
    anlass: str,
    gruendlich: bool = False,
) -> tuple[list[Ergebnis], da.Ausweis]:
    """Der Modus für Allaussagen: „es gibt keine Mail von X".

    Anwesenheit belegt ein einzelner Treffer. Abwesenheit ist eine Aussage über
    **jeden** Ordner **jedes** Kontos — und die kippt still, sobald ein Ordner
    ausgelassen, ein Konto vergessen oder ein Vorfilter zu scharf war. Deshalb
    erzwingt dieser Modus alle Konten und alle Ordner (auch Papierkorb und
    Jahresarchive) und liefert als Ergebnis den Deckungsausweis.

    Den server-seitigen Vorfilter schaltet er **nicht** blind ab, sondern belegt
    ihn: pro Konto läuft vorher :func:`kalibrierungssonde` gegen eine Menge mit
    bekannter Antwort. Besteht sie nicht, wandert das Konto als ungedeckt in den
    Ausweis, statt ein Ergebnis vorzutäuschen. Ein erzwungener Vollscan
    (``gruendlich=True``) ist möglich, dauert über alle Jahresarchive aber
    Größenordnungen länger — deshalb nicht der Default.
    """
    start = datetime.now(timezone.utc).isoformat(timespec="seconds")
    konten = imap_konten()
    nicht_gedeckt = list(nicht_erreichbare_konten())
    ergebnisse: list[Ergebnis] = []
    kalibriert: list[str] = []
    ordner_vorhanden = ordner_durchsucht = 0
    nachrichten = 0
    fehlgeschlagen = 0
    durchsucht = 0

    for kuerzel, pfad in konten:
        cfg = parse_env(pfad)
        try:
            imap = connect(cfg)
        except Exception as e:  # noqa: BLE001
            nicht_gedeckt.append((f"Konto {kuerzel}", f"Verbindung: {str(e)[:60]}"))
            continue
        try:
            ok, wie = kalibrierungssonde(imap, cfg["MAIL_FROM"])
            pfadname = f"imap-headerscan/{kuerzel}"
            if ok:
                kalibriert.append(pfadname)
            else:
                nicht_gedeckt.append((f"Kalibrierung {kuerzel}", wie))
            erg, imap = sammle_alle_ordner(
                imap,
                lambda c=cfg: connect(c),
                count=10_000,
                from_filter=from_filter,
                to_filter=to_filter,
                subject_filter=subject_filter,
                auch_ausgeschlossen=True,
                konto=kuerzel,
                # Sonde nicht bestanden -> der Vorfilter ist für dieses Konto
                # unbelegt, also nicht benutzt. Lieber langsam als unbelegt.
                gruendlich=gruendlich or not ok,
            )
            ergebnisse.append(erg)
            durchsucht += 1
            ordner_vorhanden += erg.gesamt_ordner
            ordner_durchsucht += erg.geprueft_ordner
            nachrichten += erg.nachrichten_gesehen
            fehlgeschlagen += len(erg.fehler)
            nicht_gedeckt += [(f"{kuerzel}:{o}", g) for o, g in erg.fehler]
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

    ende = datetime.now(timezone.utc).isoformat(timespec="seconds")
    frage = ", ".join(
        f"{feld}~{wert!r}"
        for feld, wert in (
            ("Absender", from_filter),
            ("Empfänger", to_filter),
            ("Betreff", subject_filter),
        )
        if wert
    )
    ausweis = da.Ausweis(
        frage=frage or "(kein Filter)",
        anlass=anlass,
        konten_vorhanden=len(konten) + len(nicht_erreichbare_konten()),
        konten_durchsucht=durchsucht,
        ordner_vorhanden=ordner_vorhanden,
        ordner_durchsucht=ordner_durchsucht,
        scan_started_at=start,
        scan_finished_at=ende,
        source_watermark=start,
        retrievalpfade=tuple(
            (f"imap-headerscan/{e.konto}", len(e.treffer)) for e in ergebnisse
        ),
        kalibriert=tuple(kalibriert),
        ordner_fehlgeschlagen=fehlgeschlagen,
        geprueft=nachrichten,
        vorhanden=nachrichten,
        nicht_gedeckt=tuple(nicht_gedeckt),
        query_fingerprint=da.fingerprint(from_filter, to_filter, subject_filter),
        tool_version=WERKZEUG,
    )
    return ergebnisse, ausweis


def cmd_fetch(
    imap: imaplib.IMAP4_SSL,
    folder: str,
    which: str,
    from_filter: str | None,
    save_dir: str | None,
    max_chars: int,
    to_filter: str | None = None,
) -> None:
    imap.select(_mailbox_arg(folder), readonly=True)
    typ, data = imap.search(None, "ALL")
    ids = data[0].split()
    target_id = None
    if which == "latest":
        for i in reversed(ids):
            typ, md = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC)])")
            hmsg = email.message_from_bytes(md[0][1])
            if matches_from(hmsg, from_filter) and matches_to(hmsg, to_filter):
                target_id = i
                break
    else:
        target_id = which.encode()
    if target_id is None:
        sys.exit("FEHLER: keine passende Mail gefunden")
    typ, md = imap.fetch(target_id, "(BODY.PEEK[])")
    msg = email.message_from_bytes(md[0][1])
    print(f"From:    {decode_hdr(msg.get('From'))}")
    print(f"Date:    {decode_hdr(msg.get('Date'))}")
    print(f"Subject: {decode_hdr(msg.get('Subject'))}")
    atts = attachment_names(msg)
    print(f"Anhänge: {', '.join(atts) if atts else 'keine'}")
    print("--- Body ---")
    print(extract_text(msg, max_chars=max_chars))
    if save_dir:
        for name, size in save_attachments(msg, Path(save_dir).expanduser()):
            print(f"Anhang gespeichert: {name} ({size} Bytes)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Zweitnamen = die Flags von graph_mail.py. Beide Werkzeuge beantworten
    # dieselbe Frage; zwei Vokabeln dafür kosteten am 2026-07-28 mehrere
    # Fehlversuche, weil --from hier und --from-filter dort gilt.
    ap.add_argument("--folder", "--source", dest="folder", default="INBOX")
    ap.add_argument(
        "--from-filter",
        "--from",
        dest="from_filter",
        default=None,
        help="Substring-Match auf From-Header (Zweitname: --from wie in graph_mail.py)",
    )
    ap.add_argument(
        "--to-filter",
        "--to",
        dest="to_filter",
        default=None,
        help="Substring-Match auf To+Cc-Header (z.B. Empfänger im Gesendete-Ordner)",
    )
    ap.add_argument(
        "--subject-filter",
        "--subject",
        dest="subject_filter",
        default=None,
        help="Substring-Match auf Subject-Header",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Ergebnis als JSON statt Text — Treffer zählen, ohne Fließtext zu grepen",
    )
    ap.add_argument(
        "--gruendlich",
        action="store_true",
        help="server-seitigen SEARCH-Vorfilter abschalten (langsamer, aber ohne "
        "Annahme über die SEARCH-Semantik des Servers)",
    )
    ap.add_argument(
        "--abwesenheitsbeweis",
        metavar="ANLASS",
        default=None,
        help="Allaussage belegen ('es gibt keine Mail von X'): ALLE Konten, ALLE "
        "Ordner, kein Vorfilter; Ausgabe ist der Deckungsausweis. Exit 1, wenn "
        "die Prüfkette reisst.",
    )
    ap.add_argument(
        "--all-folders",
        action="store_true",
        help="bei --list: ALLE Ordner durchsuchen statt nur --folder "
        "(für 'wo liegt die Mail von X?')",
    )
    ap.add_argument(
        "--auch-ausgeschlossen",
        action="store_true",
        help="bei --all-folders: auch Papierkorb/Junk/Jahresarchive mitnehmen "
        "(Default: ausgeschlossen, aber in der Bilanz ausgewiesen)",
    )
    ap.add_argument(
        "--max-chars", type=int, default=4000, help="Body-Kürzung bei --fetch"
    )
    group = ap.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--list", type=int, metavar="N", help="letzte N Mails listen (neueste zuerst)"
    )
    group.add_argument(
        "--fetch", metavar="NUM|latest", help="eine Mail vollständig lesen"
    )
    ap.add_argument(
        "--save-attachments",
        metavar="DIR",
        default=None,
        help="bei --fetch: Anhänge in DIR speichern",
    )
    ap.add_argument(
        "--config",
        metavar="ENV",
        default=None,
        help="alternative Mail-Config (Default: ~/.claude/mail.env), z.B. ~/.claude/mail-hnu.env",
    )
    ap.add_argument(
        "--account",
        metavar="NAME",
        default=None,
        help="Postfach-Kürzel → ~/.claude/mail-<NAME>.env (z.B. --account hnu). "
        "Guard-sicher: kein .env-Pfad als Argument (Secret-Leak-Guard).",
    )
    args = ap.parse_args()

    if args.abwesenheitsbeweis:
        # Der Modus wählt seine Konten selbst — ein --account waere die
        # Einschraenkung, die der Beweis gerade ausschliessen soll.
        if args.account or args.config:
            sys.exit(
                "FEHLER: --abwesenheitsbeweis laeuft ueber ALLE Konten; "
                "--account/--config widersprechen dem"
            )
        if not (args.from_filter or args.to_filter or args.subject_filter):
            sys.exit("FEHLER: --abwesenheitsbeweis braucht einen Filter")
        ergebnisse, ausweis = abwesenheitsbeweis(
            args.from_filter,
            args.to_filter,
            args.subject_filter,
            args.abwesenheitsbeweis,
            gruendlich=args.gruendlich,
        )
        if args.json:
            print(
                json.dumps(
                    {
                        "ausweis": da.als_dict(ausweis),
                        "konten": [json.loads(rendern_json(e)) for e in ergebnisse],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(da.rendern(ausweis))
            for e in ergebnisse:
                print(f"\n=== Konto {e.konto} ===")
                print(rendern_text(e))
        ok, fehler = da.pruefkette(ausweis)
        if not ok:
            print("\n✗ Pruefkette gerissen:", "; ".join(fehler), file=sys.stderr)
        sys.exit(0 if ok else 1)

    if args.list is None and args.fetch is None:
        sys.exit("FEHLER: --list, --fetch oder --abwesenheitsbeweis waehlen")

    cfg_file = _resolve_config(args.config, args.account)
    if not cfg_file.exists():
        sys.exit(
            f"FEHLER: {cfg_file} fehlt — Maschine ist für Mail nicht freigegeben (Capability-Profil)"
        )
    cfg = parse_env(cfg_file)
    missing = [k for k in ("SMTP_HOST", "MAIL_FROM", "MAIL_CREDS_FILE") if k not in cfg]
    if missing:
        sys.exit(f"FEHLER: Keys fehlen in {cfg_file}: {', '.join(missing)}")

    if args.all_folders and args.list is None:
        sys.exit(
            "FEHLER: --all-folders gilt nur für --list (--fetch braucht einen Ordner)"
        )

    konto = args.account or "default"
    ausgeben = rendern_json if args.json else rendern_text

    if args.all_folders:
        # Kein `with`: der Lauf kann die Verbindung unterwegs ersetzen (Exchange kappt
        # lange Sitzungen), und ein logout() auf dem toten Socket würde die Bilanz
        # hinter einem Traceback verschwinden lassen.
        imap = connect(cfg)
        try:
            erg, imap = sammle_alle_ordner(
                imap,
                lambda: connect(cfg),
                args.list,
                args.from_filter,
                args.to_filter,
                args.subject_filter,
                args.auch_ausgeschlossen,
                konto=konto,
                gruendlich=args.gruendlich,
            )
            print(ausgeben(erg))
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass
        return

    with connect(cfg) as imap:
        if args.list is not None:
            print(
                ausgeben(
                    sammle_einzelordner(
                        imap,
                        args.folder,
                        args.list,
                        args.from_filter,
                        args.to_filter,
                        args.subject_filter,
                        konto=konto,
                    )
                )
            )
        else:
            cmd_fetch(
                imap,
                args.folder,
                args.fetch,
                args.from_filter,
                args.save_attachments,
                args.max_chars,
                args.to_filter,
            )


if __name__ == "__main__":
    main()
