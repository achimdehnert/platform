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
  --bericht --json         Dieselben Daten maschinenlesbar — fuer eine Leseflaeche
                           ausserhalb dieser Maschine (KONZ-054 E2).

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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
)

#: Entscheidungsfrist in Tagen fuer einen NEUEN Befund: bis dahin verankern oder mit
#: Grund ablegen. Sieben, weil das eine Arbeitswoche ist und ein Befund, ueber den
#: eine Woche lang niemand entschieden hat, nicht leiser werden darf, sondern lauter.
#: Getrennt von `wiedervorlage` (Ruhefrist NACH einer Entscheidung) — ein Feld fuer
#: beides haette jeden neuen Befund zum Schweigen gebracht.
FRIST_ENTSCHEIDUNG_TAGE = 7

#: Beleg-Felder je Befund (KONZ-054 E2). Optional — aber ein Befund ohne sie ist
#: fuer den Leser um 03:00 eine Behauptung, kein Befund.
BELEG_FELDER = ("knoten", "kommando", "ausgabe", "positivkontrolle")


def _heute() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _frist(tage: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=tage)).date().isoformat()


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


def aufnehmen(saetze: list[dict], daten: dict) -> list[str]:
    """Journal fortschreiben und die Alters-Zeilen zurueckgeben.

    Regeln, in dieser Reihenfolge:
      - WARN/FAIL mit Repo r  -> Eintrag `phase::r` anlegen oder altern lassen.
      - PASS                  -> alle Eintraege DIESER Phase heilen (entfernen).
      - WARN ohne dieses Repo -> Eintrag der Phase fuer nicht mehr genannte Repos heilen.
      - Phase gar nicht dabei -> Eintrag bleibt unveraendert stehen (Abdeckungsluecke,
                                 keine Heilung — er altert aber auch nicht weiter).
    """
    befunde = daten.setdefault("befunde", {})
    heute = _heute()
    gelaufene_phasen = {s["phase"] for s in saetze}
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
    # und nur fuer Repos, die diese Phase auch erreichen konnte.
    for fid in list(befunde):
        eintrag = befunde[fid]
        if (
            eintrag.get("phase") in gelaufene_phasen
            and fid not in noch_gemeldet
            and fid not in ungeprueft
        ):
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
            "grund": grund,
            "datum": _heute(),
        }
    )
    if eintrag is not None:
        eintrag["urteil"] = urteil
    return eintrag


def praezision(daten: dict) -> list[dict]:
    """Je Melder-Phase: wie viele Befunde waren echt, wie viele Fehlalarm."""
    je_phase: dict[str, dict] = {}
    for u in daten.get("urteile", []):
        z = je_phase.setdefault(
            u["phase"], {"phase": u["phase"], "echt": 0, "falsch": 0}
        )
        if u["urteil"] == "echt":
            z["echt"] += 1
        elif u["urteil"] == "falsch":
            z["falsch"] += 1
    ergebnis = []
    for z in je_phase.values():
        gesamt = z["echt"] + z["falsch"]
        z["urteile"] = gesamt
        z["praezision"] = (z["echt"] / gesamt) if gesamt else None
        z["bewertbar"] = gesamt >= MIN_URTEILE
        ergebnis.append(z)
    ergebnis.sort(key=lambda z: (z["praezision"] if z["bewertbar"] else 2, z["phase"]))
    return ergebnis


def praezisions_bericht(daten: dict) -> str:
    zeilen = praezision(daten)
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
        if not z["bewertbar"]:
            aus.append(
                f"  {z['phase']:<28} {z['echt']} echt / {z['falsch']} falsch  "
                f"— unter {MIN_URTEILE} Urteilen, NICHT bewertbar"
            )
            continue
        quote = z["praezision"]
        marke = "🚨" if quote < PRAEZISION_SCHWELLE else "  "
        aus.append(
            f"{marke}{z['phase']:<28} {z['echt']} echt / {z['falsch']} falsch  "
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
                **{f: e.get(f) for f in BELEG_FELDER},
            }
        )
    return aus


def bericht(daten: dict, eigenes_repo: str) -> str:
    befunde = daten.get("befunde", {})
    if not befunde:
        return "Journal leer — keine offenen Befunde."
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
        zeilen.append(
            f"  {fid}{fremd}{infra}\n"
            f"      {e.get('laeufe', 0)} Laeufe · erstmals {e.get('erstmals', '?')} · "
            f"zuletzt {e.get('zuletzt', '?')} · {stand}{ruhe}{frist}{beleg}"
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
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--aufnehmen", action="store_true", help="TSV von stdin einlesen")
    p.add_argument("--bericht", action="store_true")
    p.add_argument("--json", action="store_true", help="Bericht maschinenlesbar")
    p.add_argument("--beleg", metavar="ID", help="Beleg-Felder an einen Befund haengen")
    for feld in BELEG_FELDER:
        p.add_argument(f"--{feld}", default=None, help=f"mit --beleg: {feld}")
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
    a = p.parse_args(argv)

    pfad = Path(a.datei) if a.datei else JOURNAL
    daten = lade(pfad)

    if a.aufnehmen:
        meldungen = aufnehmen(_zeilen_lesen(sys.stdin.read()), daten)
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

    if a.bericht and a.json:
        print(json.dumps(bericht_json(daten, a.repo), ensure_ascii=False, indent=1))
        return 0

    if a.echt or a.falsch:
        fid, text = a.echt or a.falsch
        urteil = "echt" if a.echt else "falsch"
        urteile_dazu(daten, fid, urteil, text)
        sichere(daten, pfad)
        print(f"{urteil}: {fid} — {text}")
        return 0

    if a.praezision:
        zeilen = praezision(daten)
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
        print(praezisions_bericht(daten))
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
        print(
            "\nVerankern:  python3 tools/befund_journal.py --verankert '<ID>' '<URL>'"
            "\nVerzichten: python3 tools/befund_journal.py --verzichtet '<ID>' '<Grund>'"
        )
        return 1

    print(bericht(daten, a.repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
