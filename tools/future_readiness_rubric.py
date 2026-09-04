#!/usr/bin/env python3
"""future_readiness_rubric.py — EINE Quelle fuer Fragenkatalog, Anwendbarkeitsmatrix und JSON-Schema
des Future-Readiness-Worker (docs/prompts/future-readiness-audit.md, ab v2.2; Stand v2.4).

    python3 tools/future_readiness_rubric.py table   # Artefakt 2, Kernfragen (mit locator_kind)
    python3 tools/future_readiness_rubric.py matrix  # Artefakt 2, Anwendbarkeit
    python3 tools/future_readiness_rubric.py schema  # Artefakt 3, JSON Schema
    python3 tools/future_readiness_rubric.py render docs/prompts/future-readiness-audit.md
        # ersetzt die Bloecke zwischen den Markern  <!-- rubric:TABLE -->…<!-- /rubric:TABLE -->
        # (ebenso MATRIX, SCHEMA); idempotent — mehrfaches Rendern aendert nichts
    python3 tools/future_readiness_rubric.py check docs/prompts/future-readiness-audit.md
        # Exit 1, wenn der Prompt nicht dem Generator entspricht (fuer CI/pre-commit)

Ein Rubrik-Edit ohne Neugenerierung ist ungueltig (Anhang des Prompts). Anlass: Canary-Lauf 2
am 2026-09-02, Review C, Blocker 1-7 — Tabelle, Matrix und Schema liefen in v2.1 auseinander.
v2.3 (Canary 3, Review B + interner Lauf): locator_kind je Frage, eindeutige Befundwerte
(D05.2, D06.6, D06.7, D09.2), Frage D06.13 (First-Party-Referenzen), Schema zustandsabhaengig
(oneOf), Zaehler/Nenner Pflicht bei partial, remediation_prs als Liste.
"""

import json
import re
import sys

SCHEMA_VERSION = "2.3"

# Schwelle, ab der eine Dimension in den Score eingeht (Kandidat 37a, Owner-Wort
# 2026-09-04): eine Dimension wird gewertet, wenn MINDESTENS SCORE_MIN_ANSWERED
# Fragen beantwortet sind ODER der Anteil beantworteter an anwendbaren Fragen
# SCORE_MIN_SHARE erreicht. Anlass: bei dev-hub fiel D06 (Gewicht 15) mit 6 von 13
# beantworteten Fragen knapp unter die reine Anteilsschwelle und ging gar nicht in
# den Score ein. Der Bewerter liest beide Werte von hier.
SCORE_MIN_ANSWERED = 3
SCORE_MIN_SHARE = 0.5

DIMS = {
    "D01": ("Runtime-Lifecycle", 10),
    "D02": ("Dependencies/Reproduzierbarkeit", 10),
    "D03": ("Architektur/API/Daten", 12),
    "D04": ("Tests/Codequalitaet", 12),
    "D05": ("CI/CD/Release", 10),
    "D06": ("Security/Supply Chain", 15),
    "D07": ("Betrieb/Resilienz", 8),
    "D08": ("Doku/Ownership", 6),
    "D09": ("Developer Experience", 6),
    "D10": ("Coding-Agent-Readiness", 5),
    "D11": ("Compliance/Lizenz", 3),
    "D12": ("Cross-Repo-Fit", 3),
}
CI, DOCS, PKG, IAC = "ci-workflow", "docs", "python-package", "iac"

#: locator_kind — bestimmt die kanonische Location im Finding-Locator (Artefakt 2):
#:   setting  → "setting:<controls-Schluessel oder API-Feld>"
#:   pattern  → ".github/workflows#<finding_type>"  (aggregierte Verhaeltnisfrage ueber Workflows)
#:   files    → sortierte konkrete Pfade, ";"-verbunden
#:   absence  → sortierte Liste der GEPRUEFTEN Namen (aus dem Paket), ";"-verbunden
#:   repo     → "repo" (repo-weiter Befund ohne Datei, z.B. Lifecycle, Konsumenten)
# (id, slug, frage, ok, partial, fail, n/a-Archetypen, locator_kind)
Q = [
    (
        "D01.1",
        "runtime-version-belegt",
        "Runtime-Version(en) belegt (Grundmenge sind nur exakte Angaben: Workflow-Pin, .python-version, .tool-versions, mise.toml, .nvmrc; eine offene untere Grenze im Manifest wie requires-python >=3.11 ist KEINE Fundstelle und steht nur in der note)",
        "genau eine exakte Version an genau einer Stelle",
        "gleiche exakte Version an mehreren Stellen",
        "widerspruechliche exakte Versionen oder keine exakte Version",
        [DOCS],
        "pattern",
    ),
    (
        "D01.2",
        "eol-datum",
        "EOL-Datum aus LIFECYCLE_SOURCE ermittelt",
        "Datum mit Quelle",
        "-",
        "Quelle liefert nichts (dann unverified)",
        [DOCS],
        "repo",
    ),
    (
        "D01.3",
        "eol-vor-horizont",
        "EOL liegt nach HORIZON_END",
        "EOL >= HORIZON_END",
        "EOL zwischen RUN_DATE+12M und HORIZON_END",
        "EOL < RUN_DATE+12M",
        [DOCS],
        "repo",
    ),
    (
        "D01.4",
        "upgrade-pfad",
        "Upgrade-Pfad dokumentiert",
        "Ziel + Termin dokumentiert",
        "Ziel ohne Termin",
        "nichts",
        [DOCS],
        "repo",
    ),
    (
        "D01.5",
        "base-image",
        "Build-/Base-Image unterstuetzt",
        "Image mit Support-Datum > HORIZON_END",
        "Support-Datum < HORIZON_END",
        "EOL-Image",
        [CI, DOCS, PKG],
        "files",
    ),
    (
        "D02.1",
        "manifest",
        "Abhaengigkeits-Manifest mit Versionsangaben (Operand: versioned_entries/entries je Manifest; [project].dependencies aus pyproject.toml zaehlt als Manifest)",
        "alle Eintraege versioniert",
        "teils versioniert",
        "kein Manifest, nur leere Manifeste (entries == 0) oder 0 versioniert",
        [DOCS],
        "files",
    ),
    (
        "D02.2",
        "lockfile",
        "Lockfile vorhanden und in CI genutzt (uv.lock, poetry.lock, requirements.lock, pdm.lock, Pipfile.lock, package-lock.json; vollstaendig gepinnte requirements*.txt zaehlt NICHT)",
        "Lockfile + CI installiert daraus",
        "Lockfile, CI nutzt es nicht",
        "kein Lockfile",
        [DOCS],
        "absence",
    ),
    (
        "D02.3",
        "update-automation",
        "Dependency-Update-Automation aktiv",
        "Config fuer alle Oekosysteme",
        "Config fuer einen Teil",
        "keine",
        [DOCS],
        "files",
    ),
    (
        "D02.4",
        "cve",
        "bekannte CVEs (Scanner)",
        "0 offen",
        "nur low/medium offen",
        "high/critical offen",
        [DOCS],
        "repo",
    ),
    (
        "D02.5",
        "unmaintained",
        "unmaintained Kernabhaengigkeit",
        "keine",
        "eine mit Ersatzplan",
        "eine ohne Plan",
        [DOCS],
        "repo",
    ),
    (
        "D03.1",
        "modulgrenzen",
        "Modulgrenzen ohne Zyklen",
        "belegt zyklenfrei",
        "Zyklen bekannt und isoliert",
        "Zyklen im Kern",
        [CI, DOCS, IAC],
        "repo",
    ),
    (
        "D03.2",
        "api-versioniert",
        "oeffentliche API/Contract versioniert",
        "Version + Deprecation-Regel",
        "Version ohne Regel",
        "unversioniert",
        [DOCS, IAC],
        "repo",
    ),
    (
        "D03.3",
        "migrationen-additiv",
        "Schema-Migrationen additiv",
        "nur additiv, geprueft",
        "additiv mit Ausnahmen",
        "destruktiv",
        [CI, DOCS, PKG, IAC],
        "files",
    ),
    (
        "D03.4",
        "timeouts-retry",
        "Timeouts und Retry gesetzt",
        "beides",
        "eines",
        "keines",
        [CI, DOCS, IAC],
        "repo",
    ),
    (
        "D03.5",
        "idempotenz",
        "kritische Operationen idempotent",
        "belegt",
        "teilweise",
        "nein",
        [CI, DOCS, IAC],
        "repo",
    ),
    (
        "D03.6",
        "adr-bedarf",
        "offener ADR-Bedarf",
        "keiner",
        "einer, getrackt",
        "einer, ungetrackt",
        [DOCS],
        "repo",
    ),
    (
        "D04.1",
        "testsuite",
        "Testsuite existiert",
        "ja, > 10 Dateien",
        "1-10 Dateien",
        "keine",
        [DOCS],
        "files",
    ),
    (
        "D04.2",
        "tests-in-ci",
        "Testlauf in CI erfolgreich (letzter Lauf des Test-Workflows; das Paket benennt den Pfad des Test-Workflows, auch wenn die Tests ueber einen konsumierten reusable Workflow laufen)",
        "success",
        "in_progress/unbekannt (dann unverified)",
        "failure oder kein Test-Workflow",
        [DOCS],
        "files",
    ),
    (
        "D04.3",
        "tests-lokal",
        "Tests lokal ausgefuehrt (T2)",
        "gruen",
        "teilweise rot, dokumentiert",
        "rot",
        [DOCS],
        "repo",
    ),
    (
        "D04.4",
        "lint-in-ci",
        "Code-Linter (ruff/eslint/shellcheck o.ae.) laeuft in CI FUER DIESES REPO (Operand executed_for_this_repo=true; ein nur exportierter workflow_call zaehlt nicht; Konfig-Linter wie yamllint zaehlen nicht)",
        "ja, letzter Lauf success",
        "Job vorhanden, letzter Lauf nicht success",
        "nein",
        [DOCS],
        "files",
    ),
    (
        "D04.5",
        "typen-in-ci",
        "Typpruefung (mypy/pyright/tsc) laeuft in CI FUER DIESES REPO (Operand wie D04.4)",
        "ja, letzter Lauf success",
        "Job vorhanden, letzter Lauf nicht success",
        "nein",
        [DOCS, IAC],
        "files",
    ),
    (
        "D04.6",
        "kritischer-pfad",
        "kritischer Pfad getestet",
        "belegt",
        "teilweise",
        "ungetestet",
        [DOCS],
        "repo",
    ),
    (
        "D05.1",
        "required-checks",
        "Required Checks im Ruleset des Default-Branch",
        "Tests + Security als Required",
        "nur ein Check",
        "keine",
        [],
        "setting",
    ),
    (
        "D05.2",
        "review-pflicht",
        "Ruleset mit Review-Pflicht (Operand: required_approving_review_count, require_code_owner_review)",
        "required_approving_review_count >= 1",
        "count == 0 UND require_code_owner_review == true",
        "beides nicht gesetzt",
        [],
        "setting",
    ),
    (
        "D05.3",
        "release-automatisiert",
        "Release/Deploy automatisiert (einmalige Bereitstellungs-Workflows ohne wiederkehrenden Trigger, also nur workflow_dispatch, sind manuelle Schritte)",
        "vollstaendig, wiederkehrender Trigger",
        "mit manuellen Schritten (auch: nur workflow_dispatch), dokumentiert",
        "manuell",
        [DOCS],
        "files",
    ),
    (
        "D05.4",
        "rollback",
        "Rollback-Weg belegt",
        "dokumentiert + geprobt",
        "dokumentiert",
        "keiner",
        [DOCS],
        "repo",
    ),
    (
        "D05.5",
        "dauerrot",
        "Workflow auf Default-Branch dauerhaft rot (>= 3 Laeufe in Folge; Laufserien je Workflow-PFAD geschluesselt, nicht je Name, mit Zeitraum im Paket)",
        "keiner",
        "einer, mit Anker/Issue",
        "einer ohne Anker",
        [],
        "files",
    ),
    (
        "D05.6",
        "shared-ci-drift",
        "Drift zu shared-ci",
        "aktuelles Band",
        "ein Band zurueck",
        "> 1 Band oder kein shared-ci",
        [DOCS],
        "repo",
    ),
    (
        "D06.1",
        "secret-scanning",
        "Secret Scanning",
        "enabled",
        "-",
        "disabled",
        [],
        "setting",
    ),
    (
        "D06.2",
        "push-protection",
        "Push Protection",
        "enabled",
        "-",
        "disabled",
        [],
        "setting",
    ),
    (
        "D06.3",
        "dependabot-alerts",
        "Dependabot-Alerts (BASIC_SECURITY_CONTROL)",
        "enabled",
        "-",
        "disabled",
        [],
        "setting",
    ),
    (
        "D06.4",
        "dependabot-security-updates",
        "Dependabot Security Updates",
        "enabled",
        "-",
        "disabled",
        [],
        "setting",
    ),
    (
        "D06.5",
        "code-scanning",
        "Code Scanning",
        "enabled mit Analyse",
        "configured_no_analysis",
        "disabled/kein Setup",
        [DOCS],
        "setting",
    ),
    (
        "D06.6",
        "action-pinning",
        "SHA-Pinning von THIRD-PARTY-Actions (uses-Ziel weder eigenes Repo noch eigene Orgs; Operand: sha_pinned/third_party gesamt; Begriff: unpinned = ohne SHA)",
        "100 %",
        "> 0 % und < 100 %",
        "0 %",
        [],
        "pattern",
    ),
    (
        "D06.7",
        "gefaehrliche-trigger",
        "pull_request_target/workflow_run mit Checkout von PR-Code (Operand: numerator = Workflows mit solchem Trigger UND Checkout des PR-Heads)",
        "numerator == 0",
        "-",
        "numerator > 0",
        [],
        "pattern",
    ),
    (
        "D06.8",
        "permissions-top",
        "Top-Level permissions: gesetzt",
        "alle Workflows",
        "> 50 %",
        "<= 50 %",
        [],
        "pattern",
    ),
    (
        "D06.9",
        "permissions-job",
        "Job-Level permissions least-privilege",
        "belegt",
        "Vorkommen gezaehlt, Werte nicht bewertet (unverified)",
        "write ohne Bedarf",
        [],
        "pattern",
    ),
    (
        "D06.10",
        "oidc",
        "kurzlebige Identitaeten statt Token",
        "OIDC ueberall",
        "teils",
        "nur Token",
        [DOCS],
        "pattern",
    ),
    (
        "D06.11",
        "sbom-provenance",
        "SBOM/Provenance",
        "beides",
        "eines",
        "keines",
        [CI, DOCS],
        "repo",
    ),
    (
        "D06.12",
        "signierung",
        "Artefakt-Signierung",
        "ja",
        "-",
        "nein",
        [CI, DOCS],
        "repo",
    ),
    (
        "D06.13",
        "first-party-refs-versioniert",
        "Referenzen auf eigene Repos/Orgs (reusable workflows, composite actions) tragen Tag oder SHA statt @main (Operand: versioned/first_party gesamt; Begriff: unversioned = @main/Branch, getrennt von unpinned aus D06.6)",
        "100 %",
        "> 0 % und < 100 %",
        "0 %",
        [DOCS],
        "pattern",
    ),
    (
        "D07.1",
        "health",
        "Health-Endpunkt (Beleg: Route/URL-Muster ODER View/Handler im Code; eine blosse Erwaehnung in der Doku genuegt nicht)",
        "Route oder Handler im Code belegt",
        "-",
        "nur Doku-Erwaehnung oder nichts",
        [CI, DOCS, PKG, IAC],
        "repo",
    ),
    (
        "D07.2",
        "logs",
        "strukturierte Logs",
        "ja",
        "unstrukturiert",
        "keine",
        [CI, DOCS, PKG, IAC],
        "repo",
    ),
    ("D07.3", "metriken", "Metriken", "ja", "-", "nein", [CI, DOCS, PKG, IAC], "repo"),
    ("D07.4", "alarmweg", "Alarmweg belegt", "ja", "-", "nein", [DOCS, PKG], "repo"),
    ("D07.5", "runbook", "Runbook", "ja", "veraltet", "keines", [DOCS, PKG], "files"),
    (
        "D07.6",
        "backup-restore",
        "Backup/Restore belegt",
        "geprobt",
        "dokumentiert",
        "nichts",
        [CI, DOCS, PKG],
        "repo",
    ),
    (
        "D08.1",
        "readme-zweck",
        "README nennt Zweck (Operand: erster Absatz im Paket)",
        "ja",
        "-",
        "nein",
        [],
        "files",
    ),
    (
        "D08.2",
        "readme-setup",
        "README nennt Setup-Weg (Operand: Setup-Abschnitt im Paket)",
        "ja",
        "-",
        "nein",
        [DOCS],
        "files",
    ),
    ("D08.3", "codeowners", "CODEOWNERS", "ja", "-", "nein", [], "absence"),
    ("D08.4", "security-md", "SECURITY.md", "ja", "-", "nein", [], "absence"),
    ("D08.5", "changelog", "CHANGELOG", "ja", "-", "nein", [], "absence"),
    (
        "D08.6",
        "einschraenkungen",
        "bekannte Einschraenkungen dokumentiert",
        "ja",
        "-",
        "nein",
        [],
        "repo",
    ),
    (
        "D09.1",
        "einstiegsbefehl",
        "ein Einstiegsbefehl (make/Taskfile)",
        "ja",
        "-",
        "nein",
        [DOCS],
        "absence",
    ),
    (
        "D09.2",
        "tool-versionen",
        "LOKALE Developer-Toolchain gepinnt: .python-version, .tool-versions, mise.toml, .nvmrc oder requires-python in pyproject (CI-Pins zaehlen NICHT; Paket listet die geprueften Namen)",
        "ja",
        "-",
        "nein",
        [DOCS],
        "absence",
    ),
    (
        "D09.3",
        "env-example",
        "Beispiel-Env-Datei",
        "ja",
        "-",
        "nein",
        [CI, DOCS, PKG],
        "absence",
    ),
    (
        "D09.4",
        "beispiele-sicher",
        "Beispieldateien ohne echte Werte",
        "ja",
        "-",
        "nein",
        [DOCS],
        "repo",
    ),
    ("D09.5", "pre-commit", "pre-commit", "ja", "-", "nein", [DOCS], "absence"),
    (
        "D09.6",
        "frisches-setup",
        "frisches Setup gelaufen (T2)",
        "gruen",
        "mit Handarbeit",
        "rot",
        [DOCS],
        "repo",
    ),
    (
        "D10.1",
        "agent-datei",
        "Agent-Instruktionsdatei (CLAUDE.md/AGENTS.md)",
        "ja",
        "-",
        "nein",
        [],
        "absence",
    ),
    (
        "D10.2",
        "agent-befehle",
        "verifizierte Befehle darin",
        "ja",
        "documented, nicht verified",
        "keine",
        [],
        "repo",
    ),
    (
        "D10.3",
        "verbotene-pfade",
        "verbotene Pfade benannt",
        "ja",
        "-",
        "nein",
        [],
        "repo",
    ),
    (
        "D10.4",
        "generierte-dateien",
        "generierte Dateien benannt",
        "ja",
        "-",
        "nein",
        [DOCS],
        "repo",
    ),
    ("D10.5", "dod", "Definition of Done", "ja", "-", "nein", [], "repo"),
    (
        "D10.6",
        "cross-repo-vertraege",
        "Cross-Repo-Vertraege benannt",
        "ja",
        "-",
        "nein",
        [DOCS],
        "repo",
    ),
    ("D11.1", "lizenz", "Lizenz", "ja", "-", "nein", [], "absence"),
    (
        "D11.2",
        "third-party-notices",
        "Third-Party-Notices",
        "ja",
        "-",
        "nein",
        [DOCS],
        "absence",
    ),
    (
        "D11.3",
        "beispieldaten-personenfrei",
        "Beispieldaten personenfrei",
        "belegt (Scanner)",
        "-",
        "Fund",
        [],
        "repo",
    ),
    (
        "D12.1",
        "shared-ci-band",
        "shared-ci-Band aktuell (identisch mit D05.6 zu behandeln)",
        "ja",
        "ein Band zurueck",
        "nein",
        [DOCS],
        "repo",
    ),
    (
        "D12.2",
        "kopierte-standards",
        "kopierte Workflows/Dockerfiles",
        "keine",
        "mit Drift-Melder",
        "ohne",
        [DOCS],
        "repo",
    ),
    (
        "D12.3",
        "unabhaengig-releasbar",
        "unabhaengig releasbar: Release-Trigger liegt im Repo und haengt von keinem Fremd-Workflow @main ab",
        "ja",
        "-",
        "nein",
        [DOCS],
        "repo",
    ),
    (
        "D12.4",
        "konsumentenzahl",
        "Konsumentenzahl gemessen (Flotten-Grep)",
        "gemessen",
        "-",
        "-",
        [],
        "repo",
    ),
]
ARCHETYPES = [
    "django-app",
    "python-package",
    "iac",
    "ci-workflow",
    "docs",
    "template",
    "experiment",
    "legacy",
    "archive-candidate",
    "other",
]
CONTROL_KEYS = [
    "secret_scanning",
    "push_protection",
    "dependabot_alerts",
    "dependabot_security_updates",
    "code_scanning",
    "action_pinning",
    "first_party_refs",
    "dangerous_triggers",
    "permissions_top",
    "permissions_job",
    "oidc",
    "sbom_provenance",
    "signing",
    "rulesets_default_branch",
    "codeowners",
]


def md_table():
    out = []
    cur = None
    for qid, slug, frage, ok, part, fail, na, kind in Q:
        d = qid.split(".")[0]
        if d != cur:
            cur = d
            name, w = DIMS[d]
            out.append(f"\n{d} {name} (Gewicht {w})")
        na_s = ", ".join(na) if na else "-"
        out.append(
            f"  {qid:<7} {slug:<30} [{kind}] {frage}\n          ok: {ok} | partial: {part} | fail: {fail} | n/a: {na_s}"
        )
    return "\n".join(out)


def matrix():
    out = ["Archetyp        | nicht anwendbare Fragen (alle anderen: anwendbar)"]
    for a in ARCHETYPES:
        na = [q[0] for q in Q if a in q[6]]
        if a in ("template", "experiment", "legacy", "archive-candidate", "other"):
            out.append(
                f"{a:<15} | wie der naechstliegende Archetyp; Wahl in archetype_note begruenden"
            )
        else:
            out.append(f"{a:<15} | " + (", ".join(na) if na else "keine"))
    return "\n".join(out)


def schema():
    evidence = {
        "type": "object",
        "required": ["kind", "ref", "checked_at", "source"],
        "additionalProperties": False,
        "properties": {
            "kind": {
                "enum": [
                    "file",
                    "manifest",
                    "setting",
                    "workflow",
                    "command",
                    "lifecycle",
                    "scanner",
                ]
            },
            "ref": {"type": "string"},
            "checked_at": {"type": "string", "format": "date-time"},
            "source": {"enum": ["pack", "own-fetch"]},
        },
    }
    ev_list = {"type": "array", "items": {"$ref": "#/$defs/evidence"}}
    control = {
        "type": "object",
        "required": ["state", "evidence"],
        "additionalProperties": False,
        "properties": {
            "state": {
                "enum": [
                    "enabled",
                    "partial",
                    "disabled",
                    "configured_no_analysis",
                    "plan_unavailable",
                    "no_permission",
                    "not_applicable",
                    "unknown",
                ]
            },
            "numerator": {"type": "integer", "minimum": 0},
            "denominator": {"type": "integer", "minimum": 1},
            "evidence": ev_list,
        },
        "allOf": [
            {
                "if": {"properties": {"state": {"const": "partial"}}},
                "then": {
                    "required": ["numerator", "denominator"],
                    "properties": {"evidence": {"minItems": 1}},
                },
            },
            {
                "if": {
                    "properties": {
                        "state": {
                            "enum": ["enabled", "disabled", "configured_no_analysis"]
                        }
                    }
                },
                "then": {"properties": {"evidence": {"minItems": 1}}},
            },
        ],
    }
    q_answered = {
        "type": "object",
        "required": ["state", "outcome", "question_score", "evidence"],
        "additionalProperties": False,
        "properties": {
            "state": {"const": "answered"},
            "outcome": {"enum": ["ok", "partial", "fail"]},
            "question_score": {"enum": [0, 3, 5]},
            "evidence": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/evidence"},
            },
            "note": {"type": "string"},
        },
        "allOf": [
            {
                "if": {"properties": {"outcome": {"const": "ok"}}},
                "then": {"properties": {"question_score": {"const": 5}}},
            },
            {
                "if": {"properties": {"outcome": {"const": "partial"}}},
                "then": {"properties": {"question_score": {"const": 3}}},
            },
            {
                "if": {"properties": {"outcome": {"const": "fail"}}},
                "then": {"properties": {"question_score": {"const": 0}}},
            },
        ],
    }
    q_open = {
        "type": "object",
        "required": ["state", "note"],
        "additionalProperties": False,
        "properties": {
            "state": {"enum": ["unverified", "not_run_at_depth", "not_applicable"]},
            "note": {"type": "string"},
        },
    }
    question = {
        "oneOf": [
            {"$ref": "#/$defs/question_answered"},
            {"$ref": "#/$defs/question_open"},
        ]
    }
    scores_props = {}
    for d in DIMS:
        qids = [q[0] for q in Q if q[0].startswith(d + ".")]
        scores_props[d] = {
            "type": "object",
            "required": ["score", "coverage", "questions"],
            "additionalProperties": False,
            "properties": {
                "score": {"type": ["integer", "null"], "minimum": 0, "maximum": 5},
                "coverage": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "questions": {
                    "type": "object",
                    "required": qids,
                    "additionalProperties": False,
                    "properties": {q: {"$ref": "#/$defs/question"} for q in qids},
                },
            },
        }
    slugs = sorted({q[1] for q in Q})
    finding = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "key",
            "locator",
            "locator_kind",
            "question_id",
            "finding_type",
            "delta",
            "prior_art",
            "remediation_prs",
            "konflikt_adr",
            "dimension",
            "severity",
            "confidence",
            "evidence",
            "observation",
            "why_it_matters",
            "blast_radius",
            "recommendation",
            "alternatives",
            "effort",
            "blockers",
            "cross_repo_sequence",
            "acceptance",
            "verification",
            "rollback",
            "safe_draft_pr",
            "requires_gate",
        ],
        "properties": {
            "key": {
                "type": "string",
                "pattern": "^[^/]+/[^/:]+:D(0[1-9]|1[0-2]):([0-9a-f]{8}|00000000)$",
            },
            "locator": {
                "type": "string",
                "pattern": "^D(0[1-9]|1[0-2])\\.[0-9]{1,2}\\|[a-z0-9-]+\\|[^|]+$",
            },
            "locator_kind": {
                "enum": ["setting", "pattern", "files", "absence", "repo"]
            },
            "question_id": {
                "type": "string",
                "pattern": "^D(0[1-9]|1[0-2])\\.[0-9]{1,2}$",
            },
            "finding_type": {"enum": slugs},
            "delta": {"enum": ["NEW", "UNCHANGED", "CHANGED", "CLOSED"]},
            "closed_evidence": ev_list,
            "prior_art": {
                "type": "object",
                "required": ["issues", "adr", "konz", "known_since"],
                "additionalProperties": False,
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                    },
                    "adr": {"type": ["string", "null"]},
                    "konz": {"type": ["string", "null"]},
                    "known_since": {"type": ["string", "null"], "format": "date"},
                },
            },
            "remediation_prs": {
                "type": "array",
                "items": {"type": "string", "format": "uri"},
            },
            "konflikt_adr": {"type": ["string", "null"]},
            "dimension": {"type": "string", "pattern": "^D(0[1-9]|1[0-2])$"},
            "severity": {"enum": ["P0", "P1", "P2", "P3"]},
            "confidence": {"enum": ["high", "medium", "low"]},
            "evidence": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/evidence"},
            },
            "observation": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "blast_radius": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string"},
            "alternatives": {"type": "array", "items": {"type": "string"}},
            "effort": {"enum": ["S", "M", "L", "XL"]},
            "blockers": {"type": "array", "items": {"type": "string"}},
            "cross_repo_sequence": {"type": "array", "items": {"type": "string"}},
            "acceptance": {"type": "array", "minItems": 1, "items": {"type": "string"}},
            "verification": {"type": "array", "items": {"type": "string"}},
            "rollback": {"type": "string"},
            "safe_draft_pr": {"type": "boolean"},
            "requires_gate": {
                "enum": [
                    "none",
                    "irreversibel",
                    "prod",
                    "security-config",
                    "scope",
                    "spend",
                ]
            },
        },
        "allOf": [
            {
                "if": {"properties": {"delta": {"const": "CLOSED"}}},
                "then": {"required": ["closed_evidence"]},
            }
        ],
    }
    entity = "^([^/]+/[^/]+|host:[a-z0-9._-]+|registry:pypi/[a-z0-9._-]+)$"
    edge = {
        "type": "object",
        "additionalProperties": False,
        "required": ["source", "target", "type", "version", "location", "confidence"],
        "properties": {
            "source": {"type": "string", "pattern": entity},
            "target": {"type": "string", "pattern": entity},
            "type": {
                "enum": [
                    "build",
                    "runtime",
                    "deploy",
                    "schema",
                    "contract",
                    "ci",
                    "org",
                    "copied",
                ]
            },
            "version": {"type": "string"},
            "location": {"type": "string"},
            "confidence": {"enum": ["high", "medium", "low"]},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "future-readiness-worker-result",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "repo",
            "analyzed_sha",
            "analyzed_at",
            "depth",
            "rubric_version",
            "run_date",
            "horizon_end",
            "archetype",
            "archetype_note",
            "lifecycle",
            "criticality",
            "data_class",
            "scores",
            "weights_override",
            "calculation",
            "readiness",
            "evidence_coverage",
            "readiness_class",
            "confidence",
            "controls",
            "findings",
            "edges",
            "provider_artifacts",
            "unknowns",
            "underspecified",
            "prior_run",
            "budget",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "repo": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
            "analyzed_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "analyzed_at": {"type": "string", "format": "date-time"},
            "depth": {"enum": ["T1", "T2"]},
            "rubric_version": {"type": "string"},
            "run_date": {"type": "string", "format": "date"},
            "horizon_end": {"type": "string", "format": "date"},
            "archetype": {"enum": ARCHETYPES},
            "archetype_note": {"type": "string"},
            "lifecycle": {
                "enum": [
                    "strategic",
                    "active",
                    "maintenance",
                    "sunset-planned",
                    "archive-candidate",
                    "unknown",
                ]
            },
            "criticality": {
                "type": "object",
                "required": ["value", "confidence", "source"],
                "additionalProperties": False,
                "properties": {
                    "value": {"enum": ["high", "medium", "low", "unknown"]},
                    "confidence": {"enum": ["high", "medium", "low"]},
                    "source": {"type": "string"},
                    "hint": {"type": "string"},
                },
            },
            "data_class": {
                "enum": ["public", "internal", "personal", "gov-citizen", "unknown"]
            },
            "scores": {
                "type": "object",
                "required": list(DIMS),
                "additionalProperties": False,
                "properties": scores_props,
            },
            "weights_override": {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^D(0[1-9]|1[0-2])$": {
                        "type": "object",
                        "required": ["weight", "reason"],
                        "additionalProperties": False,
                        "properties": {
                            "weight": {"type": "integer", "minimum": 0},
                            "reason": {"type": "string"},
                        },
                    }
                },
            },
            "calculation": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "weighted_score_sum",
                    "scored_weight_sum",
                    "readiness_raw",
                    "coverage_by_dimension",
                    "precision",
                    "rounding",
                ],
                "properties": {
                    "weighted_score_sum": {"type": "number"},
                    "scored_weight_sum": {"type": "number"},
                    "readiness_raw": {"type": "number"},
                    "coverage_by_dimension": {
                        "type": "object",
                        "required": list(DIMS),
                        "additionalProperties": False,
                        "properties": {d: {"type": ["number", "null"]} for d in DIMS},
                    },
                    "precision": {"const": 4},
                    "rounding": {"const": "half_up"},
                },
            },
            "readiness": {"type": "integer", "minimum": 0, "maximum": 100},
            "evidence_coverage": {"type": "number", "minimum": 0, "maximum": 1},
            "readiness_class": {
                "enum": ["ready", "solid", "modernize", "risk", "insufficient-evidence"]
            },
            "confidence": {"enum": ["high", "medium", "low"]},
            "controls": {
                "type": "object",
                "required": CONTROL_KEYS,
                "additionalProperties": False,
                "properties": {k: {"$ref": "#/$defs/control"} for k in CONTROL_KEYS},
            },
            "findings": {"type": "array", "items": {"$ref": "#/$defs/finding"}},
            "edges": {"type": "array", "items": {"$ref": "#/$defs/edge"}},
            "provider_artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["path", "type", "external_consumers"],
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "type": {
                            "enum": [
                                "reusable-workflow",
                                "composite-action",
                                "package",
                                "image",
                                "contract",
                            ]
                        },
                        "external_consumers": {"enum": ["unknown", "none", "some"]},
                    },
                },
            },
            "unknowns": {"type": "array", "items": {"type": "string"}},
            "underspecified": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "section",
                        "assumption",
                        "needed_rule",
                        "affected_questions",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "section": {"type": "string"},
                        "assumption": {"type": "string"},
                        "needed_rule": {"type": "string"},
                        "affected_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "prior_run": {"type": ["string", "null"]},
            "budget": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "tokens": {"type": "integer"},
                    "minutes": {"type": "number"},
                },
            },
        },
        "$defs": {
            "control": control,
            "evidence": evidence,
            "question": question,
            "question_answered": q_answered,
            "question_open": q_open,
            "finding": finding,
            "edge": edge,
        },
    }


def _blocks():
    return {
        "TABLE": md_table(),
        "MATRIX": matrix(),
        "SCHEMA": json.dumps(schema(), ensure_ascii=False, indent=1),
    }


def render_text(text):
    for name, body in _blocks().items():
        pat = re.compile(
            rf"(<!-- rubric:{name} -->\n)(?:.*?\n)?(<!-- /rubric:{name} -->)", re.DOTALL
        )
        if not pat.search(text):
            raise SystemExit(f"Marker fuer {name} fehlt im Prompt")
        text = pat.sub(
            lambda m, body=body: m.group(1) + body + "\n" + m.group(2), text, count=1
        )
    return text


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what in ("render", "check"):
        path = sys.argv[2]
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
        new = render_text(old)
        if what == "render":
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            print("rendered" if new != old else "unveraendert")
        else:
            if new != old:
                sys.exit(f"{path} entspricht nicht dem Generator — render ausfuehren")
            print("ok: Prompt == Generator")
    elif what == "table":
        print(md_table())
    elif what == "schema":
        print(json.dumps(schema(), ensure_ascii=False, indent=1))
    elif what == "matrix":
        print(matrix())
    elif what == "count":
        print(len(Q))
    else:
        sys.exit("unbekannt: table|matrix|schema|count|render <datei>|check <datei>")
