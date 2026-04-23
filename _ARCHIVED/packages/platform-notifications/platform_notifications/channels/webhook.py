"""Generic webhook notification channel (ADR-088)."""

from __future__ import annotations

import httpx

from platform_notifications.channels.base import BaseChannel


class WebhookChannel(BaseChannel):
    """Generic HTTPS webhook channel."""

    name = "webhook"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """POST notification payload to webhook URL."""
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                recipient,
                json={
                    "subject": subject,
                    "body": body,
                    **kwargs,
                },
            )
            response.raise_for_status()
        return True

    def validate_recipient(self, recipient: str) -> bool:
        """Validate HTTPS URL."""
        return recipient.startswith("https://")

    def health_check(self) -> dict[str, bool | str]:
        """Webhook health is always true (no persistent connection)."""
        return {"healthy": True, "channel": self.name}
