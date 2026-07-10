#!/usr/bin/env python3
"""Mail-Versand über den konfigurierten SMTP-Transport (Konsument: /send-mail Skill).

Konfiguration (keine Werte im Repo — Hardcoding-Verbot, policy claude-skills.md):
  ~/.claude/mail.env            SMTP_HOST, SMTP_PORT, MAIL_FROM, MAIL_CREDS_FILE
  MAIL_CREDS_FILE               user=/password=-Paare; das Paar mit user==MAIL_FROM wird genutzt

Credentials werden niemals ausgegeben — Output enthält nur Host/Port/Empfänger/Anhänge.
Nicht idempotent: jeder Aufruf verschickt eine Mail.
"""
from __future__ import annotations

import argparse
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

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
    user = None
    for line in creds_file.read_text().splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key == "user":
            user = val
        elif key == "password" and user == sender:
            return user, val
    sys.exit(f"FEHLER: kein Credentials-Paar für {sender} in {creds_file}")


def build_message(sender: str, args: argparse.Namespace) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(args.to)
    msg["Subject"] = args.subject
    body = Path(args.body_file).read_text() if args.body_file else args.body
    msg.set_content(body)
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--to", action="append", required=True, help="Empfänger (mehrfach möglich)")
    ap.add_argument("--subject", required=True)
    body_group = ap.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body", help="Mailtext direkt")
    body_group.add_argument("--body-file", help="Mailtext aus Datei")
    ap.add_argument("--attach", action="append", default=[], help="Anhang-Pfad (mehrfach möglich)")
    ap.add_argument("--from", dest="sender", default=None, help="Absender-Override (Default: MAIL_FROM)")
    args = ap.parse_args()

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


if __name__ == "__main__":
    main()
