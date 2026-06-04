#!/usr/bin/env python3
"""ref-sweep — repoint hardcoded GitHub Actions `uses:` refs across consumer repos.

KONZ-platform-002 OOTB-5 / OOTB-A. The shared-CI coupling points at ONE source
(`achimdehnert/platform`). To move that source — or extract it into a dedicated
`iilgmbh/shared-ci` repo (OOTB-A) — every consumer's `uses: <old>/...@ref` must be
repointed to `<new>/...` (and ideally repinned from `@main` to a tag).

Read-only by default (dry-run). `--apply` opens ONE PR per consumer. Idempotent:
a repo already on `<new>` produces no change; an existing sweep branch/PR is reused
or skipped, not duplicated.

HARDENED (Review 2026-06-04):
- Rewrites only real `uses:` references (YAML key), NEVER comments/banners.
- Word-bounded prefix match (`<old>` only when followed by `/`, `@`, space, quote)
  → no collision with `<old>-tools` etc.
- `--pin <tag>` repins the `@ref` (kill the `@main` supply-chain antipattern).
- `--limit N` = canary (process only the first N affected repos on --apply).
- Branch-/PR-lifecycle idempotent; per-step errors are surfaced, not swallowed.

Usage:
  GH_TOKEN=... tools/ref-sweep.py \
      [--old achimdehnert/platform] [--new iilgmbh/shared-ci] [--pin v1.0.0] \
      [--owners achimdehnert,iilgmbh] [--apply] [--limit N]
Needs `gh` authenticated. Dry-run needs read; --apply needs `repo` on consumers.
"""
from __future__ import annotations
import argparse
import base64
import json
import re
import subprocess
import sys


def gh(*args: str):
    """Run gh; return (stdout, stderr). Never raises."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return (r.stdout, None) if r.returncode == 0 else (None, r.stderr or "error")


def gh_json(path: str):
    out, err = gh("api", path)
    if out is None:
        return None, err
    try:
        return json.loads(out), None
    except Exception:
        return out, None


def raw_file(full: str, path: str, ref: str | None = None) -> str | None:
    p = f"repos/{full}/contents/{path}" + (f"?ref={ref}" if ref else "")
    out, _ = gh("api", p, "-H", "Accept: application/vnd.github.raw")
    return out


def whoami() -> str | None:
    out, _ = gh("api", "user", "--jq", ".login")
    return out.strip() if out else None


def list_repos(owner: str, me: str | None) -> list[str]:
    """For the AUTHENTICATED user use `user/repos` (includes PRIVATE own-repos);
    `users/<name>/repos` returns only public (the bug that undercounted)."""
    ep = ("user/repos?affiliation=owner&per_page=100" if me and owner == me
          else f"orgs/{owner}/repos?per_page=100")
    out, _ = gh("api", "--paginate", ep, "--jq", ".[].full_name")
    return [ln.strip() for ln in out.splitlines() if ln.strip()] if out else []


def rewrite_uses(text: str, old: str, new: str, pin: str | None):
    """Return (new_text, count). Rewrites ONLY real `uses:` lines whose value is
    `<old>` (word-bounded); skips comment lines/banners. Optionally repins @ref."""
    out_lines, count = [], 0
    # value must be <old> followed by a boundary (path '/', '@ref', whitespace, quote, EOL)
    pat = re.compile(r'(uses:\s*["\']?)(' + re.escape(old) + r')(?=[/@\s"\']|$)(\S*)')
    for line in text.split("\n"):
        if line.lstrip().startswith("#") or "uses:" not in line:
            out_lines.append(line)
            continue
        m = pat.search(line)
        if not m:
            out_lines.append(line)
            continue
        rest = m.group(3)  # e.g. "/.github/workflows/x.yml@main" or "@main" or ""
        if pin:
            rest = re.sub(r'@[^\s"\']+$', "", rest) + f"@{pin}"
        out_lines.append(line.replace(m.group(0), m.group(1) + new + rest, 1))
        count += 1
    return "\n".join(out_lines), count


def main() -> int:
    ap = argparse.ArgumentParser(description="OOTB-5/A ref-sweep (KONZ-002).")
    ap.add_argument("--old", default="achimdehnert/platform")
    ap.add_argument("--new", default="iilgmbh/shared-ci")
    ap.add_argument("--pin", default=None, help="repin @ref to this tag (e.g. v1.0.0); kills @main")
    ap.add_argument("--owners", default="achimdehnert,iilgmbh")
    ap.add_argument("--apply", action="store_true", help="open one PR per consumer (default: dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="canary: only first N affected repos on --apply")
    args = ap.parse_args()

    old, new, pin = args.old, args.new, args.pin
    if old == new and not pin:
        print("::error:: --old == --new and no --pin → nothing to do", file=sys.stderr)
        return 2

    me = whoami()
    repos = sorted({r for o in args.owners.split(",") if o.strip()
                    for r in list_repos(o.strip(), me)})
    if not repos:
        print("::error:: no repos readable (token/scope?) — refusing to report 'clean'", file=sys.stderr)
        return 1

    print(f"# ref-sweep: `{old}/…` → `{new}/…`" + (f" @{pin}" if pin else ""))
    print(f"# {len(repos)} repos · owners {args.owners} · "
          f"{'APPLY' + (f' (canary limit {args.limit})' if args.limit else '') if args.apply else 'DRY-RUN'}\n")

    plan, gaps = [], []
    for full in repos:
        wf, _ = gh_json(f"repos/{full}/contents/.github/workflows")
        if not isinstance(wf, list):
            continue
        repo_hits = 0
        for f in wf:
            path = f.get("path", "")
            if not path.endswith((".yml", ".yaml")):
                continue
            body = raw_file(full, path)
            if body is None:
                gaps.append(f"{full}:{path}")
                continue
            _, hits = rewrite_uses(body, old, new, pin)
            if hits:
                repo_hits += hits
                print(f"- {full} :: {path.split('/')[-1]} ({hits})")
        if repo_hits:
            plan.append(full)

    print(f"\n# {len(plan)} repo(s) to sweep")
    if gaps:
        print(f"# ⚠️ {len(gaps)} unreadable file(s) — NOT 'clean': {', '.join(gaps[:5])}")
    if not args.apply:
        print("\n# dry-run only — re-run with --apply to open PRs.")
        return 0

    targets = plan[:args.limit] if args.limit else plan
    if args.limit:
        print(f"\n# canary: applying to {len(targets)} of {len(plan)} (--limit {args.limit})")
    branch = "chore/ref-sweep-ootb"
    for full in targets:
        # idempotency: skip if a PR for this branch already exists
        prs, _ = gh_json(f"repos/{full}/pulls?head={full.split('/')[0]}:{branch}&state=open")
        if isinstance(prs, list) and prs:
            print(f"  skip (PR exists): {full}")
            continue
        base, _ = gh_json(f"repos/{full}")
        db = (base or {}).get("default_branch", "main")
        head, _ = gh_json(f"repos/{full}/git/ref/heads/{db}")
        sha = (head or {}).get("object", {}).get("sha")
        if not sha:
            print(f"  ⚠️ {full}: no head sha — skipped")
            continue
        existing, _ = gh_json(f"repos/{full}/git/ref/heads/{branch}")
        if not (isinstance(existing, dict) and existing.get("ref")):
            _, err = gh("api", "-X", "POST", f"repos/{full}/git/refs",
                        "-f", f"ref=refs/heads/{branch}", "-f", f"sha={sha}")
            if err:
                print(f"  ⚠️ {full}: branch create failed ({err[:60]}) — skipped")
                continue
        wf, _ = gh_json(f"repos/{full}/contents/.github/workflows")
        changed = 0
        for f in (wf if isinstance(wf, list) else []):
            path = f.get("path", "")
            if not path.endswith((".yml", ".yaml")):
                continue
            body = raw_file(full, path, ref=branch)
            if body is None:
                continue
            new_body, hits = rewrite_uses(body, old, new, pin)
            if not hits:
                continue
            meta, _ = gh_json(f"repos/{full}/contents/{path}?ref={branch}")
            fsha = (meta or {}).get("sha", "")
            b64 = base64.b64encode(new_body.encode()).decode()
            _, err = gh("api", "-X", "PUT", f"repos/{full}/contents/{path}",
                        "-f", f"message=chore(ci): ref-sweep {old} → {new}" + (f" @{pin}" if pin else ""),
                        "-f", f"content={b64}", "-f", f"sha={fsha}", "-f", f"branch={branch}")
            if err:
                print(f"  ⚠️ {full}:{path} update failed ({err[:60]})")
            else:
                changed += 1
        if not changed:
            print(f"  ⚠️ {full}: branch created but 0 files changed — check manually")
            continue
        out, err = gh("api", "-X", "POST", f"repos/{full}/pulls",
                      "-f", f"title=chore(ci): ref-sweep {old} → {new}",
                      "-f", f"head={branch}", "-f", f"base={db}",
                      "-f", "body=Automated OOTB-A ref-sweep (KONZ-002): repoint shared-CI `uses:` refs."
                            " See docs/runbooks/KONZ-002-ootb5-ref-sweep.md.")
        print(f"  {'PR opened (' + str(changed) + ' files)' if out else 'PR FAILED: ' + (err or '')[:60]} — {full}")

    print(f"\n# applied to {len(targets)} repo(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
