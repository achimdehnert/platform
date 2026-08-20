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
_TAG_BLACKLIST = (
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "link",
    "meta",
    "base",
)

#: Attribute, die auf entfernte Ressourcen zeigen (Zähl-Pixel!) oder Code tragen.
_REMOTE_ATTR = re.compile(
    r"""\s(src|srcset|background|poster|action|formaction|data|codebase)\s*=\s*"""
    r"""(?P<q>["']?)(?P<val>[^"'>\s]*)(?P=q)""",
    re.I,
)
_EVENT_ATTR = re.compile(r"""\son[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_CSS_URL = re.compile(r"""url\(\s*['"]?(?!cid:|data:)[^)]*\)""", re.I)

#: Inline-``style``-Attribute — Ansatzpunkt fuer die Hellschrift-Entschaerfung.
_STYLE_ATTR = re.compile(r"""style\s*=\s*(?P<q>["'])(?P<val>[^"']*)(?P=q)""", re.I)
_COLOR_DECL = re.compile(r"(^|;)(\s*color\s*:\s*)([^;]+)", re.I)
_RGB_WERTE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", re.I)


def _ist_helle_schrift(wert: str) -> bool:
    """Naeherungsweise: liegt die Farbe so nah an Weiss, dass sie auf hellem Grund verschwindet?"""
    w = wert.strip().lower()
    if w in ("white", "#fff", "#ffffff", "#fffffe"):
        return True
    m = _RGB_WERTE.search(w)
    if m:
        return all(int(k) >= 230 for k in m.groups())
    if re.fullmatch(r"#[0-9a-f]{6}", w):
        return all(int(w[i : i + 2], 16) >= 230 for i in (1, 3, 5))
    return False


def slugify(text: str, max_len: int = 40) -> str:
    """Betreff → dateisystemtauglicher Slug (ASCII, keine Pfadanteile)."""
    # Umlaute ZUERST ersetzen: NFKD zerlegt "ü" in "u"+Diaerese, danach greift
    # kein replace("ü", "ue") mehr und aus "bezüge" würde "bezuge".
    text = text or ""
    for umlaut, ersatz in (
        ("ä", "ae"),
        ("ö", "oe"),
        ("ü", "ue"),
        ("ß", "ss"),
        ("Ä", "Ae"),
        ("Ö", "Oe"),
        ("Ü", "Ue"),
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
    raw = _entschaerfe_helle_schrift(raw)
    return raw, blocked + css_hits


def _entschaerfe_helle_schrift(raw: str) -> str:
    """Fast weisse Inline-Schriftfarbe auf ``inherit`` zuruecksetzen — aber nur,
    wenn dasselbe ``style``-Attribut keine eigene Flaeche mitbringt.

    Grund: ``<style>``-Bloecke fliegen oben raus (``_TAG_BLACKLIST``). Eine Mail,
    die ihre dunkle Flaeche dort definiert und ihren Text inline hell faerbt,
    behaelt danach die helle Schrift und verliert den Grund — auf der hellen
    Flaeche der Ansicht steht sie dann weiss auf weiss. Traegt das Element seine
    Flaeche selbst (``background`` im selben Attribut), bleibt alles unangetastet:
    dort ist die helle Schrift gewollt und funktioniert weiter.
    """

    def _pro_attribut(m: re.Match[str]) -> str:
        val = m.group("val")
        if re.search(r"background", val, re.I):
            return m.group(0)

        def _pro_farbe(c: re.Match[str]) -> str:
            if not _ist_helle_schrift(c.group(3)):
                return c.group(0)
            return f"{c.group(1)}{c.group(2)}inherit"

        neu_val = _COLOR_DECL.sub(_pro_farbe, val)
        if neu_val == val:
            return m.group(0)
        q = m.group("q")
        return f"style={q}{neu_val}{q}"

    return _STYLE_ATTR.sub(_pro_attribut, raw)


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
 :root {{
   --grund: #ffffff;          /* Seitengrund */
   --text: #1a1a1a;
   --gedaempft: #666666;      /* Kopfzeilen-Etiketten */
   --linie: #888888;
   --hinweis: #fff6e0;
   --hinweis-linie: #e8cf95;
   --fuss: #777777;
   --fuss-linie: #dddddd;
   --link: #0b57d0;
   /* Der Mailrumpf bleibt in beiden Schemata ein helles Blatt: Mail-HTML
      bringt eigene Inline-Farben mit (Outlook setzt color:black), die auf
      dunklem Grund unlesbar waeren. Darum kein Dark-Wert fuer diese drei. */
   --flaeche: #ffffff;
   --flaeche-text: #1a1a1a;
   --flaeche-rahmen: transparent;
 }}
 @media (prefers-color-scheme: dark) {{
   :root {{
     --grund: #16181a;
     --text: #e6e6e6;
     --gedaempft: #9aa0a6;
     --linie: #555555;
     --hinweis: #2c2718;
     --hinweis-linie: #5c5230;
     --fuss: #888888;
     --fuss-linie: #333333;
     --link: #7fb2f0;
     --flaeche-rahmen: #333333;   /* Abgrenzung des hellen Blatts */
   }}
 }}
 body {{ font: 15px/1.55 -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 46rem; margin: 2rem auto; padding: 0 1rem;
         background: var(--grund); color: var(--text); }}
 a {{ color: var(--link); }}
 header {{ border-left: 3px solid var(--linie); padding-left: .9rem; margin-bottom: 1.6rem; }}
 header dl {{ display: grid; grid-template-columns: max-content 1fr; gap: .15rem .8rem; margin: 0; }}
 header dt {{ color: var(--gedaempft); }} header dd {{ margin: 0; }}
 h1 {{ font-size: 1.15rem; margin: 0 0 .7rem; }}
 .hinweis {{ background: var(--hinweis); border: 1px solid var(--hinweis-linie); padding: .5rem .8rem;
             border-radius: 4px; font-size: .85rem; margin-bottom: 1.4rem; }}
 .inhalt {{ overflow-x: auto; background: var(--flaeche); color: var(--flaeche-text);
            box-shadow: 0 0 0 1px var(--flaeche-rahmen);
            padding: .9rem 1rem; border-radius: 6px; }}
 .inhalt img {{ max-width: 100%; }}
 .inhalt a {{ color: #0b57d0; }}   /* immer heller Grund, darum schemaunabhaengig */
 pre {{ white-space: pre-wrap; word-wrap: break-word; font: 14px/1.5 ui-monospace, monospace; }}
 footer {{ margin-top: 2.5rem; border-top: 1px solid var(--fuss-linie); padding-top: .7rem;
           color: var(--fuss); font-size: .8rem; }}
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


def render(
    msg: Message,
    konto: str,
    ordner: str,
    uid: str,
    ziel: Path,
    basis: str | None = None,
) -> Path:
    """`basis` = URL-Praefix dieser Mail beim Ausliefern ueber den Link-Dienst.

    Ohne `basis` entstehen relative Anhang-Links, die neben der HTML-Datei auf der
    Platte funktionieren (der CLI-Weg). Ueber HTTP tragen sie nicht: der Browser
    loest sie gegen den AUFRUFPFAD auf, und der ist bei `/a/<nr>` ein voellig
    anderer als bei `/m/<konto>/<uid>`. Genau daraus entstand der kaputte Link
    `/a/163497-anhaenge/<datei>` — der Verzeichnisname von der Platte war in die
    URL gewandert. Mit `basis` werden die Links absolut und damit aufrufpfad-egal.
    """
    betreff = decode_hdr(msg.get("Subject")) or "(ohne Betreff)"
    ziel.mkdir(parents=True, exist_ok=True)
    datei = ziel / f"{uid}-{slugify(betreff)}.html"

    kopf = []
    for label, header in (
        ("Von", "From"),
        ("An", "To"),
        ("Cc", "Cc"),
        ("Datum", "Date"),
    ):
        wert = decode_hdr(msg.get(header))
        if wert:
            kopf.append(f"<dt>{label}</dt><dd>{html.escape(wert)}</dd>")
    kopf.append(
        f"<dt>Ordner</dt><dd>{html.escape(konto)} · {html.escape(ordner)} · UID {uid}</dd>"
    )

    anhaenge = _save_attachments(msg, datei.parent / f"{uid}-anhaenge")
    if anhaenge:
        # Auf der Platte heisst der Ordner "<uid>-anhaenge" (neben der HTML-Datei);
        # im Dienst lautet die Route "<basis>/anhaenge/<name>". Beides darf nicht
        # verwechselt werden — der Plattenname gehoert nicht in eine URL.
        praefix = f"{basis.rstrip('/')}/anhaenge" if basis else f"{uid}-anhaenge"
        # href muss URL-kodiert sein: reale Anhangsnamen tragen Leerzeichen und
        # Umlaute ("Anschreiben_Verbandsanhörung ....pdf") — roh im href bricht
        # der Link im Browser.
        links = ", ".join(
            f'<a href="{praefix}/{quote(n)}">{html.escape(n)}</a> '
            f"({groesse // 1024} kB)"
            for n, groesse in anhaenge
        )
        kopf.append(f"<dt>Anhänge</dt><dd>{links}</dd>")

    html_teil, text_teil = _body_parts(msg)
    if html_teil:
        inhalt, blockiert = sanitize_html(html_teil)
    else:
        inhalt = (
            f"<pre>{html.escape(text_teil or '(kein darstellbarer Textteil)')}</pre>"
        )
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


class MailNichtGefunden(LookupError):
    """Die angefragte Nachricht gibt es im Ordner nicht.

    Bewusst eine Ausnahme statt `sys.exit`: derselbe Code läuft im
    `mail_link_server` in einem Request-Thread. Ein `sys.exit` löst dort ein
    `SystemExit` aus, das an `except Exception` vorbeigeht — der Thread stirbt
    und der Browser bekommt eine leere Antwort statt eines 404 (gemessen
    2026-07-29 an `/m/ad/64`). Die CLI wandelt die Ausnahme unten in einen
    Exit-Code zurück.
    """


def _uid_fuer_seq(imap: imaplib.IMAP4_SSL, seq: str) -> str:
    """Sequenznummer (wie read_mail --list sie zeigt) → echte, stabile UID."""
    typ, data = imap.fetch(seq.encode(), "(UID)")
    if typ != "OK" or not data or data[0] is None:
        raise MailNichtGefunden(f"keine Nachricht mit Nummer {seq}")
    treffer = re.search(
        rb"UID (\d+)", data[0] if isinstance(data[0], bytes) else data[0][0]
    )
    if not treffer:
        raise MailNichtGefunden(f"UID zu Nummer {seq} nicht lesbar")
    return treffer.group(1).decode()


def _hole(imap: imaplib.IMAP4_SSL, uid: str) -> Message:
    typ, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
    if typ != "OK" or not data or data[0] is None:
        raise MailNichtGefunden(f"keine Nachricht mit UID {uid}")
    try:
        roh = next(teil[1] for teil in data if isinstance(teil, tuple))
    except StopIteration:
        raise MailNichtGefunden(f"keine Nachricht mit UID {uid}") from None
    return email.message_from_bytes(roh)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--account", help="Postfach-Kürzel → ~/.claude/mail-<NAME>.env")
    ap.add_argument(
        "--config", help="alternative Mail-Config (Default: ~/.claude/mail.env)"
    )
    ap.add_argument("--folder", "--source", default="INBOX", dest="folder")
    quelle = ap.add_mutually_exclusive_group(required=True)
    quelle.add_argument("--uid", help="echte IMAP-UID (stabil), Komma-Liste möglich")
    quelle.add_argument(
        "--seq", help="Nummer aus read_mail --list (verschiebt sich), Komma-Liste"
    )
    ap.add_argument(
        "--url-only", action="store_true", help="nur den file://-Link ausgeben"
    )
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
            try:
                uid = wert if args.uid else _uid_fuer_seq(imap, wert)
                datei = render(_hole(imap, uid), konto, args.folder, uid, wurzel)
            except MailNichtGefunden as fehlt:
                sys.exit(f"FEHLER: {fehlt}")
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
