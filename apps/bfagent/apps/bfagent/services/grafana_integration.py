"""
Grafana Integration Service - Proactive Intelligence
Monitoring, alerting, and error pattern detection
Integrated: December 9, 2025
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GrafanaIntegrationService:
    """
    Grafana Integration for bfagent

    Features:
    - Dashboard management
    - Prometheus/Loki queries
    - Error pattern detection (Sift)
    - Alerting
    - OnCall integration
    """

    def __init__(self):
        self.enabled = self._check_grafana_configured()
        if self.enabled:
            self._init_grafana()

    def _check_grafana_configured(self) -> bool:
        """Check if Grafana is configured"""
        try:
            from django.conf import settings

            url = getattr(settings, "GRAFANA_URL", "")
            token = getattr(settings, "GRAFANA_TOKEN", "")
            return bool(url and token)
        except:
            return False

    def _init_grafana(self):
        """Initialize Grafana connection"""
        try:
            from django.conf import settings

            self.url = settings.GRAFANA_URL
            self.token = settings.GRAFANA_TOKEN
            self.org_id = getattr(settings, "GRAFANA_ORG_ID", "")

            logger.info(f"Grafana initialized: {self.url}")

        except Exception as e:
            logger.error(f"Failed to initialize Grafana: {e}")
            self.enabled = False

    # ============================================================================
    # DASHBOARD MANAGEMENT
    # ============================================================================

    def create_bfagent_monitoring_dashboard(self) -> Optional[Dict[str, Any]]:
        """
        Create comprehensive monitoring dashboard for bfagent

        Returns:
            Dashboard UID or None
        """
        if not self.enabled:
            logger.warning("Grafana not enabled")
            return None

        dashboard = {
            "dashboard": {
                "title": "bfagent Admin Diagnostics",
                "tags": ["bfagent", "admin", "diagnostics"],
                "timezone": "browser",
                "panels": [
                    self._create_panel(
                        title="Admin URL Response Times",
                        panel_id=1,
                        query="avg(http_request_duration_seconds{job='bfagent',path=~'/admin/.*'})",
                        type="graph",
                    ),
                    self._create_panel(
                        title="Error Rate",
                        panel_id=2,
                        query="rate(errors_total{job='bfagent'}[5m])",
                        type="graph",
                    ),
                    self._create_panel(
                        title="Schema Errors (Last 24h)",
                        panel_id=3,
                        query="count(schema_errors{job='bfagent'})",
                        type="stat",
                    ),
                    self._create_panel(
                        title="Database Performance",
                        panel_id=4,
                        query="avg(db_query_duration_seconds{job='bfagent'})",
                        type="graph",
                    ),
                    self._create_panel(
                        title="Admin Health Status",
                        panel_id=5,
                        query="admin_health_check_passed{job='bfagent'}",
                        type="gauge",
                    ),
                ],
                "refresh": "30s",
            },
            "overwrite": True,
        }

        # This is a placeholder - actual implementation would use Grafana API
        logger.info("Dashboard creation requested (requires Grafana MCP)")

        return {
            "status": "pending",
            "message": "Dashboard creation requires Grafana MCP integration",
            "dashboard": dashboard,
        }

    def _create_panel(
        self, title: str, panel_id: int, query: str, type: str = "graph"
    ) -> Dict[str, Any]:
        """Create a dashboard panel configuration"""
        return {
            "id": panel_id,
            "title": title,
            "type": type,
            "targets": [
                {
                    "expr": query,
                    "refId": "A",
                }
            ],
            "gridPos": {
                "h": 8,
                "w": 12,
                "x": (panel_id - 1) % 2 * 12,
                "y": ((panel_id - 1) // 2) * 8,
            },
        }

    # ============================================================================
    # ERROR PATTERN DETECTION (SIFT)
    # ============================================================================

    def find_error_patterns(
        self, time_range: str = "24h", app: str = "bfagent"
    ) -> List[Dict[str, Any]]:
        """
        Find elevated error patterns using Sift

        Args:
            time_range: Time range to analyze (e.g., "24h", "1w")
            app: Application name

        Returns:
            List of detected patterns
        """
        if not self.enabled:
            logger.warning("Grafana not enabled")
            return []

        # Placeholder for Sift integration
        logger.info(f"Error pattern detection requested for {app} ({time_range})")

        return [
            {
                "status": "pending",
                "message": "Error pattern detection requires Grafana MCP with Sift",
                "time_range": time_range,
                "app": app,
            }
        ]

    def detect_admin_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect anomalies in admin behavior

        Returns:
            List of detected anomalies
        """
        if not self.enabled:
            return []

        # Placeholder for anomaly detection
        patterns = [
            {
                "type": "slow_response",
                "description": "Admin pages responding slower than usual",
                "threshold": "2s",
                "current": "p95 > 2s detected",
            },
            {
                "type": "error_spike",
                "description": "Elevated error rate detected",
                "threshold": "5%",
                "current": "error_rate > 5% detected",
            },
        ]

        logger.info(f"Detected {len(patterns)} anomalies")
        return patterns

    # ============================================================================
    # ALERTING
    # ============================================================================

    def create_alert_rule(
        self, name: str, condition: str, notification_channel: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Create an alert rule

        Args:
            name: Alert name
            condition: Alert condition (PromQL)
            notification_channel: Where to send alerts

        Returns:
            Alert rule ID or None
        """
        if not self.enabled:
            return None

        alert = {
            "name": name,
            "condition": condition,
            "notification_channel": notification_channel,
            "status": "pending",
        }

        logger.info(f"Alert rule creation requested: {name}")

        return alert

    def get_default_alerts(self) -> List[Dict[str, Any]]:
        """Get default alert rules for bfagent"""
        return [
            {
                "name": "Slow Admin Pages",
                "condition": 'avg(http_request_duration_seconds{path=~"/admin/.*"}) > 2',
                "severity": "warning",
                "description": "Admin pages taking > 2s to respond",
            },
            {
                "name": "High Error Rate",
                "condition": "rate(errors_total[5m]) > 0.05",
                "severity": "critical",
                "description": "Error rate > 5%",
            },
            {
                "name": "Schema Issues Detected",
                "condition": "schema_errors_total > 0",
                "severity": "warning",
                "description": "Database schema mismatches detected",
            },
            {
                "name": "Admin Health Check Failed",
                "condition": "admin_health_check_passed == 0",
                "severity": "critical",
                "description": "Admin diagnostics health check failing",
            },
        ]

    # ============================================================================
    # ONCALL INTEGRATION
    # ============================================================================

    def get_oncall_users(self, schedule: str = "platform") -> List[str]:
        """
        Get currently oncall users

        Args:
            schedule: OnCall schedule name

        Returns:
            List of oncall usernames
        """
        if not self.enabled:
            return []

        # Placeholder
        logger.info(f"OnCall query requested for schedule: {schedule}")

        return []

    def create_incident(
        self, title: str, severity: str = "high", description: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Grafana Incident

        Args:
            title: Incident title
            severity: Severity level
            description: Optional description

        Returns:
            Incident ID or None
        """
        if not self.enabled:
            return None

        incident = {
            "title": title,
            "severity": severity,
            "description": description or title,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }

        logger.info(f"Incident creation requested: {title}")

        return incident

    # ============================================================================
    # METRICS EXPORT (for Prometheus)
    # ============================================================================

    def export_admin_diagnostics_metrics(self, diagnostics_results: Dict[str, Any]):
        """
        Export admin diagnostics results as Prometheus metrics

        Args:
            diagnostics_results: Results from admin_diagnostics
        """
        if not self.enabled:
            return

        # This would export metrics to Prometheus
        # Placeholder for now

        metrics = {
            "admin_urls_tested": len(diagnostics_results.get("tested", [])),
            "admin_errors_found": len(diagnostics_results.get("errors", [])),
            "admin_fixes_applied": len(diagnostics_results.get("fixed", [])),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Metrics export: {metrics}")

    # ============================================================================
    # UTILITY
    # ============================================================================

    def is_enabled(self) -> bool:
        """Check if Grafana is enabled"""
        return self.enabled

    def get_stats(self) -> Dict[str, Any]:
        """Get Grafana integration stats"""
        return {
            "enabled": self.enabled,
            "url": getattr(self, "url", None),
            "configured": self._check_grafana_configured(),
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        if not self.enabled:
            return {"status": "disabled", "message": "Grafana not configured"}

        # Placeholder for actual health check
        return {
            "status": "pending",
            "message": "Health check requires Grafana MCP",
            "url": getattr(self, "url", None),
        }


# Global singleton
_grafana_service = None


def get_grafana_service() -> GrafanaIntegrationService:
    """Get or create the global Grafana service instance"""
    global _grafana_service
    if _grafana_service is None:
        _grafana_service = GrafanaIntegrationService()
    return _grafana_service
