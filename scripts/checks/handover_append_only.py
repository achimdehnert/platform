#!/usr/bin/env python3
"""handover_append_only.py — erzwingt die append-only-Konvention für AGENT_HANDOVER_LOG.md.

Hintergrund (KONZ-platform-027 Arm A, platform#1319): `.gitattributes` setzt für
AGENT_HANDOVER_LOG.md `merge=union`. Der Union-Treiber nimmt bei konkurrierenden Hunks
beide Seiten auf, statt einen Konflikt zu melden — das funktioniert nur, solange
Sessions ausschließlich ANHÄNGEN. Wird eine bestehende Zeile geändert oder gelöscht,
mischt Union die alte und die neue Fassung ineinander, ohne dass irgendetwas rot wird.

Warum ein Gate und nicht nur eine Konvention: Die Konvention stand am 2026-07-21 im
Skill `session-ende` — und wurde am 2026-07-22 um 05:26 von PR #1317 gebrochen, also
vom selben Ablauf, der sie tragen sollte (eine bestehende Zeile entfernt und verändert
wieder eingefügt). Eine Kanon-Entscheidung ohne durchsetzenden Check driftet; das ist
in diesem Repo mehrfach belegt (feedback_canon_decision_needs_enforcement_gate, #901).

Warum nur der LOG und nicht AGENT_HANDOVER.md: dort ist Umschreiben der Normalfall,
kein Fehler — `session-ende` Phase 0c verlangt ausdrücklich, erledigte Prio-Zeilen zu
entfernen und neu zu nummerieren, und die Archiv-Rotation verschiebt ganze Blöcke.
Gemessen über die letzten 25 Commits an AGENT_HANDOVER.md (2026-07-22): nur EINER
hängte ausschließlich an. Ein Gate auf dieser Datei wäre ein Dauer-Blocker gewesen.
Deshalb trägt AGENT_HANDOVER.md kein `merge=union` und wird hier nicht geprüft.

Der LOG dagegen kennt keine Rotation: er wächst nur. Der Opt-out (`--allow-removals`,
in CI das PR-Label `handover-rewrite`) ist für echte Ausnahmefälle da — etwa das
Entfernen eines versehentlich eingefügten Geheimnisses — und bewusst sichtbar am PR,
nicht still.

Usage:
    scripts/checks/handover_append_only.py --base origin/main [--head HEAD]
                                           [--file AGENT_HANDOVER_LOG.md] [--allow-removals]

Exit 0 = nur Ergänzungen (oder Opt-out gesetzt) · 1 = bestehende Zeilen entfernt/geändert
Exit 2 = Aufruf-/Umgebungsfehler (z. B. Base-Ref nicht vorhanden — flacher Checkout).
Nur stdlib, kein Netz.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")


def git_diff(base: str, head: str, path: str) -> str:
    """Diff des Merge-Base-Vergleichs (Drei-Punkt), damit nur die PR-eigenen
    Änderungen zählen und nicht das, was base seither dazubekommen hat."""
    cmd = ["git", "diff", "--unified=0", f"{base}...{head}", "--", path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff fehlgeschlagen")
    return proc.stdout


def removed_lines(diff: str) -> list[tuple[int, str]]:
    """[(alte Zeilennummer, Inhalt), ...] für jede entfernte Zeile."""
    out: list[tuple[int, str]] = []
    lineno = 0
    for line in diff.splitlines():
        m = HUNK_RE.match(line)
        if m:
            lineno = int(m.group(1))
            continue
        if line.startswith("---"):
            continue
        if line.startswith("-"):
            out.append((lineno, line[1:]))
            lineno += 1
        elif not line.startswith("+") and not line.startswith("\\"):
            lineno += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="Base-Ref, z. B. origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--file", default="AGENT_HANDOVER_LOG.md")
    ap.add_argument(
        "--allow-removals",
        action="store_true",
        help="Opt-out für die Archiv-Rotation (in CI: PR-Label handover-rewrite)",
    )
    a = ap.parse_args(argv)

    try:
        diff = git_diff(a.base, a.head, a.file)
    except RuntimeError as exc:
        print(f"⚠️  {a.file}: Diff nicht ermittelbar — {exc}", file=sys.stderr)
        print("   Base-Ref fehlt vermutlich (flacher Checkout?) — fetch-depth: 0 setzen.")
        return 2

    if not diff.strip():
        print(f"✅ {a.file} im PR unverändert — nichts zu prüfen.")
        return 0

    removed = removed_lines(diff)
    if not removed:
        print(f"✅ {a.file}: nur Ergänzungen ({diff.count(chr(10) + '+')} Zeilen) — append-only gewahrt.")
        return 0

    if a.allow_removals:
        print(f"✅ {a.file}: {len(removed)} entfernte Zeile(n), Opt-out gesetzt (Archiv-Rotation).")
        return 0

    print(f"⛔ {a.file}: {len(removed)} bestehende Zeile(n) entfernt oder geändert —")
    print("   das bricht die append-only-Konvention, auf der merge=union beruht.")
    print("   Union mischt in diesem Fall alte und neue Fassung still ineinander.\n")
    for no, text in removed[:10]:
        print(f"   Zeile {no}: {text[:100]}")
    if len(removed) > 10:
        print(f"   … und {len(removed) - 10} weitere")
    print(
        "\n   Richtig ist: einen NEUEN Eintrag unten anhängen, statt einen bestehenden "
        "umzuschreiben —\n"
        "   auch Korrekturen kommen als neuer Eintrag darunter.\n"
        "   Gehört die Änderung in die Prio-Tabelle? Die lebt in AGENT_HANDOVER.md und "
        "wird hier nicht geprüft.\n"
        "   Echte Ausnahme (z. B. versehentlich eingefügtes Geheimnis entfernen): "
        "PR-Label 'handover-rewrite' setzen."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
