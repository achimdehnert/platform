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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
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
CROSS_REPO_PHASEN = ("0.7 deploy-scan",)


def _heute() -> str:
    return datetime.now(timezone.utc).date().isoformat()


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
        saetze.append(
            {
                "phase": phase,
                "status": status,
                "repos": [r for r in repos.split() if r],
                "note": note,
                "ungeprueft": [r for r in ungeprueft.split() if r],
            }
        )
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
                }
                continue
            eintrag["laeufe"] = int(eintrag.get("laeufe", 0)) + 1
            eintrag["zuletzt"] = heute
            eintrag["letzte_note"] = satz["note"]
            eintrag["repo"] = repo
            eintrag["phase"] = satz["phase"]

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

    for fid, e in sorted(befunde.items(), key=lambda kv: -int(kv[1].get("laeufe", 0))):
        if fid not in noch_gemeldet:
            continue
        laeufe = int(e.get("laeufe", 0))
        if laeufe < ALT_AB_LAEUFEN:
            continue
        marke = "⏳ ALTBEFUND"
        anhang = ""
        if e.get("artefakt"):
            anhang = f" · verankert: {e['artefakt']}"
        elif e.get("verzicht"):
            anhang = f" · Verzicht: {e['verzicht'].get('grund', '')}"
        meldungen.append(
            f"  {marke} {e['phase']} · Repo {e['repo']} — "
            f"{laeufe} Laeufe, erstmals {e['erstmals']}{anhang}"
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
    """Fremd-Repo-Befunde ohne Artefakt und ohne abgelegten Verzicht.

    Nur Phasen aus ``CROSS_REPO_PHASEN`` — siehe die Begruendung dort, warum das
    Gate eng anfaengt statt jede Zeile mit einem Repo-Namen einzusammeln.
    """
    offen = []
    for fid, e in sorted(daten.get("befunde", {}).items()):
        repo = str(e.get("repo", "-"))
        if repo in ("-", eigenes_repo):
            continue
        if str(e.get("phase", "")) not in CROSS_REPO_PHASEN:
            continue
        if e.get("artefakt") or e.get("verzicht"):
            continue
        offen.append((fid, e))
    return offen


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
        zeilen.append(
            f"  {fid}{fremd}\n"
            f"      {e.get('laeufe', 0)} Laeufe · erstmals {e.get('erstmals', '?')} · "
            f"zuletzt {e.get('zuletzt', '?')} · {stand}"
        )
    offen = _cross_repo_offen(daten, eigenes_repo)
    zeilen.append("")
    if offen:
        zeilen.append(
            f"RESULT: OFFEN — {len(offen)} Fremd-Repo-Befund(e) ohne Artefakt im Zielrepo: "
            + ", ".join(e["repo"] for _, e in offen)
        )
    else:
        zeilen.append(
            "RESULT: OK — kein Fremd-Repo-Befund ohne Artefakt oder Verzicht."
        )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--aufnehmen", action="store_true", help="TSV von stdin einlesen")
    p.add_argument("--bericht", action="store_true")
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
                f"  ⚠ {len(offen)} Fremd-Repo-Befund(e) ohne Artefakt im Zielrepo: "
                + ", ".join(sorted({e["repo"] for _, e in offen}))
                + " — /session-ende fragt danach"
            )
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
        sichere(daten, pfad)
        print(f"verankert: {fid} -> {url}")
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
        sichere(daten, pfad)
        print(f"Verzicht abgelegt: {fid} — {grund.strip()}")
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
            f"RESULT: OFFEN — {len(offen)} Fremd-Repo-Befund(e) brauchen ein Artefakt "
            f"im Zielrepo (oder einen abgelegten Verzicht):"
        )
        for fid, e in offen:
            print(
                f"  {fid} — {e.get('laeufe', 0)} Laeufe, erstmals {e.get('erstmals', '?')}"
            )
            print(f"      {e.get('letzte_note', '')}")
        print(
            "\nVerankern:  python3 tools/befund_journal.py --verankert '<ID>' '<URL>'"
            "\nVerzichten: python3 tools/befund_journal.py --verzichtet '<ID>' '<Grund>'"
        )
        return 1

    print(bericht(daten, a.repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
