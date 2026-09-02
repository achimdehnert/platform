#!/usr/bin/env python3
"""modellwechsel_check.py — K2 (platform#2690): Modellwechsel ist Teil des Starts.

Vergleicht "bewertet mit" (`assessed_with` aus den Policy-Kopfzeilen,
~/.claude/policies/*.md, Zeile 2) gegen "läuft mit" (`neu`-Feld der letzten
Zeile in model-changes.log) und klassifiziert die Differenz nach der
§0-Tabelle des Runbooks (docs/governance/model-rebaseline-runbook.md).

Der Maßstab ist ausdrücklich "bewertet ↔ läuft", NICHT "Vorgänger ↔
Nachfolger" — model-changes.log protokolliert Session-Übergänge, aber das
Ritual (Runbook §3a) hängt daran, ob das AKTUELL laufende Modell noch das
ist, mit dem die Policies zuletzt bewertet wurden.

Die Klassifikation (MAJOR/MINOR/SUFFIX) ist eine Python-Portierung der
Bash-Funktionen norm_id/fam_major/datum_teil/version_kette aus
tools/claude-hooks/model_change_detector.sh (dort ~Zeilen 61-87) — bewusst
NICHT neu erfunden, weil dieser Klassifizierer nach #2655/#2664 (Versions-
Regex verlor die zweite Stelle, Alias nicht normalisiert) bereits einmal
korrigiert wurde. tools/tests/test_modellwechsel_check.py vergleicht beide
Implementierungen auf denselben Beispielen.

Aufruf:
  python3 tools/modellwechsel_check.py [--kurz] [--behandelt]
      [--log PATH] [--handled PATH] [--policies-dir PATH]

Exit 0 = nichts fällig · Exit 1 = fällig (MAJOR oder MINOR, unbehandelt).
stdlib-only.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOG = Path.home() / ".claude" / "hooks" / "state" / "model-changes.log"
DEFAULT_HANDLED = (
    Path.home() / ".claude" / "hooks" / "state" / "model-rebaseline-handled.tsv"
)
DEFAULT_POLICIES_DIR = Path.home() / ".claude" / "policies"
RUNBOOK = "docs/governance/model-rebaseline-runbook.md"

# ── Klassifizierer, portiert aus model_change_detector.sh (Runbook §0) ──────
_SUFFIX_RE = re.compile(r"\[[^\]]*\]$")
_FAM_MAJOR_RE = re.compile(r"^claude-([a-z]+)-(\d+)(?:[^0-9].*)?$")
_DATUM_RE = re.compile(r"^.*-(\d{6,})$")
_VERSION_KETTE_RE = re.compile(r"^claude-[a-z]+-(.*)$")


def norm_id(model_id: str) -> str:
    """sed -E 's/\\[[^]]*\\]$//' — Variante-Suffix am Ende entfernen."""
    return _SUFFIX_RE.sub("", model_id)


def fam_major(model_id: str) -> str | None:
    """Familie + erste Versionsstelle. None bei unbekannter Form (fail-loud)."""
    m = _FAM_MAJOR_RE.match(model_id)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def datum_teil(model_id: str) -> str | None:
    """Datums-Snapshot: Segment mit 6+ Ziffern am Ende. None wenn keins trägt."""
    m = _DATUM_RE.match(model_id)
    return m.group(1) if m else None


def version_kette(model_id: str) -> str | None:
    """Alles nach der Familie: vollständige Versionskette inkl. Datum."""
    m = _VERSION_KETTE_RE.match(model_id)
    return m.group(1) if m else None


def classify_change(prev: str, curr: str) -> str:
    """MAJOR/MINOR/SUFFIX nach Runbook §0. Vorbedingung: prev != curr (Aufrufer

    prüft Gleichheit separat — GLEICH ist im Detektor kein loggbares Ereignis).
    """
    p, c = norm_id(prev), norm_id(curr)
    if p == c:
        return "SUFFIX"
    fm_p = fam_major(p)
    if not fm_p or fm_p != fam_major(c):
        return "MAJOR"
    if datum_teil(p) != datum_teil(c):
        return "MAJOR"
    if version_kette(p) != version_kette(c):
        return "MINOR"
    return "SUFFIX"


KONSEQUENZ = {
    "MAJOR": "Vollmachten suspendiert (§3a), Smoke §1 + Köder §2 + Kommentar #1640 fällig",
    "MINOR": "Smoke §1 genügt, assessed_with im nächsten Ritual nachziehen",
    "SUFFIX": "kein Ereignis",
    "GLEICH": "kein Ereignis",
}


@dataclass
class LogEntry:
    raw: str
    utc: str
    alt: str
    neu: str
    klasse_log: str


def read_last_log_entry(log_path: Path) -> LogEntry | None:
    if not log_path.exists():
        return None
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    raw = lines[-1]
    parts = raw.split("\t")
    if len(parts) != 4:
        return None
    utc, alt, neu, klasse_log = parts
    return LogEntry(raw=raw, utc=utc, alt=alt, neu=neu, klasse_log=klasse_log)


_ASSESSED_RE = re.compile(r"assessed_with:\s*([^\s|]+)")


def read_assessed_with(policies_dir: Path) -> tuple[str | None, list[tuple[str, str]]]:
    """Liest Zeile 2 jeder Policy-Datei. Gibt (Mehrheitswert, [(Datei, Wert), ...])."""
    pairs: list[tuple[str, str]] = []
    if not policies_dir.is_dir():
        return None, pairs
    for path in sorted(policies_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 2:
            continue
        m = _ASSESSED_RE.search(lines[1])
        if m:
            pairs.append((path.name, m.group(1)))
    if not pairs:
        return None, pairs
    counts = Counter(value for _, value in pairs)
    majority = counts.most_common(1)[0][0]
    return majority, pairs


def read_handled(handled_path: Path) -> set[str]:
    if not handled_path.exists():
        return set()
    return {ln for ln in handled_path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def mark_handled(handled_path: Path, raw_line: str) -> None:
    handled = read_handled(handled_path)
    if raw_line in handled:
        return
    handled_path.parent.mkdir(parents=True, exist_ok=True)
    with handled_path.open("a", encoding="utf-8") as fh:
        fh.write(raw_line + "\n")


def consensus_note(pairs: list[tuple[str, str]]) -> str:
    counts = Counter(value for _, value in pairs)
    if len(counts) <= 1:
        return ""
    parts = ", ".join(f"{v} ({n})" for v, n in counts.most_common())
    return f" (uneinheitlich unter {len(pairs)} Policies: {parts} — Mehrheit gewertet)"


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--handled", type=Path, default=DEFAULT_HANDLED)
    parser.add_argument("--policies-dir", type=Path, default=DEFAULT_POLICIES_DIR)
    parser.add_argument("--kurz", action="store_true", help="eine Zeile statt Bericht")
    parser.add_argument(
        "--behandelt",
        action="store_true",
        help="letzte Log-Zeile als behandelt markieren (nach Smoke)",
    )
    return parser.parse_args()


def main() -> int:
    args = build_args()
    entry = read_last_log_entry(args.log)
    if entry is None:
        msg = "modellwechsel: kein Ereignis (Log leer/fehlt) — nichts fällig"
        print(msg)
        return 0

    assessed, pairs = read_assessed_with(args.policies_dir)
    if assessed is None:
        msg = (
            "modellwechsel: kein assessed_with in "
            f"{args.policies_dir} gefunden — kann nicht klassifizieren, nichts fällig"
        )
        print(msg)
        return 0

    running = entry.neu
    klasse = "GLEICH" if assessed == running else classify_change(assessed, running)

    if args.behandelt:
        mark_handled(args.handled, entry.raw)

    behandelt = entry.raw in read_handled(args.handled)
    faellig = klasse in ("MAJOR", "MINOR") and not behandelt
    konsequenz = KONSEQUENZ[klasse]
    note = consensus_note(pairs)

    if args.kurz:
        print(
            f"modellwechsel: {klasse} bewertet={assessed} läuft={running} "
            f"behandelt={'ja' if behandelt else 'nein'} "
            f"fällig={'ja' if faellig else 'nein'} — {konsequenz}"
        )
    else:
        print("Modellwechsel-Check (K2 platform#2690)")
        print(
            f"  letztes Ereignis:  {entry.utc}  {entry.alt} → {entry.neu}"
            f"  (Detektor-Klasse: {entry.klasse_log})"
        )
        print(f"  bewertet mit:      {assessed}{note}")
        print(f"  läuft mit:         {running}")
        print(f"  Einstufung:        {klasse}")
        print(f"  behandelt:         {'ja' if behandelt else 'nein'}")
        print(f"  fällig:            {'ja' if faellig else 'nein'}")
        print(f"  Konsequenz:        {konsequenz}")
        print(f"  Runbook:           {RUNBOOK}")

    return 1 if faellig else 0


if __name__ == "__main__":
    raise SystemExit(main())
