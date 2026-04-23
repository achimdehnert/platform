"""Telegram Bot notification channel (ADR-088).

Requires: TELEGRAM_BOT_TOKEN in Django settings (ADR-045).
"""

from __future__ import annotations

import logging

import httpx

from platform_notifications.channels.base import BaseChannel

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramChannel(BaseChannel):
    """Telegram notifications via Bot API.

    recipient = chat_id (string or numeric).
    """

    name = "telegram"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """Send message via Telegram Bot API."""
        token = self._get_bot_token()
        text = f"*{subject}*\n{body}" if subject else body
        url = f"{TELEGRAM_API_BASE}{token}/sendMessage"

        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                url,
                json={
                    "chat_id": recipient,
                    "text": text[:4096],
                    "parse_mode": "Markdown",
                },
            )
            response.raise_for_status()
        return True

    def validate_recipient(self, recipient: str) -> bool:
        """Validate Telegram chat_id (numeric string, optionally negative)."""
        cleaned = recipient.lstrip("-")
        return cleaned.isdigit() and len(cleaned) <= 20

    def health_check(self) -> dict[str, bool | str]:
        """Check Telegram bot token is configured."""
        try:
            self._get_bot_token()
            return {"healthy": True, "channel": self.name}
        except Exception as exc:
            return {
                "healthy": False,
                "channel": self.name,
                "error": str(exc),
            }

    def _get_bot_token(self) -> str:
        from django.conf import settings

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        return token
