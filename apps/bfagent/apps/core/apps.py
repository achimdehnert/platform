"""
Core App Configuration

Central Django app for consolidated services and utilities.
Part of the BF Agent Framework.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Core application configuration.

    This app provides:
        - Consolidated Handler Framework
        - LLM Service (multi-provider)
        - Cache Service (multi-backend)
        - Storage Service (local/cloud)
        - Export Service (DOCX/PDF/EPUB)
        - File Extractors (PDF/DOCX/PPTX/Excel)
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core Services"

    def ready(self):
        """
        Initialize core services on app startup.

        Called once when Django starts.
        """
        # Import services to register them
        self._register_services()

        # Setup logging
        self._setup_logging()

    def _register_services(self):
        """Register core services for discovery."""
        try:
            # Services are now available
            import logging

            from .services import cache, export, extractors, llm, storage

            logger = logging.getLogger(__name__)
            logger.info("Core services registered successfully")

        except ImportError as e:
            # Services may not be fully installed yet
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Some core services not yet available: {e}")

    def _setup_logging(self):
        """Configure logging for core module."""
        import logging

        # Create logger for core module
        logger = logging.getLogger("apps.core")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
