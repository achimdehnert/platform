#!/usr/bin/env python3
"""container_speicher_melder.py — Speicherdruck je Container aus der cgroup, nicht aus `docker stats` (#3400).

Anlass
------
gotenberg (doc-hub) stand in `docker stats` bei 92 % seines Limits von 512 MiB.
Die cgroup sagt etwas anderes (gemessen 2026-09-23 auf prod, nur lesend):
anon 217 MiB (42 %), kernel 64 MiB, file 186 MiB — der Rest ist freigebbarer
Datei-Cache, den `docker stats` mitzaehlt. Dafuer hatte der Kernel das Limit
1036-mal beruehrt (`memory.events max`), rund 13-mal am Tag, ohne einen einzigen
OOM-Kill. Die Frage „reicht das Limit?" laesst sich aus einer Stichprobe nicht
beantworten; dieser Melder misst sie sieben Tage lang und warnt danach dauerhaft.

Was gemessen wird
-----------------
Je laufendem Container MIT Speicherlimit auf prod (ssh-Alias `hetzner-prod`),
unter `/sys/fs/cgroup/system.slice/docker-<id>.scope/`:

  memory.max, memory.current, memory.peak
  memory.stat     anon, file, kernel
  memory.events   max (Limit beruehrt, Cache zurueckgeholt), oom_kill

Ein ssh-Aufruf, nur `cat`/`grep` — nichts wird auf dem Host installiert oder
geschrieben. `memory.peak` bleibt unberuehrt: ein Zuruecksetzen waere ein
Schreibzugriff auf Prod (#3400).

Jeder Lauf haengt EINE Zeile an ein Journal ausserhalb des Repos
(`~/.claude/container-speicher-journal.jsonl`, neben `speicher-journal.jsonl`);
Zeilen aelter als `JOURNAL_TAGE` fallen beim Schreiben heraus.

Regeln
------
  FEHLER  oom_kill ist seit dem letzten Lauf gestiegen.
  WARN    anon / memory.max > 70 %. Nur anon zaehlt: file ist Cache, den der
          Kernel vor einem OOM zurueckholt; anon kann er nicht zurueckholen.
  TREND   die Rate der `max`-Ereignisse der letzten 24 h ist mehr als doppelt so
          hoch wie die Tagesrate der Tage davor (bis 7 Tage zurueck). Die letzten
          24 h gehoeren absichtlich NICHT zur Basis — sonst verduennt ein Anstieg
          seine eigene Vergleichsgroesse. Braucht >= `TREND_MIN_BASIS_TAGE` Basis
          (vorher: SAMMELPHASE, ausdruecklich keine Entwarnung) und mindestens
          `TREND_MIN_EREIGNISSE` Ereignisse in 24 h, damit 0 -> 2 nicht ruft.

Zaehler (`oom_kill`, `max`) beginnen bei einem Neustart des Containers wieder bei
null. Faellt ein Zaehler, gilt der neue Wert als Zuwachs seit dem Neustart.

Grenze der Messung (Hypothese, nicht belegt): ein Takt von 15 min sieht kurze
anon-Spitzen einer einzelnen Konvertierung nicht. `memory.peak` faengt sie, zaehlt
aber Cache mit. Eine anon-Spitze unter der Taktung ist eine Untergrenze.

Wofuer die Messung da ist
-------------------------
Entscheid in #3400 am 2026-09-30: gotenberg-`mem_limit` auf 768m nur, wenn die
anon-Spitze der sieben Tage ueber 60 % des Limits liegt (`ENTSCHEID_ANTEIL`).
Der Vollbericht nennt diese Spitze je Container.

Exit-Codes
----------
0 = keine Befunde (auch SAMMELPHASE) · 1 = mindestens ein FEHLER/WARN/TREND
2 = blind: Host nicht erreichbar, keine Messung — blind ist nicht gruen.

Usage
-----
    python3 tools/container_speicher_melder.py              # messen + Vollbericht
    python3 tools/container_speicher_melder.py --kurz       # messen + eine Zeile
    python3 tools/container_speicher_melder.py --lesen      # nur letztes Ergebnis lesen (kein ssh)
    python3 tools/container_speicher_melder.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import melder_ergebnis  # noqa: E402

MELDER = "container_speicher_melder"
WERKZEUG_VERSION = "1"

HOST_STANDARD = "hetzner-prod"
SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
SSH_TIMEOUT_S = 60

ANON_WARN_ANTEIL = 0.70
ENTSCHEID_ANTEIL = 0.60
TREND_FAKTOR = 2.0
TREND_MIN_BASIS_TAGE = 2.0
TREND_MIN_EREIGNISSE = 10
TREND_FENSTER_TAGE = 7
JOURNAL_TAGE = 8
# Der Timer laeuft alle 15 min; vier verpasste Laeufe sind ein stehender Timer.
LESEN_MAX_ALTER_MIN = 60

_HOME = Path(os.environ.get("HOME", "/tmp"))
JOURNAL_STANDARD = _HOME / ".claude" / "container-speicher-journal.jsonl"
# Ablage wie die anderen Melder des Sitzungsstarts (session_start_checks.sh MELDER_DIR).
ERGEBNIS_STANDARD = _HOME / ".repo-session" / "melder" / "container-speicher.json"

STAT_FELDER = ("anon", "file", "kernel")
EVENT_FELDER = {"max": "ev_max", "oom_kill": "oom_kill"}

# Laeuft auf prod per `bash -s`. Nur lesen: docker ps + cat/grep auf der cgroup.
FERNSKRIPT = r"""
docker ps --no-trunc --format '{{.ID}} {{.Names}}' | while read -r id name; do
  d=/sys/fs/cgroup/system.slice/docker-$id.scope
  [ -r "$d/memory.max" ] || continue
  m=$(cat "$d/memory.max")
  [ "$m" = max ] && continue
  echo "@@ $name $m $(cat "$d/memory.current") $(cat "$d/memory.peak" 2>/dev/null || echo -)"
  grep -E '^(anon|file|kernel) ' "$d/memory.stat" | sed 's/^/s /'
  sed 's/^/e /' "$d/memory.events"
done
"""


# --- Messen -------------------------------------------------------------------


def parse_fernausgabe(text: str) -> dict[str, dict]:
    """Ausgabe von FERNSKRIPT -> {container: {max, current, peak, anon, ...}}."""
    raus: dict[str, dict] = {}
    aktuell: dict | None = None
    for zeile in text.splitlines():
        teile = zeile.split()
        if not teile:
            continue
        if teile[0] == "@@" and len(teile) == 5:
            try:
                aktuell = {
                    "max": int(teile[2]),
                    "current": int(teile[3]),
                    "peak": None if teile[4] == "-" else int(teile[4]),
                }
            except ValueError:
                aktuell = None
                continue
            raus[teile[1]] = aktuell
        elif aktuell is not None and len(teile) == 3 and teile[0] in ("s", "e"):
            schluessel = teile[1] if teile[0] == "s" else EVENT_FELDER.get(teile[1], "")
            if schluessel and (teile[0] == "e" or schluessel in STAT_FELDER):
                try:
                    aktuell[schluessel] = int(teile[2])
                except ValueError:
                    continue
    return raus


def messe(host: str) -> tuple[dict[str, dict] | None, str]:
    """(Messung, Fehlertext). Messung None = blind."""
    try:
        p = subprocess.run(
            [*SSH, host, "bash", "-s"],
            input=FERNSKRIPT,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return None, f"{host}: Zeitlimit {SSH_TIMEOUT_S} s"
    except OSError as fehler:
        return None, f"{host}: {fehler}"
    messung = parse_fernausgabe(p.stdout)
    if p.returncode != 0 and not messung:
        return None, f"{host}: ssh exit {p.returncode} {p.stderr.strip()[:120]}"
    if not messung:
        return None, f"{host}: kein Container mit Speicherlimit gefunden"
    return messung, ""


# --- Journal ------------------------------------------------------------------


def _zeit(roh: str) -> datetime:
    return datetime.fromisoformat(roh.replace("Z", "+00:00"))


def _iso(t: datetime) -> str:
    return (
        t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def lies_journal(pfad: Path) -> list[dict]:
    """Journal-Zeilen in Zeitordnung; kaputte Zeilen fallen heraus."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return []
    zeilen = []
    for roh in text.splitlines():
        try:
            z = json.loads(roh)
            z["_t"] = _zeit(z["ts"])
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if isinstance(z.get("container"), dict):
            zeilen.append(z)
    return sorted(zeilen, key=lambda z: z["_t"])


def schreibe_journal(
    pfad: Path, alte: list[dict], neu: dict, jetzt: datetime
) -> list[dict]:
    """Neue Zeile anhaengen, Zeilen aelter als JOURNAL_TAGE verwerfen; Ergebnis zurueck."""
    grenze = jetzt - timedelta(days=JOURNAL_TAGE)
    behalten = [z for z in alte if z["_t"] >= grenze] + [neu]
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(
        "".join(
            json.dumps(
                {k: v for k, v in z.items() if k != "_t"},
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for z in behalten
        ),
        encoding="utf-8",
    )
    tmp.replace(pfad)
    return behalten


def journal_zeile(host: str, messung: dict[str, dict], jetzt: datetime) -> dict:
    return {"ts": _iso(jetzt), "host": host, "container": messung, "_t": jetzt}


# --- Bewerten -----------------------------------------------------------------


def _zuwachs(vorher: int | None, nachher: int | None) -> int | None:
    """Zaehler-Zuwachs; ein gefallener Zaehler heisst Neustart -> neuer Wert zaehlt."""
    if vorher is None or nachher is None:
        return None
    return nachher - vorher if nachher >= vorher else nachher


def _schritte(journal: list[dict], name: str) -> list[tuple[datetime, float, int]]:
    """(Zeitpunkt, Tage seit Vorgaenger, max-Zuwachs) je aufeinanderfolgendem Paar."""
    raus = []
    vorher: tuple[datetime, int] | None = None
    for z in journal:
        c = z["container"].get(name)
        if not c or c.get("ev_max") is None:
            continue
        if vorher is not None:
            tage = (z["_t"] - vorher[0]).total_seconds() / 86400
            inc = _zuwachs(vorher[1], c["ev_max"])
            if tage > 0 and inc is not None:
                raus.append((z["_t"], tage, inc))
        vorher = (z["_t"], c["ev_max"])
    return raus


def trend(journal: list[dict], name: str, jetzt: datetime) -> dict:
    """Rate der max-Ereignisse: letzte 24 h gegen die Tage davor (bis 7 Tage)."""
    grenze_24h = jetzt - timedelta(days=1)
    grenze_basis = jetzt - timedelta(days=TREND_FENSTER_TAGE)
    n24 = t24 = nb = tb = 0.0
    for t, tage, inc in _schritte(journal, name):
        if t > grenze_24h:
            n24, t24 = n24 + inc, t24 + tage
        elif t > grenze_basis:
            nb, tb = nb + inc, tb + tage
    ergebnis = {
        "ereignisse_24h": int(n24),
        "basis_tage": round(tb, 2),
        "basis_rate_pro_tag": round(nb / tb, 1) if tb else None,
        "rate_24h_pro_tag": round(n24 / t24, 1) if t24 else None,
        "stand": "sammelphase",
        "feuert": False,
    }
    if tb < TREND_MIN_BASIS_TAGE or not t24:
        return ergebnis
    ergebnis["stand"] = "belastbar"
    basis = nb / tb
    ergebnis["feuert"] = (
        n24 >= TREND_MIN_EREIGNISSE and (n24 / t24) > TREND_FAKTOR * basis
    )
    return ergebnis


def anon_spitze(journal: list[dict], name: str) -> float | None:
    """Hoechster anon/max-Anteil ueber alle Journal-Zeilen (Grundlage des Entscheids)."""
    werte = [
        c["anon"] / c["max"]
        for z in journal
        if (c := z["container"].get(name)) and c.get("anon") is not None and c["max"]
    ]
    return max(werte) if werte else None


def bewerte(journal: list[dict], jetzt: datetime) -> dict:
    """Letzte Journal-Zeile gegen ihre Vorgaenger bewerten.

    `journal` enthaelt die aktuelle Messung bereits als letzte Zeile — so bewerten
    Messlauf und Tests exakt denselben Weg.
    """
    if not journal:
        return {"status": "blind", "container": [], "befunde": []}
    aktuell = journal[-1]
    vorher = journal[:-1]
    container, befunde = [], []
    for name, c in sorted(aktuell["container"].items()):
        vorgaenger = next(
            (z["container"][name] for z in reversed(vorher) if name in z["container"]),
            None,
        )
        oom_delta = _zuwachs(
            vorgaenger.get("oom_kill") if vorgaenger else None, c.get("oom_kill")
        )
        anon_anteil = (
            c["anon"] / c["max"] if c.get("anon") is not None and c["max"] else None
        )
        tr = trend(journal, name, jetzt)
        eintrag = {
            "name": name,
            "max": c["max"],
            "anon_anteil": round(anon_anteil, 3) if anon_anteil is not None else None,
            "anon_spitze": round(s, 3)
            if (s := anon_spitze(journal, name)) is not None
            else None,
            "oom_delta": oom_delta,
            "trend": tr,
        }
        container.append(eintrag)
        if oom_delta:
            befunde.append(
                {
                    "stufe": "FEHLER",
                    "name": name,
                    "text": f"oom_kill +{oom_delta}",
                }
            )
        if anon_anteil is not None and anon_anteil > ANON_WARN_ANTEIL:
            befunde.append(
                {
                    "stufe": "WARN",
                    "name": name,
                    "text": f"anon {anon_anteil:.0%} vom Limit",
                }
            )
        if tr["feuert"]:
            befunde.append(
                {
                    "stufe": "TREND",
                    "name": name,
                    "text": (
                        f"Limit-Treffer {tr['rate_24h_pro_tag']}/Tag "
                        f"statt {tr['basis_rate_pro_tag']}/Tag"
                    ),
                }
            )
    reihenfolge = {"FEHLER": 0, "WARN": 1, "TREND": 2}
    befunde.sort(key=lambda b: (reihenfolge[b["stufe"]], b["name"]))
    sammel = all(e["trend"]["stand"] == "sammelphase" for e in container)
    return {
        "status": "befund" if befunde else "ok",
        "gemessen_am": aktuell["ts"],
        "container": container,
        "befunde": befunde,
        "trend_sammelphase": sammel,
        "laeufe_im_journal": len(journal),
    }


# --- Ausgabe ------------------------------------------------------------------


def kurzzeile(e: dict) -> str:
    if e["status"] == "blind":
        return f"BLIND: {e.get('fehler', 'keine Messung')}"
    n = len(e["container"])
    zusatz = " · Trend: SAMMELPHASE" if e.get("trend_sammelphase") else ""
    if not e["befunde"]:
        return f"OK: {n} Container mit Limit, keine Befunde{zusatz}"
    teile = [f"{b['stufe']} {b['name']} {b['text']}" for b in e["befunde"][:4]]
    rest = len(e["befunde"]) - 4
    return (
        f"{len(e['befunde'])} Befund(e) in {n} Containern: "
        + " · ".join(teile)
        + (f" (+{rest} weitere)" if rest > 0 else "")
        + zusatz
    )


def vollbericht(e: dict, zeige: int = 12) -> str:
    zeilen = [
        f"# Container-Speicher (cgroup v2) — {e.get('gemessen_am', '?')}",
        "",
        kurzzeile(e),
        "",
    ]
    if e["befunde"]:
        zeilen += ["| Stufe | Container | Befund |", "|---|---|---|"]
        zeilen += [
            f"| {b['stufe']} | {b['name']} | {b['text']} |" for b in e["befunde"]
        ]
        zeilen.append("")
    rang = sorted(
        (c for c in e["container"] if c["anon_spitze"] is not None),
        key=lambda c: -c["anon_spitze"],
    )
    zeilen += [
        f"## anon-Spitze im Journal ({e.get('laeufe_im_journal', 0)} Laeufe), "
        f"Entscheid-Schwelle {ENTSCHEID_ANTEIL:.0%}",
        "",
        "| Container | Limit MiB | anon jetzt | anon Spitze | max-Treffer 24 h | Basis/Tag |",
        "|---|---|---|---|---|---|",
    ]
    for c in rang[:zeige]:
        tr = c["trend"]
        marke = " ⚑" if c["anon_spitze"] > ENTSCHEID_ANTEIL else ""
        zeilen.append(
            f"| {c['name']} | {c['max'] // 2**20} | {c['anon_anteil']:.0%} | "
            f"{c['anon_spitze']:.0%}{marke} | {tr['ereignisse_24h']} | "
            f"{tr['basis_rate_pro_tag'] if tr['basis_rate_pro_tag'] is not None else 'Sammelphase'} |"
        )
    return "\n".join(zeilen)


def exitcode(e: dict) -> int:
    return {"ok": 0, "befund": 1}.get(e["status"], 2)


def lesen(pfad: Path, jetzt: datetime) -> tuple[str, int]:
    """Letztes abgelegtes Ergebnis lesen — ohne ssh, fuer den Sitzungsstart."""
    daten = melder_ergebnis.lies(pfad, jetzt=jetzt)
    if daten is None:
        return f"NICHT GELAUFEN: kein frisches Ergebnis unter {pfad}", 2
    alter = jetzt - _zeit(daten["gemessen_am"])
    if alter > timedelta(minutes=LESEN_MAX_ALTER_MIN):
        return (
            f"NICHT GELAUFEN: letztes Ergebnis {int(alter.total_seconds() // 60)} min alt "
            "— container-speicher.timer pruefen",
            2,
        )
    e = daten["ergebnis"]
    return kurzzeile(e), exitcode(e)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--host", default=HOST_STANDARD)
    p.add_argument("--journal", type=Path, default=JOURNAL_STANDARD)
    p.add_argument("--ergebnis-datei", type=Path, default=ERGEBNIS_STANDARD)
    p.add_argument("--kurz", action="store_true")
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument(
        "--lesen",
        action="store_true",
        help="nicht messen, nur das zuletzt abgelegte Ergebnis lesen",
    )
    a = p.parse_args(argv)
    jetzt = datetime.now(timezone.utc)

    if a.lesen:
        text, rc = lesen(a.ergebnis_datei, jetzt)
        print(text)
        return rc

    messung, fehler = messe(a.host)
    if messung is None:
        e = {"status": "blind", "fehler": fehler, "container": [], "befunde": []}
    else:
        journal = schreibe_journal(
            a.journal,
            lies_journal(a.journal),
            journal_zeile(a.host, messung, jetzt),
            jetzt,
        )
        e = bewerte(journal, jetzt)
    melder_ergebnis.schreibe(
        a.ergebnis_datei,
        melder=MELDER,
        ergebnis=e,
        werkzeug_version=WERKZEUG_VERSION,
        gemessen_am=jetzt,
    )
    if a.als_json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif a.kurz:
        print(kurzzeile(e))
    else:
        print(vollbericht(e))
    return exitcode(e)


if __name__ == "__main__":
    sys.exit(main())
