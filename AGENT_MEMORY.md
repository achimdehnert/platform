# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->

```json
{
  "_type": "meta",
  "version": "1.0",
  "last_updated": "2026-04-29T16:02:40.266744+00:00",
  "last_updated_by": "cascade",
  "entry_count": 7
}
```

## Solved Problem

### SESSION-20260429-PLATFORM — Session 2026-04-29 — platform: SSoT Sync, PyPI, iil-testkit

```json
{
  "_type": "entry",
  "entry_id": "SESSION-20260429-PLATFORM",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-29 — platform: SSoT Sync, PyPI, iil-testkit",
  "content": "SSoT: sync-workflows liest DJANGO_HUBS/PACKAGES aus registry/github_repos.yaml. CI triggert bei Registry-Aenderung. Symlink-Bug: deleteFile+createFile statt updateFile (git-Mode 120000). onboarding-hub in Registry. PyPI: iil-aifw 0.10.2, iil-learnfw 0.5.4, iil-testkit 0.4.1. testkit->iil-testkit kanonisch (testkit archiviert). learnfw: ruff line-length=160, Python 3.11 raus. Issues #74 #75 #76.",
  "agent": "cascade",
  "created_at": "2026-04-29T15:20:40.141779Z",
  "updated_at": "2026-04-29T15:20:40.141787Z",
  "expires_at": "2026-05-29T15:20:40.141789Z",
  "tags": [
    "session",
    "platform",
    "ssot",
    "pypi",
    "testkit"
  ],
  "related_entries": [],
  "metadata": {}
}
```

### SESSION-2026-04-27-PLATFORM — Session 2026-04-27 - platform: LLM-Zugriff + docu-agent + Secret-Discovery

```json
{
  "_type": "entry",
  "entry_id": "SESSION-2026-04-27-PLATFORM",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-27 - platform: LLM-Zugriff + docu-agent + Secret-Discovery",
  "content": "LLM-Zugriffs-Analyse: aifw public API ist 'from aifw import sync_completion'. aifw braucht Django+DB -> nicht nutzbar in CI-Scripts. litellm>=1.30 (direkte Dep von aifw) darf in Standalone-Scripts direkt genutzt werden. docu_update_agent.py gefixt: from aifw.service Import entfernt, _call_llm() mit litellm, get_secret() Standard-Discovery. Secret-Registry in project-facts.md dokumentiert. iil-packages.md litellm-Ausnahme-Regel hinzugefuegt (Symlinks -> alle Repos aktiv). Offen: openai_api_key lokal fehlt.",
  "agent": "cascade",
  "created_at": "2026-04-27T14:15:06.246861Z",
  "updated_at": "2026-04-27T14:15:06.246873Z",
  "expires_at": "2026-05-27T14:15:06.246875Z",
  "tags": [
    "session",
    "platform",
    "aifw",
    "litellm",
    "secrets",
    "docu-agent"
  ],
  "related_entries": [],
  "metadata": {}
}
```

### SESSION-2026-04-23-PLATFORM-B — Session 2026-04-23b — gen_project_facts.py fix + desktop-setup Platform-Integration

```json
{
  "_type": "entry",
  "entry_id": "SESSION-2026-04-23-PLATFORM-B",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-23b — gen_project_facts.py fix + desktop-setup Platform-Integration",
  "content": "Letzter hardcoded /home/devuser/github Pfad in scripts/gen_project_facts.py gefunden und auf os.environ.get(GITHUB_DIR) umgestellt (Commit 39dd28f). desktop-setup Repo hat jetzt vollstaendige .windsurf/ Symlinks (9 Rules + 3 Workflows) via sync-workflows.sh. Beide Repos sauber gepusht. Session-Start Workflow komplett durchgefuehrt — alle Checks gruen.",
  "agent": "cascade",
  "created_at": "2026-04-23T19:05:27.226695Z",
  "updated_at": "2026-04-23T19:05:27.226699Z",
  "expires_at": "2026-05-23T19:05:27.226701Z",
  "tags": [
    "session",
    "platform",
    "desktop-setup",
    "hardcoding",
    "sync"
  ],
  "related_entries": [],
  "metadata": {}
}
```

### SESSION-2026-04-23-PLATFORM — Session 2026-04-23 — platform: Hardcoding-Bereinigung + docu-update-agent CI/CD

```json
{
  "_type": "entry",
  "entry_id": "SESSION-2026-04-23-PLATFORM",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-23 — platform: Hardcoding-Bereinigung + docu-update-agent CI/CD",
  "content": "Vollständige Bereinigung aller .windsurf/ Dateien (11x /home/dehnert/, 2x /home/devuser/, 7x falsche mcp-Prefixes mcp7_/mcp12_/mcp14_/mcp8_). secrets.md befüllt. onboard-repo Step 6.8 (Windsurf Platform-Integration: registry, symlinks, project-facts). Grok Fast ($0.0002/1k) in orchestrator_mcp/tools.py. cascade-auftraege.md Phase 0 GitHub Issues Queue mit grok_fast. docu_update_agent.py + docu-update-agent.yml: deterministischer CI/CD Agent auf docu-update Label ohne LLM. PROJECT_PAT Secret via API gesetzt. 9 offene docu-update Issues verarbeitet und geschlossen. Platform v2026.04.23.2 Commit 4130332.",
  "agent": "cascade",
  "created_at": "2026-04-23T18:56:02.278486Z",
  "updated_at": "2026-04-23T18:56:02.278823Z",
  "expires_at": "2026-05-23T18:56:02.278493Z",
  "tags": [
    "session",
    "platform",
    "hardcoding",
    "ci-cd",
    "docu-update",
    "grok-fast",
    "windsurf"
  ],
  "related_entries": [],
  "metadata": {}
}
```

## Repo Context

### SESSION-2026-04-28-PLATFORM — Session 2026-04-28 — platform: /prompt Groq + gen-project-facts

```json
{
  "_type": "entry",
  "entry_id": "SESSION-2026-04-28-PLATFORM",
  "entry_type": "repo_context",
  "title": "Session 2026-04-28 — platform: /prompt Groq + gen-project-facts",
  "content": "## Erledigt\n1. gen-project-facts.yml — pusht project-facts.md in alle Django-Repos wöchentlich via GH API\n2. push_project_facts.py — erkennt HTMX, Settings-Modul, Apps, pythonpath\n3. /prompt Workflow — 2 MCP-Calls statt 5, Groq Llama-3.3-70B via litellm/aifw-Venv\n4. run_prompt.py — ~60% weniger Cascade-Tokens, Key: ~/.secrets/groq_api_key\n5. risk-hub/project-facts.md live gepusht\n6. docu-update: README+CHANGELOG+Outline aktualisiert, ADR-Zahl 149->147\n## Key Files\n.github/scripts/push_project_facts.py, .github/workflows/gen-project-facts.yml, scripts/run_prompt.py, .windsurf/workflows/prompt.md\n## Secrets NEU\n~/.secrets/groq_api_key (gsk_, Free Tier, 14400 req/day)",
  "agent": "cascade",
  "created_at": "2026-04-28T14:02:48.777539Z",
  "updated_at": "2026-04-28T14:02:48.777544Z",
  "expires_at": "2026-05-28T14:02:48.777546Z",
  "tags": [
    "session",
    "platform",
    "prompt",
    "groq",
    "project-facts"
  ],
  "related_entries": [],
  "metadata": {}
}
```

## Open Task

### T-001 — Stripe Price IDs setup_plans

```json
{
  "_type": "entry",
  "entry_id": "T-001",
  "entry_type": "open_task",
  "title": "Stripe Price IDs setup_plans",
  "content": "Price IDs für coach-hub Module müssen im Stripe Dashboard erstellt werden. Danach: python manage.py setup_plans --stripe-monthly=price_xxx --stripe-yearly=price_xxx auf hetzner-prod ausführen.",
  "agent": "payment-agent",
  "created_at": "2026-03-08T11:00:00Z",
  "updated_at": "2026-03-08T12:00:00Z",
  "expires_at": "2026-04-07T12:00:00Z",
  "tags": [
    "stripe",
    "coach-hub",
    "billing"
  ],
  "related_entries": [],
  "metadata": {
    "repo": "coach-hub",
    "command": "python manage.py setup_plans --stripe-monthly=price_xxx --stripe-yearly=price_xxx",
    "modules": [
      "coaching_basic",
      "coaching_pro",
      "assessments",
      "learning",
      "reports"
    ],
    "script": "docs/adr/inputs/stripe_setup_coach_hub.py"
  }
}
```

## Agent Decision

### ADR-PLATFORM-175 — ADR-175: Workflow Modularization Pattern — Inline vs External References (Proposed)

```json
{
  "_type": "entry",
  "entry_id": "ADR-PLATFORM-175",
  "entry_type": "agent_decision",
  "title": "ADR-175: Workflow Modularization Pattern — Inline vs External References (Proposed)",
  "content": "Repo: platform\nPfad: docs/adr/ADR-175-workflow-modularization-pattern.md\nThema: Workflow-Modularisierung\nScope: workflows\nStatus: Proposed\nErstellt: 2026-04-29\nKern-Entscheidung: Selektive Auslagerung nach Inhalt-Typ. Aktive Steps + Code-Snippets bleiben INLINE; Verifikations-Checklisten + Beispiel-Referenzen + Glossare werden ausgelagert nach docs/<topic>/<workflow>-<aspect>.md. Schwellen: <300 LOC keine Aktion, 300-500 optional, 500-1000 empfohlen, >1000 Pflicht.\nAlternativen verworfen: Alles aufteilen (zerstoert linearen Step-Flow); Status quo (Token-Verschwendung).\nPilot-Refactors: onboard-repo 1175->1041 LOC, new-github-project 701->664 LOC.",
  "agent": "cascade",
  "created_at": "2026-04-29T16:02:40.265898Z",
  "updated_at": "2026-04-29T16:02:40.265905Z",
  "expires_at": "2026-05-29T16:02:40.265908Z",
  "tags": [
    "adr",
    "platform",
    "proposed",
    "workflows",
    "modularization"
  ],
  "related_entries": [],
  "metadata": {}
}
```
