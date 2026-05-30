#!/usr/bin/env python3
"""doctor.py — read-only Drift-Diagnose für CC-Skill-Distribution (platform:ADR-230).

Vergleicht die branch-stabile kanonische Quelle (platform `origin/main`
`.windsurf/workflows/`) mit dem live `~/.claude/commands/` — OHNE etwas zu ändern.
Meldet: stale Kopien, dangling Symlinks, fehlende/zusätzliche Skills, Hybrid-Status.

Usage: doctor.py [--platform ~/github/platform] [--commands ~/.claude/commands] [--ref origin/main]
"""
import argparse, os, subprocess, sys

# Footer, den generate.py an jede verteilte Kopie anhängt (MANAGED-BY-Marke).
# doctor muss ihn vor dem Inhaltsvergleich abstreifen, sonst liest sich jede
# korrekt generierte Kopie fälschlich als copy-stale (Footer ≠ nackter Blob).
MARK = "MANAGED-BY: platform/tools/cc-skill-dist"

def strip_managed_footer(text):
    idx = text.rfind("<!-- " + MARK)
    return text if idx == -1 else text[:idx]

def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--commands", default=os.path.expanduser("~/.claude/commands"))
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()

    git(["fetch", "origin", "main", "-q"], a.platform)
    # Kanonische Quelle: blob-sha = inhalts-adressiert, branch-stabil
    listing = git(["ls-tree", "-r", a.ref, ".windsurf/workflows/"], a.platform) or ""
    canon = {}  # name -> blob_sha
    for line in listing.splitlines():
        # <mode> blob <sha>\t<path>
        parts = line.split()
        if len(parts) >= 4 and parts[1] == "blob" and parts[-1].endswith(".md"):
            canon[os.path.basename(parts[-1])] = parts[2]
    if not canon:
        print(f"FEHLER: keine kanonischen Workflows unter {a.ref}:.windsurf/workflows/"); sys.exit(2)

    def canon_content(sha):
        return git(["cat-file", "blob", sha], a.platform)

    cmd_files = {f: os.path.join(a.commands, f) for f in os.listdir(a.commands) if f.endswith(".md")} \
        if os.path.isdir(a.commands) else {}

    sym_ok = sym_stale = sym_dangling = copy_fresh = copy_stale = extra = 0
    issues = []
    for name, path in sorted(cmd_files.items()):
        is_link = os.path.islink(path)
        if name not in canon:
            extra += 1; issues.append(("extra", name, "im Ziel, aber nicht in der Quelle")); continue
        if is_link and not os.path.exists(path):
            sym_dangling += 1; issues.append(("dangling", name, "Symlink ins Leere → " + os.readlink(path))); continue
        try:
            disk = open(path, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            issues.append(("unlesbar", name, str(e)[:40])); continue
        src = canon_content(canon[name]) or "\0"
        same = (strip_managed_footer(disk).rstrip("\n") == src.rstrip("\n"))
        if is_link:
            sym_ok += 1 if same else 0
            if not same: sym_stale += 1; issues.append(("symlink-stale", name, "Symlink-Inhalt ≠ Quelle"))
        else:
            if same: copy_fresh += 1
            else: copy_stale += 1; issues.append(("copy-stale", name, "Kopie ≠ Quelle (veraltet)"))

    missing = sorted(set(canon) - set(cmd_files))

    print(f"=== CC-Skill-Doctor (Quelle: {a.ref}, {len(canon)} kanonische Workflows) ===")
    print(f"  Ziel {a.commands}: {len(cmd_files)} Dateien")
    print(f"  Symlinks ok={sym_ok}  symlink-stale={sym_stale}  dangling={sym_dangling}")
    print(f"  Kopien fresh={copy_fresh}  copy-stale={copy_stale}")
    print(f"  extra (nicht in Quelle)={extra}  fehlend (in Quelle, nicht im Ziel)={len(missing)}")
    print(f"  Hybrid? {'JA — Symlinks UND Kopien gemischt' if (sym_ok+sym_stale+sym_dangling)>0 and (copy_fresh+copy_stale)>0 else 'nein'}")
    if missing:
        print("  fehlende Skills:", ", ".join(missing[:10]) + (" …" if len(missing) > 10 else ""))
    if issues:
        print("  --- Befunde (max 15) ---")
        for kind, name, why in issues[:15]:
            print(f"    [{kind}] {name} — {why}")
    drift = sym_stale + sym_dangling + copy_stale + extra + len(missing)
    print(f"=== DRIFT-SCORE: {drift} (0 = sauber) ===")
    sys.exit(1 if drift else 0)

if __name__ == "__main__":
    main()
