# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->

```json
{
  "_type": "meta",
  "version": "1.0",
  "last_updated": "2026-04-29T16:32:36.516537+00:00",
  "last_updated_by": "cascade",
  "entry_count": 7
}
```

## Solved Problem

### SESSION-20260429-PLATFORM — Session 2026-04-29 platform: SSoT, PyPI, /workflow-review, ADR-175 Accepted

```json
{
  "_type": "entry",
  "entry_id": "SESSION-20260429-PLATFORM",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-29 platform: SSoT, PyPI, /workflow-review, ADR-175 Accepted",
  "content": "VORMITTAG: SSoT-Umbau sync-workflows aus registry/github_repos.yaml. Symlink-Bug gefixt. PyPI: aifw 0.10.2, learnfw 0.5.4, iil-testkit 0.4.1. testkit->iil-testkit kanonisch.\n\nNACHMITTAG: /workflow-review erstellt + 57 Workflows analysiert. Issue #80 (P0) closed: 24 deprecated mcp2_ Calls migriert auf mcp1_agent_memory(operation=...). MCP-Prefix-Tabellen erweitert.\n\nADR-175 (Workflow Modularization) Lifecycle: Proposed -> review (3.0/5) -> amended (5/5 nach /adr-review) -> Accepted nach 5/5 Pilot-Refactors.\n\n5 Pilot-Refactors (3033->2769 LOC, -9%):\n- onboard-repo 1175->1041\n- new-github-project 701->664\n- platform-audit 420->367\n- agentic-coding 372->351\n- session-ende 365->346\n\n7 ausgelagerte Lookup-Files in docs/onboarding/ + docs/governance/.\n\nADR-175 Open Question 1 geschlossen: Sync-CI verteilt jetzt docs/<topic>/ Files mit (Lookup-Extraction-Regex, Push auch bei Workflow-SKIP). Live-Test: 23 hubs erhalten Lookup-Files.\n\nAktuelle Issues: #74-79 docu-update/quality (offen, Backlog). #80 #81 closed.",
  "agent": "cascade",
  "created_at": "2026-04-29T16:32:36.513508Z",
  "updated_at": "2026-04-29T16:32:36.516524Z",
  "expires_at": "2026-05-29T16:32:36.513519Z",
  "tags": [
    "session",
    "platform",
    "ssot",
    "pypi",
    "workflows",
    "modularization",
    "adr-175",
    "accepted"
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

### ADR-PLATFORM-175 — ADR-175: Adopt selective modularization for .windsurf/workflows/ (ACCEPTED, implemented)

```json
{
  "_type": "entry",
  "entry_id": "ADR-PLATFORM-175",
  "entry_type": "agent_decision",
  "title": "ADR-175: Adopt selective modularization for .windsurf/workflows/ (ACCEPTED, implemented)",
  "content": "Repo: platform\nPfad: docs/adr/ADR-175-workflow-modularization-pattern.md\nStatus: ACCEPTED (2026-04-29)\nimplementation_status: implemented\n\nKern-Entscheidung: Selektive Auslagerung nach Inhalt-Typ. Aktive Steps + Code-Snippets bleiben INLINE; passive Inhalte (Verifikations-Checklisten, Beispiel-Refs, Glossare) werden ausgelagert nach docs/<topic>/<workflow>-<aspect>.md.\n\n5/5 Pilot-Refactors abgeschlossen (3033->2769 LOC, -9%):\n- onboard-repo 1175->1041 (-11%)\n- new-github-project 701->664 (-5%)\n- platform-audit 420->367 (-13%)\n- agentic-coding 372->351 (-6%)\n- session-ende 365->346 (-5%)\n\nAusgelagerte Files in docs/onboarding/ und docs/governance/.\n\nOpen Questions: Sync-CI muss docs/<topic>/ mit-verteilen, sonst broken Links in non-platform Repos.",
  "agent": "cascade",
  "created_at": "2026-04-29T16:21:12.076866Z",
  "updated_at": "2026-04-29T16:21:12.077745Z",
  "expires_at": "2026-05-29T16:21:12.076875Z",
  "tags": [
    "adr",
    "platform",
    "accepted",
    "workflows",
    "modularization",
    "implemented"
  ],
  "related_entries": [],
  "metadata": {}
}
```
