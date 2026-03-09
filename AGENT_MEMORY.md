# Agent Memory Store
<!-- Automatisch generiert — nicht manuell bearbeiten -->
<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->

```json
{
  "_type": "meta",
  "version": "1.0",
  "last_updated": "2026-03-08T12:00:00+00:00",
  "last_updated_by": "cascade-init",
  "entry_count": 1
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
  "created_at": "2026-03-08T11:00:00+00:00",
  "updated_at": "2026-03-08T12:00:00+00:00",
  "expires_at": "2026-04-07T12:00:00+00:00",
  "tags": ["stripe", "coach-hub", "billing"],
  "related_entries": [],
  "metadata": {
    "repo": "coach-hub",
    "command": "python manage.py setup_plans --stripe-monthly=price_xxx --stripe-yearly=price_xxx",
    "modules": ["coaching_basic", "coaching_pro", "assessments", "learning", "reports"],
    "script": "docs/adr/inputs/stripe_setup_coach_hub.py"
  }
}
```
