"""
Deployment Core - Shared deployment utilities for BF Agent Platform.

This package provides:
- Health check probes (HTTP, TCP, Command)
- AI-powered error analysis (Claude integration)
- Smart rollback strategies
- Unified notifications (Slack, Email)

Example:
    from deployment_core import HealthChecker, HTTPProbe, ErrorAnalyzer

    # Health checks
    checker = HealthChecker(timeout=30)
    checker.add_probe(HTTPProbe("https://app.example.com/health/"))
    result = await checker.run()

    # Error analysis
    analyzer = ErrorAnalyzer(api_key="...")
    analysis = await analyzer.analyze(error_log)
    if analysis.can_auto_fix:
        await analyzer.execute_fix(analysis)
"""

from deployment_core.health import (
    HealthChecker,
    HealthProbe,
    HealthResult,
    HealthStatus,
    HTTPProbe,
    TCPProbe,
    CommandProbe,
    CompositeProbe,
)
from deployment_core.healing import (
    ErrorAnalyzer,
    ErrorAnalysis,
    ErrorCategory,
    FixAction,
    HetznerPatterns,
)
from deployment_core.rollback import (
    RollbackManager,
    RollbackStrategy,
    RollbackResult,
)
from deployment_core.notify import (
    Notifier,
    SlackNotifier,
    NotificationLevel,
)

__version__ = "0.1.0"
__all__ = [
    # Health
    "HealthChecker",
    "HealthProbe",
    "HealthResult",
    "HealthStatus",
    "HTTPProbe",
    "TCPProbe",
    "CommandProbe",
    "CompositeProbe",
    # Healing
    "ErrorAnalyzer",
    "ErrorAnalysis",
    "ErrorCategory",
    "FixAction",
    "HetznerPatterns",
    # Rollback
    "RollbackManager",
    "RollbackStrategy",
    "RollbackResult",
    # Notifications
    "Notifier",
    "SlackNotifier",
    "NotificationLevel",
]
