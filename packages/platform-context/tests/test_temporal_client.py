"""
Tests für platform_context.temporal_client — ADR-077
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTemporalClientModule:
    def test_default_address_from_env(self):
        import platform_context.temporal_client as mod
        assert mod.TEMPORAL_ADDRESS in ("temporal:7233", "localhost:7233")

    def test_default_namespace_from_env(self):
        import platform_context.temporal_client as mod
        assert mod.TEMPORAL_NAMESPACE in ("platform-dev", "default")

    def test_env_override_address(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_ADDRESS", "myhost:7233")
        import importlib
        import platform_context.temporal_client as mod
        importlib.reload(mod)
        assert mod.TEMPORAL_ADDRESS == "myhost:7233"

    def test_env_override_namespace(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-namespace")
        import importlib
        import platform_context.temporal_client as mod
        importlib.reload(mod)
        assert mod.TEMPORAL_NAMESPACE == "my-namespace"

    def test_reset_temporal_client(self):
        from platform_context.temporal_client import reset_temporal_client
        import platform_context.temporal_client as mod
        mod._client = MagicMock()
        reset_temporal_client()
        assert mod._client is None

    def test_import_error_without_temporalio(self, monkeypatch):
        """Wenn temporalio nicht installiert → ImportError mit Hinweis."""
        import platform_context.temporal_client as mod
        mod._client = None

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "temporalio.client":
                raise ImportError("No module named 'temporalio'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        import asyncio
        with pytest.raises(ImportError, match="platform-context\\[temporal\\]"):
            asyncio.run(mod.get_temporal_client())

    @pytest.mark.asyncio
    async def test_get_temporal_client_singleton(self):
        """Zweiter Aufruf gibt gecachten Client zurück."""
        import platform_context.temporal_client as mod
        mod._client = None

        mock_client = MagicMock()
        with patch("platform_context.temporal_client.Client") as MockClient:
            MockClient.connect = AsyncMock(return_value=mock_client)

            from platform_context.temporal_client import get_temporal_client
            c1 = await get_temporal_client()
            c2 = await get_temporal_client()

        assert c1 is c2
        assert MockClient.connect.call_count == 1
        mod._client = None

    @pytest.mark.asyncio
    async def test_get_temporal_client_connects_with_correct_params(self):
        import platform_context.temporal_client as mod
        mod._client = None
        mod.TEMPORAL_ADDRESS = "test-host:7233"
        mod.TEMPORAL_NAMESPACE = "test-ns"

        mock_client = MagicMock()
        with patch("platform_context.temporal_client.Client") as MockClient:
            MockClient.connect = AsyncMock(return_value=mock_client)

            from platform_context.temporal_client import get_temporal_client
            await get_temporal_client()

        MockClient.connect.assert_called_once_with("test-host:7233", namespace="test-ns")
        mod._client = None
