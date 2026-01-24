"""
UI Hub Middleware - Auto-Migration Check.

Guardrail Rule #4: Proactive table detection.
Automatically detects missing tables on first request and provides helpful error messages.
"""

import logging

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class AutoMigrationCheckMiddleware:
    """
    Middleware to check for missing database tables and provide actionable error messages.

    This implements Guardrail Rule #4: Proactive Error Detection.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._checked = False
        self._missing_tables = []

    def __call__(self, request):
        # Only check once per server lifetime
        if not self._checked and settings.DEBUG:
            self._check_tables()
            self._checked = True

        # If there are missing tables and this is a request to an affected app, show error
        if self._missing_tables and self._is_affected_request(request):
            return self._migration_required_response(request)

        response = self.get_response(request)
        return response

    def _check_tables(self):
        """Check for missing tables in local apps."""
        local_apps = [
            app
            for app in apps.get_app_configs()
            if app.name.startswith("apps.") or app.name.startswith("bfagent.")
        ]

        for app_config in local_apps:
            for model in app_config.get_models():
                table_name = model._meta.db_table
                if not self._table_exists(table_name):
                    self._missing_tables.append(
                        {
                            "app": app_config.label,
                            "model": model.__name__,
                            "table": table_name,
                        }
                    )
                    logger.warning(
                        f"Missing table detected: {table_name} "
                        f"(app: {app_config.label}, model: {model.__name__})"
                    )

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

    def _is_affected_request(self, request):
        """Check if the request is for an app with missing tables."""
        path = request.path
        for item in self._missing_tables:
            app = item["app"]
            # Check if path starts with app name
            if path.startswith(f'/{app.replace("_", "-")}/') or path.startswith(f"/admin/{app}/"):
                return True
        return False

    def _migration_required_response(self, request):
        """Return a helpful error response with migration instructions."""
        apps_affected = list(set(item["app"] for item in self._missing_tables))

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🔧 Migrations Required</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #e74c3c; }}
                h2 {{ color: #3498db; }}
                .error {{ background: #fee; padding: 15px; border-left: 4px solid #e74c3c; margin: 20px 0; }}
                .solution {{ background: #efe; padding: 15px; border-left: 4px solid #27ae60; margin: 20px 0; }}
                code {{
                    background: #f8f8f8;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background: #2c3e50;
                    color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                .command {{ margin: 10px 0; }}
                ul {{ line-height: 1.8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Database Migrations Required</h1>

                <div class="error">
                    <strong>⚠️ Guardrail Rule #4 Triggered:</strong><br>
                    Missing database tables detected for: <strong>{', '.join(apps_affected)}</strong>
                </div>

                <h2>Missing Tables:</h2>
                <ul>
                    {''.join(f'<li><code>{item["table"]}</code> (model: {item["model"]})</li>' for item in self._missing_tables)}
                </ul>

                <div class="solution">
                    <h2>✅ Auto-Fix Solution:</h2>
                    <p>Run these commands in your terminal:</p>

                    <div class="command">
                        <strong>1. Generate migrations:</strong>
                        <pre>python manage.py makemigrations</pre>
                    </div>

                    <div class="command">
                        <strong>2. Apply migrations:</strong>
                        <pre>python manage.py migrate</pre>
                    </div>

                    <div class="command">
                        <strong>3. Restart the server:</strong>
                        <pre>CTRL + C
make dev</pre>
                    </div>
                </div>

                <h2>📋 Alternative: Auto-Migration Command</h2>
                <p>Use the new auto-migration command (after server restart):</p>
                <pre>python manage.py check_and_migrate</pre>

                <h2>🎯 What Happened?</h2>
                <p>
                    Your Django models were defined but the corresponding database tables don't exist yet.
                    This usually happens when:
                </p>
                <ul>
                    <li>A new app was added to INSTALLED_APPS</li>
                    <li>New models were created</li>
                    <li>Migrations weren't run after model changes</li>
                </ul>

                <h2>🛡️ Prevention (Guardrail Rule #4):</h2>
                <p>This middleware automatically detects missing tables and shows this helpful message instead of a cryptic error.</p>

                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d;">
                    <small>
                        <strong>Request:</strong> {request.path}<br>
                        <strong>Environment:</strong> DEBUG mode<br>
                        <strong>Time:</strong> Server startup check
                    </small>
                </p>
            </div>
        </body>
        </html>
        """

        return HttpResponse(html, status=503)
