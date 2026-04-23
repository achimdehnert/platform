"""Shared fixtures for platform-notifications tests."""

import pytest

from platform_notifications.registry import ChannelRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset singleton registry between tests."""
    ChannelRegistry.reset()
