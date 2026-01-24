"""
BF Agent MCP Server
===================

Extended MCP Server with Django ORM Integration.
Inherits from bfagent-sqlite-mcp core package and adds Django-specific tools.
"""

import logging

from bfagent_sqlite_mcp import BFAgentSQLiteMCP
from django.conf import settings
from django.db import connection

from .domain_tools import DomainTools

logger = logging.getLogger(__name__)


class BFAgentMCPServer(BFAgentSQLiteMCP):
    """
    Extended MCP Server with Django Integration.

    Inherits all core MCP functionality from BFAgentSQLiteMCP:
    - SQL Operations (CRUD, Query, Transaction)
    - Security (Roles, Permissions, Validation)
    - Connection Pooling
    - Audit Logging
    - Performance Metrics

    Adds Django-specific capabilities:
    - Direct Django ORM access
    - Domain management tools
    - Handler/Workflow queries
    """

    def __init__(self):
        """Initialize MCP server with Django settings."""
        # Get Django database path
        try:
            db_config = settings.DATABASES.get("default", {})
            db_path = str(db_config.get("NAME", "db.sqlite3"))
        except Exception:
            # Fallback if settings not properly loaded
            db_path = "db.sqlite3"

        read_only = getattr(settings, "MCP_READ_ONLY", False)

        # Initialize parent with core functionality
        super().__init__(db_path=db_path, read_only=read_only)

        # Store Django-specific config
        self.pool_size = getattr(settings, "MCP_POOL_SIZE", 10)
        self.debug = getattr(settings, "DEBUG", False)
        self.audit_enabled = getattr(settings, "MCP_AUDIT_ENABLED", True)
        self.metrics_enabled = getattr(settings, "MCP_METRICS_ENABLED", True)

        # Initialize Django ORM tools
        self.domain_tools = DomainTools()

        # Initialize DevOps AI Stack services
        try:
            from apps.bfagent.services.chrome_devtools_integration import get_chrome_service
            from apps.bfagent.services.grafana_integration import get_grafana_service
            from apps.bfagent.services.sentry_integration import get_sentry_service

            self.sentry = get_sentry_service()
            self.grafana = get_grafana_service()
            self.chrome = get_chrome_service()
        except ImportError as e:
            logger.warning(f"DevOps AI Stack not available: {e}")
            self.sentry = None
            self.grafana = None
            self.chrome = None

    def status(self):
        """
        Get comprehensive server status.
        Extends core status with Django-specific info.
        """
        # Get core status
        core_status = super().status() if hasattr(super(), "status") else {}

        # Add Django-specific status
        django_status = {
            "django_version": settings.VERSION if hasattr(settings, "VERSION") else "Unknown",
            "audit_enabled": self.audit_enabled,
            "metrics_enabled": self.metrics_enabled,
            "debug": self.debug,
        }

        return {**core_status, **django_status}

    def test_connection(self):
        """Test database connection."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            return False

    # =========================================================================
    # Django ORM Tools (MCP Tool Methods)
    # =========================================================================

    def get_domains(self, active_only=True):
        """
        MCP Tool: Get all domains.

        Args:
            active_only: Only return active domains

        Returns:
            List of domain dicts
        """
        if active_only:
            return self.domain_tools.get_active_domains()
        else:
            # Would need to extend DomainTools
            return self.domain_tools.get_active_domains()

    def get_domain_by_slug(self, slug: str):
        """
        MCP Tool: Get domain by slug.

        Args:
            slug: Domain slug

        Returns:
            Domain dict or None
        """
        return self.domain_tools.get_domain_by_slug(slug)

    def get_domain_stats(self):
        """
        MCP Tool: Get domain statistics.

        Returns:
            Dict with domain counts
        """
        return self.domain_tools.get_domain_statistics()

    def search_domains(self, query: str):
        """
        MCP Tool: Search domains by name/description.

        Args:
            query: Search query

        Returns:
            List of matching domains
        """
        return self.domain_tools.search_domains(query)

    # =========================================================================
    # DevOps AI Stack Tools (Sentry, Grafana, Chrome DevTools)
    # =========================================================================

    def sentry_capture_error(self, error_message: str, context: dict = None):
        """
        MCP Tool: Capture error in Sentry.

        Args:
            error_message: Error message
            context: Additional context dict

        Returns:
            Event ID or None
        """
        if not self.sentry or not self.sentry.is_enabled():
            return {
                "status": "disabled",
                "message": "Sentry not configured. Set SENTRY_DSN in .env",
            }

        try:
            event_id = self.sentry.capture_message(error_message, context=context or {})
            return {
                "status": "success",
                "event_id": event_id,
                "sentry_url": f"https://sentry.io/issues/?query={event_id}" if event_id else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def sentry_get_stats(self):
        """
        MCP Tool: Get Sentry integration stats.

        Returns:
            Sentry stats dict
        """
        if not self.sentry:
            return {"enabled": False, "message": "Sentry service not available"}

        return self.sentry.get_stats()

    def grafana_create_dashboard(self):
        """
        MCP Tool: Create Grafana monitoring dashboard.

        Returns:
            Dashboard creation result
        """
        if not self.grafana or not self.grafana.is_enabled():
            return {
                "status": "disabled",
                "message": "Grafana not configured. Set GRAFANA_URL and GRAFANA_TOKEN in .env",
            }

        try:
            result = self.grafana.create_bfagent_monitoring_dashboard()
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def grafana_get_alerts(self):
        """
        MCP Tool: Get default alert rules.

        Returns:
            List of alert rules
        """
        if not self.grafana:
            return {"enabled": False, "message": "Grafana service not available"}

        return {"status": "success", "alerts": self.grafana.get_default_alerts()}

    def chrome_test_page(self, url: str):
        """
        MCP Tool: Test a page with Chrome DevTools.

        Args:
            url: URL to test

        Returns:
            Test results including screenshot, console errors, etc.
        """
        if not self.chrome:
            return {"enabled": False, "message": "Chrome DevTools service not available"}

        try:
            result = self.chrome.test_admin_page(url)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def chrome_measure_performance(self, url: str):
        """
        MCP Tool: Measure page performance.

        Args:
            url: URL to measure

        Returns:
            Performance metrics (LCP, FID, CLS, etc.)
        """
        if not self.chrome:
            return {"enabled": False, "message": "Chrome DevTools service not available"}

        try:
            result = self.chrome.measure_performance(url)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def admin_ultimate_check(self, app_label: str = None):
        """
        MCP Tool: Run ultimate admin health check.

        Combines all DevOps AI Stack tools for comprehensive diagnostics.

        Args:
            app_label: App to check (e.g., 'writing_hub')

        Returns:
            Complete health check report
        """
        try:
            from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics

            admin = get_admin_diagnostics()
            results = admin.ultimate_health_check(
                app_label=app_label, auto_fix=False, visual_testing=False
            )

            return results
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # Server Lifecycle
    # =========================================================================

    def run(self):
        """Run the MCP server with full protocol support."""
        print(f"🚀 BF Agent MCP Server v2.0")
        print(f"   Core Package: bfagent-sqlite-mcp v2.0.0")
        print(f"   Database: {self.db_path}")
        print(f"   Read-Only: {self.read_only}")
        print(f"   Pool Size: {self.pool_size}")
        print(f"   Audit: {'✅' if self.audit_enabled else '❌'}")
        print(f"   Metrics: {'✅' if self.metrics_enabled else '❌'}")
        print()

        if self.test_connection():
            print("✅ Database connection OK")
        else:
            print("❌ Database connection FAILED")
            return

        print()
        print("📋 Available MCP Tools:")
        print("   Core SQLite:")
        print("     - execute_query")
        print("     - get_schema")
        print("     - analyze_table")
        print("   Django ORM:")
        print("     - get_domains")
        print("     - get_domain_by_slug")
        print("     - get_domain_stats")
        print("     - search_domains")

        # Show DevOps AI Stack tools if available
        devops_tools = []
        if self.sentry:
            devops_tools.append("Sentry (sentry_capture_error, sentry_get_stats)")
        if self.grafana:
            devops_tools.append("Grafana (grafana_create_dashboard, grafana_get_alerts)")
        if self.chrome:
            devops_tools.append("Chrome DevTools (chrome_test_page, chrome_measure_performance)")

        if devops_tools:
            print("   DevOps AI Stack:")
            for tool in devops_tools:
                print(f"     - {tool}")
            print("     - admin_ultimate_check")

        print()
        print("🎯 Server ready for MCP protocol requests...")
        print("   Press Ctrl+C to stop")

        try:
            # Call parent run if it exists
            if hasattr(super(), "run"):
                super().run()
            else:
                # Fallback: simple keep-alive
                import time

                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down MCP server...")
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown server and cleanup resources."""
        print("🧹 Cleaning up...")

        # Call parent shutdown if exists
        if hasattr(super(), "shutdown"):
            super().shutdown()

        print("✅ Shutdown complete")
