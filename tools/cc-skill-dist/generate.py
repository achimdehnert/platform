#!/usr/bin/env python3
"""generate.py — deterministischer CC-Skill-Generator (platform:ADR-230, PROTOTYP).

Erzeugt aus der branch-stabilen Quelle (platform <ref>, auf einen **resolved Commit**
aufgelöst) ein Ziel-Verzeichnis mit:
- generierten Kopien, jede mit MANAGED-Footer (source_commit, content_hash, do_not_edit)
- `MANAGED_BY` (erlaubter Writer, Commit, Regen-Kommando)
- `manifest.json` (source_repo/commit, generator_version, kind, timestamp, files+hashes)

Zwei Lanes (`--kind`):
- `commands` (Default): `.windsurf/workflows/*.md` → **flach** nach `~/.claude/commands/`
  (CC-Slash-Commands).
- `skills`: `skills/<name>/SKILL.md` → **verschachtelt** nach `~/.claude/skills/<name>/SKILL.md`
  (Anthropic Agent Skills, user-level → gelten in JEDER Session / jedem Repo / jeder Org,
  ohne Repo-Kopie). Genau deshalb braucht eine Agent-Skill KEINE Verteilung in N Repos —
  ein generierter Install pro Maschine deckt alles ab; die Kanonik bleibt SSoT in platform.

Atomar: erst `<target>.tmp`, dann Rename-Swap (+ `.bak`). **Determinismus:** gleicher
resolved Commit + Generator-Version ⇒ bit-identische Kopien + Manifest (Zeitstempel
separat, nicht hash-relevant).

SICHERHEIT: `--target` ist Pflicht; schreibt NIE ins Live-Ziel der Lane ohne explizites
`--allow-live`. Default = Staging.
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

GENERATOR_VERSION = "0.2.0"
MARK = "MANAGED-BY: platform/tools/cc-skill-dist"

# Interne System-Prompt-Workflows (Frontmatter `distribute: false`) sind KEINE Slash-Commands —
# sie dienen nur als Body/System-Prompt für workflow_execute und dürfen nicht ins flache
# ~/.claude/commands verteilt werden (sonst toter /command). Nur Lane `commands`. Parität in doctor.py.
DISTRIBUTE_FALSE = re.compile(r"^distribute:\s*false\b", re.MULTILINE)

# Lane-Konfiguration: Quell-Pfad im Repo + Live-Ziel (ohne --allow-live gesperrt).
LANES = {
    "commands": {"src": ".windsurf/workflows/", "live": "~/.claude/commands"},
    "skills": {"src": "skills/", "live": "~/.claude/skills"},
    # ADR-258 Stufe A: Hook-Skripte (.sh) flach nach ~/.claude/hooks/managed/, ausführbar.
    # WICHTIG: dediziertes managed/-Unterverzeichnis, NICHT ~/.claude/hooks/ selbst — denn
    # generate macht einen atomaren Verzeichnis-SWAP, und ~/.claude/hooks/ enthält auch
    # hand-gepflegte Hooks (PreToolUse/SessionStart/…), die ein Swap sonst wegwischen würde.
    # Verteilung != Enforcement — der SessionEnd-Eintrag in settings.json bleibt manuell
    # (doctor.py prüft das Wiring; bootstrap-hook.py zeigt den Patch).
    "hooks": {"src": "tools/hooks/", "live": "~/.claude/hooks/managed"},
}


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} fehlgeschlagen: {r.stderr[:200]}")
    return r.stdout


def collect(listing, kind):
    """Quell-Blobs → name -> (blob_sha, repo_pfad).
    commands: *.md, key=basename (flach). skills: */SKILL.md, key=Skill-Verzeichnisname."""
    blobs = {}
    for line in listing.splitlines():
        p = line.split()
        if len(p) < 4 or p[1] != "blob":
            continue
        path = p[-1]
        if kind == "commands" and path.endswith(".md"):
            blobs[os.path.basename(path)] = (p[2], path)
        elif kind == "skills" and path.endswith("/SKILL.md"):
            blobs[os.path.basename(os.path.dirname(path))] = (p[2], path)
        elif kind == "hooks" and path.endswith(".sh"):
            blobs[os.path.basename(path)] = (p[2], path)
    return blobs


def _fremde_eintraege(target, inhalt):
    """Verzeichnisinhalt minus das, was laut Manifest von hier stammt.

    Ist das Manifest unlesbar oder ohne `files`, gilt ALLES als fremd — ein
    kaputtes Manifest darf kein Freibrief sein.
    """
    eigene = {"manifest.json", "MANAGED_BY"}
    try:
        with open(os.path.join(target, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        eigene |= {eintrag["name"] for eintrag in manifest["files"]}
    except (OSError, ValueError, KeyError, TypeError):
        return set(inhalt) - eigene
    return set(inhalt) - eigene


def pruefe_swap_ziel(target, kind):
    """Abbrechen, wenn der Verzeichnis-Swap Fremdinhalte wegwischen würde.

    `--target` bekommt das Lane-Verzeichnis SELBST (z.B. `~/.claude/commands`),
    nie dessen Elternverzeichnis. Wer versehentlich `~/.claude` angibt, verliert
    beim atomaren Swap das ganze Verzeichnis.

    Realfall 2026-07-30: `--target ~/.claude --kind commands --allow-live` schob
    `~/.claude` nach `~/.claude.bak` und legte ein neues mit 51 flachen Dateien an
    — `commands/`, `policies/`, `hooks/`, `bin/`, `mail-*.env` und 41
    Session-Verzeichnisse waren weg (wiederherstellbar, aber weg). Der
    `--allow-live`-Guard griff nicht: er prüft **Gleichheit** mit dem Live-Pfad,
    und `~/.claude` ist dessen Eltern, nicht der Pfad selbst.

    Kriterium: ein Swap-Ziel ist entweder leer/nicht vorhanden (frisches Staging)
    oder es enthält **ausschliesslich**, was ein früherer Lauf dort erzeugt hat.

    Die bloße ANWESENHEIT von `MANAGED_BY`/`manifest.json` genügt als Freibrief
    NICHT — der Unfall oben schreibt genau diese zwei Dateien in das falsche
    Verzeichnis. Blieben sie liegen, hätte derselbe Tippfehler beim zweiten Mal
    freie Bahn: ein Guard, dessen Erkennungsmerkmal vom Fehler selbst erzeugt
    wird, schützt nur beim ersten Mal (Retro-Befund 2026-07-31). Deshalb wird
    der Inhalt gegen die Dateiliste des Manifests gehalten: taucht dort etwas
    auf, das der Generator nicht erzeugt hat, ist es ein fremdes Verzeichnis.
    """
    if not os.path.isdir(target):
        return
    inhalt = os.listdir(target)
    if not inhalt:
        return
    lane_name = os.path.basename(LANES[kind]["live"].rstrip("/"))
    if "manifest.json" in inhalt:
        fremd = _fremde_eintraege(target, inhalt)
        if not fremd:
            return  # echter Zweitlauf: alles im Ziel stammt aus dem Manifest
        sys.exit(
            f"ABBRUCH: {target} trägt zwar ein Manifest, enthält aber "
            f"{len(fremd)} Eintrag/Einträge, die der Generator nie erzeugt hat: "
            f"{', '.join(sorted(fremd)[:6])}"
            f"{' …' if len(fremd) > 6 else ''}\n"
            f"  Das sieht nach einem Fremdverzeichnis mit Manifest-Resten aus — "
            f"ein Swap würde diese Einträge wegwischen.\n"
            f"  Gemeint war wahrscheinlich: --target {os.path.join(target, lane_name)}"
        )
    if "MANAGED_BY" in inhalt:
        sys.exit(
            f"ABBRUCH: {target} trägt ein MANAGED_BY, aber kein manifest.json — "
            f"der Inhalt ist damit nicht gegen die Generator-Dateiliste prüfbar.\n"
            f"  Entweder das Verzeichnis leeren oder --target korrigieren "
            f"(gemeint war wahrscheinlich {os.path.join(target, lane_name)})."
        )
    sys.exit(
        f"ABBRUCH: {target} ist nicht leer und stammt nicht aus einem früheren Lauf "
        f"(kein MANAGED_BY/manifest.json) — ein Swap würde {len(inhalt)} fremde "
        f"Einträge wegwischen.\n"
        f"  Gemeint war wahrscheinlich: --target {os.path.join(target, lane_name)}\n"
        f"  --target bekommt das Lane-Verzeichnis selbst, nicht sein Elternverzeichnis."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default=os.path.expanduser("~/github/platform"))
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument(
        "--kind",
        choices=list(LANES),
        default="commands",
        help="commands = Slash-Commands (flach, Default); skills = Agent Skills (verschachtelt)",
    )
    ap.add_argument(
        "--target",
        required=True,
        help="Ziel-Verzeichnis (Staging). Live nur mit --allow-live",
    )
    ap.add_argument("--allow-live", action="store_true")
    args = ap.parse_args()

    lane = LANES[args.kind]
    target = os.path.abspath(os.path.expanduser(args.target))
    live = os.path.abspath(os.path.expanduser(lane["live"]))
    if target == live and not args.allow_live:
        sys.exit(
            f"ABBRUCH: Ziel ist {lane['live']} — Prototyp schreibt nicht live (--allow-live nötig)."
        )
    # VOR dem Netz-/git-Zugriff: ein falsches --target darf nicht erst am Swap auffallen.
    pruefe_swap_ziel(target, args.kind)

    git(["fetch", "origin", "main", "-q"], args.platform)
    commit = git(["rev-parse", args.ref], args.platform).strip()
    listing = git(["ls-tree", "-r", args.ref, lane["src"]], args.platform)
    blobs = collect(listing, args.kind)
    if not blobs:
        sys.exit(
            f"ABBRUCH: keine Quellen unter {args.ref}:{lane['src']} (kind={args.kind})"
        )

    staging = target + ".tmp"
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    manifest = {
        "source_repo": "achimdehnert/platform",
        "source_commit": commit,
        "generator_version": GENERATOR_VERSION,
        "kind": args.kind,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "target_type": "copy",
        "skill_count": 0,
        "files": [],
    }
    for name, (bsha, path) in sorted(blobs.items()):
        src = git(["cat-file", "blob", bsha], args.platform)
        if args.kind == "commands" and DISTRIBUTE_FALSE.search(src):
            continue  # interner System-Prompt — kein Slash-Command
        chash = hashlib.sha256(src.encode("utf-8")).hexdigest()
        meta = (
            f"{MARK} · generated=true · source={path} · "
            f"source_commit={commit[:12]} · content_hash=sha256:{chash[:16]} · do_not_edit"
        )
        if args.kind == "hooks":
            # Shell-Skript: Footer als #-Kommentar (HTML-Kommentar wäre in .sh ungültig).
            content = src.rstrip("\n") + f"\n\n# {meta}\n"
        else:
            content = src.rstrip("\n") + f"\n\n<!-- {meta} -->\n"
        if args.kind == "skills":  # verschachtelt: <name>/SKILL.md
            os.makedirs(os.path.join(staging, name), exist_ok=True)
            out = os.path.join(staging, name, "SKILL.md")
        else:  # commands + hooks: flach
            out = os.path.join(staging, name)
        open(out, "w", encoding="utf-8").write(content)
        if args.kind == "hooks":
            os.chmod(
                out, 0o755
            )  # Hooks müssen ausführbar sein (REC-6: 0755, kein world-write)
        manifest["files"].append(
            {"name": name, "source_path": path, "content_hash": "sha256:" + chash}
        )

    manifest["skill_count"] = len(
        manifest["files"]
    )  # nach distribute:false-Filter, nicht len(blobs)
    json.dump(manifest, open(os.path.join(staging, "manifest.json"), "w"), indent=2)
    # --allow-live in die regenerate-Zeile aufnehmen, wenn das Ziel das Live-Verzeichnis
    # ist — sonst läuft ein Copy-Paste des Befehls in den Guard (target==live) und bricht ab.
    regen_live = " --allow-live" if target == live else ""
    open(os.path.join(staging, "MANAGED_BY"), "w").write(
        f"managed_by: platform/tools/cc-skill-dist/generate.py (kind={args.kind})\n"
        f"allowed_writer: cc-skill-dist generator only — KEINE Handänderung\n"
        f"source: achimdehnert/platform @ {commit}\n"
        f"regenerate: python3 tools/cc-skill-dist/generate.py --kind {args.kind} --target {target}{regen_live}\n"
    )

    # Atomarer Swap
    backup = target + ".bak"
    if os.path.exists(target):
        if os.path.exists(backup):
            shutil.rmtree(backup)
        os.replace(target, backup)
    os.replace(staging, target)

    print(f"=== generate.py — kind={args.kind}, resolved commit {commit[:12]} ===")
    print(f"  Ziel: {target}")
    print(
        f"  generiert: {len(manifest['files'])} {args.kind} + manifest.json + MANAGED_BY"
    )
    print(f"  Backup voriger Stand: {backup if os.path.exists(backup) else '—'}")


if __name__ == "__main__":
    main()
