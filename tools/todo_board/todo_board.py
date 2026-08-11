#!/usr/bin/env python3
"""Persistente Arbeitsliste — baut aus dem Vorgangs-Ledger eine HTML-Seite und serviert sie.

Warum es das gibt: `/mailcheck` erhebt den Stand offener Vorgaenge und schreibt ihn
nach `~/.claude/mail-vorgaenge.json`. Bisher war das Board fluechtig — es stand in
einer Chat-Antwort und war beim naechsten Fenster weg, waehrend Fristen (AV-Pruefung,
Angebotsfrist, DSGVO-Monatsfrist) genau dort schlummerten, wo niemand hinsieht.
Dieser Dienst macht denselben Zustand dauerhaft sichtbar.

    todo_board.py build            → schreibt ~/.claude/boards/todo.html
    todo_board.py serve            → 127.0.0.1:8789, baut bei jedem Abruf neu

Bewusst getrennt von `mail_agent/mail_link_server.py`: der rendert Mail-Koerper live
aus dem Postfach und darf darum nie oeffentlich stehen. Dieser Dienst kennt nur das
Ledger, spricht kein IMAP und hat genau eine Seite — das ist die Angriffsflaeche, die
hinter Cloudflare Access vertretbar ist.

Das Ledger enthaelt Klarnamen von Mandanten und Betreffs aus laufenden Vorgaengen.
Der Dienst bindet darum auf Loopback und verlangt fuer jede andere Adresse ein
ausdrueckliches `--oeffentlich-hinter-auth`. Wer das setzt, ohne eine
Authentifizierung davorzuhaengen, legt Mandantendaten offen.

Quelle bleibt das Ledger. Dieses Werkzeug schreibt nie hinein.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
AUSGABE = Path.home() / ".claude" / "boards" / "todo.html"
PORT = 8789
# Ab wie vielen Tagen ohne Erhebung die Seite ihren eigenen Stand in Frage stellt.
FRISCH_TAGE = 2

# Reihenfolge der Abschnitte = Reihenfolge der Dringlichkeit. Leere entfallen.
BUCKETS = (
    ("owner", "Dein Zug", "Entscheidung, Berechtigung oder Inhalt, den nur du hast"),
    ("agent", "Ich kann sofort", "Braucht kein Gate — sag zu, dann laeuft es"),
    ("warten", "Wartet auf andere", "Der naechste Zug kommt von aussen"),
)
KONTO_LABEL = {"iil": "IIL", "hnu": "HNU", "ad": "Mittwald", "": "—"}

#: Basis fuer Mail-Links. Der Board-Dienst haengt an todo.iil.pet (Port 8789), der
#: Mail-Renderer an mail.iil.pet (Port 8787) — ein relativer Pfad zeigt also ins
#: Leere. Im Ledger steht deshalb nur der PFAD (`/a/118`), der Host kommt von hier
#: und ist fuer lokale Laeufe ueberschreibbar. Host im Datenbestand waere Drift.
MAIL_BASIS = os.environ.get("TODO_BOARD_MAIL_BASIS", "https://mail.iil.pet").rstrip("/")

#: Verankerungs-Index des Mail-Dienstes: welche Board-Nummer ueberhaupt auf eine
#: Mail zeigt. Nur gelesen — geschrieben wird die Datei von `mail_link_server.py`.
ANKER_DATEI = Path.home() / ".claude" / "mail-anker.json"


def anker_nummern(pfad: Path = ANKER_DATEI) -> frozenset[str]:
    """Welche Nummern hat der Mail-Dienst verankert?

    Warum das Board diese Datei ueberhaupt liest: `/a/<nr>` ist fuer jeden Posten
    dieselbe Adresse, die Nummer steht ohnehin im Ledger — die Verlinkung liesse
    sich also blind aus `nr` ableiten. Gemessen am 2026-08-11 waeren das aber
    **14 von 18 Links, die zuverlaessig 404 liefern**: verankert sind nur 109,
    110, 115, 118. Ein Link, der verlaesslich ins Leere fuehrt, ist schlechter
    als der ehrliche Hinweis "keine Mail verknuepft" (#1875). Darum die Probe.

    Bewusst nur diese eine Datei: das Board spricht weiterhin kein IMAP und
    kennt keinen Postfachinhalt — es liest ausschliesslich, welche Nummern
    aufloesbar sind. Fehlt oder bricht die Datei, faellt die Verlinkung auf den
    Bestandsweg zurueck (nur ausdrueckliches `mail_ref`), statt zu scheitern.
    """
    try:
        with pfad.open(encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return frozenset()
    return frozenset(str(k) for k in daten) if isinstance(daten, dict) else frozenset()


def mail_ziel(
    v: dict, mail_basis: str = MAIL_BASIS, anker: frozenset[str] | None = None
) -> str | None:
    """Die URL zur Mail dieses Vorgangs — oder None, wenn keine erreichbar ist.

    Zwei Wege, in dieser Reihenfolge:
    1. ausdrueckliches `mail_ref` im Ledger (Bestandsweg, gewinnt immer),
    2. Ableitung `/a/<nr>` — aber nur, wenn die Nummer wirklich verankert ist.

    Weg 2 loest den Handgriff ab, mit dem `/mailcheck` `mail_ref` bisher von Hand
    nachtrug (K1 aus #1869): neue Vorgaenge tragen ihren Link, sobald der
    Mail-Dienst sie kennt — ohne dass jemand daran denken muss.
    """
    ref = str(v.get("mail_ref") or "").strip()
    if ref:
        # Nur serverseitige Pfade akzeptieren. Ein absoluter Wert im Ledger waere
        # ein offener Weiterleitungspunkt — der Ledger speist sich aus fremden Mails.
        # Ist der Wert unbrauchbar, gibt es KEIN Ziel: auf die Nummer auszuweichen
        # wuerde einen vergifteten Eintrag stillschweigend heilen und die Zeile
        # unauffaellig machen, die gerade auffallen soll.
        return f"{mail_basis}{ref}" if ref.startswith("/") and ref[1:2] != "/" else None
    nr = v.get("nr")
    if nr in (None, ""):
        return None
    verankert = anker_nummern() if anker is None else anker
    return f"{mail_basis}/a/{quote(str(nr), safe='')}" if str(nr) in verankert else None


def heute() -> date:
    return date.today()


def lade(pfad: Path) -> dict:
    if not pfad.exists():
        sys.exit(f"FEHLER: Ledger {pfad} fehlt — erst /mailcheck laufen lassen.")
    with pfad.open(encoding="utf-8") as fh:
        return json.load(fh)


def frist_tage(v: dict, stichtag: date) -> int | None:
    """Resttage bis zur Frist; None, wenn der Vorgang keine traegt."""
    roh = v.get("frist")
    if not roh:
        return None
    try:
        return (datetime.strptime(roh, "%Y-%m-%d").date() - stichtag).days
    except ValueError:
        # Ein unlesbares Datum ist ein Befund, kein Grund, die Seite abstuerzen zu
        # lassen — es faellt in der Ausgabe als "?" auf.
        return None


def ampel(tage: int | None) -> tuple[str, str]:
    """(CSS-Klasse, Text) fuer die Fristenspalte."""
    if tage is None:
        return "keine", "—"
    if tage < 0:
        return "rot", f"{abs(tage)} Tage ueberfaellig"
    if tage == 0:
        return "rot", "heute"
    if tage <= 3:
        return "rot", f"in {tage} Tagen"
    if tage <= 10:
        return "gelb", f"in {tage} Tagen"
    return "gruen", f"in {tage} Tagen"


def sortschluessel(v: dict, stichtag: date) -> tuple[int, int, str]:
    """Fristen zuerst, aufsteigend; Fristlose danach, alphabetisch."""
    tage = frist_tage(v, stichtag)
    return (1, 0, v.get("thread_key", "")) if tage is None else (0, tage, "")


def zeile(
    v: dict,
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: frozenset[str] | None = None,
) -> str:
    tage = frist_tage(v, stichtag)
    klasse, text = ampel(tage)
    konto = KONTO_LABEL.get(v.get("konto", ""), v.get("konto", "—"))
    frist = v.get("frist") or ""
    schluessel = v.get("thread_key", "")
    beschriftung = html.escape(schluessel or "—")
    # Ohne thread_key gibt es kein Ziel — dann bleibt es Text statt totem Link.
    sache = (
        f"<a href='{html.escape(basis)}/t/{quote(schluessel, safe='')}'>{beschriftung}</a>"
        if schluessel
        else beschriftung
    )
    # Die Nummer ist die ID aus dem Ledger, kein Laufindex je Abschnitt: sie bleibt
    # ueber Bucket-Wechsel und ueber Tage hinweg dieselbe und ist genau die Nummer,
    # unter der die Mail als `/a/<nr>` erreichbar ist. Ein Laufindex wuerde springen.
    nr = v.get("nr")
    nr_text = html.escape(str(nr)) if nr not in (None, "") else "—"
    # Der Mail-Link steht schon in der Uebersicht, nicht erst auf der Vorgangsseite:
    # der Weg zur Mail soll keinen Zwischenklick kosten (#1869).
    ziel = mail_ziel(v, mail_basis, anker)
    mail = (
        f" <a class='maillink' href='{html.escape(ziel)}' target='_blank' "
        f"rel='noreferrer' aria-label='Mail zu #{nr_text} oeffnen' "
        f"title='Mail oeffnen'>&#9993;</a>"
        if ziel
        else ""
    )
    return (
        "<tr>"
        f"<td class='nr'>{nr_text}</td>"
        f"<td class='sache'>{sache}{mail}"
        f"<span class='wer'>{html.escape(v.get('gegenueber', ''))}</span></td>"
        f"<td class='konto'>{html.escape(konto)}</td>"
        f"<td class='frist {klasse}'>{html.escape(text)}"
        f"<span class='datum'>{html.escape(frist)}</span></td>"
        f"<td class='schritt'>{html.escape(v.get('kurz') or v.get('next_trigger', ''))}</td>"
        "</tr>"
    )


def abschnitt(
    titel: str,
    unter: str,
    posten: list[dict],
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: frozenset[str] | None = None,
) -> str:
    if not posten:
        return ""
    zeilen = "".join(
        zeile(v, stichtag, basis, mail_basis, anker)
        for v in sorted(posten, key=lambda x: sortschluessel(x, stichtag))
    )
    return f"""<section>
<h2>{html.escape(titel)} <span class='zahl'>{len(posten)}</span></h2>
<p class='unter'>{html.escape(unter)}</p>
<table><thead><tr><th>#</th><th>Sache</th><th>Konto</th><th>Frist</th>
<th>Naechster Schritt</th></tr></thead>
<tbody>{zeilen}</tbody></table>
</section>"""


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a19;--stumm:#6b6b66;--linie:#e3e3df;--karte:#fff;
--rot:#b3261e;--gelb:#8a6100;--gruen:#2c6b3f}
:root:not([data-theme=light]){}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16171a;--fg:#e8e8e6;--stumm:#9a9a95;--linie:#2c2e33;--karte:#1e2024;
--rot:#f2836f;--gelb:#e0b341;--gruen:#7fc79a}}
:root[data-theme=dark]{--bg:#16171a;--fg:#e8e8e6;--stumm:#9a9a95;--linie:#2c2e33;
--karte:#1e2024;--rot:#f2836f;--gelb:#e0b341;--gruen:#7fc79a}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--fg);
font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:60rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .25rem}
.nr-marke{color:var(--stumm);font-weight:400;font-variant-numeric:tabular-nums}
.stand{color:var(--stumm);font-size:.85rem;margin:0 0 2rem}
section{background:var(--karte);border:1px solid var(--linie);border-radius:10px;
padding:1.1rem 1.25rem;margin-bottom:1.25rem}
h2{font-size:1.05rem;margin:0;display:flex;align-items:center;gap:.5rem}
.zahl{font-size:.75rem;font-weight:600;color:var(--stumm);border:1px solid var(--linie);
border-radius:999px;padding:.05rem .5rem}
.unter{color:var(--stumm);font-size:.82rem;margin:.2rem 0 .9rem}
.tabellenrahmen,section{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
color:var(--stumm);font-weight:600;padding:0 .6rem .4rem 0;border-bottom:1px solid var(--linie)}
td{padding:.6rem .6rem .6rem 0;border-bottom:1px solid var(--linie);vertical-align:top}
tr:last-child td{border-bottom:none}
.nr{color:var(--stumm);font-variant-numeric:tabular-nums;white-space:nowrap;
width:2.5rem;font-size:.85rem}
.sache{font-weight:500;min-width:14rem}
a.maillink{text-decoration:none;border-bottom:none;color:var(--stumm);
margin-left:.35rem;font-size:.95rem}
a.maillink:hover{color:var(--fg)}
.wer{display:block;font-weight:400;font-size:.78rem;color:var(--stumm);margin-top:.15rem}
.konto{color:var(--stumm);white-space:nowrap}
.frist{white-space:nowrap;font-variant-numeric:tabular-nums}
.frist .datum{display:block;font-size:.72rem;color:var(--stumm)}
.frist.rot{color:var(--rot);font-weight:600}
.frist.gelb{color:var(--gelb);font-weight:600}
.frist.gruen{color:var(--gruen)}
.frist.keine{color:var(--stumm)}
.schritt{color:var(--fg)}
.alt{background:var(--karte);border:1px solid var(--rot);border-left-width:4px;
border-radius:8px;color:var(--rot);font-size:.88rem;padding:.7rem .9rem;margin:0 0 1.25rem}
footer{color:var(--stumm);font-size:.78rem;margin-top:2rem;text-align:center}
.schritt-text{margin:.4rem 0 .6rem}
.aktionen{display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 0}
a.aktion{display:inline-block;padding:.35rem .7rem;border:1px solid var(--linie);
border-radius:6px;background:var(--karte);text-decoration:none;font-size:.86rem}
a.aktion:hover{border-color:var(--stumm)}
.kein-ziel{color:var(--stumm);font-size:.84rem;font-style:italic;margin:.2rem 0 0}
.sache a{color:inherit;text-decoration:none;border-bottom:1px solid var(--linie)}
.sache a:hover{border-bottom-color:currentColor}
pre.notiz{white-space:pre-wrap;word-break:break-word;font-size:.85rem;line-height:1.5;
background:var(--karte);border:1px solid var(--linie);border-radius:6px;padding:.8rem}
"""


def frische_banner(daten: dict, stichtag: date) -> str:
    """Sagt an, wenn die Erhebung veraltet ist — Schweigen waere hier gefaehrlich.

    Die Seite baut bei jedem Abruf neu und sieht darum immer frisch aus, auch
    wenn der naechtliche /mailcheck seit Tagen scheitert. Eine Liste, die
    stillschweigend eine Woche alten Stand zeigt, ist schlimmer als keine:
    sie beruhigt, waehrend eine Frist laeuft.
    """
    roh = daten.get("letzte_pruefung")
    if not roh:
        return "<p class='alt'>Kein Erhebungsdatum im Ledger — Stand unbekannt.</p>"
    try:
        alter = (stichtag - datetime.strptime(str(roh), "%Y-%m-%d").date()).days
    except ValueError:
        return f"<p class='alt'>Erhebungsdatum '{html.escape(str(roh))}' unlesbar.</p>"
    if alter <= FRISCH_TAGE:
        return ""
    return (
        f"<p class='alt'>Diese Liste ist {alter} Tage alt. Der naechtliche "
        f"/mailcheck hat sie seit dem {html.escape(str(roh))} nicht "
        "fortgeschrieben — neue Antworten und Fristen fehlen moeglicherweise.</p>"
    )


# Overlay nach dem Muster von tools/mail_agent/mail_link_server.py (dort Z. 126-154).
# Fällt ohne JavaScript auf einen normalen Seitenwechsel zurück: der Link im Markup
# ist ein echter Link, das Skript fängt ihn nur ab.
OVERLAY = """
<div id=ovl style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9">
 <div id=ovl-box style="position:absolute;inset:4% 6%;background:#fff;border-radius:10px;
  overflow:hidden;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.4)">
  <div style="padding:.45rem .9rem;display:flex;justify-content:flex-end;gap:1.2rem;
   border-bottom:1px solid #d0d0d0;font-size:.9rem">
   <a id=ovl-ext href="#" target=_blank rel=noreferrer>in neuem Tab oeffnen &#8599;</a>
   <a href="#" id=ovl-x>&#10005; schliessen (Esc)</a>
  </div>
  <iframe id=ovl-frame title="Vorgang" style="border:0;flex:1;width:100%"></iframe>
 </div>
</div>
<style>@media (prefers-color-scheme:dark){#ovl-box{background:#1e2024}
 #ovl-box>div{border-color:#2c2e33}}</style>
<script>
(function(){
 var ovl=document.getElementById('ovl'),fr=document.getElementById('ovl-frame'),
     ext=document.getElementById('ovl-ext');
 function zu(){ovl.style.display='none';fr.src='about:blank';}
 function auf(src){fr.src=src;ext.href=src;ovl.style.display='block';}
 document.addEventListener('click',function(e){
  var a=e.target.closest('a');if(!a)return;
  var h=a.getAttribute('href')||'';
  if(a.id==='ovl-x'){e.preventDefault();zu();return;}
  if(a===ext)return;
  /* NUR eigene Vorgangsseiten. Mail-Links gehen bewusst NICHT ins Overlay:
     mail.iil.pet steht hinter Cloudflare Access, und Access leitet auf
     iil-team.cloudflareaccess.com um, das `frame-ancestors 'none'` sendet.
     Am 2026-08-11 im Browser gemessen — das Overlay oeffnete sich und zeigte
     "hat die Verbindung abgelehnt". Ein Rahmen, der verlaesslich leer bleibt,
     ist schlechter als ein neuer Tab; die Mail-Links tragen darum target=_blank.
     Wieder moeglich waere das Modal erst, wenn beide Dienste unter DERSELBEN
     Adresse haengen (Pfad-Mount im Tunnel) — siehe #1869. */
  if(h.indexOf('/t/')>=0){e.preventDefault();auf(h);}
 });
 ovl.addEventListener('click',function(e){if(e.target===ovl)zu();});
 document.addEventListener('keydown',function(e){if(e.key==='Escape')zu();});
})();
</script>"""


def aktionen(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: frozenset[str] | None = None,
) -> list[tuple]:
    """Naechste Schritte als Ziele — ausschliesslich anzeigend.

    Bewusste Grenze (#1869): hier entsteht KEIN Knopf, der etwas ausloest. Senden,
    Buchen, Loeschen bleiben aussen vor, und es gibt keinen Rueckkanal, ueber den die
    Seite einen Agenten beauftragen koennte — Kommandokanal ist allein die
    interaktive Sitzung (Lotsen-Charta Art. 1). Wer hier spaeter einen POST ergaenzt,
    hebt genau diese Zusage auf.

    Rueckgabe: Liste aus (Beschriftung, Ziel-URL). Leere Liste heisst: kein Ziel
    ableitbar — der Aufrufer zeigt dann den `next_trigger`-Text, keinen toten Knopf.
    """
    del basis  # noch kein Ziel, das die Board-Basis braucht — siehe unten
    ziele: list[tuple] = []
    ziel = mail_ziel(v, mail_basis, anker)
    if ziel:
        ziele.append(("Mail oeffnen", ziel))
    # Bewusst KEIN Selbstlink auf `/t/<thread_key>`: die Vorgangsseite ist genau das
    # Ziel, auf dem dieser Abschnitt steht. Er waere ausserdem der einzige Grund,
    # warum Bestandsvorgaenge ohne `mail_ref` ploetzlich einen Knopf trugen.
    # „Antwort entwerfen" fehlt hier absichtlich: der Mail-Dienst hat keinen
    # Entwurfs-Endpunkt, und einen zu bauen waere ein Schreibpfad — in #1869
    # ausdruecklich out of scope.
    return ziele


def naechste_schritte(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: frozenset[str] | None = None,
) -> str:
    """Abschnitt 'Naechste Schritte': der Text aus dem Ledger plus erreichbare Ziele."""
    text = str(v.get("next_trigger") or "").strip()
    ziele = aktionen(v, mail_basis, basis, anker)
    kopf = f"<p class='schritt-text'>{html.escape(text)}</p>" if text else ""
    # Ohne Ziel bleibt der Vorschlag Text. Ein Knopf ohne Ziel waere genau der tote
    # Link, den `zeile()` beim fehlenden thread_key schon vermeidet.
    if ziele:
        rest = (
            "<p class='aktionen'>"
            + " ".join(
                f"<a class='aktion' href='{html.escape(url)}' target='_blank' "
                f"rel='noreferrer'>{html.escape(label)}</a>"
                for label, url in ziele
            )
            + "</p>"
        )
    else:
        # Die Luecke benennen statt sie zu verschweigen: am 2026-08-10 trugen 13 von
        # 17 Vorgaengen keinen Anker, und eine leere Stelle sieht aus wie ein
        # kaputter Link. Der Hinweis trennt "nichts hinterlegt" von "defekt" — und
        # zeigt nebenbei, wo /mailcheck noch nachzutragen hat.
        rest = "<p class='kein-ziel'>keine Mail verknuepft</p>"
    return f"<h2>Naechste Schritte</h2>{kopf}{rest}"


# Reihenfolge der Detailfelder: erst wer und was, dann Zustand, zuletzt der Verlauf.
DETAIL_FELDER = (
    ("gegenueber", "Gegenueber"),
    ("konto", "Konto"),
    ("typ", "Typ"),
    ("zustand", "Zustand"),
    ("frist", "Frist"),
    ("bucket", "Bucket"),
    ("angelegt", "Angelegt"),
    ("letzte_pruefung", "Zuletzt geprueft"),
    ("next_trigger", "Naechster Schritt"),
)


def detail(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: frozenset[str] | None = None,
) -> str:
    """Ein einzelner Vorgang als eigenstaendige Seite — auch ohne Overlay lesbar."""
    zeilen = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(v.get(feld) or '—'))}</td></tr>"
        for feld, label in DETAIL_FELDER
    )
    schritte = naechste_schritte(v, mail_basis, basis, anker)
    nr = v.get("nr")
    # Dieselbe Nummer wie in der Uebersicht — sie ist der Wiedererkennungsanker
    # zwischen Liste, Chat-Board und Mail-Adresse `/a/<nr>`.
    nr_marke = (
        f"<span class='nr-marke'>#{html.escape(str(nr))}</span> "
        if nr not in (None, "")
        else ""
    )
    notiz = html.escape(str(v.get("notiz") or "")).replace(" | ", "\n\n")
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{html.escape(v.get("thread_key", "Vorgang"))}</title><style>{CSS}</style></head>
<body><main>
<h1>{nr_marke}{html.escape(v.get("thread_key", "Vorgang"))}</h1>
<p class="stand">{html.escape(v.get("kurz") or "")}</p>
<table><tbody>{zeilen}</tbody></table>
{schritte}
<h2>Verlauf</h2>
<pre class="notiz">{notiz or "—"}</pre>
<footer>Quelle: mail-vorgaenge.json</footer>
</main></body></html>"""


def baue(
    daten: dict,
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: frozenset[str] | None = None,
) -> str:
    posten = daten.get("vorgaenge", [])
    # Einmal je Seitenaufbau lesen statt einmal je Zeile: die Datei aendert sich
    # waehrend eines Aufbaus nicht, und 18 Dateizugriffe fuer 18 Zeilen waeren
    # Verschwendung. `None` heisst hier "noch nicht geladen", nicht "leer".
    if anker is None:
        anker = anker_nummern()
    nach_bucket: dict[str, list[dict]] = {k: [] for k, _, _ in BUCKETS}
    # Ein Vorgang ohne bekannten Bucket verschwindet nicht — er landet sichtbar
    # bei "Dein Zug", damit eine fehlende Klassifikation auffaellt statt zu schweigen.
    for v in posten:
        schluessel = v.get("bucket")
        nach_bucket[schluessel if schluessel in nach_bucket else "owner"].append(v)
    abschnitte = "".join(
        abschnitt(t, u, nach_bucket.get(k, []), stichtag, basis, mail_basis, anker)
        for k, t, u in BUCKETS
    )
    geprueft = html.escape(str(daten.get("letzte_pruefung", "unbekannt")))
    faellig = sum(
        1 for v in posten if (d := frist_tage(v, stichtag)) is not None and d <= 3
    )
    warnung = (
        f" · <strong>{faellig} in den naechsten 3 Tagen faellig</strong>"
        if faellig
        else ""
    )
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Arbeitsliste</title><style>{CSS}</style></head>
<body><main>
<h1>Arbeitsliste</h1>
<p class="stand">{len(posten)} offene Vorgaenge · Erhebung vom {geprueft}{warnung}</p>
{frische_banner(daten, stichtag)}
{abschnitte}
<footer>Quelle: mail-vorgaenge.json · gebaut {html.escape(stichtag.isoformat())} ·
fortgeschrieben durch /mailcheck</footer>
</main>{OVERLAY}</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "todo-board"

    def _sende(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Pfade und Query-Strings koennten Vorgangsnamen tragen — nicht ins Log.
        sys.stderr.write(
            f"{self.address_string()} {self.command} {args[1] if len(args) > 1 else ''}\n"
        )

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _vorgang(self, schluessel: str) -> None:
        """Einen Vorgang ausliefern. Der Schluessel wird gegen das Ledger geprueft,
        nicht gegen das Dateisystem — es gibt hier keinen Pfad, der entgleiten kann."""
        try:
            daten = lade(LEDGER)
        except (OSError, json.JSONDecodeError) as exc:
            body = (
                f"<h1>Ledger nicht lesbar</h1><p>{html.escape(str(exc))}</p>".encode()
            )
            self._sende(
                HTTPStatus.INTERNAL_SERVER_ERROR, body, "text/html; charset=utf-8"
            )
            return
        for v in daten.get("vorgaenge", []):
            if v.get("thread_key") == schluessel and schluessel:
                self._sende(
                    HTTPStatus.OK, detail(v).encode("utf-8"), "text/html; charset=utf-8"
                )
                return
        self._sende(
            HTTPStatus.NOT_FOUND,
            b"Diesen Vorgang gibt es nicht.\n",
            "text/plain; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        pfad = self.path.split("?", 1)[0].rstrip("/") or "/"
        if pfad == "/healthz":
            self._sende(HTTPStatus.OK, b"ok\n", "text/plain; charset=utf-8")
            return
        if pfad.startswith("/t/"):
            self._vorgang(unquote(pfad[3:]))
            return
        if pfad != "/":
            self._sende(
                HTTPStatus.NOT_FOUND, b"nicht gefunden\n", "text/plain; charset=utf-8"
            )
            return
        try:
            seite = baue(lade(LEDGER), heute())
        except (OSError, json.JSONDecodeError) as exc:
            # Ein kaputtes Ledger darf nicht als leere, beruhigende Liste erscheinen.
            body = (
                f"<h1>Ledger nicht lesbar</h1><p>{html.escape(str(exc))}</p>".encode()
            )
            self._sende(
                HTTPStatus.INTERNAL_SERVER_ERROR, body, "text/html; charset=utf-8"
            )
            return
        self._sende(HTTPStatus.OK, seite.encode("utf-8"), "text/html; charset=utf-8")


def cmd_build(args: argparse.Namespace) -> None:
    ziel = Path(args.ausgabe).expanduser()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    # Die gebaute Datei wird als Datei geoeffnet — relative Links zeigten dann ins
    # Dateisystem. Darum absolute Loopback-Adresse, nie file:// (Owner-Entscheid).
    ziel.write_text(
        baue(lade(LEDGER), heute(), basis=f"http://127.0.0.1:{args.basis_port}"),
        encoding="utf-8",
    )
    print(f"OK: {ziel}")


def cmd_serve(args: argparse.Namespace) -> None:
    if args.bind != "127.0.0.1" and not args.oeffentlich_hinter_auth:
        sys.exit(
            f"FEHLER: --bind {args.bind} verweigert. Das Ledger traegt Mandanten- und\n"
            "Pruefungsdaten. Nur mit vorgelagerter Authentifizierung (Cloudflare Access,\n"
            "Tunnel-only) und dann mit --oeffentlich-hinter-auth."
        )
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"Arbeitsliste auf http://{args.bind}:{args.port}/ — Strg-C beendet.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="HTML-Datei schreiben")
    b.add_argument("--ausgabe", default=str(AUSGABE))
    b.add_argument("--basis-port", type=int, default=PORT, dest="basis_port")
    b.set_defaults(fn=cmd_build)
    s = sub.add_parser("serve", help="lokal ausliefern, bei jedem Abruf frisch gebaut")
    s.add_argument("--port", type=int, default=PORT)
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--oeffentlich-hinter-auth", action="store_true")
    s.set_defaults(fn=cmd_serve)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
