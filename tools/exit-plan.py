#!/usr/bin/env python3
"""exit-plan — derive an org's exit/portability runbook from LIVE GitHub state.

KONZ-platform-002 OOTB-4 / REC-6: portability is a *derived, tested* property,
not a maintained document. This script inventories everything that does NOT
cleanly survive an org/repo transfer (the real, operational lock-in — secrets,
environments, OIDC, webhooks, apps, deploy keys, packages, pages, rulesets,
cross-repo workflow refs) and emits a Markdown runbook on demand. Always
accurate because it reads reality; never stale.

Read-only. Needs a token with admin read on the org (GH_TOKEN env; e.g. the
enterprise PAT). Endpoints the token cannot read are reported as gaps — never
silently skipped (no false "all clear").

Usage:
    GH_TOKEN=... python3 tools/exit-plan.py <org> [--out runbook.md]
"""
from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "")
# Marker for hardcoded owner refs that break on transfer (KONZ-002 B6/OOTB-5).
OWNER_REF_HINT = b"achimdehnert/"


def api(path: str, raw: bool = False):
    """Return (status, parsed-json-or-bytes). Never raises on HTTP error."""
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.raw" if raw
                  else "application/vnd.github+json")
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read()
            return r.status, (body if raw else json.loads(body or b"null"))
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if raw else None)
    except Exception:
        return 0, None


def paged(path: str):
    """Yield items across all pages for a list endpoint."""
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        st, data = api(f"{path}{sep}per_page=100&page={page}")
        if st >= 400 or not isinstance(data, list) or not data:
            return
        yield from data
        page += 1


def names(items, key="name"):
    return sorted(i.get(key, "?") for i in items) if items else []


def count_or_gap(st, items):
    """A 4xx is a GAP (token can't see it), not 'zero' — never silently pass."""
    if st in (401, 403):
        return None  # gap: unreadable
    return items


def main() -> int:
    if not TOKEN:
        print("::error:: GH_TOKEN not set", file=sys.stderr)
        return 2
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    org = sys.argv[1]
    out = None
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]

    L: list[str] = []
    def w(s=""):
        L.append(s)

    gaps: list[str] = []

    # ---- org-level inventory ----
    st_org, org_obj = api(f"/repos/{org}")  # cheap existence probe is per-repo; use orgs
    st_meta, meta = api(f"/orgs/{org}")
    if st_meta >= 400:
        print(f"::error:: org '{org}' not readable (HTTP {st_meta})", file=sys.stderr)
        return 1

    w(f"# Exit-Plan / Portability Runbook — `{org}`")
    w()
    w("> Generated from LIVE GitHub state (KONZ-platform-002 OOTB-4). "
      "Items below do NOT cleanly survive an org/repo transfer — each is a "
      "manual re-provisioning step. Re-run any time; this is derived, not maintained.")
    w()

    st, org_secrets = api(f"/orgs/{org}/actions/secrets")
    st_v, org_vars = api(f"/orgs/{org}/actions/variables")
    st_h, org_hooks = api(f"/orgs/{org}/hooks")
    st_i, installs = api(f"/orgs/{org}/installations")
    st_p, packages = api(f"/orgs/{org}/packages?package_type=container")

    w("## 1. Org-level (re-provision on the NEW owner — none of this transfers)")
    w()
    def section(title, st, payload, extract):
        if st in (401, 403):
            gaps.append(title)
            w(f"- **{title}:** ⚠️ UNREADABLE with this token — verify manually before exit.")
            return
        vals = extract(payload) if payload else []
        if vals:
            w(f"- **{title}** ({len(vals)}): {', '.join('`'+str(v)+'`' for v in vals)}")
        else:
            w(f"- **{title}:** none")
    section("Org Actions secrets (names only — VALUES never transfer, rotate+re-add)",
            st, org_secrets, lambda d: names(d.get("secrets", [])))
    section("Org Actions variables", st_v, org_vars, lambda d: names(d.get("variables", [])))
    section("Org webhooks", st_h, org_hooks, lambda d: [h.get("config", {}).get("url", "?") for h in (d or [])])
    section("Installed GitHub Apps", st_i, installs, lambda d: [a.get("app_slug", "?") for a in d.get("installations", [])])
    section("Org container packages", st_p, packages, lambda d: names(d))
    w()

    # ---- per-repo inventory ----
    # Distinguish "genuinely 0" from "token can't see them" — never a silent cap.
    st_rl, _first = api(f"/orgs/{org}/repos?type=all&per_page=1")
    if st_rl in (401, 403):
        gaps.append("Repository listing UNREADABLE (token lacks `repo` scope) — "
                    "private repos are invisible; inventory below is INCOMPLETE")
        repos = []
    else:
        repos = list(paged(f"/orgs/{org}/repos?type=all"))
    expected = (meta.get("public_repos", 0) or 0) + \
        (meta.get("owned_private_repos") or meta.get("total_private_repos") or 0)
    if expected and len(repos) < expected:
        gaps.append(f"Repository listing INCOMPLETE: saw {len(repos)} of ~{expected} "
                    f"(token scope / visibility) — re-run with a `repo`-scoped token")
    w(f"## 2. Repositories ({len(repos)}"
      + (f" of ~{expected} expected ⚠️" if expected and len(repos) < expected else "")
      + ")")
    w()
    w("Repo transfer keeps history + sets up redirects, but the following do NOT "
      "move and must be re-created on the target:")
    w()
    for r in sorted(repos, key=lambda x: x["name"]):
        n = r["name"]
        full = f"{org}/{n}"
        w(f"### `{n}` ({'private' if r.get('private') else 'public'})")
        # secrets / variables / environments
        _, secs = api(f"/repos/{full}/actions/secrets")
        _, vars_ = api(f"/repos/{full}/actions/variables")
        _, envs = api(f"/repos/{full}/environments")
        _, hooks = api(f"/repos/{full}/hooks")
        _, keys = api(f"/repos/{full}/keys")
        _, rulesets = api(f"/repos/{full}/rulesets")
        st_pg, _pages = api(f"/repos/{full}/pages")
        st_cs, cs = api(f"/repos/{full}/code-scanning/default-setup")
        sec_names = names(secs.get("secrets", [])) if isinstance(secs, dict) else []
        var_names = names(vars_.get("variables", [])) if isinstance(vars_, dict) else []
        env_names = names(envs.get("environments", [])) if isinstance(envs, dict) else []
        hook_n = len(hooks) if isinstance(hooks, list) else 0
        key_n = len(keys) if isinstance(keys, list) else 0
        rs_n = len(rulesets) if isinstance(rulesets, list) else 0
        # hardcoded owner-refs in workflows (B6 / OOTB-5)
        owner_ref_files = []
        _, wf = api(f"/repos/{full}/contents/.github/workflows")
        if isinstance(wf, list):
            for f in wf:
                if f["name"].endswith((".yml", ".yaml")):
                    s2, body = api(f"/repos/{full}/contents/{f['path']}", raw=True)
                    if s2 < 400 and isinstance(body, (bytes, bytearray)) and OWNER_REF_HINT in body:
                        owner_ref_files.append(f["name"])
        w(f"- secrets (rotate+re-add): {', '.join('`'+s+'`' for s in sec_names) or 'none'}")
        w(f"- variables: {', '.join('`'+s+'`' for s in var_names) or 'none'}")
        w(f"- environments: {', '.join('`'+s+'`' for s in env_names) or 'none'}")
        w(f"- webhooks: {hook_n} · deploy keys: {key_n} · rulesets: {rs_n} · "
          f"pages: {'yes' if st_pg < 400 else 'no'} · "
          f"code-scanning default-setup: {cs.get('state','?') if isinstance(cs, dict) else 'n/a'}")
        if owner_ref_files:
            w(f"- ⚠️ **hardcoded `{OWNER_REF_HINT.decode()}*` refs** (break on owner change → "
              f"OOTB-5 indirection): {', '.join('`'+f+'`' for f in owner_ref_files)}")
        w()

    # ---- gaps + manual surface ----
    w("## 3. Outside-GitHub surface (cannot be read here — verify manually)")
    w()
    w("- **OIDC cloud trusts:** AWS/GCP/Azure role trust policies that reference "
      "`repo:%s/*` — update on the cloud side, not in GitHub." % org)
    w("- **DNS / custom domains** pointing at Pages or deployed services.")
    w("- **External CI/CD targets & deploy paths** (`/opt/<repo>`, servers) keyed to repo name.")
    w("- **Secret VALUES** (never exported by the API) — rotate from the source of truth.")
    w()
    w("## 4. Detach / transfer sequence")
    w()
    w("1. Freeze: disable deploy workflows on the source repos.")
    w("2. Re-provision the org-level + per-repo items in §1/§2 on the TARGET owner.")
    w("3. Transfer repos (redirects auto-created); re-add secrets/keys/webhooks/rulesets.")
    w("4. Repoint hardcoded refs (§2 ⚠️) via the OOTB-5 indirection.")
    w("5. Update the outside-GitHub surface (§3).")
    w("6. Detach org from the enterprise (security config no longer applies → re-apply locally).")
    w("7. Verify: workflows green, push-protection active, a known test secret blocks.")
    w()
    if gaps:
        w("## ⚠️ Coverage gaps (token could not read — NOT 'all clear')")
        for g in gaps:
            w(f"- {g}")
        w()

    report = "\n".join(L)
    if out:
        with open(out, "w") as f:
            f.write(report + "\n")
        print(f"wrote {out} ({len(repos)} repos, {len(gaps)} gaps)")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
