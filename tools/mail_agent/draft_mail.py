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
  draft_mail.py --account hnu --role hnu --design --to a@b.de --subject "AW: ..." \
                --body-file mail.txt --in-reply-to "<mid@host>"   # Design + Strang-Zuordnung
"""

from __future__ import annotations

import argparse
import html as html_mod
import imaplib
import mimetypes
import re
import sys
import time
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

# Config-/Credentials-Parsing und LIST-Zeilen-Regex kommen aus send_mail (eine SSoT),
# die Account-Aufloesung aus read_mail — nichts davon wird hier dupliziert.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import roles  # noqa: E402
from read_mail import _resolve_config  # noqa: E402

# html_to_text kommt aus send_mail — EINE Implementierung. Die frueher hier stehende
# Kopie hatte den <style>-Fix nicht, und genau das brach am 2026-07-30 die Textform
# von Outlook-Mails (VML-CSS statt Anrede). Der Docstring oben verspricht die SSoT.
from send_mail import (  # noqa: E402
    _LIST_LINE_RE,
    html_to_text,
    load_credentials,
    login_name,
    parse_env,
)

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


_ZITAT_FELDER = (("Von", "From"), ("Gesendet", "Date"), ("An", "To"), ("Cc", "Cc"))


def zitat_bauen(ursprung, *, als_html: bool, max_chars: int = 20000) -> str:
    """Ursprungsmail als Zitat aufbereiten — das IMAP-Gegenstueck zu Graph `createReply`.

    Graph legt den zitierten Verlauf selbst an; per IMAP-APPEND gibt es das nicht,
    also wird der Block hier gebaut: Kopfzeilen im Outlook-Stil, darunter der
    **Text**-Teil der Ursprungsmail. Bewusst der Textteil und nicht deren HTML —
    fremdes Mail-HTML brachte sonst Remote-Referenzen (Zaehlpixel) in den eigenen
    Entwurf; die neutralisiert `mail_view.py` fuer die Anzeige, nicht fuer den Versand.
    """
    from read_mail import decode_hdr, extract_text  # lokal: nur fuer diesen Weg

    kopf = [
        (label, decode_hdr(ursprung.get(feld)))
        for label, feld in _ZITAT_FELDER
        if ursprung.get(feld)
    ]
    kopf.append(("Betreff", decode_hdr(ursprung.get("Subject"))))
    rumpf = extract_text(ursprung, max_chars=max_chars).rstrip()
    if als_html:
        zeilen = "".join(
            f"<p style='margin:0;font-size:12.5px;color:#55606A;'>"
            f"<b>{html_mod.escape(label)}:</b> {html_mod.escape(wert)}</p>"
            for label, wert in kopf
        )
        return (
            '<div style="margin-top:24px;padding-top:14px;border-top:1px solid #C9C4BA;'
            "font-family:'Segoe UI',Helvetica,Arial,sans-serif;\">"
            + zeilen
            + "<div style='margin-top:12px;font-size:13px;line-height:1.55;color:#2A3138;"
            "white-space:pre-wrap;'>" + html_mod.escape(rumpf) + "</div></div>"
        )
    kopf_text = "\n".join(f"{label}: {wert}" for label, wert in kopf)
    zitiert = "\n".join(f"> {z}" for z in rumpf.split("\n"))
    return f"\n\n-----Urspruengliche Nachricht-----\n{kopf_text}\n\n{zitiert}\n"


def hole_ursprung(cfg: dict[str, str], message_id: str):
    """Ursprungsmail per Message-ID aus dem Postfach holen (read-only, BODY.PEEK).

    Die Message-ID ist der stabile Anker — UIDs wandern beim Umsortieren. Gesucht
    wird ueber alle Ordner, damit eine bereits einsortierte Mail noch gefunden wird.
    """
    from anker import suche_message_id
    from read_mail import _mailbox_arg, connect

    imap = connect(cfg)
    try:
        ordner, uid = suche_message_id(imap, message_id)
        if not uid:
            sys.exit(f"FEHLER: Message-ID {message_id} in keinem Ordner gefunden")
        imap.select(_mailbox_arg(ordner), readonly=True)
        typ, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
        if typ != "OK" or not data or not isinstance(data[0], tuple):
            sys.exit(f"FEHLER: Ursprungsmail {message_id} nicht lesbar ({ordner})")
        return message_from_bytes(data[0][1])
    finally:
        try:
            imap.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def build_draft(
    sender: str,
    to: list[str],
    cc: list[str],
    subject: str,
    *,
    text: str | None = None,
    html: str | None = None,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> EmailMessage:
    """Entwurf bauen; mit `html` als multipart/alternative, sonst reines text/plain.

    `in_reply_to`/`references` tragen die Message-ID der Ursprungsmail. Ohne sie
    landet eine Antwort beim Empfaenger als NEUER Strang — der Verlauf reisst,
    obwohl der Betreff stimmt. Graph macht das per `createReply` von selbst,
    IMAP-APPEND nicht (Befund 2026-07-30).
    """
    if not text and not html:
        raise ValueError("weder Text- noch HTML-Body angegeben")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        # References traegt die ganze Kette; fehlt sie, genuegt die eine ID.
        msg["References"] = references or in_reply_to
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
        "--in-reply-to",
        dest="in_reply_to",
        help="Message-ID der Ursprungsmail — ohne sie reisst der Strang beim Empfaenger",
    )
    ap.add_argument(
        "--references",
        help="ganze References-Kette; fehlt sie, wird --in-reply-to genommen",
    )
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
    ap.add_argument(
        "--role",
        default=None,
        help="Rollen-ID aus der Registry (KONZ-033): setzt Absender, haengt "
        "Signatur/Pflicht-Footer an und erzwingt die Kanal-Grenze (#1481)",
    )
    ap.add_argument("--registry", default=None, help="alternative Rollen-Registry")
    ap.add_argument(
        "--design",
        action="store_true",
        help="mit --role: Klartext im Rollen-Design als HTML-Mail rendern",
    )
    ap.add_argument(
        "--eyebrow",
        default=None,
        help="Kopfzeile ueber der Anrede bei --design (Default: Betreff)",
    )
    ap.add_argument(
        "--zitat-message-id",
        default=None,
        metavar="<mid@host>",
        help="Ursprungsmail (Message-ID) als Zitat unter die Antwort setzen — "
        "das IMAP-Gegenstueck zu Graph createReply",
    )
    args = ap.parse_args()
    if args.design and not args.role:
        ap.error("--design braucht --role (das Design kommt aus der Rolle)")

    profile = None
    if args.role:
        try:
            profile = roles.resolve(args.role, args.registry)
        except (FileNotFoundError, ValueError) as e:
            sys.exit(f"FEHLER: {e}")
        if profile.transport != "imap_append":
            sys.exit(
                f"FEHLER: Rolle '{profile.role_id}' hat transport "
                f"'{profile.transport}', draft_mail bedient nur 'imap_append' — "
                "fuer graph_draft graph_mail --draft, fuer smtp send_mail nutzen."
            )
        if args.sender and args.sender != profile.sender:
            sys.exit(
                f"FEHLER: --from '{args.sender}' widerspricht der Rolle "
                f"'{profile.role_id}' ('{profile.sender}') — nur eines von beiden angeben."
            )
        if args.signature_file:
            sys.exit(
                "FEHLER: --signature-file und --role zugleich — die Rolle bringt "
                "ihre Signatur mit; zwei Quellen wuerden sie doppelt anhaengen."
            )

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

    if profile:
        # Pre-Send-Gate vor jedem Netzzugriff (#1481).
        try:
            roles.pruefe_kanalgrenze(
                profile, args.subject, text, html_to_text(html) if html else None
            )
        except roles.KanalgrenzeVerletzt as e:
            sys.exit(f"ABBRUCH (Kanal-Grenze): {e}")
        if args.design:
            if html:
                sys.exit(
                    "FEHLER: --design und HTML-Body zugleich — das Design rendert "
                    "den Klartext selbst; nur eines von beiden angeben."
                )
            if not (text or "").strip():
                sys.exit("FEHLER: --design braucht einen Klartext-Body")
            html = roles.render_email_html(
                profile,
                eyebrow=args.eyebrow or args.subject,
                subject=args.subject,
                **roles.zerlege_klartext(text or ""),
            )
            text = None  # Text-Teil leitet build_draft aus dem HTML ab (mit Signatur)
        elif not html:
            text = roles.text_mit_signatur(profile, text or "")

    if args.zitat_message_id:
        ursprung = hole_ursprung(cfg, args.zitat_message_id)
        if html:
            # Das Zitat gehoert VOR </body>, sonst haengt es ausserhalb des Rumpfes.
            block = zitat_bauen(ursprung, als_html=True)
            html = (
                html.replace("</body>", f"{block}</body>", 1)
                if "</body>" in html
                else html + block
            )
        if text:
            text = text.rstrip() + zitat_bauen(ursprung, als_html=False)
        print(f"Zitat uebernommen: {args.zitat_message_id}")

    sender = (profile.sender if profile else args.sender) or cfg["MAIL_FROM"]
    # Anmeldung und Absender sind zwei verschiedene Dinge: das HNU-Postfach meldet
    # sich mit einem Benutzernamen an, verschickt aber unter einer Adresse.
    user, password = load_credentials(
        Path(cfg["MAIL_CREDS_FILE"]).expanduser(), login_name(cfg)
    )
    msg = build_draft(
        sender,
        args.to,
        args.cc,
        args.subject,
        text=text,
        html=html,
        attachments=args.attach,
        in_reply_to=args.in_reply_to,
        references=args.references,
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
    rolle = f" Rolle: {profile.role_id} ({profile.display_name})." if profile else ""
    print(
        f"OK: Entwurf ({kind}) in '{folder}' abgelegt, UID {uid} — NICHT gesendet.{rolle} "
        f"Pruefen und selbst aus dem Mail-Client senden."
    )


if __name__ == "__main__":
    main()
