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


class TestDiscordChannel:
    """Tests for DiscordChannel."""

    def test_should_validate_discord_webhook_url(self) -> None:
        from platform_notifications.channels.discord import DiscordChannel

        ch = DiscordChannel()
        assert ch.validate_recipient(
            "https://discord.com/api/webhooks/123/abc"
        ) is True
        assert ch.validate_recipient(
            "https://discordapp.com/api/webhooks/123/abc"
        ) is True
        assert ch.validate_recipient(
            "https://example.com/hook"
        ) is False
        assert ch.validate_recipient(
            "http://discord.com/api/webhooks/x"
        ) is False

    def test_should_health_check(self) -> None:
        from platform_notifications.channels.discord import DiscordChannel

        ch = DiscordChannel()
        check = ch.health_check()
        assert check["channel"] == "discord"
        assert "healthy" in check


class TestTelegramChannel:
    """Tests for TelegramChannel."""

    def test_should_validate_chat_id(self) -> None:
        from platform_notifications.channels.telegram import TelegramChannel

        ch = TelegramChannel()
        assert ch.validate_recipient("123456789") is True
        assert ch.validate_recipient("-100123456789") is True
        assert ch.validate_recipient("abc") is False
        assert ch.validate_recipient("") is False

    def test_should_health_check_without_token(self) -> None:
        from platform_notifications.channels.telegram import TelegramChannel

        ch = TelegramChannel()
        check = ch.health_check()
        assert check["channel"] == "telegram"
        assert check["healthy"] is False
