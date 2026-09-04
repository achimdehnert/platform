#!/usr/bin/env python3
"""future_readiness_score.py — deterministischer T1-Bewerter: Evidenzpaket → Worker-Ergebnis (Schema 2.3) ohne Modell.

Setzt Artefakt 2 des Prompts (docs/prompts/future-readiness-audit.md v2.4) fuer alle operanden-getriebenen
Kernfragen in Code um; Urteilsfragen bleiben `unverified` (Negativliste) und koennen von einem Modell-Worker
nachgezogen werden. Rubrik (Fragen, Matrix, Schema) kommt aus tools/future_readiness_rubric.py — eine Quelle.

    python3 tools/future_readiness_score.py DIR/evidence.json --archetype ci-workflow \\
        --criticality high --lifecycle strategic --prod-deploy true --reach true --out DIR/result.json

Ergebnis: schema-valide (tools/future_readiness_rubric.py schema), Schluessel gehasht, calculation vollstaendig.
Anlass: platform#2737 (Canaries 3-5: Modell-Worker ~150-190k Token je Repo; die Regeln sind deterministisch genug
fuer Code — Phase C ueber 56 Repos in Minuten statt Millionen Token).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import future_readiness_rubric as rubric  # noqa: E402

SCORE = {"ok": 5, "partial": 3, "fail": 0}
PARTIAL_NO_FINDING = {"D02.3", "D04.3", "D05.3", "D06.8", "D06.9", "D09.6", "D10.2"} | {
    f"D08.{i}" for i in range(1, 7)
}
BASIC_CONTROLS = {
    "D06.1": "secret_scanning",
    "D06.2": "push_protection",
    "D06.3": "dependabot_alerts",
    "D05.1": "rulesets_default_branch",
}
CONTROL_OF_QUESTION = {
    "D06.1": "secret_scanning",
    "D06.2": "push_protection",
    "D06.3": "dependabot_alerts",
    "D06.4": "dependabot_security_updates",
    "D06.5": "code_scanning",
    "D06.6": "action_pinning",
    "D06.13": "first_party_refs",
    "D06.7": "dangerous_triggers",
    "D06.8": "permissions_top",
    "D06.9": "permissions_job",
    "D06.10": "oidc",
    "D06.11": "sbom_provenance",
    "D06.12": "signing",
    "D05.1": "rulesets_default_branch",
    "D05.2": "rulesets_default_branch",
    "D08.3": "codeowners",
}
QMAP = {q[0]: q for q in rubric.Q}


def round_half_up(x: float, nd: int = 0) -> float:
    f = 10**nd
    return math.floor(x * f + 0.5) / f


class Scorer:
    def __init__(self, pack: dict, a: argparse.Namespace):
        self.pack, self.P, self.a = pack, pack["parts"], a
        self.run_date = dt.date.fromisoformat(a.run_date)
        self.horizon = dt.date.fromisoformat(a.horizon_end)
        self.now = pack["analyzed_at"]
        self.na = {q[0] for q in rubric.Q if a.archetype in q[6]}
        self.neg = self.P.get(
            "negative_list", {"unverified": {}, "not_run_at_depth": {}}
        )
        self.controls: dict[str, dict] = {}
        self.answers: dict[str, dict] = {}

    # ---- Hilfen -----------------------------------------------------------
    def ev(self, kind: str, ref: str) -> dict:
        return {"kind": kind, "ref": ref, "checked_at": self.now, "source": "pack"}

    def answered(
        self,
        qid: str,
        outcome: str,
        ref: str,
        kind: str = "file",
        note: str | None = None,
    ) -> None:
        d = {
            "state": "answered",
            "outcome": outcome,
            "question_score": SCORE[outcome],
            "evidence": [self.ev(kind, ref)],
        }
        if note:
            d["note"] = note
        self.answers[qid] = d

    def open_(self, qid: str, state: str, note: str) -> None:
        self.answers[qid] = {"state": state, "note": note}

    def control(
        self,
        key: str,
        state: str,
        ref: str,
        num: int | None = None,
        den: int | None = None,
    ) -> None:
        c = {
            "state": state,
            "evidence": [self.ev("setting", ref)]
            if state not in ("unknown", "not_applicable")
            else [],
        }
        if num is not None and den:
            c["numerator"], c["denominator"] = num, den
        self.controls[key] = c

    def sec_status(self, key: str) -> str | None:
        sa = (self.P.get("repo") or {}).get("security_and_analysis") or {}
        return (sa.get(key) or {}).get("status")

    def sec_unlesbar(self) -> tuple[str, str]:
        """Regel 34 (v2.4): warum `security_and_analysis` keinen Zustand hergibt.

        Fehlt der Block ganz, entscheidet der Kontotyp des Eigentuemers: bei einem
        PRIVATEN Repo unter einem Personenkonto gibt es die Funktionen im Plan nicht
        (`plan_unavailable`); unter einer Organisation ist der Block da, wenn das Token
        ihn sehen darf — fehlt er dort, ist es ein Rechteproblem (`no_permission`).
        Ohne `owner_type` im Paket bleibt es `unknown` — nicht geraten.
        """
        r = self.P.get("repo") or {}
        if r.get("security_and_analysis") is not None:
            return "unknown", "Block vorhanden, Schluessel fehlt"
        typ = r.get("owner_type")
        if not typ:
            return "unknown", "Block fehlt, owner_type nicht im Paket"
        if r.get("visibility") == "private" and typ == "User":
            return (
                "plan_unavailable",
                "privates Repo eines Personenkontos: nicht im Plan",
            )
        if typ == "Organization":
            return "no_permission", "Org-Repo, Block nicht sichtbar: Recht fehlt"
        return "unknown", f"Block fehlt, owner_type={typ}"

    # ---- Fragen -----------------------------------------------------------
    def evaluate(self) -> None:
        P = self.P
        files = P["files"]
        pins = P.get("python_pins_in_workflows") or {}
        pin_versions = list(pins)
        pin_files_present = [
            n
            for n in (".python-version", ".tool-versions", "mise.toml", ".nvmrc")
            if files.get(n) == "+"
        ]
        # D01
        if pin_versions or P["pyproject"].get("requires_python") or pin_files_present:
            places = (
                sum(pins.values())
                + len(pin_files_present)
                + (1 if P["pyproject"].get("requires_python") else 0)
            )
            outcome = (
                "fail"
                if len(pin_versions) > 1
                else ("ok" if places == 1 else "partial")
            )
            self.answered(
                "D01.1",
                outcome,
                f"python_pins_in_workflows={pins}, pin_files={pin_files_present}, requires_python={P['pyproject'].get('requires_python')}",
                "workflow",
            )
        else:
            self.answered(
                "D01.1",
                "fail",
                "keine Runtime-Version in Workflows, Pin-Dateien oder pyproject",
                "workflow",
            )
        eol = (
            {
                d["cycle"]: d["eol"]
                for d in P.get("endoflife_python", [])
                if isinstance(d, dict)
            }
            if isinstance(P.get("endoflife_python"), list)
            else {}
        )
        cycle = (
            max(pin_versions, key=lambda v: tuple(int(x) for x in v.split(".")))
            if pin_versions
            else None
        )
        if cycle and cycle in eol:
            eol_date = dt.date.fromisoformat(eol[cycle])
            self.answered(
                "D01.2",
                "ok",
                f"endoflife.date python {cycle} eol {eol[cycle]} ({P.get('endoflife_checked_at')})",
                "lifecycle",
            )
            twelve = self.run_date.replace(year=self.run_date.year + 1)
            oc = (
                "ok"
                if eol_date >= self.horizon
                else ("partial" if eol_date >= twelve else "fail")
            )
            self.answered(
                "D01.3",
                oc,
                f"eol {eol[cycle]} vs HORIZON_END {self.horizon} / RUN_DATE+12M {twelve}",
                "lifecycle",
            )
        else:
            self.open_(
                "D01.2",
                "unverified",
                "keine gepinnte Python-Version bzw. Lifecycle-Quelle ohne Treffer",
            )
            self.open_(
                "D01.3", "unverified", "EOL ohne Runtime-Version nicht bestimmbar"
            )
        if files.get("Dockerfile") == "+":
            self.open_(
                "D01.5",
                "unverified",
                "Dockerfile vorhanden, Base-Image-Support nicht erhoben",
            )
        # D02
        mans = {p: self.manifest(p) for p in P.get("requirements_files_tracked", [])}
        pyp = (
            P["pyproject"].get("dependencies") if P["pyproject"].get("exists") else None
        )
        ents = sum(m["entries"] for m in mans.values() if m) + (
            pyp["entries"] if pyp else 0
        )
        vers = sum(m["versioned_entries"] for m in mans.values() if m) + (
            pyp["versioned_entries"] if pyp else 0
        )
        if ents == 0 and not mans and not pyp:
            self.answered(
                "D02.1",
                "fail",
                "kein Manifest (requirements*.txt, pyproject dependencies)",
                "manifest",
            )
        elif ents == 0:
            # Regel 25/30 (v2.4): ein vorhandenes, aber leeres Manifest ist ein Befund,
            # keine Messluecke — 0 versionierte von 0 Eintraegen ist fail.
            self.answered(
                "D02.1",
                "fail",
                f"Manifest vorhanden, aber 0 Eintraege ({sorted(mans)}"
                f"{', pyproject' if pyp else ''})",
                "manifest",
            )
        else:
            self.answered(
                "D02.1",
                "ok" if vers == ents else ("partial" if vers else "fail"),
                f"versioned_entries/entries = {vers}/{ents} ({sorted(mans)}{', pyproject' if pyp else ''})",
                "manifest",
            )
        locks = [
            n
            for n in (
                "uv.lock",
                "poetry.lock",
                "requirements.lock",
                "pdm.lock",
                "Pipfile.lock",
                "package-lock.json",
            )
            if files.get(n) == "+"
        ]
        if not locks:
            self.answered(
                "D02.2",
                "fail",
                "geprueft: uv.lock;poetry.lock;requirements.lock;pdm.lock;pipfile.lock;package-lock.json — keines vorhanden",
                "file",
            )
        else:
            ci_uses_lock = any(
                re.search(
                    r"uv sync|--frozen|pip-sync|poetry install|npm ci|pdm sync",
                    json.dumps(P.get("ci_jobs", [])),
                )
                for _ in [0]
            )
            self.answered(
                "D02.2",
                "ok" if ci_uses_lock else "partial",
                f"Lockfile {locks}; CI-Nutzung {'belegt' if ci_uses_lock else 'nicht belegt'}",
                "file",
            )
        dep = P.get("dependabot_yml") or ""
        eco = set(re.findall(r'package-ecosystem: *"?([a-z-]+)', dep))
        need = (
            {"github-actions"}
            | ({"pip"} if (mans or pyp) else set())
            | ({"npm"} if files.get("package-lock.json") == "+" else set())
        )
        if not eco:
            self.answered("D02.3", "fail", "keine .github/dependabot.yml", "file")
        else:
            self.answered(
                "D02.3",
                "ok" if need <= eco else "partial",
                f"ecosystems={sorted(eco)} benoetigt={sorted(need)}",
                "file",
            )
        # D04
        n = P.get("test_file_count", 0)
        self.answered(
            "D04.1",
            "ok" if n > 10 else ("partial" if n else "fail"),
            f"test_*.py Dateien: {n}",
            "file",
        )
        twfs = P.get("test_workflows") or []
        runs = P.get("ci_runs_by_workflow_path") or {}
        if not twfs:
            self.answered(
                "D04.2",
                "fail",
                "kein Workflow mit pytest-Job, der fuer dieses Repo laeuft",
                "workflow",
            )
        else:
            last = next((r for w in twfs for r in runs.get(w, [])[:1]), None)
            if last is None or last["conclusion"] is None:
                self.open_(
                    "D04.2",
                    "unverified",
                    f"Test-Workflow {twfs}: kein abgeschlossener Lauf im Paket",
                )
            else:
                self.answered(
                    "D04.2",
                    "ok" if last["conclusion"] == "success" else "fail",
                    f"{twfs[0]} letzter Lauf {last['conclusion']} {last['created_at']}",
                    "command",
                )
        t2 = P.get("t2_local_run")
        if t2:
            passed, failed = (
                bool(re.search(r"\d+ passed", t2)),
                bool(re.search(r"\d+ failed|FAILED|Fehler|error", t2)),
            )
            self.answered(
                "D04.3",
                "ok" if passed and not failed else ("partial" if passed else "fail"),
                "T2-Abschnitt: make test",
                "command",
            )
            setup_needed = bool(re.search(r"make setup|not found|No such file", t2))
            self.answered(
                "D09.6",
                "ok"
                if passed and not setup_needed
                else ("partial" if passed else "fail"),
                "T2-Abschnitt: frisches Setup",
                "command",
            )
        for qid, tools in (
            ("D04.4", ("ruff", "flake8", "pylint", "eslint", "shellcheck")),
            ("D04.5", ("mypy", "pyright", "tsc")),
        ):
            jobs = [
                j
                for j in P.get("ci_jobs", [])
                if j["executed_for_this_repo"] and set(j["tools"]) & set(tools)
            ]
            if not jobs:
                self.answered(
                    qid,
                    "fail",
                    "kein CI-Job mit " + "/".join(tools) + " (executed_for_this_repo)",
                    "workflow",
                )
            else:
                last = next(
                    (r for j in jobs for r in runs.get(j["workflow"], [])[:1]), None
                )
                self.answered(
                    qid,
                    "ok" if last and last["conclusion"] == "success" else "partial",
                    f"{[(j['workflow'], j['job']) for j in jobs]} letzter Lauf {last['conclusion'] if last else '?'}",
                    "workflow",
                )
        # D05
        rules = P.get("rules_default_branch") or []
        rtypes = [r.get("type") for r in rules if isinstance(r, dict)]
        req = next(
            (
                r
                for r in rules
                if isinstance(r, dict) and r.get("type") == "required_status_checks"
            ),
            None,
        )
        if req:
            ctx = [
                c.get("context", "")
                for c in req["parameters"].get("required_status_checks", [])
            ]
            has_test = any(re.search(r"test|pytest", c, re.I) for c in ctx)
            has_sec = any(
                re.search(r"gitleaks|secret|security|codeql|guardian", c, re.I)
                for c in ctx
            )
            self.answered(
                "D05.1",
                "ok" if has_test and has_sec else "partial",
                f"required_status_checks={ctx}",
                "setting",
            )
            self.control(
                "rulesets_default_branch",
                "enabled",
                "rules/branches: " + ",".join(rtypes),
            )
        else:
            self.answered(
                "D05.1",
                "fail",
                f"kein required_status_checks im Ruleset (rules={rtypes}, classic={P.get('classic_protection')})",
                "setting",
            )
            self.control(
                "rulesets_default_branch",
                "disabled" if not rtypes else "partial",
                f"rules={rtypes}",
                0 if not rtypes else len(rtypes),
                1 if not rtypes else len(rtypes) + 1,
            )
        pr = next(
            (
                r
                for r in rules
                if isinstance(r, dict) and r.get("type") == "pull_request"
            ),
            None,
        )
        if pr:
            cnt = pr["parameters"].get("required_approving_review_count", 0)
            co = pr["parameters"].get("require_code_owner_review", False)
            self.answered(
                "D05.2",
                "ok" if cnt >= 1 else ("partial" if co else "fail"),
                f"required_approving_review_count={cnt} require_code_owner_review={co}",
                "setting",
            )
        else:
            self.answered(
                "D05.2",
                "fail",
                f"keine pull_request-Regel im Ruleset (rules={rtypes})",
                "setting",
            )
        red = [
            w
            for w, rs in runs.items()
            if len(rs) >= 3 and all(r["conclusion"] == "failure" for r in rs[:3])
        ]
        if red:
            self.answered(
                "D05.5",
                "partial" if self.a.prior_art_dauerrot else "fail",
                f"dauerrot (>=3 failures in Folge): {red}",
                "command",
            )
        else:
            self.answered(
                "D05.5",
                "ok",
                "kein Workflow mit >=3 failures in Folge auf dem Default-Branch",
                "command",
            )
        # D06 Einstellungen
        for qid, key in (
            ("D06.1", "secret_scanning"),
            ("D06.2", "secret_scanning_push_protection"),
            ("D06.4", "dependabot_security_updates"),
        ):
            st = self.sec_status(key)
            ck = CONTROL_OF_QUESTION[qid]
            if st in ("enabled", "disabled"):
                self.answered(
                    qid,
                    "ok" if st == "enabled" else "fail",
                    f"security_and_analysis.{key}={st}",
                    "setting",
                )
                self.control(ck, st, f"security_and_analysis.{key}")
            else:
                zustand, grund = self.sec_unlesbar()
                self.open_(
                    qid,
                    "unverified",
                    f"security_and_analysis.{key} nicht lesbar ({grund})",
                )
                self.control(ck, zustand, "")
        da = P.get("dependabot_alerts_api", {})
        if da.get("exit_code") == 0:
            self.answered("D06.3", "ok", "GET dependabot/alerts 200", "setting")
            self.control("dependabot_alerts", "enabled", da["endpoint"])
        elif "disabled" in (da.get("body_head", "") + da.get("stderr", "")):
            self.answered(
                "D06.3",
                "fail",
                "GET dependabot/alerts: 'Dependabot alerts are disabled'",
                "setting",
            )
            self.control("dependabot_alerts", "disabled", da["endpoint"])
        else:
            self.open_(
                "D06.3",
                "unverified",
                f"dependabot/alerts: exit {da.get('exit_code')} {da.get('stderr', '')[:80]}",
            )
            self.control(
                "dependabot_alerts",
                "no_permission" if "403" in da.get("stderr", "") else "unknown",
                "",
            )
        cs = P.get("code_scanning_api", {})
        sarif = any(
            "upload-sarif" in u
            for r in P.get("workflow_table", [])
            for u in r.get("third_party_uses", [])
        )
        if cs.get("exit_code") == 0:
            self.answered("D06.5", "ok", "GET code-scanning/alerts 200", "setting")
            self.control("code_scanning", "enabled", cs["endpoint"])
        elif "no analysis found" in (cs.get("body_head", "") + cs.get("stderr", "")):
            self.answered(
                "D06.5",
                "partial" if sarif else "fail",
                f"'no analysis found'; upload-sarif im Repo: {sarif}",
                "setting",
            )
            self.control(
                "code_scanning",
                "configured_no_analysis" if sarif else "disabled",
                cs["endpoint"],
            )
        else:
            self.open_(
                "D06.5",
                "unverified",
                f"code-scanning: exit {cs.get('exit_code')} {cs.get('stderr', '')[:80]}",
            )
            self.control("code_scanning", "unknown", "")
        us = P.get("uses_summary", {})
        if us.get("third_party_total", 0) == 0:
            self.open_(
                "D06.6",
                "not_applicable" if not P.get("workflows_active") else "unverified",
                "keine Third-Party-Actions in aktiven Workflows",
            )
            self.control("action_pinning", "not_applicable", "")
        else:
            n, d = us["third_party_sha_pinned"], us["third_party_total"]
            oc = "ok" if n == d else ("partial" if n else "fail")
            self.answered(
                "D06.6", oc, f"third_party sha_pinned/total = {n}/{d}", "workflow"
            )
            self.control(
                "action_pinning",
                "enabled"
                if oc == "ok"
                else ("partial" if oc == "partial" else "disabled"),
                "uses_summary",
                n,
                d,
            )
        prt_rows = [
            r
            for r in P.get("workflow_table", [])
            if r.get("pull_request_target_or_workflow_run")
        ]
        num = sum(
            1 for r in prt_rows if r.get("pull_request_target_with_checkout_of_pr_head")
        )
        self.answered(
            "D06.7",
            "ok" if num == 0 else "fail",
            f"Trigger pull_request_target/workflow_run: {len(prt_rows)} Workflows, mit PR-Head-Checkout: {num}",
            "workflow",
        )
        self.control(
            "dangerous_triggers",
            "enabled" if num == 0 else "disabled",
            "workflow_table",
            num,
            max(len(prt_rows), 1),
        )
        wt = [r for r in P.get("workflow_table", []) if "yaml_error" not in r]
        if wt:
            top = sum(1 for r in wt if r.get("top_level_permissions") is not None)
            ratio = top / len(wt)
            self.answered(
                "D06.8",
                "ok" if ratio == 1 else ("partial" if ratio > 0.5 else "fail"),
                f"top-level permissions gesetzt: {top}/{len(wt)}",
                "workflow",
            )
            self.control(
                "permissions_top",
                "enabled" if ratio == 1 else ("partial" if ratio else "disabled"),
                "workflow_table",
                top,
                len(wt),
            )
            self.control("permissions_job", "unknown", "")
        if us.get("first_party_total", 0):
            n, d = us["first_party_versioned"], us["first_party_total"]
            oc = "ok" if n == d else ("partial" if n else "fail")
            self.answered(
                "D06.13", oc, f"first_party versioned/total = {n}/{d}", "workflow"
            )
            self.control(
                "first_party_refs",
                "enabled"
                if oc == "ok"
                else ("partial" if oc == "partial" else "disabled"),
                "uses_summary",
                n,
                d,
            )
        else:
            self.open_(
                "D06.13",
                "unverified" if "D06.13" not in self.na else "not_applicable",
                "keine First-Party-Referenzen",
            )
            self.control("first_party_refs", "not_applicable", "")
        for k in ("oidc", "sbom_provenance", "signing"):
            self.control(
                k,
                "unknown"
                if k == "oidc"
                else (
                    "not_applicable"
                    if self.a.archetype in ("ci-workflow", "docs")
                    else "unknown"
                ),
                "",
            )
        # D08 / D09 / D10 / D11
        rm = P.get("readme", {})
        if files.get("README.md") == "+":
            self.answered(
                "D08.1",
                "ok" if rm.get("first_paragraph") else "fail",
                "README erster Absatz"
                + (" vorhanden" if rm.get("first_paragraph") else " leer"),
                "file",
            )
            self.answered(
                "D08.2",
                "ok" if rm.get("setup_section") else "fail",
                f"README Setup-Abschnitt: {rm.get('setup_section') or 'keiner'}",
                "file",
            )
        else:
            self.answered("D08.1", "fail", "README.md fehlt", "file")
            self.answered("D08.2", "fail", "README.md fehlt", "file")
        for qid, name in (
            ("D08.3", ".github/CODEOWNERS"),
            ("D08.4", "SECURITY.md"),
            ("D08.5", "CHANGELOG.md"),
            ("D11.1", "LICENSE"),
        ):
            self.answered(
                qid,
                "ok" if files.get(name) == "+" else "fail",
                f"{name} {'vorhanden' if files.get(name) == '+' else 'abwesend'}",
                "file",
            )
        self.control(
            "codeowners",
            "enabled" if files.get(".github/CODEOWNERS") == "+" else "disabled",
            ".github/CODEOWNERS",
        )
        self.answered(
            "D09.1",
            "ok"
            if files.get("Makefile") == "+" or files.get("Taskfile.yml") == "+"
            else "fail",
            "Makefile/Taskfile.yml",
            "file",
        )
        pins_local = pin_files_present + (
            ["pyproject:requires-python"]
            if P["pyproject"].get("requires_python")
            else []
        )
        self.answered(
            "D09.2",
            "ok" if pins_local else "fail",
            f"geprueft .python-version;.tool-versions;mise.toml;.nvmrc;requires-python — vorhanden: {pins_local or 'keine'}",
            "file",
        )
        self.answered(
            "D09.3",
            "ok" if files.get(".env.example") == "+" else "fail",
            ".env.example",
            "file",
        )
        self.answered(
            "D09.5",
            "ok" if files.get(".pre-commit-config.yaml") == "+" else "fail",
            ".pre-commit-config.yaml",
            "file",
        )
        self.answered(
            "D10.1",
            "ok"
            if files.get("CLAUDE.md") == "+" or files.get("AGENTS.md") == "+"
            else "fail",
            "CLAUDE.md/AGENTS.md",
            "file",
        )
        self.answered(
            "D11.2",
            "ok"
            if files.get("NOTICE") == "+" or files.get("THIRD_PARTY_NOTICES.md") == "+"
            else "fail",
            "NOTICE/THIRD_PARTY_NOTICES.md",
            "file",
        )
        # Rest: Matrix, Negativliste, sonst unverified
        for qid in QMAP:
            if qid in self.answers:
                if qid in self.na:
                    self.answers[qid] = {
                        "state": "not_applicable",
                        "note": f"Anwendbarkeitsmatrix {self.a.archetype}",
                    }
                continue
            if qid in self.na:
                self.open_(
                    qid, "not_applicable", f"Anwendbarkeitsmatrix {self.a.archetype}"
                )
            elif qid in self.neg.get("not_run_at_depth", {}):
                self.open_(qid, "not_run_at_depth", self.neg["not_run_at_depth"][qid])
            else:
                self.open_(
                    qid,
                    "unverified",
                    self.neg.get("unverified", {}).get(
                        qid, "vom Bewerter nicht erhoben"
                    ),
                )

    def manifest(self, p: str) -> dict | None:
        return (self.P.get("manifests") or {}).get(p)

    # ---- Aggregation --------------------------------------------------------
    def build(self) -> dict:
        self.evaluate()
        W = {d: w for d, (_, w) in rubric.DIMS.items()}
        scores, cov_by = {}, {}
        override = {}
        for d in rubric.DIMS:
            qids = [q[0] for q in rubric.Q if q[0].startswith(d + ".")]
            qs = {q: self.answers[q] for q in qids}
            appl = [q for q in qids if qs[q]["state"] != "not_applicable"]
            ans = [
                qs[q]["question_score"] for q in appl if qs[q]["state"] == "answered"
            ]
            if not appl:
                W[d] = 0
                override[d] = {
                    "weight": 0,
                    "reason": f"alle Fragen not_applicable ({self.a.archetype})",
                }
                score, cov = None, None
            else:
                cov = round_half_up(len(ans) / len(appl), 4)
                score = (
                    int(round_half_up(sum(ans) / len(ans)))
                    if len(ans) >= 0.5 * len(appl)
                    else None
                )
            scores[d] = {"score": score, "coverage": cov, "questions": qs}
            cov_by[d] = cov
        num = sum(
            W[d] * s["score"] for d, s in scores.items() if s["score"] is not None
        )
        den = sum(W[d] for d, s in scores.items() if s["score"] is not None)
        raw = num / den if den else 0.0
        readiness = int(round_half_up(raw / 5 * 100))
        cn = sum(
            W[d] * s["coverage"]
            for d, s in scores.items()
            if W[d] and s["coverage"] is not None
        )
        cd = sum(W[d] for d, s in scores.items() if W[d] and s["coverage"] is not None)
        coverage = round_half_up(cn / cd, 4) if cd else 0.0
        findings = self.findings()
        p0 = any(f["severity"] == "P0" for f in findings)
        cls = (
            "risk"
            if p0
            else (
                "insufficient-evidence"
                if self.a.depth == "T1" or coverage < 0.8
                else (
                    "risk"
                    if readiness < 50
                    else "modernize"
                    if readiness < 70
                    else "solid"
                    if readiness < 85
                    else "ready"
                )
            )
        )
        conf = (
            "high"
            if coverage >= 0.8 and all(f["confidence"] == "high" for f in findings)
            else ("medium" if coverage >= 0.5 else "low")
        )
        wt = self.P.get("workflow_table", [])
        provider = [
            {
                "path": r["path"],
                "type": "reusable-workflow",
                "external_consumers": "unknown",
            }
            for r in wt
            if r.get("workflow_call")
        ] + [
            {"path": a, "type": "composite-action", "external_consumers": "unknown"}
            for a in self.P.get("composite_actions", [])
        ]
        return {
            "schema_version": rubric.SCHEMA_VERSION,
            "repo": self.pack["repo"],
            "analyzed_sha": self.pack["analyzed_sha"],
            "analyzed_at": self.now,
            "depth": self.a.depth,
            "rubric_version": self.a.rubric_version,
            "run_date": self.a.run_date,
            "horizon_end": self.a.horizon_end,
            "archetype": self.a.archetype,
            "archetype_note": self.a.archetype_note
            or "aus KNOWN/Regel; Bewerter deterministisch",
            "lifecycle": self.a.lifecycle,
            "criticality": {
                "value": self.a.criticality,
                "confidence": "high" if self.a.criticality != "unknown" else "low",
                "source": "KNOWN_CRITICALITY"
                if self.a.criticality != "unknown"
                else "fehlt",
            },
            "data_class": "public"
            if (self.P.get("repo") or {}).get("visibility") == "public"
            else self.a.data_class,
            "scores": scores,
            "weights_override": override,
            "calculation": {
                "weighted_score_sum": num,
                "scored_weight_sum": den,
                "readiness_raw": round_half_up(raw, 4),
                "coverage_by_dimension": cov_by,
                "precision": 4,
                "rounding": "half_up",
            },
            "readiness": readiness,
            "evidence_coverage": coverage,
            "readiness_class": cls,
            "confidence": conf,
            "controls": {
                k: self.controls.get(k, {"state": "unknown", "evidence": []})
                for k in rubric.CONTROL_KEYS
            },
            "findings": sorted(findings, key=lambda f: f["key"]),
            "edges": [],
            "provider_artifacts": sorted(provider, key=lambda p: p["path"]),
            "unknowns": [],
            "underspecified": [],
            "prior_run": None,
            "budget": None,
        }

    def findings(self) -> list[dict]:
        out = []
        wt = self.P.get("workflow_table", [])
        for qid, ans in self.answers.items():
            if (
                ans["state"] != "answered"
                or ans["outcome"] == "ok"
                or (ans["outcome"] == "partial" and qid in PARTIAL_NO_FINDING)
            ):
                continue
            q = QMAP[qid]
            slug, kind = q[1], q[7]
            loc = self.location(qid, kind, ans)
            locator = f"{qid}|{slug}|{loc}"
            key = (
                f"{self.pack['repo']}:{qid.split('.')[0]}:"
                + hashlib.sha256(locator.encode()).hexdigest()[:8]
            )
            sev = "P3" if ans["outcome"] == "partial" else "P2"
            if qid == "D06.6" and any(
                len(r.get("third_party_uses", []))
                > len(r.get("third_party_sha_pinned", []))
                and (r.get("secrets_or_ssh") or r.get("workflow_call"))
                for r in wt
            ):
                sev = "P1"
            if qid == "D01.3" and ans["outcome"] == "fail" and self.a.prod_deploy:
                sev = "P1"
            if (
                qid in BASIC_CONTROLS
                and ans["outcome"] == "fail"
                and self.a.prod_deploy
            ):
                sev = "P1"
            out.append(
                {
                    "key": key,
                    "locator": locator,
                    "locator_kind": kind,
                    "question_id": qid,
                    "finding_type": slug,
                    "delta": "NEW",
                    "prior_art": {
                        "issues": self.a.prior_art.get(slug, []),
                        "adr": None,
                        "konz": None,
                        "known_since": None,
                    },
                    "remediation_prs": [],
                    "konflikt_adr": None,
                    "dimension": qid.split(".")[0],
                    "severity": sev,
                    "confidence": "high",
                    "evidence": ans["evidence"],
                    "observation": f"{q[2]}: {ans['outcome']} — {ans['evidence'][0]['ref']}",
                    "why_it_matters": {
                        "ok": "",
                        "partial": f"Anker partial: {q[4]}",
                        "fail": f"Anker fail: {q[5]}",
                    }[ans["outcome"]],
                    "blast_radius": [self.pack["repo"]],
                    "recommendation": f"Zustand '{q[3]}' herstellen",
                    "alternatives": [],
                    "effort": "S",
                    "blockers": [],
                    "cross_repo_sequence": [],
                    "acceptance": [f"{qid} outcome ok"],
                    "verification": [
                        "tools/future_readiness_evidence.py + future_readiness_score.py erneut"
                    ],
                    "rollback": "Revert",
                    "safe_draft_pr": kind in ("absence", "files")
                    and qid not in BASIC_CONTROLS,
                    "requires_gate": "security-config" if kind == "setting" else "none",
                }
            )
        return out

    def location(self, qid: str, kind: str, ans: dict) -> str:
        files = self.P["files"]
        if kind == "setting":
            return "setting:" + CONTROL_OF_QUESTION.get(qid, qid.lower())
        if kind == "pattern":
            return ".github/workflows#" + QMAP[qid][1]
        if kind == "repo":
            return "repo"
        if kind == "absence":
            names = {
                "D02.2": [
                    "uv.lock",
                    "poetry.lock",
                    "requirements.lock",
                    "pdm.lock",
                    "Pipfile.lock",
                    "package-lock.json",
                ],
                "D08.3": [".github/CODEOWNERS"],
                "D08.4": ["SECURITY.md"],
                "D08.5": ["CHANGELOG.md"],
                "D09.1": ["Makefile", "Taskfile.yml"],
                "D09.2": [
                    ".python-version",
                    ".tool-versions",
                    "mise.toml",
                    ".nvmrc",
                    "pyproject.toml:requires-python",
                ],
                "D09.3": [".env.example"],
                "D09.5": [".pre-commit-config.yaml"],
                "D10.1": ["CLAUDE.md", "AGENTS.md"],
                "D11.1": ["LICENSE"],
                "D11.2": ["NOTICE", "THIRD_PARTY_NOTICES.md"],
            }.get(qid, [])
            return ";".join(sorted(n.lower() for n in names)) or "repo"
        # files
        if qid in ("D04.4", "D04.5"):
            return (
                ";".join(sorted({j["workflow"] for j in self.P.get("ci_jobs", [])}))
                or ".github/workflows"
            )
        if qid == "D05.5":
            return ";".join(
                sorted(
                    w
                    for w, rs in (self.P.get("ci_runs_by_workflow_path") or {}).items()
                    if len(rs) >= 3
                    and all(r["conclusion"] == "failure" for r in rs[:3])
                )
            )
        if qid == "D02.1":
            # Ohne Manifest ist die Trefferliste leer; der Locator braucht aber
            # (Schema 2.3) mindestens ein Zeichen hinter dem dritten `|`. Dann
            # stehen die GEPRUEFTEN Namen drin — wie bei den absence-Fragen oben.
            # Phase C 2026-09-03: 11 von 56 Repos scheiterten daran (#2780).
            return (
                ";".join(
                    sorted(
                        self.P.get("requirements_files_tracked", [])
                        + (
                            ["pyproject.toml"]
                            if self.P["pyproject"].get("exists")
                            else []
                        )
                    )
                ).lower()
                or "pyproject.toml;requirements.txt"
            )
        if qid in ("D08.1", "D08.2"):
            return "readme.md"
        if qid == "D04.1":
            return "tests"
        if qid == "D04.2":
            return ";".join(self.P.get("test_workflows") or []) or ".github/workflows"
        return "repo" if files else "repo"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="deterministischer Future-Readiness-Bewerter (Schema 2.3)"
    )
    ap.add_argument("evidence")
    ap.add_argument("--out", required=True)
    ap.add_argument("--archetype", required=True, choices=rubric.ARCHETYPES)
    ap.add_argument("--archetype-note", default="")
    ap.add_argument(
        "--criticality", default="unknown", choices=["high", "medium", "low", "unknown"]
    )
    ap.add_argument(
        "--lifecycle",
        default="active",
        choices=[
            "strategic",
            "active",
            "maintenance",
            "sunset-planned",
            "archive-candidate",
            "unknown",
        ],
    )
    ap.add_argument(
        "--data-class",
        default="internal",
        choices=["public", "internal", "personal", "gov-citizen", "unknown"],
    )
    ap.add_argument("--prod-deploy", default="false")
    ap.add_argument("--reach", default="false")
    ap.add_argument("--depth", default="T1", choices=["T1", "T2"])
    ap.add_argument("--run-date", default=dt.date.today().isoformat())
    ap.add_argument("--horizon-end", default=None)
    ap.add_argument(
        "--rubric-version",
        default=f"{rubric.SCHEMA_VERSION}-{dt.date.today().isoformat()}",
    )
    ap.add_argument(
        "--prior-art", default="{}", help="JSON {finding_type: [issue-url, ...]}"
    )
    a = ap.parse_args()
    a.prod_deploy = a.prod_deploy.lower() == "true"
    a.reach = a.reach.lower() == "true"
    a.prior_art = json.loads(a.prior_art)
    a.prior_art_dauerrot = bool(a.prior_art.get("dauerrot"))
    if not a.horizon_end:
        rd = dt.date.fromisoformat(a.run_date)
        a.horizon_end = rd.replace(year=rd.year + 3).isoformat()
    with open(a.evidence, encoding="utf-8") as fh:
        pack = json.load(fh)
    result = Scorer(pack, a).build()
    try:
        import jsonschema  # noqa: F401

        errs = list(
            jsonschema.Draft202012Validator(rubric.schema()).iter_errors(result)
        )
        if errs:
            print(
                f"SCHEMA-FEHLER ({len(errs)}): "
                + "; ".join(
                    "/".join(map(str, e.absolute_path)) + ": " + e.message[:80]
                    for e in errs[:5]
                ),
                file=sys.stderr,
            )
            return 2
    except ImportError:
        print("jsonschema nicht installiert — Schema nicht geprueft", file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    sev = {}
    for f in result["findings"]:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print(
        f"{result['repo']} readiness={result['readiness']} coverage={result['evidence_coverage']} class={result['readiness_class']} findings={len(result['findings'])} {sev} -> {a.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
