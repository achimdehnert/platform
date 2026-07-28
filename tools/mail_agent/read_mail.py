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
import re
import sys
from email.header import decode_header
from email.message import Message
from pathlib import Path

# Config-/Credentials-Parsing wird aus send_mail wiederverwendet (eine SSoT).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from indexierung import aufteilen  # noqa: E402
from send_mail import CONFIG_FILE, load_credentials, parse_env  # noqa: E402


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


def cmd_list_alle(
    imap: imaplib.IMAP4_SSL,
    neu_verbinden,
    count: int,
    from_filter: str | None,
    to_filter: str | None,
    subject_filter: str | None,
    auch_ausgeschlossen: bool = False,
) -> imaplib.IMAP4_SSL:
    """Alle Ordner durchsuchen statt nur INBOX — der Fall 'wo liegt die Mail von X?'.

    Ohne das musste man den Ordner vorher kennen; genau daran ist am 2026-07-28
    eine Suche gescheitert, die erst nach einem Dutzend Anläufen im richtigen
    Postfach ankam. Rückgabewert ist die (ggf. neu aufgebaute) Verbindung.
    """
    ordner, unlesbar = alle_ordner(imap)
    if auch_ausgeschlossen:
        zu_pruefen, ausgeschlossen = ordner, []
    else:
        zu_pruefen, ausgeschlossen = aufteilen(ordner)

    kriterien = _such_kriterien(from_filter, to_filter, subject_filter)
    gezeigt = 0
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
                    print(
                        f"[{name}] #{i.decode()}  {decode_hdr(msg.get('Date'))[:22]}\n"
                        f"    VON {decode_hdr(msg.get('From'))[:70]}\n"
                        f"    AN  {decode_hdr(msg.get('To'))[:70]}\n"
                        f"    BET {decode_hdr(msg.get('Subject'))[:70]}"
                    )
                    gezeigt += 1
                    if gezeigt >= count:
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
        if gezeigt >= count:
            break

    print(
        _bilanz_alle(
            gesamt_ordner=len(ordner),
            geprueft=geprueft,
            gezeigt=gezeigt,
            limit=count,
            nachrichten=nachrichten,
            vorgefiltert=vorgefiltert,
            ausgeschlossen=ausgeschlossen,
            fehler=fehler,
            unlesbar=unlesbar,
        )
    )
    return imap


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


def cmd_list(
    imap: imaplib.IMAP4_SSL,
    folder: str,
    count: int,
    from_filter: str | None,
    to_filter: str | None = None,
    subject_filter: str | None = None,
) -> None:
    imap.select(_mailbox_arg(folder), readonly=True)
    typ, data = imap.search(None, "ALL")
    ids = data[0].split()
    gesamt = len(ids)
    shown = 0
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
        print(
            f"#{i.decode():>5}  {decode_hdr(msg.get('Date'))[:22]:<22}  "
            f"{decode_hdr(msg.get('From'))[:38]:<38}  {decode_hdr(msg.get('Subject'))[:60]}"
        )
        shown += 1
        if shown >= count:
            break
    if shown == 0:
        print("keine Treffer")
    print(
        _bilanz(
            folder,
            gesamt,
            geprueft,
            shown,
            count,
            from_filter,
            to_filter,
            subject_filter,
        )
    )


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
    ap.add_argument("--folder", default="INBOX")
    ap.add_argument(
        "--from-filter", default=None, help="Substring-Match auf From-Header"
    )
    ap.add_argument(
        "--to-filter",
        default=None,
        help="Substring-Match auf To+Cc-Header (z.B. Empfänger im Gesendete-Ordner)",
    )
    ap.add_argument(
        "--subject-filter", default=None, help="Substring-Match auf Subject-Header"
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
    group = ap.add_mutually_exclusive_group(required=True)
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

    if args.all_folders:
        # Kein `with`: der Lauf kann die Verbindung unterwegs ersetzen (Exchange kappt
        # lange Sitzungen), und ein logout() auf dem toten Socket würde die Bilanz
        # hinter einem Traceback verschwinden lassen.
        imap = connect(cfg)
        try:
            imap = cmd_list_alle(
                imap,
                lambda: connect(cfg),
                args.list,
                args.from_filter,
                args.to_filter,
                args.subject_filter,
                args.auch_ausgeschlossen,
            )
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass
        return

    with connect(cfg) as imap:
        if args.list is not None:
            cmd_list(
                imap,
                args.folder,
                args.list,
                args.from_filter,
                args.to_filter,
                args.subject_filter,
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
