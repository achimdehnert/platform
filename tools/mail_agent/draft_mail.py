#!/usr/bin/env python3
"""Mail-Entwurf per IMAP-APPEND ablegen (Konsument: /send-mail, /read-mail, /iil-mail).

Schliesst die Luecke, die `graph_mail.py --draft` nur fuer das IIL-Postfach (Graph)
schliesst: Entwuerfe fuer JEDES per `~/.claude/mail[-<account>].env` konfigurierte
IMAP-Postfach — insbesondere HNU (`--account hnu`), ueber das die MEiKI-Korrespondenz
laeuft. Entstanden 2026-07-22, nachdem dieselbe APPEND-Logik in einer Session zweimal
ad hoc gebaut wurde (Wachstums-Pipeline Ad-hoc -> Skill, wie read_mail.py).

KEIN VERSAND: der Entwurf landet im Drafts-Ordner, gesendet wird vom Menschen aus
Outlook. Aussenwirkung bleibt beim Kapitaen (Lotsen-Charta Art. 2).

Zwei Erfahrungswerte, die hier fest eingebaut sind:
  * Ein per APPEND abgelegter Entwurf bekommt KEINE Outlook-Signatur — deshalb
    `--signature-file`.
  * Reine text/plain-Entwuerfe bricht Outlook selbst um und erzeugt genau die
    unerwuenschten Zeilenumbrueche — deshalb `--html-file` (multipart/alternative
    mit automatisch abgeleitetem Text-Teil).

Usage:
  draft_mail.py --account hnu --to a@b.de --subject "..." --html-file mail.html
  draft_mail.py --to a@b.de --cc c@d.de --subject "..." --body-file mail.txt \
                --signature-file sig.html --attach anhang.pdf
"""

from __future__ import annotations

import argparse
import html as html_mod
import imaplib
import mimetypes
import re
import sys
import time
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

# Config-/Credentials-Parsing und LIST-Zeilen-Regex kommen aus send_mail (eine SSoT),
# die Account-Aufloesung aus read_mail — nichts davon wird hier dupliziert.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from read_mail import _resolve_config  # noqa: E402
from send_mail import _LIST_LINE_RE, load_credentials, parse_env  # noqa: E402

#: RFC 6154 SPECIAL-USE gewinnt vor Namensraten; die Hints decken de/en-Postfaecher ab.
_DRAFT_NAME_HINTS = ("drafts", "entw")


def find_drafts_folder(imap: imaplib.IMAP4_SSL, configured: str | None) -> str | None:
    """Drafts-Ordner bestimmen: SPECIAL-USE \\Drafts > --folder > Namensheuristik.

    Analog zu send_mail.find_sent_folder — bewusst dieselbe Reihenfolge, damit sich
    Sent- und Drafts-Aufloesung nicht unterschiedlich verhalten. Der Ordnername kommt
    IMAP-seitig modified-UTF-7-kodiert zurueck (z.B. `Entw&APw-rfe` fuer "Entwuerfe")
    und wird genau so wieder verwendet — nicht dekodieren, sonst schlaegt SELECT fehl.
    """
    typ, data = imap.list()
    if typ != "OK":
        return configured
    by_special_use = None
    names: list[str] = []
    for entry in data:
        if not entry:
            continue
        match = _LIST_LINE_RE.match(entry.decode(errors="replace"))
        if not match:
            continue
        name = match.group("name").strip('"')
        names.append(name)
        if "\\drafts" in match.group("flags").lower() and by_special_use is None:
            by_special_use = name
    if by_special_use:
        return by_special_use
    if configured and configured in names:
        return configured
    for candidate in names:
        if any(hint in candidate.lower() for hint in _DRAFT_NAME_HINTS):
            return candidate
    return configured


def html_to_text(html: str) -> str:
    """Lesbaren text/plain-Teil aus dem HTML ableiten (Fallback fuer Nur-Text-Clients).

    Bewusst simpel: Absaetze und Listen werden zu Leerzeilen bzw. `- `-Punkten, Tags
    fallen weg, Entities werden aufgeloest. Kein HTML-Parser — der Input sind unsere
    eigenen, handgeschriebenen Mailtexte, nicht beliebiges Web-HTML.
    """
    text = re.sub(r"(?i)<br\s*/?>", "\n", html)
    text = re.sub(r"(?i)</(p|div|h[1-6])>", "\n\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "- ", text)
    text = re.sub(r"(?i)</(li|ul|ol)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def build_draft(
    sender: str,
    to: list[str],
    cc: list[str],
    subject: str,
    *,
    text: str | None = None,
    html: str | None = None,
    attachments: list[str] | None = None,
) -> EmailMessage:
    """Entwurf bauen; mit `html` als multipart/alternative, sonst reines text/plain."""
    if not text and not html:
        raise ValueError("weder Text- noch HTML-Body angegeben")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text or html_to_text(html or ""), subtype="plain", charset="utf-8")
    if html:
        msg.add_alternative(
            html if "<body" in html.lower() else f"<html><body>{html}</body></html>",
            subtype="html",
            charset="utf-8",
        )
    for path_str in attachments or []:
        path = Path(path_str).expanduser()
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        msg.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name
        )
    return msg


def append_draft(
    host: str,
    port: int,
    user: str,
    password: str,
    msg: EmailMessage,
    folder: str | None,
) -> tuple[str, str]:
    """Nachricht mit \\Draft-Flag anhaengen; gibt (Ordner, APPENDUID-oder-'?') zurueck."""
    with imaplib.IMAP4_SSL(host, port, timeout=30) as imap:
        imap.login(user, password)
        target = find_drafts_folder(imap, folder)
        if not target:
            raise RuntimeError(
                "kein Drafts-Ordner gefunden (LIST lieferte keinen Kandidaten)"
            )
        typ, resp = imap.append(
            target, "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes()
        )
        if typ != "OK":
            raise RuntimeError(f"APPEND fehlgeschlagen: {typ} {resp}")
        uid_match = re.search(rb"APPENDUID \d+ (\d+)", resp[0] or b"")
        return target, (uid_match.group(1).decode() if uid_match else "?")


def _read(path_str: str | None) -> str | None:
    return Path(path_str).expanduser().read_text(encoding="utf-8") if path_str else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--to", action="append", required=True, help="Empfaenger (mehrfach moeglich)"
    )
    ap.add_argument("--cc", action="append", default=[], help="Cc (mehrfach moeglich)")
    ap.add_argument("--subject", required=True)
    body = ap.add_mutually_exclusive_group(required=True)
    body.add_argument("--body", help="Mailtext direkt (text/plain)")
    body.add_argument(
        "--body-file", help="Mailtext aus Datei (.html/.htm => HTML-Teil)"
    )
    body.add_argument("--html-file", help="HTML-Body; Text-Teil wird abgeleitet")
    ap.add_argument("--text-file", help="expliziter Text-Teil zu --html-file")
    ap.add_argument("--signature-file", help="Signatur, wird an den Body angehaengt")
    ap.add_argument(
        "--attach", action="append", default=[], help="Anhang (mehrfach moeglich)"
    )
    ap.add_argument(
        "--from", dest="sender", default=None, help="Absender (Default: MAIL_FROM)"
    )
    ap.add_argument(
        "--config", help="alternative Mail-Config (Default: ~/.claude/mail.env)"
    )
    ap.add_argument("--account", help="Postfach-Kuerzel => ~/.claude/mail-<NAME>.env")
    ap.add_argument("--folder", help="Drafts-Ordner erzwingen (sonst Auto-Erkennung)")
    args = ap.parse_args()

    cfg_file = _resolve_config(args.config, args.account)
    if not cfg_file.exists():
        sys.exit(f"FEHLER: {cfg_file} fehlt — Maschine ist fuer Mail nicht freigegeben")
    cfg = parse_env(cfg_file)
    missing = [k for k in ("SMTP_HOST", "MAIL_FROM", "MAIL_CREDS_FILE") if k not in cfg]
    if missing:
        sys.exit(f"FEHLER: Keys fehlen in {cfg_file}: {', '.join(missing)}")

    html = _read(args.html_file)
    text = args.body or _read(args.text_file)
    if args.body_file:
        content = _read(args.body_file) or ""
        if args.body_file.lower().endswith((".html", ".htm")):
            html = content
        else:
            text = content
    signature = _read(args.signature_file)
    if signature:
        if html:
            html = html.rstrip() + "\n" + signature
        if text:
            text = text.rstrip() + "\n\n" + html_to_text(signature)

    sender = args.sender or cfg["MAIL_FROM"]
    user, password = load_credentials(Path(cfg["MAIL_CREDS_FILE"]).expanduser(), sender)
    msg = build_draft(
        sender,
        args.to,
        args.cc,
        args.subject,
        text=text,
        html=html,
        attachments=args.attach,
    )
    folder, uid = append_draft(
        cfg.get("IMAP_HOST", cfg["SMTP_HOST"]),
        int(cfg.get("IMAP_PORT", "993")),
        user,
        password,
        msg,
        args.folder,
    )
    kind = "HTML+Text" if html else "Text"
    print(
        f"OK: Entwurf ({kind}) in '{folder}' abgelegt, UID {uid} — NICHT gesendet. "
        f"Pruefen und selbst aus dem Mail-Client senden."
    )


if __name__ == "__main__":
    main()
