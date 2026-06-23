#!/usr/bin/env python3
"""doctor.py — read-only Drift-Diagnose für CC-Skill-Distribution (platform:ADR-230).

Vergleicht die branch-stabile kanonische Quelle (platform `origin/main`) mit dem
Live-Ziel — OHNE etwas zu ändern. Meldet stale Kopien, dangling Symlinks,
fehlende/zusätzliche Skills, Hybrid-Status und einen Drift-Score.

Zwei Lanes (`--kind`):
- `commands` (Default): `.windsurf/workflows/*.md` ↔ `~/.claude/commands/` (flach).
- `skills`: `skills/<name>/SKILL.md` ↔ `~/.claude/skills/<name>/SKILL.md` (Agent Skills,
  verzeichnis-basiert). Der Relativlink-Guard greift NICHT — Agent-Skill-Verzeichnisse
  dürfen gebündelte Relativ-Referenzen tragen.

Usage: doctor.py [--kind commands|skills] [--platform ~/github/platform]
                 [--commands ~/.claude/commands] [--skills-dir ~/.claude/skills] [--ref origin/main]
"""
import argparse, os, re, subprocess, sys

# Relativlink-Guard (nur Lane `commands`): das flache Ziel ~/.claude/commands kann keine
# Pfad-Slash-Links auflösen → dangling. http(s)/Anker/mailto sind ok. Verlangt Pfad-Slash
# UND echte Datei-Endung, damit Regex/sed-Snippets in Code-Blöcken nicht fehl-matchen.
REL_LINK = re.compile(
    r"\]\((?!https?://|#|mailto:)([^)\s]*/[^)\s]*\.(?:md|markdown|ya?ml|sh|py|txt|json|toml))\)")

MARK = "MANAGED-BY: platform/tools/cc-skill-dist"

# Interne System-Prompt-Workflows (distribute: false) werden nicht in die flache commands-Lane
# verteilt → dürfen im Ziel fehlen, ohne als Drift zu zählen. Parität zu generate.py.
DISTRIBUTE_FALSE = re.compile(r"^distribute:\s*false\b", re.MULTILINE)

# Lane: (Quell-Pfad im Repo, Blob-Endung, key-Extraktor aus repo-Pfad, Live-Ziel, Ziel-Enumerator)
def _name_basename(path): return os.path.basename(path)
def _name_skilldir(path): return os.path.basename(os.path.dirname(path))

def strip_managed_footer(text):
    idx = text.rfind("<!-- " + MARK)
    return text if idx == -1 else text[:idx]

def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def enumerate_commands(root):
    """Flaches Ziel: name -> Pfad zur .md-Datei."""
    if not os.path.isdir(root):
        return {}
    return {f: os.path.join(root, f) for f in os.listdir(root) if f.endswith(".md")}

def enumerate_skills(root):
    """Verzeichnis-Ziel: name -> Pfad zur <name>/SKILL.md."""
    if not os.path.isdir(root):
        return {}
    out = {}
    for d in os.listdir(root):
        p = os.path.join(root, d, "SKILL.md")
        if os.path.isfile(p) or os.path.islink(p):
            out[d] = p
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["commands", "skills"], default="commands")
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--commands", default=os.path.expanduser("~/.claude/commands"))
    ap.add_argument("--skills-dir", default=os.path.expanduser("~/.claude/skills"))
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()

    if a.kind == "commands":
        src_path, suffix, key_of = ".windsurf/workflows/", ".md", _name_basename
        target_dir, target_files, rel_guard = a.commands, enumerate_commands(a.commands), True
    else:
        src_path, suffix, key_of = "skills/", "/SKILL.md", _name_skilldir
        target_dir, target_files, rel_guard = a.skills_dir, enumerate_skills(a.skills_dir), False

    git(["fetch", "origin", "main", "-q"], a.platform)
    listing = git(["ls-tree", "-r", a.ref, src_path], a.platform) or ""
    canon = {}  # name -> blob_sha
    for line in listing.splitlines():
        parts = line.split()  # <mode> blob <sha>\t<path>
        if len(parts) >= 4 and parts[1] == "blob" and parts[-1].endswith(suffix):
            canon[key_of(parts[-1])] = parts[2]
    if not canon:
        print(f"FEHLER: keine kanonischen Quellen unter {a.ref}:{src_path} (kind={a.kind})"); sys.exit(2)

    def canon_content(sha):
        return git(["cat-file", "blob", sha], a.platform)

    if a.kind == "commands":  # interne System-Prompts (distribute: false) sind nie im flachen Ziel
        canon = {n: sha for n, sha in canon.items()
                 if not DISTRIBUTE_FALSE.search(canon_content(sha) or "")}

    sym_ok = sym_stale = sym_dangling = copy_fresh = copy_stale = extra = 0
    issues = []
    for name, path in sorted(target_files.items()):
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

    rel_links = 0
    if rel_guard:
        for name, sha in sorted(canon.items()):
            body = canon_content(sha) or ""
            for m in REL_LINK.finditer(body):
                rel_links += 1
                issues.append(("rel-link", name, f"unauflösbarer Relativlink im flachen Ziel → {m.group(1)}"))

    missing = sorted(set(canon) - set(target_files))

    print(f"=== CC-Skill-Doctor (kind={a.kind}, Quelle: {a.ref}, {len(canon)} kanonisch) ===")
    print(f"  Ziel {target_dir}: {len(target_files)} Einträge")
    print(f"  Symlinks ok={sym_ok}  symlink-stale={sym_stale}  dangling={sym_dangling}")
    print(f"  Kopien fresh={copy_fresh}  copy-stale={copy_stale}")
    print(f"  extra (nicht in Quelle)={extra}  fehlend (in Quelle, nicht im Ziel)={len(missing)}")
    if rel_guard:
        print(f"  rel-links (unauflösbar im flachen Ziel)={rel_links}")
    print(f"  Hybrid? {'JA — Symlinks UND Kopien gemischt' if (sym_ok+sym_stale+sym_dangling)>0 and (copy_fresh+copy_stale)>0 else 'nein'}")
    if missing:
        print("  fehlende Skills:", ", ".join(missing[:10]) + (" …" if len(missing) > 10 else ""))
    if issues:
        print("  --- Befunde (max 15) ---")
        for kind, name, why in issues[:15]:
            print(f"    [{kind}] {name} — {why}")
    drift = sym_stale + sym_dangling + copy_stale + extra + len(missing) + rel_links
    print(f"=== DRIFT-SCORE: {drift} (0 = sauber) ===")
    sys.exit(1 if drift else 0)

if __name__ == "__main__":
    main()
