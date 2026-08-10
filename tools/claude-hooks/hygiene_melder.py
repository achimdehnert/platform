#!/usr/bin/env python3
"""SessionStart-Melder fuer zwei stille Ansammlungen.

Beide Klassen wachsen, ohne dass jemand es merkt — weil das Werkzeug, das sie
aufraeumt, aus gutem Grund schweigt, wenn es nichts tun darf.

**Abgelaufene Leases.** `repo-session.sh reap` ueberspringt dirty Worktrees
korrekt (fremde, unfertige Arbeitsstaende) und meldet das nur im eigenen Lauf.
Wer nie reapt, erfaehrt nie davon. Gemessen 2026-08-02: 79 von 116 offenen
Leases waren ueber ihr `expires_at` hinaus, die aeltesten sieben Wochen alt.

Seit 2026-08-10 (#1866) nennt der Melder nicht mehr EINE Zahl. Eine einzige Zahl
war eine Aufforderung, die niemand erfuellen konnte: von 68 abgelaufenen Leases
konnte `reap` an dem Tag **keines** abraeumen, weil keines einen gemergten PR
hatte. Ein Melder, dessen Zahl durch das von ihm empfohlene Mittel nicht kleiner
wird, wird dauerhaft rot — und ein dauerhaft roter Melder meldet nichts mehr.

Getrennt wird deshalb in zwei Klassen, lokal und ohne Netz:

    Kandidat   Worktree clean, Branch bestimmbar → `reap` entscheidet am
               PR-Zustand, ob es ihn nimmt. Das ist die Aufforderung.
    Sichten    dirty, detached HEAD oder Worktree weg → `reap` fasst diese
               NIE an. Das ist ein Bestand, keine Aufgabe.

Die Klassifikation ruft `git status` je Lease und laeuft unter einem Zeitbudget
(gemessen: 68 Leases in 0,8 s). Reisst das Budget, wird der Rest als
**unklassifiziert** ausgewiesen statt stillschweigend einer Klasse zugeschlagen.

**Verteilte Kopien.** Hooks unter `~/.claude/hooks/` sind Kopien aus
`platform/tools/claude-hooks/` bzw. `platform/tools/hooks/`. Driften sie, wirkt
ein Fix in platform nicht — und der laufende Hook ist die Kopie. Der
cc-skill-dist-Generator wird bewusst nicht benutzt: sein `--target` tauscht ein
ganzes Verzeichnis aus und hat `~/.claude` schon einmal ersetzt.

Vertrag: **immer Exit 0**, Ausgabe nur bei Befund. Ein Melder darf nie blockieren.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

LEASES = Path.home() / ".repo-session" / "leases"
KOPIEN = Path.home() / ".claude" / "hooks"
QUELLEN = ("tools/claude-hooks", "tools/hooks")


def abgelaufene_leases(
    jetzt: dt.datetime, wurzel: Path = LEASES
) -> list[tuple[str, int]]:
    """(Lease-Name, Tage ueberfaellig), aelteste zuerst."""
    if not wurzel.is_dir():
        return []
    treffer: list[tuple[str, int]] = []
    for p in sorted(wurzel.glob("*.json")):
        try:
            daten = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        roh = daten.get("expires_at")
        if not roh:
            continue
        try:
            ende = dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ende.tzinfo is None:
            ende = ende.replace(tzinfo=dt.timezone.utc)
        if ende < jetzt:
            treffer.append((p.stem, (jetzt - ende).days))
    return sorted(treffer, key=lambda t: -t[1])


def _git(pfad: str, *args: str, timeout: float = 5.0) -> tuple[int, str]:
    """git im Worktree. Jeder Fehler wird zu (rc!=0, "") — ein Melder wirft nie."""
    try:
        fertig = subprocess.run(
            ["git", "-C", pfad, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return fertig.returncode, fertig.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def lease_klassen(
    jetzt: dt.datetime,
    wurzel: Path = LEASES,
    zeitbudget: float = 8.0,
    _uhr=time.monotonic,
) -> dict[str, list[str] | int]:
    """Abgelaufene Leases in 'kandidat' und die Sicht-Klassen trennen.

    Rein lokal: kein `gh`, kein Netz. Die Frage "nimmt `reap` das?" haengt am
    PR-Zustand und ist damit hier nicht abschliessend beantwortbar — deshalb
    heisst die Klasse **Kandidat** und nicht "abraeumbar".
    """
    ergebnis: dict[str, list[str] | int] = {
        "kandidat": [],
        "dirty": [],
        "detached": [],
        "ohne_worktree": [],
        "unklassifiziert": 0,
    }
    start = _uhr()
    for name, _tage in abgelaufene_leases(jetzt, wurzel):
        pfad = wurzel / f"{name}.json"
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        baum = daten.get("worktree") or ""
        if not baum or not Path(baum).is_dir():
            ergebnis["ohne_worktree"].append(name)  # type: ignore[union-attr]
            continue
        if _uhr() - start > zeitbudget:
            # Lieber ehrlich unklassifiziert als falsch einsortiert.
            ergebnis["unklassifiziert"] += 1  # type: ignore[operator]
            continue
        rc, aus = _git(baum, "status", "--porcelain", "--untracked-files=no")
        if rc != 0:
            ergebnis["ohne_worktree"].append(name)  # type: ignore[union-attr]
            continue
        if aus.strip():
            ergebnis["dirty"].append(name)  # type: ignore[union-attr]
            continue
        if _git(baum, "symbolic-ref", "-q", "HEAD")[0] != 0:
            ergebnis["detached"].append(name)  # type: ignore[union-attr]
            continue
        ergebnis["kandidat"].append(name)  # type: ignore[union-attr]
    return ergebnis


def _hash(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def driftende_kopien(platform: Path, kopien: Path = KOPIEN) -> list[str]:
    """Dateinamen, die als Kopie existieren und von ihrer Quelle abweichen."""
    if not kopien.is_dir():
        return []
    quelle: dict[str, Path] = {}
    for rel in QUELLEN:
        d = platform / rel
        if d.is_dir():
            for p in d.iterdir():
                if p.is_file():
                    quelle.setdefault(p.name, p)

    drift: list[str] = []
    for kopie in sorted(kopien.iterdir()):
        if not kopie.is_file() or kopie.name not in quelle:
            continue
        a, b = _hash(kopie), _hash(quelle[kopie.name])
        if a and b and a != b:
            drift.append(kopie.name)
    return drift


def _platform_wurzel() -> Path:
    """Der platform-Checkout — von hier aus zwei Ebenen hoch."""
    return Path(__file__).resolve().parent.parent.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", default=str(_platform_wurzel()))
    ap.add_argument("--leases", default=str(LEASES))
    args = ap.parse_args(argv)

    try:
        json.load(sys.stdin)  # SessionStart-JSON; Inhalt wird nicht gebraucht
    except Exception:  # noqa: BLE001 — stdin darf fehlen oder Muell sein
        pass

    zeilen: list[str] = []

    jetzt = dt.datetime.now(dt.timezone.utc)
    alt = abgelaufene_leases(jetzt, Path(args.leases))
    if alt:
        klassen = lease_klassen(jetzt, Path(args.leases))
        kandidat = len(klassen["kandidat"])  # type: ignore[arg-type]
        sichten = (
            len(klassen["dirty"])  # type: ignore[arg-type]
            + len(klassen["detached"])  # type: ignore[arg-type]
            + len(klassen["ohne_worktree"])  # type: ignore[arg-type]
        )
        teile = [
            f"· {len(alt)} abgelaufene repo-session-Leases (aeltester {alt[0][1]} Tage "
            f"ueberfaellig): {kandidat} Kandidat(en), {sichten} zum Sichten."
        ]
        if kandidat:
            teile.append(
                "  Kandidaten sind clean und haben einen Branch — "
                "`bash tools/repo-session.sh reap ~/github/<repo>` nimmt davon die, "
                "deren PR gemergt ist. Die uebrigen bleiben liegen, das ist richtig."
            )
        gruende = [
            f"{len(klassen[k])} {wort}"  # type: ignore[arg-type]
            for k, wort in (
                ("dirty", "dirty"),
                ("detached", "detached HEAD"),
                ("ohne_worktree", "ohne Worktree"),
            )
            if klassen[k]
        ]
        if gruende:
            teile.append(
                "  Zum Sichten (" + ", ".join(gruende) + ") — `reap` fasst diese NIE "
                "an; sie gehoeren jemandem und wollen angesehen, nicht entfernt werden."
            )
        if klassen["unklassifiziert"]:
            teile.append(
                f"  {klassen['unklassifiziert']} unklassifiziert (Zeitbudget) — "
                f"nicht als 'in Ordnung' lesen."
            )
        zeilen.append("\n".join(teile))

    drift = driftende_kopien(Path(args.platform))
    if drift:
        zeilen.append(
            f"· {len(drift)} verteilte Hook-Kopie(n) weichen von der platform-Quelle ab: "
            + ", ".join(drift)
            + ". Der LAUFENDE Hook ist die Kopie — ein Fix in platform wirkt erst nach "
            "dem Nachziehen."
        )

    if not zeilen:
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "🧹 hygiene-melder:\n" + "\n".join(zeilen),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
