#!/usr/bin/env python3
"""windsurf-subset.py — generiert das Windsurf-ADR-Review-Subset (platform:ADR-230, PROTOTYP).

Auswahl primär über **Frontmatter-Tag** `tool_targets: [windsurf-review]` (REC-10);
solange noch keine Workflows getaggt sind, **Fallback** auf eine kuratierte Default-Liste
(adr*, *review, challenger, curator) — mit klarem Log, dass Tags nachzuziehen sind.

Erzeugt die Subset-Kopien (MANAGED-Footer + manifest) in ein **Staging-Dir**.
SICHERHEIT: `--target` Pflicht; schreibt NIE in `~/.codeium/windsurf/windsurf/workflows/`
ohne `--allow-live` (im Prototyp nicht genutzt).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

GENERATOR_VERSION = "0.1.0"
MARK = "MANAGED-BY: platform/tools/cc-skill-dist (windsurf-subset)"
DEFAULT_SUBSET = ["adr.md", "adr-review.md", "adr-challenger.md", "adr-curator.md",
                  "adr-health.md", "adr-handoff-extern.md", "agent-review.md",
                  "pr-review.md", "workflow-review.md", "review.md"]
WINDSURF_LIVE = os.path.expanduser("~/.codeium/windsurf/windsurf/workflows")

def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} fehlgeschlagen: {r.stderr[:200]}")
    return r.stdout

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""

def has_windsurf_tag(text):
    fm = frontmatter(text)
    m = re.search(r"^tool_targets:\s*(.+)$", fm, re.M)
    return bool(m and "windsurf-review" in m.group(1))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--target", required=True)
    ap.add_argument("--allow-live", action="store_true")
    args = ap.parse_args()

    target = os.path.abspath(os.path.expanduser(args.target))
    if os.path.abspath(target) == os.path.abspath(WINDSURF_LIVE) and not args.allow_live:
        sys.exit("ABBRUCH: Ziel ist die Live-Windsurf-Location — Prototyp schreibt nicht live (--allow-live nötig).")

    git(["fetch", "origin", "main", "-q"], args.platform)
    commit = git(["rev-parse", args.ref], args.platform).strip()
    listing = git(["ls-tree", "-r", args.ref, ".windsurf/workflows/"], args.platform)
    blobs = {}
    for line in listing.splitlines():
        p = line.split()
        if len(p) >= 4 and p[1] == "blob" and p[-1].endswith(".md"):
            blobs[os.path.basename(p[-1])] = (p[2], p[-1])
    contents = {n: git(["cat-file", "blob", sha], args.platform) for n, (sha, _) in blobs.items()}

    tagged = sorted(n for n, txt in contents.items() if has_windsurf_tag(txt))
    if tagged:
        selected, mode = tagged, "Frontmatter-Tag (tool_targets: windsurf-review)"
    else:
        selected = sorted(n for n in DEFAULT_SUBSET if n in blobs)
        mode = "FALLBACK kuratierte Liste — KEINE tool_targets-Tags vorhanden (Tags via Folge-PR nachziehen)"

    staging = target + ".tmp"
    if os.path.exists(staging): shutil.rmtree(staging)
    os.makedirs(staging)
    manifest = {"source_repo": "achimdehnert/platform", "source_commit": commit,
                "generator_version": GENERATOR_VERSION, "selection_mode": mode,
                "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "target_type": "windsurf-subset", "skill_count": len(selected), "files": []}
    for name in selected:
        src = contents[name]; _, path = blobs[name]
        chash = hashlib.sha256(src.encode("utf-8")).hexdigest()
        footer = (f"\n\n<!-- {MARK} · windsurf-review-subset · source={path} · "
                  f"source_commit={commit[:12]} · content_hash=sha256:{chash[:16]} · do_not_edit -->\n")
        open(os.path.join(staging, name), "w", encoding="utf-8").write(src.rstrip("\n") + footer)
        manifest["files"].append({"name": name, "source_path": path, "content_hash": "sha256:" + chash})
    json.dump(manifest, open(os.path.join(staging, "manifest.json"), "w"), indent=2)

    backup = target + ".bak"
    if os.path.exists(target):
        if os.path.exists(backup): shutil.rmtree(backup)
        os.replace(target, backup)
    os.replace(staging, target)

    print(f"=== windsurf-subset.py (PROTOTYP) — resolved commit {commit[:12]} ===")
    print(f"  Auswahl-Modus: {mode}")
    print(f"  Subset ({len(selected)}): {', '.join(selected)}")
    print(f"  Ziel: {target}")

if __name__ == "__main__":
    main()
