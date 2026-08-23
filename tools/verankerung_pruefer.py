#!/usr/bin/env python3
"""Verankerungs-Pruefer — Zusagen am **Typ** pruefen statt am Wortlaut (platform#2211).

## Warum es diesen zweiten Weg gibt

Fuer dieselbe Regel („bewusst Ausgelassenes bekommt im SELBEN Zug ein
Tracking-Artefakt") existierten bereits zwei Muster-Scanner:

* ``tools/deferral_anchor_check.py``  — Aufschub-Sprache im PR-Text + Anker in der Naehe
* ``tools/claude-hooks/deferred_item_scanner.py`` — dieselbe Frage auf dem Turn-Text

Beide sind Wortlisten. Ihre Fehlerklasse ist nicht theoretisch, sondern am
Realfall gemessen (Retro 9d861a Befund #3, PR platform#2007, Abschnitt
„Bewusste Restueberschneidung"):

===================================================================  =========
Messung am Originaltext von PR #2007                                 Ergebnis
===================================================================  =========
``AUFSCHUB`` (PR-Gate) trifft die Zeile                              **nein**
``DEFERRAL_PATTERNS`` (Stop-Hook) trifft die Zeile                   **nein**
… beide treffen, sobald die Markdown-Fettschrift entfernt ist        ja
``ANKER`` findet in derselben Zeile eine Referenz                    ``#2005``
… ``#2005`` ist ein **Pull Request**, kein Tracking-Issue            —
===================================================================  =========

Zwei unabhaengige Gruende, dieselbe Stelle zu verfehlen:

**A — Auszeichnung zerreisst den Wortlaut.** Der reale Text lautet
``bewusst **nicht** mitgemacht``. Zwischen den beiden Woertern stehen vier
Sternchen, und damit trifft kein Muster, das ``bewusst nicht`` erwartet. Genau
dieser Wortlaut wurde am 2026-08-16 eigens in den Stop-Hook nachgetragen — er
war danach immer noch blind fuer das Artefakt, fuer das er nachgetragen wurde.

**B — Naehe ist keine Zustaendigkeit.** Selbst mit entfernter Auszeichnung
verschwindet der Fund, weil im selben Satz ``#2005`` steht. Diese Referenz
belegt eine *Herkunft* („aus #2005"), sie *verfolgt* die aufgeschobene Arbeit
nicht. Ein Anker-Fenster kann diesen Unterschied nicht sehen.

„Ein Muster mehr" heilt A nur bis zur naechsten Auszeichnung und B ueberhaupt
nicht. Deshalb prueft dieses Werkzeug den **Typ der Zusage**, nicht ihre
Formulierung — und den **Anker als Zustaendigkeit**, nicht als Nachbarschaft.

## Wie

1. **Normalisieren** (deterministisch): Markdown-Auszeichnung faellt weg, der
   Satz wird wieder ein Satz. Behebt A fuer jeden nachgelagerten Schritt.
2. **Segmentieren** (deterministisch): Ueberschrift-Abschnitte, darin Absaetze
   und Listenpunkte. Ein Segment ist die Einheit, ueber die geurteilt wird.
3. **Klassifizieren** (Modell, loopback-lokal): welcher Zusage-Typ steckt im
   Segment — ``vertagung``, ``restarbeit``, ``freigabe`` oder ``keine``? Ein
   Klassifikator generalisiert ueber Formulierungen, die niemand aufgezaehlt
   hat; das ist der ganze Unterschied zu einer Musterliste.
4. **Anker pruefen** (deterministisch): ein Anker ist eine **Issue**-Referenz
   IM Segment. Ein ``/pull/``-Link ist keiner (Fehlermodus B). Ein blosses
   ``#N`` laesst sich ohne GitHub nicht unterscheiden und zaehlt dann
   konservativ als Anker — die Unsicherheit wird ausgewiesen, nicht verschwiegen.

## Ehrlichkeits-Sperre

Ist kein Klassifikator erreichbar, meldet das Werkzeug ``NICHT PRUEFBAR`` und
niemals „keine Zusagen gefunden". „Nichts gefunden" und „nichts pruefen
koennen" sind zwei Aussagen (Hausregel, Realfall 0.7.6/#2007).

Exit: 0 = sauber, ohne Befund oder advisory-Fund · 1 = Fund im ``--block``-Modus
· 2 = Werkzeugfehler / nicht pruefbar.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gelesen.
GATE_HEADER = {
    "slug": "zusage-ohne-verankerung",
    "mode": "advisory",  # blocking erst nach Kalibrierfenster mit ECHTEN Treffern
    "owner": "achim",
    "last_drill_pass": "2026-08-23",
    "evidence": "tools/tests/test_verankerung_pruefer.py",
    "covers": ["deferred-item-no-tracking-issue"],
}

DEFAULT_MODELL = "qwen2.5:7b"
DEFAULT_HOST = "http://127.0.0.1:11434"

KLASSEN = ("vertagung", "restarbeit", "freigabe", "keine")
# Nur diese Klassen verlangen ein durables Artefakt. `keine` ist der Normalfall.
ZUSAGE_KLASSEN = ("vertagung", "restarbeit", "freigabe")


class NichtPruefbar(RuntimeError):
    """Der Klassifikator war nicht erreichbar — kein Urteil moeglich."""


# ── 1. Normalisieren ─────────────────────────────────────────────────────────

# Fehlermodus A wohnt in tools/markdown_klartext.py — dasselbe Modul benutzt
# tools/deferral_anchor_check.py, damit die Normalisierung nicht in zwei
# Fassungen auseinanderlaeuft.
from markdown_klartext import normalisiere  # noqa: E402  (bewusst nach den Konstanten)


# ── 2. Segmentieren ──────────────────────────────────────────────────────────

_UEBERSCHRIFT = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
# Metadaten-Zeilen eines PR-Textes: Signatur, Co-Autor, Schliess-Schluesselwort.
# Sie tragen nie eine Zusage, erben aber die Ueberschrift des letzten Abschnitts —
# und wurden dadurch im Kalibrierlauf als `restarbeit` unter „Bewusste
# Restueberschneidung" gemeldet (Fehlalarm 2 von 2, qwen2.5:14b, 2026-08-23).
_BEIWERK = re.compile(
    r"^\s*(?:🤖\s*Generated with|Co-Authored-By:|Generated with \[Claude)"
    r"|^\s*(?:Closes|Fixes|Resolves|Refs|Schlie(?:ss|ß)t)\s+[\w./-]*#\d+\s*$",
    re.I,
)
_LISTENPUNKT = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_CODEZAUN = re.compile(r"^\s*```")
# Zu kurze Segmente tragen keine Zusage und kosten sonst je einen Modell-Aufruf.
MIN_ZEICHEN = 40


@dataclass
class Segment:
    text: str
    ueberschrift: str
    zeile: int

    @property
    def volltext(self) -> str:
        """Segmenttext mit seiner Ueberschrift — die Ueberschrift traegt Bedeutung.

        „## Bewusste Restueberschneidung" allein feuert bei keinem Muster; als
        Kontext des Absatzes darunter ist sie fuer die Klassifikation wesentlich.
        """
        return (
            f"{self.ueberschrift}\n{self.text}".strip()
            if self.ueberschrift
            else self.text
        )


def segmentiere(text: str) -> list[Segment]:
    """Markdown in Urteils-Einheiten zerlegen: Absaetze und Listenpunkte je Abschnitt.

    Code-Bloecke fallen heraus — sie sind Beleg, nicht Zusage.
    """
    segmente: list[Segment] = []
    ueberschrift = ""
    puffer: list[str] = []
    start = 1
    im_code = False

    def schliesse(ende_zeile: int) -> None:
        nonlocal puffer, start
        roh = "\n".join(puffer).strip()
        puffer = []
        if len(roh) >= MIN_ZEICHEN:
            segmente.append(Segment(text=roh, ueberschrift=ueberschrift, zeile=start))
        start = ende_zeile + 1

    for i, zeile in enumerate(text.splitlines(), start=1):
        if _CODEZAUN.match(zeile):
            schliesse(i)
            im_code = not im_code
            continue
        if im_code:
            continue
        kopf = _UEBERSCHRIFT.match(zeile)
        if kopf:
            schliesse(i)
            ueberschrift = kopf.group(2).strip()
            continue
        if not zeile.strip():
            schliesse(i)
            continue
        if _BEIWERK.match(zeile):
            schliesse(i)
            continue
        if _LISTENPUNKT.match(zeile) and puffer:
            schliesse(i)
        if not puffer:
            start = i
        puffer.append(zeile)
    schliesse(len(text.splitlines()) + 1)
    return segmente


# ── 3. Klassifizieren ────────────────────────────────────────────────────────

PROMPT = """Du pruefst EINEN Abschnitt aus einem Entwickler-Artefakt (Pull-Request-Text,
Uebergabe-Notiz, Bericht) auf eine offene ZUSAGE.

Eine Zusage ist eine Aussage ueber Arbeit, die AUSSTEHT — verschoben, ausgelassen,
als Restschuld benannt — oder eine Genehmigung einer Person, die spaeter jemand
nachvollziehen koennen muss. Es zaehlt der SINN, nicht die Wortwahl.

WICHTIG, der haeufigste Fehler: Ein Abschnitt, der beschreibt, was GETAN, gebaut,
gemessen, belegt oder verifiziert wurde, ist KEINE Zusage — auch dann nicht, wenn
er Einschraenkungen, Risiken, Zahlen oder Fehler nennt. Nur was NOCH AUSSTEHT zaehlt.

Klassen:
- "vertagung": Arbeit wird ausdruecklich auf spaeter verschoben, ausgelassen, nicht
  mitgemacht, einem eigenen Umbau/PR ueberlassen.
- "restarbeit": eine Luecke oder Restschuld bleibt nach diesem Stand ausdruecklich
  bestehen und wird hier NICHT behoben.
- "freigabe": eine Person (Owner/Auftraggeber) hat etwas genehmigt, entschieden oder
  angewiesen, und diese Entscheidung traegt eine Handlung.
- "keine": alles andere.

Beispiele:
Abschnitt: "Eine Zusammenlegung waere ein eigener Umbau und ist hier bewusst nicht
mitgemacht." -> {"klasse":"vertagung","zitat":"ist hier bewusst nicht mitgemacht","begruendung":"Umbau ausdruecklich ausgelassen"}
Abschnitt: "5 neue Drills, Datei gesamt 17 passed. Volle Suite 2354 passed." ->
{"klasse":"keine","zitat":"","begruendung":"Bericht ueber erledigte Verifikation"}
Abschnitt: "Von den 20 Eintraegen sind 12 UNKNOWN, weil das Token die privaten Repos
nicht sieht. Sie werden als eine Abdeckungszeile ausgewiesen." ->
{"klasse":"keine","zitat":"","begruendung":"beschreibt gebautes Verhalten"}
Abschnitt: "Der Owner hat am 16.08. entschieden zu verdrahten." ->
{"klasse":"freigabe","zitat":"Owner hat entschieden zu verdrahten","begruendung":"Genehmigung traegt die Handlung"}

Antworte NUR mit JSON:
{"klasse": "<eine der vier>", "zitat": "<woertlicher Halbsatz oder \\"\\">", "begruendung": "<max 12 Woerter>"}

Abschnitt:
---
%s
---"""


def ollama_klassifikator(
    modell: str = DEFAULT_MODELL, host: str = DEFAULT_HOST, timeout: int = 120
) -> Callable[[str], dict]:
    """Klassifikator ueber einen loopback-lokalen Ollama.

    Bewusst kein externer Anbieter als Default: der Text ist Sitzungs- und
    Repo-Inhalt. Verlaesst er die Maschine, ist das eine Egress-Entscheidung
    und keine Nebenwirkung (dieselbe Linie wie tools/print_agent/llm_gate.py).
    """

    def klassifiziere(text: str) -> dict:
        rumpf = json.dumps(
            {
                "model": modell,
                "prompt": PROMPT % text,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode()
        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/generate",
            data=rumpf,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as antwort:
                roh = json.load(antwort).get("response", "")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise NichtPruefbar(f"{modell} auf {host} nicht erreichbar: {exc}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise NichtPruefbar(f"{modell} lieferte kein JSON: {exc}") from exc
        try:
            d = json.loads(roh)
        except (json.JSONDecodeError, ValueError):
            # Ein einzelner unparsbarer Abschnitt ist kein Grund, den Lauf
            # abzubrechen — aber er gilt als NICHT geprueft, nicht als sauber.
            return {
                "klasse": "unklar",
                "zitat": "",
                "begruendung": "Antwort nicht parsbar",
            }
        klasse = str(d.get("klasse", "")).strip().lower()
        return {
            "klasse": klasse if klasse in KLASSEN else "unklar",
            "zitat": str(d.get("zitat", ""))[:200],
            "begruendung": str(d.get("begruendung", ""))[:200],
        }

    return klassifiziere


GEGENPROBE = """Ein Abschnitt aus einem Entwickler-Artefakt wurde als Zusage eingestuft
(Arbeit steht noch aus). Pruefe das nach.

Frage: Steht die genannte Arbeit zum Zeitpunkt dieses Textes NOCH AUS?

"nein" ist richtig, wenn der Abschnitt erledigte Arbeit beschreibt, einen Fix
berichtet, misst, begruendet oder belegt — auch wenn er dabei Einschraenkungen
oder Zahlen nennt.
"ja" ist richtig, wenn die Arbeit ausdruecklich verschoben, ausgelassen oder als
offene Restschuld benannt wird.

Antworte NUR mit JSON: {"steht_aus": true|false}

Eingestuft als: %s
Zitat: %s
Abschnitt:
---
%s
---"""


def ollama_bestaetiger(
    modell: str = DEFAULT_MODELL, host: str = DEFAULT_HOST, timeout: int = 120
) -> Callable[[str, str, str], bool]:
    """Zweite, unabhaengige Frage an dasselbe Modell — Gegenprobe je Kandidat.

    Warum ueberhaupt: der Kalibrierlauf 2026-08-23 zeigte, dass die
    Klassifikation abgeschlossene Arbeit gelegentlich als Zusage liest
    („Dublettenfilter entfernt. Idempotenz braucht ihn nicht" → `vertagung`,
    PR #2196). Die Gegenprobe fragt nicht nach dem Typ, sondern nach dem
    Zustand: steht die Arbeit noch aus? Sie laeuft nur ueber Kandidaten und
    kostet deshalb wenige Aufrufe.
    """
    roh = ollama_klassifikator(modell, host, timeout)

    def bestaetige(text: str, klasse: str, zitat: str) -> bool:
        rumpf = json.dumps(
            {
                "model": modell,
                "prompt": GEGENPROBE % (klasse, zitat or "—", text),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            }
        ).encode()
        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/generate",
            data=rumpf,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as antwort:
                d = json.loads(json.load(antwort).get("response", "{}"))
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise NichtPruefbar(f"Gegenprobe nicht erreichbar: {exc}") from exc
        except (json.JSONDecodeError, ValueError):
            # Unlesbare Gegenprobe darf einen Fund nicht still schlucken.
            return True
        return bool(d.get("steht_aus", True))

    _ = roh  # gemeinsame Fehlerbehandlung oben, Aufruf getrennt gehalten
    return bestaetige


# ── 4. Anker pruefen ─────────────────────────────────────────────────────────

from github_referenzen import ISSUE_URL as _ISSUE_URL  # noqa: E402
from github_referenzen import KURZ_REF as _KURZ_REF  # noqa: E402
from github_referenzen import PR_URL as _PR_URL  # noqa: E402


@dataclass
class Ankerurteil:
    verankert: bool
    grund: str
    unsicher: bool = False


def pruefe_anker(
    segment_text: str, mit_github: bool = True, repo: str = ""
) -> Ankerurteil:
    """Traegt das Segment eine Issue-Referenz, die diese Zusage verfolgt?

    Ein ``/pull/``-Link ist ausdruecklich KEIN Anker: er belegt Herkunft, nicht
    Zustaendigkeit (Fehlermodus B, gemessen an PR #2007 → ``#2005``). Ein blosses
    ``#N`` ist ohne GitHub nicht von einem PR zu unterscheiden; es zaehlt dann
    als Anker, und die Unsicherheit wird ausgewiesen.
    """
    if _ISSUE_URL.search(segment_text):
        return Ankerurteil(
            True, f"Issue-Link {_ISSUE_URL.search(segment_text).group(0)}"
        )

    # Nummern, die im selben Segment als /pull/-Link ausgeschrieben stehen, sind
    # ohne jede Rueckfrage als Pull Request erkannt — die Markdown-Form
    # `[#2005](…/pull/2005)` ist genau der Realfall aus PR #2007.
    pr_nummern = set(_PR_URL.findall(segment_text))
    kurz = [(b, n) for b, n in _KURZ_REF.findall(segment_text) if n not in pr_nummern]
    if not kurz:
        pr = _PR_URL.search(segment_text)
        if pr:
            return Ankerurteil(
                False, f"nur PR-Link {pr.group(0)} — belegt Herkunft, nicht Tracking"
            )
        return Ankerurteil(False, "keine Issue-Referenz im Segment")

    if not mit_github:
        return Ankerurteil(
            True, f"#{kurz[0][1]} ungeprueft als Anker gewertet", unsicher=True
        )

    for besitzer, nummer in kurz:
        ziel = besitzer or repo
        if not ziel:
            return Ankerurteil(
                True, f"#{nummer} ohne Repo-Kontext gewertet", unsicher=True
            )
        art = _art_der_referenz(ziel, nummer)
        if art == "issue":
            return Ankerurteil(True, f"{ziel}#{nummer} ist ein Issue")
        if art == "unbekannt":
            return Ankerurteil(True, f"{ziel}#{nummer} nicht abfragbar", unsicher=True)
    return Ankerurteil(False, f"alle Referenzen sind Pull Requests ({len(kurz)})")


_REF_CACHE: dict[tuple[str, str], str] = {}


def _art_der_referenz(repo: str, nummer: str) -> str:
    """``issue`` | ``pr`` | ``unbekannt`` — ueber die GitHub-CLI, mit Cache."""
    schluessel = (repo, nummer)
    if schluessel in _REF_CACHE:
        return _REF_CACHE[schluessel]
    ergebnis = "unbekannt"
    try:
        lauf = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/{nummer}",
                "--jq",
                '.pull_request.url // "issue"',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if lauf.returncode == 0:
            ergebnis = "issue" if lauf.stdout.strip() == "issue" else "pr"
    except (OSError, subprocess.SubprocessError):
        ergebnis = "unbekannt"
    _REF_CACHE[schluessel] = ergebnis
    return ergebnis


# ── Zusammenfuehren ──────────────────────────────────────────────────────────


@dataclass
class Befund:
    segment: Segment
    klasse: str
    zitat: str
    begruendung: str
    anker: Ankerurteil = field(default_factory=lambda: Ankerurteil(False, ""))


def pruefe(
    text: str,
    klassifikator: Callable[[str], dict],
    mit_github: bool = True,
    repo: str = "",
    klassen: tuple[str, ...] = ZUSAGE_KLASSEN,
    bestaetiger: Callable[[str, str, str], bool] | None = None,
) -> tuple[list[Befund], list[Segment]]:
    """(Befunde, geprüfte Segmente) — Befund = Zusage-Typ ohne gueltigen Anker."""
    segmente = segmentiere(normalisiere(text))
    befunde: list[Befund] = []
    for seg in segmente:
        urteil = klassifikator(seg.volltext)
        klasse = urteil.get("klasse", "unklar")
        if klasse not in klassen:
            continue
        anker = pruefe_anker(seg.text, mit_github=mit_github, repo=repo)
        if anker.verankert:
            continue
        if bestaetiger is not None and not bestaetiger(
            seg.volltext, klasse, urteil.get("zitat", "")
        ):
            continue
        befunde.append(
            Befund(
                segment=seg,
                klasse=klasse,
                zitat=urteil.get("zitat", ""),
                begruendung=urteil.get("begruendung", ""),
                anker=anker,
            )
        )
    return befunde, segmente


def bericht(
    befunde: list[Befund], segmente: list[Segment], quelle: str, block: bool
) -> str:
    if not segmente:
        return f"◌ {quelle}: kein pruefbares Segment (Text zu kurz oder nur Code)."
    if not befunde:
        return (
            f"✅ Verankerung {quelle}: {len(segmente)} Segment(e) geprueft, "
            "jede Zusage traegt ein Tracking-Issue."
        )
    kopf = "❌" if block else "⚠️ "
    zeilen = [
        f"{kopf} Verankerung {quelle}: {len(befunde)} von {len(segmente)} Segment(en) "
        "tragen eine Zusage ohne Tracking-Issue:"
    ]
    for b in befunde:
        ort = f"Zeile {b.segment.zeile}"
        if b.segment.ueberschrift:
            ort += f" · „{b.segment.ueberschrift}“"
        zeilen.append(f"  [{b.klasse}] {ort}")
        if b.zitat:
            zeilen.append(f"      Zitat: „{b.zitat}“")
        zeilen.append(
            f"      Anker: {b.anker.grund}"
            + (" (unsicher)" if b.anker.unsicher else "")
        )
    zeilen.append(
        "\nDer Artefakt-Text zaehlt nicht als Tracking (Hausregel). Billigste Aktion: "
        "`gh issue create` und die Issue-Nummer IM selben Abschnitt nennen."
    )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Zusagen am Typ pruefen, nicht am Wortlaut."
    )
    quelle = ap.add_mutually_exclusive_group()
    quelle.add_argument("--pr", help="PR-Nummer; Text via gh")
    quelle.add_argument("--datei", help="Datei mit Markdown-Text")
    ap.add_argument(
        "--repo",
        default=os.environ.get("VERANKERUNG_REPO", ""),
        help="owner/repo fuer --pr und #N-Aufloesung",
    )
    ap.add_argument(
        "--modell", default=os.environ.get("VERANKERUNG_MODELL", DEFAULT_MODELL)
    )
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST", DEFAULT_HOST))
    ap.add_argument(
        "--ohne-github", action="store_true", help="keine gh-Abfragen (offline)"
    )
    ap.add_argument(
        "--klassen",
        default="vertagung",
        help=(
            "Zusage-Klassen, die als Befund gelten (Komma-Liste aus "
            f"{','.join(ZUSAGE_KLASSEN)}). Welle 1 ist bewusst `vertagung`: nur fuer "
            "sie ist die Praezision gemessen (docs/governance/verankerung-kalibrierung-2026-08-23.md)."
        ),
    )
    ap.add_argument(
        "--ohne-gegenprobe",
        action="store_true",
        help="Kandidaten nicht zweitpruefen (schneller, ungenauer)",
    )
    ap.add_argument("--block", action="store_true", help="Exit 1 bei Fund")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    args = ap.parse_args(argv)

    if args.pr:
        befehl = ["gh", "pr", "view", args.pr, "--json", "body", "--jq", ".body"]
        if args.repo:
            befehl[3:3] = ["--repo", args.repo]
        lauf = subprocess.run(befehl, capture_output=True, text=True, timeout=60)
        if lauf.returncode != 0:
            print(
                f"FEHLER: PR {args.pr} nicht lesbar: {lauf.stderr.strip()}",
                file=sys.stderr,
            )
            return 2
        text, name = lauf.stdout, f"PR #{args.pr}"
    elif args.datei:
        try:
            with open(args.datei, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"FEHLER: {exc}", file=sys.stderr)
            return 2
        name = args.datei
    else:
        text, name = sys.stdin.read(), "stdin"

    try:
        klassen = tuple(k.strip() for k in args.klassen.split(",") if k.strip())
        unbekannt = [k for k in klassen if k not in ZUSAGE_KLASSEN]
        if unbekannt:
            print(
                f"FEHLER: unbekannte Klasse(n): {', '.join(unbekannt)}", file=sys.stderr
            )
            return 2
        befunde, segmente = pruefe(
            text,
            ollama_klassifikator(args.modell, args.host),
            mit_github=not args.ohne_github,
            repo=args.repo,
            klassen=klassen,
            bestaetiger=None
            if args.ohne_gegenprobe
            else ollama_bestaetiger(args.modell, args.host),
        )
    except NichtPruefbar as exc:
        # Ehrlichkeits-Sperre: kein Urteil ist NICHT dasselbe wie ein sauberes.
        print(f"◌ NICHT PRUEFBAR — {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "quelle": name,
                    "segmente": len(segmente),
                    "befunde": [
                        {
                            "klasse": b.klasse,
                            "zeile": b.segment.zeile,
                            "ueberschrift": b.segment.ueberschrift,
                            "zitat": b.zitat,
                            "anker_grund": b.anker.grund,
                            "anker_unsicher": b.anker.unsicher,
                        }
                        for b in befunde
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(bericht(befunde, segmente, name, args.block))
    return 1 if (befunde and args.block) else 0


if __name__ == "__main__":
    sys.exit(main())
