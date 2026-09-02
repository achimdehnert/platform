#!/usr/bin/env python3
"""gate_wirkung.py — Rueckfall-Mass fuer gebaute Gates (Session-Loop, KONZ-platform-010).

## Warum es das gibt

Der Retro-Loop hatte bis hierhin drei Messpunkte und eine Luecke:

- `docs/governance/gate-registry.json` sagt, ein Gate ist **gebaut**.
- `tools/gate_drill_check.py` sagt, es **feuert** (Drill gruen).
- `tools/retro_kpis.py` zaehlt, wie oft ein Slug **insgesamt** wiederkehrt.

Keiner davon beantwortet die Frage, an der sich entscheidet, ob der Loop besser
wird: **wie oft ist der Befund aufgetreten, NACHDEM sein Gate gebaut war?**

Ohne diese Trennung ist ein Gate mit 16 Rueckfaellen seit dem Bau in jeder
Anzeige ununterscheidbar von einem, das gestern gebaut wurde und noch nie
gebraucht wurde. Genau das war der Zustand am 2026-08-20: `claim-before-cheapest-check`
stand bei ×47 Gesamt-Vorkommen, das blockierende Stop-Hook-Gate war seit
2026-08-02 gebaut, verdrahtet (`~/.claude/settings.json`, Stop-Event) und der
Drill gruen — und der Slug kehrte danach **16 weitere Male** wieder, zuletzt am
Tag dieser Messung. Der Retro-Report buchte ihn jedes Mal als N-te Wiederholung
desselben Befunds statt als Befund **ueber das Gate**.

Die Konsequenz ist keine Zahl, sondern eine Klasse: ein rueckfaelliges Gate
braucht Umbau, Ausweitung oder eine ehrliche Herabstufung — nicht das
N+1-te Memo mit demselben Slug.

## Ehrlichkeits-Sperre (bewusst, nicht optional)

Ein frisch gebautes Gate mit null Rueckfaellen ist **nicht** wirksam, sondern
ungeprueft. Wer das verwechselt, misst die Bauzeit statt die Wirkung und bekommt
eine Kennzahl, die durch blosses Neubauen steigt (Goodhart). Deshalb gilt jedes
Gate, hinter dessen Bau-Datum weniger als `MIN_FENSTER` Retros liegen, als
**zu frueh** — nicht als wirksam. Die Sperre ist der Grund, warum dieses Werkzeug
Retros zaehlt und nicht Tage: ein ruhiger Monat ohne Sitzungen ist keine Evidenz.

## Aufruf

    python3 tools/gate_wirkung.py            # voller Report
    python3 tools/gate_wirkung.py --kurz     # eine Zeile fuer den Session-Start-Runner
                                             #   (leere Ausgabe = kein Rueckfall)
    python3 tools/gate_wirkung.py --json     # maschinenlesbar
    python3 tools/gate_wirkung.py --dir <p>  # Retro-Verzeichnis(se) ueberschreiben

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `retro_kpis.py`
und `gate_drill_check.py`). Das Urteil steht im Text; erzwungen wird es dort, wo
es hingehoert: im Retro-Skill als eigene Befund-Klasse.

stdlib-only, damit es in jeder Retro-Phase und im Runner ohne Setup laeuft.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

# Maschinenlesbarer Kopf (KONZ-038 D8) — steht im Modul, nicht nur in der Registry,
# damit `gate_drill_check.py` ihn gegen die Registry pruefen kann.
GATE_HEADER = {
    "slug": "gate-rueckfall-unbemerkt",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-02",
    "evidence": "tools/tests/test_gate_wirkung.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")

# Mindestzahl Retros NACH dem Bau-Datum, bevor ueber ein Gate geurteilt wird.
# 3 ist bewusst niedrig: es geht um den Unterschied "hatte ueberhaupt Gelegenheit"
# gegen "hatte keine", nicht um statistische Signifikanz.
MIN_FENSTER = 3

# Protokoll der Gate-Treffer (lokal, angelegt von tools/claude-hooks/gate_hits.py).
# Ueberschreibbar ueber dieselbe Env-Variable wie dort, damit ein Test nicht das
# echte Protokoll des Entwicklers liest.
GATE_HITS = os.environ.get(
    "GATE_HITS_DATEI",
    os.path.join(os.path.expanduser("~"), ".claude", "hooks", "gate-hits.jsonl"),
)

# Ab so vielen Rueckfaellen gilt ein Gate als rueckfaellig. 2 statt 1, weil ein
# einzelner Rueckfall auch der Lauf sein kann, in dem das Gate gebaut WURDE.
RUECKFALL_SCHWELLE = 2

_DATUM_AUS_NAME = re.compile(r"session-retro-(\d{4}-\d{2}-\d{2})-")
_INLINE = re.compile(r"^recurring_findings\s*:\s*\[(.*?)\]", re.S | re.M)
_BLOCK_START = re.compile(r"^recurring_findings\s*:\s*$")
#: Zweite Liste im selben Frontmatter: Slugs, deren Befund in dieser Sitzung von
#: einem BESTEHENDEN Gate gefangen wurde. Sie stehen zusaetzlich in
#: `recurring_findings` (der Befund trat ja auf, `retro_kpis.py` zaehlt ihn weiter),
#: sind hier aber Evidenz FUER das Gate und nicht gegen es.
_INLINE_GEFANGEN = re.compile(r"^gates_caught\s*:\s*\[(.*?)\]", re.S | re.M)
_BLOCK_START_GEFANGEN = re.compile(r"^gates_caught\s*:\s*$")
# Zweite Quelle seit 2026-09-02 (platform#2374 Ziel A, PR #2615): die Befund-Tabelle (§2)
# der Retro. Die Frontmatter ist selbst-etikettiert — ein Rueckfall stand dort nur, wenn der
# Autor den Slug eintippte. Gemessen ueber 109 Retros: bei 12 von 33 Gates wich sie von der
# Tabelle ab, 14 Gates waren rueckfaellig statt der gemeldeten 2 (Realfall: Retro fdd368
# Z. 63 SURVIVES fuer `worktree-midsession-accumulation`, Frontmatter ohne — Urteil war
# "wirksam"). Eine SURVIVES-Zeile, deren letzte Spalte den Slug nennt, zaehlt als Vorkommen.
# Zeilen mit dem Wort `gates_caught` sind vom Autor zeilengenau als gefangen markiert und
# zaehlen nicht; die Frontmatter-Liste `gates_caught` allein reicht dafuer NICHT mehr, weil
# sie je Retro gilt und beim Abzug belegte Rueckfaelle derselben Sitzung verschluckte
# (cc4e11 2026-09-01: zwei SURVIVES-Zeilen ausdruecklich "nicht gefangen").
_VERDIKT = re.compile(r"SURVIVES|REFUTED|WIDERLEGT")
_PIPE = re.compile(r"(?<!\\)\|")
_SLUG_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")
_ZEILE_GEFANGEN = re.compile(r"gates_caught")


def _slugs_aus_tabelle(text: str) -> list[str]:
    """Slugs aus SURVIVES-Zeilen der Befund-Tabelle (letzte Spalte = Recurrence).

    Zeilen ohne Verdikt-Spalte, REFUTED-Zeilen und Zeilen mit `gates_caught`-Marker
    liefern nichts. Bewusst tolerant gegen Spaltenzahl und Verdikt-Schreibweisen
    (`SURVIVES (kommandobelegt)`, `**SURVIVES**`), weil 109 Retros 32 Varianten kennen.
    """
    slugs: set[str] = set()
    for zeile in text.splitlines():
        if not zeile.startswith("|"):
            continue
        zellen = [z.strip() for z in _PIPE.split(zeile)]
        v_idx = next((i for i, z in enumerate(zellen) if _VERDIKT.search(z)), None)
        if v_idx is None or v_idx < 2 or "SURVIVES" not in zellen[v_idx]:
            continue
        rest = [z for z in zellen[v_idx + 1 :] if z]
        if not rest or _ZEILE_GEFANGEN.search(zeile):
            continue
        slugs.update(_SLUG_TOKEN.findall(rest[-1]))
    return sorted(slugs)


# Kommentar-Toleranz ist nicht kosmetisch: ohne sie brach der Block beim ersten
# `- slug  # Notiz` ab und ALLE folgenden Slugs fielen still weg — die Fehlrichtung,
# die echte Rueckfaelle verdeckt (Retro beefc148, Befund #3).
_LISTEN_EINTRAG = re.compile(r"^\s*-\s*([a-z0-9][a-z0-9-]*)\s*(?:#.*)?$")
_LEER_ODER_KOMMENTAR = re.compile(r"^\s*(?:#.*)?$")


def standard_verzeichnisse() -> list[str]:
    """docs/retros/ (git-durabel) + ~/shared/ (Schreibpfad des Skills) — wie retro_kpis."""
    return [
        os.path.join(REPO_ROOT, "docs", "retros"),
        os.path.join(os.path.expanduser("~"), "shared"),
    ]


def lies_retros(verzeichnisse: list[str]) -> list[tuple[str, list[str], str]]:
    """(datum, slugs, dateiname) je Retro. Dedupliziert nach Dateiname.

    `-extern-`-Briefings sind Handoffs an fremde LLMs, keine Retros — sie tragen
    keine eigenen Befunde und wuerden sonst doppelt zaehlen.
    """
    gesehen: dict[str, tuple[str, list[str], str]] = {}
    for verzeichnis in verzeichnisse:
        for pfad in sorted(glob.glob(os.path.join(verzeichnis, "session-retro-*.md"))):
            name = os.path.basename(pfad)
            if "-extern-" in name or name in gesehen:
                continue
            treffer = _DATUM_AUS_NAME.match(name)
            if not treffer:
                continue
            try:
                text = open(pfad, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            gesehen[name] = (
                treffer.group(1),
                _slugs_aus_frontmatter(text),
                name,
                _slugs_aus_frontmatter(text, _INLINE_GEFANGEN, _BLOCK_START_GEFANGEN),
                _slugs_aus_tabelle(text),
            )
    return sorted(gesehen.values())


def _slugs_aus_frontmatter(
    text: str, inline=_INLINE, block_start=_BLOCK_START
) -> list[str]:
    """`recurring_findings` als Inline-Liste ODER als YAML-Block — beide Formen kommen vor.

    Mit `inline`/`block_start` liest dieselbe Mechanik auch `gates_caught`.
    """
    if not text.startswith("---"):
        return []
    teile = text.split("---", 2)
    if len(teile) < 3:
        return []
    frontmatter = teile[1]

    treffer = inline.search(frontmatter)
    if treffer:
        roh = treffer.group(1).replace("\n", " ")
        # Auch in der Inline-Form kann ein Kommentar stehen (`[a, b]  # Notiz` faengt
        # der Regex nicht, aber `[a, # weg\n b]` schon) — je Eintrag abschneiden.
        eintraege = (e.split("#", 1)[0].strip() for e in roh.split(","))
        return [e for e in eintraege if e]

    slugs: list[str] = []
    im_block = False
    for zeile in frontmatter.splitlines():
        if block_start.match(zeile):
            im_block = True
            continue
        if im_block:
            eintrag = _LISTEN_EINTRAG.match(zeile)
            if eintrag:
                slugs.append(eintrag.group(1))
            elif _LEER_ODER_KOMMENTAR.match(zeile):
                continue  # Leerzeile/Kommentarzeile beendet die Liste nicht
            else:
                im_block = False
    return slugs


def _zerlege(retro) -> tuple[str, list[str], str, list[str], list[str]]:
    """(datum, slugs, name[, gefangen[, tabelle]]) — vierte Stelle seit 2026-08-20,
    fuenfte (Slugs aus der Befund-Tabelle) seit 2026-09-02.

    Aeltere Aufrufer und Tests reichen kuerzere Tupel; die werden weiter angenommen,
    statt sie mit einer Signaturaenderung stillzulegen.
    """
    return (
        retro[0],
        retro[1],
        retro[2],
        (retro[3] if len(retro) > 3 else []),
        (retro[4] if len(retro) > 4 else []),
    )


def bewerte(gates: list[dict], retros: list) -> list[dict]:
    """Je Gate: Vorkommen vor/nach Bau-Datum + Urteil.

    `vorher_messbar` ist der zweite Ehrlichkeits-Marker: liegt das Bau-Datum vor
    dem aeltesten vorliegenden Retro, dann ist "vorher = 0" kein Messwert, sondern
    das Ende des Datenfensters. Ohne diesen Marker liest sich ein Gate von 2026-06-01
    wie eines, das nie gebraucht wurde — obwohl der Zeitraum davor schlicht fehlt.
    """
    zerlegt = [_zerlege(r) for r in retros]
    aeltestes = min((d for d, _, _, _, _ in zerlegt), default="")
    ergebnis = []
    for gate in gates:
        slug = gate.get("slug", "")
        # `revised` schlaegt `built`: ein umgebautes Gate wird ab seinem Umbau
        # gemessen. Ohne das bleibt es fuer immer RUECKFAELLIG — die Vorkommen von
        # vor der Reparatur zaehlen weiter mit, das Signal wird zu Laerm, und der
        # naechste Leser lernt, die Zeile zu ueberblaettern. Genau die Mechanik, die
        # dieses Werkzeug abstellen soll. Die Abnahme in #2143 verlangt es woertlich:
        # "die behandelten Gates stehen auf zu-frueh (Zaehler neu ab neuem Bau-Datum)".
        # Missbrauchsschutz: `revised` ist ein Datum wie `built` und steht im selben
        # oeffentlichen Registry-Eintrag — wer es setzt, ohne umzubauen, hinterlaesst
        # den Beleg dafuer im Diff.
        gebaut = gate.get("revised") or gate.get("built") or ""
        umgebaut = bool(gate.get("revised"))
        # Ein Befund, den das Gate GEFANGEN hat, ist kein Rueckfall gegen dieses
        # Gate — er ist der Beleg, dass es wirkt. Bis 2026-08-20 zaehlte beides
        # gleich: ein Gate, das seine Arbeit tat, sammelte dieselben Ausrufezeichen
        # wie eines, das blind war. Die Markierung setzt die Retro je Fall
        # (`gates_caught`), nicht das Werkzeug — und sie ist eng: „hat gefangen"
        # heisst rechtzeitig, nicht „hat sich hinterher gemeldet".
        # Seit 2026-09-02 zaehlt ein Vorkommen aus BEIDEN Quellen: Frontmatter-Liste
        # ODER SURVIVES-Zeile der Befund-Tabelle. "Gefangen" entlastet nur noch, wenn die
        # Tabelle KEINE ungefangene Zeile fuer den Slug traegt — sonst hat die Sitzung
        # beides erlebt, und der Rueckfall ist der Teil, der zaehlt.
        gefangen = sorted(d for d, _, _, g, t in zerlegt if slug in g and slug not in t)
        vorkommen = sorted(
            d
            for d, slugs, _, g, t in zerlegt
            if slug in t or (slug in slugs and slug not in g)
        )
        nur_tabelle = sorted(
            d for d, slugs, _, _, t in zerlegt if slug in t and slug not in slugs
        )
        # Das Retro des BAU-TAGS zaehlt in keinen der beiden Toepfe. Es ist in aller
        # Regel genau der Befund, AUS DEM das Gate entstand — als "vorher" wuerde es
        # den Erfolg schoenen, als "nachher" ist es ein Rueckfall gegen ein Gate, das
        # es selbst ausgeloest hat. Zweiteres war bis 2026-08-20 der Fall (`d >= gebaut`)
        # und machte die Schwelle faktisch zu 1 statt 2: ein fremder Pruefer reproduzierte
        # `RUECKFAELLIG` aus zwei Retros, von denen eines der Bau-Tag war (Retro beefc148,
        # Befund #2). Der Kommentar an RUECKFALL_SCHWELLE behauptete genau das Gegenteil.
        vorher = [d for d in vorkommen if gebaut and d < gebaut]
        nachher = [d for d in vorkommen if gebaut and d > gebaut]
        fenster = len({d for d, _, _, _, _ in zerlegt if gebaut and d > gebaut})
        nur_tabelle_nachher = [d for d in nur_tabelle if gebaut and d > gebaut]
        vorher_messbar = bool(gebaut) and bool(aeltestes) and gebaut > aeltestes
        # "vorher" heisst bei einem umgebauten Gate: vor dem Umbau, nicht vor dem
        # Erstbau — die Zahl bleibt ehrlich, nur ihr Bezugspunkt wandert mit.

        # Reihenfolge mit Absicht: RUECKFAELLIG steht VOR der Fenster-Sperre.
        # Die Sperre schuetzt die POSITIVE Aussage ("wirksam") vor einem zu kurzen
        # Beobachtungszeitraum — sie darf einen tatsaechlich beobachteten Rueckfall
        # nicht verschlucken. Zwei echte Vorkommen nach dem Bau sind Evidenz, egal wie
        # kurz das Fenster ist; sie als "zu-frueh" zu fuehren waere genau die Sorte
        # Beschoenigung, gegen die dieses Werkzeug gebaut wurde. Die Retro beefc148
        # schlug vor, die Reihenfolge zu drehen — der reproduzierte Fehlfall verschwindet
        # aber bereits durch den Bau-Tag-Ausschluss oben, und das Drehen haette echte
        # Signale unterdrueckt. Bewusst nicht uebernommen.
        if not gebaut:
            urteil = "ohne-datum"
        elif len(nachher) >= RUECKFALL_SCHWELLE:
            urteil = "RUECKFAELLIG"
        elif fenster < MIN_FENSTER:
            urteil = "zu-frueh"
        elif nachher:
            urteil = "beobachten"
        elif vorher:
            urteil = "wirksam"
        elif not vorher_messbar:
            # Kein Rueckfall, aber auch kein Vorher-Zeitraum in den Daten: darueber
            # laesst sich nichts sagen, und "unerprobt" waere schon zu viel Aussage.
            urteil = "kein-vorher-fenster"
        else:
            urteil = "unerprobt"

        ergebnis.append(
            {
                "slug": slug,
                "modus": gate.get("mode", "?"),
                "modul": gate.get("module"),
                "gebaut": gebaut,
                "umgebaut": umgebaut,
                "ref": gate.get("ref"),
                "vorher": len(vorher),
                "vorher_messbar": vorher_messbar,
                "nachher": len(nachher),
                "gefangen": len([d for d in gefangen if gebaut and d > gebaut]),
                "nur_tabelle": len(nur_tabelle_nachher),
                "letzter_rueckfall": nachher[-1] if nachher else None,
                "fenster_retros": fenster,
                "urteil": urteil,
            }
        )
    # Rueckfaellige zuerst, danach nach Zahl der Rueckfaelle.
    rang = {
        "RUECKFAELLIG": 0,
        "beobachten": 1,
        "zu-frueh": 2,
        "kein-vorher-fenster": 3,
        "unerprobt": 4,
        "wirksam": 5,
    }
    ergebnis.sort(key=lambda e: (rang.get(e["urteil"], 9), -e["nachher"], e["slug"]))
    return ergebnis


def kalibrier_stand(gate: dict, heute: str, hits_datei: str = "") -> dict | None:
    """Wie weit ist das Kalibrierfenster dieses Gates? ``None`` = keins offen.

    Ein Kalibrierfenster ist die Zusage "wir schalten spaeter scharf, wenn die
    Fehlalarm-Quote es hergibt". Bis zum 2026-08-23 stand diese Zusage nur als
    Prosa in `revision_note` — ein Datum, das niemand liest und nichts prueft.
    Die Frist 2026-09-03 des Claim-Gates lief deshalb auf **einer** Protokollzeile
    zu, und die trug einen leeren Ausschnitt: zaehlbar, nicht beurteilbar.

    Gezaehlt wird darum nicht "Treffer", sondern **beurteilbare** Treffer der
    genannten Klasse: eine Zeile ohne Ausschnitt ist kein Datenpunkt, sie ist ein
    Strich auf einem Zettel.
    """
    fenster = gate.get("kalibrierfenster")
    if not fenster:
        return None
    beurteilbar = 0
    gesamt = 0
    try:
        with open(hits_datei or GATE_HITS, encoding="utf-8") as datei:
            for zeile in datei:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    treffer = json.loads(zeile)
                except ValueError:
                    continue
                if treffer.get("slug") != gate.get("slug"):
                    continue
                if fenster.get("klasse", "") not in treffer.get("marker", ""):
                    continue
                if treffer.get("zeit", "")[:10] < fenster.get("seit", ""):
                    continue
                gesamt += 1
                if treffer.get("ausschnitt"):
                    beurteilbar += 1
    except OSError:
        # Fail-open: kein Protokoll heisst "nichts gemessen", nicht "alles gut".
        pass

    mindest = int(fenster.get("min_beurteilbar", 0))
    if mindest <= 0:
        # Ohne Mindestzahl kann das Fenster NIE entscheidungsreif werden — es
        # haengt bis zum Fristablauf in "sammelt" und faellt dann durch. Das ist
        # ein Konfigurationsfehler und gehoert gesagt, nicht ausgesessen
        # (Retro a84f71 Befund 4: der Rand war ungetestet und still).
        zustand = "unbestimmt"
    elif beurteilbar >= mindest:
        zustand = "entscheidungsreif"
    elif heute > fenster.get("bis", "9999-12-31"):
        zustand = "abgelaufen"
    else:
        zustand = "sammelt"
    return {
        "slug": gate.get("slug", "?"),
        "seit": fenster.get("seit", "?"),
        "bis": fenster.get("bis", "?"),
        "min_beurteilbar": mindest,
        "beurteilbar": beurteilbar,
        "gesamt": gesamt,
        "zustand": zustand,
    }


def kalibrier_zeile(stand: dict) -> str:
    if stand["zustand"] == "unbestimmt":
        return (
            f"Kalibrierfenster {stand['slug']}: keine Mindestzahl gesetzt "
            f"(`min_beurteilbar`) — das Fenster kann nie entscheidungsreif werden, "
            f"Frist {stand['bis']} liefe ins Leere"
        )
    if stand["zustand"] == "entscheidungsreif":
        return (
            f"Kalibrierfenster {stand['slug']}: {stand['beurteilbar']} beurteilbare "
            f"Zeile(n) — Mindestzahl {stand['min_beurteilbar']} erreicht, entscheiden "
            f"(scharf schalten oder Modus herabstufen)"
        )
    if stand["zustand"] == "abgelaufen":
        return (
            f"Kalibrierfenster {stand['slug']}: Frist {stand['bis']} abgelaufen mit "
            f"{stand['beurteilbar']} von {stand['min_beurteilbar']} beurteilbaren "
            f"Zeile(n) ({stand['gesamt']} protokolliert) — Frist traegt keine "
            f"Entscheidung, neu setzen oder Fenster aufgeben"
        )
    return (
        f"Kalibrierfenster {stand['slug']}: {stand['beurteilbar']}/"
        f"{stand['min_beurteilbar']} beurteilbar seit {stand['seit']}, Frist "
        f"{stand['bis']} — sammelt noch"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--dir", action="append", dest="dirs")
    parser.add_argument(
        "--kurz", action="store_true", help="eine Zeile fuer den Runner"
    )
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
        gates = registry.get("gates", [])
    except (OSError, ValueError) as fehler:
        # Fail-open: ein Melder, der den Sitzungsstart aufhaelt, wird abgeschaltet
        # und meldet danach gar nichts mehr.
        # `--kurz` schrieb diese Zeile bisher gar nicht, und im Nicht-kurz-Fall
        # ging sie nach stderr. Der Sitzungsstart ruft `--kurz 2>/dev/null` auf:
        # beide Unterdrueckungen zugleich. Leere Ausgabe liest der Runner als
        # PASS und behauptet dann "kein Gate rueckfaellig" — ein Satz ueber Gates, die nie
        # gelesen wurden. Fail-open bleibt (Exit 0, der Start laeuft weiter),
        # aber die Zeile geht nach STDOUT, damit daraus ein WARN wird statt
        # eines stillen Gruens (platform#2278).
        print(
            "Registry nicht lesbar — dieser Lauf misst nichts, kein Urteil ueber Gates"
        )
        if not args.kurz:
            print(f"  Grund: {fehler}", file=sys.stderr)
        return 0

    retros = lies_retros(args.dirs or standard_verzeichnisse())
    bewertet = bewerte(gates, retros)
    rueckfaellig = [e for e in bewertet if e["urteil"] == "RUECKFAELLIG"]
    heute = datetime.now(timezone.utc).date().isoformat()
    staende = [k for k in (kalibrier_stand(g, heute) for g in gates) if k]
    # Nur ein Fenster, das eine ENTSCHEIDUNG traegt, ist im Runner laut. Ein noch
    # sammelndes wuerde die Phase jede Sitzung auf WARN drehen — und ein Melder,
    # der immer feuert, wird gelesen wie einer, der nie feuert.
    laut = [
        k
        for k in staende
        if k["zustand"] in ("entscheidungsreif", "abgelaufen", "unbestimmt")
    ]

    if args.als_json:
        print(
            json.dumps(
                {"retros": len(retros), "gates": bewertet, "kalibrierfenster": staende},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.kurz:
        if not rueckfaellig and laut:
            print(kalibrier_zeile(laut[0]))
            for stand in laut[1:]:
                print(f"  · {kalibrier_zeile(stand)}")
            return 0
        if rueckfaellig:
            spitze = rueckfaellig[0]
            weitere = (
                f" (+{len(rueckfaellig) - 1} weitere)" if len(rueckfaellig) > 1 else ""
            )
            print(
                f"{len(rueckfaellig)} Gate(s) rueckfaellig — "
                f"{spitze['slug']}: {spitze['nachher']}x seit Bau {spitze['gebaut']}, "
                f"zuletzt {spitze['letzter_rueckfall']}{weitere}"
            )
            for eintrag in rueckfaellig[1:]:
                print(
                    f"  · {eintrag['slug']} — {eintrag['nachher']}x seit {eintrag['gebaut']}, "
                    f"zuletzt {eintrag['letzter_rueckfall']}"
                )
            for stand in laut:
                print(f"  · {kalibrier_zeile(stand)}")
        return 0

    daten = [_zerlege(r)[0] for r in retros]
    spanne = f"{daten[0]} .. {daten[-1]}" if daten else "keine"
    print(f"# Gate-Wirkung ueber {len(retros)} Retro-Reports ({spanne})\n")
    kopf = f"{'slug':<46}{'gebaut':<12}{'modus':<10}{'vor':>4}{'NACH':>6}  {'urteil':<19}letzter Rueckfall"
    print(kopf)
    print("-" * len(kopf))
    for e in bewertet:
        marke = "🚨" if e["urteil"] == "RUECKFAELLIG" else "  "
        vor = f"{e['vorher']}" + ("" if e["vorher_messbar"] else "*")
        # ~ markiert ein Datum, das vom Umbau stammt statt vom Erstbau — sonst liest
        # sich die Spalte, als sei das Gate erst gestern entstanden.
        datum = e["gebaut"] + ("~" if e.get("umgebaut") else "")
        print(
            f"{marke}{e['slug']:<44}{datum:<12}{e['modus']:<10}"
            f"{vor:>4}{e['nachher']:>6}  {e['urteil']:<19}{e['letzter_rueckfall'] or '—'}"
        )

    print()
    if rueckfaellig:
        print(
            f"→ {len(rueckfaellig)} Gate(s) RUECKFAELLIG: der Befund kam nach dem Bau des Gates "
            f"mindestens {RUECKFALL_SCHWELLE}x wieder."
        )
        print(
            "  Das ist ein Befund UEBER das Gate, nicht die N-te Wiederholung des Slugs. "
            "Drei ehrliche Antworten: Gate ausweiten (es sieht die Familie nicht), "
            "Gate umbauen (es feuert zu spaet), oder Modus herabstufen und in der "
            "declined-Liste begruenden."
        )
    else:
        print("→ Kein Gate rueckfaellig.")

    ohne_vorher = [e for e in bewertet if not e["vorher_messbar"]]
    if ohne_vorher:
        print(
            f"  (* {len(ohne_vorher)} Gate(s) aelter als das aelteste Retro — deren "
            "'vorher' ist das Ende des Datenfensters, kein Messwert.)"
        )

    nur_tabelle = [e for e in bewertet if e.get("nur_tabelle")]
    if nur_tabelle:
        namen = ", ".join(f"{e['slug']} ({e['nur_tabelle']}x)" for e in nur_tabelle)
        print(
            f"  ({len(nur_tabelle)} Gate(s) mit Rueckfaellen, die NUR in der Befund-Tabelle "
            f"stehen, nicht in der Frontmatter: {namen} — die Frontmatter ist selbst-"
            "etikettiert; seit 2026-09-02 zaehlen beide Quellen.)"
        )

    zu_frueh = [e for e in bewertet if e["urteil"] == "zu-frueh"]
    gefangen_gesamt = [e for e in bewertet if e.get("gefangen")]
    if gefangen_gesamt:
        namen = ", ".join(f"{e['slug']} ({e['gefangen']}x)" for e in gefangen_gesamt)
        print(
            f"  ({len(gefangen_gesamt)} Gate(s) haben ihren Befund GEFANGEN: {namen} — "
            "diese Vorkommen zaehlen nicht als Rueckfall, sie sind der Wirksamkeits-Beleg.)"
        )
    if zu_frueh:
        print(
            f"  ({len(zu_frueh)} Gate(s) 'zu-frueh' — weniger als {MIN_FENSTER} Retros seit Bau. "
            "Kein Rueckfall ist hier KEIN Wirksamkeits-Beleg.)"
        )

    if staende:
        print()
        print(
            "Offene Kalibrierfenster (Zusage 'spaeter scharf', mit Datum und Mindestzahl):"
        )
        for stand in staende:
            zeichen = {
                "entscheidungsreif": "🚨",
                "abgelaufen": "🚨",
                "unbestimmt": "🚨",
            }.get(stand["zustand"], "  ")
            print(f"  {zeichen} {kalibrier_zeile(stand)}")
        print(
            "  Gezaehlt werden BEURTEILBARE Zeilen (mit Ausschnitt), nicht Treffer: "
            "ein Fenster, das nichts beurteilen kann, kann auch nichts scharfschalten."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
