#!/usr/bin/env python3
"""future_readiness_render.py — result.json (Schema 2.3) → Markdown-Repo-Bericht.

Dritter Baustein neben future_readiness_evidence.py (Paket) und future_readiness_score.py
(Bewertung): rendert das Ergebnis in das Format der Canary-Berichte (Kopfzeile, Findings-
Tabelle, Score-Tabelle), damit die Ablage je Repo reproduzierbar ist und nicht von Hand
geschrieben wird.

    python3 tools/future_readiness_render.py DIR/result.json DIR/report.md

Anlass: Phase C (platform#2737) legte den Renderer zuerst als Datei unter docs/ im
Zielrepo ab — dort verbietet das Doc-Health-Gate Python-Dateien, und ruff fand ihn auch.
Ein Werkzeug gehoert neben seine Geschwister, nicht in den Bericht.
"""

from __future__ import annotations

import json
import sys

SEV_ORDER = {"P1": 0, "P2": 1, "P3": 2}


def _zelle(s: object, n: int = 100) -> str:
    """Eine Tabellenzelle: einzeilig, ohne Pipe, gedeckelt."""
    t = str(s).replace("\n", " ").replace("|", "/")
    return t if len(t) <= n else t[:n]


def render(d: dict) -> str:
    findings = d.get("findings", [])
    sev = {k: sum(1 for f in findings if f.get("severity") == k) for k in SEV_ORDER}
    lines = [
        f"# {d['repo']} — Future-Readiness (v2.3, {d.get('depth', 'T1')}, {d['run_date']}, "
        "deterministischer Bewerter `tools/future_readiness_score.py`)",
        "",
        f"Archetyp **{d['archetype']}** ({d.get('archetype_note', '')}) · "
        f"SHA `{d['analyzed_sha'][:8]}` · **Readiness {d['readiness']}** · "
        f"Coverage {d['evidence_coverage']:.2f} · Klasse `{d['readiness_class']}` · "
        f"Findings {len(findings)} (P1 {sev['P1']}, P2 {sev['P2']}, P3 {sev['P3']})",
        "",
        f"Kriterien: criticality={d['criticality']['value']} ({d['criticality']['source']}) · "
        f"lifecycle={d['lifecycle']} · data_class={d['data_class']}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        lines += ["| Sev | Frage | Typ | Beobachtung | Gate |", "|---|---|---|---|---|"]
        for f in sorted(
            findings,
            key=lambda x: (
                SEV_ORDER.get(x.get("severity"), 3),
                x.get("question_id", ""),
            ),
        ):
            lines.append(
                f"| {f.get('severity', '')} | {f.get('question_id', '')} | "
                f"{f.get('finding_type', '')} | {_zelle(f.get('observation', ''))} | "
                f"{f.get('requires_gate', 'none')} |"
            )
    else:
        lines.append("Keine Findings.")
    lines += ["", "## Scores", "", "| Dim | Score | Coverage |", "|---|---|---|"]
    for dim, sd in d.get("scores", {}).items():
        score = sd.get("score")
        lines.append(
            f"| {dim} | {'–' if score is None else score} | {sd.get('coverage', 0)} |"
        )
    lines.append("")  # Leerzeile nach der Tabelle — wie die abgelegten Berichte
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("Aufruf: future_readiness_render.py result.json out.md", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        d = json.load(fh)
    with open(argv[2], "w", encoding="utf-8") as fh:
        fh.write(render(d))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
