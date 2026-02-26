# ADR-088: Notification Registry — Einheitliches Multi-Channel-Benachrichtigungssystem

> **Status:** Proposed  
> **Datum:** 2026-02-26  
> **Autor:** Platform Team  
> **Scope:** `platform`, alle Apps  
> **Inspiriert von:** OpenClaw `src/channels/registry.ts` + `dock.ts` (MIT-Lizenz) — Pattern-Übernahme  

---

## Kontext

Jede App hat eigene, isolierte Benachrichtigungslogik:

| App | Aktuell | Bedarf |
|-----|---------|--------|
| **wedding-hub** | `EmailLog` Modell, `console.EmailBackend` | Magic-Link per E-Mail, perspektivisch WhatsApp |
| **risk-hub** | Kein Notification-System | Alerts bei kritischen Gefährdungen |
| **bfagent** | Kein Notification-System | Buch-Completion, Review-Requests |
| **dev-hub** | Kein Notification-System | Deploy-Status, Test-Failures |
| **weltenhub** | Kein Notification-System | Collaboration-Updates |

Es gibt kein einheitliches Interface — jede App müsste Channel-Integrationen (SMTP, Webhook, Telegram) selbst bauen.

## Entscheidung

Wir implementieren eine **Notification Registry** als Platform-Package mit:
- **Channel-Abstraktion**: Einheitliches Interface für alle Benachrichtigungskanäle
- **Channel-Registry**: Deklarative Registrierung verfügbarer Kanäle
- **Tenant-aware Routing**: Jeder Tenant konfiguriert eigene Channel-Präferenzen
- **Django Signals Integration**: Notifications via `notification_sent` / `notification_failed`

### Architektur

```
App Code
  │
  ▼
NotificationService.send(
    recipient, template, context, channels=["email", "webhook"]
)
  │
  ├── ChannelRegistry.get("email") → EmailChannel.send()
  ├── ChannelRegistry.get("webhook") → WebhookChannel.send()
  └── ChannelRegistry.get("telegram") → TelegramChannel.send()
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
    error: str | None = None

class NotificationChannel(ABC):
    """Base class für alle Notification Channels."""
    
    @property
    @abstractmethod
    def meta(self) -> ChannelMeta: ...
    
    @abstractmethod
    async def send(
        self,
        recipient: str,
        message: NotificationMessage,
        tenant_id: str | None = None,
    ) -> SendResult: ...
    
    @abstractmethod
    async def validate_recipient(self, recipient: str) -> bool: ...
```

#### 2. Channel Registry

```python
# platform/packages/platform-notify/registry.py
class ChannelRegistry:
    """Singleton Registry für alle verfügbaren Notification Channels.
    
    Inspiriert von OpenClaw src/channels/registry.ts — vereinfacht für Django.
    """
    
    _channels: dict[str, NotificationChannel] = {}
    
    @classmethod
    def register(cls, channel: NotificationChannel) -> None:
        cls._channels[channel.meta.id] = channel
    
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
        )
```

#### 4. Notification Service

```python
# platform/packages/platform-notify/service.py
class NotificationService:
    """Zentrale Fassade für das Senden von Benachrichtigungen."""
    
    @staticmethod
    async def send(
        recipient: str,
        message: NotificationMessage,
        channels: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> list[SendResult]:
        """Sende Nachricht über einen oder mehrere Channels."""
        if channels is None:
            channels = [m.id for m in ChannelRegistry.list_enabled()]
        
        results: list[SendResult] = []
        for channel_id in channels:
            channel = ChannelRegistry.get(channel_id)
            if channel is None:
                results.append(SendResult(
                    success=False,
                    channel_id=channel_id,
                    recipient=recipient,
                    error=f"Channel '{channel_id}' not registered",
                ))
                continue
            
            result = await channel.send(recipient, message, tenant_id)
            results.append(result)
            
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
        
        return results
```

#### 5. Notification Log (Audit-Trail)

```python
# platform/packages/platform-notify/models.py
class NotificationLog(TenantModel):
    """Audit-Trail für alle gesendeten Benachrichtigungen."""
    
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

async def send_magic_link(guest_email: str, token: str, tenant_id: str) -> None:
    await NotificationService.send(
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

## Alternativen (verworfen)

| Alternative | Warum verworfen |
|-------------|----------------|
| **OpenClaw als Service** | TypeScript, 600-Datei-Monolith, massiver Overhead |
| **Django-Notifications (Paket)** | In-App-only, kein Multi-Channel-Dispatch |
| **Celery-only** | Kein einheitliches Interface, kein Audit-Trail |
| **Pro-App eigene Integration** | DRY-Verletzung, N×M Integrationen |

## Konsequenzen

### Positiv
- Einheitliches Interface für alle Apps
- Neue Channels ohne App-Änderungen hinzufügbar
- Audit-Trail für Compliance (DSGVO)
- Tenant-isoliert

### Negativ
- Neue Abhängigkeit für alle Apps
- Async-Interface erfordert Celery für synchrone Views

## Implementierungsplan

1. **Phase 1** (Q3 2026): EmailChannel + WebhookChannel + NotificationLog
2. **Phase 2** (Q3 2026): TelegramChannel (Bot API)
3. **Phase 3** (Q4 2026): Tenant-Präferenzen (Django Admin: welche Channels pro Org)
4. **Phase 4** (2027): SMS-Channel, Push-Notifications

## Referenzen

- OpenClaw `src/channels/registry.ts` — Channel-Registry-Pattern (MIT)
- OpenClaw `src/channels/dock.ts` — Channel-Adapter mit Capabilities (MIT)
- Django Signals: `django.dispatch.Signal`
- ADR-035: Shared Django Tenancy Package
