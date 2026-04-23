# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->

```json
{
  "_type": "meta",
  "version": "1.0",
  "last_updated": "2026-04-23T16:53:47.293373+00:00",
  "last_updated_by": "cascade",
  "entry_count": 2
}
```

## Solved Problem

### SESSION-2026-04-23-PLATFORM — Session 2026-04-23 — platform: .windsurf Optimierung + devhub_web Fix

```json
{
  "_type": "entry",
  "entry_id": "SESSION-2026-04-23-PLATFORM",
  "entry_type": "solved_problem",
  "title": "Session 2026-04-23 — platform: .windsurf Optimierung + devhub_web Fix",
  "content": "Fixes: (1) devhub_web HealthBypassMiddleware + platform_context komplett via docker cp gepatcht -> healthy. (2) .windsurf: 12 Workflows von ~/github/ auf ${GITHUB_DIR} umgestellt. (3) Platform Sync Loop: session-start pull+sync + session-ende push+sync als GitHub-SSoT-Kreislauf. (4) Versions-Banner + VERSION Datei 2026.04.23.1 angelegt. (5) mcp-tools.md + project-facts.md fuer Dev-Desktop aktualisiert. GITHUB_DIR=$HOME/CascadeProjects in ~/.bashrc gesetzt. Offen: billing-hub decouple-Fehler (Image-Rebuild noetig), travel-beat celery restarting.",
  "agent": "cascade",
  "created_at": "2026-04-23T16:53:47.293004Z",
  "updated_at": "2026-04-23T16:53:47.293011Z",
  "expires_at": "2026-05-23T16:53:47.293012Z",
  "tags": [
    "session",
    "platform",
    "windsurf",
    "devhub",
    "sync-loop"
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
