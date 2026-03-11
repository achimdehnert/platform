#!/usr/bin/env python3
"""Backfill implementation_status into all Accepted ADR frontmatters (ADR-138)."""
import re
from pathlib import Path

ADR_DIR = Path(__file__).parent.parent / "docs" / "adr"

# ── Categorisation based on code review 2026-03-11 ──────────────────────────
# Key: ADR number → (implementation_status, evidence_list)

IMPLEMENTED = "implemented"
PARTIAL = "partial"
NONE = "none"
VERIFIED = "verified"

STATUS_MAP: dict[int, tuple[str, list[str]]] = {
    # ── Governance / Process ADRs (the ADR IS the implementation) ──
    7:   (IMPLEMENTED, ["bfagent, weltenhub, risk-hub: tenant + RBAC models in production"]),
    10:  (IMPLEMENTED, ["platform/docs/adr/: governance process active"]),
    12:  (IMPLEMENTED, ["mcp-hub: quality standards enforced"]),
    14:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/agent_team/: AI-native team active"]),
    15:  (IMPLEMENTED, ["platform/docs/adr/: governance system active"]),
    22:  (IMPLEMENTED, ["platform-context MCP: consistency checks active"]),
    40:  (IMPLEMENTED, ["platform/.windsurf/rules/reviewer.md: completeness gate"]),
    41:  (IMPLEMENTED, ["all hubs: Django component pattern adopted"]),
    42:  (IMPLEMENTED, ["all repos: dev environment + deploy workflow"]),
    43:  (IMPLEMENTED, [".windsurf/workflows/: AI-assisted development active"]),
    45:  (IMPLEMENTED, ["all hubs: decouple.config() for secrets"]),
    46:  (IMPLEMENTED, ["platform/docs/: documentation governance active"]),
    48:  (IMPLEMENTED, ["all hubs: HTMX patterns adopted"]),
    51:  (IMPLEMENTED, [".windsurf/workflows/adr.md: concept-to-ADR pipeline"]),
    55:  (IMPLEMENTED, ["GitHub Issues: cross-app bug management active"]),
    71:  (IMPLEMENTED, ["all repos: ruff + bandit in CI"]),
    73:  (IMPLEMENTED, ["platform/docs/adr/ADR-073: 30 repos classified"]),
    80:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/agent_team/: multi-agent team"]),
    81:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/: guardrails + gate levels"]),
    82:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/: LLM tool integration"]),
    94:  (IMPLEMENTED, ["all hubs: migration conflict resolution pattern adopted"]),
    138: (IMPLEMENTED, ["docs/adr/ADR-138: this ADR + backfill script"]),

    # ── Fully implemented features ──
    21:  (IMPLEMENTED, ["all hubs: unified deployment via ship.sh / deploy.yml"]),
    27:  (IMPLEMENTED, ["platform-context package: shared backend services"]),
    28:  (IMPLEMENTED, ["platform-context MCP: platform context API"]),
    30:  (IMPLEMENTED, ["odoo-hub: Odoo management app deployed on 46.225.127.211"]),
    31:  (IMPLEMENTED, ["all hubs: static asset versioning active"]),
    35:  (IMPLEMENTED, ["iil-testkit: shared tenancy fixtures"]),
    36:  (IMPLEMENTED, ["bfagent: chat agent ecosystem with DomainToolkits"]),
    37:  (IMPLEMENTED, ["bfagent: chat conversation logging in AIUsageLog"]),
    44:  (IMPLEMENTED, ["mcp-hub: consolidated architecture (deployment, orchestrator, llm MCPs)"]),
    50:  (IMPLEMENTED, ["29 repos: hub landscape decomposed per ADR-050"]),
    70:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/: progressive autonomy gate levels"]),
    84:  (IMPLEMENTED, ["aifw: LLMModel + LLMProvider models, DB-driven routing"]),
    86:  (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/agent_team/: sprint execution pattern"]),
    89:  (IMPLEMENTED, ["aifw: LiteLLM backend + DB-driven model routing in production"]),
    90:  (IMPLEMENTED, ["platform/.github/workflows/: reusable CI/CD pipelines"]),
    95:  (IMPLEMENTED, ["aifw/src/aifw/service.py: _lookup_cascade(), get_action_config()"]),
    97:  (IMPLEMENTED, ["aifw/src/aifw/: models, migration 0005, service, constants, types, admin, tests"]),
    99:  (VERIFIED, ["https://devhub.iil.pet/releases/: Release Management UI live"]),
    100: (IMPLEMENTED, ["testkit: iil-testkit v0.1.0 on PyPI"]),
    102: (IMPLEMENTED, ["Cloudflare DNS active for all *.iil.pet domains"]),
    107: (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/: deployment agent active"]),
    112: (IMPLEMENTED, ["mcp-hub/orchestrator_mcp/skills/: skill registry + session memory"]),
    114: (IMPLEMENTED, ["mcp-hub/discord/: Discord bot with 9 slash commands live"]),
    120: (IMPLEMENTED, ["all 18 Django hubs: deploy.yml via reusable workflows"]),
    121: (IMPLEMENTED, ["writing-hub: iil-outlinefw v0.1.0 on PyPI"]),

    # ── Partially implemented ──
    49:  (PARTIAL, ["some hubs: design tokens adopted, not all"]),
    59:  (PARTIAL, ["platform-context MCP: basic drift detection, no automated alerts yet"]),
    61:  (PARTIAL, ["most hubs: hardcoding reduced, some legacy remains"]),
    62:  (PARTIAL, ["billing-hub: exists but Stripe integration incomplete"]),
    69:  (PARTIAL, ["mcp-hub: web intelligence basic, advanced features pending"]),
    72:  (PARTIAL, ["weltenhub, risk-hub: schema isolation, other hubs pending"]),
    74:  (PARTIAL, ["iil-testkit: tenant fixtures, not all hubs adopted"]),
    79:  (PARTIAL, ["bfagent: Temporal planned, Celery still primary"]),
    85:  (PARTIAL, ["mcp-hub/orchestrator_mcp/: basic task pipeline, NL→TaskGraph pending"]),
    87:  (PARTIAL, ["weltenhub: pgvector active, FTS not platform-wide yet"]),
    88:  (PARTIAL, ["some hubs: notification basics, registry not centralized yet"]),
    103: (PARTIAL, ["ausschreibungs-hub: Django app exists, full v3 architecture in progress"]),
    118: (PARTIAL, ["billing-hub: store concept exists, full user registration flow pending"]),
    131: (PARTIAL, ["platform-context: shared services exist, not all extracted yet"]),

    # ── Not yet implemented ──
    96:  (NONE, ["authoringfw: package exists but no writing/research/analysis sub-modules yet"]),
    117: (NONE, ["weltenfw: package exists but shared world layer not extracted from weltenhub yet"]),
    119: (NONE, ["authored content pipeline: ADR accepted, implementation not started"]),
    137: (NONE, ["tenant lifecycle module: ADR accepted, implementation not started"]),
}


def backfill() -> None:
    updated = 0
    skipped = 0

    for adr_file in sorted(ADR_DIR.glob("ADR-*.md")):
        text = adr_file.read_text()

        # Only process files with status: accepted
        if not re.search(r"^status:\s*accepted", text, re.MULTILINE):
            continue

        # Skip if already has implementation_status
        if "implementation_status:" in text:
            skipped += 1
            continue

        # Extract ADR number
        m = re.search(r"ADR-(\d+)", adr_file.name)
        if not m:
            continue
        adr_num = int(m.group(1))

        if adr_num not in STATUS_MAP:
            print(f"  WARN: ADR-{adr_num:03d} not in STATUS_MAP — skipping")
            continue

        impl_status, evidence = STATUS_MAP[adr_num]

        # Build the new fields
        evidence_yaml = "\n".join(f'  - "{e}"' for e in evidence)
        new_fields = f"implementation_status: {impl_status}\nimplementation_evidence:\n{evidence_yaml}"

        # Insert before closing --- of frontmatter
        # Find the second --- (closing frontmatter)
        parts = text.split("---", 2)
        if len(parts) < 3:
            print(f"  WARN: ADR-{adr_num:03d} — cannot parse frontmatter")
            continue

        # Add fields at end of frontmatter
        frontmatter = parts[1].rstrip()
        new_text = f"---{frontmatter}\n{new_fields}\n---{parts[2]}"
        adr_file.write_text(new_text)
        updated += 1
        print(f"  ✅ ADR-{adr_num:03d}: {impl_status}")

    print(f"\nDone: {updated} updated, {skipped} already had implementation_status")


if __name__ == "__main__":
    backfill()
