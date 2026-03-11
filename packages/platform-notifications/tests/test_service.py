"""Tests for NotificationService."""

from unittest.mock import MagicMock, patch

import pytest

from platform_notifications.channels.base import BaseChannel
from platform_notifications.registry import ChannelRegistry


class MockChannel(BaseChannel):
    """Mock channel for testing."""

    name = "mock"
    delivered: list = []

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        self.delivered.append(
            {"recipient": recipient, "subject": subject, "body": body}
        )
        return True

    def validate_recipient(self, recipient: str) -> bool:
        return recipient.startswith("valid")


@pytest.mark.django_db
class TestNotificationService:
    """Tests for NotificationService."""

    def test_should_reject_invalid_recipient(self) -> None:
        from platform_notifications.service import (
            Notification,
            NotificationService,
        )

        registry = ChannelRegistry.get_instance()
        registry.register(MockChannel())

        with pytest.raises(ValueError, match="Invalid recipient"):
            NotificationService.send(
                Notification(
                    tenant_id="t1",
                    channel="mock",
                    recipient="invalid",
                    body="test",
                    source_app="test",
                    source_event="test",
                )
            )

    def test_should_create_log_and_dispatch(
        self,
    ) -> None:
        from platform_notifications.models import NotificationLog
        from platform_notifications.service import (
            Notification,
            NotificationService,
        )

        registry = ChannelRegistry.get_instance()
        registry.register(MockChannel())

        with patch(
            "platform_notifications.tasks"
            ".dispatch_notification_task"
        ) as mock_task:
            mock_task.delay = MagicMock()
            log_id = NotificationService.send(
                Notification(
                    tenant_id="t1",
                    channel="mock",
                    recipient="valid_user",
                    subject="Test",
                    body="Hello",
                    source_app="test-app",
                    source_event="test_event",
                )
            )

        assert log_id
        log = NotificationLog.objects.get(id=log_id)
        assert log.status == "pending"
        assert log.channel == "mock"
        assert log.source_app == "test-app"

    def test_should_send_sync(self) -> None:
        from platform_notifications.models import NotificationLog
        from platform_notifications.service import (
            Notification,
            NotificationService,
        )

        registry = ChannelRegistry.get_instance()
        mock_ch = MockChannel()
        mock_ch.delivered = []
        registry.register(mock_ch)

        log_id = NotificationService.send_sync(
            Notification(
                tenant_id="t1",
                channel="mock",
                recipient="valid_user",
                subject="Sync Test",
                body="Hello Sync",
                source_app="test-app",
                source_event="test_event",
            )
        )

        log = NotificationLog.objects.get(id=log_id)
        assert log.status == "sent"
        assert len(mock_ch.delivered) == 1
        assert mock_ch.delivered[0]["subject"] == "Sync Test"

    def test_should_health_check(self) -> None:
        from platform_notifications.service import (
            NotificationService,
        )

        registry = ChannelRegistry.get_instance()
        registry.register(MockChannel())

        checks = NotificationService.health_check()
        assert "mock" in checks
        assert checks["mock"]["healthy"] is True
