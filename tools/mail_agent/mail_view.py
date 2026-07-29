#!/usr/bin/env python3
"""Eine IMAP-Mail als lokale HTML-Datei rendern und ihren file://-Link ausgeben.

Warum es das gibt: Für das IIL-Postfach (M365/Graph) lässt sich ein OWA-Deeplink
aus der Graph-`id` bauen — die Mail ist aus dem Action-Board heraus anklickbar.
Für HNU (Exchange on-prem) und AD läuft der Zugriff über IMAP, und IMAP kennt
keine Item-URL; eine Rechte-Anpassung an der Hochschule ist nicht möglich
(Owner-Feststellung 2026-07-29). Der Link muss deshalb nicht ins Postfach zeigen:
Dieses Werkzeug rendert die Mail read-only in den lokalen Cache und liefert einen
kurzen `file://`-Link, den das Board wie jeden anderen Link trägt.

Strikt read-only gegenüber dem Postfach: `select(readonly=True)` + `BODY.PEEK`.

Datenschutz — zwei bewusste Eigenschaften:
  * Der Cache liegt unter ~/.claude/mail-cache/, also NIE in einem Repo
    (Mail-Inhalt ist Fremd-Daten, Charta Art. 2 — nichts davon gehört ins git).
  * Externe Referenzen im HTML-Teil werden neutralisiert. Zähl-Pixel und
    Remote-Bilder würden beim Öffnen der Datei einen Abruf beim Absender
    auslösen und damit "gelesen am ..." verraten — das wäre eine Außenwirkung
    ohne Freigabe. Bilder werden angezeigt, wenn sie als CID-Anhang mitkamen.

Verwendung:
    python3 tools/mail_agent/mail_view.py --account hnu --uid 42315
    python3 tools/mail_agent/mail_view.py --account hnu --seq 174        # Nummer aus read_mail --list
    python3 tools/mail_agent/mail_view.py --account hnu --seq 174 --url-only
    python3 tools/mail_agent/mail_view.py --account hnu --seq 174,178,182 --url-only

`--seq` nimmt die Nummer, die `read_mail.py --list` anzeigt. Das ist die
IMAP-*Sequenznummer*, nicht die UID: sie verschiebt sich, sobald eine ältere
Mail im Ordner gelöscht wird. Ausgegeben wird darum immer zusätzlich die echte
UID — die überlebt alles außer dem Verschieben in einen anderen Ordner.
"""

from __future__ import annotations

import argparse
import email
import html
import imaplib
import re
import sys
import unicodedata
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from read_mail import (  # noqa: E402
    WERKZEUG as READ_MAIL_WERKZEUG,
    _mailbox_arg,
    _resolve_config,
    connect,
    decode_hdr,
)
from send_mail import parse_env  # noqa: E402

#: Cache-Wurzel — bewusst unter ~/.claude, nie in einem Repo-Checkout.
CACHE_ROOT = Path.home() / ".claude" / "mail-cache"

#: Tags, die im gerenderten Ausschnitt nichts zu suchen haben.
_TAG_BLACKLIST = ("script", "style", "iframe", "object", "embed", "link", "meta", "base")

#: Attribute, die auf entfernte Ressourcen zeigen (Zähl-Pixel!) oder Code tragen.
_REMOTE_ATTR = re.compile(
    r"""\s(src|srcset|background|poster|action|formaction|data|codebase)\s*=\s*"""
    r"""(?P<q>["']?)(?P<val>[^"'>\s]*)(?P=q)""",
    re.I,
)
_EVENT_ATTR = re.compile(r"""\son[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_CSS_URL = re.compile(r"""url\(\s*['"]?(?!cid:|data:)[^)]*\)""", re.I)


def slugify(text: str, max_len: int = 40) -> str:
    """Betreff → dateisystemtauglicher Slug (ASCII, keine Pfadanteile)."""
    # Umlaute ZUERST ersetzen: NFKD zerlegt "ü" in "u"+Diaerese, danach greift
    # kein replace("ü", "ue") mehr und aus "bezüge" würde "bezuge".
    text = text or ""
    for umlaut, ersatz in (
        ("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
        ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
    ):
        text = text.replace(umlaut, ersatz)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (text[:max_len].rstrip("-")) or "ohne-betreff"


def sanitize_html(raw: str) -> tuple[str, int]:
    """Fremdes Mail-HTML entschärfen. Rückgabe: (html, Anzahl neutralisierter Verweise).

    Kein vollwertiger Sanitizer und will auch keiner sein — die Datei wird lokal
    per file:// geöffnet, nicht ausgeliefert. Ziel ist eng: kein Skript-Ausführen,
    und vor allem KEIN Abruf beim Absender (Zähl-Pixel), der das Lesen verrät.
    """
    for tag in _TAG_BLACKLIST:
        raw = re.sub(rf"<{tag}\b.*?</{tag}\s*>", "", raw, flags=re.S | re.I)
        raw = re.sub(rf"<{tag}\b[^>]*/?>", "", raw, flags=re.I)
    raw = _EVENT_ATTR.sub("", raw)

    blocked = 0

    def _neutralize(m: re.Match[str]) -> str:
        nonlocal blocked
        val = m.group("val")
        if val.startswith(("cid:", "data:")) or not val:
            return m.group(0)
        blocked += 1
        return f' data-blockiert-{m.group(1).lower()}="{html.escape(val, quote=True)}"'

    raw = _REMOTE_ATTR.sub(_neutralize, raw)
    raw, css_hits = _CSS_URL.subn("none", raw)
    return raw, blocked + css_hits


def _body_parts(msg: Message) -> tuple[str, str]:
    """(html_teil, text_teil) — je der erste passende Nicht-Anhang-Teil."""
    html_part = text_part = ""
    for part in msg.walk():
        if part.get_filename():
            continue
        ctype = part.get_content_type()
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", "replace")
        if ctype == "text/html" and not html_part:
            html_part = text
        elif ctype == "text/plain" and not text_part:
            text_part = text
    return html_part, text_part


def _save_attachments(msg: Message, target: Path) -> list[tuple[str, int]]:
    """Anhänge neben die HTML-Datei legen. Pfadanteile werden gestrippt."""
    saved: list[tuple[str, int]] = []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        name = Path(decode_hdr(fn)).name
        if not name or name in (".", ".."):
            continue
        data = part.get_payload(decode=True) or b""
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(data)
        saved.append((name, len(data)))
    return saved


_PAGE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<title>{titel}</title>
<style>
 body {{ font: 15px/1.55 -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 46rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
 header {{ border-left: 3px solid #888; padding-left: .9rem; margin-bottom: 1.6rem; }}
 header dl {{ display: grid; grid-template-columns: max-content 1fr; gap: .15rem .8rem; margin: 0; }}
 header dt {{ color: #666; }} header dd {{ margin: 0; }}
 h1 {{ font-size: 1.15rem; margin: 0 0 .7rem; }}
 .hinweis {{ background: #fff6e0; border: 1px solid #e8cf95; padding: .5rem .8rem;
             border-radius: 4px; font-size: .85rem; margin-bottom: 1.4rem; }}
 .inhalt {{ overflow-x: auto; }}
 .inhalt img {{ max-width: 100%; }}
 pre {{ white-space: pre-wrap; word-wrap: break-word; font: 14px/1.5 ui-monospace, monospace; }}
 footer {{ margin-top: 2.5rem; border-top: 1px solid #ddd; padding-top: .7rem;
           color: #777; font-size: .8rem; }}
 @media (prefers-color-scheme: dark) {{
   body {{ background: #16181a; color: #e6e6e6; }}
   header {{ border-color: #555; }} header dt {{ color: #9aa0a6; }}
   .hinweis {{ background: #2c2718; border-color: #5c5230; }}
   footer {{ border-color: #333; color: #888; }}
   a {{ color: #7fb2f0; }}
 }}
</style></head><body>
<header>
 <h1>{betreff}</h1>
 <dl>{kopfzeilen}</dl>
</header>
{hinweis}
<div class="inhalt">{inhalt}</div>
<footer>Lokale Ansicht, erzeugt {stand} durch {werkzeug} · Postfach unverändert
 (read-only, BODY.PEEK) · nicht die Mail selbst, sondern eine Kopie.</footer>
</body></html>
"""


def render(msg: Message, konto: str, ordner: str, uid: str, ziel: Path) -> Path:
    betreff = decode_hdr(msg.get("Subject")) or "(ohne Betreff)"
    ziel.mkdir(parents=True, exist_ok=True)
    datei = ziel / f"{uid}-{slugify(betreff)}.html"

    kopf = []
    for label, header in (
        ("Von", "From"), ("An", "To"), ("Cc", "Cc"), ("Datum", "Date"),
    ):
        wert = decode_hdr(msg.get(header))
        if wert:
            kopf.append(f"<dt>{label}</dt><dd>{html.escape(wert)}</dd>")
    kopf.append(f"<dt>Ordner</dt><dd>{html.escape(konto)} · {html.escape(ordner)} · UID {uid}</dd>")

    anhaenge = _save_attachments(msg, datei.parent / f"{uid}-anhaenge")
    if anhaenge:
        # href muss URL-kodiert sein: reale Anhangsnamen tragen Leerzeichen und
        # Umlaute ("Anschreiben_Verbandsanhörung ....pdf") — roh im href bricht
        # der Link im Browser.
        links = ", ".join(
            f'<a href="{uid}-anhaenge/{quote(n)}">{html.escape(n)}</a> '
            f"({groesse // 1024} kB)"
            for n, groesse in anhaenge
        )
        kopf.append(f"<dt>Anhänge</dt><dd>{links}</dd>")

    html_teil, text_teil = _body_parts(msg)
    if html_teil:
        inhalt, blockiert = sanitize_html(html_teil)
    else:
        inhalt = f"<pre>{html.escape(text_teil or '(kein darstellbarer Textteil)')}</pre>"
        blockiert = 0

    hinweis = ""
    if blockiert:
        hinweis = (
            f'<p class="hinweis">{blockiert} externe Verweis(e) neutralisiert — '
            "Remote-Bilder und Zähl-Pixel würden dem Absender sonst melden, "
            "dass und wann die Mail gelesen wurde.</p>"
        )

    datei.write_text(
        _PAGE.format(
            titel=html.escape(betreff),
            betreff=html.escape(betreff),
            kopfzeilen="".join(kopf),
            hinweis=hinweis,
            inhalt=inhalt,
            stand=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            werkzeug=html.escape(f"mail_view.py (auf {READ_MAIL_WERKZEUG})"),
        ),
        encoding="utf-8",
    )
    return datei


def _uid_fuer_seq(imap: imaplib.IMAP4_SSL, seq: str) -> str:
    """Sequenznummer (wie read_mail --list sie zeigt) → echte, stabile UID."""
    typ, data = imap.fetch(seq.encode(), "(UID)")
    if typ != "OK" or not data or data[0] is None:
        sys.exit(f"FEHLER: keine Nachricht mit Nummer {seq}")
    treffer = re.search(rb"UID (\d+)", data[0] if isinstance(data[0], bytes) else data[0][0])
    if not treffer:
        sys.exit(f"FEHLER: UID zu Nummer {seq} nicht lesbar")
    return treffer.group(1).decode()


def _hole(imap: imaplib.IMAP4_SSL, uid: str) -> Message:
    typ, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
    if typ != "OK" or not data or data[0] is None:
        sys.exit(f"FEHLER: keine Nachricht mit UID {uid}")
    roh = next(teil[1] for teil in data if isinstance(teil, tuple))
    return email.message_from_bytes(roh)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--account", help="Postfach-Kürzel → ~/.claude/mail-<NAME>.env")
    ap.add_argument("--config", help="alternative Mail-Config (Default: ~/.claude/mail.env)")
    ap.add_argument("--folder", "--source", default="INBOX", dest="folder")
    quelle = ap.add_mutually_exclusive_group(required=True)
    quelle.add_argument("--uid", help="echte IMAP-UID (stabil), Komma-Liste möglich")
    quelle.add_argument("--seq", help="Nummer aus read_mail --list (verschiebt sich), Komma-Liste")
    ap.add_argument("--url-only", action="store_true", help="nur den file://-Link ausgeben")
    ap.add_argument("--cache-root", default=str(CACHE_ROOT))
    args = ap.parse_args()

    cfg = parse_env(_resolve_config(args.config, args.account))
    konto = args.account or cfg.get("MAIL_FROM", "default")
    wurzel = Path(args.cache_root).expanduser() / slugify(konto) / slugify(args.folder)

    imap = connect(cfg)
    try:
        imap.select(_mailbox_arg(args.folder), readonly=True)
        werte = (args.uid or args.seq).split(",")
        for wert in [w.strip() for w in werte if w.strip()]:
            uid = wert if args.uid else _uid_fuer_seq(imap, wert)
            datei = render(_hole(imap, uid), konto, args.folder, uid, wurzel)
            if args.url_only:
                print(datei.as_uri())
            else:
                betreff = datei.stem.split("-", 1)[-1]
                print(f"UID {uid} · {betreff}")
                print(f"  {datei.as_uri()}")
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()


if __name__ == "__main__":
    main()
