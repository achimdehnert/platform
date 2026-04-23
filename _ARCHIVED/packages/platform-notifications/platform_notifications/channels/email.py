"""Email notification channel (ADR-088)."""

from __future__ import annotations

from platform_notifications.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Email channel via Django send_mail."""

    name = "email"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        """Send email via Django mail backend."""
        from django.core.mail import send_mail

        send_mail(
            subject,
            body,
            None,
            [recipient],
            fail_silently=False,
        )
        return True

    def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        from django.core.validators import validate_email

        try:
            validate_email(recipient)
            return True
        except Exception:
            return False

    def health_check(self) -> dict[str, bool | str]:
        """Check Django email backend is configured."""
        from django.conf import settings

        has_backend = bool(
            getattr(settings, "EMAIL_BACKEND", None)
        )
        return {"healthy": has_backend, "channel": self.name}
