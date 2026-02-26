"""Tests for ChannelRegistry."""

import threading

import pytest

from platform_notifications.channels.base import BaseChannel
from platform_notifications.registry import ChannelRegistry


class FakeChannel(BaseChannel):
    """Test channel implementation."""

    name = "fake"

    def deliver(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: object,
    ) -> bool:
        return True

    def validate_recipient(self, recipient: str) -> bool:
        return recipient == "valid"


class TestChannelRegistry:
    """Tests for ChannelRegistry."""

    def test_should_register_and_get_channel(self) -> None:
        registry = ChannelRegistry.get_instance()
        channel = FakeChannel()
        registry.register(channel)
        assert registry.get("fake") is channel

    def test_should_raise_on_unknown_channel(self) -> None:
        registry = ChannelRegistry.get_instance()
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent")

    def test_should_list_channels(self) -> None:
        registry = ChannelRegistry.get_instance()
        registry.register(FakeChannel())
        assert "fake" in registry.list_channels()

    def test_should_be_singleton(self) -> None:
        r1 = ChannelRegistry.get_instance()
        r2 = ChannelRegistry.get_instance()
        assert r1 is r2

    def test_should_reset_singleton(self) -> None:
        r1 = ChannelRegistry.get_instance()
        r1.register(FakeChannel())
        ChannelRegistry.reset()
        r2 = ChannelRegistry.get_instance()
        assert r1 is not r2
        assert r2.list_channels() == []

    def test_should_health_check_all(self) -> None:
        registry = ChannelRegistry.get_instance()
        registry.register(FakeChannel())
        checks = registry.health_check_all()
        assert checks["fake"]["healthy"] is True

    def test_should_be_thread_safe(self) -> None:
        registry = ChannelRegistry.get_instance()
        errors: list[Exception] = []

        def register_channel(i: int) -> None:
            try:
                ch = FakeChannel()
                ch.name = f"ch_{i}"
                registry.register(ch)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register_channel, args=(i,))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(registry.list_channels()) == 20
