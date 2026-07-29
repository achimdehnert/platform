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

#: Aus einer Graph-`id` wird der OWA-Deeplink so gebaut (belegt: funktioniert im Board).
OWA_TEMPLATE = (
    "https://outlook.office365.com/owa/?ItemID={id}&exvsurl=1&viewmodel=ReadMessageItem"
)

_UID = re.compile(r"^\d+$")
_KURZ_ID = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


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


class MailLinkHandler(BaseHTTPRequestHandler):
    server_version = "mail-link-server/1.0"

    # Konfiguration: Klassenattribute, von main() bzw. den Tests gesetzt.
    konten: dict[str, str | None] = {}
    default_konto: str = "hnu"
    ordner: str = "INBOX"
    cache_root: Path = CACHE_ROOT
    registry_pfad: Path = LINK_REGISTRY

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
        if teile[0] == "m":
            return self._mail(teile[1:])
        return self._fehler(HTTPStatus.NOT_FOUND, "Unbekannter Pfad.")

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
        konten = ", ".join(sorted(self.konten)) or self.default_konto
        seite = f"""<!doctype html><meta charset=utf-8><title>Mail-Links</title>
<body style="font:15px/1.55 -apple-system,Segoe UI,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem">
<h1>Mail-Links</h1>
<p><code>/m/&lt;uid&gt;</code> rendert eine Mail aus <strong>{html.escape(self.default_konto)}</strong>
live über IMAP (read-only). Andere Konten: <code>/m/&lt;konto&gt;/&lt;uid&gt;</code> —
verfügbar: {html.escape(konten)}.</p>
<p><code>/i/&lt;kurz-id&gt;</code> leitet auf den OWA-Deeplink einer IIL-Mail weiter.</p>
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

    def _mail(self, teile: list[str]) -> None:
        if not teile:
            return self._fehler(HTTPStatus.BAD_REQUEST, "UID fehlt.")
        konto = self.default_konto
        if teile[0] in self.konten:
            konto, teile = teile[0], teile[1:]
        if not teile or not _UID.match(teile[0]):
            return self._fehler(HTTPStatus.BAD_REQUEST, "UID muss eine Zahl sein.")
        uid, rest = teile[0], teile[1:]

        try:
            datei = self._rendern(konto, uid)
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

    def _rendern(self, konto: str, uid: str) -> Path:
        cfg = parse_env(_resolve_config(None, self.konten.get(konto, konto)))
        ziel = self.cache_root / slugify(konto) / slugify(self.ordner)
        imap = connect(cfg)
        try:
            imap.select(_mailbox_arg(self.ordner), readonly=True)
            return render(_hole(imap, uid), konto, self.ordner, uid, ziel)
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
