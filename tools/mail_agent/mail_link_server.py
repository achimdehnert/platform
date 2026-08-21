#!/usr/bin/env python3
"""Kurze, anklickbare Links auf Mails — lokaler Dienst, nur über Loopback.

Warum es das gibt: Die Arbeitssitzung läuft per SSH auf dem Server, der Browser
aber auf dem Rechner des Owners. Ein `file://`-Link zeigt darum ins Leere, und
das HNU-Postfach hängt hinter einem Citrix-Gateway, hat also auch keinen
brauchbaren OWA-Deeplink. Dieser Dienst löst beides:

    http://localhost:8787/m/163497   → HNU-Mail live gerendert (IMAP, read-only)
    http://localhost:8787/i/az1      → 302 auf den langen OWA-Deeplink (IIL)

Erreichbar wird er über einen SSH-Tunnel, nicht über das Netz:

    ssh -N -L 8787:127.0.0.1:8787 devuser@<server>

Bewusst KEIN öffentlicher Endpunkt: hier gehen Mail-Inhalte über die Leitung
(Studierende, LRA-Vorgänge, Mandantensachen). Der Dienst bindet darum auf
127.0.0.1 und weigert sich, ohne ausdrückliches `--ich-weiss-was-ich-tue` auf
eine andere Adresse zu gehen. Wer ihn öffentlich stellen will, braucht davor
eine Authentifizierung — das ist eine Datenschutz-Entscheidung, keine Bequemlichkeit.

Gegenüber dem Postfach strikt read-only (`select(readonly=True)` + `BODY.PEEK`).
"""

from __future__ import annotations

import base64
import argparse
import html
import json
import re
import sys
import unicodedata
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anker import (  # noqa: E402
    ANKER_DATEI,
    GELOESCHT,
    UNPRUEFBAR,
    VERSCHOBEN,
    pruefe_anker,
)
from anker import lade as anker_lade  # noqa: E402
from anker import speichere as anker_speichere  # noqa: E402
from anker import uebernehme as anker_uebernehme  # noqa: E402
from read_mail import alle_ordner, ordner_klartext  # noqa: E402
from mail_view import (  # noqa: E402
    CACHE_ROOT,
    MailNichtGefunden,
    _hole,
    _mailbox_arg,
    _resolve_config,
    connect,
    parse_env,
    render,
    slugify,
)

#: Kurz-ID → Ziel. Liegt neben dem Board unter ~/.claude, nie in einem Repo.
LINK_REGISTRY = Path.home() / ".claude" / "mail-links.json"

#: Arbeitslisten (Boards) als Markdown. Bewusst ein EIGENES Verzeichnis und
#: ausdrücklich NICHT ``~/shared``: das ist laut CLAUDE.md die Übergabeschleuse,
#: in der Secrets zeitweise im Klartext liegen. Ein Dienst, der ``~/shared``
#: ausliefert, würde sie über den Tunnel sichtbar machen. Hier landet nur, was
#: für die Anzeige gedacht ist.
BOARD_ROOT = Path.home() / ".claude" / "boards"

#: Aus einer Graph-`id` wird der OWA-Deeplink so gebaut (belegt: funktioniert im Board).
OWA_TEMPLATE = (
    "https://outlook.office365.com/owa/?ItemID={id}&exvsurl=1&viewmodel=ReadMessageItem"
)

_UID = re.compile(r"^\d+$")
_KURZ_ID = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
_BOARD_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def board_pfad(name: str, wurzel: Path = BOARD_ROOT) -> Path | None:
    """Board-Name aus der URL → Datei unter ``wurzel``. None, wenn unbrauchbar.

    Bewusst restriktiv: nur ``[A-Za-z0-9_-]`` (also kein ``.``, kein ``/``), feste
    Endung ``.md``, und danach noch einmal geprüft, dass der aufgelöste Pfad
    wirklich unterhalb der Wurzel liegt — ein Symlink im Board-Verzeichnis soll
    nicht aus ihr herausführen.
    """
    if not _BOARD_NAME.match(name):
        return None
    ziel = (wurzel / f"{name}.md").resolve()
    try:
        ziel.relative_to(wurzel.resolve())
    except (ValueError, OSError):
        return None
    return ziel if ziel.is_file() else None


def board_als_html(text: str, titel: str) -> str:
    """Markdown → HTML. Fällt ohne die Bibliothek auf lesbaren Rohtext zurück."""
    try:
        import markdown  # noqa: PLC0415

        rumpf = markdown.markdown(text, extensions=["tables", "sane_lists"])
    except ImportError:
        rumpf = f"<pre>{html.escape(text)}</pre>"
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(titel)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<body style="font:15px/1.6 -apple-system,Segoe UI,sans-serif;max-width:70rem;margin:2rem auto;padding:0 1rem">
<style>
 table{{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.92em}}
 th,td{{border:1px solid #d0d0d0;padding:.35rem .5rem;text-align:left}}
 th{{background:#f4f4f4}} tr:nth-child(even) td{{background:#fafafa}}
 code{{background:#f2f2f2;padding:.1rem .3rem;border-radius:3px}}
 h2{{margin-top:2rem;border-bottom:1px solid #e0e0e0;padding-bottom:.2rem}}
 @media (prefers-color-scheme:dark){{
   body{{background:#16181c;color:#e6e6e6}} th{{background:#23262c}}
   tr:nth-child(even) td{{background:#1c1f24}} th,td{{border-color:#333}}
   code{{background:#23262c}} a{{color:#7ab7ff}} h2{{border-color:#333}}
 }}
</style>
{rumpf}
<p style="color:#777;font-size:.85rem;margin-top:2rem">Nur über Loopback erreichbar.
<a href="/">Übersicht</a></p>
<div id=ovl style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9">
 <div id=ovl-box style="position:absolute;inset:4% 6%;background:#fff;border-radius:10px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.4)">
  <div style="padding:.45rem .9rem;display:flex;justify-content:flex-end;gap:1.2rem;border-bottom:1px solid #d0d0d0;font-size:.9rem">
   <a id=ovl-ext href="#" target=_blank rel=noreferrer>in OWA/neuem Tab öffnen ↗</a>
   <a href="#" id=ovl-x>✕ schließen (Esc)</a>
  </div>
  <iframe id=ovl-frame title="Mail" style="border:0;flex:1;width:100%"></iframe>
 </div>
</div>
<style>@media (prefers-color-scheme:dark){{#ovl-box{{background:#16181c}}
 #ovl-box>div{{border-color:#333}}}}</style>
<script>
(function(){{
 var ovl=document.getElementById('ovl'),fr=document.getElementById('ovl-frame'),
     ext=document.getElementById('ovl-ext');
 function zu(){{ovl.style.display='none';fr.src='about:blank';}}
 function auf(src,orig){{fr.src=src;ext.href=orig;ovl.style.display='block';}}
 document.addEventListener('click',function(e){{
  var a=e.target.closest('a');if(!a)return;
  var h=a.getAttribute('href')||'';
  if(a.id==='ovl-x'){{e.preventDefault();zu();return;}}
  if(a===ext)return;                      // Absprung nach draußen: normal folgen
  if(h.indexOf('/i/')===0){{e.preventDefault();auf('/r/'+h.slice(3),h);}}
  else if(h.indexOf('/m/')===0){{e.preventDefault();auf(h,h);}}
 }});
 ovl.addEventListener('click',function(e){{if(e.target===ovl)zu();}});
 document.addEventListener('keydown',function(e){{if(e.key==='Escape')zu();}});
}})();
</script>"""


def lade_registry(pfad: Path = LINK_REGISTRY) -> dict[str, dict[str, str]]:
    if not pfad.exists():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return daten if isinstance(daten, dict) else {}


def speichere_registry(
    daten: dict[str, dict[str, str]], pfad: Path = LINK_REGISTRY
) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")


def owa_link(graph_id: str) -> str:
    return OWA_TEMPLATE.format(id=quote(graph_id, safe=""))


def sicherer_dateiname(name: str) -> str | None:
    """Anhangsname aus der URL → Dateiname ohne Pfadanteile. None, wenn unbrauchbar."""
    name = unicodedata.normalize("NFC", unquote(name))
    if "\x00" in name:
        return None
    rein = Path(name).name
    if not rein or rein in (".", "..") or rein.startswith("/"):
        return None
    return rein


class MailMehrdeutig(LookupError):
    """Eine UID ohne Ordnerangabe kommt in mehreren Ordnern vor.

    Kein Fehlerfall im engeren Sinn, sondern eine Frage an den Menschen: IMAP
    vergibt UIDs je Ordner, dieselbe Zahl steht also fuer verschiedene
    Nachrichten. Wer hier den ersten Treffer ausliefert, zeigt irgendwann die
    falsche Mail — und weil sie plausibel aussieht, faellt es niemandem auf.
    """

    def __init__(self, konto: str, uid: str, ordner: list[str]) -> None:
        super().__init__(f"UID {uid} kommt in {len(ordner)} Ordnern vor")
        self.konto = konto
        self.uid = uid
        self.ordner = ordner


class MailLinkHandler(BaseHTTPRequestHandler):
    server_version = "mail-link-server/1.0"

    # Konfiguration: Klassenattribute, von main() bzw. den Tests gesetzt.
    konten: dict[str, str | None] = {}
    default_konto: str = "hnu"
    ordner: str = "INBOX"
    #: Graph-Konto für /r/ (IIL-Mails im Board-Modal); Token liegt in graph-mail-tokens.
    graph_konto: str = "achim.dehnert@iil.gmbh"
    cache_root: Path = CACHE_ROOT
    registry_pfad: Path = LINK_REGISTRY
    anker_pfad: Path = ANKER_DATEI

    board_root: Path = BOARD_ROOT

    # --- Antwort-Helfer ----------------------------------------------------

    def _sende(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Referrer unterdrücken: der Weiterleitungspfad soll nicht bei Microsoft landen.
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _fehler(self, status: HTTPStatus, text: str) -> None:
        seite = (
            f"<!doctype html><meta charset=utf-8><title>{status.value}</title>"
            f"<body style='font:15px/1.5 sans-serif;max-width:36rem;margin:3rem auto'>"
            f"<h1>{status.value} — {html.escape(status.phrase)}</h1>"
            f"<p>{html.escape(text)}</p>"
            f"<p><a href='/'>Übersicht</a></p>"
        )
        self._sende(status, seite.encode("utf-8"), "text/html; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:
        # Kein Mail-Betreff und keine UID ins Log — das Log ist kein Ort für Postfachinhalt.
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    # --- Routen ------------------------------------------------------------

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_GET(self) -> None:  # noqa: N802
        pfad = self.path.split("?", 1)[0].rstrip("/") or "/"
        teile = [t for t in pfad.split("/") if t]

        if pfad == "/":
            return self._index()
        if teile[0] == "i" and len(teile) == 2:
            return self._weiterleiten(teile[1])
        if teile[0] == "r" and len(teile) == 2:
            return self._graph_rendern(teile[1])
        if teile[0] == "r" and len(teile) == 4 and teile[2] == "anhaenge":
            return self._graph_anhang(teile[1], teile[3])
        if teile[0] == "a":
            return self._anker(teile[1:])
        if teile[0] == "m":
            return self._mail(teile[1:])
        if teile[0] == "d" and len(teile) == 2:
            return self._board(teile[1])
        return self._fehler(HTTPStatus.NOT_FOUND, "Unbekannter Pfad.")

    def _anker(self, teile: list[str]) -> None:
        """`/a/<item>` — Board-Eintrag über seine Message-ID auflösen.

        Der stabile Weg: `/m/<uid>` bricht, sobald die Mail den Ordner wechselt.
        Hier wird bei einem Fehlschlag über die Message-ID nachgesucht, der Anker
        nachgezogen und die Mail trotzdem ausgeliefert.

        Für Graph-Konten (IIL) gibt es keinen IMAP-Anker; dort greift die
        Kurz-ID-Registry. Ohne diesen Rückfall trügen HNU-Posten einen Link und
        IIL-Posten keinen — genau die Lücke, an der die Hälfte des Boards
        unverlinkt blieb. `/a/<nr>` ist damit für jeden Posten dieselbe Adresse,
        unabhängig vom Konto.
        """
        if not teile:
            return self._fehler(HTTPStatus.BAD_REQUEST, "Board-Nummer fehlt.")
        item = teile[0]
        anker = anker_lade(self.anker_pfad)
        eintrag = anker.get(item)
        if not eintrag:
            if lade_registry(self.registry_pfad).get(item):
                return self._weiterleiten(item)
            return self._fehler(
                HTTPStatus.NOT_FOUND, f"Für #{item} ist keine Mail verankert."
            )

        try:
            cfg = parse_env(
                _resolve_config(
                    None,
                    None
                    if eintrag.konto == "default"
                    else self.konten.get(eintrag.konto, eintrag.konto),
                )
            )
            imap = connect(cfg)
        except Exception as fehler:
            return self._fehler(
                HTTPStatus.BAD_GATEWAY, f"Postfach nicht erreichbar: {fehler}"
            )
        try:
            befund = pruefe_anker(imap, eintrag)
            if befund.zustand == GELOESCHT:
                return self._fehler(
                    HTTPStatus.GONE,
                    f"Die Mail zu #{item} liegt in keinem Ordner mehr — "
                    f"zuletzt gesehen in '{eintrag.ordner}'. "
                    "Gelöscht, oder aus dem Postfach entfernt (bei Termineinladungen "
                    "passiert das beim Annehmen).",
                )
            if befund.zustand == UNPRUEFBAR:
                return self._fehler(HTTPStatus.BAD_GATEWAY, befund.hinweis)

            ordner = befund.neuer_ordner or eintrag.ordner
            uid = befund.neue_uid or eintrag.uid
            if befund.zustand == VERSCHOBEN:
                anker[item] = anker_uebernehme([befund], anker)[item]
                anker_speichere(anker, self.anker_pfad)
            imap.select(_mailbox_arg(ordner), readonly=True)
            ziel = self.cache_root / slugify(eintrag.konto) / slugify(ordner)
            datei = render(
                _hole(imap, uid),
                eintrag.konto,
                ordner,
                uid,
                ziel,
                f"/m/{eintrag.konto}/{slugify(ordner_klartext(ordner))}/{uid}",
            )
        except MailNichtGefunden as fehlt:
            return self._fehler(HTTPStatus.NOT_FOUND, str(fehlt))
        except Exception as fehler:
            return self._fehler(
                HTTPStatus.BAD_GATEWAY, f"Postfach nicht lesbar: {fehler}"
            )
        finally:
            try:
                imap.logout()
            except Exception:
                pass
        return self._sende(
            HTTPStatus.OK, datei.read_bytes(), "text/html; charset=utf-8"
        )

    def _board(self, name: str) -> None:
        pfad = board_pfad(name, self.board_root)
        if pfad is None:
            return self._fehler(HTTPStatus.NOT_FOUND, "Kein Board unter diesem Namen.")
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError as e:
            return self._fehler(HTTPStatus.INTERNAL_SERVER_ERROR, f"Nicht lesbar: {e}")
        seite = board_als_html(text, name)
        self._sende(HTTPStatus.OK, seite.encode("utf-8"), "text/html; charset=utf-8")

    def _index(self) -> None:
        eintraege = lade_registry(self.registry_pfad)
        zeilen = (
            "".join(
                f"<li><a href='/i/{html.escape(kurz)}'>/i/{html.escape(kurz)}</a> — "
                f"{html.escape(ziel.get('notiz', 'IIL-Mail'))}</li>"
                for kurz, ziel in sorted(eintraege.items())
            )
            or "<li><em>keine Kurz-Links registriert</em></li>"
        )
        anker_zeilen = (
            "".join(
                f"<li><a href='/a/{html.escape(item)}'>/a/{html.escape(item)}</a> — "
                f"{html.escape(a.betreff[:60])}</li>"
                for item, a in sorted(
                    anker_lade(self.anker_pfad).items(),
                    key=lambda kv: (len(kv[0]), kv[0]),
                )
            )
            or "<li><em>keine Board-Einträge verankert</em></li>"
        )
        konten = ", ".join(sorted(self.konten)) or self.default_konto
        try:
            dateien = sorted(p.stem for p in self.board_root.glob("*.md"))
        except OSError:
            dateien = []
        boards = (
            "".join(
                f"<li><a href='/d/{html.escape(n)}'>/d/{html.escape(n)}</a></li>"
                for n in dateien
                if _BOARD_NAME.match(n)
            )
            or "<li><em>keine Arbeitslisten abgelegt</em></li>"
        )
        seite = f"""<!doctype html><meta charset=utf-8><title>Mail-Links</title>
<body style="font:15px/1.55 -apple-system,Segoe UI,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem">
<h1>Mail-Links</h1>
<p><code>/m/&lt;uid&gt;</code> rendert eine Mail aus <strong>{html.escape(self.default_konto)}</strong>
live über IMAP (read-only). Andere Konten: <code>/m/&lt;konto&gt;/&lt;uid&gt;</code> —
verfügbar: {html.escape(konten)}.</p>
<p>Ein anderer Ordner als {html.escape(self.ordner)} kommt als Segment davor:
<code>/m/&lt;konto&gt;/&lt;ordner&gt;/&lt;uid&gt;</code> — z.B.
<code>/m/hnu/entwuerfe/23254</code>. Der Ordnername ist der Klartext-Slug
(„Entwürfe" → <code>entwuerfe</code>), ein eindeutiger Anfang genügt.</p>
<p><code>/i/&lt;kurz-id&gt;</code> leitet auf den OWA-Deeplink einer IIL-Mail weiter.</p>
<p><code>/a/&lt;board-nummer&gt;</code> löst über die <strong>Message-ID</strong> auf und
überlebt darum ein Verschieben — der Anker wird dabei automatisch nachgezogen.</p>
<h2>Verankerte Board-Einträge</h2><ul>{anker_zeilen}</ul>

<p><code>/d/&lt;name&gt;</code> zeigt eine Arbeitsliste aus <code>~/.claude/boards/</code>.</p>
<h2>Arbeitslisten</h2><ul>{boards}</ul>
<h2>Registrierte Kurz-Links</h2><ul>{zeilen}</ul>
<p style="color:#777;font-size:.85rem">Nur über Loopback erreichbar. Läuft der Zugriff
über einen SSH-Tunnel, sieht niemand sonst diese Inhalte.</p>"""
        self._sende(HTTPStatus.OK, seite.encode("utf-8"), "text/html; charset=utf-8")

    def _weiterleiten(self, kurz: str) -> None:
        if not _KURZ_ID.match(kurz):
            return self._fehler(HTTPStatus.BAD_REQUEST, "Ungültige Kurz-ID.")
        ziel = lade_registry(self.registry_pfad).get(kurz)
        if not ziel:
            return self._fehler(
                HTTPStatus.NOT_FOUND, f"Kurz-ID '{kurz}' ist nicht registriert."
            )
        url = ziel.get("url") or owa_link(ziel.get("graph_id", ""))
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", url)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _graph_rendern(self, kurz: str) -> None:
        """`/r/<kurz-id>` — IIL-Mail read-only über Graph rendern (fürs Board-Modal).

        OWA lässt sich nicht einbetten (Frame-Blocking), darum rendert das Modal
        eine eigene Text-Ansicht. Der OWA-Deeplink bleibt als Absprung erhalten.
        """
        if not _KURZ_ID.match(kurz):
            return self._fehler(HTTPStatus.BAD_REQUEST, "Ungültige Kurz-ID.")
        ziel = lade_registry(self.registry_pfad).get(kurz)
        if not ziel or not ziel.get("graph_id"):
            return self._fehler(
                HTTPStatus.NOT_FOUND, f"Kurz-ID '{kurz}' ist nicht registriert."
            )
        try:
            import graph_mail  # noqa: PLC0415

            cfg = graph_mail.load_cfg()
            tok = graph_mail.token(cfg, self.graph_konto)
        except SystemExit as e:
            return self._fehler(HTTPStatus.SERVICE_UNAVAILABLE, str(e))
        if not tok:
            return self._fehler(
                HTTPStatus.SERVICE_UNAVAILABLE,
                f"{self.graph_konto} nicht angemeldet — graph_mail.py --login nötig.",
            )
        r = graph_mail._http(
            "GET",
            f"{graph_mail.GRAPH}/me/messages/{quote(ziel['graph_id'], safe='')}"
            "?$select=subject,from,toRecipients,receivedDateTime,body,hasAttachments",
            headers=graph_mail._auth(tok),
        )
        if r.status_code != 200:
            return self._fehler(
                HTTPStatus.BAD_GATEWAY, f"Graph antwortet {r.status_code}."
            )
        m = r.json()
        von = (m.get("from") or {}).get("emailAddress", {})
        an = ", ".join(
            e.get("emailAddress", {}).get("address", "")
            for e in m.get("toRecipients", [])
        )
        body = m.get("body") or {}
        text = body.get("content", "")
        if body.get("contentType", "").lower() == "html":
            text = graph_mail._strip_html(text)
        anhang = (
            self._graph_anhang_liste(kurz, ziel["graph_id"], tok)
            if m.get("hasAttachments")
            else ""
        )
        seite = f"""<!doctype html><meta charset=utf-8><title>{html.escape(m.get("subject") or kurz)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<body style="font:14px/1.55 -apple-system,Segoe UI,sans-serif;max-width:52rem;margin:1rem auto;padding:0 1rem">
<style>@media (prefers-color-scheme:dark){{body{{background:#16181c;color:#e6e6e6}}a{{color:#7ab7ff}}}}</style>
<h2 style="margin:.2rem 0">{html.escape(m.get("subject") or "")}</h2>
<p style="color:#777;margin:.2rem 0">Von: {html.escape(von.get("name") or "")} &lt;{html.escape(von.get("address") or "")}&gt;<br>
An: {html.escape(an)}<br>Datum: {html.escape(m.get("receivedDateTime") or "")}</p>
{anhang}<hr>
<div style="white-space:pre-wrap">{html.escape(text)}</div>"""
        self._sende(HTTPStatus.OK, seite.encode("utf-8"), "text/html; charset=utf-8")

    def _graph_anhang_liste(self, kurz: str, graph_id: str, tok: str) -> str:
        """Anhänge einer Graph-Nachricht als klickbare Liste.

        Vorher stand hier nur der Satz "im OWA-Deeplink abrufbar" — auf einem
        Rechner ohne angemeldetes OWA heisst das: gar nicht abrufbar. Der
        IMAP-Zweig liefert Anhänge längst aus (`/m/<uid>/anhaenge/<name>`); der
        Graph-Zweig zog nur nicht nach. Für IIL-Vorgänge blieb damit jeder Anhang
        hinter einer Anzeige, die aussah wie ein Hinweis und wirkte wie eine Wand.

        Eingebettete Nachrichten (`itemAttachment`) werden hier **benannt**, aber
        nicht verlinkt: sie haben keine Bytes, die man ausliefern könnte. Sie
        stumm wegzulassen wäre der schlimmere Fehler — genau so verschwand am
        2026-08-19 ein weitergeleiteter Mailanhang spurlos aus der Ansicht.
        """
        import graph_mail  # noqa: PLC0415

        r = graph_mail._http(
            "GET",
            f"{graph_mail.GRAPH}/me/messages/{quote(graph_id, safe='')}"
            # `@odata.type` gehoert NICHT ins $select — Graph antwortet darauf 400
            # (am 2026-08-19 live gemessen). Die Typangabe kommt ohnehin mit: sie
            # ist eine OData-Annotation, keine Eigenschaft. Und ohne
            # `contentBytes` im $select bleibt die Antwort leicht — sonst zoege
            # jeder Seitenaufruf jeden Anhang komplett nach.
            "/attachments?$select=id,name,size,contentType,isInline",
            headers=graph_mail._auth(tok),
        )
        if r.status_code != 200:
            return (
                "<p style='color:#a60'>📎 Anhänge vorhanden — Abruf scheiterte "
                f"(Graph {r.status_code}).</p>"
            )
        zeilen = []
        for a in r.json().get("value", []):
            name = a.get("name") or "(ohne Namen)"
            if a.get("isInline"):
                continue
            if "itemAttachment" in (a.get("@odata.type") or ""):
                zeilen.append(
                    f"<li>{html.escape(name)} — eingebettete Nachricht, "
                    "nicht als Datei abrufbar</li>"
                )
                continue
            groesse = a.get("size") or 0
            ziel = f"/r/{quote(kurz)}/anhaenge/{quote(name)}"
            zeilen.append(
                f'<li><a href="{html.escape(ziel)}">{html.escape(name)}</a> '
                f"<span style='color:#777'>({groesse // 1024} kB)</span></li>"
            )
        if not zeilen:
            return ""
        return "<p style='color:#a60'>📎 Anhänge</p><ul>" + "".join(zeilen) + "</ul>"

    def _graph_anhang(self, kurz: str, name: str) -> None:
        """`/r/<kurz>/anhaenge/<name>` — einen Anhang ausliefern."""
        if not _KURZ_ID.match(kurz):
            return self._fehler(HTTPStatus.BAD_REQUEST, "Unzulässige Kurz-ID.")
        rein = sicherer_dateiname(name)
        if not rein:
            return self._fehler(HTTPStatus.BAD_REQUEST, "Unzulässiger Anhangsname.")
        ziel = lade_registry(self.registry_pfad).get(kurz)
        if not ziel:
            return self._fehler(HTTPStatus.NOT_FOUND, f"Kurz-ID '{kurz}' unbekannt.")
        try:
            import graph_mail  # noqa: PLC0415

            cfg = graph_mail.load_cfg()
            tok = graph_mail.token(cfg, self.graph_konto)
        except SystemExit as e:
            return self._fehler(HTTPStatus.SERVICE_UNAVAILABLE, str(e))
        if not tok:
            return self._fehler(
                HTTPStatus.SERVICE_UNAVAILABLE,
                f"{self.graph_konto} nicht angemeldet — graph_mail.py --login nötig.",
            )
        r = graph_mail._http(
            "GET",
            f"{graph_mail.GRAPH}/me/messages/{quote(ziel['graph_id'], safe='')}"
            "/attachments",
            headers=graph_mail._auth(tok),
        )
        if r.status_code != 200:
            return self._fehler(
                HTTPStatus.BAD_GATEWAY, f"Graph antwortet {r.status_code}."
            )
        for a in r.json().get("value", []):
            if sicherer_dateiname(a.get("name") or "") != rein:
                continue
            roh = a.get("contentBytes")
            if not roh:
                return self._fehler(
                    HTTPStatus.NOT_FOUND,
                    "Dieser Anhang hat keinen Dateiinhalt (eingebettete Nachricht).",
                )
            return self._sende(
                HTTPStatus.OK,
                base64.b64decode(roh),
                a.get("contentType") or "application/octet-stream",
            )
        return self._fehler(HTTPStatus.NOT_FOUND, "Anhang nicht gefunden.")

    def _auswahl(self, mehrdeutig: MailMehrdeutig) -> None:
        """Welche der gleichnamigen UIDs war gemeint? — der Mensch entscheidet.

        Die Seite verlinkt jeden Kandidaten auf seine **vollqualifizierte** Route.
        Wer einmal geklickt hat, hat damit die eindeutige Adresse in der
        Browserzeile und kann sie zurueck in den Vorgang schreiben.
        """
        zeilen = "".join(
            f"<li><a href='/m/{html.escape(mehrdeutig.konto)}/"
            f"{html.escape(slugify(o))}/{html.escape(mehrdeutig.uid)}'>"
            f"{html.escape(o)}</a></li>"
            for o in mehrdeutig.ordner
        )
        seite = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Welche Nachricht?</title>"
            f"<h1>UID {html.escape(mehrdeutig.uid)} gibt es mehrfach</h1>"
            "<p>IMAP vergibt Nummern je Ordner — diese Zahl steht in mehreren "
            "Ordnern fuer verschiedene Nachrichten. Bitte den gemeinten Ordner "
            "waehlen; der Link darunter ist eindeutig und laesst sich in den "
            "Vorgang zurueckschreiben.</p>"
            f"<ul>{zeilen}</ul>"
        )
        self._sende(
            HTTPStatus.MULTIPLE_CHOICES,
            seite.encode("utf-8"),
            "text/html; charset=utf-8",
        )

    def _mail(self, teile: list[str]) -> None:
        if not teile:
            return self._fehler(HTTPStatus.BAD_REQUEST, "UID fehlt.")
        konto = self.default_konto
        if teile[0] in self.konten:
            konto, teile = teile[0], teile[1:]
        # Ein nicht-numerisches Segment vor der UID ist der Ordner: /m/hnu/entwuerfe/23254.
        # Ohne diese Route war nur INBOX erreichbar — ein Entwurf lag ausserhalb (404).
        ordner_slug = None
        if len(teile) >= 2 and not _UID.match(teile[0]):
            ordner_slug, teile = teile[0], teile[1:]
        if not teile or not _UID.match(teile[0]):
            return self._fehler(HTTPStatus.BAD_REQUEST, "UID muss eine Zahl sein.")
        uid, rest = teile[0], teile[1:]

        try:
            datei = self._rendern(konto, uid, ordner_slug)
        except MailMehrdeutig as mehrdeutig:
            return self._auswahl(mehrdeutig)
        except MailNichtGefunden as fehlt:
            return self._fehler(HTTPStatus.NOT_FOUND, str(fehlt))
        except Exception as fehler:  # Netz/IMAP — dem Browser sagen, was los ist
            return self._fehler(
                HTTPStatus.BAD_GATEWAY, f"Postfach nicht lesbar: {fehler}"
            )

        if not rest:
            return self._sende(
                HTTPStatus.OK, datei.read_bytes(), "text/html; charset=utf-8"
            )
        if len(rest) == 2 and rest[0] == "anhaenge":
            name = sicherer_dateiname(rest[1])
            if not name:
                return self._fehler(HTTPStatus.BAD_REQUEST, "Unzulässiger Anhangsname.")
            anhang = datei.parent / f"{uid}-anhaenge" / name
            if not anhang.is_file():
                return self._fehler(HTTPStatus.NOT_FOUND, "Anhang nicht gefunden.")
            return self._sende(
                HTTPStatus.OK, anhang.read_bytes(), "application/octet-stream"
            )
        return self._fehler(HTTPStatus.NOT_FOUND, "Unbekannter Unterpfad.")

    #: Wo eine UID gesucht wird, wenn der Aufruf keinen Ordner nennt. Bewusst
    #: eine kurze, geordnete Liste statt aller ~120 Ordner: jeder Kandidat kostet
    #: ein SELECT, und die Jahresarchive enthalten keine Nachricht, auf die ein
    #: laufender Vorgang verweist. INBOX zuerst, weil dort der Regelfall liegt.
    UID_SUCHORDNER = (
        "inbox",
        "posteingang",
        "entwuerfe",
        "drafts",
        "gesendete-objekte",
        "gesendete-elemente",
        "sent",
        "sent-items",
        "geloeschte-objekte",
        "geloeschte-elemente",
        "papierkorb",
        "trash",
        "junk-e-mail",
        "junk",
    )

    def _ordner_mit_uid(self, imap, uid: str) -> list[str]:
        """Alle Suchordner, die diese UID fuehren — in der Reihenfolge oben.

        IMAP-UIDs sind **je Ordner** vergeben: dieselbe Zahl bezeichnet in
        INBOX und Entwuerfen zwei verschiedene Nachrichten. Deshalb wird nicht
        beim ersten Treffer abgebrochen, sondern vollstaendig gesammelt. Ein
        Treffer heisst rendern, mehrere heissen **fragen** — und keiner heisst
        sagen, wo gesucht wurde. Stillschweigend den ersten Fund auszuliefern
        waere die bequeme Variante und genau die, die irgendwann die falsche
        Mail zeigt, ohne dass es jemandem auffaellt.

        Gesucht wird mit SEARCH, nicht mit FETCH: das kostet keinen Nachrichten-
        Body und macht die Runde ueber ein Dutzend Ordner bezahlbar.
        """
        namen, _ = alle_ordner(imap)
        nach_slug: dict[str, str] = {}
        for name in namen:
            nach_slug.setdefault(slugify(ordner_klartext(name)), name)
        treffer: list[str] = []
        for slug in self.UID_SUCHORDNER:
            name = nach_slug.get(slug)
            if not name:
                continue
            try:
                typ, _ = imap.select(_mailbox_arg(name), readonly=True)
                if typ != "OK":
                    continue
                typ, data = imap.uid("SEARCH", "UID", str(uid))
            except Exception:
                continue  # ein zickiger Ordner darf die Suche nicht abbrechen
            if typ == "OK" and data and (data[0] or b"").split():
                treffer.append(name)
        return treffer

    def _ordner_aufloesen(self, imap, slug: str) -> str:
        """URL-Slug → echter (kodierter) Ordnername. Wirft MailNichtGefunden.

        Verglichen wird gegen den KLARTEXT-Namen: 'Entw&APw-rfe' heisst im Postfach
        "Entwürfe" und soll als `/entwuerfe/` erreichbar sein, nicht als
        `/entw-apw-rfe/`. Eindeutiger Anfang genuegt (`gesendete` → "Gesendete Elemente").
        """
        namen, _ = alle_ordner(imap)
        paare = [(slugify(ordner_klartext(n)), n) for n in namen]
        genau = [n for s, n in paare if s == slug]
        if genau:
            return genau[0]
        anfang = [n for s, n in paare if s.startswith(slug)]
        if len(anfang) == 1:
            return anfang[0]
        if anfang:
            raise MailNichtGefunden(
                f"Ordner '{slug}' ist nicht eindeutig — gemeint: "
                + ", ".join(sorted(slugify(ordner_klartext(n)) for n in anfang))
            )
        raise MailNichtGefunden(
            f"Ordner '{slug}' gibt es in diesem Postfach nicht — bekannt sind u.a. "
            + ", ".join(sorted(s for s, _ in paare)[:8])
        )

    def _ordner_ohne_angabe(self, imap, konto: str, uid: str) -> str:
        """Der Ordner einer UID, wenn der Aufruf keinen nennt.

        Bis 2026-08-21 war die Antwort schlicht `self.ordner` (INBOX). Das machte
        jede Referenz auf einen Entwurf, eine gesendete oder geloeschte Nachricht
        unverlinkbar — und weil ein toter Link schlechter ist als keiner, blieben
        auf der Vorgangsseite die meisten Nachrichten-Nummern stummer Text. Der
        Preis dafuer stand nicht im Renderer, sondern in der Prosa daneben: wer
        nicht klicken kann, muss erklaeren, was in der Mail steht.
        """
        treffer = self._ordner_mit_uid(imap, uid)
        if len(treffer) == 1:
            return treffer[0]
        if not treffer:
            # Der haeufigste Grund ist KEIN Fehler: eine IMAP-UID gilt nur
            # innerhalb ihres Ordners. Verschiebt jemand die Nachricht — oder
            # sendet einen Entwurf —, bekommt sie im Zielordner eine NEUE
            # Nummer, und die alte existiert nirgends mehr. Real nachgemessen
            # am 2026-08-21: zwei Entwuerfe, im Ledger als UID 23588/23589
            # notiert, lagen nach dem Verschieben als 104322/104323 im
            # Papierkorb. Ohne diesen Satz liest sich der 404 wie ein defektes
            # Werkzeug statt wie eine bewegte Mail.
            raise MailNichtGefunden(
                f"UID {uid} liegt in keinem der durchsuchten Ordner "
                f"({', '.join(self.UID_SUCHORDNER)}). "
                "Haeufigster Grund: die Nachricht wurde verschoben oder gesendet "
                "— eine IMAP-UID gilt nur in ihrem Ordner und wird beim Wechsel "
                "neu vergeben. Der dauerhafte Weg zu einem Vorgang ist /a/<nummer>, "
                "das ueber die Message-ID aufloest."
            )
        raise MailMehrdeutig(konto, uid, [ordner_klartext(n) for n in treffer])

    def _rendern(self, konto: str, uid: str, ordner_slug: str | None = None) -> Path:
        cfg = parse_env(_resolve_config(None, self.konten.get(konto, konto)))
        imap = connect(cfg)
        try:
            if ordner_slug:
                ordner = self._ordner_aufloesen(imap, ordner_slug)
            else:
                ordner = self._ordner_ohne_angabe(imap, konto, uid)
            slug = slugify(ordner_klartext(ordner))
            ziel = self.cache_root / slugify(konto) / slug
            imap.select(_mailbox_arg(ordner), readonly=True)
            # Immer die vollqualifizierte Route als Basis — sie ist von jedem
            # Aufrufpfad aus gueltig, auch von `/a/<nr>`.
            basis = f"/m/{konto}/{slug}/{uid}"
            return render(
                _hole(imap, uid), konto, ordner_klartext(ordner), uid, ziel, basis
            )
        finally:
            try:
                imap.close()
            except Exception:
                pass
            imap.logout()


def cmd_register(args: argparse.Namespace) -> None:
    if not _KURZ_ID.match(args.register):
        sys.exit(
            "FEHLER: Kurz-ID darf nur A-Z a-z 0-9 _ - enthalten (max. 24 Zeichen)."
        )
    registry = lade_registry()
    registry[args.register] = {
        "graph_id": args.graph_id,
        "notiz": args.notiz or "",
    }
    speichere_registry(registry)
    print(f"/i/{args.register} → {owa_link(args.graph_id)[:60]}…")


def konten_aufloesen(angaben: list[str]) -> dict[str, str | None]:
    """`["hnu", "ad=default"]` → `{"hnu": "hnu", "ad": None}`, mit Fail-Fast.

    Ohne diese Prüfung startet der Dienst fröhlich mit einem Konto, dessen Config
    gar nicht existiert, und jede Anfrage endet in einem 502 — gemessen am
    2026-07-29 mit `--account ad` (es gibt kein `~/.claude/mail-ad.env`, das
    AD-Postfach liegt in der namenlosen `mail.env`).
    """
    aufgeloest: dict[str, str | None] = {}
    for angabe in angaben:
        route, trenner, konfig = angabe.partition("=")
        if not trenner:
            konfig_name: str | None = route  # --account hnu → mail-hnu.env
        elif konfig == "default":
            konfig_name = None  # --account ad=default → mail.env
        else:
            konfig_name = konfig  # --account privat=search → mail-search.env
        pfad = _resolve_config(None, konfig_name)
        if not pfad.exists():
            vorhanden = sorted(
                p.name for p in (Path.home() / ".claude").glob("mail*.env")
            )
            sys.exit(
                f"FEHLER: Konto '{route}' verweist auf {pfad}, die es nicht gibt.\n"
                f"Vorhanden: {', '.join(vorhanden) or '(keine)'}\n"
                "Für das Postfach in der namenlosen mail.env: --account "
                f"{route}=default"
            )
        aufgeloest[route] = konfig_name
    return aufgeloest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument(
        "--ich-weiss-was-ich-tue",
        action="store_true",
        help="Bindung an eine andere Adresse als 127.0.0.1 zulassen (dann Auth davorschalten!)",
    )
    ap.add_argument("--default-account", default="hnu")
    ap.add_argument(
        "--account",
        action="append",
        default=[],
        metavar="ROUTE[=KONFIG]",
        help="zusätzliches Konto freischalten (mehrfach möglich). 'ad=default' bedient "
        "/m/ad/ aus ~/.claude/mail.env — das Konto ohne Namensteil.",
    )
    ap.add_argument("--folder", default="INBOX")
    ap.add_argument(
        "--graph-account",
        default="achim.dehnert@iil.gmbh",
        help="Graph-Konto, mit dem /r/<kurz-id> IIL-Mails rendert",
    )
    ap.add_argument(
        "--register", metavar="KURZ-ID", help="Kurz-Link anlegen statt Server starten"
    )
    ap.add_argument("--graph-id", help="zu --register: Graph-id der IIL-Mail")
    ap.add_argument(
        "--notiz", help="zu --register: kurze Beschreibung für die Übersicht"
    )
    ap.add_argument(
        "--list-links", action="store_true", help="registrierte Kurz-Links zeigen"
    )
    args = ap.parse_args()

    if args.list_links:
        for kurz, ziel in sorted(lade_registry().items()):
            print(f"/i/{kurz}\t{ziel.get('notiz', '')}")
        return
    if args.register:
        if not args.graph_id:
            sys.exit("FEHLER: --register braucht --graph-id.")
        return cmd_register(args)

    if (
        args.host not in ("127.0.0.1", "localhost", "::1")
        and not args.ich_weiss_was_ich_tue
    ):
        sys.exit(
            f"FEHLER: --host {args.host} würde Mail-Inhalte über das Netz ausliefern.\n"
            "Der Dienst hat keine Authentifizierung. Gedacht ist er für einen SSH-Tunnel:\n"
            f"  ssh -N -L {args.port}:127.0.0.1:{args.port} devuser@<server>\n"
            "Wenn du wirklich öffentlich binden willst, schalte eine Auth davor und setze\n"
            "--ich-weiss-was-ich-tue."
        )

    konten = konten_aufloesen([args.default_account, *args.account])
    MailLinkHandler.konten = konten
    MailLinkHandler.default_konto = args.default_account
    MailLinkHandler.ordner = args.folder
    MailLinkHandler.graph_konto = args.graph_account

    with ThreadingHTTPServer((args.host, args.port), MailLinkHandler) as srv:
        print(
            f"Mail-Links auf http://{args.host}:{args.port}/  (Konten: {', '.join(konten)})"
        )
        print(f"Tunnel:  ssh -N -L {args.port}:127.0.0.1:{args.port} devuser@<server>")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nbeendet.")


if __name__ == "__main__":
    main()
