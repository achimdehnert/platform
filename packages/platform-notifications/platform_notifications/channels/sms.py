"""SMS notification channel via Twilio (ADR-088).

Requires: pip install platform-notifications[sms]
Secrets: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER (ADR-045)
"""

from __future__ import annotations

import re

from platform_notifications.channels.base import BaseChannel

E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


class SmsChannel(BaseChannel):
    """SMS via Twilio. Replaces wedding-hub direct Twilio calls."""

    name = "sms"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """Send SMS via Twilio API."""
        from twilio.rest import Client  # type: ignore[import-untyped]

        client = Client(
            self._get_account_sid(),
            self._get_auth_token(),
        )
        client.messages.create(
            body=body,
            from_=self._get_from_number(),
            to=recipient,
        )
        return True

    def validate_recipient(self, recipient: str) -> bool:
        """Validate E.164 phone number format."""
        return bool(E164_PATTERN.match(recipient))

    def health_check(self) -> dict[str, bool | str]:
        """Check Twilio credentials are configured."""
        try:
            self._get_account_sid()
            return {"healthy": True, "channel": self.name}
        except Exception as exc:
            return {
                "healthy": False,
                "channel": self.name,
                "error": str(exc),
            }

    def _get_account_sid(self) -> str:
        from django.conf import settings
        return settings.TWILIO_ACCOUNT_SID  # type: ignore[attr-defined]

    def _get_auth_token(self) -> str:
        from django.conf import settings
        return settings.TWILIO_AUTH_TOKEN  # type: ignore[attr-defined]

    def _get_from_number(self) -> str:
        from django.conf import settings
        return settings.TWILIO_FROM_NUMBER  # type: ignore[attr-defined]
