#!/usr/bin/env python3
"""Entscheidet, ob eine Datei-Liste die `paths`-Filter eines Workflows trifft.

Hintergrund (platform#1414): `tools-tests.yml` trug einen `paths`-Filter auf
`pull_request`. Ein *required* Check mit `paths`-Filter laeuft auf PRs, die
keinen der Pfade beruehren, gar nicht — GitHub haelt ihn dort dauerhaft auf
`pending` und blockiert damit ausgerechnet die PRs, die er nicht prueft.

Loesung ist der "Zwilling": der Job laeuft IMMER (kein `paths` auf
`pull_request`), meldet also immer seinen Check-Namen, und entscheidet als
ersten Schritt selbst, ob die teuren Steps noetig sind. Dieses Skript ist
dieser Schritt.

**Die Pfad-Liste bleibt SSoT im Workflow.** Gelesen wird `on.push.paths` —
derselbe Block, der den Push-Trigger filtert. Es gibt also weiterhin genau
eine Liste, keine Komplementaerliste, die auseinanderdriften koennte (genau
der Drift, den eine zweite "paths-ignore"-Variante eingefuehrt haette).

Aufruf:

    python3 tools/ci_relevant_paths.py \\
        --workflow .github/workflows/tools-tests.yml \\
        --changed-file <(git diff --name-only origin/main...HEAD)

    # oder direkt aus stdin:
    git diff --name-only origin/main...HEAD | \\
        python3 tools/ci_relevant_paths.py --workflow <wf> --changed-stdin

Exit-Code ist IMMER 0 — das Ergebnis steht auf stdout als `relevant=true`
bzw. `relevant=false` (GitHub-Output-Syntax). Ein nicht-null Exit waere hier
falsch: "nicht relevant" ist kein Fehler.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path


def load_workflow_paths(workflow_path: Path) -> list[str]:
    """Liest `on.push.paths` aus dem Workflow.

    Bewusst ueber PyYAML statt Handparser: der `on:`-Block traegt Kommentare
    und Verschachtelung; ein Zeilen-Parser waere genau die Sorte stiller
    Fehlerquelle, die den Gate falsch-gruen faerbt.
    """
    import yaml

    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{workflow_path}: kein YAML-Mapping")

    # YAML 1.1: unquoted `on:` wird zu True geparst (Norway-Problem).
    trigger = data.get("on", data.get(True))
    if not isinstance(trigger, dict):
        raise ValueError(f"{workflow_path}: kein `on:`-Mapping gefunden")

    push = trigger.get("push")
    if not isinstance(push, dict) or "paths" not in push:
        raise ValueError(
            f"{workflow_path}: `on.push.paths` fehlt — dieses Skript liest die "
            "Pfad-Liste von dort (SSoT). Ohne sie ist keine Relevanz entscheidbar."
        )

    paths = push["paths"]
    if not isinstance(paths, list) or not paths:
        raise ValueError(f"{workflow_path}: `on.push.paths` ist leer")

    return [str(p) for p in paths]


def matches(changed: str, pattern: str) -> bool:
    """GitHub-`paths`-Semantik fuer die hier verwendeten Muster.

    Abgedeckt ist die Form `<prefix>/**` (alle Muster dieses Repos) sowie
    einfache Globs. `**` matcht in GitHub auch ueber `/` hinweg — fnmatch
    tut das mit `*` ohnehin, deshalb wird `/**` als Praefix-Test behandelt.
    """
    changed = changed.strip()
    if not changed:
        return False
    if pattern.endswith("/**"):
        prefix = pattern[: -len("/**")]
        return changed == prefix or changed.startswith(prefix + "/")
    return fnmatch.fnmatch(changed, pattern)


def is_relevant(changed_files: list[str], patterns: list[str]) -> bool:
    return any(matches(f, p) for f in changed_files for p in patterns)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workflow", required=True, type=Path)
    ap.add_argument(
        "--changed-file",
        type=Path,
        help="Datei mit den geaenderten Pfaden, einer pro Zeile",
    )
    ap.add_argument(
        "--changed-stdin",
        action="store_true",
        help="geaenderte Pfade von stdin lesen",
    )
    ap.add_argument(
        "--github-output",
        type=Path,
        help="zusaetzlich nach $GITHUB_OUTPUT schreiben",
    )
    args = ap.parse_args(argv)

    if args.changed_stdin:
        raw = sys.stdin.read()
    elif args.changed_file:
        raw = args.changed_file.read_text(encoding="utf-8")
    else:
        ap.error("--changed-file oder --changed-stdin noetig")

    changed = [line for line in raw.splitlines() if line.strip()]
    patterns = load_workflow_paths(args.workflow)
    relevant = is_relevant(changed, patterns)

    # Leerer Diff: konservativ relevant. Ein leeres Ergebnis heisst hier meist
    # "der Vergleich lief ins Leere" (fehlender Base-Ref, flacher Klon), nicht
    # "nichts geaendert" — dann lieber einmal zu viel pruefen als still gruen.
    if not changed:
        relevant = True
        print("hinweis: leerer Diff — konservativ als relevant gewertet", file=sys.stderr)

    line = f"relevant={'true' if relevant else 'false'}"
    print(line)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    print(
        f"geprueft: {len(changed)} Datei(en) gegen {len(patterns)} Muster "
        f"aus {args.workflow}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
