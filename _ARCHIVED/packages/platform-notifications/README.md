# platform-notifications

> Platform-wide multi-channel notification registry (ADR-088)

## Overview

Unified notification system with channel abstraction, Celery-First
async delivery, audit logging, and thread-safe registry pattern.

## Installation

```bash
pip install -e packages/platform-notifications
pip install -e "packages/platform-notifications[sms]"  # for Twilio SMS
```

## Usage

```python
from platform_notifications.service import NotificationService, Notification

NotificationService.send(Notification(
    tenant_id=request.tenant_id,
    channel="email",
    recipient="user@example.com",
    subject="Welcome",
    body="Hello from the platform!",
    source_app="wedding-hub",
    source_event="rsvp_confirmation",
))
```

## Built-in Channels

- **email** — Django `send_mail`
- **sms** — Twilio (requires `twilio` extra)
- **webhook** — Generic HTTPS POST via `httpx`

## Configuration

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

## Database

Run: `python manage.py migrate platform_notifications`

## Related ADRs

- **ADR-088**: Notification Registry
- **ADR-045**: Secret Management (Twilio, Discord, Telegram)
- **ADR-072**: Schema Isolation (Row-Level deviation documented)
