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
import argparse
import os
import re
import subprocess
import sys

# Relativlink-Guard (nur Lane `commands`): das flache Ziel ~/.claude/commands kann keine
# Pfad-Slash-Links auflösen → dangling. http(s)/Anker/mailto sind ok. Verlangt Pfad-Slash
# UND echte Datei-Endung, damit Regex/sed-Snippets in Code-Blöcken nicht fehl-matchen.
REL_LINK = re.compile(
    r"\]\((?!https?://|#|mailto:)([^)\s]*/[^)\s]*\.(?:md|markdown|ya?ml|sh|py|txt|json|toml))\)")

MARK = "MANAGED-BY: platform/tools/cc-skill-dist"

# Interne System-Prompt-Workflows (distribute: false) werden nicht in die flache commands-Lane
# verteilt → dürfen im Ziel fehlen, ohne als Drift zu zählen. Parität zu generate.py.
DISTRIBUTE_FALSE = re.compile(r"^distribute:\s*false\b", re.MULTILINE)

# SUGGEST-lint (ADR-230 Phase-1): mcp[0-9]_tool — Windsurf-Ära-Präfix in verteilten Skills.
# Nicht in DRIFT-SCORE (neue Regeln starten als SUGGEST per repo-health-rule-discipline).
MCP_LEGACY_TOKEN = re.compile(r"mcp\d+_\w+")

# SUGGEST-lint (Issue #970, PR #965-Nachtrag): KD-Referenz-Feldkonsistenz — jede Skill-Datei,
# die einen KD-Referenz-Block deklariert (kd-scout/klickdummy/kd-review), muss alle 4 Felder
# nennen. Verhindert genau die Drift, die PR #965 selbst schon einmal manuell nachziehen musste
# (Session-Retro 2026-07-06). Bewusst NUR Feld-Praesenz, NICHT ob jedes "—" einen Grund traegt —
# das ist am Skill-Definitions-Text (der die Konvention selbst beschreibt) nicht false-positive-frei
# pruefbar, nur am RENDERED Output einer echten Skill-Ausfuehrung (out of scope fuer diesen Linter).
KD_REFERENZ_MARKER = "KD-Referenz"
KD_REFERENZ_FIELDS = ("Spec", "Lokal", "GitHub", "iil.pet")

# Lane: (Quell-Pfad im Repo, Blob-Endung, key-Extraktor aus repo-Pfad, Live-Ziel, Ziel-Enumerator)
def _name_basename(path): return os.path.basename(path)
def _name_skilldir(path): return os.path.basename(os.path.dirname(path))

def strip_managed_footer(text):
    # HTML-Footer (commands/skills) ODER Shell-#-Footer (hooks, ADR-258).
    idx_html = text.rfind("<!-- " + MARK)
    idx_sh = text.rfind("# " + MARK)
    idx = max(idx_html, idx_sh)
    return text if idx == -1 else text[:idx]


def enumerate_hooks(root):
    """Flaches Ziel: name -> Pfad zur .sh-Datei (ADR-258 hooks-Lane)."""
    if not os.path.isdir(root):
        return {}
    return {f: os.path.join(root, f) for f in os.listdir(root) if f.endswith(".sh")}


# ADR-258 REC-3/4: stabiler Hook-Pfad + verpflichtende settings.json-Wiring-Prüfung.
REAPER_HOOK = "reap_worktrees.sh"


def check_hook_wiring(hooks_dir):
    """Prüft, ob der Reaper-Hook (a) ausführbar im Ziel liegt UND (b) in
    ~/.claude/settings.json als SessionEnd-Command auf den stabilen Pfad verdrahtet ist.
    Verteilung allein (Datei da) zählt NICHT als gesund (REC-1/3). Gibt issues-Liste zurück."""
    import json

    issues = []
    stable = os.path.join(os.path.expanduser(hooks_dir), REAPER_HOOK)
    if os.path.isfile(stable) and not os.access(stable, os.X_OK):
        issues.append(("hook-not-executable", REAPER_HOOK, "Datei vorhanden, aber nicht ausführbar"))
    settings = os.path.expanduser("~/.claude/settings.json")
    if not os.path.isfile(settings):
        issues.append(("settings-missing", "settings.json", "keine ~/.claude/settings.json gefunden"))
        return issues
    try:
        cfg = json.load(open(settings, encoding="utf-8"))
    except Exception as e:
        issues.append(("settings-unparsable", "settings.json", str(e)[:60]))
        return issues
    cmds = []
    for grp in cfg.get("hooks", {}).get("SessionEnd", []):
        for h in grp.get("hooks", []):
            cmds.append(h.get("command", ""))
    # Pfad-PRÄZISE prüfen (nicht nur Basename): der Eintrag muss auf den stabilen managed-Pfad
    # zeigen — ein Verweis auf einen alten/hand-gepflegten Pfad gleichen Namens zählt NICHT.
    want = os.path.normpath(os.path.expanduser(stable))
    if not any(os.path.normpath(os.path.expanduser(c)) == want for c in cmds):
        issues.append(("settings-wiring-missing", "SessionEnd",
                       f"kein SessionEnd-Hook verweist auf {stable} — Hook feuert nie (REC-3)"))
    return issues

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
    ap.add_argument("--kind", choices=["commands", "skills", "hooks"], default="commands")
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--commands", default=os.path.expanduser("~/.claude/commands"))
    ap.add_argument("--skills-dir", default=os.path.expanduser("~/.claude/skills"))
    ap.add_argument("--hooks-dir", default=os.path.expanduser("~/.claude/hooks/managed"))
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()

    if a.kind == "commands":
        src_path, suffix, key_of = ".windsurf/workflows/", ".md", _name_basename
        target_dir, target_files, rel_guard = a.commands, enumerate_commands(a.commands), True
    elif a.kind == "hooks":
        src_path, suffix, key_of = "tools/hooks/", ".sh", _name_basename
        target_dir, target_files, rel_guard = a.hooks_dir, enumerate_hooks(a.hooks_dir), False
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

    # ADR-258 REC-3: für die hooks-Lane reicht „Datei verteilt" NICHT — das settings.json-
    # Wiring muss vorhanden sein, sonst feuert der Hook nie. Zählt in den Drift-Score.
    wiring_issues = check_hook_wiring(a.hooks_dir) if a.kind == "hooks" else []
    issues.extend(wiring_issues)

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
    if a.kind == "hooks":
        print(f"  Wiring-Befunde (settings.json SessionEnd)={len(wiring_issues)}")
    drift = sym_stale + sym_dangling + copy_stale + extra + len(missing) + rel_links + len(wiring_issues)
    print(f"=== DRIFT-SCORE: {drift} (0 = sauber) ===")

    # SUGGEST-lint: mcp[0-9]_token in distributed commands (advisory, not in DRIFT-SCORE)
    if a.kind == "commands":
        suggest_hits = []
        for name, sha in sorted(canon.items()):
            body = canon_content(sha) or ""
            for line in body.splitlines():
                if MCP_LEGACY_TOKEN.search(line) and "TODO(mcp-migration)" not in line:
                    for tok in MCP_LEGACY_TOKEN.findall(line):
                        suggest_hits.append((name, tok))
        if suggest_hits:
            print(f"  --- SUGGEST ({len(suggest_hits)} legacy mcp[0-9]_ Token(s) in verteilten Skills) ---")
            for skill, tok in suggest_hits[:15]:
                print(f"    [suggest] {skill} — {tok} (Windsurf-Präfix, Phase-2-Migration offen)")
            if len(suggest_hits) > 15:
                print(f"    … und {len(suggest_hits) - 15} weitere")
        else:
            print("  --- SUGGEST: 0 legacy mcp[0-9]_ Token(s) — Phase-1-Migration vollständig ---")

        # SUGGEST-lint: KD-Referenz-Feldkonsistenz (Issue #970)
        kd_incomplete = []
        kd_declared = False
        for name, sha in sorted(canon.items()):
            body = canon_content(sha) or ""
            if KD_REFERENZ_MARKER not in body:
                continue
            kd_declared = True
            missing_fields = [f for f in KD_REFERENZ_FIELDS if f not in body]
            if missing_fields:
                kd_incomplete.append((name, missing_fields))
        if kd_declared:
            if kd_incomplete:
                print(
                    f"  --- SUGGEST ({len(kd_incomplete)} Skill(s) mit unvollständigem KD-Referenz-Schema) ---"
                )
                for skill, missing_fields in kd_incomplete[:15]:
                    print(f"    [suggest] {skill} — fehlende Felder: {', '.join(missing_fields)}")
            else:
                print("  --- SUGGEST: 0 Skills mit unvollständigem KD-Referenz-Schema ---")

    sys.exit(1 if drift else 0)

if __name__ == "__main__":
    main()
