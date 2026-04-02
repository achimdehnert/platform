# Review: ADR-088 — Notification Registry

> **Reviewer:** Platform Review (Template C — Intensive)  
> **Datum:** 2026-02-26  
> **ADR:** [ADR-088-notification-registry.md](../ADR-088-notification-registry.md)  
> **Status des ADR:** `Proposed`  

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present (`status`, `date`, `decision-makers`) | ⚠️ | Blockquote-Format statt YAML frontmatter; `decision-makers` fehlt |
| 1.2 | Title is a decision statement (not a topic) | ⚠️ | Besser: "Adopt a Shared Notification Registry as Platform-wide Multi-Channel Messaging System" |
| 1.3 | `## Context and Problem Statement` section present | ✅ | Vorhanden als `## Kontext` — klar mit App-Bedarfstabelle |
| 1.4 | `## Decision Drivers` section present (bullet list) | ❌ | **Fehlt.** Implizit: DRY, Compliance (DSGVO), Multi-Channel, Tenant-Isolation |
| 1.5 | `## Considered Options` section lists ≥ 3 options | ✅ | 4 Alternativen (OpenClaw, Django-Notifications, Celery-only, Pro-App) |
| 1.6 | `## Decision Outcome` states chosen option with explicit reasoning | ⚠️ | `## Entscheidung` beschreibt Lösung gut, aber kein explizites "Chosen option" Statement |
| 1.7 | `## Pros and Cons of the Options` covers all considered options | ❌ | **Nur 1-Zeiler pro Alternative.** Keine Pro/Contra-Analyse. Gewählte Option hat keine Pro/Contra-Diskussion |
| 1.8 | `## Consequences` uses Good/Bad bullet format | ⚠️ | Positiv/Negativ vorhanden, aber nicht im MADR-Format |
| 1.9 | `### Confirmation` subsection | ❌ | **Fehlt.** Wie wird Compliance verifiziert? |
| 1.10 | `## More Information` links related ADRs | ⚠️ | Verlinkt ADR-035 (Tenancy) — aber ADR-045 (Secrets) und ADR-072 (Schema-Isolation) fehlen |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP referenced correctly | N/A | |
| 2.2 | SSH access rationale | N/A | |
| 2.3 | `StrictHostKeyChecking=no` absent | N/A | |
| 2.4 | Registry `ghcr.io/achimdehnert/` | N/A | |
| 2.5 | `GITHUB_TOKEN` scope | N/A | |
| 2.6 | Secrets via `DEPLOY_*` | ⚠️ | Telegram Bot Token + SMTP-Credentials benötigt — Secret-Handling nicht spezifiziert |
| 2.7 | Deploy path | N/A | |
| 2.8 | Health endpoints | ❌ | **Fehlt.** Kein Health-Endpoint für Notification-Service (z.B. SMTP-Konnektivität, Telegram-Bot-Erreichbarkeit) |
| 2.9 | Port allocation | N/A | |
| 2.10 | Nginx retained | N/A | |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.1–3.9 | Docker/CI checks | N/A | Shared Package, kein eigener Container |
| 3.10 | Worker/Beat Healthcheck | ⚠️ | Async-Dispatch impliziert Celery-Worker — aber kein Worker-Healthcheck definiert |

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | Expand-Contract pattern | ✅ | `NotificationLog` ist neues Model, keine Breaking Changes |
| 4.2 | `makemigrations --check` | N/A | Noch nicht implementiert |
| 4.3 | Migration backwards-compatible | ✅ | Neues Model, kein Impact auf bestehende Schemas |
| 4.4 | `tenant_id` present | ✅ | `NotificationLog(TenantModel)` erbt `tenant_id` |
| 4.5 | Shared DB risk | ⚠️ | **Unklar in welcher DB** `NotificationLog` lebt. Pro App? Zentrale Notifications-DB? Content Store? |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | No secrets hardcoded | ✅ | Keine Secrets in Code-Beispielen |
| 5.2 | `.env.prod` never committed | N/A | |
| 5.3 | SOPS/ADR-045 compatibility | ❌ | **Telegram Bot Token**, SMTP-Credentials, Webhook-URLs — alle als Secrets zu behandeln. Kein Verweis auf ADR-045 |
| 5.4 | `DEPLOY_*` secrets | N/A | |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service layer pattern | ✅ | `NotificationService` als Service-Fassade, Channel-Klassen als Adapter — saubere Trennung |
| 6.2 | No contradiction with existing ADRs | ⚠️ | **wedding-hub** hat bereits `EmailLog` + `SystemEmailTemplate` in `apps/communication/models.py` — Migration/Koexistenz nicht adressiert |
| 6.3 | Zero Breaking Changes | ✅ | Neues System, opt-in |
| 6.4 | ADR-054 Architecture Guardian | N/A | |
| 6.5 | Migration tracking table | ⚠️ | Keine Migrationsstrategie für bestehende wedding-hub `EmailLog` → `NotificationLog` |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | All open questions listed | ❌ | **Keine `## Open Questions` Sektion.** Offene Fragen: (a) Sync vs. Async Default? (b) Retry-Policy bei Fehlschlag? (c) Rate-Limiting pro Channel? (d) DSGVO: Retention-Policy für NotificationLog? (e) Template-System: Django Templates oder eigenes? |
| 7.2 | Deferred decisions reference future ADR | ❌ | SMS-Channel und Push-Notifications als "Phase 4 (2027)" — kein ADR referenziert |
| 7.3 | Conscious decisions documented | ⚠️ | Warum `async def send()` statt sync? Django-Views sind primär sync — `asgiref.async_to_sync` Wrapping nötig |

---

## 8. Modern Platform Patterns

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.1 | infra-deploy (ADR-075) | N/A | |
| 8.2 | MCP Deprecation-Warning | N/A | |
| 8.3 | Multi-Tenancy (ADR-072): Schema-Isolation | ⚠️ | `NotificationLog` nutzt Row-Level via `TenantModel`. Für ein Audit-Trail-Model ist das vertretbar, sollte aber explizit begründet werden |
| 8.4 | `tenant_id` Index | ✅ | Composite Index `["tenant_id", "channel_id", "-sent_at"]` vorhanden |
| 8.5 | Content Store `async_to_sync` | ⚠️ | **Relevant!** `NotificationService.send()` ist `async` — in Django sync-Views muss `async_to_sync` genutzt werden. ADR sollte dies explizit adressieren (ADR-062 Incident) |
| 8.6 | Content Store DSN | N/A | |
| 8.7 | Catalog `catalog-info.yaml` | N/A | |
| 8.8 | Drift-Detector Felder | ❌ | Fehlt |
| 8.9 | Runner Labels | N/A | |
| 8.10 | Temporal Workflows | N/A | |

---

## 9. Review Scoring

| Category | Score (1–5) | Notes |
|----------|-------------|-------|
| MADR 4.0 compliance | **2** | Decision Drivers, Confirmation, Pro/Cons pro Option fehlen |
| Platform Infrastructure Specifics | **3** | Secret-Handling und Health-Endpoint fehlen |
| CI/CD & Docker Conventions | **4** | Nicht direkt betroffen (Package) |
| Database & Migration Safety | **3** | DB-Zuordnung unklar, Migration bestehender EmailLog nicht adressiert |
| Security & Secrets | **3** | Telegram Token, SMTP Secrets nicht an ADR-045 gebunden |
| Architectural Consistency | **4** | Saubere Service-Architektur, aber wedding-hub Migration offen |
| Open Questions | **2** | Viele offene Punkte nicht dokumentiert |
| Modern Platform Patterns | **3** | async/sync Thematik unaddressiert, Drift-Detector fehlt |
| **Overall** | **3.0** | |

---

## 10. Recommendation

- [ ] **Accept** — ready to merge
- [x] **Accept with changes** — minor fixes required (list below)
- [ ] **Reject** — fundamental issues (list below)

### Required changes

1. **[CRITICAL] Sync/Async-Strategie klären**: `NotificationService.send()` ist `async` — aber Django-Views sind sync. Explizit dokumentieren:
   - (a) Sync-Wrapper via `asgiref.async_to_sync` (wie ADR-062 Content Store)
   - (b) Oder: Celery-Task als primärer Dispatch (`send_notification.delay(...)`) — dann braucht `send()` nicht async sein
   - Empfehlung: **Celery-First** — alle Notifications über Celery-Tasks, `send()` als sync-Methode die den Task dispatcht

2. **[CRITICAL] Retry-Policy definieren**: Was passiert bei SMTP-Timeout oder Telegram-API-Fehler?
   - Empfehlung: Celery `autoretry_for=(ConnectionError, TimeoutError)`, `max_retries=3`, `retry_backoff=True`

3. **[HIGH] Decision Drivers ergänzen**: DRY, DSGVO-Compliance, Multi-Channel-Erweiterbarkeit, Tenant-Isolation.

4. **[HIGH] Open Questions Sektion**:
   - DSGVO Retention-Policy für `NotificationLog` (wie lange aufbewahren?)
   - Rate-Limiting (max. N Notifications/Stunde pro Tenant)
   - Template-Rendering: Django-Templates vs. Channel-spezifische Formate
   - Recipient-Validation: E-Mail-Syntax, Telegram-Chat-ID-Format

5. **[HIGH] wedding-hub Migration**: Bestehende `EmailLog` + `SystemEmailTemplate` → `NotificationLog` Migrationspfad dokumentieren oder explizit koexistieren lassen.

6. **[HIGH] Confirmation Sektion**: "Verifiziert durch: (a) Integration-Test sendet über alle registrierten Channels, (b) NotificationLog Eintrag für jede gesendete Nachricht, (c) Django-Signal `notification_sent` wird gefeuert."

7. **[MEDIUM] Secret-Management**: Verweis auf ADR-045 für `EMAIL_HOST_PASSWORD`, `TELEGRAM_BOT_TOKEN`, Webhook-Secrets.

8. **[MEDIUM] ChannelRegistry Thread-Safety**: Class-Variable `_channels: dict` ist nicht thread-safe bei concurrent registration. Entweder:
   - (a) `threading.Lock` um `register()` 
   - (b) Registration nur beim App-Start (Django `AppConfig.ready()`)
   - Empfehlung: (b) — Registration in `AppConfig.ready()`, danach read-only

9. **[LOW] Drift-Detector Felder**: `<!-- staleness_months: 12, drift_check_paths: platform/packages/platform-notify/** -->` einfügen.

10. **[LOW] `SendResult.error`**: Sollte keine internen Details leaken (Stack-Traces, IP-Adressen). Sanitized Error Messages für Audit-Trail.

---

*Review-Template: v2.0 (2026-02-24) — Intensive Review*
