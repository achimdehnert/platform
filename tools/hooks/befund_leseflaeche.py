#!/usr/bin/env python3
"""befund_leseflaeche.py — SessionStart-Leseflaeche fuer Melder-Befunde (platform#1908 Etappe 1).

Das Problem, gegen das dieses Werkzeug gebaut ist, ist NICHT ein fehlender Melder.
Der naechtliche `handover-reconcile` arbeitet seit Wochen korrekt und hat dieselbe
Diskrepanz an mindestens fuenf aufeinanderfolgenden Naechten gemeldet (Laeufe
31074214916 und 31357132824, beide `success`). Gelesen hat sie niemand: das Ergebnis
landet in einer Job-Summary eines Laufs, der per Design immer gruen ist. Entdeckt
wurde der Fehler jeweils interaktiv beim naechsten Sitzungsstart — die Automatik
lief die ganze Zeit korrekt daneben (platform#1894).

Dieses Werkzeug ist die **Leseflaeche**: es bringt den vorhandenen Befund dorthin,
wo die veraltete Information konsumiert wird. Es erweitert KEINE Schreibrechte und
haengt deshalb nicht am Pilot-Ausgang (#1908, Vorbedingung).

Abgedeckte Abnahmekriterien aus #1908 Etappe 1:
  L1 Auffindbarkeit  — Ausgabe beim Sitzungsstart statt nur in der Job-Summary
  L2 Dedup + Zustand — ein Eintrag je Befund-Schluessel, mit Alter/Klasse/Quelle/Zustand
  L3 Sicht-Frist     — ueberfaellige, unbestaetigte Befunde werden eskaliert markiert
  L4 Exit-Kriterium  — `--exit-kriterium` beantwortet maschinell, ob Etappe 2 starten darf

Aufruf:
  befund_leseflaeche.py                      # rendern (SessionStart-Modus)
  befund_leseflaeche.py --report <datei>     # feste Report-Datei statt Abruf (Tests/manuell)
  befund_leseflaeche.py --gesehen <SCHLUESSEL> [...]   # Befund(e) als gesehen markieren
  befund_leseflaeche.py --alle-gesehen       # alle offenen als gesehen markieren
  befund_leseflaeche.py --exit-kriterium     # L4-Status ausgeben (exit 0 = erfuellt)

FAIL-OPEN: Jeder Fehler endet mit Exit 0 und ohne Ausgabe. Ein Hook, der den
Sitzungsstart kaputtmacht, wird abgeschaltet und meldet danach gar nichts mehr —
das waere derselbe Fehlermodus eine Ebene hoeher.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gelesen.
GATE_HEADER = {
    "slug": "melder-ohne-leser",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-11",
    "evidence": "tools/tests/test_befund_leseflaeche.py",
}

STATE_PFAD = Path(
    os.environ.get(
        "LESEFLAECHE_STATE",
        os.path.expanduser("~/.claude/hooks/state/leseflaeche.json"),
    )
)
# Sicht-Frist (L3): so lange darf ein Befund unbestaetigt bleiben, bevor er
# eskaliert markiert wird. Bewusst kurz — der Realfall lief fuenf Naechte.
SICHT_FRIST = timedelta(days=int(os.environ.get("LESEFLAECHE_FRIST_TAGE", "2")))
# Wie alt darf der zwischengespeicherte Report sein, bevor neu abgerufen wird.
# SessionStart hat ein knappes Zeitbudget; ein `gh`-Abruf bei JEDEM Start waere
# zu teuer und wuerde den Hook in sein eigenes Timeout treiben.
ABRUF_INTERVALL = timedelta(hours=int(os.environ.get("LESEFLAECHE_ABRUF_STUNDEN", "6")))
ARTEFAKT = "handover-reconcile-report"
WORKFLOW = "handover-reconcile.yml"
MAX_ZEILEN = 8  # mehr als das liest beim Sitzungsstart niemand — Rest wird gezaehlt

#: Klassen, die KEIN Befund sind, sondern eine Abdeckungsluecke.
#:
#: Gemessen beim Verdrahten (2026-08-16, platform#2006) am echten Report des Laufs
#: 31927075538: 20 Eintraege, davon **12 `UNKNOWN`** — jeder mit dem Detail
#: `gh: Not Found (HTTP 404)`, und jeder auf ein PRIVATES Repo (risk-hub, tax-hub,
#: ttz-hub, travel-beat, frist-hub, mcp-hub, dev-hub). Der Workflow laeuft mit dem
#: repo-eigenen Token; `platform` ist oeffentlich, die anderen nicht. `UNKNOWN`
#: heisst hier also „mit diesem Token nicht pruefbar", nicht „stimmt nicht".
#:
#: Sie als Befunde zu rendern waere der sichere Weg, diese Leseflaeche wieder
#: unlesbar zu machen: 12 von 20 Zeilen Rauschen, und ein dauerhaft lautes Werkzeug
#: wird abgeschaltet — dann meldet es gar nichts mehr (#1508). Sie verschwinden aber
#: auch nicht: sie werden als **eine** Abdeckungszeile ausgewiesen, so wie Phase 0.7
#: des Runners ihre nicht abfragbaren Repos nennt statt sie wegzulassen.
NICHT_PRUEFBAR = ("UNKNOWN",)


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def lade_state() -> dict:
    try:
        d = json.loads(STATE_PFAD.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def schreibe_state(state: dict) -> None:
    try:
        STATE_PFAD.parent.mkdir(parents=True, exist_ok=True)
        STATE_PFAD.write_text(
            json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    except OSError:
        pass  # fail-open: lieber kein State als ein kaputter Sitzungsstart


def hole_report(repo_dir: Path) -> dict | None:
    """Letzten Reconcile-Report als Artefakt ziehen. None bei jedem Fehlschlag."""
    try:
        lauf = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                WORKFLOW,
                "-L",
                "1",
                "--json",
                "databaseId,conclusion",
                "--jq",
                ".[0].databaseId",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=repo_dir,
        )
        lauf_id = lauf.stdout.strip()
        if lauf.returncode != 0 or not lauf_id.isdigit():
            return None
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dl = subprocess.run(
                ["gh", "run", "download", lauf_id, "-n", ARTEFAKT, "-D", tmp],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=repo_dir,
            )
            if dl.returncode != 0:
                return None
            for p in Path(tmp).rglob("*.json"):
                return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return None
    return None


def verschmelze(state: dict, report: dict) -> dict:
    """L2: ein Eintrag je Schluessel; Erstsichtung bleibt erhalten, Wiederholung zaehlt hoch.

    Das ist der Kern der Deduplizierung: derselbe Befund an fuenf Naechten ist EIN
    Eintrag mit `wiederholungen: 5`, nicht fuenf Zeilen. Die Wiederholungszahl ist
    dabei die eigentliche Information — sie sagt, wie lange niemand hingesehen hat.
    """
    befunde = state.setdefault("befunde", {})
    jetzt = _iso(_jetzt())
    aktuelle = set()
    for b in report.get("befunde", []):
        s = b.get("schluessel")
        if not s:
            continue
        aktuelle.add(s)
        eintrag = befunde.get(s)
        if eintrag is None:
            befunde[s] = {
                "erstmals": jetzt,
                "zuletzt": jetzt,
                "wiederholungen": 1,
                "klasse": b.get("klasse", "?"),
                "detail": b.get("detail", ""),
                "zeile_nr": b.get("zeile_nr"),
                "bestaetigt": None,
            }
        else:
            # Nur hochzaehlen, wenn es ein NEUER Lauf ist — sonst wuerde jeder
            # Sitzungsstart die Zahl aufblaehen und "fuenf Naechte" nicht mehr
            # von "fuenf Starts an einem Tag" unterscheidbar machen.
            if eintrag.get("zuletzt", "")[:10] != jetzt[:10]:
                eintrag["wiederholungen"] = eintrag.get("wiederholungen", 1) + 1
            eintrag["zuletzt"] = jetzt
            eintrag["klasse"] = b.get("klasse", eintrag.get("klasse", "?"))
            eintrag["detail"] = b.get("detail", eintrag.get("detail", ""))
    # Verschwundene Befunde entfernen — sie sind behoben; sie stehenzulassen
    # erzeugt genau die Geister-Liste, die man wieder nicht liest.
    for s in [s for s in befunde if s not in aktuelle]:
        del befunde[s]
    state["letzter_abruf"] = jetzt
    return state


def offene(state: dict) -> list[tuple[str, dict, int]]:
    """(Schluessel, Eintrag, Alter in Tagen) je unbestaetigtem Befund, aeltester zuerst.

    Ohne die nicht pruefbaren Klassen — die sind eine Abdeckungsluecke und kein
    Befund (siehe ``NICHT_PRUEFBAR``); sie stehen als eigene Zeile im Bericht.
    """
    jetzt = _jetzt()
    raus = []
    for s, e in (state.get("befunde") or {}).items():
        if e.get("bestaetigt"):
            continue
        if e.get("klasse") in NICHT_PRUEFBAR:
            continue
        erst = _parse(e.get("erstmals", "")) or jetzt
        raus.append((s, e, (jetzt - erst).days))
    raus.sort(key=lambda t: -t[2])
    return raus


def ungeprueft(state: dict) -> list[str]:
    """Schluessel, ueber die der Melder kein Urteil faellen konnte."""
    return sorted(
        s
        for s, e in (state.get("befunde") or {}).items()
        if not e.get("bestaetigt") and e.get("klasse") in NICHT_PRUEFBAR
    )


def rendere(state: dict) -> str:
    posten = offene(state)
    luecken = ungeprueft(state)
    if not posten:
        # Auch ein reiner Luecken-Stand wird gezeigt: „nichts gefunden" und
        # „nichts pruefen koennen" sind zwei verschiedene Aussagen, und die
        # zweite als Stille auszugeben ist genau die Falle, gegen die es geht.
        if luecken:
            return (
                f"👁  Leseflaeche — 0 Befunde · {len(luecken)} Eintrag/Eintraege "
                f"NICHT pruefbar (Token ohne Zugriff): {', '.join(luecken[:4])}"
                + (" …" if len(luecken) > 4 else "")
            )
        return ""
    ueberfaellig = [p for p in posten if timedelta(days=p[2]) >= SICHT_FRIST]
    kopf = f"👁  Leseflaeche — {len(posten)} offene(r) Melder-Befund(e)"
    if ueberfaellig:
        kopf += f", davon {len(ueberfaellig)} ueber der Sicht-Frist ({SICHT_FRIST.days} Tage)"
    zeilen = [kopf]
    for s, e, alter in posten[:MAX_ZEILEN]:
        marker = "⏰" if timedelta(days=alter) >= SICHT_FRIST else "·"
        wdh = e.get("wiederholungen", 1)
        wdh_txt = f", {wdh}x gemeldet" if wdh > 1 else ""
        zeilen.append(
            f"  {marker} {s} — {e.get('klasse', '?')}: {e.get('detail', '')}"
            f" (seit {alter} Tag(en){wdh_txt})"
        )
    if len(posten) > MAX_ZEILEN:
        zeilen.append(f"  … und {len(posten) - MAX_ZEILEN} weitere")
    if luecken:
        zeilen.append(
            f"  ◌ {len(luecken)} Eintrag/Eintraege NICHT pruefbar (Token ohne Zugriff): "
            + ", ".join(luecken[:4])
            + (" …" if len(luecken) > 4 else "")
        )
    zeilen.append(
        "  Gesehen? `befund_leseflaeche.py --alle-gesehen` — sonst erscheint es wieder."
    )
    return "\n".join(zeilen)


def exit_kriterium(state: dict) -> tuple[bool, str]:
    """L4: Etappe 2 darf starten, wenn kein Befund die Sicht-Frist unbestaetigt reisst."""
    ueberfaellig = [p for p in offene(state) if timedelta(days=p[2]) >= SICHT_FRIST]
    if not ueberfaellig:
        return True, (
            f"L4 erfuellt: kein unbestaetigter Befund aelter als {SICHT_FRIST.days} Tage."
        )
    aeltester = ueberfaellig[0]
    return False, (
        f"L4 NICHT erfuellt: {len(ueberfaellig)} unbestaetigte(r) Befund(e) ueber der "
        f"Sicht-Frist, aeltester {aeltester[0]} seit {aeltester[2]} Tagen."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--gesehen", nargs="+", default=None)
    ap.add_argument("--alle-gesehen", action="store_true")
    ap.add_argument("--exit-kriterium", action="store_true")
    ap.add_argument("--repo-dir", type=Path, default=Path.cwd())
    a = ap.parse_args(argv)

    state = lade_state()

    if a.gesehen or a.alle_gesehen:
        jetzt = _iso(_jetzt())
        ziele = a.gesehen or [s for s, _, _ in offene(state)]
        n = 0
        for s in ziele:
            e = (state.get("befunde") or {}).get(s)
            if e is not None and not e.get("bestaetigt"):
                e["bestaetigt"] = jetzt
                n += 1
        schreibe_state(state)
        print(f"✓ {n} Befund(e) als gesehen markiert.")
        return 0

    report = None
    if a.report:
        try:
            report = json.loads(a.report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0
    else:
        letzter = _parse(state.get("letzter_abruf", "") or "")
        if letzter is None or (_jetzt() - letzter) >= ABRUF_INTERVALL:
            report = hole_report(a.repo_dir)
    if report is not None:
        state = verschmelze(state, report)
        schreibe_state(state)

    if a.exit_kriterium:
        ok, text = exit_kriterium(state)
        print(text)
        return 0 if ok else 1

    ausgabe = rendere(state)
    if ausgabe:
        print(ausgabe)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — fail-open, s. Modul-Docstring
        sys.exit(0)
