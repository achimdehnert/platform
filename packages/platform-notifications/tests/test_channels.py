"""Tests for built-in notification channels."""

import pytest

from platform_notifications.channels.email import EmailChannel
from platform_notifications.channels.webhook import WebhookChannel


class TestEmailChannel:
    """Tests for EmailChannel."""

    def test_should_validate_email(self) -> None:
        ch = EmailChannel()
        assert ch.validate_recipient("user@example.com") is True
        assert ch.validate_recipient("not-an-email") is False
        assert ch.validate_recipient("") is False

    @pytest.mark.django_db
    def test_should_deliver_email(self) -> None:
        from django.core import mail

        ch = EmailChannel()
        result = ch.deliver(
            recipient="test@example.com",
            subject="Test",
            body="Hello",
        )
        assert result is True
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Test"

    def test_should_health_check(self) -> None:
        ch = EmailChannel()
        check = ch.health_check()
        assert check["channel"] == "email"
        assert "healthy" in check


class TestWebhookChannel:
    """Tests for WebhookChannel."""

    def test_should_validate_https_url(self) -> None:
        ch = WebhookChannel()
        assert ch.validate_recipient("https://example.com/hook") is True
        assert ch.validate_recipient("http://example.com/hook") is False
        assert ch.validate_recipient("not-a-url") is False

    def test_should_health_check(self) -> None:
        ch = WebhookChannel()
        check = ch.health_check()
        assert check["healthy"] is True


class TestSmsChannel:
    """Tests for SmsChannel recipient validation."""

    def test_should_validate_e164_number(self) -> None:
        try:
            from platform_notifications.channels.sms import SmsChannel
        except ImportError:
            pytest.skip("twilio not installed")
        ch = SmsChannel()
        assert ch.validate_recipient("+4917612345678") is True
        assert ch.validate_recipient("+1234") is True
        assert ch.validate_recipient("017612345678") is False
        assert ch.validate_recipient("") is False
