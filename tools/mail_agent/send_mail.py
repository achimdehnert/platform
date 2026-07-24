#!/usr/bin/env python3
"""Mail-Versand über den konfigurierten SMTP-Transport (Konsument: /send-mail Skill).

Konfiguration (keine Werte im Repo — Hardcoding-Verbot, policy claude-skills.md):
  ~/.claude/mail.env            SMTP_HOST, SMTP_PORT, MAIL_FROM, MAIL_CREDS_FILE
                                 optional: IMAP_HOST (default SMTP_HOST), IMAP_PORT (default 993),
                                 IMAP_SENT_FOLDER (default: Auto-Erkennung per LIST)
  MAIL_CREDS_FILE               user=/password=-Paare; das Paar mit user==MAIL_FROM wird genutzt

Credentials werden niemals ausgegeben — Output enthält nur Host/Port/Empfänger/Anhänge.
Nicht idempotent: jeder Aufruf verschickt eine Mail.

Reiner SMTP-Submit legt keine Kopie im "Gesendet"-Ordner ab (das macht sonst der
Mail-Client per IMAP-APPEND) — nach dem SMTP-Versand hängt main() daher optional
eine IMAP-APPEND-Kopie in den Sent-Ordner an. Schlägt das fehl (Server ohne IMAP,
falsche Zugangsdaten, Netz), ist das nur eine Warnung: die Mail ist bereits
verschickt, das Fehlen der Sent-Kopie darf den Erfolg nicht überschreiben.
"""
from __future__ import annotations

import argparse
import imaplib
import re
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path

_LIST_LINE_RE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?P<delim>[^"]*)"|NIL)\s+(?P<name>.+)$')

CONFIG_FILE = Path.home() / ".claude" / "mail.env"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    return values


def load_credentials(creds_file: Path, sender: str) -> tuple[str, str]:
    # Bei mehreren Paaren mit gleichem user gewinnt das LETZTE — Rotation hängt
    # typischerweise das neue Paar unten an (retro f4a546-incr #6: first-match
    # lieferte still das veraltete Passwort).
    user = None
    match = None
    for line in creds_file.read_text().splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key == "user":
            user = val
        elif key == "password" and user == sender:
            match = (user, val)
    if match is None:
        sys.exit(f"FEHLER: kein Credentials-Paar für {sender} in {creds_file}")
    return match


def html_to_text(html: str) -> str:
    """Minimaler Text-Fallback für den text/plain-Teil einer multipart/alternative-Mail.

    Kein vollwertiger HTML-Renderer — echte Clients zeigen ohnehin den HTML-Teil;
    dieser Fallback ist nur für reine Text-Clients und für die Sent-Kopie lesbar.
    """
    import html as _htmlmod

    text = re.sub(r"(?is)<(script|style|head|title)[^>]*>.*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6])\s*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = _htmlmod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def build_message(sender: str, args: argparse.Namespace) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(args.to)
    msg["Subject"] = args.subject
    text = Path(args.body_file).read_text() if args.body_file else args.body
    html_file = getattr(args, "html_file", None)
    html = Path(html_file).read_text() if html_file else None
    if html is not None:
        # multipart/alternative: Text-Teil zuerst (Fallback), dann HTML — Clients
        # bevorzugen den zuletzt hinzugefügten passenden Teil (RFC 2046 §5.1.4).
        msg.set_content(text if text is not None else html_to_text(html))
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text)
    for att in args.attach:
        p = Path(att).expanduser()
        maintype, subtype = ("text", "plain")
        if p.suffix == ".md":
            subtype = "markdown"
        elif p.suffix == ".pdf":
            maintype, subtype = ("application", "pdf")
        elif p.suffix not in {".txt", ".md", ".csv", ".log"}:
            maintype, subtype = ("application", "octet-stream")
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)
    return msg


def send(host: str, port: int, user: str, password: str, msg: EmailMessage) -> str:
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
        return f"SSL:{port}"
    except (smtplib.SMTPException, OSError) as e:
        print(f"{port}/SSL fehlgeschlagen ({type(e).__name__}), versuche 587/STARTTLS", file=sys.stderr)
    with smtplib.SMTP(host, 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(user, password)
        s.send_message(msg)
    return "STARTTLS:587"


def find_sent_folder(imap: imaplib.IMAP4_SSL, configured: str | None) -> str | None:
    # LIST-Zeilenform: (flags) "delim" name — name ist nur gequotet, wenn er Sonderzeichen
    # enthält (RFC 3501 §7.2.2), z.B. `(\HasNoChildren \Sent) "." INBOX.Sent` ohne Quotes.
    typ, data = imap.list()
    if typ != "OK":
        return configured
    by_special_use = None
    names = []
    for entry in data:
        if not entry:
            continue
        decoded = entry.decode(errors="replace")
        m = _LIST_LINE_RE.match(decoded)
        if not m:
            continue
        name = m.group("name").strip('"')
        names.append(name)
        if "\\sent" in m.group("flags").lower() and by_special_use is None:
            by_special_use = name  # RFC 6154 SPECIAL-USE \Sent gewinnt vor Namens-Rätselraten
    if by_special_use:
        return by_special_use
    if configured and configured in names:
        return configured
    for candidate in names:
        if "sent" in candidate.lower():
            return candidate
    return configured


def append_to_sent(
    host: str, port: int, user: str, password: str, msg: EmailMessage, sent_folder: str | None
) -> str:
    with imaplib.IMAP4_SSL(host, port, timeout=30) as imap:
        imap.login(user, password)
        folder = find_sent_folder(imap, sent_folder)
        if not folder:
            raise RuntimeError("kein Sent-Ordner gefunden (LIST lieferte keinen Kandidaten)")
        date_time = imaplib.Time2Internaldate(time.time())
        typ, resp = imap.append(folder, "(\\Seen)", date_time, msg.as_bytes())
        if typ != "OK":
            raise RuntimeError(f"APPEND fehlgeschlagen: {typ} {resp}")
        return folder


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--to", action="append", required=True, help="Empfänger (mehrfach möglich)")
    ap.add_argument("--subject", required=True)
    body_group = ap.add_mutually_exclusive_group(required=False)
    body_group.add_argument("--body", help="Mailtext direkt (text/plain)")
    body_group.add_argument("--body-file", help="Mailtext aus Datei (text/plain)")
    ap.add_argument(
        "--html-file",
        help="HTML-Body aus Datei (multipart/alternative). Text-Fallback aus "
        "--body/--body-file, sonst automatisch aus dem HTML abgeleitet.",
    )
    ap.add_argument("--attach", action="append", default=[], help="Anhang-Pfad (mehrfach möglich)")
    ap.add_argument("--from", dest="sender", default=None, help="Absender-Override (Default: MAIL_FROM)")
    args = ap.parse_args()
    if not (args.body or args.body_file or args.html_file):
        ap.error("mindestens eine Body-Quelle nötig: --body, --body-file oder --html-file")

    if not CONFIG_FILE.exists():
        sys.exit(f"FEHLER: {CONFIG_FILE} fehlt — Bootstrap siehe /send-mail Step 0")
    cfg = parse_env(CONFIG_FILE)
    missing = [k for k in ("SMTP_HOST", "SMTP_PORT", "MAIL_FROM", "MAIL_CREDS_FILE") if k not in cfg]
    if missing:
        sys.exit(f"FEHLER: Keys fehlen in {CONFIG_FILE}: {', '.join(missing)}")

    sender = args.sender or cfg["MAIL_FROM"]
    creds_file = Path(cfg["MAIL_CREDS_FILE"]).expanduser()
    user, password = load_credentials(creds_file, sender)
    msg = build_message(sender, args)
    via = send(cfg["SMTP_HOST"], int(cfg["SMTP_PORT"]), user, password, msg)
    atts = ", ".join(Path(a).name for a in args.attach) or "keine"
    print(f"OK: Mail an {', '.join(args.to)} via {cfg['SMTP_HOST']} ({via}), Anhänge: {atts}")

    imap_host = cfg.get("IMAP_HOST", cfg["SMTP_HOST"])
    imap_port = int(cfg.get("IMAP_PORT", "993"))
    try:
        folder = append_to_sent(imap_host, imap_port, user, password, msg, cfg.get("IMAP_SENT_FOLDER"))
        print(f"Sent-Kopie abgelegt in '{folder}' auf {imap_host}")
    except (imaplib.IMAP4.error, RuntimeError, OSError) as e:
        print(
            f"WARNUNG: Sent-Kopie fehlgeschlagen ({type(e).__name__}: {e}) — "
            "Mail wurde trotzdem verschickt (s.o.)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
