---
status: accepted
date: 2026-02-26
decision-makers: [Platform Team]
implementation_status: implemented
implementation_evidence:
  - "Phase 1 Package: platform/packages/platform-notifications/ — 21 Tests passed"
  - "5 Channels: EmailChannel, SmsChannel, WebhookChannel, DiscordChannel, TelegramChannel"
  - "ChannelRegistry: thread-safe Singleton, auto-registration via AppConfig.ready()"
  - "NotificationService: send() (Celery-async) + send_sync() + health_check()"
  - "Celery dispatch task: autoretry (3×, exponential backoff, jitter)"
  - "NotificationLog: BigAutoField PK, Row-Level Tenant Isolation, 4 DB-Indexes"
  - "FIX: UUIDField(primary_key=True) → BigAutoField (Platform-Regel)"
  - "Noch offen: Phase 2-4 Consumer-Migrations (wedding-hub, bfagent, risk-hub, weltenhub)"
---

<!-- Drift-Detector-Felder: staleness_months: 12, drift_check_paths: platform/packages/platform-notifications/**, supersedes_check: none -->

# ADR-088: Adopt a Shared Notification Registry as Platform-wide Multi-Channel Messaging System

> **Scope:** `platform`, `bfagent`, `risk-hub`, `weltenhub`, `wedding-hub`  
> **Inspiriert von:** OpenClaw `src/channels/` (MIT-Lizenz) — Konzeptübernahme, kein Code-Port  

---

## Context and Problem Statement

Mehrere Plattform-Apps versenden Benachrichtigungen über unterschiedliche Kanäle:

| App | Kanäle | Aktueller Zustand |
|-----|--------|-------------------|
| **bfagent** | Email, Webhook | Custom `send_email()` + `requests.post()` |
| **risk-hub** | Email | Django `send_mail()` direkt in Views |
| **weltenhub** | Email, Discord | Eigene Abstraktionsschicht |
| **wedding-hub** | Email, SMS (Twilio) | Direkte Twilio-API-Calls in Views |

Probleme:
- **Keine einheitliche API** — jede App implementiert Benachrichtigungen anders
- **Kein Audit-Log** — keine nachvollziehbare Historie wer wann was gesendet hat
- **Keine Retry-Logik** — fehlgeschlagene Benachrichtigungen gehen verloren
- **Kanal-Kopplung** — Views sind direkt an Kanal-Implementierung gebunden

## Decision Drivers

- **Einheitliche API** für alle Apps — `NotificationService.send()` statt N verschiedene Implementierungen
- **Multi-Channel** — Email, SMS, Webhook, Discord, Telegram erweiterbar
- **Audit-Trail** — lückenlose Nachvollziehbarkeit aller Benachrichtigungen
- **Retry & Resilience** — automatische Wiederholung bei transienten Fehlern
- **Celery-First** — synchrone API, asynchrone Delivery via Celery (kein `async_to_sync` Problem)
- **Multi-Tenant-Isolation** — Tenant-spezifische Channel-Konfiguration
- **Wiederverwendbarkeit** als Shared Platform-Package

## Considered Options

1. **Registry Pattern mit Channel-Abstraktion** (gewählt)
2. **Django Signals + Custom Handlers**
3. **Celery-Only (Tasks pro Kanal)**
4. **External Service (Novu, Knock)**
5. **django-notifications-hq**

## Decision Outcome

**Chosen option: "Registry Pattern mit Channel-Abstraktion"**, because:
- Zentrales Registry für Channel-Klassen — dynamisch erweiterbar
- Saubere Trennung: Views → NotificationService → ChannelRegistry → Channel
- Synchrone `send()` API dispatcht Celery-Task für jede Delivery
- Audit-Log für jede Benachrichtigung (Erfolg + Fehler)
- Retry-Policy konfigurierbar pro Channel
- wedding-hub Twilio-Calls werden zu `SmsChannel`-Implementierung migriert

### ADR-072 Schema-Isolation — Begründete Abweichung

ADR-072 fordert Schema-Isolation für Multi-Tenancy. `NotificationLog` nutzt stattdessen **Row-Level Isolation** (`WHERE tenant_id = ...`), weil:
- Notification-Logs sind eine **zentrale Audit-Ressource** — Schema-Isolation würde Partitions pro Tenant erfordern (Ops-Overhead für Audit-Tabelle unverhältnismäßig)
- Cross-Tenant-Audit ist **nicht erforderlich** — alle Queries filtern nach `tenant_id`
- Der `idx_notification_tenant` B-Tree-Index gewährleistet performante Isolation
- Notification-Logs werden typischerweise nach Datum gequeried (zeitbasierte Partitionierung effizienter als Tenant-Schema)

Dies ist eine bewusste Ausnahme, dokumentiert in Übereinstimmung mit ADR-072 §Exceptions.

### Celery-First Design

`NotificationService.send()` ist **synchron** und kann direkt aus Django Views aufgerufen werden:
1. View ruft `NotificationService.send(notification)` auf
2. Service erstellt `NotificationLog`-Einträge (Status: `pending`)
3. Service dispatcht **einen Celery-Task pro Channel** (`dispatch_notification_task.delay(log_id)`)
4. Celery-Task führt `channel.deliver()` aus und aktualisiert Log-Status + `retry_count`

Dadurch wird kein `async_to_sync` benötigt (vgl. ADR-062 §Content Store Pattern).

### Retry-Policy

```python
# Default Retry-Konfiguration pro Channel
RETRY_POLICY = {
    "max_retries": 3,
    "retry_backoff": True,           # Exponential backoff
    "retry_backoff_max": 300,        # Max 5 Minuten
    "retry_jitter": True,            # Jitter gegen Thundering Herd
    "autoretry_for": (ConnectionError, TimeoutError),
}
```

## Architektur

```
Django View (sync)
  └── NotificationService.send(notification)
        ├── Validate channels
        ├── Create NotificationLog entries (status: pending)
        └── dispatch_notification_task.delay(log_id)  ← Celery
              └── ChannelRegistry.get(channel_name)
                    └── channel.deliver(notification)
                          ├── Success → log.status = sent
                          └── Failure → retry or log.status = failed
```

### Komponenten

#### 1. Channel Interface

```python
# platform/packages/platform-notifications/channels/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict, Field

class ChannelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    max_retries: int = Field(default=3, description="Max delivery retries")
    retry_backoff: bool = Field(default=True, description="Exponential backoff")
    retry_backoff_max: int = Field(default=300, description="Max backoff seconds")
    timeout: int = Field(default=30, description="Delivery timeout seconds")

class BaseChannel(ABC):
    """Abstract base for notification channels."""
    
    name: str
    config: ChannelConfig
    
    def __init__(self, config: ChannelConfig | None = None) -> None:
        self.config = config or ChannelConfig()
    
    @abstractmethod
    def deliver(self, recipient: str, subject: str, body: str, **kwargs: object) -> bool:
        """Deliver notification. Returns True on success."""
        ...
    
    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format (e.g. email, phone number)."""
        ...
    
    def health_check(self) -> dict[str, bool | str]:
        """Check channel connectivity. Override for provider-specific checks."""
        return {"healthy": True, "channel": self.name}
```

#### 2. Channel Registry

```python
# platform/packages/platform-notifications/registry.py
import threading
from typing import ClassVar

class ChannelRegistry:
    """Thread-safe registry for notification channels.
    
    Singleton pattern with lock for thread-safety (Gunicorn workers).
    Reference: OpenClaw src/channels/registry.ts (MIT)
    """
    
    _instance: ClassVar["ChannelRegistry | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __init__(self) -> None:
        self._channels: dict[str, BaseChannel] = {}
        self._channel_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> "ChannelRegistry":
        """Thread-safe singleton access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def register(self, channel: BaseChannel) -> None:
        """Register a channel. Thread-safe."""
        with self._channel_lock:
            self._channels[channel.name] = channel
    
    def get(self, name: str) -> BaseChannel:
        """Get channel by name. Raises KeyError if not found."""
        with self._channel_lock:
            return self._channels[name]
    
    def list_channels(self) -> list[str]:
        """List registered channel names."""
        with self._channel_lock:
            return list(self._channels.keys())
    
    def health_check_all(self) -> dict[str, dict[str, bool | str]]:
        """Run health checks on all registered channels."""
        with self._channel_lock:
            channels = dict(self._channels)
        return {name: ch.health_check() for name, ch in channels.items()}
```

#### 3. Built-in Channels

```python
# platform/packages/platform-notifications/channels/email.py
from django.core.mail import send_mail

class EmailChannel(BaseChannel):
    name = "email"
    
    def deliver(self, recipient: str, subject: str, body: str, **kwargs: object) -> bool:
        send_mail(subject, body, None, [recipient], fail_silently=False)
        return True
    
    def validate_recipient(self, recipient: str) -> bool:
        from django.core.validators import validate_email
        try:
            validate_email(recipient)
            return True
        except Exception:
            return False
    
    def health_check(self) -> dict[str, bool | str]:
        from django.conf import settings
        has_backend = bool(getattr(settings, "EMAIL_BACKEND", None))
        return {"healthy": has_backend, "channel": self.name}

# platform/packages/platform-notifications/channels/sms.py
class SmsChannel(BaseChannel):
    """SMS via Twilio. Replaces wedding-hub direct Twilio calls."""
    name = "sms"
    
    def deliver(self, recipient: str, subject: str, body: str, **kwargs: object) -> bool:
        from twilio.rest import Client  # type: ignore[import-untyped]
        client = Client(self._get_account_sid(), self._get_auth_token())
        client.messages.create(
            body=body,
            from_=self._get_from_number(),
            to=recipient,
        )
        return True
    
    def validate_recipient(self, recipient: str) -> bool:
        import re
        return bool(re.match(r"^\+[1-9]\d{1,14}$", recipient))
    
    def health_check(self) -> dict[str, bool | str]:
        try:
            self._get_account_sid()
            return {"healthy": True, "channel": self.name}
        except Exception as exc:
            return {"healthy": False, "channel": self.name, "error": str(exc)}
    
    def _get_account_sid(self) -> str:
        from django.conf import settings
        return settings.TWILIO_ACCOUNT_SID
    
    def _get_auth_token(self) -> str:
        from django.conf import settings
        return settings.TWILIO_AUTH_TOKEN
    
    def _get_from_number(self) -> str:
        from django.conf import settings
        return settings.TWILIO_FROM_NUMBER

# platform/packages/platform-notifications/channels/webhook.py
import httpx

class WebhookChannel(BaseChannel):
    """Generic webhook channel."""
    name = "webhook"
    
    def deliver(self, recipient: str, subject: str, body: str, **kwargs: object) -> bool:
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                recipient,
                json={"subject": subject, "body": body, **kwargs},
            )
            response.raise_for_status()
        return True
    
    def validate_recipient(self, recipient: str) -> bool:
        return recipient.startswith("https://")
    
    def health_check(self) -> dict[str, bool | str]:
        return {"healthy": True, "channel": self.name}
```

#### 4. Notification Service

```python
# platform/packages/platform-notifications/service.py
import logging
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

class Notification(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    tenant_id: str = Field(description="Tenant UUID")
    channel: str = Field(description="Channel name (email, sms, webhook, ...)")
    recipient: str = Field(description="Recipient address")
    subject: str = Field(default="", description="Notification subject")
    body: str = Field(description="Notification body")
    source_app: str = Field(description="Sending app (bfagent, risk-hub, ...)")
    source_event: str = Field(description="Event type (rsvp_confirmation, ...)")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

class NotificationService:
    """Platform-wide notification service.
    
    Synchronous API — dispatches Celery tasks for async delivery.
    """
    
    @classmethod
    def send(cls, notification: Notification) -> str:
        """Send notification. Returns log_id. Sync — safe for Django views."""
        from platform_notifications.models import NotificationLog
        from platform_notifications.tasks import dispatch_notification_task
        
        registry = ChannelRegistry.get_instance()
        channel = registry.get(notification.channel)
        
        if not channel.validate_recipient(notification.recipient):
            raise ValueError(f"Invalid recipient for channel {notification.channel}")
        
        log = NotificationLog.objects.create(
            tenant_id=notification.tenant_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            body=notification.body,
            source_app=notification.source_app,
            source_event=notification.source_event,
            metadata=notification.metadata,
            status="pending",
        )
        
        dispatch_notification_task.delay(str(log.id))
        logger.info(
            "Notification queued: log_id=%s channel=%s app=%s",
            log.id, notification.channel, notification.source_app,
        )
        return str(log.id)
    
    @classmethod
    def health_check(cls) -> dict[str, dict[str, bool | str]]:
        """Health check all registered channels."""
        return ChannelRegistry.get_instance().health_check_all()
```

#### 5. Celery Task (Celery-First)

```python
# platform/packages/platform-notifications/tasks.py
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    autoretry_for=(ConnectionError, TimeoutError),
)
def dispatch_notification_task(self, log_id: str) -> None:
    """Deliver notification via channel. Celery-First pattern."""
    from platform_notifications.models import NotificationLog
    from platform_notifications.registry import ChannelRegistry
    
    log = NotificationLog.objects.get(id=log_id)
    registry = ChannelRegistry.get_instance()
    
    try:
        channel = registry.get(log.channel)
        success = channel.deliver(
            recipient=log.recipient,
            subject=log.subject,
            body=log.body,
        )
        if success:
            log.status = "sent"
            log.sent_at = timezone.now()
            log.retry_count = self.request.retries
            log.save(update_fields=["status", "sent_at", "retry_count", "updated_at"])
            logger.info("Notification sent: log_id=%s channel=%s", log_id, log.channel)
    except (ConnectionError, TimeoutError):
        log.retry_count = self.request.retries
        log.save(update_fields=["retry_count", "updated_at"])
        raise  # Celery autoretry handles re-queue
    except Exception:
        _log_failure(log, self.request.retries)
        logger.exception(
            "Notification delivery failed: log_id=%s channel=%s",
            log_id, log.channel,
        )


def _log_failure(log: "NotificationLog", retry_count: int) -> None:
    """Mark notification as failed with sanitized error info."""
    log.status = "failed"
    log.retry_count = retry_count
    log.error_message = "Delivery failed after retries. See application logs for details."
    log.save(update_fields=["status", "retry_count", "error_message", "updated_at"])
```

#### 6. Audit-Log Model

```python
# platform/packages/platform-notifications/models.py
import uuid
from django.db import models

class NotificationLog(models.Model):
    """Audit log for all notifications.
    
    Multi-Tenancy: Row-Level Isolation via tenant_id.
    Begründung: Siehe ADR-088 §ADR-072 Abweichung.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=50)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    source_app = models.CharField(max_length=50)
    source_event = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "notification_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_notification_tenant_status"),
            models.Index(fields=["channel", "status"], name="idx_notification_channel_status"),
            models.Index(fields=["source_app", "source_event"], name="idx_notification_source"),
            models.Index(fields=["created_at"], name="idx_notification_created"),
        ]
```

### Secret Management (ADR-045)

Neue Secrets für Notification-Channels:

| Secret | Channel | Beschreibung |
|--------|---------|--------------|
| `TWILIO_ACCOUNT_SID` | SMS | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | SMS | Twilio Auth Token |
| `TWILIO_FROM_NUMBER` | SMS | Absender-Telefonnummer |
| `DISCORD_WEBHOOK_URL` | Discord | Discord Webhook URL |
| `TELEGRAM_BOT_TOKEN` | Telegram | Telegram Bot API Token |

Alle Secrets werden via SOPS verwaltet (ADR-045) und über `django.conf.settings` geladen.

### Wedding-Hub Migration

wedding-hub hat aktuell direkte Twilio-API-Calls in Views:

```python
# VORHER (wedding-hub/views.py)
from twilio.rest import Client
client = Client(ACCOUNT_SID, AUTH_TOKEN)
client.messages.create(body=msg, from_=FROM, to=phone)

# NACHHER (wedding-hub/views.py)
from platform_notifications.service import NotificationService, Notification
NotificationService.send(Notification(
    tenant_id=request.tenant_id,
    channel="sms",
    recipient=phone,
    subject="",
    body=msg,
    source_app="wedding-hub",
    source_event="rsvp_confirmation",
))
```

Migrationsstrategie:
1. **Phase 1**: Platform-Package bereitstellen, wedding-hub als Pilot
2. **Phase 2**: Beide Pfade parallel (Feature-Flag `USE_NOTIFICATION_REGISTRY`)
3. **Phase 3**: Alten Code entfernen nach 2 Releases (Zero Breaking Changes, ADR-021)

### Integration pro App

| App | Kanäle | Trigger |
|-----|--------|---------|
| **bfagent** | Email, Webhook | Book-Export fertig, Agent-Task abgeschlossen |
| **risk-hub** | Email | Assessment-Deadline, neue Gefährdung |
| **weltenhub** | Email, Discord | Story-Update, Collaboration-Invite |
| **wedding-hub** | Email, SMS | RSVP-Bestätigung, Event-Reminder |

### Konfiguration

```python
# config/settings/base.py
PLATFORM_NOTIFICATIONS = {
    "DEFAULT_CHANNELS": ["email"],
    "RETRY_MAX": 3,
    "RETRY_BACKOFF": True,
    "RETRY_BACKOFF_MAX": 300,
    "LOG_RETENTION_DAYS": 90,
}
```

## Pros and Cons of the Options

### Option 1: Registry Pattern mit Channel-Abstraktion (gewählt)

- Good, because einheitliche API für alle Apps
- Good, because dynamisch erweiterbar (neue Channels ohne Code-Änderung in Apps)
- Good, because Celery-First — keine async_to_sync Probleme
- Good, because Audit-Log für Compliance und Debugging
- Good, because Thread-safe Registry (Gunicorn-kompatibel)
- Bad, because höherer initialer Implementierungsaufwand
- Bad, because Migration bestehender Apps nötig

### Option 2: Django Signals + Custom Handlers

- Good, because nutzt Django-Bordmittel
- Good, because lose Kopplung
- Bad, because synchrone Signal-Handler blockieren Request
- Bad, because kein standardisiertes Retry
- Bad, because Signal-Handler-Reihenfolge nicht garantiert

### Option 3: Celery-Only (Tasks pro Kanal)

- Good, because async by default
- Good, because einfach zu implementieren
- Bad, because keine Abstraktion — jeder Task kennt Channel-Details
- Bad, because kein Registry — neue Channels erfordern neue Tasks
- Bad, because Audit-Log muss separat implementiert werden

### Option 4: External Service (Novu, Knock)

- Good, because feature-complete out-of-the-box
- Good, because UI für Template-Management
- Bad, because externe Abhängigkeit, Vendor Lock-in
- Bad, because Kosten bei steigendem Volumen
- Bad, because DSGVO-Risiko bei US-Anbietern

### Option 5: django-notifications-hq

- Good, because etabliertes Django-Package
- Bad, because nur In-App-Notifications, kein Multi-Channel
- Bad, because kein SMS/Webhook/Telegram Support
- Bad, because keine Retry-Logik

## Consequences

- Good, because einheitliche Notification-API über alle Apps
- Good, because Audit-Trail für alle Benachrichtigungen
- Good, because automatische Retries bei transienten Fehlern
- Good, because Celery-First — keine async/sync Probleme
- Good, because dynamisch erweiterbar (Plugin-Pattern)
- Bad, because initialer Migrationsaufwand für bestehende Apps
- Bad, because zusätzliche Celery-Tasks pro Notification
- Bad, because Twilio/SMS-Kosten bleiben bestehen

### Risks

- Channel-Registry Singleton könnte bei Hot-Reload (Django `runserver`) zurückgesetzt werden — akzeptabel für Dev, nicht für Prod (Gunicorn re-importiert Module)
- Hohe Notification-Volumes könnten Celery-Queue überlasten — Rate-Limiting pro Channel evaluieren (Open Question Q4)

### Confirmation

Compliance wird verifiziert durch:
1. **pytest-Suite**: Mindestens 1 Test pro Channel (deliver + validate_recipient)
2. **Health-Check**: `NotificationService.health_check()` integriert in `/healthz/` Endpoint
3. **Audit-Abfrage**: `NotificationLog.objects.filter(status="failed").count()` < Threshold
4. **wedding-hub Smoke-Test**: SMS-Versand über neuen `SmsChannel` nach Migration
5. **Thread-Safety Test**: Concurrent Registry-Zugriff mit `threading.Thread`

## Open Questions

| # | Frage | Status | Empfehlung |
|---|-------|--------|------------|
| Q1 | **Template-Engine**: Sollen Notification-Templates (Jinja2/Django) unterstützt werden? | Offen | Phase 2 — zunächst Plain-Text |
| Q2 | **Rate-Limiting**: Max Notifications pro Tenant pro Zeiteinheit? | Offen | 100/h pro Channel als Default |
| Q3 | **Batch-Notifications**: Digest-Modus (z.B. tägliche Zusammenfassung)? | Deferred | Eigenes ADR nach Phase 3 |
| Q4 | **Queue-Isolation**: Dedizierte Celery-Queue für Notifications? | Offen | Ja — `notifications` Queue mit eigenen Workers |
| Q5 | **DB-Zuordnung**: Eigene DB oder Content Store für NotificationLog? | Offen | Eigene DB `notification_db` — trennt Audit-Daten von Content |
| Q6 | **Log-Retention**: Wie lange werden NotificationLogs aufbewahrt? | Offen | 90 Tage, dann Celery-Beat Task archiviert/löscht |

## Implementierungsplan

1. **Phase 1**: `platform/packages/platform-notifications/` Package — BaseChannel, Registry, NotificationService, EmailChannel
2. **Phase 2**: wedding-hub Migration (SMS → SmsChannel) + Feature-Flag
3. **Phase 3**: bfagent + risk-hub Integration
4. **Phase 4**: weltenhub (Discord-Channel) + Telegram-Channel

## More Information

### Related ADRs

- **ADR-021**: Platform Infrastructure — Zero Breaking Changes (§6.3)
- **ADR-035**: Shared Django Tenancy Package — `TenantModel` base class
- **ADR-045**: Secret Management — Twilio/Discord/Telegram Secrets via SOPS
- **ADR-062**: Content Store — Sync-Pattern Referenz (kein async_to_sync)
- **ADR-072**: Multi-Tenancy Schema-Isolation — begründete Abweichung (Row-Level)

### External References

- OpenClaw `src/channels/registry.ts` — Channel-Registry Pattern (MIT)
- OpenClaw `src/channels/dock.ts` — Channel-Adapter Pattern (MIT)
- [Celery Retry Documentation](https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying)
