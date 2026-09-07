#!/usr/bin/env python3
"""future_readiness_evidence.py — Evidenzpaket (T0/T1) fuer EIN Repo, deterministisch aus Arbeitskopie + GitHub-API.

Artefakt 1 („EVIDENZPAKET") des Prompts docs/prompts/future-readiness-audit.md (v2.4): SHA-gebunden,
JSON-Listen, Pflicht-Tabelle je Workflow, Operanden je Frage, Negativliste je Frage. Der deterministische
Bewerter (tools/future_readiness_score.py) liest genau dieses Format; ein Modell-Worker bekommt es als
Markdown-Rendering (`--md`).

    python3 tools/future_readiness_evidence.py achimdehnert/platform ~/github/platform --out /tmp/fr/platform
    python3 tools/future_readiness_evidence.py achimdehnert/aifw <worktree> --out DIR --t2 t2.txt --md

Anlass: platform#2736 (Canary 3 baute das Paket ad hoc; Zaehler liefen auseinander). Keine Secrets:
Werte hinter PASSWORD=/TOKEN=/SECRET= werden vor dem Schreiben redigiert.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

import yaml

OWN_ORGS = ("achimdehnert", "iilgmbh", "ttz-lif", "meiki-lra")
SHA40 = re.compile(r"@[0-9a-f]{40}$")
REDACT = re.compile(r"((?:PASSWORD|TOKEN|SECRET|API_KEY)\s*[=:]\s*)[^\s\"'\\]+", re.I)

# D10-Ausbau (Auftrag 2026-09-07, platform#2944): begrenzte, redigierte Struktur je
# Agent-Instruktionsdatei (CLAUDE.md/AGENTS.md) fuer D10.2-D10.6. Es wird NIE der
# Volltext uebernommen — nur Ueberschriften, die erste Zeile jedes Codeblocks (der
# Befehl) und Zeilen mit den vier Markern unten. Summe aller uebernommenen Zeilen ist
# auf AGENT_DOC_LINE_CAP gedeckelt (Prioritaet: Ueberschriften vor Befehlen vor Markern);
# wird gedeckelt, steht "capped": true im Datensatz.
AGENT_DOC_LINE_CAP = 200
AGENT_DOC_HEADING_RE = re.compile(r"^#{1,6} ")
AGENT_DOC_MARKERS = {
    # D10.3 — verbotene Pfade/Aktionen ("NIE anfassen", "do not touch", ...)
    #
    # Die Frage lautet "verbotene PFADE benannt", nicht "irgendwo steht nie".
    # "nie" und "verboten" sind Alltagswoerter: "wir haben nie Tests geschrieben"
    # wuerde sonst als benannter verbotener Pfad zaehlen — ein falsches Gruen in
    # genau dem Werkzeug, das Selbsttaeuschung aufdecken soll. Der Treffer muss
    # deshalb in derselben Zeile ein pfadartiges Zeichen tragen: Backtick,
    # Schraegstrich, Dateiendung oder Platzhalter.
    "verbotene_pfade": re.compile(
        r"(?=.*(?:`|/|\*|\.(?:py|md|ya?ml|json|toml|sh|lock|txt|cfg|ini)\b))"
        r"\b(NIE|NEVER|verboten|forbidden|nicht anfassen|do not (edit|touch|modify))\b",
        re.I,
    ),
    # D10.4 — generierte Dateien, die nicht von Hand editiert werden sollen
    "generierte_dateien": re.compile(
        r"\b(generiert|generated|auto-?generated|nicht manuell (editieren|bearbeiten|"
        r"aendern|ändern)|do not edit)\b",
        re.I,
    ),
    # D10.5 — Definition of Done / Akzeptanzkriterien
    "definition_of_done": re.compile(
        r"\bdefinition of done\b|\bDoD\b|\bakzeptanzkriterien\b|\bfertig ist\b", re.I
    ),
    # D10.6 — Cross-Repo-Vertraege (gemeinsame Schemas/Contracts ueber Repo-Grenzen)
    "cross_repo_vertraege": re.compile(
        r"\bcross-repo\b|\bshared[_-]contracts?\b|\banderen? repos?\b|\bcontract\b",
        re.I,
    ),
}

# Negativliste je Frage (Auftrag D10-Ausbau 2026-09-07, platform#2944): drei
# unterscheidbare Begruendungsklassen statt eines einzigen Pauschalsatzes.
NEG_JUDGMENT_NOTE = (
    "Urteilsfrage, statisch nicht redlich bewertbar — bewusst nicht erhoben "
    "(Entscheid 2026-09-07, platform#2944)"
)
NEG_JUDGMENT_QUESTIONS = [f"D03.{i}" for i in range(1, 7)]
NEG_EXTERNAL_METER_NOTES = {
    "D07.1": (
        "wird ausserhalb gemessen (tools/erreichbarkeit_melder.py), "
        "Anschluss offen — platform#2944"
    ),
    "D07.4": (
        "wird ausserhalb gemessen (tools/alarmweg_probe.py), "
        "Anschluss offen — platform#2944"
    ),
    "D07.6": (
        "wird ausserhalb gemessen (tools/backup_meter.py), "
        "Anschluss offen — platform#2944"
    ),
    "D12.2": (
        "wird ausserhalb gemessen (tools/sync_drift_meter.py), "
        "Anschluss offen — platform#2944"
    ),
    # Korrektur 2026-09-07, zweiter Anlauf: erst hiess es handover_fleet_check.py
    # (misst den Handover-Zustand, nicht Versionsbaender), dann "kein Werkzeug
    # vorhanden". Beides falsch — tools/sharedci/pin_landschaft.py misst genau
    # das: welche shared-ci-Version jedes Repo in welcher Datei pinnt. Uebersehen,
    # weil das Suchmuster nur tools/*.py abdeckte und keine Unterverzeichnisse.
    "D12.1": (
        "wird ausserhalb gemessen (tools/sharedci/pin_landschaft.py), "
        "Anschluss offen — platform#2944"
    ),
}
NEG_NOT_COLLECTED_NOTE = (
    "statisch lesbar, von future_readiness_evidence.py nicht erhoben"
)
NEG_NOT_COLLECTED_QUESTIONS = [
    "D01.4",
    "D02.5",
    "D04.6",
    "D05.3",
    "D05.4",
    "D05.6",
    "D06.9",
    "D06.10",
    "D06.11",
    "D06.12",
    "D07.2",
    "D07.3",
    "D07.5",
    "D08.6",
    "D09.4",
    "D12.3",
]
KEY_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSE",
    "SECURITY.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CORE_CONTEXT.md",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".pre-commit-config.yaml",
    "Makefile",
    "Taskfile.yml",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "uv.lock",
    "poetry.lock",
    "requirements.lock",
    "pdm.lock",
    "Pipfile.lock",
    "package-lock.json",
    ".python-version",
    ".tool-versions",
    "mise.toml",
    ".nvmrc",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "manage.py",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
]
LOCKFILES = [
    "uv.lock",
    "poetry.lock",
    "requirements.lock",
    "pdm.lock",
    "Pipfile.lock",
    "package-lock.json",
]
PIN_FILES = [".python-version", ".tool-versions", "mise.toml", ".nvmrc"]
CI_TOOLS = (
    "ruff",
    "flake8",
    "pylint",
    "eslint",
    "mypy",
    "pyright",
    "tsc",
    "shellcheck",
    "pytest",
    "yamllint",
    "actionlint",
)


def now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sh(cmd: str, cwd: str | None = None) -> dict:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return {
        "cmd": cmd,
        "exit_code": r.returncode,
        "stdout": r.stdout.rstrip("\n"),
        "stderr": r.stderr.strip()[:300],
    }


def gh_api(path: str) -> dict:
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    try:
        body = json.loads(r.stdout) if r.stdout.strip() else None
    except json.JSONDecodeError:
        body = r.stdout[:500]
    return {
        "endpoint": path,
        "exit_code": r.returncode,
        "body": body,
        "stderr": r.stderr.strip()[:200],
    }


def uses_in(path: str) -> list[str]:
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.search(r"uses:\s*([^\s#\"']+)", line)
            if m:
                out.append(m.group(1).rstrip("`"))
    return out


def classify_use(u: str) -> str:
    if u.startswith("./"):
        return "local"
    owner = u.split("/")[0]
    return "first_party" if owner in OWN_ORGS else "third_party"


def manifest_ops(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = [
                ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")
            ]
    except FileNotFoundError:
        return None
    entries = [ln for ln in lines if not ln.startswith("-")]
    versioned = [ln for ln in entries if re.search(r"==|>=|<=|~=|!=|@|===", ln)]
    return {"entries": len(entries), "versioned_entries": len(versioned)}


def _bracket_list_span(text: str, open_idx: int) -> str | None:
    """Inhalt der TOML-Liste, deren `[` bei `open_idx` liegt — quote-bewusst, damit
    ein `]` INNERHALB eines Strings (z. B. `"pkg[extra]"`) die Liste nicht vorzeitig
    schliesst. Gibt None zurueck, wenn keine passende schliessende Klammer folgt."""
    depth, in_str, i = 0, False, open_idx
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '"' and text[i - 1] != "\\":
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i]
        i += 1
    return None


def _toml_list_entries(content: str) -> list[str]:
    """Eintraege einer TOML-Liste als die darin liegenden gequoteten Strings —
    ein Komma INNERHALB eines Eintrags (z. B. `"pkg>=1.0,<2.0"`) trennt nicht."""
    return re.findall(r'"([^"]*)"', content)


def pyproject_ops(root: str) -> dict:
    """`pyproject.toml` → Abhaengigkeits-Operanden fuer D02.1 (Rubrik v2.5).

    Nur mit `[project]`-Tabelle ist die Datei ueberhaupt ein Manifest (eine
    `pyproject.toml`, die ausschliesslich `[tool.*]`/`[build-system]` traegt, ist
    KEIN Manifest — `dependencies` bleibt dann `None`, wie beim fehlenden File).
    `[project.optional-dependencies]`-Extras zaehlen zu `entries`/`versioned_entries`
    mit (dedupliziert ueber Gruppen); eine Extra-Gruppe, die nur eigene Extras
    referenziert (z. B. `all = ["pkg[a,b]"]`), wird uebersprungen (Eintrag beginnt
    mit dem eigenen Paketnamen). Anlass: platform#2737 Frage 2/#2876 — iil-enrichment,
    iil-ingest, nl2cad fuehren alles als Extras, `dependencies` bleibt leer.
    """
    p = os.path.join(root, "pyproject.toml")
    if not os.path.exists(p):
        return {"exists": False}
    txt = open(p, encoding="utf-8", errors="replace").read()
    project_table = bool(re.search(r"^\[project\]", txt, re.M))
    deps_dict = None
    optional_entries = 0
    if project_table:
        name_m = re.search(r'^name\s*=\s*"([^"]+)"', txt, re.M)
        pkg_name = name_m.group(1) if name_m else None
        deps_m = re.search(r"^dependencies\s*=\s*\[", txt, re.M)
        base_entries = []
        if deps_m:
            content = _bracket_list_span(txt, deps_m.end() - 1)
            base_entries = _toml_list_entries(content) if content is not None else []
        opt_block = re.search(
            r"^\[project\.optional-dependencies\]\s*\n(.*?)(?=^\[|\Z)",
            txt,
            re.S | re.M,
        )
        optional_all = []
        if opt_block:
            block = opt_block.group(1)
            for group_m in re.finditer(r"^[A-Za-z0-9_.-]+\s*=\s*\[", block, re.M):
                content = _bracket_list_span(block, group_m.end() - 1)
                if content is None:
                    continue
                for entry in _toml_list_entries(content):
                    if pkg_name and entry.startswith(pkg_name):
                        continue  # eigene Extras-Selbstreferenz, z.B. all = ["pkg[a,b]"]
                    optional_all.append(entry)
        optional_unique = sorted(set(optional_all))
        optional_entries = len(optional_unique)
        all_entries = base_entries + optional_unique
        deps_dict = {
            "entries": len(all_entries),
            "versioned_entries": sum(
                1 for e in all_entries if re.search(r"[=<>~!]", e)
            ),
        }
    return {
        "exists": True,
        "project_table": project_table,
        "requires_python": bool(re.search(r"^requires-python", txt, re.M)),
        "dependencies": deps_dict,
        "optional_entries": optional_entries,
        "head": "\n".join(txt.splitlines()[:25]),
    }


def workflow_table(root: str) -> tuple[list[dict], list[dict]]:
    rows, ci_jobs = [], []
    for w in sorted(glob.glob(os.path.join(root, ".github/workflows/*.y*ml"))):
        rel = os.path.relpath(w, root)
        try:
            y = yaml.safe_load(open(w, encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            rows.append({"path": rel, "yaml_error": str(e)[:120]})
            continue
        on = y.get("on", y.get(True, {}))
        on_keys = (
            list(on.keys())
            if isinstance(on, dict)
            else ([on] if isinstance(on, str) else list(on or []))
        )
        txt = open(w, encoding="utf-8", errors="replace").read()
        uses = uses_in(w)
        third = [u for u in uses if classify_use(u) == "third_party"]
        first = [u for u in uses if classify_use(u) == "first_party"]
        prt = any(k in on_keys for k in ("pull_request_target", "workflow_run"))
        prt_checkout = prt and bool(
            re.search(
                r"ref:\s*\$\{\{\s*github\.event\.(pull_request|workflow_run)\.head", txt
            )
        )
        jobs = y.get("jobs") or {}
        executed = any(
            k in on_keys for k in ("push", "pull_request", "merge_group", "schedule")
        )
        for jn, jd in jobs.items():
            if not isinstance(jd, dict):
                continue
            steps = " ".join(
                str(s.get("run", "")) + " " + str(s.get("uses", ""))
                for s in (jd.get("steps") or [])
                if isinstance(s, dict)
            )
            tools = [t for t in CI_TOOLS if re.search(rf"\b{t}\b", steps)]
            if tools or jd.get("uses"):
                ci_jobs.append(
                    {
                        "workflow": rel,
                        "job": jn,
                        "tools": tools,
                        "calls_reusable": jd.get("uses"),
                        "executed_for_this_repo": executed,
                        "on": on_keys,
                    }
                )
        rows.append(
            {
                "path": rel,
                "on": on_keys,
                "workflow_call": "workflow_call" in on_keys,
                "secrets_or_ssh": bool(
                    re.search(r"secrets\.|ssh-action|scp-action", txt)
                ),
                "top_level_permissions": y.get("permissions"),
                "job_level_permissions": {
                    j: (jd.get("permissions") if isinstance(jd, dict) else None)
                    for j, jd in jobs.items()
                },
                "third_party_uses": third,
                "third_party_sha_pinned": [u for u in third if SHA40.search(u)],
                "first_party_uses": first,
                "first_party_versioned": [
                    u for u in first if not re.search(r"@(main|master|develop)$", u)
                ],
                "pull_request_target_or_workflow_run": prt,
                "pull_request_target_with_checkout_of_pr_head": prt_checkout,
            }
        )
    return rows, ci_jobs


def agent_doc_digest(root: str, name: str) -> dict:
    """Begrenzte, redigierte Struktur EINER Agent-Instruktionsdatei (D10.2-D10.6).

    Nimmt nie den Volltext auf: nur alle Ueberschriften (Ebene 1-6), die erste Zeile
    jedes Codeblocks (das ist der dokumentierte Befehl) und Zeilen mit den Markern aus
    AGENT_DOC_MARKERS. Die Summe der uebernommenen Zeilen ist auf AGENT_DOC_LINE_CAP
    gedeckelt (Ueberschriften zuerst, dann Befehle, dann Marker); wird gedeckelt, traegt
    das Ergebnis "capped": true.
    """
    with open(os.path.join(root, name), encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    headings = [ln for ln in lines if AGENT_DOC_HEADING_RE.match(ln)]
    command_lines: list[str | None] = []
    in_block = False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_block = not in_block
            if in_block:
                command_lines.append(None)
            continue
        if in_block and command_lines and command_lines[-1] is None:
            command_lines[-1] = ln
    code_block_count = len(command_lines)
    command_lines = [ln for ln in command_lines if ln is not None]
    marker_lines = {
        key: [ln for ln in lines if pat.search(ln)]
        for key, pat in AGENT_DOC_MARKERS.items()
    }
    # Deckel ueber alle Kategorien zusammen, in fester Prioritaet.
    ordered = (
        [("headings", ln) for ln in headings]
        + [("command_lines", ln) for ln in command_lines]
        + [(k, ln) for k, v in marker_lines.items() for ln in v]
    )
    capped = len(ordered) > AGENT_DOC_LINE_CAP
    kept = ordered[:AGENT_DOC_LINE_CAP] if capped else ordered
    out_headings: list[str] = []
    out_commands: list[str] = []
    out_markers: dict[str, list[str]] = {k: [] for k in AGENT_DOC_MARKERS}
    for cat, ln in kept:
        red = REDACT.sub(r"\1<redigiert>", ln)
        if cat == "headings":
            out_headings.append(red)
        elif cat == "command_lines":
            out_commands.append(red)
        else:
            out_markers[cat].append(red)
    return {
        "size_lines": len(lines),
        "headings": out_headings,
        "code_block_count": code_block_count,
        "code_block_first_lines": out_commands,
        "marker_lines": out_markers,
        "lines_taken": len(kept),
        "capped": capped,
    }


def collect(repo: str, root: str, t2_file: str | None, lifecycle_source: str) -> dict:
    root = os.path.abspath(root)
    head = sh("git rev-parse HEAD", root)["stdout"]
    db = (
        sh(
            "git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed s#origin/##",
            root,
        )["stdout"]
        or "main"
    )
    pack: dict = {
        "schema": "future-readiness-evidence/1",
        "repo": repo,
        "analyzed_sha": head,
        "default_branch": db,
        "analyzed_at": now_iso(),
        "truncated": False,
        "parts": {},
    }
    P = pack["parts"]
    meta = gh_api(f"repos/{repo}")["body"]
    if isinstance(meta, dict):
        P["repo"] = {
            k: meta.get(k)
            for k in (
                "visibility",
                "archived",
                "fork",
                "default_branch",
                "pushed_at",
                "size",
                "language",
                "security_and_analysis",
                "has_issues",
            )
        }
        P["repo"]["license"] = (meta.get("license") or {}).get("spdx_id")
        # Regel 34 (v2.4): der Kontotyp entscheidet, ob ein fehlender
        # security_and_analysis-Block plan_unavailable oder no_permission bedeutet.
        P["repo"]["owner_type"] = (meta.get("owner") or {}).get("type")
    else:
        P["repo"] = {"error": str(meta)[:200]}
    P["rules_default_branch"] = gh_api(f"repos/{repo}/rules/branches/{db}")["body"]
    prot = gh_api(f"repos/{repo}/branches/{db}/protection")
    P["classic_protection"] = (
        "present"
        if prot["exit_code"] == 0
        else (
            "absent_404"
            if "404" in prot["stderr"] or "Not Found" in prot["stderr"]
            else "error"
        )
    )
    for key, ep in (
        (
            "dependabot_alerts_api",
            f"repos/{repo}/dependabot/alerts?state=open&per_page=1",
        ),
        (
            "code_scanning_api",
            f"repos/{repo}/code-scanning/alerts?state=open&per_page=1",
        ),
        (
            "private_vulnerability_reporting_api",
            f"repos/{repo}/private-vulnerability-reporting",
        ),
    ):
        r = gh_api(ep)
        P[key] = {
            "endpoint": ep,
            "exit_code": r["exit_code"],
            "body_head": str(r["body"])[:200],
            "stderr": r["stderr"],
        }
    # Dateien
    P["files"] = {
        n: ("+" if os.path.exists(os.path.join(root, n)) else "-") for n in KEY_FILES
    }
    tracked = sh("git ls-files", root)["stdout"].splitlines()
    P["requirements_files_tracked"] = [
        p
        for p in tracked
        if re.search(r"(^|/)requirements[^/]*\.txt$", p) and "_ARCHIVED" not in p
    ]
    P["pyproject"] = pyproject_ops(root)
    P["manifests"] = {
        p: manifest_ops(os.path.join(root, p)) for p in P["requirements_files_tracked"]
    }
    P["dependabot_yml"] = sh(
        "grep -E 'package-ecosystem|interval' .github/dependabot.yml 2>/dev/null", root
    )["stdout"]
    P["make_targets"] = sh(
        "grep -oE '^[a-zA-Z_-]+:' Makefile 2>/dev/null | tr -d :", root
    )["stdout"].split()
    P["make_test_target"] = REDACT.sub(
        r"\1<redigiert>",
        sh("grep -n -A8 '^test:' Makefile 2>/dev/null", root)["stdout"],
    )
    P["precommit_hooks"] = sh(
        "grep -E '^\\s*- id:' .pre-commit-config.yaml 2>/dev/null | sed 's/.*id: *//'",
        root,
    )["stdout"].split()
    P["test_files_by_dir"] = sh(
        "find . -name 'test_*.py' -not -path './.*' -not -path './_ARCHIVED/*' -not -path './node_modules/*' | sed 's#/[^/]*$##' | sort | uniq -c | sort -rn",
        root,
    )["stdout"]
    P["test_file_count"] = sum(
        int(ln.split()[0]) for ln in P["test_files_by_dir"].splitlines() if ln.strip()
    )
    pins = sh(
        "grep -rhoE \"python-version: *['\\\"]?[0-9.]+\" .github/workflows/ 2>/dev/null | grep -oE '[0-9]+\\.[0-9]+' | sort | uniq -c",
        root,
    )["stdout"]
    P["python_pins_in_workflows"] = {
        ln.split()[1]: int(ln.split()[0]) for ln in pins.splitlines() if ln.strip()
    }
    P["readme"] = {
        "headings": sh("grep -E '^#{1,2} ' README.md 2>/dev/null | head -15", root)[
            "stdout"
        ].splitlines(),
        "first_paragraph": sh(
            "awk 'NF && !/^#/ && !/^[|>!]/ {print; c++} c>=3 {exit}' README.md 2>/dev/null",
            root,
        )["stdout"],
        "setup_section": sh(
            "grep -inE '^#+ .*(setup|install|quick ?start|einrichtung|getting started)' README.md 2>/dev/null | head -5",
            root,
        )["stdout"],
    }
    P["agent_docs"] = {
        n: agent_doc_digest(root, n)
        for n in ("CLAUDE.md", "AGENTS.md")
        if os.path.exists(os.path.join(root, n))
    }
    P["codeowners"] = sh(
        "grep -vE '^\\s*(#|$)' .github/CODEOWNERS 2>/dev/null | head -20", root
    )["stdout"].splitlines()
    P["django"] = os.path.exists(os.path.join(root, "manage.py"))
    # Lifecycle
    eol = sh(f"curl -s {lifecycle_source}/api/python.json")
    try:
        P["endoflife_python"] = [
            {"cycle": d["cycle"], "eol": d["eol"]}
            for d in json.loads(eol["stdout"])[:8]
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        P["endoflife_python"] = {"error": (eol["stderr"] or "parse")[:120]}
    P["endoflife_checked_at"] = now_iso()
    # Workflows
    rows, ci_jobs = workflow_table(root)
    P["workflows_active"] = [r["path"] for r in rows]
    P["workflows_archived_not_executed"] = sorted(
        os.path.relpath(p, root)
        for p in glob.glob(os.path.join(root, ".github/workflows/*/*.y*ml"))
    )
    P["composite_actions"] = sorted(
        os.path.relpath(p, root)
        for p in glob.glob(os.path.join(root, ".github/actions/*/action.yml"))
    )
    P["composite_action_uses"] = {
        os.path.relpath(a, root): uses_in(a)
        for a in glob.glob(os.path.join(root, ".github/actions/*/action.yml"))
    }
    P["workflow_table"] = rows
    P["ci_jobs"] = ci_jobs
    third = [u for r in rows for u in r.get("third_party_uses", [])] + [
        u
        for us in P["composite_action_uses"].values()
        for u in us
        if classify_use(u) == "third_party"
    ]
    first = [u for r in rows for u in r.get("first_party_uses", [])]
    P["uses_summary"] = {
        "third_party_total": len(third),
        "third_party_sha_pinned": sum(1 for u in third if SHA40.search(u)),
        "first_party_total": len(first),
        "first_party_versioned": sum(
            1 for u in first if not re.search(r"@(main|master|develop)$", u)
        ),
    }
    # CI
    runs = gh_api(f"repos/{repo}/actions/runs?branch={db}&per_page=100")["body"]
    runs = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
    by_wf: dict[str, list] = {}
    for r in runs:
        by_wf.setdefault(r.get("path", r["name"]), []).append(
            {
                "conclusion": r["conclusion"],
                "status": r["status"],
                "created_at": r["created_at"],
                "event": r["event"],
            }
        )
    P["ci_runs_by_workflow_path"] = {k: v[:6] for k, v in sorted(by_wf.items())}
    test_wfs = sorted(
        {
            j["workflow"]
            for j in ci_jobs
            if "pytest" in j["tools"] and j["executed_for_this_repo"]
        },
        key=lambda w: (0 if re.search(r"test", os.path.basename(w)) else 1, w),
    )
    P["test_workflows"] = test_wfs
    # T2
    if t2_file:
        with open(t2_file, encoding="utf-8", errors="replace") as fh:
            P["t2_local_run"] = REDACT.sub(r"\1<redigiert>", fh.read())
    # Negativliste (was dieses Werkzeug NICHT erhebt)
    P["negative_list"] = {
        "unverified": {
            **{q: NEG_JUDGMENT_NOTE for q in NEG_JUDGMENT_QUESTIONS},
            **NEG_EXTERNAL_METER_NOTES,
            **{q: NEG_NOT_COLLECTED_NOTE for q in NEG_NOT_COLLECTED_QUESTIONS},
        },
        "not_run_at_depth": {
            "D02.4": "CVE-Scan (Scanner)",
            "D11.3": "Personendaten-Scan (Scanner)",
            "D12.4": "Konsumentenzahl (Flotten-Grep)",
            **(
                {}
                if t2_file
                else {"D04.3": "Tests lokal (T2)", "D09.6": "frisches Setup (T2)"}
            ),
        },
    }
    return pack


def render_md(pack: dict) -> str:
    P = pack["parts"]

    def j(x):
        return "```json\n" + json.dumps(x, ensure_ascii=False, indent=1) + "\n```"

    def t(x):
        return "```text\n" + str(x) + "\n```"

    parts = [
        f"## Evidenzpaket — `{pack['repo']}`, SHA `{pack['analyzed_sha']}`, erhoben {pack['analyzed_at']}\n",
        "Alle Teile an diesen SHA gebunden, `truncated: false`, Listen als JSON-Arrays. Nur `-` bedeutet nachweislich abwesend.\n",
    ]
    order = [
        ("T0 — Repository", "repo"),
        ("T0 — Ruleset Default-Branch", "rules_default_branch"),
        ("T0 — klassischer Branch-Schutz", "classic_protection"),
        (
            "T0 — Sicherheits-Endpunkte",
            [
                "dependabot_alerts_api",
                "code_scanning_api",
                "private_vulnerability_reporting_api",
            ],
        ),
        ("T1 — Dateiexistenz", "files"),
        ("T1 — Manifeste", ["requirements_files_tracked", "pyproject"]),
        ("T1 — Dependabot", "dependabot_yml"),
        ("T1 — Makefile", ["make_targets", "make_test_target"]),
        ("T1 — pre-commit", "precommit_hooks"),
        ("T1 — Tests", ["test_files_by_dir", "test_file_count", "test_workflows"]),
        ("T1 — Python-Pins", "python_pins_in_workflows"),
        ("T1 — Lifecycle", ["endoflife_python", "endoflife_checked_at"]),
        (
            "T1 — README / Agent-Doku / CODEOWNERS",
            ["readme", "agent_docs", "codeowners"],
        ),
        (
            "T1 — Workflows und Actions",
            [
                "workflows_active",
                "workflows_archived_not_executed",
                "composite_actions",
                "composite_action_uses",
                "uses_summary",
            ],
        ),
        ("T1 — Pflicht-Tabelle je Workflow", "workflow_table"),
        ("T1 — CI-Jobs (Operanden D04.4/D04.5)", "ci_jobs"),
        ("T0 — CI-Läufe je Workflow-Pfad", "ci_runs_by_workflow_path"),
        ("T2 — lokaler Lauf", "t2_local_run"),
        ("Negativliste je Frage", "negative_list"),
    ]
    for title, key in order:
        keys = key if isinstance(key, list) else [key]
        data = {k: P.get(k) for k in keys} if len(keys) > 1 else P.get(keys[0])
        if data is None:
            continue
        parts.append(f"### {title}\n" + (t(data) if isinstance(data, str) else j(data)))
    return "\n\n".join(parts) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Future-Readiness Evidenzpaket (T0/T1) fuer ein Repo"
    )
    ap.add_argument("repo", help="owner/repo")
    ap.add_argument("root", help="lokale Arbeitskopie (sauber, auf origin/<default>)")
    ap.add_argument("--out", required=True, help="Ausgabeverzeichnis")
    ap.add_argument("--t2", help="Textdatei mit lokalem make-test-Lauf (T2)")
    ap.add_argument("--md", action="store_true", help="zusaetzlich evidence.md rendern")
    ap.add_argument("--lifecycle-source", default="https://endoflife.date")
    a = ap.parse_args()
    pack = collect(a.repo, a.root, a.t2, a.lifecycle_source)
    os.makedirs(a.out, exist_ok=True)
    raw = json.dumps(pack, ensure_ascii=False, indent=1)
    raw = REDACT.sub(r"\1<redigiert>", raw)
    with open(os.path.join(a.out, "evidence.json"), "w", encoding="utf-8") as fh:
        fh.write(raw)
    if a.md:
        with open(os.path.join(a.out, "evidence.md"), "w", encoding="utf-8") as fh:
            fh.write(render_md(json.loads(raw)))
    us = pack["parts"]["uses_summary"]
    print(
        f"{a.repo} sha={pack['analyzed_sha'][:8]} workflows={len(pack['parts']['workflows_active'])} "
        f"third_party_pinned={us['third_party_sha_pinned']}/{us['third_party_total']} -> {a.out}/evidence.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
