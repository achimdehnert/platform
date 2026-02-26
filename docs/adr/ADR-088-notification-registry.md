<!-- Drift-Detector-Felder: staleness_months: 12, drift_check_paths: platform/packages/platform-notify/**, supersedes_check: none -->

# ADR-088: Adopt a Shared Notification Registry as Platform-wide Multi-Channel Messaging System

---
status: proposed
date: 2026-02-26
decision-makers: [Platform Team]
---

> **Scope:** `platform`, alle Apps  
> **Inspiriert von:** OpenClaw `src/channels/registry.ts` + `dock.ts` (MIT-Lizenz) — Pattern-Übernahme  

---

## Context and Problem Statement

Jede App hat eigene, isolierte Benachrichtigungslogik:

| App | Aktuell | Bedarf |
|-----|---------|--------|
| **wedding-hub** | `EmailLog` + `SystemEmailTemplate` in `apps/communication/` | Magic-Link per E-Mail, perspektivisch WhatsApp |
| **risk-hub** | Kein Notification-System | Alerts bei kritischen Gefährdungen |
| **bfagent** | Kein Notification-System | Buch-Completion, Review-Requests |
| **dev-hub** | Kein Notification-System | Deploy-Status, Test-Failures |
| **weltenhub** | Kein Notification-System | Collaboration-Updates |

Es gibt kein einheitliches Interface — jede App müsste Channel-Integrationen (SMTP, Webhook, Telegram) selbst bauen.

## Decision Drivers

- **DRY**: Keine N×M Channel-Integrationen über alle Apps
- **DSGVO-Compliance**: Audit-Trail für alle gesendeten Benachrichtigungen
- **Multi-Channel-Erweiterbarkeit**: Neue Channels ohne App-Änderungen
- **Tenant-Isolation**: Jeder Tenant konfiguriert eigene Channel-Präferenzen
- **Celery-First**: Notifications sind asynchron — kein Blockieren von HTTP-Requests
- **Bestehende Systeme**: wedding-hub hat bereits `EmailLog` — Migration/Koexistenz berücksichtigen

## Considered Options

1. **Shared Notification Registry** (gewählt)
2. **OpenClaw als Service** (TypeScript-Monolith)
3. **Django-Notifications** (Paket)
4. **Celery-only** (ohne Registry)
5. **Pro-App eigene Integration**

## Decision Outcome

**Chosen option: "Shared Notification Registry"**, because:
- Einheitliches Interface für alle Apps über ein Platform-Package
- Channel-Abstraktion erlaubt neue Channels ohne App-Änderungen
- Celery-First-Design: `send()` ist **synchron** und dispatcht Celery-Tasks
- Audit-Trail via `NotificationLog` für DSGVO-Compliance
- Registration in `AppConfig.ready()` garantiert Thread-Safety

### Sync/Async-Strategie: Celery-First

Entgegen dem initialen Design ist `NotificationService.send()` **synchron** und dispatcht Celery-Tasks:

```python
# Aufruf in Django-Views (sync, kein async_to_sync nötig):
NotificationService.send(
    recipient="user@example.com",
    message=NotificationMessage(subject="Test", body_text="Hello"),
    channels=["email"],
    tenant_id=str(request.tenant_id),
)
# → Erstellt Celery-Task, kehrt sofort zurück
```

Dies vermeidet das `async_to_sync`-Problem aus ADR-062 (Content Store Incident).

### wedding-hub Migration

Bestehende `EmailLog` + `SystemEmailTemplate` in `apps/communication/`:
- **Phase 1**: Koexistenz — neues `NotificationLog` + altes `EmailLog` parallel
- **Phase 2**: Wedding-hub `send_magic_link()` auf `NotificationService.send()` umstellen
- **Phase 3**: `EmailLog` deprecaten, Daten nach `NotificationLog` migrieren (Management Command)
- **Phase 4**: `EmailLog` Model entfernen (Expand-Contract, ADR-021 §2.16)

## Architektur

```
App Code (sync)
  │
  ▼
NotificationService.send()        ← sync, dispatcht Celery-Task
  │
  ▼
Celery Task: dispatch_notification
  │
  ├── ChannelRegistry.get("email") → EmailChannel.deliver()
  ├── ChannelRegistry.get("webhook") → WebhookChannel.deliver()
  └── ChannelRegistry.get("telegram") → TelegramChannel.deliver()
  │
  ▼
Django Signal: notification_sent / notification_failed
  │
  ▼
NotificationLog (Audit-Trail)
```

### Komponenten

#### 1. Channel Interface

```python
# platform/packages/platform-notify/channels/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict, Field

class ChannelCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    supports_html: bool = Field(default=False, description="HTML-Nachrichten")
    supports_attachments: bool = Field(default=False, description="Dateianhänge")
    supports_templates: bool = Field(default=True, description="Template-Rendering")
    max_length: int | None = Field(default=None, description="Max Nachrichtenlänge")

class ChannelMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    id: str = Field(description="Eindeutige Channel-ID")
    label: str = Field(description="Anzeigename")
    capabilities: ChannelCapabilities = Field(default_factory=ChannelCapabilities)
    priority: int = Field(default=100, description="Sortierung (niedriger = höher)")
    enabled_by_default: bool = Field(default=False, description="Standardmäßig aktiv")
    max_retries: int = Field(default=3, description="Max Retry-Versuche")
    retry_backoff: bool = Field(default=True, description="Exponential Backoff")

class NotificationMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    subject: str = Field(description="Betreff / Titel")
    body_text: str = Field(description="Plain-Text Body")
    body_html: str | None = Field(default=None, description="HTML Body")
    template_name: str | None = Field(default=None, description="Django Template")
    context: dict = Field(default_factory=dict, description="Template Context")
    metadata: dict = Field(default_factory=dict, description="Channel-spezifische Daten")

class SendResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    success: bool
    channel_id: str
    recipient: str
    message_id: str | None = None
    error: str | None = Field(
        default=None,
        description="Sanitized error message (no stack traces, IPs, or internal details)",
    )

class NotificationChannel(ABC):
    """Base class für alle Notification Channels."""
    
    @property
    @abstractmethod
    def meta(self) -> ChannelMeta: ...
    
    @abstractmethod
    def deliver(
        self,
        recipient: str,
        message: NotificationMessage,
        tenant_id: str | None = None,
    ) -> SendResult:
        """Sync delivery — called inside Celery task."""
        ...
    
    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool: ...
```

#### 2. Channel Registry (Thread-Safe)

```python
# platform/packages/platform-notify/registry.py
class ChannelRegistry:
    """Singleton Registry für alle verfügbaren Notification Channels.
    
    Thread-Safety: Registration happens exclusively in AppConfig.ready().
    After startup, _channels is read-only.
    
    Inspiriert von OpenClaw src/channels/registry.ts — vereinfacht für Django.
    """
    
    _channels: dict[str, NotificationChannel] = {}
    _frozen: bool = False
    
    @classmethod
    def register(cls, channel: NotificationChannel) -> None:
        if cls._frozen:
            raise RuntimeError(
                "ChannelRegistry is frozen. Register channels in AppConfig.ready() only."
            )
        cls._channels[channel.meta.id] = channel
    
    @classmethod
    def freeze(cls) -> None:
        """Called after all AppConfig.ready() have run."""
        cls._frozen = True
    
    @classmethod
    def get(cls, channel_id: str) -> NotificationChannel | None:
        return cls._channels.get(channel_id)
    
    @classmethod
    def list_channels(cls) -> list[ChannelMeta]:
        return sorted(
            [ch.meta for ch in cls._channels.values()],
            key=lambda m: m.priority,
        )
    
    @classmethod
    def list_enabled(cls) -> list[ChannelMeta]:
        return [m for m in cls.list_channels() if m.enabled_by_default]
```

#### 3. Built-in Channels

```python
# Phase 1: Email (Django)
class EmailChannel(NotificationChannel):
    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="email",
            label="E-Mail",
            capabilities=ChannelCapabilities(
                supports_html=True,
                supports_attachments=True,
            ),
            priority=10,
            enabled_by_default=True,
            max_retries=3,
        )

# Phase 1: Webhook (HTTP POST)
class WebhookChannel(NotificationChannel):
    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="webhook",
            label="Webhook",
            capabilities=ChannelCapabilities(max_length=65536),
            priority=50,
            max_retries=5,
        )

# Phase 2: Telegram Bot
class TelegramChannel(NotificationChannel):
    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="telegram",
            label="Telegram",
            capabilities=ChannelCapabilities(
                supports_html=True,
                max_length=4096,
            ),
            priority=20,
            max_retries=3,
        )
```

#### 4. Notification Service (Celery-First)

```python
# platform/packages/platform-notify/service.py
from platform_notify.tasks import dispatch_notification_task

class NotificationService:
    """Zentrale Fassade für das Senden von Benachrichtigungen.
    
    All methods are sync — safe to call from Django views.
    Actual delivery happens in Celery tasks.
    """
    
    @staticmethod
    def send(
        recipient: str,
        message: NotificationMessage,
        channels: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Queue notification for async delivery via Celery."""
        if channels is None:
            channels = [m.id for m in ChannelRegistry.list_enabled()]
        
        for channel_id in channels:
            dispatch_notification_task.delay(
                channel_id=channel_id,
                recipient=recipient,
                message_dict=message.model_dump(),
                tenant_id=tenant_id,
            )
    
    @staticmethod
    def send_sync(
        recipient: str,
        message: NotificationMessage,
        channels: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[SendResult]:
        """Synchronous delivery — for tests and management commands only."""
        ...


# platform/packages/platform-notify/tasks.py
from celery import shared_task

@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
)
def dispatch_notification_task(
    self,
    channel_id: str,
    recipient: str,
    message_dict: dict,
    tenant_id: str | None = None,
) -> None:
    """Celery task: deliver notification via specified channel."""
    channel = ChannelRegistry.get(channel_id)
    if channel is None:
        _log_failure(channel_id, recipient, tenant_id, f"Channel '{channel_id}' not registered")
        return
    
    message = NotificationMessage(**message_dict)
    result = channel.deliver(recipient, message, tenant_id)
    
    # Audit-Trail
    NotificationLog.objects.create(
        tenant_id=tenant_id,
        channel_id=channel_id,
        recipient=recipient,
        subject=message.subject,
        status="sent" if result.success else "failed",
        error_message=result.error or "",
        message_id=result.message_id or "",
    )
    
    # Django Signal
    if result.success:
        notification_sent.send(
            sender=NotificationService,
            channel_id=channel_id,
            recipient=recipient,
            tenant_id=tenant_id,
        )
    else:
        notification_failed.send(
            sender=NotificationService,
            channel_id=channel_id,
            recipient=recipient,
            error=result.error,
            tenant_id=tenant_id,
        )
```

#### 5. Notification Log (Audit-Trail)

```python
# platform/packages/platform-notify/models.py
class NotificationLog(TenantModel):
    """Audit-Trail für alle gesendeten Benachrichtigungen.
    
    Row-Level Tenant-Isolation (begründete Abweichung von ADR-072):
    NotificationLog ist ein zentrales Audit-Model — Schema-Isolation
    würde Cross-Channel-Reporting pro Tenant erschweren.
    """
    
    channel_id = models.CharField(max_length=50, db_index=True)
    recipient = models.CharField(max_length=500)
    subject = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=[("sent", "Gesendet"), ("failed", "Fehlgeschlagen")],
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    message_id = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict)
    retry_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["tenant_id", "channel_id", "-sent_at"]),
        ]
```

### App-Integration (Beispiel: wedding-hub)

```python
# apps/communication/services.py
from platform_notify import NotificationService, NotificationMessage

def send_magic_link(guest_email: str, token: str, tenant_id: str) -> None:
    """Send magic link — sync, dispatches Celery task."""
    NotificationService.send(
        recipient=guest_email,
        message=NotificationMessage(
            subject="Deine Einladung",
            body_text=f"Klicke hier: https://.../?token={token}",
            template_name="communication/magic_link.html",
            context={"token": token},
        ),
        channels=["email"],
        tenant_id=tenant_id,
    )
```

### App Registration (Django AppConfig)

```python
# platform/packages/platform-notify/apps.py
from django.apps import AppConfig

class PlatformNotifyConfig(AppConfig):
    name = "platform_notify"
    
    def ready(self) -> None:
        from platform_notify.channels.email import EmailChannel
        from platform_notify.channels.webhook import WebhookChannel
        from platform_notify.registry import ChannelRegistry
        
        ChannelRegistry.register(EmailChannel())
        ChannelRegistry.register(WebhookChannel())
        ChannelRegistry.freeze()
```

## Pros and Cons of the Options

### Option 1: Shared Notification Registry (gewählt)

- **Good**: Einheitliches Interface für alle Apps
- **Good**: Neue Channels ohne App-Änderungen hinzufügbar
- **Good**: Audit-Trail für DSGVO-Compliance
- **Good**: Tenant-isoliert
- **Good**: Celery-First — kein Blockieren von Views
- **Bad**: Neue Abhängigkeit für alle Apps
- **Bad**: Celery muss in jeder App konfiguriert sein
- **Bad**: Migration bestehender wedding-hub EmailLog nötig

### Option 2: OpenClaw als Service

- **Good**: Feature-rich, battle-tested Channel-System
- **Bad**: TypeScript, 600-Datei-Monolith
- **Bad**: Massiver Overhead für unser Usecase
- **Bad**: Eigener Service zu betreiben

### Option 3: Django-Notifications (Paket)

- **Good**: Established Django-Paket
- **Bad**: In-App-only, kein Multi-Channel-Dispatch
- **Bad**: Keine Webhook/Telegram-Unterstützung out-of-the-box

### Option 4: Celery-only (ohne Registry)

- **Good**: Minimal, nutzt bestehende Infra
- **Bad**: Kein einheitliches Interface
- **Bad**: Kein Audit-Trail
- **Bad**: Kein Channel-Discovery

### Option 5: Pro-App eigene Integration

- **Good**: Maximale Flexibilität pro App
- **Bad**: DRY-Verletzung, N×M Integrationen
- **Bad**: Kein einheitlicher Audit-Trail
- **Bad**: Nicht wartbar bei wachsender App-Zahl

## Consequences

### Good

- Einheitliches Interface für alle Apps
- Neue Channels ohne App-Änderungen hinzufügbar
- Audit-Trail für DSGVO-Compliance
- Tenant-isoliert
- Celery-First — Views blockieren nicht

### Bad

- Neue Abhängigkeit für alle Apps
- Celery muss in jeder App konfiguriert sein
- wedding-hub EmailLog → NotificationLog Migration nötig

### Confirmation

Compliance wird verifiziert durch:
1. **Integration-Tests**: Senden über alle registrierten Channels (EmailChannel + WebhookChannel) in pytest
2. **Audit-Trail**: Jede gesendete Nachricht erzeugt einen `NotificationLog`-Eintrag
3. **Django-Signal**: `notification_sent` / `notification_failed` wird gefeuert und von Receiver getestet
4. **Retry-Test**: Simulierter SMTP-Timeout → Celery retry → Ergebnis im NotificationLog
5. **Thread-Safety**: `ChannelRegistry.freeze()` in Tests aufrufen, danach `register()` wirft `RuntimeError`

## Open Questions

| # | Frage | Status | Empfehlung |
|---|-------|--------|------------|
| Q1 | **DSGVO Retention-Policy**: Wie lange wird `NotificationLog` aufbewahrt? | Offen | 90 Tage, danach anonymisieren (recipient → hash) |
| Q2 | **Rate-Limiting**: Max. N Notifications/Stunde pro Tenant? | Offen | 100/h Email, 1000/h Webhook, konfigurierbar pro Tenant |
| Q3 | **Template-Rendering**: Django-Templates oder Channel-spezifische Formate? | Offen | Django-Templates für Email/HTML, plain-text für Telegram/Webhook |
| Q4 | **Recipient-Validation**: Welche Formate pro Channel? | Offen | Email: RFC 5322, Telegram: numeric Chat-ID, Webhook: HTTPS-URL |
| Q5 | **NotificationLog DB-Zuordnung**: In welcher DB? | Offen | Eigenes Schema oder App-DB; für Phase 1 in App-DB (TenantModel) |
| Q6 | **SMS/Push**: Welcher Provider für Phase 4? | Deferred → ADR-089+ | Twilio (SMS), Firebase (Push) evaluieren |

## Implementierungsplan

1. **Phase 1** (Q3 2026): EmailChannel + WebhookChannel + NotificationLog + Celery-Tasks
2. **Phase 2** (Q3 2026): TelegramChannel (Bot API)
3. **Phase 3** (Q3 2026): wedding-hub Migration (EmailLog → NotificationLog)
4. **Phase 4** (Q4 2026): Tenant-Präferenzen (Django Admin: welche Channels pro Org)
5. **Phase 5** (2027): SMS-Channel, Push-Notifications (→ eigenes ADR)

## More Information

### Related ADRs

- **ADR-021**: Platform Infrastructure — Expand-Contract Migration (§2.16)
- **ADR-035**: Shared Django Tenancy Package — `TenantModel` base class
- **ADR-045**: Secret Management — `EMAIL_HOST_PASSWORD`, `TELEGRAM_BOT_TOKEN` via SOPS
- **ADR-062**: Content Store — `async_to_sync` Incident (vermieden durch Celery-First)
- **ADR-072**: Multi-Tenancy Schema-Isolation — begründete Abweichung für Audit-Models

### External References

- OpenClaw `src/channels/registry.ts` — Channel-Registry-Pattern (MIT)
- OpenClaw `src/channels/dock.ts` — Channel-Adapter mit Capabilities (MIT)
- Django Signals: `django.dispatch.Signal`
- Celery: `autoretry_for`, `retry_backoff` patterns
