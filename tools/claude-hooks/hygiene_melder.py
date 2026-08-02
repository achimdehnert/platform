#!/usr/bin/env python3
"""SessionStart-Melder fuer zwei stille Ansammlungen.

Beide Klassen wachsen, ohne dass jemand es merkt — weil das Werkzeug, das sie
aufraeumt, aus gutem Grund schweigt, wenn es nichts tun darf.

**Abgelaufene Leases.** `repo-session.sh reap` ueberspringt dirty Worktrees
korrekt (fremde, unfertige Arbeitsstaende) und meldet das nur im eigenen Lauf.
Wer nie reapt, erfaehrt nie davon. Gemessen 2026-08-02: 79 von 116 offenen
Leases waren ueber ihr `expires_at` hinaus, die aeltesten sieben Wochen alt.

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
import sys
from pathlib import Path

LEASES = Path.home() / ".repo-session" / "leases"
KOPIEN = Path.home() / ".claude" / "hooks"
QUELLEN = ("tools/claude-hooks", "tools/hooks")


def abgelaufene_leases(jetzt: dt.datetime, wurzel: Path = LEASES) -> list[tuple[str, int]]:
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

    alt = abgelaufene_leases(dt.datetime.now(dt.timezone.utc), Path(args.leases))
    if alt:
        aeltester = alt[0][1]
        zeilen.append(
            f"· {len(alt)} abgelaufene repo-session-Leases, aeltester {aeltester} Tage ueberfaellig. "
            f"`bash tools/repo-session.sh reap ~/github/<repo>` raeumt gemergte und "
            f"CLEANE Worktrees ab; dirty Baeume bleiben bewusst stehen — die gehoeren "
            f"jemandem und wollen angesehen, nicht entfernt werden."
        )

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
                    "additionalContext": "🧹 hygiene-melder:\n" + "\n".join(zeilen)
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
