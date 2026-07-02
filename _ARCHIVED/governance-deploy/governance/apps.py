"""
Governance App Configuration
============================

DDL (Domain Development Lifecycle) - ADR-017
Manages Business Cases, Use Cases, ADRs, and Reviews.
"""

from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    """Configuration for the Governance app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "governance"
    verbose_name = "DDL Governance"
    
    def ready(self):
        """Import signals when app is ready."""
        pass  # Signals will be added later if needed
