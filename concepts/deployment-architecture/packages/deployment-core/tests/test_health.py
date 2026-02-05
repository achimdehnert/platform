"""Tests for deployment_core.health module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deployment_core.health import (
    CommandProbe,
    CompositeProbe,
    HealthChecker,
    HealthResult,
    HealthStatus,
    HTTPProbe,
    TCPProbe,
)


class TestHealthResult:
    """Tests for HealthResult dataclass."""

    def test_is_healthy_true(self):
        result = HealthResult(status=HealthStatus.HEALTHY, name="test")
        assert result.is_healthy is True

    def test_is_healthy_false(self):
        result = HealthResult(status=HealthStatus.UNHEALTHY, name="test")
        assert result.is_healthy is False

    def test_to_dict(self):
        result = HealthResult(
            status=HealthStatus.HEALTHY,
            name="test",
            message="OK",
            latency_ms=100.5,
        )
        data = result.to_dict()

        assert data["status"] == "healthy"
        assert data["name"] == "test"
        assert data["message"] == "OK"
        assert data["latency_ms"] == 100.5


class TestHTTPProbe:
    """Tests for HTTPProbe."""

    @pytest.mark.asyncio
    async def test_successful_check(self):
        probe = HTTPProbe("https://example.com/health/", timeout=5.0)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await probe.check()

            assert result.is_healthy
            assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_unexpected_status_code(self):
        probe = HTTPProbe("https://example.com/health/", expected_status=200)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await probe.check()

            assert not result.is_healthy
            assert result.status == HealthStatus.UNHEALTHY
            assert "500" in result.message

    @pytest.mark.asyncio
    async def test_expected_body_check(self):
        probe = HTTPProbe(
            "https://example.com/health/",
            expected_body="healthy",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "healthy"}'
            mock_response.json.return_value = {"status": "healthy"}

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await probe.check()

            assert result.is_healthy

    @pytest.mark.asyncio
    async def test_missing_expected_body(self):
        probe = HTTPProbe(
            "https://example.com/health/",
            expected_body="healthy",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "degraded"}'

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await probe.check()

            assert not result.is_healthy
            assert "Expected body content not found" in result.message


class TestTCPProbe:
    """Tests for TCPProbe."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        probe = TCPProbe("localhost", 8080, timeout=5.0)

        with patch.object(probe, "_connect"):
            result = await probe.check()

            assert result.is_healthy
            assert "8080" in result.message

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        probe = TCPProbe("localhost", 9999, timeout=1.0)

        with patch.object(
            probe, "_connect", side_effect=ConnectionRefusedError("Connection refused")
        ):
            result = await probe.check()

            assert not result.is_healthy
            assert "Connection refused" in str(result.error) or "failed" in result.message.lower()


class TestCommandProbe:
    """Tests for CommandProbe."""

    @pytest.mark.asyncio
    async def test_successful_command(self):
        probe = CommandProbe("echo hello", timeout=5.0)

        result = await probe.check()

        assert result.is_healthy
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_failed_command(self):
        probe = CommandProbe("exit 1", expected_exit_code=0)

        result = await probe.check()

        assert not result.is_healthy
        assert "exit code" in result.message.lower() or result.details.get("exit_code") != 0

    @pytest.mark.asyncio
    async def test_expected_output(self):
        probe = CommandProbe("echo hello world", expected_output="hello")

        result = await probe.check()

        assert result.is_healthy

    @pytest.mark.asyncio
    async def test_missing_expected_output(self):
        probe = CommandProbe("echo hello", expected_output="goodbye")

        result = await probe.check()

        assert not result.is_healthy
        assert "Expected output not found" in result.message


class TestCompositeProbe:
    """Tests for CompositeProbe."""

    @pytest.mark.asyncio
    async def test_all_healthy_require_all(self):
        probe1 = MagicMock(spec=HTTPProbe)
        probe1.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe1")
        )

        probe2 = MagicMock(spec=TCPProbe)
        probe2.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe2")
        )

        composite = CompositeProbe([probe1, probe2], require_all=True)
        result = await composite.check()

        assert result.is_healthy
        assert "2/2" in result.message

    @pytest.mark.asyncio
    async def test_one_unhealthy_require_all(self):
        probe1 = MagicMock(spec=HTTPProbe)
        probe1.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe1")
        )

        probe2 = MagicMock(spec=TCPProbe)
        probe2.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.UNHEALTHY, name="probe2")
        )

        composite = CompositeProbe([probe1, probe2], require_all=True)
        result = await composite.check()

        assert not result.is_healthy
        assert "1/2" in result.message

    @pytest.mark.asyncio
    async def test_one_healthy_require_any(self):
        probe1 = MagicMock(spec=HTTPProbe)
        probe1.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe1")
        )

        probe2 = MagicMock(spec=TCPProbe)
        probe2.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.UNHEALTHY, name="probe2")
        )

        composite = CompositeProbe([probe1, probe2], require_all=False)
        result = await composite.check()

        assert result.is_healthy


class TestHealthChecker:
    """Tests for HealthChecker."""

    @pytest.mark.asyncio
    async def test_no_probes(self):
        checker = HealthChecker()
        result = await checker.run()

        assert result.status == HealthStatus.UNKNOWN
        assert "No probes configured" in result.message

    @pytest.mark.asyncio
    async def test_all_probes_pass(self):
        checker = HealthChecker(retries=1, interval=0.1)

        probe1 = MagicMock(spec=HTTPProbe)
        probe1.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe1")
        )

        probe2 = MagicMock(spec=TCPProbe)
        probe2.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.HEALTHY, name="probe2")
        )

        checker.add_probe(probe1)
        checker.add_probe(probe2)

        result = await checker.run()

        assert result.is_healthy
        assert "2 checks passed" in result.message

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        checker = HealthChecker(retries=3, interval=0.1)

        call_count = 0

        async def check_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return HealthResult(status=HealthStatus.UNHEALTHY, name="probe")
            return HealthResult(status=HealthStatus.HEALTHY, name="probe")

        probe = MagicMock(spec=HTTPProbe)
        probe.check = check_with_retry

        checker.add_probe(probe)
        result = await checker.run()

        assert result.is_healthy
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        checker = HealthChecker(retries=2, interval=0.1)

        probe = MagicMock(spec=HTTPProbe)
        probe.name = "failing_probe"
        probe.check = AsyncMock(
            return_value=HealthResult(status=HealthStatus.UNHEALTHY, name="failing_probe")
        )

        checker.add_probe(probe)
        result = await checker.run()

        assert not result.is_healthy
        assert "failed after 2 attempts" in result.message

    def test_add_probe_returns_self(self):
        checker = HealthChecker()
        probe = MagicMock(spec=HTTPProbe)

        result = checker.add_probe(probe)

        assert result is checker
