#!/usr/bin/env python3
"""worktree-reaper — deterministischer GC für git-Worktrees (ADR-233).

Entfernt Worktrees, deren Branch nachweislich **gemergt** ist (squash-aware via
`gh pr ... --state merged`) oder die **>N Tage unberührt** sind. Konservativ by
default:

- **dry-run** ist Standard; `--apply` führt Entfernungen erst aus.
- **Dirty-Guard:** ein Worktree mit uncommitted changes wird NIE angefasst.
- **Unsicherheit = KEEP:** wenn der Merge-Status nicht zweifelsfrei bestimmbar ist
  (kein `gh`, privater Fork, API-Fehler), wird der Worktree behalten, nie gereapt.
- **Stale-but-unmerged** wird nur mit `--include-stale` entfernt (sonst nur gemeldet).
  Stale-Entscheidung läuft primär über die **Lease** (repo-session.sh, `expires_at`,
  ADR-233 §2.4); nur ohne/unparsebare Lease fällt sie auf Commit-mtime zurück.
- Primärer Worktree und der aktuelle Worktree sind immer ausgenommen.
- Jede Entfernung wird in ein **Restore-Manifest** (JSONL) geschrieben:
  `git worktree add <path> <branch>` stellt sie wieder her.

Bezug: ADR-233, feedback_branch_cleanup_squash_worktree (squash-aware Wahrheit,
Worktree-Branches ausschließen, Restore-Manifest schreiben).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen. Der Reaper ist das Gate gegen
# das Retro-Muster `worktree-midsession-accumulation` (Worktrees sammeln sich an,
# bis der naechste Merge kollidiert): aufgerufen via `repo-session.sh reap` und
# session-start Phase 0.4.5. Bestand seit cf9ccb48, registriert erst 2026-08-12
# (platform#1650 Nachmessung: ein unregistriertes Gate drillt niemand).
GATE_HEADER = {
    "slug": "worktree-midsession-accumulation",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-08-12",
    "evidence": "tools/tests/test_worktree_reaper.py",
}

PROTECTED_BRANCHES = {"main", "master"}
LEASE_DIR = (
    Path(os.environ.get("REPO_SESSION_DIR", str(Path.home() / ".repo-session")))
    / "leases"
)


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()


def list_worktrees() -> list[dict]:
    """Parse `git worktree list --porcelain` → [{path, head, branch, bare, detached}]."""
    rc, out = _run(["git", "worktree", "list", "--porcelain"])
    if rc != 0:
        sys.exit("FEHLER: kein git-Repo / `git worktree list` fehlgeschlagen.")
    trees, cur = [], {}
    for line in out.splitlines():
        if not line:
            if cur:
                trees.append(cur)
                cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = {
                "path": val,
                "branch": None,
                "head": None,
                "detached": False,
                "bare": False,
            }
        elif key == "HEAD":
            cur["head"] = val
        elif key == "branch":
            cur["branch"] = val.removeprefix("refs/heads/")
        elif key == "detached":
            cur["detached"] = True
        elif key == "bare":
            cur["bare"] = True
    if cur:
        trees.append(cur)
    return trees


def is_dirty(path: str) -> bool:
    rc, out = _run(["git", "status", "--porcelain"], cwd=path)
    return rc != 0 or bool(out)  # rc!=0 (z.B. Pfad weg) → konservativ als dirty werten


def commit_age_days(path: str) -> float | None:
    rc, out = _run(["git", "log", "-1", "--format=%ct"], cwd=path)
    if rc != 0 or not out.isdigit():
        return None
    age = datetime.now(timezone.utc).timestamp() - int(out)
    return age / 86400.0


def lease_for(path: str) -> dict | None:
    """Lease (repo-session.sh) für einen Worktree-Pfad finden, falls vorhanden."""
    if not LEASE_DIR.is_dir():
        return None
    for f in LEASE_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("worktree") == path:
            return d
    return None


def close_lease_for(path: str) -> bool:
    """Lease eines entfernten Worktrees auf .closed setzen (Lease- an Worktree-Lifecycle koppeln).
    Verhindert verwaiste offene Leases (Lease-Friedhof, Retro 2026-06-24)."""
    if not LEASE_DIR.is_dir():
        return False
    for f in LEASE_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("worktree") == path:
            f.rename(f.with_suffix(".json.closed"))
            return True
    return False


def close_orphan_leases() -> int:
    """Offene Leases schließen, deren Worktree-Verzeichnis nicht mehr existiert
    (Backlog-Cleanup + Selbstheilung bei manuell entfernten Worktrees)."""
    if not LEASE_DIR.is_dir():
        return 0
    closed = 0
    for f in LEASE_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        wt = d.get("worktree")
        if wt and not Path(wt).is_dir():
            f.rename(f.with_suffix(".json.closed"))
            closed += 1
    return closed


def lease_expired(lease: dict) -> bool | None:
    """True/False ob expires_at überschritten; None wenn nicht parsebar."""
    exp = lease.get("expires_at")
    if not exp:
        return None
    try:
        ts = datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
    return datetime.now(timezone.utc) > ts


def pr_state(branch: str, repo: str | None) -> str:
    """'merged' | 'open' | 'none' | 'unknown' (gh fehlt/Fehler → unknown = KEEP)."""
    if not branch:
        return "unknown"
    # --state all: sonst defaultet gh auf 'open' und gemergte PRs bleiben unsichtbar.
    base = [
        "gh",
        "pr",
        "list",
        "--head",
        branch,
        "--state",
        "all",
        "--json",
        "number,state",
        "--limit",
        "10",
    ]
    if repo:
        base += ["--repo", repo]
    rc, out = _run(base)
    if rc != 0:
        return "unknown"
    try:
        prs = json.loads(out or "[]")
    except json.JSONDecodeError:
        return "unknown"
    states = {p.get("state", "").upper() for p in prs}
    if "MERGED" in states:
        return "merged"
    if "OPEN" in states:
        return "open"
    return "none"


def fremde_aktivitaet(path: str) -> str:
    """Anzeichen, dass in diesem Baum noch jemand arbeitet — "" = keins.

    Der `--sitzungsende`-Bypass verzichtet auf die Karenz, weil die besitzende
    Sitzung selbst sagt, dass sie fertig ist. Ein Baum kann aber GETEILT sein
    (feedback_shared_worktree_multisession_git_collision): dann endet Sitzung A,
    waehrend Sitzung B im selben Verzeichnis weiterarbeitet. Der Dirty-Guard
    faengt das nur, solange B uncommitted Aenderungen hat.

    Zwei billige Indikatoren, beide ohne Netz und ohne Raten:
      - `.git/index.lock` — eine git-Operation laeuft in genau diesem Moment.
      - mehr als ein OFFENES Lease auf denselben Pfad — zwei Sitzungen haben
        sich denselben Baum genommen.
    """
    # NICHT `<path>/.git/index.lock`: in einem Linked-Worktree ist `.git` eine
    # DATEI (`gitdir: …`), und genau Linked-Worktrees sind hier der Normalfall.
    # Der Lock liegt im echten gitdir, das git selbst nennt. Der erste Versuch
    # dieser Funktion griff auf den Verzeichnispfad — der eigene Drill hat es
    # gefangen, bevor der Guard wirkungslos in Betrieb ging.
    rc, gitdir = _run(["git", "-C", path, "rev-parse", "--absolute-git-dir"])
    if rc == 0 and gitdir and (Path(gitdir) / "index.lock").exists():
        return "git-Operation laeuft (index.lock)"
    if LEASE_DIR.is_dir():
        treffer = 0
        for f in LEASE_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if d.get("worktree") == path:
                treffer += 1
        if treffer > 1:
            return f"{treffer} offene Leases auf denselben Baum"
    return ""


def _gleicher_pfad(pfad: str, kandidaten: tuple[str, ...]) -> bool:
    """Kanonischer Vergleich — ein Lease-/Hook-Pfad kann `/./` oder Symlinks tragen."""
    if not kandidaten:
        return False
    try:
        ziel = Path(pfad).resolve()
    except OSError:
        return False
    for k in kandidaten:
        try:
            if Path(k).resolve() == ziel:
                return True
        except OSError:
            continue
    return False


def classify(
    wt: dict,
    primary: str,
    current: str,
    repo: str | None,
    stale_days: int,
    karenz_stunden: float = 12.0,
    sitzungsende: tuple[str, ...] = (),
) -> tuple[str, str]:
    """→ (verdict, reason). verdict ∈ {KEEP, REAP_MERGED, REAP_STALE, SKIP}."""
    path, branch = wt["path"], wt["branch"]
    if wt.get("bare") or path == primary:
        return "SKIP", "primärer/barer Worktree"
    if Path(path) == Path(current):
        return "SKIP", "aktueller Worktree"
    if wt.get("detached") or not branch:
        return "SKIP", "detached HEAD — Branch unbestimmbar"
    if branch in PROTECTED_BRANCHES:
        return "SKIP", f"geschützter Branch ({branch})"
    if is_dirty(path):
        return "SKIP", "DIRTY — uncommitted changes (Guard)"
    # Ein AKTIVES Lease schlaegt jeden Merge-Zustand (#1866). Bis 2026-08-10 stand
    # die pr_state-Pruefung davor, und ein gemergter PR fuehrte sofort zu
    # REAP_MERGED — das Lease wurde nie gelesen. Genau das ist der Normalfall am
    # Ende einer Sitzung: PR gemergt, im selben Baum wird weitergearbeitet
    # (Folge-Commits, session-ende, Handover). Gemessen am 2026-08-10 waren ALLE
    # drei REAP_MERGED-Kandidaten der Flotte Worktrees einer laufenden Sitzung mit
    # Lease bis 2026-08-17. Substanz haette das nicht gekostet (dirty ist SKIP,
    # Branches gepusht, Restore-Manifest), aber es zieht einer lebenden Sitzung den
    # Boden weg — und ohne diese Reihenfolge waere ein Auto-Reap nicht
    # verantwortbar. Das Lease ist die Aussage "eine Sitzung besitzt diesen Baum";
    # sie gilt, bis sie ablaeuft.
    lease = lease_for(path)
    if lease is not None and lease_expired(lease) is False:
        # Karenz statt Kadenz (Retro 8d6869, 2026-08-20): die Regel oben schuetzt die
        # Weiterarbeit unmittelbar NACH dem Merge — sie soll nicht bedeuten, dass ein
        # fertiger Baum sieben Tage stehenbleibt. `gate_wirkung.py` hat das Gate genau
        # deshalb als rueckfaellig gemessen: nach dem Merge passiert nichts mehr, und
        # bis zum Lease-Ablauf raeumt niemand. Ist der Baum sauber, sein PR gemergt und
        # seit `karenz_stunden` kein Commit mehr gefallen, ist die Sitzung erkennbar
        # vorbei — dann greift der Reaper trotz aktivem Lease. Eine lebende Sitzung
        # committet innerhalb dieser Frist und bleibt damit unangetastet.
        # Die Sitzung, die diesen Baum besitzt, sagt selbst, dass sie fertig ist:
        # dann ist die Karenz gegenstandslos. Sie schuetzt die Weiterarbeit einer
        # LEBENDEN Sitzung — und genau die gibt es hier nicht mehr.
        #
        # Ohne diese Ausnahme konnte die Karenz den Fall, fuer den sie gebaut wurde,
        # strukturell nie erreichen: der SessionEnd-Hook `reap_worktrees.sh` laeuft
        # bei JEDEM Sitzungsende, aber 12 Stunden sind laenger als jede Sitzung —
        # der eigene, frisch gemergte Baum war beim Aufraeumen immer zu jung.
        # Gemessen als zwei Rueckfaelle des Gates `worktree-midsession-accumulation`
        # NACH dem Karenz-Umbau vom 2026-08-20 (chat-hub 2026-08-21: sechs Baeume;
        # ausschreibungs-hub 2026-08-23: drei Baeume nach drei Merges).
        eigener = _gleicher_pfad(path, sitzungsende)
        alter = commit_age_days(path)
        if eigener and pr_state(branch, repo) == "merged":
            # Der Verzicht auf die Karenz gilt nur, wenn nichts auf eine zweite,
            # lebende Sitzung im selben Baum hindeutet (Retro a84f71 Befund 2).
            # Findet sich ein Anzeichen, faellt der Fall auf die normale Karenz
            # zurueck — nicht auf "trotzdem entfernen".
            fremd = fremde_aktivitaet(path)
            if fremd:
                return "KEEP", f"Baum der endenden Sitzung, aber {fremd} — Karenz gilt"
            return (
                "REAP_MERGED",
                "PR gemergt, Baum der endenden Sitzung (Karenz entfaellt)",
            )
        if (
            alter is not None
            and alter * 24 >= karenz_stunden
            and pr_state(branch, repo) == "merged"
        ):
            return (
                "REAP_MERGED",
                f"PR gemergt, Lease aktiv, aber seit {alter * 24:.0f}h unberuehrt "
                f"(Karenz {karenz_stunden:.0f}h)",
            )
        return "KEEP", f"Lease aktiv bis {lease.get('expires_at')}"

    state = pr_state(branch, repo)
    if state == "merged":
        return "REAP_MERGED", "PR gemergt (squash-aware), kein aktives Lease"
    if state == "unknown":
        return "KEEP", "Merge-Status unbestimmbar → konservativ behalten"
    if state == "open":
        return "KEEP", "offener PR"
    # Stale-Entscheidung: Lease primär (ADR-233 §2.4), mtime nur als Fallback.
    if lease is not None:
        exp = lease_expired(lease)
        if exp is True:
            return (
                "REAP_STALE",
                f"Lease abgelaufen ({lease.get('expires_at')}), kein PR",
            )
        # exp is None → expires_at unparsebar, falle auf mtime zurück
    age = commit_age_days(path)
    if age is not None and age > stale_days:
        return "REAP_STALE", f"unberührt seit {age:.0f}d, kein PR (kein Lease)"
    return "KEEP", "aktiv / kein Reap-Kriterium"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministischer git-Worktree-GC (ADR-233)."
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Entfernungen ausführen (Standard: dry-run).",
    )
    ap.add_argument(
        "--include-stale",
        action="store_true",
        help="Auch stale-but-unmerged entfernen.",
    )
    ap.add_argument(
        "--stale-days",
        type=int,
        default=14,
        help="Stale-Schwelle in Tagen (default 14).",
    )
    ap.add_argument(
        "--repo", default=None, help="OWNER/REPO für gh (default: aus Remote)."
    )
    ap.add_argument(
        "--karenz-stunden",
        type=float,
        default=12.0,
        dest="karenz_stunden",
        help="Stunden ohne Commit, nach denen ein gemergter Baum trotz aktivem "
        "Lease abgeraeumt wird (Default 12).",
    )
    ap.add_argument(
        "--sitzungsende",
        action="append",
        default=[],
        metavar="PFAD",
        help="Worktree(s) der gerade endenden Sitzung: fuer sie entfaellt die Karenz, "
        "alle anderen Regeln (clean, PR gemergt, nicht primaer) gelten unveraendert. "
        "Mehrfach angebbar.",
    )
    ap.add_argument("--manifest", default=None, help="Restore-Manifest-Pfad (JSONL).")
    args = ap.parse_args()

    trees = list_worktrees()
    primary = trees[0]["path"] if trees else ""
    current = _run(["git", "rev-parse", "--show-toplevel"])[1] or str(Path.cwd())

    plan, reap = [], []
    for wt in trees:
        verdict, reason = classify(
            wt,
            primary,
            current,
            args.repo,
            args.stale_days,
            args.karenz_stunden,
            tuple(args.sitzungsende),
        )
        plan.append((verdict, wt, reason))
        if verdict == "REAP_MERGED" or (verdict == "REAP_STALE" and args.include_stale):
            reap.append((wt, reason))

    print(f"{'VERDIKT':<13} {'BRANCH':<42} GRUND")
    print("-" * 90)
    for verdict, wt, reason in sorted(plan, key=lambda x: x[0]):
        print(f"{verdict:<13} {(wt['branch'] or '(detached)'):<42} {reason}")
    print(f"\n{len(reap)} Worktree(s) zum Entfernen, {len(plan) - len(reap)} behalten.")

    if not reap:
        return 0
    if not args.apply:
        print("\n[dry-run] Nichts entfernt. Mit --apply ausführen.")
        return 0

    if args.manifest:
        mf = Path(args.manifest)
    else:
        # Default ins .git/ (git-common-dir) schreiben — git trackt .git/-Inhalt
        # nie, also dirtyt das Manifest kein Repo (sonst false-positive bei jedem
        # session-ende-Pflicht-Reaper). Fallback cwd, falls kein git-Kontext.
        rc, gitdir = _run(["git", "rev-parse", "--git-common-dir"])
        base = Path(gitdir.strip()) if rc == 0 and gitdir.strip() else Path.cwd()
        mf = base / "worktree-reaper-manifest.jsonl"
    removed = 0
    with mf.open("a", encoding="utf-8") as f:
        for wt, reason in reap:
            rec = {
                "removed_at": datetime.now(timezone.utc).isoformat(),
                "path": wt["path"],
                "branch": wt["branch"],
                "head": wt["head"],
                "reason": reason,
            }
            rc, out = _run(["git", "worktree", "remove", wt["path"]])
            if rc == 0:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                removed += 1
                lease_note = (
                    " + Lease geschlossen" if close_lease_for(wt["path"]) else ""
                )
                print(
                    f"entfernt: {wt['branch']}{lease_note}  (restore: git worktree add {wt['path']} {wt['branch']})"
                )
            else:
                print(f"FEHLER beim Entfernen {wt['path']}: {out}", file=sys.stderr)
    orphaned = close_orphan_leases()
    extra = f" · {orphaned} verwaiste Lease(s) geschlossen" if orphaned else ""
    print(f"\n{removed} entfernt · Restore-Manifest: {mf}{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
