#!/usr/bin/env python3
"""check_noop_changes.py — findet Dateien im Diff ohne semantische Aenderung.

Anlass (platform, 2026-07-21): ein `ruff format tools/` auf das ganze Verzeichnis,
gefolgt von `git add -A tools/`, schleuste 95 fremde Dateien mit 4.912 Zeilen reiner
Reformatierung in einen PR, der 4 Dateien haette aendern sollen. Aufgefallen ist das
erst am Rebase-Konflikt in einer Datei, die mit dem PR-Thema nichts zu tun hatte.

Zwei Detektoren:

  ws_only   Der Datei-Diff verschwindet unter `git diff -w` — reine Whitespace-
            Aenderung (Einrueckung, trailing spaces).

  ast_only  Nur `.py`: der AST von Base- und Head-Version ist identisch. Die Datei
            wurde umformatiert, ohne dass sich das Programm aendert.

**ast_only ist der eigentlich tragende Detektor.** `git diff -w` ignoriert Whitespace
nur INNERHALB von Zeilen; ein Formatter bricht Zeilen um, und das zaehlt weiter als
echte Aenderung. Am realen Anlassfall gemessen (Commit 12f7c3e, 95 py-Dateien):
ws_only fand 0, ast_only fand 93 — die zwei uebrigen waren genau die Dateien, die
in den PR gehoerten. Ein reiner Whitespace-Check haette den Fehler durchgelassen.

Legitime Reformatierungs-PRs gibt es (angekuendigte Formatter-Sweeps). Der Check ist
deshalb SUGGEST/non-gating: er fragt "beabsichtigt?", er verbietet nicht.

Grenze: braucht die Base-Ref lokal. Im flachen CI-Checkout (fetch-depth 1) fehlt sie —
dann meldet der Check das und endet mit 0, statt falsch-gruen zu behaupten, es sei
nichts gefunden worden.

Usage:
    python3 tools/check_noop_changes.py [--range origin/main...HEAD]
                                        [--format human|github] [--gate]
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import subprocess
import sys
from dataclasses import dataclass

DEFAULT_RANGE = "origin/main...HEAD"


@dataclass
class Finding:
    path: str
    kind: str  # ws_only | ast_only


def _git(args: list[str], cwd: pathlib.Path) -> tuple[str, int]:
    r = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return r.stdout.strip(), r.returncode


def _split_range(rng: str) -> tuple[str, str]:
    """'a...b' / 'a..b' / 'a' → (base, head)."""
    for sep in ("...", ".."):
        if sep in rng:
            base, _, head = rng.partition(sep)
            return base or "HEAD", head or "HEAD"
    return rng, "HEAD"


def run(rng: str, repo_root: pathlib.Path) -> tuple[list[Finding], dict[str, int]]:
    stats = {"changed": 0, "py_compared": 0, "unreadable": 0}
    base, head = _split_range(rng)

    for ref in (base, head):
        _, rc = _git(
            ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], repo_root
        )
        if rc:
            raise LookupError(ref)

    all_out, rc = _git(["diff", "--name-only", rng], repo_root)
    if rc:
        raise LookupError(rng)

    changed = [f for f in all_out.splitlines() if f]
    stats["changed"] = len(changed)

    findings: list[Finding] = []
    for f in changed:
        # `git diff --name-only -w` taugt hier NICHT: --name-only vergleicht Blob-
        # Hashes und ignoriert die Whitespace-Optionen, die Datei steht also auch
        # unter -w in der Liste (verifiziert 2026-07-21). Nur die Per-Datei-Abfrage
        # mit --quiet wertet -w wirklich aus.
        _, rc_ws = _git(["diff", "-w", "--quiet", rng, "--", f], repo_root)
        if rc_ws == 0:
            findings.append(Finding(f, "ws_only"))
            continue
        if not f.endswith(".py"):
            continue
        old, rc1 = _git(["show", f"{base}:{f}"], repo_root)
        new, rc2 = _git(["show", f"{head}:{f}"], repo_root)
        if rc1 or rc2 or not old or not new:
            continue  # neu angelegt oder geloescht — es gibt kein Vorher/Nachher
        try:
            same = ast.dump(ast.parse(old)) == ast.dump(ast.parse(new))
        except SyntaxError:
            stats["unreadable"] += 1
            continue
        stats["py_compared"] += 1
        if same:
            findings.append(Finding(f, "ast_only"))
    return findings, stats


def emit(findings: list[Finding], stats: dict[str, int], fmt: str, rng: str) -> None:
    if fmt == "github":
        for f in findings:
            hint = (
                "AST identisch — reine Reformatierung"
                if f.kind == "ast_only"
                else "nur Whitespace geaendert"
            )
            print(
                f"::warning file={f.path},title=noop-change ({f.kind})::"
                f"{hint}. Gehoert die Datei in diesen PR?"
            )
        if findings:
            print(
                f"::warning title=noop-changes summary::{len(findings)} von "
                f"{stats['changed']} geaenderten Dateien ohne semantische Aenderung. "
                f"Bei einem angekuendigten Formatter-Sweep erwartet, sonst ein Zeichen "
                f"fuer versehentlich mitformatierte Dateien."
            )
        else:
            print(
                f"✓ Keine rein formalen Aenderungen ({stats['changed']} Dateien geprueft)."
            )
        return

    for f in findings:
        print(f"{f.path}  [{f.kind}]")
    print(
        f"\nRange            : {rng}\n"
        f"geaenderte Dateien: {stats['changed']}\n"
        f"py AST-verglichen : {stats['py_compared']}\n"
        f"py unparsebar     : {stats['unreadable']}\n"
        f"Findings          : {len(findings)}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--range", dest="rng", default=DEFAULT_RANGE)
    ap.add_argument("--format", choices=["human", "github"], default="human")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Findings (Default ist SUGGEST/immer 0)",
    )
    args = ap.parse_args(argv)

    repo_root = pathlib.Path(args.repo_root).resolve()
    try:
        findings, stats = run(args.rng, repo_root)
    except LookupError as exc:
        # Flacher Checkout: lieber ehrlich melden als falsch-gruen behaupten.
        msg = (
            f"Ref/Range '{exc.args[0]}' nicht aufloesbar — vermutlich flacher Checkout. "
            f"Fuer diesen Check `fetch-depth: 0` setzen bzw. die Base-Ref nachladen."
        )
        if args.format == "github":
            print(f"::warning title=noop-changes uebersprungen::{msg}")
        else:
            print(msg, file=sys.stderr)
        return 0
    emit(findings, stats, args.format, args.rng)
    return 1 if (args.gate and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
