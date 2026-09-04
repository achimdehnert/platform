#!/usr/bin/env python3
"""modellwechsel_check.py — K2 (platform#2690): Modellwechsel ist Teil des Starts.

Vergleicht "bewertet mit" (`assessed_with` aus den Policy-Kopfzeilen,
~/.claude/policies/*.md, Zeile 2) gegen "läuft mit" (das AKTUELL laufende
Modell) und klassifiziert die Differenz nach der §0-Tabelle des Runbooks
(docs/governance/model-rebaseline-runbook.md).

Der Maßstab ist ausdrücklich "bewertet ↔ läuft", NICHT "Vorgänger ↔
Nachfolger" — model-changes.log protokolliert Session-Übergänge, aber das
Ritual (Runbook §3a) hängt daran, ob das AKTUELL laufende Modell noch das
ist, mit dem die Policies zuletzt bewertet wurden.

**Laufendes Modell wird in dieser Reihenfolge ermittelt** (Befund #2693-Review:
model-changes.log trägt nur den settings-Alias, z.B. "fable"/"opus" — NICHT
die Gewichtsmatrix, also nie direkt vergleichbar mit `assessed_with`):
  (a) `--laufend <id>` — explizite Angabe, höchste Priorität;
  (b) neuestes Transkript des aktuellen Projekts
      (~/.claude/projects/<slug>/*.jsonl, slug = cwd mit "/"→"-"): letzte
      assistant-Zeile mit `message.model` beginnend "claude-";
  (c) NUR als letzter Fallback: die Alias-Tabelle unten, angewandt auf das
      `neu`-Feld der letzten model-changes.log-Zeile — mit Warnhinweis im
      Bericht ("Tabelle altert, Transkript fehlte"). Ein unbekannter Alias
      bleibt unverändert stehen und fällt beim Klassifizieren fail-loud auf
      MAJOR (er passt in keine "claude-<familie>-<version>"-Form).

Die Klassifikation (MAJOR/MINOR/SUFFIX) ist eine Python-Portierung der
Bash-Funktionen norm_id/fam_major/datum_teil/version_kette aus
tools/claude-hooks/model_change_detector.sh (dort ~Zeilen 61-87) — bewusst
NICHT neu erfunden, weil dieser Klassifizierer nach #2655/#2664 (Versions-
Regex verlor die zweite Stelle, Alias nicht normalisiert) bereits einmal
korrigiert wurde. tools/tests/test_modellwechsel_check.py vergleicht beide
Implementierungen auf denselben Beispielen.

Aufruf:
  python3 tools/modellwechsel_check.py [--kurz] [--behandelt] [--laufend ID]
      [--log PATH] [--handled PATH] [--policies-dir PATH] [--transkript-dir PATH]

Exit 0 = nichts fällig · Exit 1 = fällig (MAJOR oder MINOR, unbehandelt).
stdlib-only.
"""

from __future__ import annotations

import argparse
import json
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

# Letzter Fallback (c) — Session-Alias → vollständige Modell-ID. Altert per
# Konstruktion (neue Aliase kommen nach, alte bleiben); jeder Treffer wird im
# Bericht als Warnung ausgewiesen, ein Treffer im Transkript (b) hat Vorrang.
ALIAS_TABLE = {
    "fable": "claude-fable-5-1",
    "opus": "claude-opus-5",
    "sonnet": "claude-sonnet-5",
    "haiku": "claude-haiku-4-5-20251001",
}

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


def cwd_slug() -> str:
    """Projekt-Ordnername unter ~/.claude/projects/ — cwd mit "/" → "-"."""
    return str(Path.cwd()).replace("/", "-")


def find_latest_transcript_model(transcript_dir: Path) -> str | None:
    """Neuestes *.jsonl im Projektordner; darin die LETZTE assistant-Zeile mit

    `message.model`. None wenn Ordner/Dateien fehlen oder keine Zeile passt.
    """
    if not transcript_dir.is_dir():
        return None
    files = sorted(transcript_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    model: str | None = None
    try:
        with files[0].open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message")
                if isinstance(msg, dict):
                    candidate = msg.get("model")
                    if isinstance(candidate, str) and candidate.startswith("claude-"):
                        model = candidate
    except OSError:
        return None
    return model


@dataclass
class RunningModel:
    model_id: str | None
    quelle: str  # argument | transkript | alias-tabelle | alias-unbekannt | unbekannt
    hinweis: str


def resolve_running_model(
    laufend_arg: str | None, transcript_dir: Path, log_neu: str | None
) -> RunningModel:
    if laufend_arg:
        return RunningModel(laufend_arg, "argument", "")
    transcript_model = find_latest_transcript_model(transcript_dir)
    if transcript_model:
        return RunningModel(transcript_model, "transkript", "")
    if log_neu is None:
        return RunningModel(None, "unbekannt", "kein --laufend, kein Transkript, kein Log")
    mapped = ALIAS_TABLE.get(log_neu)
    if mapped:
        return RunningModel(
            mapped,
            "alias-tabelle",
            f"Alias '{log_neu}' aufgelöst — Tabelle altert, Transkript fehlte",
        )
    return RunningModel(
        log_neu,
        "alias-unbekannt",
        f"'{log_neu}' nicht in Alias-Tabelle und kein Transkript — fail-loud",
    )


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
    parser.add_argument(
        "--transkript-dir",
        type=Path,
        default=None,
        help="Default: ~/.claude/projects/<cwd-slug>/",
    )
    parser.add_argument(
        "--laufend", default=None, help="laufendes Modell explizit angeben (höchste Priorität)"
    )
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
    transcript_dir = args.transkript_dir or (Path.home() / ".claude" / "projects" / cwd_slug())
    log_neu = entry.neu if entry else None
    running_info = resolve_running_model(args.laufend, transcript_dir, log_neu)

    if running_info.model_id is None:
        msg = f"modellwechsel: kein Ereignis ({running_info.hinweis}) — nichts fällig"
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

    running = running_info.model_id
    klasse = "GLEICH" if assessed == running else classify_change(assessed, running)

    if args.behandelt and entry is not None:
        mark_handled(args.handled, entry.raw)

    behandelt = entry is not None and entry.raw in read_handled(args.handled)
    faellig = klasse in ("MAJOR", "MINOR") and not behandelt
    konsequenz = KONSEQUENZ[klasse]
    note = consensus_note(pairs)
    quelle_note = f" ({running_info.hinweis})" if running_info.hinweis else ""

    if args.kurz:
        print(
            f"modellwechsel: {klasse} bewertet={assessed} läuft={running} "
            f"quelle={running_info.quelle} "
            f"behandelt={'ja' if behandelt else 'nein'} "
            f"fällig={'ja' if faellig else 'nein'} — {konsequenz}{quelle_note}"
        )
    else:
        print("Modellwechsel-Check (K2 platform#2690)")
        if entry is not None:
            print(
                f"  letztes Log-Ereignis:  {entry.utc}  {entry.alt} → {entry.neu}"
                f"  (Detektor-Klasse: {entry.klasse_log})"
            )
        else:
            print("  letztes Log-Ereignis:  kein model-changes.log-Eintrag")
        print(f"  bewertet mit:          {assessed}{note}")
        print(f"  läuft mit:             {running}")
        print(f"  Quelle (laufend):      {running_info.quelle}{quelle_note}")
        print(f"  Einstufung:            {klasse}")
        print(f"  behandelt:             {'ja' if behandelt else 'nein'}")
        print(f"  fällig:                {'ja' if faellig else 'nein'}")
        print(f"  Konsequenz:            {konsequenz}")
        print(f"  Runbook:               {RUNBOOK}")

    return 1 if faellig else 0


if __name__ == "__main__":
    raise SystemExit(main())
