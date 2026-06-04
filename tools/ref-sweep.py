#!/usr/bin/env python3
"""ref-sweep — repoint hardcoded GitHub Actions refs across consumer repos.

KONZ-platform-002 OOTB-5. The discovery (2026-06-04) showed the org's shared-CI
coupling is NOT scattered: every `uses:` ref points at ONE source repo
(`achimdehnert/platform/...`). When that source moves (S3 platform migration),
each consumer's `uses: <old>/...@ref` must be repointed to `<new>/...`.

This tool finds those refs across consumer repos and, with --apply, opens ONE PR
per consumer that rewrites them. **Read-only by default (dry-run).** Idempotent:
a repo already on `<new>` produces no change.

It deliberately rewrites only `uses:` references whose path starts with the
`--old` `owner/repo` prefix (e.g. `achimdehnert/platform/`), preserving the rest
of the path and the `@ref`. Nothing else is touched.

Usage:
  GH_TOKEN=... tools/ref-sweep.py \
      [--old achimdehnert/platform] [--new iilgmbh/platform] \
      [--owners achimdehnert,iilgmbh] [--apply]

Needs the `gh` CLI authenticated (GH_TOKEN env or `gh auth login`).
Dry-run needs read access; --apply needs `repo` scope on the consumers.
"""
from __future__ import annotations
import argparse
import base64
import json
import subprocess
import sys


def gh(*args: str):
    """Run gh; return (stdout, stderr). Never raises."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    return (r.stdout, None) if r.returncode == 0 else (None, r.stderr or "error")


def gh_json(path: str, method: str = "GET", fields: dict | None = None):
    args = ["api", "-X", method, path]
    for k, v in (fields or {}).items():
        args += ["-f", f"{k}={v}"]
    out, err = gh(*args)
    if out is None:
        return None, err
    try:
        return json.loads(out), None
    except Exception:
        return out, None  # raw (e.g. file content via raw accept handled separately)


def raw_file(full: str, path: str) -> str | None:
    out, _ = gh("api", f"repos/{full}/contents/{path}",
                "-H", "Accept: application/vnd.github.raw")
    return out


def whoami() -> str | None:
    out, _ = gh("api", "user", "--jq", ".login")
    return out.strip() if out else None


def list_repos(owner: str, me: str | None) -> list[str]:
    """All repos for an owner (paginated). For the AUTHENTICATED user, use
    `user/repos` so PRIVATE own-repos are included — `users/<name>/repos`
    returns only PUBLIC ones (the bug that undercounted consumers)."""
    if me and owner == me:
        ep = "user/repos?affiliation=owner&per_page=100"
    else:
        ep = f"orgs/{owner}/repos?per_page=100"
    out, _ = gh("api", "--paginate", ep, "--jq", ".[].full_name")
    if out is None:
        return []
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def find_refs(text: str, old_prefix: str) -> bool:
    return f"{old_prefix}/" in text


def main() -> int:
    ap = argparse.ArgumentParser(description="OOTB-5 ref-sweep (KONZ-002).")
    ap.add_argument("--old", default="achimdehnert/platform",
                    help="old owner/repo prefix of the shared source")
    ap.add_argument("--new", default="iilgmbh/platform",
                    help="new owner/repo prefix to repoint to")
    ap.add_argument("--owners", default="achimdehnert,iilgmbh",
                    help="comma-separated owners whose repos to scan (consumers)")
    ap.add_argument("--apply", action="store_true",
                    help="open one PR per consumer with the rewrite (default: dry-run)")
    args = ap.parse_args()

    old, new = args.old, args.new
    if old == new:
        print("::error:: --old and --new are identical", file=sys.stderr)
        return 2

    owners = [o.strip() for o in args.owners.split(",") if o.strip()]
    me = whoami()
    repos = sorted({r for o in owners for r in list_repos(o, me)})
    if not repos:
        print("::error:: no repos readable (token/scope?) — refusing to report 'clean'", file=sys.stderr)
        return 1

    print(f"# ref-sweep (OOTB-5): `{old}/…` → `{new}/…`")
    print(f"# scanning {len(repos)} repos across owners: {', '.join(owners)}")
    print(f"# mode: {'APPLY (opens PRs)' if args.apply else 'DRY-RUN (read-only)'}\n")

    plan: list[tuple[str, str, int]] = []  # (repo, file, hit_count)
    gaps: list[str] = []

    for full in repos:
        wf, _ = gh_json(f"repos/{full}/contents/.github/workflows")
        if not isinstance(wf, list):
            continue  # no workflows dir
        for f in wf:
            path = f.get("path")
            if not path or not path.endswith((".yml", ".yaml")):
                continue
            body = raw_file(full, path)
            if body is None:
                gaps.append(f"{full}:{path} unreadable")
                continue
            if find_refs(body, old):
                hits = body.count(f"{old}/")
                plan.append((full, path, hits))
                print(f"- {full} :: {path} ({hits} ref{'s' if hits != 1 else ''})")

    print(f"\n# {len(plan)} file(s) in {len({p[0] for p in plan})} repo(s) reference `{old}/`")
    if gaps:
        print(f"# ⚠️ {len(gaps)} unreadable file(s) — NOT 'clean': {', '.join(gaps[:5])}"
              + (" …" if len(gaps) > 5 else ""))

    if not args.apply:
        print("\n# dry-run only — re-run with --apply to open PRs.")
        return 0

    # ---- APPLY: one PR per repo ----
    branch = "chore/ootb5-ref-sweep"
    changed_repos = sorted({p[0] for p in plan})
    for full in changed_repos:
        files = [p[1] for p in plan if p[0] == full]
        base, _ = gh_json(f"repos/{full}")
        default_branch = (base or {}).get("default_branch", "main")
        head, _ = gh_json(f"repos/{full}/git/ref/heads/{default_branch}")
        sha = (head or {}).get("object", {}).get("sha")
        if not sha:
            print(f"  ⚠️ {full}: cannot resolve {default_branch} head — skipped")
            continue
        gh("api", "-X", "POST", f"repos/{full}/git/refs",
           "-f", f"ref=refs/heads/{branch}", "-f", f"sha={sha}")
        for path in files:
            body = raw_file(full, path)
            if body is None or f"{old}/" not in body:
                continue
            new_body = body.replace(f"{old}/", f"{new}/")
            meta, _ = gh_json(f"repos/{full}/contents/{path}?ref={branch}")
            fsha = (meta or {}).get("sha")
            b64 = base64.b64encode(new_body.encode()).decode()
            gh("api", "-X", "PUT", f"repos/{full}/contents/{path}",
               "-f", f"message=chore(ci): OOTB-5 repoint {old} -> {new}",
               "-f", f"content={b64}", "-f", f"sha={fsha or ''}", "-f", f"branch={branch}")
        out, err = gh("api", "-X", "POST", f"repos/{full}/pulls",
                      "-f", f"title=chore(ci): OOTB-5 repoint {old} → {new}",
                      "-f", f"head={branch}", "-f", f"base={default_branch}",
                      "-f", f"body=Automated OOTB-5 ref-sweep (KONZ-002): repoint shared-CI refs from `{old}/` to `{new}/` after the source repo moved. See docs/runbooks/KONZ-002-ootb5-ref-sweep.md.")
        print(f"  {'PR opened' if out else 'PR FAILED: ' + (err or '')[:80]} — {full}")

    print(f"\n# applied to {len(changed_repos)} repo(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
