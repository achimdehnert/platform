#!/usr/bin/env python3
"""generate.py — deterministischer CC-Skill-Generator (platform:ADR-230, PROTOTYP).

Erzeugt aus der branch-stabilen Quelle (platform <ref>, auf einen **resolved Commit**
aufgelöst) ein Ziel-Verzeichnis mit:
- generierten Kopien, jede mit MANAGED-Footer (source_commit, content_hash, do_not_edit)
- `MANAGED_BY` (erlaubter Writer, Commit, Regen-Kommando)
- `manifest.json` (source_repo/commit, generator_version, kind, timestamp, files+hashes)

Lanes (`--kind`, s. `LANES`) je in `mode: swap` (Default, atomarer Verzeichnistausch)
oder `mode: merge` (Ziel gehört dem Generator NICHT allein, s. `merge_in_place`):
- `commands` (Default, swap): `.windsurf/workflows/*.md` → **flach** nach
  `~/.claude/commands/` (CC-Slash-Commands).
- `skills` (merge, seit platform#3467): `skills/<name>/SKILL.md` (+ evtl. weitere
  Dateien) → **verschachtelt** nach `~/.claude/skills/<name>/` (Anthropic Agent Skills,
  user-level → gelten in JEDER Session / jedem Repo / jeder Org, ohne Repo-Kopie).
  Genau deshalb braucht eine Agent-Skill KEINE Verteilung in N Repos — ein generierter
  Install pro Maschine deckt alles ab; die Kanonik bleibt SSoT in platform. Merge statt
  Swap, weil der claude.ai-Skill-Sync eigenmächtig `synced/<bucket-id>/` ins selbe
  Verzeichnis schreibt — ein Swap würde das wegwischen.
- `hooks`/`claude-hooks`: s. Kommentare in `LANES` (ADR-258 bzw. platform#1989).

Swap-Lanes: erst `<target>.tmp`, dann atomarer Rename-Swap (+ `.bak`). **Determinismus:**
gleicher resolved Commit + Generator-Version ⇒ bit-identische Kopien + Manifest
(Zeitstempel separat, nicht hash-relevant). Merge-Lanes schreiben einzeln ins bestehende
Ziel (kein `.bak`-Verzeichnis-Swap) — s. `merge_in_place`.

SICHERHEIT: `--target` ist Pflicht; schreibt NIE ins Live-Ziel der Lane ohne explizites
`--allow-live`. Default = Staging.
"""

import argparse
import datetime
import filecmp
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
    # platform#3467: seit 2026-09-17 schreibt der claude.ai-Skill-Sync eigenmächtig
    # nach ~/.claude/skills (synced/<bucket-id>/, .bucket-*-Marker). Ein Swap dort
    # würde diesen Fremdinhalt wegwischen — derselbe Fehler, gegen den `merge` bei
    # `claude-hooks` schon existiert. `mode: merge` macht das Ziel-Verzeichnis darum
    # zu einem GETEILTEN Verzeichnis: nur die eigenen (Manifest-gelisteten) Skill-
    # Unterverzeichnisse werden angefasst, alles andere bleibt liegen (`merge_in_place`).
    #
    # Übergang vom alten Swap-Regime: ein Ziel, das noch ein `MANAGED_BY`/`manifest.json`
    # aus einem früheren SWAP-Lauf trägt, ist beim ersten Merge-Lauf KEIN Fehler mehr —
    # `pruefe_swap_ziel` greift nur noch für Lanes mit `mode: swap` (s.u. in `main()`).
    # `merge_in_place` räumt die beiden Alt-Dateien auf (superseded durch das
    # dot-file `.cc-skill-dist-manifest.json`, s. MERGE_MANIFEST) statt sie als
    # Leiche liegen zu lassen.
    "skills": {"src": "skills/", "live": "~/.claude/skills", "mode": "merge"},
    # ADR-258 Stufe A: Hook-Skripte (.sh) flach nach ~/.claude/hooks/managed/, ausführbar.
    # WICHTIG: dediziertes managed/-Unterverzeichnis, NICHT ~/.claude/hooks/ selbst — denn
    # generate macht einen atomaren Verzeichnis-SWAP, und ~/.claude/hooks/ enthält auch
    # hand-gepflegte Hooks (PreToolUse/SessionStart/…), die ein Swap sonst wegwischen würde.
    # Verteilung != Enforcement — der SessionEnd-Eintrag in settings.json bleibt manuell
    # (doctor.py prüft das Wiring; bootstrap-hook.py zeigt den Patch).
    "hooks": {"src": "tools/hooks/", "live": "~/.claude/hooks/managed"},
    # platform#1989: die Welle-1-Scanner liegen FLACH in ~/.claude/hooks/ und werden
    # von settings.json von dort ausgeführt. Sie fielen aus der `hooks`-Lane durch
    # zwei unabhängige Gründe: anderes Quellverzeichnis (tools/claude-hooks/) und ein
    # Filter, der nur `.sh` matcht. Verteilt wurden sie deshalb VON HAND — mit der
    # Folge, dass am 2026-08-15 alle drei aktiven Kopien von `main` abwichen und im
    # aktiven `gate_hits.py` die pytest-Sperre aus #1986 fehlte: gemergt, grün, ohne
    # Wirkung.
    #
    # Diese Lane schreibt `mode: merge` — KEIN Verzeichnis-Swap. Das ist keine
    # Geschmacksfrage: `~/.claude/hooks/` enthält ein Dutzend fremder Einträge
    # (`inject_policies.py`, `board_lint.py`, `state/`, `managed/`, das
    # Treffer-Protokoll), die ein Swap wegwischen würde — genau der Unfall vom
    # 2026-07-30, gegen den `pruefe_swap_ziel` existiert.
    "claude-hooks": {
        "src": "tools/claude-hooks/",
        "live": "~/.claude/hooks",
        "mode": "merge",
        "suffixes": (".py", ".sh"),
        "top_level_only": True,  # tests/ und __pycache__/ gehören nie in den aktiven Pfad
    },
}

#: Dateiliste eines Merge-Laufs. Bewusst ein Dot-File und NICHT `manifest.json`:
#: in einem gemischten Verzeichnis wäre der übliche Name ein Fehlsignal für
#: `pruefe_swap_ziel`, das aus dessen Anwesenheit auf ein Swap-Lane-Ziel schliesst.
MERGE_MANIFEST = ".cc-skill-dist-manifest.json"


def lane_mode(kind):
    return LANES[kind].get("mode", "swap")


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
        elif kind == "claude-hooks":
            lane = LANES[kind]
            if not path.endswith(lane["suffixes"]):
                continue
            # Nur die oberste Ebene: `ls-tree -r` liefert auch `tests/…` und
            # `__pycache__/…`. Ein Drill im aktiven Hook-Pfad wäre schlimmer als
            # gar keine Verteilung — er würde bei jedem Stop-Event mitlaufen.
            rest = path[len(lane["src"]) :]
            if lane.get("top_level_only") and "/" in rest:
                continue
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


#: Dateinamen aus dem alten SWAP-Regime — beim Übergang eines Lane-Ziels von
#: `mode: swap` auf `mode: merge` sind sie Leichen (superseded durch MERGE_MANIFEST,
#: das eigene Skill-Verzeichnisse listet statt einer flachen Datei-Liste). Nur diese
#: beiden Namen: sie sind eine eigene Konvention dieses Tools, keine generische
#: Fremddatei-Heuristik.
_LEGACY_SWAP_ARTEFAKTE = ("MANAGED_BY", "manifest.json")


def _dirs_equal(a, b):
    """True, wenn zwei Verzeichnisse rekursiv identischen Inhalt haben (Namen + Bytes).

    Für den Skill-Merge: eine `<name>/`-Kopie wird nur ersetzt, wenn sie sich
    wirklich unterscheidet — kein Backup-/Kopier-Rauschen bei unveraenderten Skills.
    """
    vergleich = filecmp.dircmp(a, b)
    if (
        vergleich.left_only
        or vergleich.right_only
        or vergleich.diff_files
        or vergleich.funny_files
    ):
        return False
    return all(
        _dirs_equal(os.path.join(a, sub), os.path.join(b, sub))
        for sub in vergleich.common_dirs
    )


def merge_in_place(staging, target, manifest):
    """Erzeugte Dateien/Verzeichnisse EINZELN ins Ziel schreiben — nie löschen, nie swappen.

    Zwei Merge-Lanes, zwei Layouts:
    - `claude-hooks`: flache Dateien (`<name>` direkt unter `staging`/`target`).
    - `skills`: Verzeichnisse (`<name>/SKILL.md`, ADR-230) — das ganze `<name>/`-
      Verzeichnis wird ersetzt, nicht einzelne Dateien darin (ein Skill kann weitere
      Dateien neben SKILL.md tragen).

    Beide teilen sich ihr Ziel mit Fremdinhalt (claude-hooks: hand-gepflegte Hooks,
    Zustand, eine zweite Lane; skills: `synced/` vom claude.ai-Skill-Sync seit
    2026-09-17, platform#3467). Für so ein Verzeichnis ist der atomare Swap die
    falsche Operation: er ist genau dann korrekt, wenn das Ziel dem Generator allein
    gehört.

    Gibt den Backup-Pfad zurück (oder ""), wenn eine bestehende Datei/ein Verzeichnis
    ersetzt wurde. Ein Lauf, der nichts ersetzt, legt kein leeres Backup-Verzeichnis an.
    """
    os.makedirs(target, exist_ok=True)
    stempel = manifest["generated_at"].replace(":", "").replace("-", "")[:15]
    backup = os.path.join(target, f".cc-dist-backup-{stempel}")
    ersetzt = 0

    # Übergang eines Ziels von mode:swap auf mode:merge (platform#3467): die alten
    # Swap-Marker sind ab hier bedeutungslos — MERGE_MANIFEST unten ersetzt sie.
    # Liegen bleiben lassen wuerde ein `regenerate:`-Kommando zeigen, das fuer diese
    # Lane nicht mehr stimmt (es rief den Swap-Modus auf).
    for legacy in _LEGACY_SWAP_ARTEFAKTE:
        legacy_pfad = os.path.join(target, legacy)
        if os.path.isfile(legacy_pfad):
            os.remove(legacy_pfad)

    for eintrag in manifest["files"]:
        name = eintrag["name"]
        neu = os.path.join(staging, name)
        alt = os.path.join(target, name)
        if os.path.isdir(neu):
            # Skills: <name>/ als Ganzes ersetzen (SKILL.md + evtl. weitere Dateien).
            if os.path.islink(alt) or os.path.isfile(alt):
                # Fremder Eintrag mit demselben Namen wie ein eigenes Skill-Verzeichnis
                # (z.B. ein kaputter Symlink) — nicht blind ueberschreiben.
                sys.exit(
                    f"ABBRUCH: {alt} ist keine Datei/kein Symlink, sondern sollte ein "
                    f"Skill-Verzeichnis sein — Merge bricht ab, statt es zu ersetzen."
                )
            if os.path.isdir(alt):
                if _dirs_equal(neu, alt):
                    continue  # identisch: nicht anfassen, kein Backup-Rauschen
                os.makedirs(backup, exist_ok=True)
                shutil.copytree(alt, os.path.join(backup, name))
                shutil.rmtree(alt)
                ersetzt += 1
            shutil.copytree(neu, alt)
            continue
        if os.path.exists(alt):
            # Die ersetzte Fassung ist der einzige Zeuge dessen, was zuletzt real
            # lief — bei einem Fehlverhalten will man sie vergleichen können.
            if filecmp.cmp(neu, alt, shallow=False):
                continue  # identisch: nicht anfassen, kein Backup-Rauschen
            os.makedirs(backup, exist_ok=True)
            shutil.copy2(alt, os.path.join(backup, name))
            ersetzt += 1
        # copy2 erhält den Modus — das 0o755 setzt bereits der Staging-Schritt.
        # Ein zweites chmod hier wäre toter Code: der Mutationstest zeigte, dass
        # sein Entfernen keinen Drill umwirft, das Entfernen des Staging-chmod
        # dagegen schon.
        shutil.copy2(neu, alt)

    with open(os.path.join(target, MERGE_MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return backup if ersetzt else ""


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
    # Der Guard schuetzt den Verzeichnis-SWAP. Eine Merge-Lane loescht nichts und
    # teilt ihr Ziel per Definition mit Fremdinhalt — dort waere er ein Dauer-Abbruch.
    if lane_mode(args.kind) == "swap":
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
        if args.kind in ("hooks", "claude-hooks"):
            # Skript-Lane: Footer als #-Kommentar. Gilt fuer .sh UND .py — ein
            # HTML-Kommentar waere in beiden ein Syntaxfehler.
            content = src.rstrip("\n") + f"\n\n# {meta}\n"
        else:
            content = src.rstrip("\n") + f"\n\n<!-- {meta} -->\n"
        if args.kind == "skills":  # verschachtelt: <name>/SKILL.md
            os.makedirs(os.path.join(staging, name), exist_ok=True)
            out = os.path.join(staging, name, "SKILL.md")
        else:  # commands + hooks: flach
            out = os.path.join(staging, name)
        open(out, "w", encoding="utf-8").write(content)
        if args.kind in ("hooks", "claude-hooks"):
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

    if lane_mode(args.kind) == "merge":
        backup = merge_in_place(staging, target, manifest)
        shutil.rmtree(staging)
        print(f"=== generate.py — kind={args.kind}, resolved commit {commit[:12]} ===")
        print(f"  Ziel: {target}  (Modus: merge — kein Verzeichnis-Swap)")
        print(f"  geschrieben: {len(manifest['files'])} Datei(en) + {MERGE_MANIFEST}")
        print(f"  Backup ersetzter Dateien: {backup or '— (nichts ersetzt)'}")
        return

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
