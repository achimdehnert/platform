#!/usr/bin/env python3
"""agent_handover_reconcile.py — Nightly-Reconciler AGENT_HANDOVER.md ↔ GitHub-Live-State.

Stufe 1 (dieser Stand): **strikt read-only**. Prüft für jede Referenz in den offenen
Handover-Abschnitten (Parser: handover_refs.py), ob das Objekt auf GitHub noch offen
ist, und schreibt einen Markdown-Report (stdout + optional --summary für
$GITHUB_STEP_SUMMARY). KEIN Kommentar, KEIN Issue, KEIN Schreibrecht — das
Scharfschalten von Schreib-Aktionen ist per Gate `autonomous-no-human-review`
separat gegated (Follow-up-Issue, siehe Workflow-Kommentar).

Motiv: `handover-stale-vor-merge` ist das häufigste gate-pflichtige Muster (12×,
Retro f218be); die Session-Start-Reconciliation (session-start Phase 2.6) findet
stale Prios erst beim nächsten interaktiven Start — nachts findet sie niemand.

Klassifikation je Referenz:
- OK          — Objekt ist offen (Handover-Eintrag konsistent)
- DISKREPANZ  — Objekt ist geschlossen/gemergt, steht aber als offen im Handover
- UNKNOWN     — API nicht abfragbar (Token-Scope cross-repo/privat, gelöscht, Netz)
                → wird gemeldet, NICHT unterschlagen (kein Silent Cap)

Exit-Code: immer 0 im Report-Modus (ein dauerroter Nightly-Check erzeugt
Alarm-Müdigkeit — Befunde gehören in die Summary, nicht in den Job-Status).
Mit --strict: Exit 1 bei ≥1 DISKREPANZ (für den PR-Wiring-Beweis nicht nutzen).

Aufruf:
  agent_handover_reconcile.py AGENT_HANDOVER.md --repo-slug achimdehnert/platform \
      [--summary /pfad/zur/summary.md] [--strict]

Braucht `gh` im PATH mit GH_TOKEN (in Actions: github.token, read-only Scopes).
Tests (Parser): tools/tests/test_handover_refs.py. Verdrahtet in
.github/workflows/handover-reconcile.yml.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handover_refs import Ref, extract_refs  # noqa: E402


def query_state(ref: Ref) -> tuple[str, str]:
    """Liefert (klasse, detail) für eine Referenz via gh api (issues-Endpoint deckt auch PRs)."""
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{ref.owner}/{ref.repo}/issues/{ref.number}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "UNKNOWN", f"gh nicht ausführbar/Timeout: {exc}"
    if proc.returncode != 0:
        return "UNKNOWN", (proc.stderr.strip().split("\n")[0] or "gh api Fehler")[:120]
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "UNKNOWN", "unparsebare API-Antwort"
    state = data.get("state", "?")
    is_pr = "pull_request" in data
    merged = bool((data.get("pull_request") or {}).get("merged_at"))
    kind = "PR" if is_pr else "Issue"
    if state == "open":
        return "OK", f"{kind} offen"
    detail = f"{kind} {'gemergt' if merged else 'geschlossen'}"
    return "DISKREPANZ", detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("handover", type=Path)
    ap.add_argument("--repo-slug", required=True, help="owner/repo für nackte #N-Referenzen")
    ap.add_argument("--summary", type=Path, default=None)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    owner, repo = args.repo_slug.split("/", 1)
    if not args.handover.is_file():
        print(f"::warning::{args.handover} nicht gefunden — nichts zu prüfen (PASS-degradiert)")
        return 0

    refs, skipped_sections = extract_refs(args.handover.read_text(), owner, repo)
    rows: list[tuple[str, Ref, str]] = []
    for ref in refs:
        klass, detail = query_state(ref)
        rows.append((klass, ref, detail))

    disc = [r for r in rows if r[0] == "DISKREPANZ"]
    unknown = [r for r in rows if r[0] == "UNKNOWN"]

    out: list[str] = []
    out.append("## Handover-Reconcile (Stufe 1, read-only)")
    out.append("")
    out.append(
        f"Geprüft: **{len(rows)}** Referenzen aus offenen Abschnitten · "
        f"OK {len(rows) - len(disc) - len(unknown)} · "
        f"DISKREPANZ {len(disc)} · UNKNOWN {len(unknown)}"
    )
    if disc:
        out.append("")
        out.append("### ⚠️ Diskrepanzen (im Handover offen, auf GitHub zu)")
        out.append("")
        out.append("| Referenz | Live-State | Handover-Zeile |")
        out.append("|---|---|---|")
        for _, ref, detail in disc:
            out.append(
                f"| {ref.owner}/{ref.repo}#{ref.number} | {detail} "
                f"| Z.{ref.line_no}: {ref.line[:80].replace('|', '/')} |"
            )
        out.append("")
        out.append(
            "→ Nächste interaktive Session: Handover-Nachzug-PR (Muster: platform#1251). "
            "Ein DISKREPANZ-Treffer kann auch ein False-Positive sein "
            "(Verlaufs-Referenz im offenen Abschnitt) — Triage vor Nachzug."
        )
    if unknown:
        out.append("")
        out.append("### ❔ Nicht prüfbar (kein Silent Skip)")
        out.append("")
        for _, ref, detail in unknown:
            out.append(f"- {ref.owner}/{ref.repo}#{ref.number} — {detail}")
    if skipped_sections:
        out.append("")
        out.append(
            "Nicht gescannte Abschnitte (bewusste Parser-Grenze, s. handover_refs.py): "
            + " · ".join(f"„{s}“" for s in skipped_sections[:8])
        )

    report = "\n".join(out)
    print(report)
    if args.summary:
        args.summary.write_text(report + "\n")
    if args.strict and disc:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
