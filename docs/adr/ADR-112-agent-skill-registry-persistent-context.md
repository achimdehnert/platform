---
status: accepted
date: 2026-03-08
updated: 2026-03-11
decision-makers: Achim Dehnert
consulted: Claude Sonnet (Cascade)
informed: Agent Team
implementation_status: implemented
implementation_evidence:
  - "mcp-hub/orchestrator_mcp/skills/: skill registry + session memory"
---

# ADR-112: Agent Skill Registry + Persistent Context Store

## Status

Accepted — v1.1 (2026-03-11, Phase 1 implementiert: SkillRegistry + 3 Skills)

## Context and Problem Statement

Das Agent Team (ADR-107) verfügt über konkrete MCP Tools (`get_infra_context`,
`get_payment_context`) und eine `AGENT_HANDOVER.md` als passives Kontext-Dokument.
Mit dem iPad-Workflow (GitHub Actions Trigger) und dem Payment Agent (ADR-062) wächst
das System. Dabei entstehen drei neue Probleme:

1. **Skills sind implizit** — MCP Tools sind registriert, aber nicht als versionierte,
   beschreibbare Einheiten modelliert. Ein neuer Agent (z.B. für Stripe, i18n, Tenants)
   muss manuell in `roles.py`, `tools.py` und `server.py` verankert werden.

2. **Kontext ist session-flüchtig** — `AGENT_HANDOVER.md` ist statisch. Agent-Entscheidungen,
   gelöste Probleme und gewonnene Erkenntnisse gehen zwischen Sessions verloren.
   Cascade Memory DB ist nicht git-tracked und nicht für andere Agents zugänglich.

3. **Onboarding neuer Repos ist manuell** — Kein Mechanismus scannt ein neues Repo
   automatisch und leitet daraus Agent-Kontext ab (Struktur, Migrations-Stand, Health-URL).

Inspiration: OpenClaw CLI-Ecosystem (2026) etabliert Skills als erste Klasse Objekte
und persistente Memory als git-tracked Artefakte. Diese Konzepte sind auf unser
MCP-basiertes System übertragbar.

## Decision Drivers

- Agent-Erweiterungen sollen ohne Code-Änderungen in 3 Dateien möglich sein
- Kontext soll über Sessions hinweg erhalten bleiben und von allen Agents lesbar sein
- Repo-Onboarding soll automatisierbar sein (Trigger: neues Repo im Org)
- Keine Abhängigkeit von proprietären Tools (kein OpenClaw, kein n8n)
- Kompatibel mit bestehender ADR-107/ADR-108 Architektur

## Considered Options

1. **OpenClaw direkt installieren** — proprietär, keine Kontrolle, externes Tooling
2. **Skill Registry in roles.py erweitern** — minimaler Ansatz, nur Code-Änderung
3. **Skill Registry + Agent Memory Store** — vollständige Lösung, git-tracked *(gewählt)*
4. **Externes Tool (LangChain Memory etc.)** — zu komplex, neue Abhängigkeit

## Decision Outcome

**Option 3** wird implementiert: eine formale `SkillRegistry` in `orchestrator_mcp` plus
ein git-tracked `AGENT_MEMORY.md` als beschreibbarer, strukturierter Kontext-Store.

### Positive Consequences

- Neue Agent-Skills mit einer Datei hinzufügbar (`skills/` Verzeichnis)
- Agent-Erkenntnisse bleiben persistent und sind diff-bar via Git
- Repo-Onboarding automatisierbar via GitHub Actions
- iPad-Workflow profitiert: Agent kann eigenen Kontext erweitern nach Task-Abschluss

### Negative Consequences

- `AGENT_MEMORY.md` kann merge-konflikte erzeugen bei parallelen Agent-Runs
- Skills-Verzeichnis erfordert Disziplin beim Hinzufügen (kein Registry-Chaos)

---

## Architecture

### 1. Skill Registry (`orchestrator_mcp/skills/`)

Jeder Skill ist eine Python-Datei mit einem standardisierten Interface:

```python
# orchestrator_mcp/skills/base.py
from dataclasses import dataclass
from typing import Any

@dataclass
class Skill:
    name: str           # z.B. "payment_context"
    version: str        # semver: "1.0.0"
    domain: str         # z.B. "payment", "infra", "tenancy"
    description: str
    mcp_tool_name: str  # z.B. "get_payment_context"
    gate_level: int     # 0-3

    def invoke(self) -> dict[str, Any]:
        """Wird von MCP Server aufgerufen."""
        raise NotImplementedError
```

Skills-Verzeichnis:
```
orchestrator_mcp/
└── skills/
    ├── __init__.py
    ├── base.py               ← SkillRegistry + Skill Dataclass
    ├── infra_context.py      ← bestehender get_infra_context
    ├── payment_context.py    ← bestehender get_payment_context
    ├── repo_scan.py          ← NEU: automatisches Repo-Onboarding
    └── session_memory.py     ← NEU: AGENT_MEMORY.md schreiben/lesen
```

### 2. SkillRegistry

```python
# orchestrator_mcp/skills/__init__.py
SKILL_REGISTRY: dict[str, Skill] = {}

def register(skill: Skill) -> None:
    SKILL_REGISTRY[skill.name] = skill

def get_skill(name: str) -> Skill:
    if name not in SKILL_REGISTRY:
        raise KeyError(f"Unknown skill: {name!r}")
    return SKILL_REGISTRY[name]
```

Auto-Registration via `__init_subclass__` oder explizit in `server.py`.

### 3. Agent Memory Store (`AGENT_MEMORY.md`)

Neben `AGENT_HANDOVER.md` (statisch, manuell) ein zweites Dokument:

```
platform/
├── AGENT_HANDOVER.md     ← statisch, manuell gepflegt (bleibt)
└── AGENT_MEMORY.md       ← dynamisch, von Agents geschrieben, git-tracked
```

Format:

```markdown
# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Letzte Aktualisierung: 2026-03-08T11:45:00Z von payment-agent -->

## Gelöste Probleme

### 2026-03-08 | payment-agent | billing-hub setup
- Status: setup_plans noch ausstehend (Price IDs fehlen)
- Kontext: STRIPE_SECRET_KEY in /opt/billing-hub/.env (noch nicht deployed)
- Next Action: Price IDs aus Stripe Dashboard → setup_plans ausführen

## Repo-Kontext Cache

### coach-hub (2026-03-08)
- Health: https://kiohnerisiko.de/healthz/ ✅
- Migrations: aktuell
- Stripe: MODULE_SHOP_CATALOGUE konfiguriert, Price IDs ausstehend

## Offene Agent-Tasks

| ID | Task | Status | Agent | Datum |
|---|---|---|---|---|
| T-001 | Stripe Price IDs setup_plans | pending | payment | 2026-03-08 |
```

### 4. Repo-Scan Skill (`repo_scan.py`)

Wird beim Onboarding eines neuen Repos ausgelöst (GitHub Actions `workflow_dispatch`
oder Issue-Label `repo-onboard`):

```python
def scan_repo(repo_name: str, github_token: str) -> dict:
    """
    Scannt ein Repo und gibt strukturierten Kontext zurück:
    - Erkannte Apps (Django, FastAPI, ...)
    - Health-URL (aus docker-compose.prod.yml)
    - Migrations-Stand
    - Offene Issues mit Labels
    - AGENT_HANDOVER.md falls vorhanden
    """
```

Ergebnis wird in `AGENT_MEMORY.md` als Repo-Kontext-Eintrag gespeichert.

---

## Migration Plan

| Schritt | Aktion | Aufwand |
|---|---|---|
| 1 | `orchestrator_mcp/skills/` Verzeichnis + `base.py` | 30 min |
| 2 | `infra_context.py` + `payment_context.py` als Skills refactoren | 30 min |
| 3 | `AGENT_MEMORY.md` anlegen (leer, Struktur definiert) | 10 min |
| 4 | `session_memory.py` Skill: AGENT_MEMORY.md lesen/schreiben | 45 min |
| 5 | `repo_scan.py` Skill: GitHub API basierter Repo-Scanner | 60 min |
| 6 | `agent-session-start.md` Workflow um Memory-Read erweitern | 15 min |
| 7 | GitHub Actions Workflow `agent-repo-onboard.yml` in mcp-hub | 30 min |

Gesamt: ~4h, vollständig rückwärtskompatibel (bestehende MCP Tools bleiben erhalten).

### Implementierungsstatus (2026-03-11)

| Schritt | Status |
|---------|--------|
| 1. `skills/` + `base.py` | ✅ Done (mcp-hub `5951acc`) |
| 2. `infra_context.py` als Skill | ✅ Done |
| 3. `AGENT_MEMORY.md` anlegen | ✅ Done (in platform/) |
| 4. `session_memory.py` Skill | ✅ Done |
| 5. `memory_schema.py` (Pydantic v2) | ✅ Done |
| 6. `__init__.py` (SkillRegistry + discover_skills) | ✅ Done |
| 7. GitHub Actions Workflow | 🔜 Pending |

---

## OpenClaw-Konzepte — Adoption-Entscheidungen

| OpenClaw-Konzept | Adoption | Begründung |
|---|---|---|
| Skills als Module | ✅ Übernommen | `orchestrator_mcp/skills/` |
| Persistent Memory | ✅ Übernommen | `AGENT_MEMORY.md` git-tracked |
| Wizard-Onboarding | ✅ Übernommen | `repo_scan.py` + GitHub Actions |
| Remote Mode API | ❌ Nicht nötig | MCP-Server ist bereits das Äquivalent |
| Swarm / tmux | ❌ Nicht nötig | GitHub Actions matrix-jobs bei Bedarf |
| Policy Firewall (`rampart`) | ✅ Bereits vorhanden | `ShellAllowlist` + `GateLevel` (ADR-107) |
| Cost Tracking | ✅ Bereits vorhanden | `get_cost_estimate` (ADR-108) |

---

## ADR-Referenzen

- **ADR-062**: Central Billing Service (billing-hub) — Payment Agent Kontext
- **ADR-107**: Extended Agent Team + Deployment Agent — Basis-Architektur
- **ADR-108**: Agent QA Loop — evaluate_task, verify_task
- **iPad-Workflow**: `.github/workflows/agent-task-dispatch.yml` in mcp-hub (2026-03-08)

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-08 | v1.0 | Cascade | ❌ 3B/4C/5H → Impl-Plan | [Review](../reviews/ADR-112-review-implementation.md) |
| 2026-03-11 | v1.0 → v1.1 | Cascade | ✅ Phase 1 implementiert (mcp-hub `5951acc`) | — |
