#!/usr/bin/env python3
"""Claude Code SessionEnd hook + CLI — Modellmix je Session messen (#2750 K1).

GATE_HEADER (KONZ-038 D8, maschinenlesbar):
  "slug": "fable-session-delegation-unmeasured"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-09-03"
  "evidence": "tools/claude-hooks/tests/test_session_modellmix.py"

Warum: `policies/session-routing.md` schreibt seit 2026-05 Tier-Disziplin fest
(Fable 5 nur mit expliziter Rechtfertigung, Routinearbeit auf T3) — aber bis
hierher lief das ungemessen. Abgerechnet wird je Nachricht nach dem Modell,
das sie tatsächlich ausführt: ein per `Agent`-Tool delegierter Subagent OHNE
eigenes `model:`-Feld erbt das Hauptmodell der Session und läuft damit
unbemerkt auf dem teuren Tier mit, egal was die Session-Policy fürs
Hauptmodell vorschreibt. Dieses Werkzeug liest Haupt- und Subagenten-
Transkript, summiert Tokens/Werkzeugaufrufe je Modell und schreibt (als
SessionEnd-Hook) eine Ledger-Zeile — die Datengrundlage für Kriterium 4 von
platform#2750 (Vorher/Nachher-Vergleich des Modellmix).

Zwei Modi in einer Datei:
  CLI:  session_modellmix.py <session-id-oder-pfad> [--projects-dir DIR]
        [--project SLUG] [--json] [--ledger PFAD]
  Hook: session_modellmix.py --hook   (liest stdin-JSON, schreibt Ledger,
        IMMER Exit 0 — Vertrag wie model_change_detector.sh)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

#: Werkzeuge, die Dateiinhalte verändern — Kennzahl "schreibende Aufrufe".
WRITING_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"}

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_LEDGER = Path.home() / ".claude" / "hooks" / "state" / "modellmix-ledger.tsv"

LEDGER_HEADER = (
    "datum_iso\tsession_id\thauptmodell\tanteil_tokens_nicht_hauptmodell\t"
    "anteil_schreibaufrufe_nicht_hauptmodell\tn_subagenten\tgesamt_tokens\n"
)


def _iter_records(path: Path):
    """Zeilenweise JSON lesen, kaputte Zeilen still überspringen (kein Abbruch)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue


def _tokens(usage: dict) -> int:
    return (
        int(usage.get("input_tokens") or 0)
        + int(usage.get("output_tokens") or 0)
        + int(usage.get("cache_read_input_tokens") or 0)
        + int(usage.get("cache_creation_input_tokens") or 0)
    )


def _accumulate(path: Path, agg: dict, main_counts: dict | None) -> None:
    """Assistenten-Nachrichten aus `path` in `agg` (je Modell) einrechnen.

    `main_counts` (nur beim Haupt-Transkript gesetzt) zählt Assistenten-
    Nachrichten je Modell — daraus folgt das Hauptmodell der Session.
    """
    for rec in _iter_records(path):
        if rec.get("type") != "assistant":
            continue
        message = rec.get("message") or {}
        model = message.get("model")
        if not model:
            continue
        if main_counts is not None:
            main_counts[model] = main_counts.get(model, 0) + 1
        usage = message.get("usage") or {}
        bucket = agg.setdefault(
            model, {"output": 0, "gesamt": 0, "tool_use": 0, "schreibend": 0}
        )
        bucket["output"] += int(usage.get("output_tokens") or 0)
        bucket["gesamt"] += _tokens(usage)
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                bucket["tool_use"] += 1
                if block.get("name") in WRITING_TOOLS:
                    bucket["schreibend"] += 1


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total * 100, 1)


def compute(main_path: Path, session_id: str) -> dict:
    """Modellmix einer Session berechnen (Haupt-Transkript + alle Subagenten)."""
    agg: dict[str, dict] = {}
    main_counts: dict[str, int] = {}
    _accumulate(main_path, agg, main_counts)

    subagents_dir = main_path.parent / main_path.stem / "subagents"
    n_subagenten = 0
    if subagents_dir.is_dir():
        for sub_path in sorted(subagents_dir.glob("agent-*.jsonl")):
            n_subagenten += 1
            _accumulate(sub_path, agg, None)

    hauptmodell = ""
    if main_counts:
        hauptmodell = min(main_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    total_output = sum(b["output"] for b in agg.values())
    total_gesamt = sum(b["gesamt"] for b in agg.values())
    total_schreibend = sum(b["schreibend"] for b in agg.values())

    modelle = {}
    for model in sorted(agg):
        b = agg[model]
        modelle[model] = {
            "output_tokens": b["output"],
            "gesamt_tokens": b["gesamt"],
            "tool_use": b["tool_use"],
            "schreibend": b["schreibend"],
            "anteil_output_pct": _pct(b["output"], total_output),
            "anteil_gesamt_pct": _pct(b["gesamt"], total_gesamt),
            "anteil_schreibend_pct": _pct(b["schreibend"], total_schreibend),
        }

    haupt_bucket = agg.get(hauptmodell, {"gesamt": 0, "schreibend": 0})
    nicht_haupt_gesamt = total_gesamt - haupt_bucket["gesamt"]
    nicht_haupt_schreibend = total_schreibend - haupt_bucket["schreibend"]

    return {
        "session_id": session_id,
        "hauptmodell": hauptmodell,
        "modelle": modelle,
        "anteil_tokens_nicht_hauptmodell": _pct(nicht_haupt_gesamt, total_gesamt),
        "anteil_schreibaufrufe_nicht_hauptmodell": _pct(
            nicht_haupt_schreibend, total_schreibend
        ),
        "n_subagenten": n_subagenten,
        "gesamt_tokens": total_gesamt,
    }


def render_text(result: dict) -> str:
    lines = [f"{'Modell':<28}{'Output%':>9}{'Gesamt%':>9}{'Schreib%':>10}"]
    for model, m in result["modelle"].items():
        lines.append(
            f"{model:<28}{m['anteil_output_pct']:>9.1f}{m['anteil_gesamt_pct']:>9.1f}"
            f"{m['anteil_schreibend_pct']:>10.1f}"
        )
    lines.append("")
    lines.append(
        f"anteil_tokens_nicht_hauptmodell: "
        f"{result['anteil_tokens_nicht_hauptmodell']:.1f}"
    )
    lines.append(
        f"anteil_schreibaufrufe_nicht_hauptmodell: "
        f"{result['anteil_schreibaufrufe_nicht_hauptmodell']:.1f}"
    )
    lines.append(f"n_subagenten: {result['n_subagenten']}")
    return "\n".join(lines)


def ledger_row(result: dict) -> dict:
    return {
        "datum_iso": _dt.datetime.now(tz=_dt.timezone.utc).date().isoformat(),
        "session_id": result["session_id"][:8],
        "hauptmodell": result["hauptmodell"],
        "anteil_tokens_nicht_hauptmodell": result["anteil_tokens_nicht_hauptmodell"],
        "anteil_schreibaufrufe_nicht_hauptmodell": result[
            "anteil_schreibaufrufe_nicht_hauptmodell"
        ],
        "n_subagenten": result["n_subagenten"],
        "gesamt_tokens": result["gesamt_tokens"],
    }


def append_ledger(ledger_path: str | Path, row: dict) -> None:
    """Genau eine TSV-Zeile anhängen; Kopfzeile nur, wenn die Datei neu/leer ist."""
    path = Path(ledger_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as fh:
        if is_new:
            fh.write(LEDGER_HEADER)
        fh.write(
            f"{row['datum_iso']}\t{row['session_id']}\t{row['hauptmodell']}\t"
            f"{row['anteil_tokens_nicht_hauptmodell']}\t"
            f"{row['anteil_schreibaufrufe_nicht_hauptmodell']}\t"
            f"{row['n_subagenten']}\t{row['gesamt_tokens']}\n"
        )


def resolve_transcript(
    session_arg: str, projects_dir: Path, project_slug: str | None
) -> tuple[Path | None, str]:
    """Session-ID ODER direkten Pfad zum Haupt-Transkript auflösen."""
    candidate = Path(session_arg).expanduser()
    if candidate.is_file():
        return candidate, candidate.stem

    session_id = session_arg
    if project_slug:
        c = projects_dir / project_slug / f"{session_id}.jsonl"
        return (c, session_id) if c.is_file() else (None, session_id)

    if projects_dir.is_dir():
        for c in sorted(projects_dir.glob(f"*/{session_id}.jsonl")):
            if c.is_file():
                return c, session_id
    return None, session_id


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "session", nargs="?", help="Session-ID oder Pfad zum Haupt-Transkript"
    )
    p.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p.add_argument("--project", default=None, help="Projekt-Slug (Unterordner)")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    p.add_argument("--ledger", default=None, help="TSV-Pfad; hängt genau eine Zeile an")
    p.add_argument(
        "--hook", action="store_true", help="Hook-Modus: liest stdin-JSON (SessionEnd)"
    )
    return p


def _run_cli(args: argparse.Namespace) -> int:
    if not args.session:
        print("Fehler: Session-ID oder Pfad erforderlich", file=sys.stderr)
        return 2
    projects_dir = Path(args.projects_dir).expanduser()
    main_path, session_id = resolve_transcript(args.session, projects_dir, args.project)
    if main_path is None:
        print(f"Session nicht gefunden: {args.session}", file=sys.stderr)
        return 2

    result = compute(main_path, session_id)
    if args.ledger:
        append_ledger(args.ledger, ledger_row(result))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(render_text(result))
    return 0


def _run_hook() -> int:
    """SessionEnd-Vertrag: IMMER Exit 0, kein/kaum Stdout, auch bei jedem Fehler."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        transcript_path = event.get("transcript_path") or ""
        if not transcript_path:
            return 0
        main_path = Path(transcript_path).expanduser()
        if not main_path.is_file():
            return 0
        session_id = str(event.get("session_id") or main_path.stem)
        result = compute(main_path, session_id)
        ledger_path = os.environ.get("MODELLMIX_LEDGER") or str(DEFAULT_LEDGER)
        append_ledger(ledger_path, ledger_row(result))
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie scheitern
        print(f"session_modellmix: {type(exc).__name__}: {exc}"[:400], file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.hook:
        return _run_hook()
    return _run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
