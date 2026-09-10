#!/usr/bin/env python3
"""Gate: aufgeschobene Arbeit im PR-Text braucht einen Anker.

Vier gate-pflichtige Retro-Muster beschreiben denselben Vorgang aus vier
Blickwinkeln — `deferred-item-no-tracking-issue`, `workaround-without-tracking-anchor`,
`planned-phase-no-issue`, `tracking-doc-stale-after-new-occurrence`. Sie sind der
direkte Treiber dafuer, dass `risiko_debt` ueber 60 Retro-Messungen die
schwaechste Dimension ist (Ø 2,55).

Die Hausregel dazu lautet: bewusst Ausgelassenes bekommt im SELBEN Zug ein
Tracking-Artefakt; der PR-Text zaehlt ausdruecklich NICHT als Tracking. Dieser
Check erzwingt genau das — er liest den PR-Text, sucht nach Aufschub-Sprache und
verlangt in ihrer Naehe eine Issue-Referenz.

Bewusst eng gehalten: nur Formulierungen, die eine Auslassung ANKUENDIGEN, nicht
jedes Vorkommen von "offen". Ein Gate mit Fehlalarmen wird umgangen statt befolgt.

Exit: 0 = sauber oder nur Warnung, 1 = Fund im --block-Modus, 2 = Werkzeugfehler.

── Modus `--issue N` (2026-09-10, Retro-Anlass platform#3015) ───────────────

Bisher las dieses Gate ausschliesslich den PR-Text. Am 2026-09-10 standen
sechs Folgearbeiten als Aufschub-Prosa ohne Anker in einem SACHSTANDS-
KOMMENTAR des Auftrags-Issues (#3015) — eine Quelle, die der PR-Text-Scanner
per Konstruktion nicht sieht, genau wie 2026-08-29 der Docstring im Code.
`--issue N [--repo owner/repo]` laedt Issue-Body + alle Kommentare (`gh api`,
paginiert) und wendet dieselbe Funktion `finde_ankerlose_stellen` auf jeden
Kommentar-Body einzeln an. Bewusst ADVISORY in CI (kein neuer Required
Check): ein Sachstand-Kommentar entsteht oft NACH dem PR und soll den PR
nicht rueckwirkend blockieren.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_referenzen import ohne_pr_referenzen  # noqa: E402  (haengt am sys.path oben)
from markdown_klartext import normalisiere_zeilen  # noqa: E402

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gelesen und
# gegen docs/governance/gate-registry.json abgeglichen. Ohne Kopf verrottet die
# Registry still; ohne Registry-Eintrag drillt das Gate niemand.
#
# `covers` ist der Grund, warum dieses Gate existiert: EIN Mechanismus deckt vier
# gate-pflichtige Retro-Slugs ab, statt vier Einzelgates zu bauen (Empfehlung aus
# platform#1650). `deferred-item-no-tracking-issue` traegt zusaetzlich ein eigenes
# Gate (deferred_item_scanner.py, Session-Kontext) — dieses hier greift im PR-Text.
GATE_HEADER = {
    "slug": "aufschub-anker",
    # blocking seit 2026-09-02 (E4, platform#2606): Fenster 2026-08-10..09-02 mit
    # 1 echtem Treffer und 0 Fehlalarmen. Der Modus wirkt im WORKFLOW
    # (.github/workflows/aufschub-anker-gate.yml), nicht in diesem Modul: hier
    # entscheidet weiterhin `--block` ueber den Exit-Code.
    "mode": "blocking",
    "owner": "achim",
    "last_drill_pass": "2026-09-02",  # Drill am realen Rueckfall writing-hub#851 (s. Tests)
    "evidence": "tools/tests/test_deferral_anchor_check.py",
    "covers": [
        "workaround-without-tracking-anchor",
        "planned-phase-no-issue",
        "tracking-doc-stale-after-new-occurrence",
        "deferred-item-no-tracking-issue",
    ],
}

# Wendungen, die eine Auslassung ankuendigen. Positivliste — Fliesstext, der
# zufaellig "offen" enthaelt, soll NICHT feuern.
AUFSCHUB = re.compile(
    r"(nicht enthalten|nicht Teil dieses PR|nicht in diesem PR|bewusst ausgelassen"
    r"|bewusst nicht|folgt separat|kommt separat|in einem Folge-PR|Folgearbeit"
    r"|spaeter nachziehen|später nachziehen|bleibt offen|noch offen"
    r"|entscheidet der Owner separat|vertagt|Restschuld|Restarbeit"
    # Ergaenzt 2026-08-29 aus einem gemessenen Rueckfall (writing-hub#851,
    # `apps/core/langlauf.py`). Die Vertagung stand woertlich als
    # »bleibt vorerst eigenstaendig — Owner-Konvention: nachziehen nur, wenn wir
    # es ohnehin anfassen«. KEIN Wort der bisherigen Liste kam darin vor: das
    # Gate liess den Satz durch, auch als er ihm direkt eingespeist wurde.
    # Vorher gemessen, dann ergaenzt — die urspruengliche Fix-Idee (nur die
    # Quelle erweitern) haette den Ausloeser weiterhin verfehlt.
    r"|bleibt (vorerst|zunaechst|zunächst|einstweilen|erstmal|fuers erste|fürs erste)"
    r"|(nachziehen|angleichen|migrieren|umstellen) nur,? wenn"
    r"|wenn wir (es|ihn|sie|das) (ohnehin|sowieso|eh) anfass"
    r"|vorerst (nicht|unveraendert|unverändert|so belassen)"
    r"|noch nicht (umgesetzt|migriert|angeglichen|nachgezogen))",
    re.IGNORECASE,
)

# ── Kalibrierung 2026-09-03 (platform#2234) ──────────────────────────────────
#
# Gemessener Fehlalarm (platform#2757, Kalibrierung platform#2234): der Satz
#
#     <generische Verneinung> `gh api rate_limit`: das misst das Primaerlimit ...
#
#   Der Wortlaut steht als Pruefmaterial im Drill, nicht hier: eine woertliche
#   Wiedergabe in diesem Kommentar loest den Waechter selbst aus — gemessen beim
#   Bau, die Kalibrierung blockierte ihren eigenen PR.
#
# ist eine METHODENWAHL, keine Vertagung — »X ist das falsche Werkzeug«, nicht
# »machen wir spaeter«. Dieselben Woerter, gegensaetzliche Bedeutung.
#
# Der Unterschied liegt am direkten Objekt: steht dort ein CODE-BEZEICHNER in
# Backticks, ist die Verneinung eine technische Entscheidung. Steht dort ein
# Liefergegenstand (»die Verdrahtung als Hook«, »der Backfill«), bleibt es ein
# Aufschub.
#
# Bewusst SEHR eng gefasst. Ein erster, breiterer Entwurf verlangte irgendein
# Arbeitswort im Satz — er liess prompt neun bestehende Drills durchfallen,
# darunter einen Satz, dessen Objekt ein Liefergegenstand war (»die Verdrahtung
# als Hook«) — auch dieser Wortlaut steht im Drill, nicht hier. Deutsche Vertagungen
# stehen regelmaessig als Substantiv da; eine Verb-Liste haette das Gate
# stillgelegt statt kalibriert. Der Fehlversuch steht hier, damit ihn niemand
# wiederholt.
#
# NICHT geloest: der zweite Fehlalarm desselben Tages, die Abschnitts-
# Ueberschrift »Was bewusst NICHT« (platform#2036). Dort fehlt ein Objekt
# vollstaendig, und jede Regel dafuer waere geraten statt gemessen. Er bleibt als
# dokumentierter Fehlalarm in platform#2234 stehen.
METHODENWAHL = re.compile(
    r"(bewusst nicht|bewusst ausgelassen|nicht enthalten"
    r"|nicht Teil dieses PR|nicht in diesem PR)"
    r"\s*:?\s*`[^`]+`",
    re.IGNORECASE,
)


def ist_methodenwahl(zeile: str) -> bool:
    """True, wenn die Verneinung ein Werkzeug benennt statt Arbeit zu vertagen.

    Traegt die Zeile daneben eine SPEZIFISCHE Wendung (»folgt separat«,
    »Restschuld«, »vertagt«, …), bleibt es ein Fund — die tragen die Bedeutung
    schon im Wortlaut.
    """
    if not METHODENWAHL.search(zeile):
        return False
    ohne = METHODENWAHL.sub(" ", zeile)
    return not AUFSCHUB.search(ohne)


# Ein Anker ist eine Issue-Referenz — nicht bloss eine PR-Nummer.
ANKER = re.compile(
    r"(#\d+|(?:Refs|Closes|Fixes|Tracked in|getrackt (?:in|als))\s*[:#]?\s*\S+"
    r"|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)",
    re.IGNORECASE,
)

# Wie viele Zeilen um die Fundstelle als "Naehe" gelten.
FENSTER = 4

# Obergrenze fuer das Abschnitts-Fenster einer Ueberschrift (s. finde_ankerlose_stellen).
# Begrenzt, damit eine Ueberschrift ohne folgende Ueberschrift nicht den ganzen
# Resttext als "Naehe" verbucht und jeden Anker weiter unten einsammelt.
ABSCHNITT_MAX = 20


UEBERSCHRIFT = re.compile(r"^\s{0,3}#{1,6}\s")


def finde_ankerlose_stellen(text: str, fenster: int = FENSTER) -> list[tuple[int, str]]:
    """(Zeilennummer, Zeile) je Aufschub-Stelle ohne Anker in der Naehe.

    Ueberschriften bekommen ein groesseres Suchfenster: eine Zeile wie
    "## Bewusst nicht in diesem PR" kuendigt einen ABSCHNITT an, und der Anker
    steht dann bei den einzelnen Punkten darunter — regelmaessig mehr als
    `fenster` Zeilen entfernt. Mit dem engen Fenster meldete das Gate genau
    diesen Fall als Fund, obwohl der Anker zwei Zeilen spaeter dastand: der
    erste Live-Fehlalarm, gefangen auf dem eigenen Einfuehrungs-PR (#1897).

    Fuer eine Ueberschrift wird deshalb bis zur naechsten Ueberschrift gesucht
    (hoechstens ABSCHNITT_MAX Zeilen). Bewusst NICHT: Ueberschriften ganz
    ueberspringen — ein Abschnitt, der Aufschub ankuendigt und in seinem
    gesamten Rumpf kein Issue nennt, bleibt ein Fund.
    """
    # Zeilentreu entschmuecken, bevor gematcht wird: der reale Rueckfall stand
    # als `bewusst **nicht** mitgemacht` da und war fuer AUFSCHUB unsichtbar
    # (gemessen an PR #2007, docs/governance/verankerung-kalibrierung-2026-08-23.md).
    zeilen = normalisiere_zeilen(text).splitlines()
    # `normalisiere_zeilen` entfernt die Auszeichnung — auch die Backticks. Die
    # Methodenwahl-Erkennung braucht sie aber: sie unterscheidet gerade daran,
    # ob das Objekt ein Code-Bezeichner ist. Deshalb wird SIE auf dem Original
    # geprueft, alles andere weiter auf der entschmueckten Fassung. Beim ersten
    # Versuch stand hier die entschmueckte Zeile, und die Regel griff nie.
    roh = text.splitlines()
    funde: list[tuple[int, str]] = []
    for i, zeile in enumerate(zeilen):
        if not AUFSCHUB.search(zeile):
            continue
        if ist_methodenwahl(roh[i] if i < len(roh) else zeile):
            continue
        if UEBERSCHRIFT.match(zeile):
            bis = min(len(zeilen), i + 1 + ABSCHNITT_MAX)
            for j in range(i + 1, bis):
                if UEBERSCHRIFT.match(zeilen[j]):
                    bis = j
                    break
            von = i
        else:
            von, bis = max(0, i - fenster), min(len(zeilen), i + fenster + 1)
        # Ein PR-Verweis ist kein Anker: er belegt Herkunft, nicht Zustaendigkeit.
        # Ohne diesen Schritt raeumt `#2005` im selben Satz den Fund ab, den
        # Retro 9d861a als Befund #3 fuehrt (PR #2007).
        if ANKER.search(ohne_pr_referenzen("\n".join(zeilen[von:bis]))):
            continue
        funde.append((i + 1, zeile.strip()))
    return funde


#: Zeilenanfaenge, die eine hinzugefuegte Zeile als Prosa-im-Code ausweisen.
KOMMENTAR = re.compile(r"^\s*(#|//|\*|<!--)")

#: Dreifach-Anfuehrungszeichen — Beginn oder Ende eines Docstrings.
DREIFACH = re.compile(r"(\"\"\"|''')")

#: Dateien, deren hinzugefuegte Kommentarzeilen mitgelesen werden.
QUELLDATEIEN = (".py", ".js", ".ts", ".html", ".jinja2", ".yml", ".yaml", ".sh")


def prosa_aus_diff(diff: str) -> str:
    """Die hinzugefuegten Kommentar- und Docstring-Zeilen eines Unified Diff.

    **Warum das Gate hier ueberhaupt hinsehen muss.** Es las bisher nur den
    PR-Text. Der reale Rueckfall vom 2026-08-29 (writing-hub#851) stand aber in
    einem **Docstring im Code** — dort kann ein PR-Text-Scanner ihn per
    Konstruktion nicht finden. Eine Vertagung im Code zaehlt so wenig als
    Tracking wie eine im PR-Text; also gehoert sie in denselben Blick.

    **Grenze, ausdruecklich benannt:** der Docstring-Zustand wird nur INNERHALB
    der hinzugefuegten Zeilen einer Datei verfolgt. Beginnt ein Hunk mitten in
    einem Docstring, erkennt diese Funktion ihn nicht als solchen. Fuer den Fall,
    der sie ausgeloest hat — eine **neue** Datei, deren Docstring vollstaendig im
    Diff steht — traegt das; fuer eine Aenderung tief in einem bestehenden
    Docstring nicht. Das ist eine bekannte Luecke, keine stille.
    """
    zeilen: list[str] = []
    interessant = False
    im_docstring = False
    for roh in diff.splitlines():
        if roh.startswith("+++ "):
            pfad = roh[4:].strip()
            interessant = pfad.endswith(QUELLDATEIEN)
            im_docstring = False
            continue
        if roh.startswith(("--- ", "diff ", "index ", "@@")):
            if roh.startswith("@@"):
                # Neuer Hunk: der Docstring-Zustand des vorigen gilt nicht weiter.
                im_docstring = False
            continue
        if not interessant or not roh.startswith("+"):
            continue
        inhalt = roh[1:]
        treffer = len(DREIFACH.findall(inhalt))
        if im_docstring or KOMMENTAR.match(inhalt) or treffer:
            zeilen.append(inhalt)
        if treffer % 2 == 1:
            im_docstring = not im_docstring
    return "\n".join(zeilen)


def _parse_verkettete_json_arrays(ausgabe: str) -> list:
    """`gh api ... --paginate` haengt eine JSON-Liste pro Seite aneinander.

    Ohne `--slurp` (nicht auf jeder gh-Version vorhanden) liefert die
    Ausgabe mehrere top-level JSON-Arrays hintereinander statt eines
    gemeinsamen — Standardverhalten von `gh api --paginate` bei
    Listen-Endpunkten. `json.loads` scheitert daran; ein
    `JSONDecoder.raw_decode`-Loop liest sie einzeln und haengt sie zu einer
    Liste zusammen.
    """
    dec = json.JSONDecoder()
    text = ausgabe.strip()
    ergebnis: list = []
    idx = 0
    laenge = len(text)
    while idx < laenge:
        while idx < laenge and text[idx].isspace():
            idx += 1
        if idx >= laenge:
            break
        obj, ende = dec.raw_decode(text, idx)
        ergebnis.extend(obj if isinstance(obj, list) else [obj])
        idx = ende
    return ergebnis


def _issue_stoff_per_gh(issue: int, repo: str) -> tuple[str, list[dict]]:
    """Issue-Body + alle Kommentare ueber `gh api` (paginiert)."""
    body_lauf = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue}"],
        capture_output=True,
        text=True,
        check=True,
    )
    body = json.loads(body_lauf.stdout).get("body") or ""

    kommentare_lauf = subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue}/comments", "--paginate"],
        capture_output=True,
        text=True,
        check=True,
    )
    kommentare = _parse_verkettete_json_arrays(kommentare_lauf.stdout)
    return body, kommentare


def _issue_stoff_aus_datei(pfad: str) -> tuple[str, list[dict]]:
    """`--eingabe DATEI`: JSON `{"body": "...", "comments": [{"id", "html_url", "body"}]}`.

    Ersetzt den `gh`-Aufruf fuer Tests — kein Netzwerk, kein Token noetig.
    """
    with open(pfad, encoding="utf-8") as f:
        daten = json.load(f)
    return daten.get("body") or "", daten.get("comments") or []


def _berichte(funde: list[tuple], block: bool) -> int:
    """Gemeinsame Ausgabe/Exit-Logik fuer PR-Text-, Diff- und Issue-Modus.

    `funde` ist entweder eine Liste aus (Zeile, Text) — PR-Text/Diff-Modus —
    oder aus (Ort, Zeile, Text) — Issue-Modus, wo `Ort` den Kommentar
    benennt (Issue-Body oder Kommentar-URL).
    """
    if not funde:
        print(
            "✅ Aufschub-Anker: jede angekuendigte Auslassung hat eine Issue-Referenz."
        )
        return 0

    kopf = "❌ Aufschub ohne Anker" if block else "⚠️  Aufschub ohne Anker"
    print(
        f"{kopf}: {len(funde)} Stelle(n) kuendigen Arbeit an, ohne ein Issue zu nennen:"
    )
    for eintrag in funde:
        if len(eintrag) == 3:
            ort, nr, zeile = eintrag
            print(f"  {ort} — Zeile {nr}: {zeile[:110]}")
        else:
            nr, zeile = eintrag
            print(f"  Zeile {nr}: {zeile[:110]}")
    print(
        "\nDer PR-Text zaehlt nicht als Tracking. Lege ein Issue an und nenne es in "
        "der Naehe der Stelle (`Refs #N`), oder streiche die Ankuendigung."
    )
    return 1 if block else 0


def _pruefe_issue(args: argparse.Namespace) -> int:
    """`--issue`/`--eingabe`-Modus: Issue-Body + Kommentare statt PR-Text."""
    try:
        if args.eingabe:
            body, kommentare = _issue_stoff_aus_datei(args.eingabe)
        else:
            if args.issue is None:
                print(
                    "FEHLER: --eingabe ohne --issue braucht keine Issue-Nummer, "
                    "aber --issue ohne --eingabe schon.",
                    file=sys.stderr,
                )
                return 2
            repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
            if not repo:
                print(
                    "FEHLER: --repo fehlt (oder $GITHUB_REPOSITORY setzen)",
                    file=sys.stderr,
                )
                return 2
            body, kommentare = _issue_stoff_per_gh(args.issue, repo)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    # Abdeckungsauskunft: wie viele Kommentare wurden ueberhaupt gesehen —
    # sonst bleibt ein leerer Fund ("0 Stellen") nicht von "Issue hatte gar
    # keine Kommentare" unterscheidbar.
    print(f"Geprueft: Issue-Body + {len(kommentare)} Kommentar(e).")

    funde: list[tuple[str, int, str]] = [
        ("Issue-Body", nr, zeile)
        for nr, zeile in finde_ankerlose_stellen(body, args.fenster)
    ]
    for kommentar in kommentare:
        ort = kommentar.get("html_url") or f"Kommentar {kommentar.get('id', '?')}"
        for nr, zeile in finde_ankerlose_stellen(
            kommentar.get("body") or "", args.fenster
        ):
            funde.append((ort, nr, zeile))

    return _berichte(funde, args.block)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", action="store_true", help="Exit 1 bei Fund")
    ap.add_argument("--fenster", type=int, default=FENSTER)
    ap.add_argument("datei", nargs="?", help="PR-Text; ohne Angabe von stdin")
    ap.add_argument(
        "--diff",
        metavar="DATEI",
        help="Zusaetzlich die hinzugefuegten Kommentar-/Docstring-Zeilen eines "
        "Unified Diff pruefen (Vertagung im Code zaehlt wie eine im PR-Text)",
    )
    ap.add_argument(
        "--issue",
        type=int,
        help="Issue-Nummer: prueft Issue-Body + alle Kommentare statt PR-Text "
        "(gh api, paginiert)",
    )
    ap.add_argument(
        "--repo",
        help="owner/repo fuer --issue (Default: $GITHUB_REPOSITORY)",
    )
    ap.add_argument(
        "--eingabe",
        metavar="DATEI",
        help='JSON {"body": "...", "comments": [{"id","html_url","body"}]} '
        "statt gh-Aufruf — ersetzt --issue in Tests",
    )
    args = ap.parse_args(argv)

    if args.issue is not None or args.eingabe:
        return _pruefe_issue(args)

    try:
        if args.datei:
            with open(args.datei, encoding="utf-8") as f:
                text = f.read()
        else:
            text = sys.stdin.read()
    except OSError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    funde = finde_ankerlose_stellen(text, args.fenster)

    # Der Diff wird als EIGENER Text geprueft, nicht an den PR-Text gehaengt: ein
    # Anker im PR-Text soll eine Vertagung im Code nicht abdecken. Die beiden
    # stehen an verschiedenen Orten, und der Leser des einen sieht den anderen
    # nicht.
    if args.diff:
        try:
            with open(args.diff, encoding="utf-8") as f:
                prosa = prosa_aus_diff(f.read())
        except OSError as exc:
            print(f"FEHLER: {exc}", file=sys.stderr)
            return 2
        funde += [
            (nr, f"[Code] {zeile}")
            for nr, zeile in finde_ankerlose_stellen(prosa, args.fenster)
        ]

    return _berichte(funde, args.block)


if __name__ == "__main__":
    sys.exit(main())
