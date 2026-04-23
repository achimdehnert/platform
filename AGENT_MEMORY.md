# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->

```json
{
  "_type": "meta",
  "version": "1.0",
  "last_updated": "2026-04-23T18:56:02.278855+00:00",
  "last_updated_by": "cascade",
  "entry_count": 2
}
```

## Solved Problem

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
