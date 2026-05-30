#!/usr/bin/env python3
"""generate.py — deterministischer CC-Skill-Generator (platform:ADR-230, PROTOTYP).

Erzeugt aus der branch-stabilen Quelle (platform <ref> `.windsurf/workflows/`,
auf einen **resolved Commit** aufgelöst) ein Ziel-Verzeichnis mit:
- generierten Kopien, jede mit MANAGED-Footer (source_commit, content_hash, do_not_edit)
- `MANAGED_BY` (erlaubter Writer, Commit, Regen-Kommando)
- `manifest.json` (source_repo/commit, generator_version, timestamp, files+hashes)

Atomar: erst nach `<target>.tmp`, dann Rename-Swap. **Determinismus:** gleicher
resolved Commit + gleiche Generator-Version ⇒ bit-identische Kopien + Manifest
(Zeitstempel separat, nicht hash-relevant).

SICHERHEIT: `--target` ist Pflicht; schreibt NIE nach `~/.claude/commands` ohne
explizites `--allow-live` (im Prototyp nicht genutzt). Default = Staging.
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys

GENERATOR_VERSION = "0.1.0-prototype"
MARK = "MANAGED-BY: platform/tools/cc-skill-dist"

def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} fehlgeschlagen: {r.stderr[:200]}")
    return r.stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--target", required=True, help="Ziel-Verzeichnis (Staging). NIE ~/.claude/commands ohne --allow-live")
    ap.add_argument("--allow-live", action="store_true")
    args = ap.parse_args()

    target = os.path.abspath(os.path.expanduser(args.target))
    live = os.path.abspath(os.path.expanduser("~/.claude/commands"))
    if target == live and not args.allow_live:
        sys.exit("ABBRUCH: Ziel ist ~/.claude/commands — Prototyp schreibt nicht live (--allow-live nötig).")

    git(["fetch", "origin", "main", "-q"], args.platform)
    commit = git(["rev-parse", args.ref], args.platform).strip()
    listing = git(["ls-tree", "-r", args.ref, ".windsurf/workflows/"], args.platform)
    blobs = {}  # name -> blob_sha
    for line in listing.splitlines():
        p = line.split()
        if len(p) >= 4 and p[1] == "blob" and p[-1].endswith(".md"):
            blobs[os.path.basename(p[-1])] = (p[2], p[-1])

    staging = target + ".tmp"
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    manifest = {"source_repo": "achimdehnert/platform", "source_commit": commit,
                "generator_version": GENERATOR_VERSION,
                "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "target_type": "copy", "skill_count": len(blobs), "files": []}
    for name, (bsha, path) in sorted(blobs.items()):
        src = git(["cat-file", "blob", bsha], args.platform)
        chash = hashlib.sha256(src.encode("utf-8")).hexdigest()
        footer = (f"\n\n<!-- {MARK} · generated=true · source={path} · "
                  f"source_commit={commit[:12]} · content_hash=sha256:{chash[:16]} · do_not_edit -->\n")
        open(os.path.join(staging, name), "w", encoding="utf-8").write(src.rstrip("\n") + footer)
        manifest["files"].append({"name": name, "source_path": path, "content_hash": "sha256:" + chash})

    json.dump(manifest, open(os.path.join(staging, "manifest.json"), "w"), indent=2)
    open(os.path.join(staging, "MANAGED_BY"), "w").write(
        f"managed_by: platform/tools/cc-skill-dist/generate.py\n"
        f"allowed_writer: cc-skill-dist generator only — KEINE Handänderung\n"
        f"source: achimdehnert/platform @ {commit}\n"
        f"regenerate: python3 tools/cc-skill-dist/generate.py --target {target}\n")

    # Atomarer Swap
    backup = target + ".bak"
    if os.path.exists(target):
        if os.path.exists(backup):
            shutil.rmtree(backup)
        os.replace(target, backup)
    os.replace(staging, target)

    print(f"=== generate.py (PROTOTYP) — resolved commit {commit[:12]} ===")
    print(f"  Ziel: {target}")
    print(f"  generiert: {len(blobs)} Skills + manifest.json + MANAGED_BY")
    print(f"  Backup voriger Stand: {backup if os.path.exists(backup) else '—'}")

if __name__ == "__main__":
    main()
