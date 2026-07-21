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
import sys
from email.header import decode_header
from email.message import Message
from pathlib import Path

# Config-/Credentials-Parsing wird aus send_mail wiederverwendet (eine SSoT).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from send_mail import CONFIG_FILE, load_credentials, parse_env  # noqa: E402


def decode_hdr(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
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


def connect(cfg: dict[str, str]) -> imaplib.IMAP4_SSL:
    host = cfg.get("IMAP_HOST", cfg["SMTP_HOST"])
    port = int(cfg.get("IMAP_PORT", "993"))
    user, password = load_credentials(
        Path(cfg["MAIL_CREDS_FILE"]).expanduser(), cfg["MAIL_FROM"]
    )
    imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    imap.login(user, password)
    return imap


def cmd_list(
    imap: imaplib.IMAP4_SSL, folder: str, count: int, from_filter: str | None
) -> None:
    imap.select(folder, readonly=True)
    typ, data = imap.search(None, "ALL")
    ids = data[0].split()
    shown = 0
    for i in reversed(ids):
        typ, md = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        msg = email.message_from_bytes(md[0][1])
        if not matches_from(msg, from_filter):
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


def cmd_fetch(
    imap: imaplib.IMAP4_SSL,
    folder: str,
    which: str,
    from_filter: str | None,
    save_dir: str | None,
    max_chars: int,
) -> None:
    imap.select(folder, readonly=True)
    typ, data = imap.search(None, "ALL")
    ids = data[0].split()
    target_id = None
    if which == "latest":
        for i in reversed(ids):
            typ, md = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
            if matches_from(email.message_from_bytes(md[0][1]), from_filter):
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
    args = ap.parse_args()

    cfg_file = Path(args.config).expanduser() if args.config else CONFIG_FILE
    if not cfg_file.exists():
        sys.exit(
            f"FEHLER: {cfg_file} fehlt — Maschine ist für Mail nicht freigegeben (Capability-Profil)"
        )
    cfg = parse_env(cfg_file)
    missing = [k for k in ("SMTP_HOST", "MAIL_FROM", "MAIL_CREDS_FILE") if k not in cfg]
    if missing:
        sys.exit(f"FEHLER: Keys fehlen in {cfg_file}: {', '.join(missing)}")

    with connect(cfg) as imap:
        if args.list is not None:
            cmd_list(imap, args.folder, args.list, args.from_filter)
        else:
            cmd_fetch(
                imap,
                args.folder,
                args.fetch,
                args.from_filter,
                args.save_attachments,
                args.max_chars,
            )


if __name__ == "__main__":
    main()
