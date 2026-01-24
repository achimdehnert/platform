"""
Sentry Integration Service - Reactive Intelligence
Error tracking, AI analysis, and auto-fix with Seer
Integrated: December 9, 2025
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SentryIntegrationService:
    """
    Sentry Integration for bfagent

    Features:
    - Automatic error tracking
    - Issue management
    - Seer AI integration (root cause analysis)
    - Performance monitoring
    - Release tracking
    """

    def __init__(self):
        self.enabled = self._check_sentry_available()
        if self.enabled:
            self._init_sentry()

    def _check_sentry_available(self) -> bool:
        """Check if Sentry SDK is available"""
        try:
            import sentry_sdk

            return True
        except ImportError:
            logger.warning("Sentry SDK not installed. Run: pip install sentry-sdk")
            return False

    def _init_sentry(self):
        """Initialize Sentry SDK"""
        try:
            import sentry_sdk
            from django.conf import settings

            # Check if DSN is configured
            dsn = getattr(settings, "SENTRY_DSN", None)
            if not dsn:
                logger.info("Sentry DSN not configured. Set SENTRY_DSN in settings.")
                self.enabled = False
                return

            # Initialize Sentry
            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 1.0),
                profiles_sample_rate=getattr(settings, "SENTRY_PROFILES_SAMPLE_RATE", 1.0),
                environment=getattr(settings, "SENTRY_ENVIRONMENT", "development"),
                release=getattr(settings, "SENTRY_RELEASE", None),
                send_default_pii=False,  # Don't send PII by default
            )

            logger.info("Sentry initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            self.enabled = False

    # ============================================================================
    # ERROR CAPTURE
    # ============================================================================

    def capture_exception(
        self,
        exception: Exception,
        context: Dict[str, Any] = None,
        level: str = "error",
        tags: Dict[str, str] = None,
    ) -> Optional[str]:
        """
        Capture an exception to Sentry

        Args:
            exception: The exception to capture
            context: Additional context (extras)
            level: Error level (error, warning, info)
            tags: Tags for filtering

        Returns:
            Event ID or None
        """
        if not self.enabled:
            return None

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                # Add context
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)

                # Add tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)

                # Set level
                scope.level = level

                # Capture
                event_id = sentry_sdk.capture_exception(exception)
                logger.info(f"Sentry event captured: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture exception to Sentry: {e}")
            return None

    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Dict[str, Any] = None,
        tags: Dict[str, str] = None,
    ) -> Optional[str]:
        """
        Capture a message to Sentry

        Args:
            message: Message to capture
            level: Message level
            context: Additional context
            tags: Tags for filtering

        Returns:
            Event ID or None
        """
        if not self.enabled:
            return None

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)

                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)

                scope.level = level

                event_id = sentry_sdk.capture_message(message, level=level)
                logger.info(f"Sentry message captured: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture message to Sentry: {e}")
            return None

    # ============================================================================
    # ADMIN DIAGNOSTICS INTEGRATION
    # ============================================================================

    def capture_admin_error(
        self, error_info: Dict[str, Any], auto_analyze: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Capture admin error from diagnostics

        Args:
            error_info: Error information from admin_diagnostics
            auto_analyze: If True, invoke Seer for analysis

        Returns:
            Dict with event_id and optional analysis
        """
        if not self.enabled:
            return None

        try:
            # Extract error details
            model = error_info.get("model", "Unknown")
            url = error_info.get("url", "")
            error = error_info.get("error", {})

            # Build message
            if isinstance(error, dict):
                error_msg = error.get("message", str(error))
            else:
                error_msg = str(error)

            message = f"Admin Error: {model} - {error_msg}"

            # Capture to Sentry
            event_id = self.capture_message(
                message=message,
                level="error",
                context={
                    "url": url,
                    "model": model,
                    "error_details": error,
                    "source": "admin_diagnostics",
                },
                tags={
                    "component": "admin",
                    "model": model.split(".")[-1] if "." in model else model,
                },
            )

            result = {
                "event_id": event_id,
                "message": message,
                "sentry_url": self._get_issue_url(event_id) if event_id else None,
            }

            # Seer analysis (if MCP available)
            if auto_analyze and event_id:
                analysis = self._invoke_seer_analysis(event_id, error_info)
                if analysis:
                    result["seer_analysis"] = analysis

            return result

        except Exception as e:
            logger.error(f"Failed to capture admin error: {e}")
            return None

    def _get_issue_url(self, event_id: str) -> Optional[str]:
        """Get Sentry issue URL for event"""
        try:
            from django.conf import settings

            dsn = getattr(settings, "SENTRY_DSN", "")

            # Extract org and project from DSN
            # Format: https://key@o{org_id}.ingest.sentry.io/{project_id}
            if "@" in dsn and ".ingest.sentry.io/" in dsn:
                parts = dsn.split("@")[1].split(".ingest.sentry.io/")
                if len(parts) == 2:
                    org_part = parts[0]
                    project_id = parts[1]

                    # Extract org_id
                    if org_part.startswith("o"):
                        org_id = org_part[1:]
                        return f"https://sentry.io/organizations/{org_id}/issues/?query={event_id}"

            return f"https://sentry.io/issues/?query={event_id}"

        except:
            return None

    def _invoke_seer_analysis(
        self, event_id: str, error_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke Seer AI for root cause analysis

        Note: This requires Sentry MCP to be configured
        This is a placeholder for MCP integration
        """
        # TODO: Implement when Sentry MCP is available
        # For now, return placeholder
        logger.info(f"Seer analysis requested for event {event_id}")

        return {
            "status": "pending",
            "message": "Seer MCP integration pending",
            "event_id": event_id,
        }

    # ============================================================================
    # PERFORMANCE MONITORING
    # ============================================================================

    def start_transaction(self, name: str, op: str = "task", description: str = None):
        """
        Start a performance transaction

        Args:
            name: Transaction name
            op: Operation type
            description: Optional description

        Returns:
            Transaction object or None
        """
        if not self.enabled:
            return None

        try:
            import sentry_sdk

            transaction = sentry_sdk.start_transaction(op=op, name=name, description=description)

            return transaction

        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            return None

    def add_breadcrumb(
        self, message: str, category: str = None, level: str = "info", data: Dict[str, Any] = None
    ):
        """Add a breadcrumb for context"""
        if not self.enabled:
            return

        try:
            import sentry_sdk

            sentry_sdk.add_breadcrumb(
                message=message, category=category, level=level, data=data or {}
            )

        except Exception as e:
            logger.error(f"Failed to add breadcrumb: {e}")

    # ============================================================================
    # RELEASE MANAGEMENT
    # ============================================================================

    def set_release(self, version: str):
        """Set the current release version"""
        if not self.enabled:
            return

        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("release", version)

            logger.info(f"Sentry release set to: {version}")

        except Exception as e:
            logger.error(f"Failed to set release: {e}")

    # ============================================================================
    # UTILITY
    # ============================================================================

    def is_enabled(self) -> bool:
        """Check if Sentry is enabled"""
        return self.enabled

    def get_stats(self) -> Dict[str, Any]:
        """Get Sentry integration stats"""
        return {
            "enabled": self.enabled,
            "sdk_installed": self._check_sentry_available(),
            "dsn_configured": self.enabled,
        }


# Global singleton
_sentry_service = None


def get_sentry_service() -> SentryIntegrationService:
    """Get or create the global Sentry service instance"""
    global _sentry_service
    if _sentry_service is None:
        _sentry_service = SentryIntegrationService()
    return _sentry_service
