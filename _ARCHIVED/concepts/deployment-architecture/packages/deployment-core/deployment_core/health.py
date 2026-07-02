"""
Health check probes and checker for deployment verification.

This module provides various health check probes:
- HTTPProbe: HTTP/HTTPS endpoint checks
- TCPProbe: TCP port connectivity checks
- CommandProbe: Shell command execution checks
- CompositeProbe: Combine multiple probes

Example:
    checker = HealthChecker(timeout=30, retries=5)
    checker.add_probe(HTTPProbe("https://app.example.com/health/"))
    checker.add_probe(TCPProbe("localhost", 5432, name="postgres"))

    result = await checker.run()
    if result.is_healthy:
        print("All checks passed!")
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class HealthStatus(Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthResult:
    """Result of a health check."""

    status: HealthStatus
    name: str
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if status is healthy."""
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "name": self.name,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


class HealthProbe(ABC):
    """Base class for health probes."""

    def __init__(self, name: str = "probe", timeout: float = 10.0):
        self.name = name
        self.timeout = timeout

    @abstractmethod
    async def check(self) -> HealthResult:
        """Execute the health check."""
        pass


class HTTPProbe(HealthProbe):
    """HTTP/HTTPS health check probe."""

    def __init__(
        self,
        url: str,
        *,
        name: str | None = None,
        timeout: float = 10.0,
        expected_status: int = 200,
        expected_body: str | None = None,
        headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
    ):
        super().__init__(name=name or url, timeout=timeout)
        self.url = url
        self.expected_status = expected_status
        self.expected_body = expected_body
        self.headers = headers or {}
        self.verify_ssl = verify_ssl

    async def check(self) -> HealthResult:
        """Execute HTTP health check."""
        start = asyncio.get_event_loop().time()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl,
            ) as client:
                response = await client.get(self.url, headers=self.headers)

                latency = (asyncio.get_event_loop().time() - start) * 1000

                # Check status code
                if response.status_code != self.expected_status:
                    return HealthResult(
                        status=HealthStatus.UNHEALTHY,
                        name=self.name,
                        message=f"Unexpected status: {response.status_code}",
                        latency_ms=latency,
                        details={
                            "url": self.url,
                            "status_code": response.status_code,
                            "expected": self.expected_status,
                        },
                    )

                # Check body content
                if self.expected_body and self.expected_body not in response.text:
                    return HealthResult(
                        status=HealthStatus.UNHEALTHY,
                        name=self.name,
                        message="Expected body content not found",
                        latency_ms=latency,
                        details={"url": self.url, "expected_body": self.expected_body},
                    )

                # Try to parse JSON response for details
                details: dict[str, Any] = {"url": self.url, "status_code": response.status_code}
                try:
                    json_body = response.json()
                    if isinstance(json_body, dict):
                        details.update(json_body)
                except Exception:
                    pass

                return HealthResult(
                    status=HealthStatus.HEALTHY,
                    name=self.name,
                    message="OK",
                    latency_ms=latency,
                    details=details,
                )

        except httpx.TimeoutException:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message="Request timed out",
                latency_ms=self.timeout * 1000,
                error="TimeoutException",
                details={"url": self.url, "timeout": self.timeout},
            )
        except httpx.ConnectError as e:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message="Connection failed",
                error=str(e),
                details={"url": self.url},
            )
        except Exception as e:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message=f"Unexpected error: {type(e).__name__}",
                error=str(e),
                details={"url": self.url},
            )


class TCPProbe(HealthProbe):
    """TCP port connectivity check."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        name: str | None = None,
        timeout: float = 5.0,
    ):
        super().__init__(name=name or f"tcp://{host}:{port}", timeout=timeout)
        self.host = host
        self.port = port

    async def check(self) -> HealthResult:
        """Execute TCP connectivity check."""
        start = asyncio.get_event_loop().time()

        try:
            # Run socket connection in thread pool
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, self._connect),
                timeout=self.timeout,
            )

            latency = (asyncio.get_event_loop().time() - start) * 1000

            return HealthResult(
                status=HealthStatus.HEALTHY,
                name=self.name,
                message=f"Port {self.port} is open",
                latency_ms=latency,
                details={"host": self.host, "port": self.port},
            )

        except asyncio.TimeoutError:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message="Connection timed out",
                latency_ms=self.timeout * 1000,
                error="TimeoutError",
                details={"host": self.host, "port": self.port},
            )
        except Exception as e:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message=f"Connection failed: {e}",
                error=str(e),
                details={"host": self.host, "port": self.port},
            )

    def _connect(self) -> None:
        """Synchronous socket connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
        finally:
            sock.close()


class CommandProbe(HealthProbe):
    """Shell command health check."""

    def __init__(
        self,
        command: str | list[str],
        *,
        name: str | None = None,
        timeout: float = 30.0,
        expected_exit_code: int = 0,
        expected_output: str | None = None,
    ):
        cmd_name = command if isinstance(command, str) else " ".join(command[:2])
        super().__init__(name=name or f"cmd:{cmd_name}", timeout=timeout)
        self.command = command
        self.expected_exit_code = expected_exit_code
        self.expected_output = expected_output

    async def check(self) -> HealthResult:
        """Execute command health check."""
        start = asyncio.get_event_loop().time()

        try:
            # Run command
            if isinstance(self.command, str):
                proc = await asyncio.create_subprocess_shell(
                    self.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *self.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                return HealthResult(
                    status=HealthStatus.UNHEALTHY,
                    name=self.name,
                    message="Command timed out",
                    latency_ms=self.timeout * 1000,
                    error="TimeoutError",
                    details={"command": self.command},
                )

            latency = (asyncio.get_event_loop().time() - start) * 1000
            output = stdout.decode() if stdout else ""
            error_output = stderr.decode() if stderr else ""

            # Check exit code
            if proc.returncode != self.expected_exit_code:
                return HealthResult(
                    status=HealthStatus.UNHEALTHY,
                    name=self.name,
                    message=f"Unexpected exit code: {proc.returncode}",
                    latency_ms=latency,
                    error=error_output[:500] if error_output else None,
                    details={
                        "command": self.command,
                        "exit_code": proc.returncode,
                        "expected": self.expected_exit_code,
                    },
                )

            # Check output
            if self.expected_output and self.expected_output not in output:
                return HealthResult(
                    status=HealthStatus.UNHEALTHY,
                    name=self.name,
                    message="Expected output not found",
                    latency_ms=latency,
                    details={
                        "command": self.command,
                        "expected_output": self.expected_output,
                    },
                )

            return HealthResult(
                status=HealthStatus.HEALTHY,
                name=self.name,
                message="Command succeeded",
                latency_ms=latency,
                details={
                    "command": self.command,
                    "exit_code": proc.returncode,
                    "output_preview": output[:200] if output else None,
                },
            )

        except Exception as e:
            return HealthResult(
                status=HealthStatus.UNHEALTHY,
                name=self.name,
                message=f"Command failed: {e}",
                error=str(e),
                details={"command": self.command},
            )


class CompositeProbe(HealthProbe):
    """Combine multiple probes with AND/OR logic."""

    def __init__(
        self,
        probes: list[HealthProbe],
        *,
        name: str = "composite",
        require_all: bool = True,
    ):
        super().__init__(name=name)
        self.probes = probes
        self.require_all = require_all

    async def check(self) -> HealthResult:
        """Run all probes and aggregate results."""
        results = await asyncio.gather(*[p.check() for p in self.probes])

        healthy_count = sum(1 for r in results if r.is_healthy)
        total = len(results)

        if self.require_all:
            is_healthy = healthy_count == total
        else:
            is_healthy = healthy_count > 0

        return HealthResult(
            status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
            name=self.name,
            message=f"{healthy_count}/{total} checks passed",
            details={
                "checks": [r.to_dict() for r in results],
                "require_all": self.require_all,
            },
        )


class HealthChecker:
    """
    Health checker that runs multiple probes with retries.

    Example:
        checker = HealthChecker(timeout=60, retries=5, interval=10)
        checker.add_probe(HTTPProbe("https://app.example.com/health/"))
        checker.add_probe(TCPProbe("localhost", 5432, name="postgres"))
        checker.add_probe(TCPProbe("localhost", 6379, name="redis"))

        result = await checker.run()
        if not result.is_healthy:
            print(f"Health check failed: {result.message}")
    """

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        retries: int = 5,
        interval: float = 10.0,
    ):
        self.timeout = timeout
        self.retries = retries
        self.interval = interval
        self.probes: list[HealthProbe] = []

    def add_probe(self, probe: HealthProbe) -> "HealthChecker":
        """Add a probe to the checker."""
        self.probes.append(probe)
        return self

    async def run(self) -> HealthResult:
        """Run all probes with retries."""
        if not self.probes:
            return HealthResult(
                status=HealthStatus.UNKNOWN,
                name="health_checker",
                message="No probes configured",
            )

        start = asyncio.get_event_loop().time()
        last_results: list[HealthResult] = []

        for attempt in range(1, self.retries + 1):
            logger.info("health_check_attempt", attempt=attempt, retries=self.retries)

            # Run all probes concurrently
            last_results = await asyncio.gather(*[p.check() for p in self.probes])

            # Check if all passed
            all_healthy = all(r.is_healthy for r in last_results)

            if all_healthy:
                latency = (asyncio.get_event_loop().time() - start) * 1000
                return HealthResult(
                    status=HealthStatus.HEALTHY,
                    name="health_checker",
                    message=f"All {len(self.probes)} checks passed",
                    latency_ms=latency,
                    details={
                        "attempt": attempt,
                        "checks": [r.to_dict() for r in last_results],
                    },
                )

            # Wait before retry (unless last attempt)
            if attempt < self.retries:
                logger.warning(
                    "health_check_retry",
                    attempt=attempt,
                    failed=[r.name for r in last_results if not r.is_healthy],
                )
                await asyncio.sleep(self.interval)

        # All retries exhausted
        latency = (asyncio.get_event_loop().time() - start) * 1000
        failed_probes = [r for r in last_results if not r.is_healthy]

        return HealthResult(
            status=HealthStatus.UNHEALTHY,
            name="health_checker",
            message=f"Health check failed after {self.retries} attempts",
            latency_ms=latency,
            error=f"Failed probes: {', '.join(r.name for r in failed_probes)}",
            details={
                "attempts": self.retries,
                "checks": [r.to_dict() for r in last_results],
            },
        )
