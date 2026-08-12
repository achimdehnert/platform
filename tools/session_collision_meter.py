#!/usr/bin/env python3
"""Session-Kollisions-Meter — wie oft kollidieren parallele Sessions wirklich?

Misst K5 aus platform#1944 (Zielzustand: parallele Sessions arbeiten
kollisionsfrei). Parallele Sessions sind in diesem Repo der **Normalfall** —
gemessen wird deshalb nicht ihre Zahl, sondern wie oft sie sich in die Quere
kommen.

Definitionen (bewusst schmal, damit die Zahl reproduzierbar bleibt):

  Zwei gemergte PRs **ueberlappen**, wenn ihre offenen Zeitraeume
  [createdAt, mergedAt] sich schneiden — beide waren gleichzeitig offen.

  Ein **Kollisionspaar** ist ein ueberlappendes Paar, das mindestens eine
  geaenderte Datei teilt. Das ist die Risikoflaeche (Kennzahl R).

  Darunter drei Klassen, nach Schwere getrennt:

    N  Nummernkollision — beide PRs legen eine NEUE Datei
       ADR-NNN-*.md bzw. KONZ-platform-NNN-*.md mit **derselben Nummer**, aber
       verschiedenem Dateinamen an. Die harte Klasse: bricht CI, erzwingt
       Umnummerierung. Realfall 2026-08-12: KONZ-043 (PR #1942).
    G  Generat-Kollision — die geteilte Datei ist eine generierte Sammel-/
       Registry-Datei (docs/adr/INDEX.md, index.json, gate-registry.json,
       AGENT_HANDOVER.md ...). Erzeugt Merge-Churn, aber keinen Denkfehler.
    S  Substanz-Kollision — die geteilte Datei ist echter Quell- oder
       Doku-Inhalt. Die Klasse, die einen Menschen zum Zusammenfuehren braucht.

Ein Paar kann in mehreren Klassen zaehlen (verschiedene geteilte Dateien);
R zaehlt jedes Paar genau einmal.

Datenquelle: `gh pr list` fuer die Zeitraeume, lokales git fuer die Dateilisten
(ein API-Call statt einem pro PR). Das Repo muss aktuell gefetcht sein.

Usage:
    python3 tools/session_collision_meter.py                  # 30 Tage, Report
    python3 tools/session_collision_meter.py --days 90
    python3 tools/session_collision_meter.py --json           # maschinenlesbar
    python3 tools/session_collision_meter.py --repo owner/x
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Dateien, deren Inhalt generiert oder als Sammelstelle fortgeschrieben wird.
#: Eine Kollision hier ist Churn, kein inhaltlicher Konflikt.
GENERATED_PATHS = (
    "docs/adr/INDEX.md",
    "docs/adr/index.json",
    "docs/governance/gate-registry.json",
    "AGENT_HANDOVER.md",
    "AGENT_HANDOVER_LOG.md",
    ".windsurf/rules/project-facts.md",
)

#: Neue nummerierte Dokumente, bei denen zwei Sessions dieselbe Nummer ziehen koennen.
NUMBERED_RE = re.compile(
    r"(?:^|/)(?P<kind>ADR|KONZ-platform)-(?P<num>\d{3,4})-(?P<slug>[^/]+)\.md$",
    re.IGNORECASE,
)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_prs(repo: str | None, days: int, limit: int) -> list[dict]:
    """Gemergte PRs im Fenster, mit Zeitraum und Merge-Commit."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "merged",
        "--limit",
        str(limit),
        "--json",
        "number,title,createdAt,mergedAt,mergeCommit,headRefName,author",
    ]
    if repo:
        cmd += ["--repo", repo]
    res = _run(cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        raise SystemExit(f"gh pr list fehlgeschlagen: {res.stderr.strip()[:300]}")

    prs = []
    for pr in json.loads(res.stdout or "[]"):
        merged = _parse_ts(pr.get("mergedAt") or "")
        created = _parse_ts(pr.get("createdAt") or "")
        if not merged or not created or merged < since:
            continue
        pr["_created"] = created
        pr["_merged"] = merged
        prs.append(pr)
    return prs


def files_of(pr: dict) -> tuple[list[str], list[str]]:
    """(alle geaenderten Dateien, neu hinzugefuegte Dateien) via lokales git.

    Erster Elternteil ist bei Merge-Commits `main`, bei Squash-Commits der
    Vorgaenger — `<sha>^1..<sha>` liefert in beiden Faellen den PR-Beitrag.
    """
    commit = (pr.get("mergeCommit") or {}).get("oid")
    if not commit:
        return [], []
    res = _run(["git", "diff", "--name-status", f"{commit}^1", commit], cwd=REPO_ROOT)
    if res.returncode != 0:
        return [], []
    changed, added = [], []
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        changed.append(path)
        if status.startswith("A"):
            added.append(path)
    return changed, added


def numbered_claims(added: list[str]) -> dict[tuple[str, int], str]:
    """(kind, nummer) -> dateiname, nur fuer NEU angelegte nummerierte Dokumente."""
    claims: dict[tuple[str, int], str] = {}
    for path in added:
        m = NUMBERED_RE.search(path)
        if m:
            key = (m.group("kind").upper(), int(m.group("num")))
            claims[key] = Path(path).name
    return claims


def overlaps(a: dict, b: dict) -> bool:
    return a["_created"] <= b["_merged"] and b["_created"] <= a["_merged"]


def classify(shared: set[str]) -> tuple[set[str], set[str]]:
    """Geteilte Dateien in (generiert, substanziell) trennen."""
    generated = {f for f in shared if f in GENERATED_PATHS}
    return generated, shared - generated


def analyse(prs: list[dict]) -> dict:
    for pr in prs:
        pr["_files"], pr["_added"] = files_of(pr)
        pr["_claims"] = numbered_claims(pr["_added"])

    pairs_overlapping = 0
    collisions: list[dict] = []
    hot_files: dict[str, int] = {}

    for a, b in combinations(prs, 2):
        if not overlaps(a, b):
            continue
        pairs_overlapping += 1

        shared = set(a["_files"]) & set(b["_files"])
        number_hits = [
            {
                "kind": kind,
                "number": num,
                "files": sorted({a["_claims"][(kind, num)], b["_claims"][(kind, num)]}),
            }
            for (kind, num) in set(a["_claims"]) & set(b["_claims"])
            if a["_claims"][(kind, num)] != b["_claims"][(kind, num)]
        ]
        if not shared and not number_hits:
            continue

        generated, substantial = classify(shared)
        for f in shared:
            hot_files[f] = hot_files.get(f, 0) + 1

        collisions.append(
            {
                "prs": [a["number"], b["number"]],
                "titles": [a["title"][:70], b["title"][:70]],
                "shared_files": sorted(shared),
                "generated": sorted(generated),
                "substantial": sorted(substantial),
                "number_collisions": number_hits,
            }
        )

    return {
        "prs_merged": len(prs),
        "pairs_overlapping": pairs_overlapping,
        "R_collision_pairs": len(collisions),
        "N_number_collisions": sum(1 for c in collisions if c["number_collisions"]),
        "G_generated_only": sum(
            1 for c in collisions if c["generated"] and not c["substantial"]
        ),
        "S_substantial": sum(1 for c in collisions if c["substantial"]),
        "hot_files": sorted(hot_files.items(), key=lambda kv: -kv[1])[:10],
        "collisions": collisions,
    }


def report(result: dict, days: int) -> str:
    lines = [
        f"# Session-Kollisions-Meter — Fenster {days} Tage",
        "",
        f"Gemergte PRs im Fenster ......... {result['prs_merged']}",
        f"Gleichzeitig offene Paare ....... {result['pairs_overlapping']}",
        "",
        f"R  Kollisionspaare ............... {result['R_collision_pairs']}",
        f"   N  Nummernkollision .......... {result['N_number_collisions']}",
        f"   S  Substanz-Kollision ........ {result['S_substantial']}",
        f"   G  nur Generat-Churn ......... {result['G_generated_only']}",
    ]
    if result["pairs_overlapping"]:
        quote = 100 * result["R_collision_pairs"] / result["pairs_overlapping"]
        lines.append(f"   Kollisionsquote ............. {quote:.1f} % der Paare")
    lines += ["", "Haeufigste geteilte Dateien:"]
    for path, count in result["hot_files"]:
        mark = "GENERAT" if path in GENERATED_PATHS else "Substanz"
        lines.append(f"  {count:4d}x  [{mark:8s}] {path}")
    if result["N_number_collisions"]:
        lines += ["", "Nummernkollisionen (harte Klasse):"]
        for c in result["collisions"]:
            for n in c["number_collisions"]:
                lines.append(
                    f"  {n['kind']}-{n['number']:03d}  PRs {c['prs']}  {n['files']}"
                )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=30, help="Fenstergroesse (Default 30)")
    ap.add_argument("--limit", type=int, default=600, help="max. PRs von gh")
    ap.add_argument("--repo", default=None, help="owner/repo (Default: cwd-Repo)")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    args = ap.parse_args()

    prs = fetch_prs(args.repo, args.days, args.limit)
    result = analyse(prs)
    result["window_days"] = args.days

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(report(result, args.days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
