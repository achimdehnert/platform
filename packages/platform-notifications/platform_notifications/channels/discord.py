"""Discord webhook notification channel (ADR-088).

Requires: DISCORD_WEBHOOK_URL in Django settings (ADR-045).
"""

from __future__ import annotations

import logging

import httpx

from platform_notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class DiscordChannel(BaseChannel):
    """Discord notifications via webhook URL."""

    name = "discord"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """Post message to Discord webhook.

        recipient = webhook URL (per-channel or per-tenant).
        """
        content = f"**{subject}**\n{body}" if subject else body
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                recipient,
                json={"content": content[:2000]},
            )
            response.raise_for_status()
        return True

    def validate_recipient(self, recipient: str) -> bool:
        """Validate Discord webhook URL format."""
        return (
            recipient.startswith("https://discord.com/api/webhooks/")
            or recipient.startswith("https://discordapp.com/api/webhooks/")
        )

    def health_check(self) -> dict[str, bool | str]:
        """Check Discord webhook URL is configured."""
        try:
            from django.conf import settings

            url = getattr(settings, "DISCORD_WEBHOOK_URL", "")
            return {
                "healthy": bool(url),
                "channel": self.name,
            }
        except Exception as exc:
            return {
                "healthy": False,
                "channel": self.name,
                "error": str(exc),
            }
