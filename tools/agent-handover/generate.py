#!/usr/bin/env python3
"""generate.py — erzeugt/aktualisiert <repo>/docs/AGENT_HANDOVER.md mit
verifizierbaren Ankern + SSoT-Zeigern (platform:new-github-project-Vorlage).

Prinzip: Anker werden GEZOGEN (git/gh/Repo-Introspektion), nicht getippt —
daher driftfrei. Der Auto-Block liegt zwischen Markern; Re-Runs ersetzen NUR
diesen Block, von Hand gepflegte Abschnitte bleiben erhalten.

Uniform über alle Repos (keine ttz/meiki-Sonderbehandlung — souveränitäts-
neutrale Doku-/Metadaten-Arbeit).

`--ref` liest die Anker read-only aus einem Git-Ref (z. B. `origin/main`),
OHNE den (evtl. dirty / Feature-Branch-) Working-Tree anzufassen. Pflicht für
Repos, in denen man nicht selbst arbeitet, sonst sind die Anker stale.

Verhalten bei bestehender docs/AGENT_HANDOVER.md:
  - mit AUTO-Markern   → nur Auto-Block ersetzt (Hand-Abschnitte bleiben)
  - ohne Marker        → Auto-Block wird nach dem H1 EINGEFÜGT, restliches
                         Dokument bleibt vollständig erhalten (Inject-Modus)
  - keine Datei        → aus Vorlage neu erstellt
  - --force            → bestehende Datei mit frischer Vorlage ÜBERSCHREIBEN
                         (Bestand verworfen; nur bewusst nutzen)

Usage:
  generate.py [REPO_PATH] [--ref origin/main] [--write] [--force] [--no-orchestrator]
  Default: Dry-Run (stdout). REPO_PATH default = cwd.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

AUTO_START = "<!-- AGENT_HANDOVER:AUTO START — generiert via platform/tools/agent-handover, nicht von Hand editieren -->"
AUTO_END = "<!-- AGENT_HANDOVER:AUTO END -->"
INJECT_NOTE = "> _Anker-Block unten ist generiert (`platform/tools/agent-handover`); Re-Runs ersetzen nur den Block zwischen den Markern. Restliches Dokument von Hand gepflegt._"

PF_CANDIDATES = ("project-facts.md", ".windsurf/rules/project-facts.md", "docs/project-facts.md")


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=40)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def read_project_facts(root, ref):
    for p in PF_CANDIDATES:
        if ref:
            c = run(["git", "show", "{0}:{1}".format(ref, p)], root)
            if c is not None:
                return p, c
        else:
            fp = os.path.join(root, p)
            if os.path.isfile(fp):
                return p, open(fp, encoding="utf-8").read()
    return PF_CANDIDATES[0], ""


def pf_value(text, key):
    m = re.search(r"\*\*" + re.escape(key) + r"\*\*\s*[:=]\s*`?([^`\n|]+?)`?\s*$", text, re.M)
    return m.group(1).strip() if m else None


def build_auto(root, today, no_orch, ref):
    pf_rel, pf = read_project_facts(root, ref)
    repo_name = pf_value(pf, "REPO_NAME") or os.path.basename(root)
    owner = pf_value(pf, "REPO_OWNER") or "achimdehnert"
    adr_path = pf_value(pf, "ADR_PATH") or "docs/adr"

    if ref:
        branch = ref.split("/")[-1]
        last = run(["git", "log", "-1", "--format=%h %s", ref], root) or "?"
        clean = "n/a (Snapshot von {0})".format(ref)
        manage = run(["bash", "-c", "git ls-tree -r --name-only {0} | grep -E '(^|/)manage\\.py$' | head -1".format(ref)], root)
        log5 = run(["git", "log", "-5", "--format=%ad %s", "--date=short", ref], root) or ""
        adr_listing = run(["bash", "-c", "git ls-tree --name-only {0}:{1} 2>/dev/null".format(ref, adr_path)], root) or ""
        adr_files = [l for l in adr_listing.splitlines() if re.match(r"ADR-\d+", l)]
    else:
        branch = run(["git", "branch", "--show-current"], root) or "main"
        last = run(["git", "log", "-1", "--format=%h %s"], root) or "?"
        dirty = run(["git", "status", "--porcelain"], root)
        clean = "ja" if dirty == "" else "nein (uncommittete Änderungen)"
        manage = run(["bash", "-c", "find . -name manage.py -not -path '*/node_modules/*' -not -path '*/.venv*' | head -1"], root)
        log5 = run(["git", "log", "-5", "--format=%ad %s", "--date=short"], root) or ""
        adr_dir = os.path.join(root, adr_path)
        adr_files = sorted(f for f in os.listdir(adr_dir) if re.match(r"ADR-\d+", f)) if os.path.isdir(adr_dir) else []

    last_sha = last.split(" ", 1)[0]

    ci = "n/a"
    ci_raw = run(["gh", "run", "list", "-L1", "--branch", branch, "--repo",
                  "{0}/{1}".format(owner, repo_name), "--json", "conclusion,databaseId"], root)
    if ci_raw:
        try:
            arr = json.loads(ci_raw)
            if arr:
                ci = "{0}@{1}".format(arr[0].get("conclusion"), arr[0].get("databaseId"))
        except Exception:
            pass

    if manage:
        mig_val, mig_cmd = "siehe Prüfbefehl (DB nötig)", "python manage.py showmigrations | grep '\\[ \\]'"
    else:
        mig_val, mig_cmd = "n/a (kein Django/manage.py)", "—"

    recent = "\n".join("- " + l for l in log5.splitlines()) or "- (keine Commits gelesen)"

    adr_files = adr_files[:6]
    if adr_files:
        adr_line = ", ".join("`{0}:{1}`".format(repo_name, re.match(r"(ADR-\d+)", a).group(1)) for a in adr_files)
    else:
        adr_line = "`{0}/` (Index)".format(adr_path)

    orch_line = "" if no_orch else "\n- Orchestrator-Memory: `agent_memory_search \"{0}\"`".format(repo_name)

    auto = """{START}
## Aktueller Stand
| Attribut | Wert |
|---|---|
| Zuletzt aktualisiert | {today} |
| Branch | {branch} |
| Phase | _siehe `{pf_rel}` / vom Bearbeiter pflegen_ |

## Verifizierbare Anker
> **Empfänger-Ritual:** Diese Anker ZUERST prüfen, bevor du dem Prosa-Stand glaubst.
> Stimmt einer nicht → Handover als veraltet behandeln.
| Anker | Wert | Prüfbefehl |
|---|---|---|
| Letzter stabiler SHA | `{last}` | `git log --oneline -1 {last_sha}` |
| CI-Status | {ci} | `gh run list -L1 --branch {branch}` |
| Migrationen | {mig_val} | `{mig_cmd}` |
| Working-Tree sauber | {clean} | `git status --porcelain` |

## SSoT-Zeiger (referenzieren, NICHT nacherzählen)
- Projekt-Fakten: `{pf_rel}`
- Relevante ADRs: {adr_line}{orch_line}

## Was wurde zuletzt getan?
{recent}
{END}""".format(START=AUTO_START, END=AUTO_END, today=today, branch=branch, pf_rel=pf_rel,
                last=last, last_sha=last_sha, ci=ci, mig_val=mig_val, mig_cmd=mig_cmd,
                clean=clean, adr_line=adr_line, orch_line=orch_line, recent=recent)
    return repo_name, auto


HEADER = """# AGENT_HANDOVER — {repo_name}
> Lesen vor jeder Session. Aktualisieren nach jeder Session.
> Der Anker-Block ist generiert (`platform/tools/agent-handover`); die Abschnitte
> unterhalb des AUTO-END-Markers von Hand pflegen.

"""

HUMAN_DEFAULT = """

## Offene Aufgaben (Priorisiert)
- [ ] _vom Bearbeiter zu füllen — aktueller In-Flight-Task_

## Bekannte Probleme / Technical Debt
| Problem | Priorität |
|---|---|
| _keine erfasst — bei Auftreten eintragen_ | — |

## Wichtige Befehle
```bash
# repo-spezifisch ergänzen (siehe project-facts / Makefile)
```
"""


def inject(existing, auto):
    """Auto-Block nach dem H1 (vor der ersten ##-Überschrift) einfügen, Rest erhalten."""
    m = re.search(r"^## ", existing, re.M)
    cut = m.start() if m else len(existing)
    pre, rest = existing[:cut].rstrip(), existing[cut:]
    body = pre + "\n\n" + INJECT_NOTE + "\n\n" + auto
    return body + ("\n\n" + rest if rest.strip() else "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_path", nargs="?", default=".")
    ap.add_argument("--ref", default=None, help="Git-Ref für Anker (z. B. origin/main); read-only, kein Working-Tree")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true", help="Bestandsdatei mit frischer Vorlage ÜBERSCHREIBEN (Bestand verworfen)")
    ap.add_argument("--no-orchestrator", action="store_true")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.repo_path)
    today = args.date or datetime.date.today().isoformat()
    repo_name, auto = build_auto(root, today, args.no_orchestrator, args.ref)

    target = os.path.join(root, "docs", "AGENT_HANDOVER.md")
    existing = open(target, encoding="utf-8").read() if os.path.isfile(target) else None

    if args.force or not existing:
        new = HEADER.format(repo_name=repo_name) + auto + HUMAN_DEFAULT
        mode = "überschrieben (--force, Bestand verworfen)" if existing else "neu erstellt"
    elif AUTO_START in existing and AUTO_END in existing:
        new = re.sub(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END), lambda m: auto, existing, flags=re.S)
        mode = "aktualisiert (Auto-Block ersetzt, Hand-Abschnitte erhalten)"
    else:
        new = inject(existing, auto)
        mode = "Anker-Block injiziert (Bestandsdokument erhalten)"

    if args.write:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write(new)
        sys.stderr.write("{0}: {1}\n".format(mode, target))
    else:
        sys.stderr.write("[Dry-Run] würde {0}: {1}\n".format(mode, target))
        print(new)


if __name__ == "__main__":
    main()
