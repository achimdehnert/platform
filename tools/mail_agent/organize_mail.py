#!/usr/bin/env python3
"""Postfach aufräumen über IMAP — Mails VERSCHIEBEN und Ordner anlegen (Konsument: /organize-mail).

Owner-Entscheid 2026-07-18 (Lotsen-Charta Capability-Erweiterung, als solche gekennzeichnet).
BEWUSST getrennt von read_mail.py, damit dessen strikte Read-Only-Garantie unberührt bleibt.

Sicherheits-Design (KONZ-025):
- KEIN hartes Löschen. Die einzige „Lösch"-Aktion ist Verschieben in den Papierkorb — reversibel.
- Verschieben bevorzugt IMAP UID MOVE (atomar); Fallback COPY + \\Deleted + gezieltes UID EXPUNGE
  (nur die betroffenen UIDs, via UIDPLUS) — NIE ein ordner-weites EXPUNGE.
- Bestätigungs-Anzeige vor jedem Zug (welche Mails, wohin); ohne --yes interaktive Rückfrage.
- Maschinen-Gate: läuft nur mit ~/.claude/mail.env (Capability-Profil). Credentials nie nach stdout.

Kommandos:
  --list-folders
  --create-folder "INBOX.Studenten"
  --move --from "antonela" --to "INBOX.Trash" [--source INBOX] [--subject "..."] [--yes]
  --to-trash --from "antonela"                # Kurzform: in den Papierkorb
  --flag   --from "antonela" [--subject "..."] [--source INBOX] [--yes]   # \\Flagged setzen
  --unflag --from "antonela" [--subject "..."] [--yes]                    # \\Flagged entfernen

Hinweis: Eine echte Wichtigkeitsstufe (hoch/normal/niedrig) ist über IMAP nachträglich
NICHT setzbar — sie steckt in Kopfzeilen des Absenders. \\Flagged (das „Fähnchen" in
Outlook/Thunderbird) ist die IMAP-Entsprechung der Nachverfolgung. Wer echte Importance
braucht, nutzt das M365-Postfach über graph_mail.py --importance.
"""

from __future__ import annotations

import argparse
import email
import imaplib
import re
import sys
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from send_mail import CONFIG_FILE, load_credentials, parse_env  # noqa: E402

TRASH_CANDIDATES = (
    "INBOX.Trash",
    "Trash",
    "INBOX.Papierkorb",
    "Deleted Items",
    # Deutsches Exchange/M365 — sowohl Klartext als auch die Form, in der der
    # Server sie über LIST meldet (IMAP modified UTF-7, RFC 3501 §5.1.3).
    "Gelöschte Objekte",
    "Gel&APY-schte Objekte",
)
# Marker für die Heuristik, wenn kein Kandidat exakt passt. "schte objekte" trifft
# absichtlich BEIDE Schreibweisen von "Gelöschte Objekte" (Klartext + UTF-7),
# ohne dass dafür ein UTF-7-Decoder nötig wäre.
_TRASH_MARKERS = ("trash", "papierkorb", "deleted", "schte objekte")
# LIST-Zeile: (flags) "delim" name — name nur gequotet bei Sonderzeichen (RFC 3501 §7.2.2).
_LIST_LINE_RE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$')


def _decode(v: str | None) -> str:
    if not v:
        return ""
    out = []
    for chunk, cs in decode_header(v):
        out.append(
            chunk.decode(cs or "utf-8", errors="replace")
            if isinstance(chunk, bytes)
            else chunk
        )
    return "".join(out).replace("\n", " ").replace("\r", "").strip()


def connect(config_file: Path | None = None) -> tuple[imaplib.IMAP4_SSL, dict]:
    cfg_file = config_file or CONFIG_FILE
    if not cfg_file.exists():
        sys.exit(
            f"FEHLER: {cfg_file} fehlt — Maschine ist für Mail nicht freigegeben (Capability-Profil)"
        )
    cfg = parse_env(cfg_file)
    for k in ("SMTP_HOST", "MAIL_FROM", "MAIL_CREDS_FILE"):
        if k not in cfg:
            sys.exit(f"FEHLER: {k} fehlt in {cfg_file}")
    user, password = load_credentials(
        Path(cfg["MAIL_CREDS_FILE"]).expanduser(), cfg["MAIL_FROM"]
    )
    host = cfg.get("IMAP_HOST", cfg["SMTP_HOST"])
    port = int(cfg.get("IMAP_PORT", "993"))
    imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    imap.login(user, password)
    return imap, cfg


def list_folders(imap: imaplib.IMAP4_SSL) -> list[str]:
    typ, data = imap.list()
    names = []
    if typ == "OK":
        for entry in data:
            if not entry:
                continue
            m = _LIST_LINE_RE.match(entry.decode(errors="replace"))
            if m:
                names.append(m.group("name").strip().strip('"'))
    return names


def _mailbox_arg(folder: str) -> str:
    """Ordnernamen mit Leerzeichen für IMAP quoten (z.B. 'Gesendete Objekte').
    imaplib quotet nicht selbst — ein unquoted Name mit Space bricht SELECT und
    lässt UID MOVE/COPY mit 'BAD Command Argument Error' scheitern.
    Identisch zu read_mail._mailbox_arg (dort seit jeher vorhanden)."""
    if " " in folder and not (folder.startswith('"') and folder.endswith('"')):
        return f'"{folder}"'
    return folder


def resolve_trash(imap: imaplib.IMAP4_SSL) -> str | None:
    names = list_folders(imap)
    for c in TRASH_CANDIDATES:
        if c in names:
            return c
    for n in names:
        if any(m in n.lower() for m in _TRASH_MARKERS):
            return n
    return None


def cmd_list_folders(imap: imaplib.IMAP4_SSL) -> None:
    for n in list_folders(imap):
        print(n)


def cmd_create_folder(imap: imaplib.IMAP4_SSL, name: str) -> None:
    if name in list_folders(imap):
        print(f"Ordner '{name}' existiert bereits — nichts zu tun.")
        return
    typ, resp = imap.create(name)
    if typ != "OK":
        sys.exit(f"FEHLER: Ordner anlegen fehlgeschlagen: {resp}")
    imap.subscribe(name)
    print(f"OK: Ordner '{name}' angelegt.")


def _matches(
    imap: imaplib.IMAP4_SSL, source: str, from_sub: str | None, subj_sub: str | None
):
    # WICHTIG: UID-basiert suchen UND holen, damit die zurückgegebenen IDs echte
    # UIDs sind — _move() verschiebt mit UID MOVE. Sequenz-Nummern (imap.search/
    # imap.fetch) fallen nur bei lückenlosen Postfächern mit UIDs zusammen; auf
    # Exchange traf UID MOVE sonst ins Leere und meldete trotzdem OK (still 0 verschoben).
    imap.select(_mailbox_arg(source), readonly=True)
    typ, data = imap.uid("SEARCH", "ALL")
    if typ != "OK" or not data or not data[0]:
        return []
    all_uids = data[0].split()
    hits = []
    # In Blöcken holen (ein FETCH je Block) — sonst ein Round-Trip je Mail (bei
    # 1000+ Mails > 2 min). UID FETCH liefert je Treffer "<seq> (UID <n> BODY...)".
    for i in range(0, len(all_uids), 500):
        block = all_uids[i : i + 500]
        typ, md = imap.uid(
            "FETCH",
            b",".join(block),
            "(UID BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
        )
        if typ != "OK" or not md:
            continue
        for idx, part in enumerate(md):
            if not isinstance(part, tuple):
                continue
            # UID steht je nach Server in part[0] (Dovecot) ODER im nachfolgenden
            # Separator (Exchange: b" UID 147004)"). Beide Stellen absuchen.
            blob = part[0] or b""
            nxt = md[idx + 1] if idx + 1 < len(md) else b""
            if isinstance(nxt, (bytes, bytearray)):
                blob += nxt
            m = re.search(rb"UID (\d+)", blob)
            if not m:
                continue
            uid = m.group(1)
            msg = email.message_from_bytes(part[1])
            frm, subj = _decode(msg.get("From")), _decode(msg.get("Subject"))
            if from_sub and from_sub.lower() not in frm.lower():
                continue
            if subj_sub and subj_sub.lower() not in subj.lower():
                continue
            hits.append((uid, _decode(msg.get("Date"))[:22], frm[:40], subj[:55]))
    return hits


def _move(imap: imaplib.IMAP4_SSL, source: str, target: str, uids: list[bytes]) -> None:
    imap.select(_mailbox_arg(source))  # read-write
    uid_set = b",".join(uids)
    caps = getattr(imap, "capabilities", ())
    if "MOVE" in caps:
        typ, resp = imap.uid("MOVE", uid_set, _mailbox_arg(target))
        if typ != "OK":
            sys.exit(f"FEHLER: MOVE fehlgeschlagen: {resp}")
        return
    typ, resp = imap.uid("COPY", uid_set, _mailbox_arg(target))
    if typ != "OK":
        sys.exit(f"FEHLER: COPY nach {target} fehlgeschlagen: {resp}")
    imap.uid("STORE", uid_set, "+FLAGS", r"(\Deleted)")
    if "UIDPLUS" in caps:
        imap.uid("EXPUNGE", uid_set)  # nur die betroffenen UIDs
    else:
        print(
            "Hinweis: Server ohne UIDPLUS — Quell-Mails sind als gelöscht MARKIERT und "
            "verschwinden beim nächsten Client-Sync; ordner-weites EXPUNGE wird bewusst NICHT ausgeführt.",
            file=sys.stderr,
        )


def cmd_move(
    imap: imaplib.IMAP4_SSL,
    source: str,
    target: str,
    from_sub: str | None,
    subj_sub: str | None,
    yes: bool,
) -> None:
    if target not in list_folders(imap):
        sys.exit(
            f"FEHLER: Zielordner '{target}' existiert nicht — erst --create-folder \"{target}\"."
        )
    hits = _matches(imap, source, from_sub, subj_sub)
    if not hits:
        print("Keine passenden Mails gefunden — nichts verschoben.")
        return
    krit = (
        " & ".join(
            filter(
                None,
                [
                    f'Absender~"{from_sub}"' if from_sub else None,
                    f'Betreff~"{subj_sub}"' if subj_sub else None,
                ],
            )
        )
        or "ALLE"
    )
    print(
        f"Verschieben aus '{source}' nach '{target}'  (Kriterium: {krit}) — reversibel:"
    )
    for _, date, frm, subj in hits:
        print(f"  · {date:<22} {frm:<40} {subj}")
    print(f"  = {len(hits)} Mail(s)")
    if not yes:
        try:
            if input("Verschieben? [j/N] ").strip().lower() not in (
                "j",
                "ja",
                "y",
                "yes",
            ):
                sys.exit("Abgebrochen — nichts verschoben.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe möglich — abgebrochen.")
    _move(imap, source, target, [u for u, *_ in hits])
    print(
        f"OK: {len(hits)} Mail(s) nach '{target}' verschoben (im Zielordner wiederherstellbar)."
    )


def _set_flagged(
    imap: imaplib.IMAP4_SSL, source: str, uids: list[bytes], add: bool
) -> None:
    """\\Flagged auf den UIDs setzen (+FLAGS) oder entfernen (-FLAGS) — kein EXPUNGE."""
    imap.select(_mailbox_arg(source))  # read-write
    op = "+FLAGS" if add else "-FLAGS"
    typ, resp = imap.uid("STORE", b",".join(uids), op, r"(\Flagged)")
    if typ != "OK":
        sys.exit(f"FEHLER: STORE {op} \\Flagged fehlgeschlagen: {resp}")


def cmd_flag(
    imap: imaplib.IMAP4_SSL,
    source: str,
    from_sub: str | None,
    subj_sub: str | None,
    yes: bool,
    add: bool,
) -> None:
    hits = _matches(imap, source, from_sub, subj_sub)
    if not hits:
        print("Keine passenden Mails gefunden — nichts geändert.")
        return
    krit = (
        " & ".join(
            filter(
                None,
                [
                    f'Absender~"{from_sub}"' if from_sub else None,
                    f'Betreff~"{subj_sub}"' if subj_sub else None,
                ],
            )
        )
        or "ALLE"
    )
    label = (
        "Zur Nachverfolgung markieren (\\Flagged)"
        if add
        else "Nachverfolgungs-Markierung (\\Flagged) entfernen"
    )
    print(f"{label} in '{source}'  (Kriterium: {krit}) — reversibel:")
    for _, date, frm, subj in hits:
        print(f"  · {date:<22} {frm:<40} {subj}")
    print(f"  = {len(hits)} Mail(s)")
    if not yes:
        try:
            if input(f"{label}? [j/N] ").strip().lower() not in (
                "j",
                "ja",
                "y",
                "yes",
            ):
                sys.exit("Abgebrochen — nichts geändert.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe möglich — abgebrochen.")
    _set_flagged(imap, source, [u for u, *_ in hits], add)
    print(f"OK: {len(hits)} Mail(s) — {label}.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list-folders", action="store_true")
    g.add_argument("--create-folder", metavar="NAME")
    g.add_argument("--move", action="store_true", help="Mails nach --to verschieben")
    g.add_argument(
        "--to-trash",
        action="store_true",
        help="Kurzform: passende Mails in den Papierkorb",
    )
    g.add_argument(
        "--flag",
        action="store_true",
        help="passende Mails zur Nachverfolgung markieren (\\Flagged)",
    )
    g.add_argument(
        "--unflag",
        action="store_true",
        help="Nachverfolgungs-Markierung (\\Flagged) wieder entfernen",
    )
    ap.add_argument("--source", default="INBOX", help="Quellordner (Default: INBOX)")
    ap.add_argument("--to", help="Zielordner (bei --move)")
    ap.add_argument("--from", dest="from_sub", help="Absender-Substring")
    ap.add_argument("--subject", dest="subj_sub", help="Betreff-Substring")
    ap.add_argument(
        "--yes", action="store_true", help="ohne Rückfrage (Anzeige-Gate aus)"
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
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    if args.config:
        cfg_file = Path(args.config).expanduser()
    elif args.account:
        cfg_file = Path.home() / ".claude" / f"mail-{args.account}.env"
    else:
        cfg_file = None
    imap, _ = connect(cfg_file)
    try:
        if args.list_folders:
            cmd_list_folders(imap)
        elif args.create_folder:
            cmd_create_folder(imap, args.create_folder)
        elif args.to_trash:
            if not (args.from_sub or args.subj_sub):
                ap.error(
                    "--to-trash braucht --from und/oder --subject (Sicherheit: kein Pauschal-Papierkorb)"
                )
            trash = resolve_trash(imap)
            if not trash:
                sys.exit("FEHLER: kein Papierkorb-Ordner gefunden.")
            cmd_move(imap, args.source, trash, args.from_sub, args.subj_sub, args.yes)
        elif args.flag or args.unflag:
            if not (args.from_sub or args.subj_sub):
                ap.error(
                    "--flag/--unflag braucht --from und/oder --subject (Sicherheit: kein Pauschal-Zug)"
                )
            cmd_flag(
                imap, args.source, args.from_sub, args.subj_sub, args.yes, add=args.flag
            )
        else:  # --move
            if not args.to:
                ap.error("--move braucht --to ZIELORDNER")
            if not (args.from_sub or args.subj_sub):
                ap.error(
                    "--move braucht --from und/oder --subject (Sicherheit: kein Pauschal-Verschieben)"
                )
            cmd_move(imap, args.source, args.to, args.from_sub, args.subj_sub, args.yes)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
