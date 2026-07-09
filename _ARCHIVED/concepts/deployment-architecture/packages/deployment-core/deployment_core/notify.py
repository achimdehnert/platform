"""
Unified notifications for deployment events.

This module provides:
- SlackNotifier: Send notifications to Slack
- EmailNotifier: Send email notifications (placeholder)
- Notifier: Base class for notifications

Example:
    notifier = SlackNotifier(webhook_url=os.environ["SLACK_WEBHOOK_URL"])
    
    await notifier.notify_deployment_success(
        app="travel-beat",
        tag="abc123",
        url="https://travel-beat.iil.pet"
    )
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class NotificationLevel(Enum):
    """Notification severity levels."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class NotificationPayload:
    """Notification payload."""

    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    app: str | None = None
    environment: str | None = None
    url: str | None = None
    details: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class Notifier(ABC):
    """Base class for notifiers."""

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns True on success."""
        pass

    async def notify_deployment_started(
        self,
        app: str,
        tag: str,
        environment: str = "production",
        triggered_by: str | None = None,
    ) -> bool:
        """Notify that deployment has started."""
        return await self.send(
            NotificationPayload(
                title=f"🚀 {app} Deployment Started",
                message=f"Deploying `{tag}` to {environment}",
                level=NotificationLevel.INFO,
                app=app,
                environment=environment,
                details={"tag": tag, "triggered_by": triggered_by},
            )
        )

    async def notify_deployment_success(
        self,
        app: str,
        tag: str,
        environment: str = "production",
        url: str | None = None,
        duration_seconds: float | None = None,
    ) -> bool:
        """Notify successful deployment."""
        message = f"Successfully deployed `{tag}` to {environment}"
        if duration_seconds:
            message += f" in {duration_seconds:.1f}s"

        return await self.send(
            NotificationPayload(
                title=f"✅ {app} Deployed",
                message=message,
                level=NotificationLevel.SUCCESS,
                app=app,
                environment=environment,
                url=url,
                details={"tag": tag, "duration_seconds": duration_seconds},
            )
        )

    async def notify_deployment_failed(
        self,
        app: str,
        tag: str,
        environment: str = "production",
        error: str | None = None,
        rollback_triggered: bool = False,
    ) -> bool:
        """Notify failed deployment."""
        message = f"Deployment of `{tag}` to {environment} failed"
        if rollback_triggered:
            message += "\nAutomatic rollback triggered"
        if error:
            message += f"\nError: {error[:200]}"

        return await self.send(
            NotificationPayload(
                title=f"❌ {app} Deployment Failed",
                message=message,
                level=NotificationLevel.ERROR,
                app=app,
                environment=environment,
                details={
                    "tag": tag,
                    "error": error,
                    "rollback_triggered": rollback_triggered,
                },
            )
        )

    async def notify_rollback(
        self,
        app: str,
        from_tag: str,
        to_tag: str,
        environment: str = "production",
        reason: str | None = None,
    ) -> bool:
        """Notify rollback event."""
        message = f"Rolled back from `{from_tag}` to `{to_tag}` in {environment}"
        if reason:
            message += f"\nReason: {reason}"

        return await self.send(
            NotificationPayload(
                title=f"⏪ {app} Rolled Back",
                message=message,
                level=NotificationLevel.WARNING,
                app=app,
                environment=environment,
                details={"from_tag": from_tag, "to_tag": to_tag, "reason": reason},
            )
        )

    async def notify_health_check_failed(
        self,
        app: str,
        environment: str = "production",
        url: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Notify health check failure."""
        message = f"Health check failed for {app} in {environment}"
        if error:
            message += f"\nError: {error[:200]}"

        return await self.send(
            NotificationPayload(
                title=f"🏥 {app} Health Check Failed",
                message=message,
                level=NotificationLevel.ERROR,
                app=app,
                environment=environment,
                url=url,
                details={"error": error},
            )
        )


class SlackNotifier(Notifier):
    """
    Send notifications to Slack via webhooks.

    Example:
        notifier = SlackNotifier(
            webhook_url=os.environ["SLACK_WEBHOOK_URL"],
            channel="#deployments"
        )
        await notifier.notify_deployment_success(app="myapp", tag="v1.0.0")
    """

    # Emoji mapping for notification levels
    LEVEL_EMOJI = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.SUCCESS: "✅",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨",
    }

    # Color mapping for notification levels
    LEVEL_COLOR = {
        NotificationLevel.INFO: "#3498db",  # Blue
        NotificationLevel.SUCCESS: "#2ecc71",  # Green
        NotificationLevel.WARNING: "#f39c12",  # Orange
        NotificationLevel.ERROR: "#e74c3c",  # Red
        NotificationLevel.CRITICAL: "#9b59b6",  # Purple
    }

    def __init__(
        self,
        webhook_url: str | None = None,
        channel: str | None = None,
        username: str = "Deploy Bot",
        icon_emoji: str = ":rocket:",
    ):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji

        if not self.webhook_url:
            logger.warning("slack_webhook_not_configured")

    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification to Slack."""
        if not self.webhook_url:
            logger.warning("slack_send_skipped", reason="no webhook URL")
            return False

        try:
            slack_payload = self._build_slack_payload(payload)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=slack_payload,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info("slack_notification_sent", title=payload.title)
                    return True
                else:
                    logger.error(
                        "slack_notification_failed",
                        status_code=response.status_code,
                        response=response.text,
                    )
                    return False

        except Exception as e:
            logger.error("slack_notification_error", error=str(e))
            return False

    def _build_slack_payload(self, payload: NotificationPayload) -> dict[str, Any]:
        """Build Slack message payload."""
        emoji = self.LEVEL_EMOJI.get(payload.level, "📋")
        color = self.LEVEL_COLOR.get(payload.level, "#808080")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{payload.title}*\n{payload.message}",
                },
            }
        ]

        # Add URL button if provided
        if payload.url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Open App"},
                            "url": payload.url,
                        }
                    ],
                }
            )

        # Add context with timestamp and environment
        context_elements = []
        if payload.environment:
            context_elements.append(
                {"type": "mrkdwn", "text": f"*Environment:* {payload.environment}"}
            )
        if payload.timestamp:
            context_elements.append(
                {"type": "mrkdwn", "text": f"*Time:* {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"}
            )

        if context_elements:
            blocks.append({"type": "context", "elements": context_elements})

        slack_payload: dict[str, Any] = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [{"color": color, "blocks": blocks}],
        }

        if self.channel:
            slack_payload["channel"] = self.channel

        return slack_payload


class ConsoleNotifier(Notifier):
    """
    Simple console notifier for testing/development.

    Example:
        notifier = ConsoleNotifier()
        await notifier.notify_deployment_success(app="myapp", tag="v1.0.0")
    """

    async def send(self, payload: NotificationPayload) -> bool:
        """Print notification to console."""
        level_symbols = {
            NotificationLevel.INFO: "ℹ️ ",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️ ",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }

        symbol = level_symbols.get(payload.level, "📋")

        print(f"\n{'='*60}")
        print(f"{symbol} {payload.title}")
        print(f"{'='*60}")
        print(payload.message)
        if payload.url:
            print(f"\nURL: {payload.url}")
        if payload.details:
            print(f"\nDetails: {payload.details}")
        print(f"{'='*60}\n")

        return True


class CompositeNotifier(Notifier):
    """
    Send notifications to multiple channels.

    Example:
        notifier = CompositeNotifier([
            SlackNotifier(webhook_url="..."),
            ConsoleNotifier(),
        ])
        await notifier.notify_deployment_success(app="myapp", tag="v1.0.0")
    """

    def __init__(self, notifiers: list[Notifier]):
        self.notifiers = notifiers

    async def send(self, payload: NotificationPayload) -> bool:
        """Send to all notifiers."""
        import asyncio

        results = await asyncio.gather(
            *[n.send(payload) for n in self.notifiers],
            return_exceptions=True,
        )

        # Return True if at least one succeeded
        return any(r is True for r in results)
