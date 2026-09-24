#!/usr/bin/env python3
"""befund_journal.py — Befunde des Session-Start-Runners ueber Sitzungen hinweg fuehren.

Warum es das gibt (gemessen 2026-08-16, platform#2004):
    Der Runner meldet jede Sitzung dieselben WARN-Zeilen mit derselben Lautstaerke.
    Fuenf `[deploy-health]`-Issues standen offen — apo-hub (10 Tage), trading-hub
    (10 Tage), travel-beat, cad-hub, tax-hub — **alle im Repo `platform`**, alle
    ueber andere Repos, keins bearbeitet. Erkannt hatte der Melder zuverlaessig;
    ein Leser fehlte. Und weil eine WARN-Zeile am zehnten Tag genauso klingt wie
    am ersten, gab es kein Signal, das den Unterschied traegt.

Zwei Dinge tut diese Datei, mehr nicht:

1. **Altern.** Jeder Befund bekommt einen Fingerabdruck (`phase::repo`) und faengt
   an zu zaehlen: erstmals gesehen, in wie vielen Runner-Laeufen, zuletzt wann.
   Der Runner haengt das an seine WARN-Zeile. Ein Altbefund sieht damit anders aus
   als ein neuer, ohne dass jemand sich erinnern muss.

2. **Das Zielrepo festhalten.** Ein Befund ueber `cad-hub` traegt `cad-hub`, nicht
   `platform`. `/session-ende` liest das (`--offen-cross-repo`) und laesst die
   Sitzung nicht abschliessen, solange ein Fremd-Repo-Befund weder ein Artefakt
   im Zielrepo noch einen abgelegten Verzicht hat.

Bewusst NICHT hier drin:
    Kein Anlegen von Issues, kein Netzzugriff, keine Bewertung. Das Journal ist ein
    Gedaechtnis, kein Handelnder — es sagt, was seit wann offen ist, und ueberlaesst
    das Urteil der Sitzung. (Ein Melder, der selbst Artefakte erzeugt, produziert als
    erstes das Reflex-Artefakt, das er beanstanden soll — Prio-4-Lehre vom 2026-08-15.)

Heilung und Abdeckungsluecken sind bewusst verschieden behandelt:
    Ein Befund verschwindet nur, wenn **seine Phase lief** und ihn nicht mehr nennt.
    Lief die Phase gar nicht (0.7 erreicht z.B. `trading-hub` regelmaessig nicht),
    bleibt der Eintrag stehen und altert **nicht** weiter. Sonst wuerde eine
    Abdeckungsluecke wie eine Heilung aussehen — der teuerste Fehler, den ein
    Melder-Gedaechtnis machen kann.

Heilung ist ausserdem an dasselbe Zielrepo gebunden, wo eine Phase je Lauf nur
EIN Repo kennen kann (#3470, gemessen 2026-09-24): Ein Lauf mit
`TARGET_REPO=platform` legte `0.7.26 ci-deckung::platform` an; ein PARALLELER
Lauf mit `TARGET_REPO=robo-lab` sah dieselbe Phase in seinem eigenen Lauf
"geurteilt" und loeschte den platform-Eintrag, obwohl er dessen Zielrepo nie
erreichen konnte — `laeufe`, `erstmals`, `entscheiden_bis` und ein gesetzter
Anker gingen verloren. Ob eine Phase pro Lauf nur ein Repo melden kann
(`$TARGET_REPO` in `tools/session_start_checks.sh`, z.B. 0.4 parallel-sessions,
0.4.1 reflex, 0.7.4 prio-referenzen, 0.7.26 ci-deckung) oder flottenweit mehrere
Repos in jedem Lauf sieht (0.7 deploy-scan, 0.7.12 prod-wirkung, 0.7.16
origin-tls, …), steht je Phase in `governance/melder-register.yaml` als
`zielgebunden: true|false` (Default `false` = flottenweit, bisheriges
Verhalten). Fuer eine zielgebundene Phase heilt ein Eintrag nur, wenn der Lauf
dasselbe Zielrepo hatte wie der Eintrag; alles andere heilt weiterhin, sobald
seine Phase lief und es nicht mehr meldet. Fehlt einer gelaufenen Phase der
Register-Eintrag, gilt derselbe Default (flottenweit) — mit einer Warnzeile im
Bericht, statt die Luecke stillschweigend zu schliessen.

Zustand liegt lokal (`~/.claude/befund-journal.json`), nicht im Repo: die Notizen
tragen Ausschnitte des eigenen Laufs und sind maschinengebunden — dieselbe Grenze
wie bei `gate_hits.py` (Charta Art. 2).

Kommandos:
  --aufnehmen              TSV auf stdin: phase<TAB>status<TAB>repos<TAB>note
                           Aktualisiert das Journal, schreibt die Alters-Zeilen nach stdout.
  --bericht                Offene Befunde zeigen (Alter, Zielrepo, Verankerung).
  --offen-cross-repo       Exit 1, wenn ein Fremd-Repo-Befund ohne Artefakt/Verzicht offen ist.
  --verankert ID URL       Artefakt im Zielrepo hinterlegen.
  --verzichtet ID GRUND    Bewusst nicht verfolgen — mit Grund, sonst zaehlt es nicht.
  --beleg ID ...           Kommando, Ausgabe, Knoten, Positivkontrolle an einen Befund haengen.
  --fix ID --pr URL --wirkung "<Satz>" [--messung YYYY-MM-DD]
                           Fix in Arbeit vermerken: PR, erwartete Wirkung, Messdatum.
  --bericht --json         Dieselben Daten maschinenlesbar — fuer eine Leseflaeche
                           ausserhalb dieser Maschine (KONZ-054 E2).
  --praezision --json      Trefferquote je Melder maschinenlesbar (#2690 K3) —
                           Basis fuer tools/melder_register_check.py --herabstufung.
  --deklaration ZIEL --art ART --grund "<Satz>" --gueltig-bis YYYY-MM-DD [--quelle TEXT]
                           Ausnahme mit Ablauf setzen (#3495 V2) — ZIEL ist Host,
                           Dienst oder Journal-Schluessel.

Seit 2026-08-30 (KONZ-platform-054 E2) drei Dinge mehr, alle aus derselben Messung:
    17 Befunde offen, 0 verankert, 12 ohne Frist — und 7 davon waren platform-eigene
    Infra-Befunde, die das Gate per Eigen-Repo-Ausnahme gar nicht sah. Deshalb:
    (1) Infra-Phasen (``INFRA_PHASEN``) laufen ins Gate, auch wenn ihr Repo `platform`
        ist — ein Swap-Befund auf prod ist ein Arbeitsauftrag, kein lokaler Zustand.
    (2) Jeder neue Befund bekommt eine Entscheidungsfrist (``entscheiden_bis``): bis
        dahin ist er zu verankern oder mit Grund abzulegen. Ein Befund ohne Frist
        gilt nicht — er wuerde nur altern, und Alter allein hat niemanden bewegt.
    (3) Ein Befund traegt Kommando, Ausgabe, Knoten und Positivkontrolle, wenn der
        Melder sie liefert. Ohne sie muss der Leser jede Zeile selbst nachmessen —
        und dann spart der Melder nichts (Maintainer-2028-Einwand zu KONZ-054).

Seit 2026-09-24 (#3495 V4) ein viertes Feld: Fix in Arbeit. Der Advocatus-Diabolus-
Befund L2 (Kommentar in #3471) stellte fest, dass das Journal keine laufende
Reparatur kennt — eine neue Sitzung sieht dieselbe WARN-Zeile und fixt sie ein
zweites Mal. Real passiert: #3465 und #3466 fixten unabhaengig voneinander
denselben Befund, weil keine Sitzung sehen konnte, dass die andere schon dabei
war. `--fix ID --pr URL --wirkung "<Satz>" [--messung DATUM]` haengt PR,
erwartete Wirkung und ein Messdatum an einen Befund; `--bericht` zeigt die Zeile,
und liegt das Messdatum in der Vergangenheit, waehrend der Eintrag weiterhin im
Journal steht (Phase hat ihn nicht geheilt), markiert der Bericht ihn als
ueberfaellig — dieselbe Ruhe-vs-laut-Mechanik wie bei
`entscheiden_bis`, nur fuer den laufenden Fix statt fuer den Erstbefund.

Seit 2026-09-24 (#3495 V2) Deklarationen — Ausnahmen mit Pflicht-Ablaufdatum:
    Der Sonderfall "Knoten mit `betrieb: auf_zuruf` ist unerreichbar -> schlaeft,
    kein Befund" war fuenfmal gebaut (`flottenbild.py`, `speicher_melder.py`,
    `reconcile_registry_live.py`, `host_datei_drift.py`, `deploy-script-drift.sh`),
    jede Kopie las `infra/hosts.yaml` selbst, und keine kannte ein Ende — eine
    Ausnahme ohne Ablauf ist eine Dauerausnahme (Advocatus-Diaboli-Befund E1a,
    #3471). Jetzt gibt es EINE Lesefunktion, ``deklarationen_fuer(ziel, heute,
    art)``, und alle Melder fragen nur sie. Arten: ``DEKLARATIONS_ARTEN``. Ein
    Eintrag ohne ``gueltig_bis`` ist ungueltig und wirkt nicht; ein abgelaufener
    wirkt nicht und steht im Bericht als ``⏰ Deklaration abgelaufen`` — der
    Melder meldet den Knoten ab dem Tag danach wieder.

    Quelle ist ``governance/deklarationen.json`` im Repo, nicht die lokale
    Journal-Datei. Grund: `reconcile_registry_live.py` laeuft taeglich auf dem
    Prod-Runner (`.github/workflows/registry-live-reconcile.yml`), wo es kein
    `~/.claude/befund-journal.json` gibt — laege die Deklaration nur lokal, kaeme
    dort `C0:gpu-box` zurueck, genau der Fund, den #3479 abgestellt hat. Eine
    Deklaration ist ausserdem eine Owner-Entscheidung und kein Laufausschnitt; sie
    traegt nichts, was nach Charta Art. 2 lokal bleiben muss, und wird wie jede
    Entscheidung per PR sichtbar. `infra/hosts.yaml` fuehrt das Feld `betrieb:
    auf_zuruf` nicht mehr, der Knoten-Eintrag nennt nur die Herkunft; ein Test
    (`test_should_not_declare_auf_zuruf_in_hosts_yaml`) haelt das Feld dort fern,
    damit keine zweite Quelle nachwaechst. Gesetzt wird mit
    `--deklaration ZIEL --art ART --grund "<Satz>" --gueltig-bis YYYY-MM-DD`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _lade_melder_register_check():
    """`melder_register_check.py` per Dateipfad laden, nicht per `import`.

    Register-Lader wiederverwenden statt zweite Kopie (#2895): dieselbe
    `lade_register()` wie `tools/melder_register_check.py --kurz` liest,
    damit genau eine Stelle YAML->dict versteht. Ein normaler `import
    melder_register_check` verlaesst sich auf `sys.path` — das traegt beim
    Skriptaufruf (Python haengt das eigene Verzeichnis automatisch an) und
    beim `import befund_journal` nach `sys.path.insert(...tools...)`, bricht
    aber, sobald ein Aufrufer dieses Modul per `importlib.spec_from_file_
    location` laedt (so tut es `tools/tests/test_befund_praezision.py`) —
    dann ist `tools/` nirgends in `sys.path`. Der Dateipfad relativ zu
    `__file__` ist ladeartunabhaengig.
    """
    pfad = Path(__file__).resolve().parent / "melder_register_check.py"
    spec = importlib.util.spec_from_file_location("melder_register_check", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_mrc = _lade_melder_register_check()

#: Nur lokal — die Notizen tragen Ausschnitte des eigenen Laufs (Charta Art. 2).
JOURNAL = Path(
    os.environ.get(
        "BEFUND_JOURNAL_DATEI", Path.home() / ".claude" / "befund-journal.json"
    )
)

#: Maschinenlesbarer Kopf (KONZ-038 D8) — muss im Modul stehen, nicht nur in der
#: Registry, sonst verrottet er still.
GATE_HEADER = {
    "slug": "cross-repo-befund-ohne-artefakt-im-zielrepo",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-08-16",
    "evidence": "tools/tests/test_befund_journal.py",
}

#: Ab so vielen Laeufen gilt ein Befund als Altbefund und wird eigens ausgewiesen.
#: Drei, weil zwei noch Zufall sein koennen und vier schon eine Woche ist.
ALT_AB_LAEUFEN = 3

#: Wiedervorlage-Fristen in Tagen. Ein verankerter oder mit Verzicht abgelegter
#: Befund ruht bis zum Fristende — er verschwindet NICHT, er wird nur leise.
#:
#: Warum ueberhaupt: `--verankert` hing bis 2026-08-23 nur eine URL an die Zeile und
#: aenderte an ihrer Lautstaerke nichts. Der Deploy-Befund zu `coach-hub` war seit dem
#: 2026-08-20 in coach-hub#67 verankert und erschien trotzdem in **22 aufeinander-
#: folgenden Laeufen** wortgleich. Wer 22-mal dieselbe Zeile liest, liest die 23. nicht
#: mehr — und uebersieht darin den neuen Befund. Das Journal misst Alter (K3) seit
#: 2026-08-16; was fehlte, war die Erlaubnis zu schweigen.
#:
#: 14 Tage fuer ein Artefakt: lang genug, dass ein Issue bearbeitet werden kann, kurz
#: genug, dass ein liegengebliebenes im selben Monat zurueckkommt. 30 fuer den Verzicht:
#: er ist eine getroffene Entscheidung, wird aber nicht unbefristet geglaubt.
FRIST_VERANKERT_TAGE = 14
FRIST_VERZICHT_TAGE = 30

#: Phasen, deren Befund ein **Arbeitsauftrag im genannten Repo** ist — nur sie
#: laufen in das Abschluss-Gate von `/session-ende`.
#:
#: Bewusst mit genau einer Phase gestartet, und zwar nach einer Messung statt nach
#: einem Gefuehl: der erste scharfe Lauf am 2026-08-16 haette drei Repos gefordert,
#: aber nur eines davon zu Recht. `0.4 repo-sync` meldete `risk-hub:GUARD(dirty)` —
#: das ist ein **lokaler** Zustand des Arbeitsbaums (fremde Sitzung moeglich, nicht
#: anfassen), kein Defekt im Repo `risk-hub`; ein Issue dort waere Unsinn gewesen.
#: `0.7 deploy-scan` dagegen meldet einen roten Prod-Deploy — der gehoert genau
#: dorthin, und dass er es bisher nicht tat, ist der Anlass fuer platform#2004.
#:
#: Die Liste waechst durch Belege, nicht durch Vollstaendigkeitsdrang: eine Phase
#: kommt dazu, wenn ein konkreter Befund von ihr in einem fremden Repo repariert
#: werden musste. Ein zu breites Gate produziert Fehlalarme, und ein Gate, das oft
#: falsch feuert, wird abgeschaltet — dann meldet es gar nichts mehr (#1508).
#: Das Journal fuehrt trotzdem ALLE Repos: Alter (K3) gilt fuer jeden Befund,
#: nur die Artefakt-Pflicht (K2) ist eng.
#: `0.7.12 prod-wirkung` kam am 2026-08-23 dazu, und zwar mit Beleg statt aus
#: Symmetrie: risk-hub stand beim ersten Lauf vier Tage hinter `origin/main`
#: (Prod-Gate, `staging`-Default) und writing-hub frisch — beides Befunde, die
#: in ihrem eigenen Repo repariert werden, nicht hier. Bei tax-hub blieb genau
#: diese Klasse sieben Tage unsichtbar, weil kein Check davon rot wird (#2148).
CROSS_REPO_PHASEN = ("0.7 deploy-scan", "0.7.12 prod-wirkung")

#: Phasen, deren Befund ein **Infra-Arbeitsauftrag** ist — egal in welchem Repo er
#: gefuehrt wird. Sie laufen ins Abschluss-Gate auch dann, wenn `repo` das eigene ist.
#:
#: Anlass (gemessen 2026-08-30, KONZ-platform-054): 7 von 17 offenen Befunden waren
#: platform-eigene Infra-Befunde — Swap 99,8 % auf prod, tote vhosts, Backup-Luecke —
#: und genau die nahm `_cross_repo_offen` per `repo == eigenes_repo` vom Gate aus.
#: Die Ausnahme war fuer lokale Zustaende gedacht (dirty Arbeitsbaum), nicht fuer
#: Befunde ueber Produktionsknoten. Die Liste ist eng und waechst durch Belege.
INFRA_PHASEN = (
    "0.1 server-probe",
    "0.7.11 erreichbarkeit",
    "0.7.16 origin-tls",
    "0.7.17 backup-deckung",
    "0.7.18 speicher",
    "0.7.2 cron-melder",
    "0.7.20 umgebung",
    "0.7.21 alarmweg",
    "0.7.22 flottenbild",
)

#: Entscheidungsfrist in Tagen fuer einen NEUEN Befund: bis dahin verankern oder mit
#: Grund ablegen. Sieben, weil das eine Arbeitswoche ist und ein Befund, ueber den
#: eine Woche lang niemand entschieden hat, nicht leiser werden darf, sondern lauter.
#: Getrennt von `wiedervorlage` (Ruhefrist NACH einer Entscheidung) — ein Feld fuer
#: beides haette jeden neuen Befund zum Schweigen gebracht.
FRIST_ENTSCHEIDUNG_TAGE = 7

#: Default-Messfrist in Tagen fuer ``--fix``, wenn ``--messung`` fehlt (#3495 V4).
#: Sieben, aus demselben Grund wie bei ``FRIST_ENTSCHEIDUNG_TAGE``: eine
#: Arbeitswoche ist genug Zeit fuer den naechsten Runner-Lauf, der die Wirkung
#: pruefen kann, und kurz genug, dass ein liegengebliebener Fix nicht monatelang
#: als "in Arbeit" gilt.
FRIST_FIX_MESSUNG_TAGE = 7

#: Beleg-Felder je Befund (KONZ-054 E2). Optional — aber ein Befund ohne sie ist
#: fuer den Leser um 03:00 eine Behauptung, kein Befund.
BELEG_FELDER = ("knoten", "kommando", "ausgabe", "positivkontrolle")


def _heute() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _frist(tage: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=tage)).date().isoformat()


# ── Deklarationen (#3495 V2) ─────────────────────────────────────────────────

#: Arten einer Deklaration. `auf_zuruf`: Knoten laeuft planmaessig nur auf Zuruf,
#: Unerreichbarkeit ist kein Befund. `verzicht`: Befund bewusst nicht verfolgt.
#: `stundung`: Befund bekannt, Behebung terminiert. `betriebsstatus`: Dienst
#: planmaessig nicht aktiv (Vokabular `tools/betriebsstatus.py`).
DEKLARATIONS_ARTEN = ("auf_zuruf", "verzicht", "stundung", "betriebsstatus")

#: Relativ zur Repo-Wurzel. Warum im Repo und nicht lokal: Modul-Docstring,
#: Abschnitt "Deklarationen".
DEKLARATIONEN_REL = Path("governance") / "deklarationen.json"

_DEKLARATIONEN_HINWEIS = (
    "Verwaltet von tools/befund_journal.py --deklaration (#3495 V2). "
    "Jeder Eintrag braucht gueltig_bis; gelesen wird nur ueber deklarationen_fuer()."
)


def _deklarationen_pfad(pfad: Path | None = None) -> Path:
    """Explizit > ``$BEFUND_DEKLARATIONEN_DATEI`` > Repo-Datei.

    Die Umgebungsvariable wird bei JEDEM Aufruf gelesen, nicht beim Import —
    Tests und Werkzeuge ohne eigenen Pfad-Parameter (``reconcile_registry_live``)
    lenken sie so auf eine Fixture um.
    """
    if pfad is not None:
        return Path(pfad)
    env = os.environ.get("BEFUND_DEKLARATIONEN_DATEI")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / DEKLARATIONEN_REL


def lade_deklarationen(pfad: Path | None = None) -> list[dict]:
    """Alle Eintraege, auch ungueltige und abgelaufene — fuer den Bericht.

    Eine fehlende oder kaputte Datei ergibt ``[]``: dann gilt keine Ausnahme, und
    die Melder melden laut. Das ist die sichere Richtung — eine verlorene
    Deklaration erzeugt einen Befund, nie ein Schweigen.
    """
    try:
        daten = json.loads(_deklarationen_pfad(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    liste = daten.get("deklarationen") if isinstance(daten, dict) else None
    if not isinstance(liste, list):
        return []
    return [d for d in liste if isinstance(d, dict)]


def deklarations_fehler(d: dict) -> str | None:
    """Warum dieser Eintrag nicht wirken darf — oder ``None``, wenn er gueltig ist."""
    if d.get("art") not in DEKLARATIONS_ARTEN:
        return (
            f"art '{d.get('art')}' unbekannt (erlaubt: {', '.join(DEKLARATIONS_ARTEN)})"
        )
    if not str(d.get("ziel") or "").strip():
        return "ziel fehlt"
    if not str(d.get("grund") or "").strip():
        return "grund fehlt"
    bis = str(d.get("gueltig_bis") or "").strip()
    if not bis:
        return "gueltig_bis fehlt — ohne Ablauf waere es eine Dauerausnahme"
    try:
        date.fromisoformat(bis)
    except ValueError:
        return f"gueltig_bis '{bis}' ist kein Datum YYYY-MM-DD"
    return None


def _tag(heute: str | date | None) -> str:
    if isinstance(heute, date):
        return heute.isoformat()
    return heute or _heute()


def deklarationen_fuer(
    ziel: str,
    heute: str | date | None = None,
    art: str | None = None,
    pfad: Path | None = None,
) -> list[dict]:
    """DIE Lesefunktion: gueltige, nicht abgelaufene Deklarationen fuer ``ziel``.

    ``ziel`` ist ein Host (Schluessel in `infra/hosts.yaml`), ein Dienst oder ein
    Journal-Schluessel. ``art`` filtert (z. B. ``"auf_zuruf"``). Am Tag
    ``gueltig_bis`` wirkt die Deklaration noch, am Tag danach nicht mehr.
    Ungueltige Eintraege (ohne Ablauf, unbekannte Art) wirken nie.
    """
    tag = _tag(heute)
    return [
        d
        for d in lade_deklarationen(pfad)
        if str(d.get("ziel", "")).strip() == ziel
        and (art is None or d.get("art") == art)
        and deklarations_fehler(d) is None
        and tag <= date.fromisoformat(str(d["gueltig_bis"]).strip()).isoformat()
    ]


def setze_deklaration(
    ziel: str,
    art: str,
    grund: str,
    gueltig_bis: str,
    quelle: str = "",
    pfad: Path | None = None,
    heute: str | None = None,
) -> dict:
    """Deklaration anlegen oder ersetzen (Schluessel: ziel + art).

    Wirft ``ValueError`` bei einem ungueltigen Eintrag und ``OSError``, wenn die
    Datei nicht geschrieben werden kann.
    """
    neu = {
        "ziel": ziel.strip(),
        "art": art,
        "grund": grund.strip(),
        "quelle": quelle.strip(),
        "gesetzt_am": heute or _heute(),
        "gueltig_bis": gueltig_bis.strip(),
    }
    fehler = deklarations_fehler(neu)
    if fehler:
        raise ValueError(fehler)
    liste = [
        d
        for d in lade_deklarationen(pfad)
        if not (str(d.get("ziel", "")).strip() == neu["ziel"] and d.get("art") == art)
    ]
    liste.append(neu)
    liste.sort(key=lambda d: (str(d.get("ziel", "")), str(d.get("art", ""))))
    p = _deklarationen_pfad(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"hinweis": _DEKLARATIONEN_HINWEIS, "deklarationen": liste},
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return neu


def deklarations_zeilen(
    deklarationen: list[dict], heute: str | None = None
) -> list[str]:
    """Bericht-Zeilen: eine Summe fuer die aktiven, je eine Zeile fuer abgelaufene
    und ungueltige — die leisen Ausnahmen sind genau die, die man sehen muss."""
    tag = _tag(heute)
    aktiv, abgelaufen, kaputt = [], [], []
    for d in deklarationen:
        fehler = deklarations_fehler(d)
        if fehler:
            kaputt.append((d, fehler))
        elif tag > date.fromisoformat(str(d["gueltig_bis"]).strip()).isoformat():
            abgelaufen.append(d)
        else:
            aktiv.append(d)
    zeilen = []
    if aktiv:
        naechste = min(aktiv, key=lambda d: str(d["gueltig_bis"]))
        zeilen.append(
            f"  {len(aktiv)} Deklaration(en) aktiv, nächste Fälligkeit "
            f"{naechste['gueltig_bis']} ({naechste['ziel']} [{naechste['art']}])"
        )
    for d in abgelaufen:
        zeilen.append(
            f"  ⏰ Deklaration abgelaufen: {d['ziel']} [{d['art']}] gueltig bis "
            f"{d['gueltig_bis']} — wirkt nicht mehr, die Melder melden wieder. "
            f"Verlaengern: --deklaration '{d['ziel']}' --art {d['art']} "
            "--grund '<Satz>' --gueltig-bis YYYY-MM-DD"
        )
    for d, fehler in kaputt:
        zeilen.append(
            f"  ⚠ Deklaration ungueltig ({fehler}): {d.get('ziel') or '?'} "
            f"[{d.get('art') or '?'}] — wirkt nicht"
        )
    return zeilen


def ruhezustand(eintrag: dict, heute: str) -> str:
    """Wie laut darf dieser Befund sein? ``laut`` | ``faellig`` | ``ruht``.

    Drei Wege aus der Ruhe, und alle drei sind Absicht:
      * keine Frist gesetzt        -> laut (nichts hat je jemand entschieden)
      * Frist abgelaufen           -> faellig (die Entscheidung ist zu pruefen)
      * Symptomtext hat sich geaendert -> laut (es ist nicht mehr derselbe Befund,
        auf den sich die Entscheidung bezog)

    Die dritte ist die wichtigste: eine Parkerlaubnis gilt fuer den Befund, der
    beim Parken vorlag, nicht fuer alles, was spaeter unter derselben ID auftaucht.
    """
    frist = eintrag.get("wiedervorlage")
    if not frist:
        return "laut"
    if (
        eintrag.get("ruht_note") is not None
        and eintrag.get("letzte_note") != eintrag["ruht_note"]
    ):
        return "laut"
    return "faellig" if heute > str(frist) else "ruht"


def lade(pfad: Path | None = None) -> dict:
    """Journal lesen. Ein kaputtes Journal blockiert nie — es startet neu.

    Der Runner darf an dieser Datei nicht scheitern; ein Melder, der die Sitzung
    aufhaelt, wird abgeschaltet und meldet danach gar nichts mehr.
    """
    p = pfad or JOURNAL
    try:
        daten = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"befunde": {}}
    if not isinstance(daten, dict) or not isinstance(daten.get("befunde"), dict):
        return {"befunde": {}}
    return daten


def sichere(daten: dict, pfad: Path | None = None) -> bool:
    p = pfad or JOURNAL
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def fingerabdruck(phase: str, repo: str) -> str:
    """Stabiler Schluessel. Bewusst OHNE den Notiztext.

    Die Notiz traegt wechselnde Zahlen (`9/10 Repos`, Commit-Abstaende); waere sie
    Teil des Schluessels, waere jeder Lauf ein neuer Befund und nichts wuerde je
    altern. Phase + Zielrepo ist die Frage, die zaehlt: „meldet dieselbe Pruefung
    seit wann dasselbe Repo?"
    """
    return f"{phase.strip()}::{repo.strip() or '-'}"


def _zeilen_lesen(text: str) -> list[dict]:
    """TSV vom Runner in Datensaetze wandeln. Kaputte Zeilen werden uebergangen."""
    saetze = []
    for roh in text.splitlines():
        if not roh.strip():
            continue
        teile = roh.split("\t")
        if len(teile) < 2:
            continue
        phase, status = teile[0].strip(), teile[1].strip().upper()
        repos = teile[2].strip() if len(teile) > 2 else ""
        note = teile[3].strip() if len(teile) > 3 else ""
        ungeprueft = teile[4].strip() if len(teile) > 4 else ""
        satz = {
            "phase": phase,
            "status": status,
            "repos": [r for r in repos.split() if r],
            "note": note,
            "ungeprueft": [r for r in ungeprueft.split() if r],
        }
        # Spalten 6-9 sind die Beleg-Felder, in der Reihenfolge von BELEG_FELDER.
        # Ein Melder, der sie nicht liefert, laesst sie leer — der Befund wird
        # trotzdem gefuehrt, nur eben als unbelegter.
        for i, feld in enumerate(BELEG_FELDER, start=5):
            wert = teile[i].strip() if len(teile) > i else ""
            if wert:
                satz[feld] = wert
        saetze.append(satz)
    return saetze


def _zielgebunden(phase: str, by_phase: dict[str, dict]) -> bool | None:
    """``zielgebunden``-Flag der Phase aus dem Register, oder ``None`` wenn kein
    Eintrag existiert (Aufrufer entscheidet dann per Default + Warnung, #3470)."""
    eintrag = by_phase.get(phase)
    if eintrag is None:
        return None
    return bool(eintrag.get("zielgebunden", False))


def aufnehmen(
    saetze: list[dict],
    daten: dict,
    lauf_repo: str = "",
    register: list[dict] | None = None,
) -> list[str]:
    """Journal fortschreiben und die Alters-Zeilen zurueckgeben.

    Regeln, in dieser Reihenfolge:
      - WARN/FAIL mit Repo r  -> Eintrag `phase::r` anlegen oder altern lassen.
      - PASS                  -> alle Eintraege DIESER Phase heilen (entfernen).
      - WARN ohne dieses Repo -> Eintrag der Phase fuer nicht mehr genannte Repos heilen.
      - Phase gar nicht dabei -> Eintrag bleibt unveraendert stehen (Abdeckungsluecke,
                                 keine Heilung — er altert aber auch nicht weiter).

    ``lauf_repo`` ist das Zielrepo DIESES Laufs (`--repo`/`$TARGET_REPO`). Eine
    Phase, die im Register (`governance/melder-register.yaml`) als
    ``zielgebunden: true`` gefuehrt wird, heilt nur, wenn ihr Eintrag dasselbe
    Repo traegt wie ``lauf_repo`` — sonst konnte DIESER Lauf das Zielrepo des
    Eintrags gar nicht erreichen und "geurteilt" haette nur wegen eines fremden
    Repos (#3470). ``register`` ist wie bei ``praezision()`` ein reiner
    Parameter, keine versteckte Disk-Lesung: ohne Angabe gilt ``[]`` — jede
    Phase dann ohne Register-Eintrag, also Default flottenweit (unveraendertes
    Verhalten fuer Aufrufer, die den Parameter nicht kennen).
    """
    befunde = daten.setdefault("befunde", {})
    heute = _heute()
    gelaufene_phasen = {s["phase"] for s in saetze}
    by_phase = _mrc.register_zuordnung(register or [])
    # Fingerabdruecke, ueber die diese Phase KEIN Urteil faellen konnte.
    ungeprueft: set[str] = {
        fingerabdruck(s["phase"], r) for s in saetze for r in s.get("ungeprueft", [])
    }
    noch_gemeldet: set[str] = set()
    meldungen: list[str] = []

    for satz in saetze:
        if satz["status"] not in ("WARN", "FAIL"):
            continue
        repos = satz["repos"] or ["-"]
        for repo in repos:
            fid = fingerabdruck(satz["phase"], repo)
            noch_gemeldet.add(fid)
            eintrag = befunde.get(fid)
            belege = {f: satz[f] for f in BELEG_FELDER if satz.get(f)}
            if eintrag is None:
                befunde[fid] = {
                    "phase": satz["phase"],
                    "repo": repo,
                    "erstmals": heute,
                    "zuletzt": heute,
                    "laeufe": 1,
                    "letzte_note": satz["note"],
                    "artefakt": None,
                    "verzicht": None,
                    "entscheiden_bis": _frist(FRIST_ENTSCHEIDUNG_TAGE),
                    **belege,
                }
                continue
            eintrag["laeufe"] = int(eintrag.get("laeufe", 0)) + 1
            eintrag["zuletzt"] = heute
            eintrag["letzte_note"] = satz["note"]
            eintrag["repo"] = repo
            eintrag["phase"] = satz["phase"]
            # Altbestand ohne Frist bekommt sie jetzt — ab heute, nicht rueckwirkend:
            # rueckwirkend waeren alle 17 sofort ueberfaellig und das Gate wuerde
            # als Rauschen abgeschaltet, statt gelesen.
            eintrag.setdefault("entscheiden_bis", _frist(FRIST_ENTSCHEIDUNG_TAGE))
            eintrag.update(belege)

    # Heilung: nur fuer Phasen, die in DIESEM Lauf tatsaechlich geurteilt haben —
    # und nur fuer Repos, die diese Phase auch erreichen konnte. Fuer eine
    # zielgebundene Phase heisst "erreichen konnte" zusaetzlich: der Lauf hatte
    # dasselbe Zielrepo wie der Eintrag (#3470) — sonst heilt ein Lauf mit
    # TARGET_REPO=robo-lab einen Befund, den nur TARGET_REPO=platform je sehen
    # konnte, und `laeufe`/`erstmals`/`entscheiden_bis`/Anker gehen verloren.
    ungeregistrierte_phasen: set[str] = set()
    for fid in list(befunde):
        eintrag = befunde[fid]
        phase = eintrag.get("phase")
        if not (
            phase in gelaufene_phasen
            and fid not in noch_gemeldet
            and fid not in ungeprueft
        ):
            continue
        zg = _zielgebunden(phase, by_phase)
        if zg is None:
            ungeregistrierte_phasen.add(phase)
            zg = False
        if zg and eintrag.get("repo") != lauf_repo:
            continue  # zielgebunden, aber fremdes Zielrepo -> keine Heilung
        del befunde[fid]

    ruhend = []
    for fid, e in sorted(befunde.items(), key=lambda kv: -int(kv[1].get("laeufe", 0))):
        if fid not in noch_gemeldet:
            continue
        laeufe = int(e.get("laeufe", 0))
        zustand = ruhezustand(e, heute)
        if zustand == "ruht":
            ruhend.append(e)
            continue
        if laeufe < ALT_AB_LAEUFEN and zustand != "faellig":
            continue
        marke = "⏰ WIEDERVORLAGE" if zustand == "faellig" else "⏳ ALTBEFUND"
        anhang = ""
        if e.get("artefakt"):
            anhang = f" · verankert: {e['artefakt']}"
        elif e.get("verzicht"):
            anhang = f" · Verzicht: {e['verzicht'].get('grund', '')}"
        if zustand == "faellig":
            anhang += f" · Frist {e.get('wiedervorlage')} abgelaufen — Stand pruefen"
        meldungen.append(
            f"  {marke} {e['phase']} · Repo {e['repo']} — "
            f"{laeufe} Laeufe, erstmals {e['erstmals']}{anhang}"
        )

    # Nichts verschwindet still: die Ruhenden bekommen EINE Sammelzeile mit der
    # naechsten faelligen Frist. Ohne sie waere Schweigen von Vergessen nicht zu
    # unterscheiden — und genau das waere die schlimmere Krankheit.
    if ruhend:
        naechste = min(str(e.get("wiedervorlage", "")) for e in ruhend)
        meldungen.append(
            f"  ⏸ {len(ruhend)} Befund(e) ruhen bis zur Wiedervorlage "
            f"(naechste {naechste}) — Vollbild: tools/befund_journal.py --bericht"
        )
    if ungeregistrierte_phasen:
        meldungen.append(
            f"  ⚠ {len(ungeregistrierte_phasen)} Phase(n) ohne Eintrag in "
            "governance/melder-register.yaml — Heilung default flottenweit "
            "(zielgebunden unbekannt): " + ", ".join(sorted(ungeregistrierte_phasen))
        )
    return meldungen


# Ab so vielen Urteilen wird eine Praezision ueberhaupt ausgewiesen. Darunter ist
# jede Quote ein Zufallswert — und ein Melder wegen zweier Fehlalarme abzuwerten
# waere schlimmer als gar nicht zu messen.
MIN_URTEILE = 3

# Unter dieser Praezision erzieht ein Melder zum Wegsehen. Kein Automatismus haengt
# daran: die Zahl ist ein Gespraechsanlass, keine Abschaltung.
PRAEZISION_SCHWELLE = 0.6


def urteile_dazu(daten: dict, fid: str, urteil: str, grund: str) -> dict | None:
    """Ein Urteil ueber einen Befund festhalten: war er echt oder ein Fehlalarm?

    **Die Historie liegt bewusst NEBEN den Befunden, nicht in ihnen.** Ein Eintrag
    verschwindet, sobald seine Phase ihn nicht mehr meldet (Heilung) — und mit ihm
    waere jedes Urteil weg. Die Praezision eines Melders liesse sich dann genau so
    lange messen, wie sein Fehlalarm noch offen steht: also nie.
    """
    eintrag = daten.get("befunde", {}).get(fid)
    daten.setdefault("urteile", []).append(
        {
            "fid": fid,
            "phase": (eintrag or {}).get("phase") or fid.split("::")[0],
            "repo": (eintrag or {}).get("repo") or (fid.split("::") + ["-"])[1],
            "urteil": urteil,
            # Der BEURTEILTE Text, nicht die Begruendung des Urteils. `grund`
            # entsteht NACH dem Urteil und nennt es meist mit — als Eingabe fuer
            # eine spaetere Auswertung verraet er die Antwort. `eingabe` ist das,
            # was der Melder gemeldet hat, bevor jemand darauf geschaut hat.
            # Ohne dieses Feld sind die Urteile Etiketten ohne Gegenstand: die
            # 51 Urteile bis zum 2026-09-21 lassen sich nicht mehr zuordnen,
            # weil ihre Meldetexte nirgends mitgeschrieben wurden (#3337).
            "eingabe": (eintrag or {}).get("letzte_note"),
            "grund": grund,
            "datum": _heute(),
        }
    )
    if eintrag is not None:
        eintrag["urteil"] = urteil
    return eintrag


def _geschaerft_je_phase(register: list[dict]) -> dict[str, str]:
    """Phase -> `geschaerft_am` aus der Registry, nur wo das Feld gesetzt ist."""
    ergebnis = {}
    for e in register:
        if not isinstance(e, dict) or not e.get("phase"):
            continue
        datum = str(e.get("geschaerft_am") or "").strip()
        if datum:
            ergebnis[e["phase"]] = datum
    return ergebnis


def praezision(daten: dict, register: list[dict] | None = None) -> list[dict]:
    """Je Melder-Phase: wie viele Befunde waren echt, wie viele Fehlalarm.

    ``geschaerft_am`` aus `governance/melder-register.yaml` ist eine Null-
    stellung MIT Datum, keine Loeschung: Urteile VOR diesem Datum zaehlen
    nicht mehr in die Trefferquote — dieselbe Mechanik wie `revised` bei
    `tools/gate_wirkung.py` (Zeile ~256), nur fuer Melder statt Gates. Ohne
    das rechnet eine geschaerfte Phase weiter mit Urteilen aus der Zeit VOR
    der Reparatur und bleibt WARN, obwohl die Ursache behoben ist — genau
    das Muster, das #2895 fuer 0.7.4 prio-referenzen (PR #2890) meldete.

    ``register`` ist bewusst ein reiner Parameter, keine versteckte Disk-Lesung
    (dieselbe Trennung wie `herabstufungen()` in melder_register_check.py):
    ohne Angabe gilt ``[]`` — keine Nullstellung, unveraendertes Verhalten.
    `main()` laedt die echte Registry und reicht sie durch, damit ein blosser
    CLI-Aufruf ohne Zusatzflag die Nullstellung sieht; ein Direktaufruf der
    Funktion (Tests, andere Werkzeuge) bleibt deterministisch ohne Diskzugriff.
    """
    geschaerft = _geschaerft_je_phase(register or [])
    je_phase: dict[str, dict] = {}
    for u in daten.get("urteile", []):
        phase = u["phase"]
        schwelle = geschaerft.get(phase)
        if schwelle and str(u.get("datum") or "") < schwelle:
            continue  # Urteil vor der Nullstellung — zaehlt nicht mehr.
        z = je_phase.setdefault(phase, {"phase": phase, "echt": 0, "falsch": 0})
        if u["urteil"] == "echt":
            z["echt"] += 1
        elif u["urteil"] == "falsch":
            z["falsch"] += 1
    # Ein frisch geschaerfter Melder ohne EIN neues Urteil soll sichtbar
    # "0 Urteile seit ..." zeigen, statt spurlos aus dem Bericht zu fallen.
    for phase in geschaerft:
        je_phase.setdefault(phase, {"phase": phase, "echt": 0, "falsch": 0})
    ergebnis = []
    for z in je_phase.values():
        gesamt = z["echt"] + z["falsch"]
        z["urteile"] = gesamt
        z["praezision"] = (z["echt"] / gesamt) if gesamt else None
        z["bewertbar"] = gesamt >= MIN_URTEILE
        z["geschaerft_am"] = geschaerft.get(z["phase"])
        ergebnis.append(z)
    ergebnis.sort(key=lambda z: (z["praezision"] if z["bewertbar"] else 2, z["phase"]))
    return ergebnis


def praezisions_bericht(daten: dict, register: list[dict] | None = None) -> str:
    zeilen = praezision(daten, register)
    if not zeilen:
        return (
            "Keine Urteile erfasst. Ein Melder-Befund wird beim Abschluss mit\n"
            "  befund_journal.py --echt <ID> '<Notiz>'   bzw.   --falsch <ID> '<Grund>'\n"
            "eingestuft — ohne das ist die Praezision eines Melders unbekannt, und\n"
            "ein Melder mit vielen Fehlalarmen sieht aus wie einer, der viel findet."
        )
    aus = ["Melder-Praezision (echt / Fehlalarm):", ""]
    schwach = []
    for z in zeilen:
        seit = z.get("geschaerft_am")
        marke_seit = f" (seit {seit}, {z['urteile']} Urteile)" if seit else ""
        if not z["bewertbar"]:
            aus.append(
                f"  {z['phase']:<28} {z['echt']} echt / {z['falsch']} falsch{marke_seit}  "
                f"— unter {MIN_URTEILE} Urteilen, NICHT bewertbar"
            )
            continue
        quote = z["praezision"]
        marke = "🚨" if quote < PRAEZISION_SCHWELLE else "  "
        aus.append(
            f"{marke}{z['phase']:<28} {z['echt']} echt / {z['falsch']} falsch{marke_seit}  "
            f"= {quote:.0%}"
        )
        if quote < PRAEZISION_SCHWELLE:
            schwach.append(z["phase"])
    if schwach:
        aus += [
            "",
            f"→ {len(schwach)} Melder unter {PRAEZISION_SCHWELLE:.0%}: {', '.join(schwach)}.",
            "  Ein Melder, der oefter irrt als trifft, erzieht zum Wegsehen — und das",
            "  trifft dann auch seine richtigen Befunde. Dieselben drei Antworten wie",
            "  beim rueckfaelligen Gate: schaerfen, umbauen, oder ehrlich herabstufen.",
        ]
    return "\n".join(aus)


def _cross_repo_offen(daten: dict, eigenes_repo: str) -> list[tuple[str, dict]]:
    """Befunde ohne Artefakt und ohne abgelegten Verzicht, die das Gate sehen muss.

    Zwei Wege hinein, beide eng und beide belegt:
      * Fremd-Repo-Befund einer ``CROSS_REPO_PHASEN``-Phase — der Arbeitsauftrag
        liegt in einem anderen Repo.
      * Befund einer ``INFRA_PHASEN``-Phase — der Arbeitsauftrag liegt auf einem
        Knoten, und zwar unabhaengig davon, unter welchem Repo er gefuehrt wird.
        Bis 2026-08-30 fielen genau diese durch die Eigen-Repo-Ausnahme.
    Lokale Zustaende (dirty Arbeitsbaum, `0.4 repo-sync`) bleiben draussen.
    """
    offen = []
    for fid, e in sorted(daten.get("befunde", {}).items()):
        repo = str(e.get("repo", "-"))
        phase = str(e.get("phase", ""))
        fremd = repo not in ("-", eigenes_repo) and phase in CROSS_REPO_PHASEN
        infra = phase in INFRA_PHASEN
        if not (fremd or infra):
            continue
        if e.get("artefakt") or e.get("verzicht"):
            continue
        offen.append((fid, e))
    return offen


def ueberfaellig(eintrag: dict, heute: str) -> bool:
    """Entscheidungsfrist verstrichen, ohne dass verankert oder verzichtet wurde."""
    frist = eintrag.get("entscheiden_bis")
    if not frist or eintrag.get("artefakt") or eintrag.get("verzicht"):
        return False
    return heute > str(frist)


def fix_ueberfaellig(eintrag: dict, heute: str) -> bool:
    """Messdatum eines laufenden Fixes verstrichen, waehrend der Eintrag noch im Journal steht.

    Der Befund heilt (verschwindet) ohnehin, sobald seine Phase ihn nicht mehr
    meldet — dann gibt es keinen Eintrag mehr, an dem diese Funktion etwas
    pruefen koennte. Diese Pruefung setzt also voraus, dass der Aufrufer bereits
    einen Eintrag in der Hand haelt, dessen ``fix.messung`` in der Vergangenheit liegt.
    """
    fix = eintrag.get("fix")
    if not fix or not fix.get("messung"):
        return False
    return heute > str(fix["messung"])


def bericht_json(daten: dict, eigenes_repo: str) -> list[dict]:
    """Ein Datensatz je Befund, vollstaendig — die Leseflaeche baut sich daraus.

    Bewusst keine Kuerzung: was hier fehlt, muss der Leser am Knoten nachmessen.
    """
    heute = _heute()
    offen_ids = {fid for fid, _ in _cross_repo_offen(daten, eigenes_repo)}
    aus = []
    for fid, e in sorted(daten.get("befunde", {}).items()):
        aus.append(
            {
                "id": fid,
                "phase": e.get("phase"),
                "repo": e.get("repo"),
                "fremd": e.get("repo") not in ("-", eigenes_repo),
                "infra": e.get("phase") in INFRA_PHASEN,
                "im_gate": fid in offen_ids,
                "erstmals": e.get("erstmals"),
                "zuletzt": e.get("zuletzt"),
                "laeufe": int(e.get("laeufe", 0)),
                "note": e.get("letzte_note"),
                "artefakt": e.get("artefakt"),
                "verzicht": e.get("verzicht"),
                "wiedervorlage": e.get("wiedervorlage"),
                "ruhezustand": ruhezustand(e, heute),
                "entscheiden_bis": e.get("entscheiden_bis"),
                "ueberfaellig": ueberfaellig(e, heute),
                "urteil": e.get("urteil"),
                "fix": e.get("fix"),
                "fix_ueberfaellig": fix_ueberfaellig(e, heute),
                **{f: e.get(f) for f in BELEG_FELDER},
            }
        )
    return aus


def bericht(
    daten: dict, eigenes_repo: str, deklarationen: list[dict] | None = None
) -> str:
    """``deklarationen`` (aus ``lade_deklarationen()``) haengt die Deklarations-
    Zeilen an; ``None`` laesst den Bericht wie vor #3495 V2."""
    dekl = deklarations_zeilen(deklarationen or [])
    anhang = ("\n\nDeklarationen:\n" + "\n".join(dekl)) if dekl else ""
    befunde = daten.get("befunde", {})
    if not befunde:
        return "Journal leer — keine offenen Befunde." + anhang
    zeilen = [f"{len(befunde)} offene(r) Befund(e):", ""]
    for fid, e in sorted(
        befunde.items(), key=lambda kv: (kv[1].get("repo", ""), kv[0])
    ):
        stand = (
            f"verankert {e['artefakt']}"
            if e.get("artefakt")
            else (
                f"Verzicht ({e['verzicht'].get('grund', '')})"
                if e.get("verzicht")
                else "OHNE Artefakt"
            )
        )
        fremd = " [FREMD]" if e.get("repo") not in ("-", eigenes_repo) else ""
        zustand = ruhezustand(e, _heute())
        ruhe = {
            "ruht": f" · ruht bis {e.get('wiedervorlage')}",
            "faellig": f" · ⏰ Frist {e.get('wiedervorlage')} abgelaufen",
        }.get(zustand, "")
        infra = " [INFRA]" if e.get("phase") in INFRA_PHASEN else ""
        frist = ""
        if ueberfaellig(e, _heute()):
            frist = f" · ⏰ Entscheidung seit {e.get('entscheiden_bis')} ueberfaellig"
        elif e.get("entscheiden_bis") and not (e.get("artefakt") or e.get("verzicht")):
            frist = f" · entscheiden bis {e.get('entscheiden_bis')}"
        beleg = ""
        if e.get("kommando"):
            beleg = f"\n      {e.get('knoten') or '?'}$ {e['kommando']}"
            if e.get("ausgabe"):
                beleg += f" → {e['ausgabe']}"
        elif not e.get("kommando"):
            beleg = "\n      (ohne Beleg — Kommando/Knoten fehlen, --beleg nachtragen)"
        fix_zeile = ""
        if e.get("fix"):
            fx = e["fix"]
            fix_zeile = (
                f"\n      🔧 Fix in Arbeit: {fx.get('pr')} — {fx.get('wirkung')} "
                f"(Messung {fx.get('messung')})"
            )
            if fix_ueberfaellig(e, _heute()):
                fix_zeile += "\n      ⏰ Fix-Messung überfällig"
        zeilen.append(
            f"  {fid}{fremd}{infra}\n"
            f"      {e.get('laeufe', 0)} Laeufe · erstmals {e.get('erstmals', '?')} · "
            f"zuletzt {e.get('zuletzt', '?')} · {stand}{ruhe}{frist}{beleg}{fix_zeile}"
        )
    offen = _cross_repo_offen(daten, eigenes_repo)
    zeilen.append("")
    if offen:
        zeilen.append(
            f"RESULT: OFFEN — {len(offen)} Fremd-Repo-/Infra-Befund(e) ohne Artefakt: "
            + ", ".join(sorted({e["repo"] for _, e in offen}))
        )
    else:
        zeilen.append(
            "RESULT: OK — kein Fremd-Repo- oder Infra-Befund ohne Artefakt oder Verzicht."
        )
    return "\n".join(zeilen) + anhang


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--aufnehmen", action="store_true", help="TSV von stdin einlesen")
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--json", action="store_true", help="Bericht maschinenlesbar")
    p.add_argument("--beleg", metavar="ID", help="Beleg-Felder an einen Befund haengen")
    for feld in BELEG_FELDER:
        p.add_argument(f"--{feld}", default=None, help=f"mit --beleg: {feld}")
    p.add_argument(
        "--fix", metavar="ID", help="Fix in Arbeit setzen (mit --pr und --wirkung)"
    )
    p.add_argument("--pr", default=None, help="mit --fix: PR-URL")
    p.add_argument(
        "--wirkung", default=None, help="mit --fix: erwartete Wirkung als Satz"
    )
    p.add_argument(
        "--messung",
        default=None,
        metavar="DATUM",
        help=f"mit --fix: Messdatum YYYY-MM-DD (Default: +{FRIST_FIX_MESSUNG_TAGE} Tage)",
    )
    p.add_argument(
        "--deklaration",
        metavar="ZIEL",
        help="Deklaration setzen: Host, Dienst oder Journal-Schluessel "
        "(mit --art, --grund, --gueltig-bis)",
    )
    p.add_argument("--art", choices=DEKLARATIONS_ARTEN, help="mit --deklaration")
    p.add_argument("--grund", default=None, help="mit --deklaration: Grund als Satz")
    p.add_argument(
        "--gueltig-bis",
        default=None,
        metavar="DATUM",
        help="mit --deklaration: Pflicht",
    )
    p.add_argument(
        "--quelle", default="", help="mit --deklaration: Herkunft (Issue, Datei)"
    )
    p.add_argument(
        "--deklarationen",
        type=Path,
        default=None,
        help=f"Deklarations-Datei (Default: {DEKLARATIONEN_REL})",
    )
    p.add_argument("--offen-cross-repo", action="store_true")
    p.add_argument("--verankert", nargs=2, metavar=("ID", "URL"))
    p.add_argument(
        "--echt", nargs=2, metavar=("ID", "NOTIZ"), help="Befund war berechtigt"
    )
    p.add_argument(
        "--falsch", nargs=2, metavar=("ID", "GRUND"), help="Fehlalarm des Melders"
    )
    p.add_argument("--praezision", action="store_true", help="Trefferquote je Melder")
    p.add_argument("--kurz", action="store_true", help="eine Zeile fuer den Runner")
    p.add_argument("--verzichtet", nargs=2, metavar=("ID", "GRUND"))
    p.add_argument(
        "--frist",
        type=int,
        default=None,
        metavar="TAGE",
        help=f"Ruhefrist ueberschreiben (Vorgabe: {FRIST_VERANKERT_TAGE} verankert / {FRIST_VERZICHT_TAGE} Verzicht)",
    )
    p.add_argument(
        "--repo", default="platform", help="eigenes Repo (Default: platform)"
    )
    p.add_argument("--datei", default=None, help="Journal-Pfad (Tests)")
    p.add_argument(
        "--register",
        type=Path,
        default=_mrc.DEFAULT_REGISTER,
        help="Melder-Registry fuer geschaerft_am (Default: governance/melder-register.yaml)",
    )
    a = p.parse_args(argv)

    pfad = Path(a.datei) if a.datei else JOURNAL
    daten = lade(pfad)

    if a.aufnehmen:
        # Registry nur hier geladen (main-Zeitpunkt) — dieselbe Trennung wie bei
        # --praezision: aufnehmen() bleibt ohne Angabe deterministisch (Tests,
        # andere Aufrufer), nur der CLI-Pfad sieht das echte zielgebunden-Feld.
        register = _mrc.lade_register(a.register)
        meldungen = aufnehmen(
            _zeilen_lesen(sys.stdin.read()), daten, lauf_repo=a.repo, register=register
        )
        sichere(daten, pfad)
        for m in meldungen:
            print(m)
        offen = _cross_repo_offen(daten, a.repo)
        if offen:
            print(
                f"  ⚠ {len(offen)} Fremd-Repo-/Infra-Befund(e) ohne Artefakt: "
                + ", ".join(sorted({e["repo"] for _, e in offen}))
                + " — /session-ende fragt danach"
            )
        return 0

    if a.beleg:
        e = daten.get("befunde", {}).get(a.beleg)
        if e is None:
            print(f"Kein Befund mit ID {a.beleg}", file=sys.stderr)
            return 2
        gesetzt = {f: getattr(a, f) for f in BELEG_FELDER if getattr(a, f)}
        if not gesetzt:
            print(
                "--beleg ohne Feld: mindestens eines von "
                + ", ".join(f"--{f}" for f in BELEG_FELDER),
                file=sys.stderr,
            )
            return 2
        e.update(gesetzt)
        sichere(daten, pfad)
        print(
            f"Beleg an {a.beleg}: " + ", ".join(f"{k}={v}" for k, v in gesetzt.items())
        )
        return 0

    if a.fix:
        e = daten.get("befunde", {}).get(a.fix)
        if e is None:
            print(f"Kein Befund mit ID {a.fix}", file=sys.stderr)
            return 2
        if not a.pr or not a.wirkung:
            print("--fix braucht --pr und --wirkung.", file=sys.stderr)
            return 2
        messung = a.messung or _frist(FRIST_FIX_MESSUNG_TAGE)
        e["fix"] = {
            "pr": a.pr,
            "wirkung": a.wirkung,
            "messung": messung,
            "gesetzt_am": _heute(),
        }
        sichere(daten, pfad)
        print(f"Fix in Arbeit: {a.fix} -> {a.pr} · Messung {messung}")
        return 0

    if a.deklaration:
        if not (a.art and a.grund and a.gueltig_bis):
            print(
                "--deklaration braucht --art, --grund und --gueltig-bis — "
                "ohne Ablauf keine Deklaration.",
                file=sys.stderr,
            )
            return 2
        try:
            if date.fromisoformat(a.gueltig_bis.strip()).isoformat() < _heute():
                print(
                    f"--gueltig-bis {a.gueltig_bis} liegt in der Vergangenheit.",
                    file=sys.stderr,
                )
                return 2
            d = setze_deklaration(
                a.deklaration,
                a.art,
                a.grund,
                a.gueltig_bis,
                quelle=a.quelle,
                pfad=a.deklarationen,
            )
        except ValueError as exc:
            print(f"Deklaration ungueltig: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"Deklaration nicht geschrieben: {exc}", file=sys.stderr)
            return 2
        print(
            f"Deklaration gesetzt: {d['ziel']} [{d['art']}] gueltig bis "
            f"{d['gueltig_bis']} — {d['grund']}"
        )
        return 0

    if a.bericht and a.json:
        print(json.dumps(bericht_json(daten, a.repo), ensure_ascii=False, indent=1))
        return 0

    if a.echt or a.falsch:
        fid, text = a.echt or a.falsch
        urteil = "echt" if a.echt else "falsch"
        befunde = daten.get("befunde", {})
        if fid not in befunde:
            # Der Runner druckt die ID als `0.7 deploy-scan::x` — der Phasen-
            # Praefix wirkt wie ein Label, ist aber Teil des Schluessels. Wer
            # ihn weglaesst, darf trotzdem treffen, wenn GENAU ein Befund passt.
            treffer = sorted(
                {
                    k
                    for k in befunde
                    if k.endswith(" " + fid) or k.split(" ", 1)[-1] == fid
                }
            )
            if len(treffer) == 1:
                print(f"hinweis: ID vervollständigt zu '{treffer[0]}'", file=sys.stderr)
                fid = treffer[0]
            elif fid in {u.get("fid") for u in daten.get("urteile", [])}:
                # Befund geheilt (nicht mehr gemeldet), aber schon einmal
                # beurteilt — das macht die ID bekannt, kein Phantom.
                pass
            else:
                print(f"Kein Befund mit ID {fid}", file=sys.stderr)
                return 2
        urteile_dazu(daten, fid, urteil, text)
        sichere(daten, pfad)
        print(f"{urteil}: {fid} — {text}")
        return 0

    if a.praezision:
        # Registry nur hier geladen (main-Zeitpunkt), nicht in praezision()
        # selbst — sonst haengt eine reine Funktion an einer Disk-Lesung und
        # jeder Direktaufruf (Tests, andere Werkzeuge) wird nicht-deterministisch.
        register = _mrc.lade_register(a.register)

    if a.praezision and a.json:
        print(json.dumps(praezision(daten, register), ensure_ascii=False, indent=1))
        return 0

    if a.praezision:
        zeilen = praezision(daten, register)
        schwach = [
            z
            for z in zeilen
            if z["bewertbar"] and z["praezision"] < PRAEZISION_SCHWELLE
        ]
        if a.kurz:
            if schwach:
                spitze = schwach[0]
                weitere = f" (+{len(schwach) - 1} weitere)" if len(schwach) > 1 else ""
                print(
                    f"{len(schwach)} Melder unter {PRAEZISION_SCHWELLE:.0%} Trefferquote — "
                    f"{spitze['phase']}: {spitze['praezision']:.0%} "
                    f"({spitze['echt']} echt / {spitze['falsch']} falsch){weitere}"
                )
                for z in schwach[1:5]:
                    print(f"  · {z['phase']} — {z['praezision']:.0%}")
            return 0
        print(praezisions_bericht(daten, register))
        return 0

    if a.verankert:
        fid, url = a.verankert
        e = daten.get("befunde", {}).get(fid)
        if e is None:
            print(f"Kein Befund mit ID {fid}", file=sys.stderr)
            return 2
        e["artefakt"] = url
        tage = a.frist if a.frist is not None else FRIST_VERANKERT_TAGE
        e["wiedervorlage"] = _frist(tage)
        e["ruht_note"] = e.get("letzte_note")
        sichere(daten, pfad)
        print(
            f"verankert: {fid} -> {url} · ruht bis {e['wiedervorlage']} ({tage} Tage)"
        )
        return 0

    if a.verzichtet:
        fid, grund = a.verzichtet
        e = daten.get("befunde", {}).get(fid)
        if e is None:
            print(f"Kein Befund mit ID {fid}", file=sys.stderr)
            return 2
        if not grund.strip():
            print("Verzicht ohne Grund zaehlt nicht.", file=sys.stderr)
            return 2
        e["verzicht"] = {"grund": grund.strip(), "am": _heute()}
        tage = a.frist if a.frist is not None else FRIST_VERZICHT_TAGE
        e["wiedervorlage"] = _frist(tage)
        e["ruht_note"] = e.get("letzte_note")
        sichere(daten, pfad)
        print(
            f"Verzicht abgelegt: {fid} — {grund.strip()} · ruht bis "
            f"{e['wiedervorlage']} ({tage} Tage)"
        )
        return 0

    if a.offen_cross_repo:
        # Kein Journal = keine Datenbasis = kein Urteil (Retro 9d861a, Befund #9).
        # Beim allerersten Lauf meldete dieses Gate `OK`, obwohl die Datei noch gar
        # nicht existierte — ein vakuum wahres Freigabe-Signal, genau die Fehlform,
        # die am 2026-08-15 schon einmal ein „0 Fehlalarme"-Urteil wertlos machte
        # (platform#1986). `UNGEPRUEFT` ist die ehrliche Antwort; Exit 0, weil das
        # Fehlen der Datei kein Verstoss ist, sondern ein Zustand vor dem ersten Lauf.
        if not pfad.exists():
            print(
                f"RESULT: UNGEPRUEFT — Journal {pfad} existiert nicht. Der "
                "Session-Start-Runner legt es beim naechsten Lauf an; bis dahin ist "
                "ueber Fremd-Repo-Befunde nichts ausgesagt (kein OK)."
            )
            return 0
        offen = _cross_repo_offen(daten, a.repo)
        if not offen:
            print("RESULT: OK — kein Fremd-Repo-Befund ohne Artefakt oder Verzicht.")
            return 0
        print(
            f"RESULT: OFFEN — {len(offen)} Fremd-Repo-/Infra-Befund(e) brauchen ein "
            f"Artefakt im Zielrepo (oder einen abgelegten Verzicht):"
        )
        heute = _heute()
        for fid, e in offen:
            marke = " ⏰ UEBERFAELLIG" if ueberfaellig(e, heute) else ""
            art = " [INFRA]" if e.get("phase") in INFRA_PHASEN else ""
            print(
                f"  {fid}{art}{marke} — {e.get('laeufe', 0)} Laeufe, erstmals "
                f"{e.get('erstmals', '?')}, entscheiden bis {e.get('entscheiden_bis', '?')}"
            )
            print(f"      {e.get('letzte_note', '')}")
            if e.get("kommando"):
                print(f"      {e.get('knoten') or '?'}$ {e['kommando']}")
            # Konkrete Schluessel, keine Platzhalter (#2863): sonst nimmt der
            # naechste Aufruf die ID ohne Phasen-Praefix und trifft ins Leere.
            print(f"      -> python3 tools/befund_journal.py --echt '{fid}' '<Notiz>'")
            print(
                f"      -> python3 tools/befund_journal.py --verankert '{fid}' '<URL>'"
            )
        print(
            "\nVerankern:  python3 tools/befund_journal.py --verankert '<ID>' '<URL>'"
            "\nVerzichten: python3 tools/befund_journal.py --verzichtet '<ID>' '<Grund>'"
        )
        return 1

    print(bericht(daten, a.repo, deklarationen=lade_deklarationen(a.deklarationen)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
