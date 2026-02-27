import logging
from dataclasses import dataclass, field
from typing import Any

from iil_commons.settings import get_setting

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body: str
    html_body: str | None = None
    from_email: str | None = None
    reply_to: list[str] = field(default_factory=list)


class EmailService:
    """Provider-agnostic email abstraction (ADR-091 Phase 3).

    Provider selection via IIL_COMMONS['EMAIL_PROVIDER']:
      - 'smtp'    — Django's built-in EmailBackend (default)
      - 'resend'  — Resend API (requires resend>=2.0 + RESEND_API_KEY)

    Usage:
        svc = EmailService()
        svc.send(EmailMessage(
            to=["guest@example.com"],
            subject="Your invitation",
            body="Hello!",
            html_body="<p>Hello!</p>",
        ))
    """

    def send(self, message: EmailMessage) -> bool:
        """Send a single email. Returns True on success."""
        provider = get_setting("EMAIL_PROVIDER", "smtp")
        try:
            if provider == "resend":
                return self._send_resend(message)
            return self._send_smtp(message)
        except Exception as exc:
            logger.error("email send failed (provider=%s): %s", provider, exc)
            return False

    def _send_smtp(self, message: EmailMessage) -> bool:
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives

        from_email = message.from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
        )
        mail = EmailMultiAlternatives(
            subject=message.subject,
            body=message.body,
            from_email=from_email,
            to=message.to,
            reply_to=message.reply_to or None,
        )
        if message.html_body:
            mail.attach_alternative(message.html_body, "text/html")
        mail.send(fail_silently=False)
        logger.debug("email sent via smtp to %s", message.to)
        return True

    def _send_resend(self, message: EmailMessage) -> bool:
        try:
            import resend  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "resend package is required for EMAIL_PROVIDER='resend'. "
                "Install with: pip install 'iil-django-commons[email]'"
            ) from exc

        import os

        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        from django.conf import settings

        from_email = message.from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
        )
        params: dict[str, Any] = {
            "from": from_email,
            "to": message.to,
            "subject": message.subject,
            "text": message.body,
        }
        if message.html_body:
            params["html"] = message.html_body
        if message.reply_to:
            params["reply_to"] = message.reply_to

        resend.Emails.send(params)
        logger.debug("email sent via resend to %s", message.to)
        return True
