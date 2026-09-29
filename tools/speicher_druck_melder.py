#!/usr/bin/env python3
"""Speicherdruck auf dem Sitzungs-Host melden, bevor der Kernel toetet (platform#3607).

## Warum es das gibt

Am 2026-09-26 zwischen 08:06 und 11:08 UTC toetete ein globaler OOM auf dev-desktop 35
Prozesse, darunter den CI-Runner von mcp-hub (3 Tage tot, platform#3606), cloudflared und
Dev-Dienste. Den Speicher hielten 16 Worker eines Optimierungslaufs (je ~1,4 GB, zusammen
22,4 GB) in einer Login-Sitzung. Zuerst traf es kleine Prozesse mit hohem
`oom_score_adj` (der erste: ein 44-kB-gpg-agent mit 500), nicht die Worker. Laut sar waren
um 08:00 noch 60 % frei. Der Einbruch kam also binnen Minuten, danach stand die Maschine
drei Stunden bei 1 % verfuegbar und 100 % Swap. Niemand hat es gesehen, denn auf dem Host
lief weder `systemd-oomd` noch ein Exporter.

Der Melder verhindert den ersten Kill nicht, dafuer ist das Fenster zu kurz. Er sorgt aber
dafuer, dass die laufende und die naechste Sitzung binnen einer Minute wissen, WER den
Speicher haelt, statt es Tage spaeter aus dem Kernel-Log zu rekonstruieren.

## Was gemessen wird (nur lesend, nur /proc)

- `/proc/pressure/memory`: `some avg60` ist der Anteil der Zeit, in der Prozesse auf
  Speicher warten. Das ist das Fruehsignal. Swap-Belegung allein ist es nicht, denn
  ausgelagerte Seiten bleiben liegen (gemessen 2026-09-29 im Ruhezustand: 5 von 7 GB).
- `/proc/meminfo`: Anteil `MemAvailable`.
- `/proc/vmstat oom_kill`: der Zaehler seit dem Boot. Ein Zuwachs seit dem letzten Lauf ist
  ein Kill, auch wenn der Druck zwischen zwei Laeufen kam und wieder ging.

Bei einem Befund haelt der Melder fest, wer den Speicher haelt: je cgroup die Summe aus
`RssAnon` und `VmSwap` aus `/proc/<pid>/status`, dazu Prozesszahl und haeufigster
Prozessname. Kommandozeilen und Umgebung liest er nie (Secrets), das sichert ein Test ab.

## Ablage

Journal (nur Befunde, hoechstens alle 5 min): `~/.claude/speicher-druck-journal.jsonl`.
Ergebnis (jeder Lauf): `~/.repo-session/melder/speicher-druck.json`. Der Sitzungsstart
liest es mit `--lesen` (0.7.30).

    python3 tools/speicher_druck_melder.py            # messen, ablegen (Timer, jede Minute)
    python3 tools/speicher_druck_melder.py --lesen    # nur letztes Ergebnis lesen

Exit bei `--lesen`: 0 ruhig, 1 Befund in den letzten 24 h, 2 kein frisches Ergebnis.
Beim Messen immer 0: ein minuetlich rot werdender Dienst waere Rauschen (wie registry-probe).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import melder_ergebnis  # noqa: E402

WERKZEUG_VERSION = "1"
MELDER = "speicher_druck_melder"
PROC_STANDARD = Path("/proc")
JOURNAL_STANDARD = Path.home() / ".claude" / "speicher-druck-journal.jsonl"
ERGEBNIS_STANDARD = Path.home() / ".repo-session" / "melder" / "speicher-druck.json"

# Schwellen. PSI 10 %: im Ruhebetrieb liegt `some avg60` bei 0,00 (gemessen 2026-09-29);
# 10 % heisst, jede zehnte Sekunde wartet ein Prozess auf Speicher, spuerbar, aber noch
# lange vor dem Kill. MemAvailable 10 %: unterhalb davon bleibt dem Kernel kaum Cache.
PSI_SOME_AVG60_SCHWELLE = 10.0
MEM_VERFUEGBAR_PROZENT_SCHWELLE = 10.0
# Der Timer laeuft jede Minute. Ein Ergebnis, das aelter als 15 min ist, heisst: der Timer
# steht. Das ist ein Befund, nie ein PASS.
MAX_ALTER = timedelta(minutes=15)
# Ein Befund bleibt 24 h sichtbar, damit ihn auch die naechste Sitzung am Morgen sieht.
BEFUND_SICHTBAR = timedelta(hours=24)
SCHNAPPSCHUSS_ABSTAND = timedelta(minutes=5)
TOP_GRUPPEN = 5


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return (
        t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _von_iso(s: object) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Messen ────────────────────────────────────────────────────────────────────


def lies_meminfo(proc: Path) -> dict[str, int]:
    """Werte in kB."""
    werte: dict[str, int] = {}
    for zeile in (proc / "meminfo").read_text(encoding="utf-8").splitlines():
        name, _, rest = zeile.partition(":")
        teile = rest.split()
        if teile and teile[0].isdigit():
            werte[name.strip()] = int(teile[0])
    return werte


def lies_psi(proc: Path) -> dict[str, float]:
    """`some`/`full` avg60 in Prozent. Fehlt PSI (Kernel ohne CONFIG_PSI), leer."""
    try:
        text = (proc / "pressure" / "memory").read_text(encoding="utf-8")
    except OSError:
        return {}
    werte: dict[str, float] = {}
    for zeile in text.splitlines():
        teile = zeile.split()
        if not teile:
            continue
        for feld in teile[1:]:
            k, _, v = feld.partition("=")
            if k == "avg60":
                werte[teile[0]] = float(v)
    return werte


def lies_oom_kill(proc: Path) -> int | None:
    for zeile in (proc / "vmstat").read_text(encoding="utf-8").splitlines():
        teile = zeile.split()
        if len(teile) == 2 and teile[0] == "oom_kill":
            return int(teile[1])
    return None


def schnappschuss(proc: Path, top: int = TOP_GRUPPEN) -> list[dict]:
    """Je cgroup: anon+swap (MB), Prozesszahl, haeufigster Name. Groesste zuerst."""
    gruppen: dict[str, dict] = {}
    for d in proc.iterdir():
        if not d.name.isdigit():
            continue
        try:
            status = (d / "status").read_text(encoding="utf-8")
            cgroup = (d / "cgroup").read_text(encoding="utf-8")
        except OSError:
            continue  # Prozess inzwischen beendet oder nicht lesbar
        felder = {}
        for zeile in status.splitlines():
            k, _, v = zeile.partition(":")
            felder[k] = v.strip()
        kb = 0
        for k in ("RssAnon", "VmSwap"):
            teile = felder.get(k, "").split()
            if teile and teile[0].isdigit():
                kb += int(teile[0])
        if not kb:
            continue  # Kernel-Threads und leere Prozesse
        pfad = "?"
        for zeile in cgroup.splitlines():
            if zeile.startswith("0::"):
                pfad = zeile[3:] or "/"
        g = gruppen.setdefault(pfad, {"kb": 0, "namen": Counter()})
        g["kb"] += kb
        g["namen"][felder.get("Name", "?")] += 1
    reihe = sorted(gruppen.items(), key=lambda kv: -kv[1]["kb"])[:top]
    return [
        {
            "cgroup": pfad,
            "mb": round(g["kb"] / 1024),
            "prozesse": sum(g["namen"].values()),
            "name": g["namen"].most_common(1)[0][0],
        }
        for pfad, g in reihe
    ]


def bewerte(
    meminfo: dict[str, int], psi: dict[str, float], oom_delta: int
) -> list[str]:
    """Regeln, die feuern. Leer = ruhig."""
    regeln = []
    some = psi.get("some")
    if some is not None and some >= PSI_SOME_AVG60_SCHWELLE:
        regeln.append(f"psi-some-avg60 {some:.1f} % >= {PSI_SOME_AVG60_SCHWELLE:.0f} %")
    gesamt = meminfo.get("MemTotal", 0)
    if gesamt:
        verf = 100.0 * meminfo.get("MemAvailable", 0) / gesamt
        if verf < MEM_VERFUEGBAR_PROZENT_SCHWELLE:
            regeln.append(
                f"mem-verfuegbar {verf:.1f} % < {MEM_VERFUEGBAR_PROZENT_SCHWELLE:.0f} %"
            )
    if oom_delta > 0:
        regeln.append(f"oom-kill +{oom_delta} seit letztem Lauf")
    return regeln


def messe(proc: Path, vorher: dict | None, jetzt: datetime) -> tuple[dict, dict | None]:
    """Ergebnis fuer die Huelle und, falls faellig, eine Journal-Zeile."""
    meminfo = lies_meminfo(proc)
    psi = lies_psi(proc)
    oom = lies_oom_kill(proc)
    alt = (vorher or {}).get("ergebnis") or {}
    oom_alt = alt.get("oom_kill_zaehler")
    # Kleinerer Zaehler als vorher = Neustart dazwischen; der Zuwachs ist dann unbekannt.
    oom_delta = 0
    if isinstance(oom_alt, int) and oom is not None and oom >= oom_alt:
        oom_delta = oom - oom_alt
    regeln = bewerte(meminfo, psi, oom_delta)
    gesamt = meminfo.get("MemTotal", 0) or 1
    swap_gesamt = meminfo.get("SwapTotal", 0)
    ergebnis = {
        "psi_some_avg60": psi.get("some"),
        "psi_full_avg60": psi.get("full"),
        "mem_verfuegbar_prozent": round(
            100.0 * meminfo.get("MemAvailable", 0) / gesamt, 1
        ),
        "swap_belegt_prozent": (
            round(100.0 * (swap_gesamt - meminfo.get("SwapFree", 0)) / swap_gesamt, 1)
            if swap_gesamt
            else None
        ),
        "oom_kill_zaehler": oom,
        "regeln": regeln,
        "letzter_befund": alt.get("letzter_befund"),
    }
    journal = None
    if regeln:
        letzter = alt.get("letzter_befund") or {}
        letzte_zeit = _von_iso(letzter.get("zeit"))
        faellig = letzte_zeit is None or jetzt - letzte_zeit >= SCHNAPPSCHUSS_ABSTAND
        gruppen = schnappschuss(proc) if faellig else letzter.get("gruppen", [])
        ergebnis["letzter_befund"] = {
            "zeit": _iso(jetzt) if faellig else letzter.get("zeit"),
            "regeln": regeln,
            "gruppen": gruppen,
        }
        if faellig:
            messwerte = {k: v for k, v in ergebnis.items() if k != "letzter_befund"}
            journal = {"zeit": _iso(jetzt), **messwerte, "gruppen": gruppen}
    return ergebnis, journal


# ── Lesen (Sitzungsstart) ─────────────────────────────────────────────────────


def zeile_lesen(daten: dict | None, jetzt: datetime) -> tuple[int, str]:
    if daten is None:
        return (
            2,
            "kein Ergebnis (speicher-druck.timer installiert? README host-maintenance)",
        )
    gemessen = _von_iso(daten.get("gemessen_am"))
    if gemessen is None or jetzt - gemessen > MAX_ALTER:
        return 2, f"Ergebnis veraltet ({daten.get('gemessen_am')}), Timer steht"
    e = daten.get("ergebnis", {})
    stand = (
        f"PSI {e.get('psi_some_avg60')} % · verfuegbar {e.get('mem_verfuegbar_prozent')} % "
        f"· Swap {e.get('swap_belegt_prozent')} %"
    )
    befund = e.get("letzter_befund") or {}
    zeit = _von_iso(befund.get("zeit"))
    if zeit is not None and jetzt - zeit <= BEFUND_SICHTBAR:
        top = befund.get("gruppen") or [{}]
        g = top[0]
        return 1, (
            f"Speicherdruck {befund.get('zeit')}: {'; '.join(befund.get('regeln', []))} "
            f"— groesste cgroup {g.get('cgroup')} {g.get('mb')} MB "
            f"({g.get('prozesse')}x {g.get('name')}) · jetzt {stand}"
        )
    return 0, stand


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--proc", type=Path, default=PROC_STANDARD)
    p.add_argument("--journal", type=Path, default=JOURNAL_STANDARD)
    p.add_argument("--ergebnis-datei", type=Path, default=ERGEBNIS_STANDARD)
    p.add_argument(
        "--lesen", action="store_true", help="nur letztes Ergebnis lesen, eine Zeile"
    )
    a = p.parse_args(argv)
    jetzt = _jetzt()
    if a.lesen:
        rc, text = zeile_lesen(
            melder_ergebnis.lies(a.ergebnis_datei, max_alter_tage=1), jetzt
        )
        print(text)
        return rc
    vorher = melder_ergebnis.lies(a.ergebnis_datei, max_alter_tage=1)
    ergebnis, journal = messe(a.proc, vorher, jetzt)
    melder_ergebnis.schreibe(
        a.ergebnis_datei,
        MELDER,
        ergebnis,
        werkzeug_version=WERKZEUG_VERSION,
        gemessen_am=jetzt,
    )
    if journal is not None:
        a.journal.parent.mkdir(parents=True, exist_ok=True)
        with a.journal.open("a", encoding="utf-8") as f:
            f.write(json.dumps(journal, ensure_ascii=False) + "\n")
        print(f"BEFUND {'; '.join(ergebnis['regeln'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
