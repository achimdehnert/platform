#!/usr/bin/env python3
"""future_readiness_rubric.py — EINE Quelle fuer Fragenkatalog, Anwendbarkeitsmatrix und JSON-Schema
des Future-Readiness-Worker (docs/prompts/future-readiness-audit.md, v2.2).

    python3 tools/future_readiness_rubric.py table   # Artefakt 2, Kernfragen
    python3 tools/future_readiness_rubric.py matrix  # Artefakt 2, Anwendbarkeit
    python3 tools/future_readiness_rubric.py schema  # Artefakt 3, JSON Schema
    python3 tools/future_readiness_rubric.py render docs/prompts/future-readiness-audit.md  # {{TABLE}}/{{MATRIX}}/{{SCHEMA}} ersetzen

Ein Rubrik-Edit ohne Neugenerierung ist ungueltig (Anhang des Prompts). Anlass: Canary-Lauf 2
am 2026-09-02, Review C, Blocker 1-7 — Tabelle, Matrix und Schema liefen in v2.1 auseinander.
"""

import json
import sys

# (id, slug, weight_dim, frage, ok, partial, fail, na_archetypes)
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
Q = [
    (
        "D01.1",
        "runtime-version-belegt",
        "Runtime-Version(en) belegt",
        "genau eine Version an einer Stelle",
        "mehrere Stellen, gleiche Version",
        "widerspruechliche oder keine Version",
        [DOCS],
    ),
    (
        "D01.2",
        "eol-datum",
        "EOL-Datum aus LIFECYCLE_SOURCE ermittelt",
        "Datum mit Quelle",
        "-",
        "Quelle liefert nichts (dann unverified)",
        [DOCS],
    ),
    (
        "D01.3",
        "eol-vor-horizont",
        "EOL liegt nach HORIZON_END",
        "EOL >= HORIZON_END",
        "EOL zwischen RUN_DATE+12M und HORIZON_END",
        "EOL < RUN_DATE+12M",
        [DOCS],
    ),
    (
        "D01.4",
        "upgrade-pfad",
        "Upgrade-Pfad dokumentiert",
        "Ziel + Termin dokumentiert",
        "Ziel ohne Termin",
        "nichts",
        [DOCS],
    ),
    (
        "D01.5",
        "base-image",
        "Build-/Base-Image unterstuetzt",
        "Image mit Support-Datum > HORIZON_END",
        "Support-Datum < HORIZON_END",
        "EOL-Image",
        [CI, DOCS, PKG],
    ),
    (
        "D02.1",
        "manifest",
        "Abhaengigkeits-Manifest vorhanden",
        "ein Manifest mit Versionsangaben",
        "Manifest ohne Versionen",
        "kein Manifest",
        [DOCS],
    ),
    (
        "D02.2",
        "lockfile",
        "Lockfile vorhanden und in CI genutzt",
        "Lockfile + CI installiert daraus",
        "Lockfile, CI nutzt es nicht",
        "kein Lockfile",
        [DOCS],
    ),
    (
        "D02.3",
        "update-automation",
        "Dependency-Update-Automation aktiv",
        "Config fuer alle Oekosysteme",
        "Config fuer einen Teil",
        "keine",
        [DOCS],
    ),
    (
        "D02.4",
        "cve",
        "bekannte CVEs (Scanner)",
        "0 offen",
        "nur low/medium offen",
        "high/critical offen",
        [DOCS],
    ),
    (
        "D02.5",
        "unmaintained",
        "unmaintained Kernabhaengigkeit",
        "keine",
        "eine mit Ersatzplan",
        "eine ohne Plan",
        [DOCS],
    ),
    (
        "D03.1",
        "modulgrenzen",
        "Modulgrenzen ohne Zyklen",
        "belegt zyklenfrei",
        "Zyklen bekannt und isoliert",
        "Zyklen im Kern",
        [CI, DOCS, IAC],
    ),
    (
        "D03.2",
        "api-versioniert",
        "oeffentliche API/Contract versioniert",
        "Version + Deprecation-Regel",
        "Version ohne Regel",
        "unversioniert",
        [DOCS, IAC],
    ),
    (
        "D03.3",
        "migrationen-additiv",
        "Schema-Migrationen additiv",
        "nur additiv, geprueft",
        "additiv mit Ausnahmen",
        "destruktiv",
        [CI, DOCS, PKG, IAC],
    ),
    (
        "D03.4",
        "timeouts-retry",
        "Timeouts und Retry gesetzt",
        "beides",
        "eines",
        "keines",
        [CI, DOCS, IAC],
    ),
    (
        "D03.5",
        "idempotenz",
        "kritische Operationen idempotent",
        "belegt",
        "teilweise",
        "nein",
        [CI, DOCS, IAC],
    ),
    (
        "D03.6",
        "adr-bedarf",
        "offener ADR-Bedarf",
        "keiner",
        "einer, getrackt",
        "einer, ungetrackt",
        [DOCS],
    ),
    (
        "D04.1",
        "testsuite",
        "Testsuite existiert",
        "ja, > 10 Dateien",
        "1-10 Dateien",
        "keine",
        [DOCS],
    ),
    (
        "D04.2",
        "tests-in-ci",
        "Testlauf in CI erfolgreich (letzter Lauf des Test-Workflows)",
        "success",
        "in_progress/unbekannt (dann unverified)",
        "failure oder kein Test-Workflow",
        [DOCS],
    ),
    (
        "D04.3",
        "tests-lokal",
        "Tests lokal ausgefuehrt (T2)",
        "gruen",
        "teilweise rot, dokumentiert",
        "rot",
        [DOCS],
    ),
    ("D04.4", "lint-in-ci", "Lint in CI", "ja", "nur lokal/pre-commit", "nein", [DOCS]),
    (
        "D04.5",
        "typen-in-ci",
        "Typpruefung in CI",
        "ja",
        "nur lokal",
        "nein",
        [DOCS, IAC],
    ),
    (
        "D04.6",
        "kritischer-pfad",
        "kritischer Pfad getestet",
        "belegt",
        "teilweise",
        "ungetestet",
        [DOCS],
    ),
    (
        "D05.1",
        "required-checks",
        "Required Checks vorhanden",
        "Tests + Security als Required",
        "nur ein Check",
        "keine",
        [],
    ),
    (
        "D05.2",
        "review-pflicht",
        "Ruleset mit Review-Pflicht",
        "Approvals >= 1 oder Codeowner-Review",
        "nur Codeowner ohne Approval",
        "keine",
        [],
    ),
    (
        "D05.3",
        "release-automatisiert",
        "Release/Deploy automatisiert",
        "vollstaendig",
        "mit manuellen Schritten, dokumentiert",
        "manuell",
        [DOCS],
    ),
    (
        "D05.4",
        "rollback",
        "Rollback-Weg belegt",
        "dokumentiert + geprobt",
        "dokumentiert",
        "keiner",
        [DOCS],
    ),
    (
        "D05.5",
        "dauerrot",
        "Workflow auf Default-Branch dauerhaft rot (>= 3 Laeufe)",
        "keiner",
        "einer, mit Anker/Issue",
        "einer ohne Anker",
        [],
    ),
    (
        "D05.6",
        "shared-ci-drift",
        "Drift zu shared-ci",
        "aktuelles Band",
        "ein Band zurueck",
        "> 1 Band oder kein shared-ci",
        [DOCS],
    ),
    ("D06.1", "secret-scanning", "Secret Scanning", "enabled", "-", "disabled", []),
    ("D06.2", "push-protection", "Push Protection", "enabled", "-", "disabled", []),
    ("D06.3", "dependabot-alerts", "Dependabot-Alerts", "enabled", "-", "disabled", []),
    (
        "D06.4",
        "dependabot-security-updates",
        "Dependabot Security Updates",
        "enabled",
        "-",
        "disabled",
        [],
    ),
    (
        "D06.5",
        "code-scanning",
        "Code Scanning",
        "enabled mit Analyse",
        "configured_no_analysis",
        "disabled/kein Setup",
        [DOCS],
    ),
    (
        "D06.6",
        "action-pinning",
        "Action-Pinning (SHA-Anteil externer uses:)",
        "100 %",
        "> 0 % und < 100 %",
        "0 %",
        [],
    ),
    (
        "D06.7",
        "gefaehrliche-trigger",
        "pull_request_target/workflow_run ohne Checkout von PR-Code",
        "kein solcher Trigger",
        "Trigger ohne Checkout",
        "Trigger mit Checkout",
        [],
    ),
    (
        "D06.8",
        "permissions-top",
        "Top-Level permissions: gesetzt",
        "alle Workflows",
        "> 50 %",
        "<= 50 %",
        [],
    ),
    (
        "D06.9",
        "permissions-job",
        "Job-Level permissions least-privilege",
        "belegt",
        "Vorkommen gezaehlt, Werte nicht bewertet (unverified)",
        "write ohne Bedarf",
        [],
    ),
    (
        "D06.10",
        "oidc",
        "kurzlebige Identitaeten statt Token",
        "OIDC ueberall",
        "teils",
        "nur Token",
        [DOCS],
    ),
    (
        "D06.11",
        "sbom-provenance",
        "SBOM/Provenance",
        "beides",
        "eines",
        "keines",
        [CI, DOCS],
    ),
    ("D06.12", "signierung", "Artefakt-Signierung", "ja", "-", "nein", [CI, DOCS]),
    ("D07.1", "health", "Health-Endpunkt", "ja", "-", "nein", [CI, DOCS, PKG, IAC]),
    (
        "D07.2",
        "logs",
        "strukturierte Logs",
        "ja",
        "unstrukturiert",
        "keine",
        [CI, DOCS, PKG, IAC],
    ),
    ("D07.3", "metriken", "Metriken", "ja", "-", "nein", [CI, DOCS, PKG, IAC]),
    ("D07.4", "alarmweg", "Alarmweg belegt", "ja", "-", "nein", [DOCS, PKG]),
    ("D07.5", "runbook", "Runbook", "ja", "veraltet", "keines", [DOCS, PKG]),
    (
        "D07.6",
        "backup-restore",
        "Backup/Restore belegt",
        "geprobt",
        "dokumentiert",
        "nichts",
        [CI, DOCS, PKG],
    ),
    ("D08.1", "readme-zweck", "README nennt Zweck", "ja", "-", "nein", []),
    ("D08.2", "readme-setup", "README nennt Setup-Weg", "ja", "-", "nein", [DOCS]),
    ("D08.3", "codeowners", "CODEOWNERS", "ja", "-", "nein", []),
    ("D08.4", "security-md", "SECURITY.md", "ja", "-", "nein", []),
    ("D08.5", "changelog", "CHANGELOG", "ja", "-", "nein", []),
    (
        "D08.6",
        "einschraenkungen",
        "bekannte Einschraenkungen dokumentiert",
        "ja",
        "-",
        "nein",
        [],
    ),
    (
        "D09.1",
        "einstiegsbefehl",
        "ein Einstiegsbefehl (make/Taskfile)",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    (
        "D09.2",
        "tool-versionen",
        "Tool-Versionen gepinnt (.python-version o.ae.)",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    ("D09.3", "env-example", "Beispiel-Env-Datei", "ja", "-", "nein", [CI, DOCS, PKG]),
    (
        "D09.4",
        "beispiele-sicher",
        "Beispieldateien ohne echte Werte",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    ("D09.5", "pre-commit", "pre-commit", "ja", "-", "nein", [DOCS]),
    (
        "D09.6",
        "frisches-setup",
        "frisches Setup gelaufen (T2)",
        "gruen",
        "mit Handarbeit",
        "rot",
        [DOCS],
    ),
    ("D10.1", "agent-datei", "Agent-Instruktionsdatei", "ja", "-", "nein", []),
    (
        "D10.2",
        "agent-befehle",
        "verifizierte Befehle darin",
        "ja",
        "documented, nicht verified",
        "keine",
        [],
    ),
    ("D10.3", "verbotene-pfade", "verbotene Pfade benannt", "ja", "-", "nein", []),
    (
        "D10.4",
        "generierte-dateien",
        "generierte Dateien benannt",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    ("D10.5", "dod", "Definition of Done", "ja", "-", "nein", []),
    (
        "D10.6",
        "cross-repo-vertraege",
        "Cross-Repo-Vertraege benannt",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    ("D11.1", "lizenz", "Lizenz", "ja", "-", "nein", []),
    ("D11.2", "third-party-notices", "Third-Party-Notices", "ja", "-", "nein", [DOCS]),
    (
        "D11.3",
        "beispieldaten-personenfrei",
        "Beispieldaten personenfrei",
        "belegt (Scanner)",
        "-",
        "Fund",
        [],
    ),
    (
        "D12.1",
        "shared-ci-band",
        "shared-ci-Band aktuell",
        "ja",
        "ein Band zurueck",
        "nein",
        [DOCS],
    ),
    (
        "D12.2",
        "kopierte-standards",
        "kopierte Workflows/Dockerfiles",
        "keine",
        "mit Drift-Melder",
        "ohne",
        [DOCS],
    ),
    (
        "D12.3",
        "unabhaengig-releasbar",
        "unabhaengig releasbar",
        "ja",
        "-",
        "nein",
        [DOCS],
    ),
    (
        "D12.4",
        "konsumentenzahl",
        "Konsumentenzahl gemessen (Flotten-Grep)",
        "gemessen",
        "-",
        "-",
        [],
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


def md_table():
    out = []
    cur = None
    for qid, slug, frage, ok, part, fail, na in Q:
        d = qid.split(".")[0]
        if d != cur:
            cur = d
            name, w = DIMS[d]
            out.append(f"\n{d} {name} (Gewicht {w})")
        na_s = ", ".join(na) if na else "-"
        out.append(
            f"  {qid:<7} {slug:<28} {frage}\n          ok: {ok} | partial: {part} | fail: {fail} | n/a: {na_s}"
        )
    return "\n".join(out)


def schema():
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
            "denominator": {"type": "integer", "minimum": 0},
            "evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
        },
    }
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
    question = {
        "type": "object",
        "required": ["state"],
        "additionalProperties": False,
        "properties": {
            "state": {
                "enum": ["answered", "unverified", "not_run_at_depth", "not_applicable"]
            },
            "outcome": {"enum": ["ok", "partial", "fail"]},
            "question_score": {"enum": [0, 3, 5]},
            "evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
            "note": {"type": "string"},
        },
        "allOf": [
            {
                "if": {"properties": {"state": {"const": "answered"}}},
                "then": {
                    "required": ["outcome", "question_score", "evidence"],
                    "properties": {"evidence": {"minItems": 1}},
                },
            },
            {
                "if": {"properties": {"state": {"const": "not_applicable"}}},
                "then": {"required": ["note"]},
            },
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
    scores_props = {}
    for d, (name, w) in DIMS.items():
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
    controls_keys = [
        "secret_scanning",
        "push_protection",
        "dependabot_alerts",
        "dependabot_security_updates",
        "code_scanning",
        "action_pinning",
        "dangerous_triggers",
        "permissions_top",
        "permissions_job",
        "oidc",
        "sbom_provenance",
        "signing",
        "rulesets_default_branch",
        "codeowners",
    ]
    slugs = sorted({q[1] for q in Q})
    finding = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "key",
            "locator",
            "question_id",
            "finding_type",
            "delta",
            "prior_art",
            "remediation_pr",
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
                "pattern": "^[^/]+/[^/:]+:D(0[1-9]|1[0-2]):[0-9a-f]{8}$",
            },
            "locator": {
                "type": "string",
                "pattern": "^D(0[1-9]|1[0-2])\\.[0-9]{1,2}\\|[a-z0-9-]+\\|[^|]+$",
            },
            "question_id": {
                "type": "string",
                "pattern": "^D(0[1-9]|1[0-2])\\.[0-9]{1,2}$",
            },
            "finding_type": {"enum": slugs},
            "delta": {"enum": ["NEW", "UNCHANGED", "CHANGED", "CLOSED"]},
            "closed_evidence": {"type": "array", "items": {"$ref": "#/$defs/evidence"}},
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
            "remediation_pr": {"type": ["string", "null"], "format": "uri"},
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
    s = {
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
            "schema_version": {"const": "2.2"},
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
                "required": controls_keys,
                "additionalProperties": False,
                "properties": {k: {"$ref": "#/$defs/control"} for k in controls_keys},
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
                    "required": ["section", "assumption", "needed_rule"],
                    "additionalProperties": False,
                    "properties": {
                        "section": {"type": "string"},
                        "assumption": {"type": "string"},
                        "needed_rule": {"type": "string"},
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
            "finding": finding,
            "edge": edge,
        },
    }
    return s


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


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "render":
        path = sys.argv[2]
        text = open(path, encoding="utf-8").read()
        text = (
            text.replace("{{TABLE}}", md_table())
            .replace("{{MATRIX}}", matrix())
            .replace("{{SCHEMA}}", json.dumps(schema(), ensure_ascii=False, indent=1))
        )
        open(path, "w", encoding="utf-8").write(text)
        print("rendered")
    elif what == "table":
        print(md_table())
    elif what == "schema":
        print(json.dumps(schema(), ensure_ascii=False, indent=1))
    elif what == "matrix":
        print(matrix())
    elif what == "count":
        print(len(Q))
    else:
        sys.exit(f"unbekannt: {what} (table|matrix|schema|count|render <datei>)")
