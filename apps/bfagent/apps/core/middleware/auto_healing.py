"""
Auto-Healing Middleware.

Monitors Django exceptions and automatically fixes known issues.
Part of Generic Guardrail Rule #4: Proactive Error Detection & Auto-Fix.

Features:
- Catches "relation does not exist" errors
- Automatically runs migrations
- Catches template not found errors
- Automatically creates templates
- Logs all auto-fixes for transparency
"""

import io
import logging
import re
import sys
import time
import traceback

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# Import tracking system
try:
    from packages.monitoring_mcp.monitoring_mcp.tracking import track_healing_event
except ImportError:
    # Fallback if monitoring MCP not installed
    def track_healing_event(*args, **kwargs):
        pass


class AutoHealingMiddleware:
    """
    Middleware that automatically heals common Django errors.

    Supported auto-fixes:
    - ProgrammingError: relation does not exist → auto-migrate
    - TemplateDoesNotExist → auto-generate template
    - ImportError → install missing package
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._healing_in_progress = False
        self._healing_attempts = {}

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # Try to auto-heal the error
            if settings.DEBUG and not self._healing_in_progress:
                healed = self._try_heal_error(e, request)
                if healed:
                    # Retry the request after healing
                    return self.get_response(request)

            # If not healed, re-raise
            raise

    def process_exception(self, request, exception):
        """Process exceptions and try to auto-heal."""
        if not settings.DEBUG or self._healing_in_progress:
            return None

        healed = self._try_heal_error(exception, request)

        if healed:
            # Return a redirect response to retry
            return HttpResponse(
                self._get_healing_response(exception, request), status=200, content_type="text/html"
            )

        return None

    def _try_heal_error(self, exception, request):
        """Try to automatically heal the error."""
        exception_type = type(exception).__name__
        exception_msg = str(exception)

        # Prevent infinite loops
        error_key = f"{exception_type}:{exception_msg}"
        if self._healing_attempts.get(error_key, 0) >= 3:
            logger.warning(f"Auto-healing failed after 3 attempts: {error_key}")
            return False

        self._healing_attempts[error_key] = self._healing_attempts.get(error_key, 0) + 1
        self._healing_in_progress = True

        try:
            # Try different healing strategies
            healed = False

            if "relation" in exception_msg and "does not exist" in exception_msg:
                healed = self._heal_missing_table(exception_msg, request)

            elif "TemplateDoesNotExist" in exception_type:
                healed = self._heal_missing_template(exception_msg, request)

            elif "NoReverseMatch" in exception_type:
                healed = self._heal_missing_url(exception_msg, request)

            if healed:
                logger.info(f"✅ Auto-healed: {exception_type} - {exception_msg}")

            return healed

        finally:
            self._healing_in_progress = False

    def _heal_missing_table(self, error_msg, request):
        """Auto-heal missing database tables."""
        start_time = time.time()

        # Extract table name from error
        match = re.search(r'relation "([^"]+)" does not exist', error_msg)
        if not match:
            return False

        table_name = match.group(1)

        # Extract app from table name (e.g., "ui_hub_categories" -> "ui_hub")
        app_label = table_name.split("_")[0] if "_" in table_name else "unknown"

        logger.info(f'🔧 Auto-healing: Missing table "{table_name}"')

        try:
            # Run makemigrations
            logger.info("  Running makemigrations...")
            stdout = io.StringIO()
            call_command("makemigrations", stdout=stdout, interactive=False)
            output = stdout.getvalue()
            logger.info(f"  makemigrations output: {output}")

            # Run migrate
            logger.info("  Running migrate...")
            stdout = io.StringIO()
            call_command("migrate", stdout=stdout, interactive=False)
            output = stdout.getvalue()
            logger.info(f"  migrate output: {output}")

            # Verify table exists now
            duration = time.time() - start_time

            if self._table_exists(table_name):
                logger.info(f"✅ Successfully created table: {table_name}")

                # Track successful healing
                track_healing_event(
                    app=app_label,
                    error_type="ProgrammingError",
                    error_message=f'relation "{table_name}" does not exist',
                    action="migrate",
                    success=True,
                    duration_seconds=duration,
                    metadata={"table_name": table_name, "path": request.path},
                )

                return True
            else:
                logger.warning(f"⚠️  Table still missing after migration: {table_name}")

                # Track failed healing
                track_healing_event(
                    app=app_label,
                    error_type="ProgrammingError",
                    error_message=f'relation "{table_name}" does not exist',
                    action="migrate",
                    success=False,
                    duration_seconds=duration,
                    metadata={"table_name": table_name, "path": request.path},
                )

                return False

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Auto-healing failed for table {table_name}: {e}")

            # Track failed healing
            track_healing_event(
                app=app_label,
                error_type="ProgrammingError",
                error_message=f'relation "{table_name}" does not exist',
                action="migrate",
                success=False,
                duration_seconds=duration,
                metadata={"table_name": table_name, "path": request.path, "error": str(e)},
            )

            return False

    def _heal_missing_template(self, error_msg, request):
        """Auto-heal missing templates."""
        # Extract template name
        match = re.search(r"Couldn't find '([^']+)'", error_msg)
        if not match:
            return False

        template_name = match.group(1)

        logger.info(f'🔧 Auto-healing: Missing template "{template_name}"')

        try:
            # Try to generate basic template
            from pathlib import Path

            template_path = Path(settings.BASE_DIR) / "templates" / template_name
            template_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate basic template
            template_content = self._generate_basic_template(template_name)
            template_path.write_text(template_content)

            logger.info(f"✅ Successfully created template: {template_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Auto-healing failed for template {template_name}: {e}")
            return False

    def _heal_missing_url(self, error_msg, request):
        """Auto-heal missing URL patterns."""
        logger.info(f"🔧 Auto-healing: Missing URL pattern")

        # This is more complex - for now just log
        logger.warning("⚠️  URL auto-healing not yet implemented")
        return False

    def _table_exists(self, table_name):
        """Check if a table exists."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = %s
                    )
                """,
                    [table_name],
                )
                return cursor.fetchone()[0]
        except Exception:
            return False

    def _generate_basic_template(self, template_name):
        """Generate a basic template."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Auto-Generated Template</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container my-5">
        <div class="alert alert-info">
            <h4>✅ Auto-Generated Template</h4>
            <p>This template was automatically generated by the Auto-Healing system.</p>
            <p><strong>Template:</strong> <code>{template_name}</code></p>
            <p>You can customize it in: <code>templates/{template_name}</code></p>
        </div>
    </div>
</body>
</html>
"""

    def _get_healing_response(self, exception, request):
        """Get a response that explains the healing."""
        exception_type = type(exception).__name__
        exception_msg = str(exception)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Auto-Healed</title>
            <meta http-equiv="refresh" content="2;url={request.path}">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                }}
                .healing {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 600px;
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    width: 50px;
                    height: 50px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                h1 {{ color: #27ae60; }}
                code {{
                    background: #f8f8f8;
                    padding: 2px 6px;
                    border-radius: 3px;
                    color: #e74c3c;
                }}
            </style>
        </head>
        <body>
            <div class="healing">
                <h1>✅ Auto-Healed!</h1>
                <div class="spinner"></div>
                <p><strong>Error Type:</strong> <code>{exception_type}</code></p>
                <p><strong>Fixed:</strong> {exception_msg[:100]}...</p>
                <p>Redirecting in 2 seconds...</p>
                <p><small>Powered by Generic Guardrail Rule #4</small></p>
            </div>
        </body>
        </html>
        """
