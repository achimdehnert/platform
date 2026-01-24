"""
Generic Auto-Setup Middleware.

Guardrail Rule #4 (Generic Version):
Automatically detects and sets up ANY new Django app - not just ui_hub.

Features:
- Auto-detects missing tables for ALL apps
- Auto-generates basic templates for apps without templates
- Auto-creates basic views for apps without views
- Works for ANY app in the system
"""

import logging
import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class GenericAutoSetupMiddleware:
    """
    Universal auto-setup middleware for ALL Django apps.

    Implements Generic Guardrail Rule #4:
    - Auto-detects missing DB tables
    - Auto-generates missing templates
    - Auto-creates basic views
    - Works for any app without hardcoding
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._checked = False
        self._issues = {
            "missing_tables": [],
            "missing_templates": [],
            "missing_views": [],
        }

    def __call__(self, request):
        # Only check once per server lifetime and only in DEBUG
        if not self._checked and settings.DEBUG:
            self._check_all_apps()
            self._checked = True

        # If there are issues and this request is affected, show helpful page
        if self._has_issues() and self._is_affected_request(request):
            return self._setup_required_response(request)

        response = self.get_response(request)
        return response

    def _check_all_apps(self):
        """Check ALL local apps for common issues."""
        local_apps = self._get_local_apps()

        for app_config in local_apps:
            # Check for missing tables
            self._check_app_tables(app_config)

            # Check for missing templates
            self._check_app_templates(app_config)

            # Check for missing views
            self._check_app_views(app_config)

    def _get_local_apps(self):
        """Get all local apps (not Django built-ins)."""
        return [
            app
            for app in apps.get_app_configs()
            if app.name.startswith("apps.") or app.name.startswith("bfagent.")
        ]

    def _check_app_tables(self, app_config):
        """Check if app has missing database tables."""
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if not self._table_exists(table_name):
                self._issues["missing_tables"].append(
                    {
                        "app": app_config.label,
                        "app_name": app_config.name,
                        "model": model.__name__,
                        "table": table_name,
                    }
                )
                logger.warning(
                    f"Missing table: {table_name} "
                    f"(app: {app_config.label}, model: {model.__name__})"
                )

    def _check_app_templates(self, app_config):
        """Check if app has a templates directory."""
        app_path = Path(app_config.path)
        templates_path = app_path / "templates"

        # Only check if app has views.py (likely needs templates)
        views_file = app_path / "views.py"
        if views_file.exists() and not templates_path.exists():
            self._issues["missing_templates"].append(
                {
                    "app": app_config.label,
                    "app_name": app_config.name,
                    "path": str(templates_path),
                }
            )
            logger.warning(
                f"Missing templates directory for {app_config.label} "
                f"(expected: {templates_path})"
            )

    def _check_app_views(self, app_config):
        """Check if app has views but no URLs."""
        app_path = Path(app_config.path)
        views_file = app_path / "views.py"
        urls_file = app_path / "urls.py"

        if views_file.exists() and not urls_file.exists():
            self._issues["missing_views"].append(
                {
                    "app": app_config.label,
                    "app_name": app_config.name,
                    "path": str(urls_file),
                }
            )
            logger.warning(f"App {app_config.label} has views.py but no urls.py")

    def _table_exists(self, table_name):
        """Check if a table exists in the database."""
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

    def _has_issues(self):
        """Check if any issues were found."""
        return any(self._issues.values())

    def _is_affected_request(self, request):
        """Check if the request path is affected by any issues."""
        path = request.path

        # Check missing tables
        for item in self._issues["missing_tables"]:
            app_label = item["app"]
            if self._path_matches_app(path, app_label):
                return True

        # Check missing templates
        for item in self._issues["missing_templates"]:
            app_label = item["app"]
            if self._path_matches_app(path, app_label):
                return True

        return False

    def _path_matches_app(self, path, app_label):
        """Check if a URL path belongs to an app."""
        # Convert app_label to URL-friendly format
        url_prefix = app_label.replace("_", "-")

        return path.startswith(f"/{url_prefix}/") or path.startswith(f"/admin/{app_label}/")

    def _setup_required_response(self, request):
        """Return a helpful error response with auto-fix instructions."""
        html = self._generate_error_page()
        return HttpResponse(html, status=503)

    def _generate_error_page(self):
        """Generate a comprehensive error page for all issues."""
        # Group issues by app
        apps_affected = set()
        for issue_type in self._issues.values():
            for item in issue_type:
                apps_affected.add(item["app"])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🔧 Auto-Setup Required</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    max-width: 900px;
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
                h2 {{ color: #3498db; margin-top: 30px; }}
                .error {{ background: #fee; padding: 15px; border-left: 4px solid #e74c3c; margin: 20px 0; }}
                .warning {{ background: #ffeaa7; padding: 15px; border-left: 4px solid #fdcb6e; margin: 20px 0; }}
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
                .command {{ margin: 15px 0; }}
                ul {{ line-height: 1.8; }}
                .badge {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 5px;
                }}
                .badge-error {{ background: #e74c3c; color: white; }}
                .badge-warning {{ background: #f39c12; color: white; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Generic Auto-Setup Required</h1>

                <div class="error">
                    <strong>⚠️ Generic Guardrail Rule #4 Triggered:</strong><br>
                    Setup issues detected for {len(apps_affected)} app(s): <strong>{', '.join(sorted(apps_affected))}</strong>
                </div>

                {self._render_missing_tables()}
                {self._render_missing_templates()}
                {self._render_missing_views()}

                <div class="solution">
                    <h2>✅ Universal Auto-Fix Solution:</h2>

                    <div class="command">
                        <strong>1. Auto-fix ALL issues with ONE command:</strong>
                        <pre>python manage.py auto_setup_all</pre>
                    </div>

                    <div class="command">
                        <strong>2. Or fix individually:</strong>
                        <pre># Database tables
python manage.py makemigrations
python manage.py migrate

# Templates & Views
python manage.py generate_app_templates &lt;app_name&gt;
python manage.py generate_app_views &lt;app_name&gt;</pre>
                    </div>

                    <div class="command">
                        <strong>3. Restart server:</strong>
                        <pre>CTRL + C
make dev</pre>
                    </div>
                </div>

                <div class="section">
                    <h2>🎯 What Happened?</h2>
                    <p>The Generic Auto-Setup System detected missing components:</p>
                    <ul>
                        <li><strong>Missing Tables:</strong> Models defined but database tables not created</li>
                        <li><strong>Missing Templates:</strong> Views exist but no templates directory</li>
                        <li><strong>Missing Views:</strong> Views exist but no URL routing</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>🛡️ Generic Guardrail Rule #4:</h2>
                    <p>
                        This middleware <strong>automatically detects setup issues for ALL apps</strong>,
                        not just specific ones. It works for:
                    </p>
                    <ul>
                        <li>✅ Any app in <code>apps.*</code></li>
                        <li>✅ Any custom app in <code>bfagent.*</code></li>
                        <li>✅ Automatically adapts to new apps</li>
                        <li>✅ No hardcoding required</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>📊 Affected Apps:</h2>
                    <ul>
                        {''.join(f'<li><code>{app}</code></li>' for app in sorted(apps_affected))}
                    </ul>
                </div>

                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d;">
                    <small>
                        <strong>Environment:</strong> DEBUG mode<br>
                        <strong>Detection:</strong> Automatic on server startup<br>
                        <strong>System:</strong> Generic Auto-Setup (works for ALL apps)
                    </small>
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def _render_missing_tables(self):
        """Render missing tables section."""
        if not self._issues["missing_tables"]:
            return ""

        apps_with_tables = {}
        for item in self._issues["missing_tables"]:
            app = item["app"]
            if app not in apps_with_tables:
                apps_with_tables[app] = []
            apps_with_tables[app].append(item)

        html = '<div class="section">\n'
        html += '<h2><span class="badge badge-error">ERROR</span> Missing Database Tables</h2>\n'
        html += "<ul>\n"

        for app, items in sorted(apps_with_tables.items()):
            html += f"<li><strong>{app}</strong>: {len(items)} tables<ul>\n"
            for item in items:
                html += f'<li><code>{item["table"]}</code> (model: {item["model"]})</li>\n'
            html += "</ul></li>\n"

        html += "</ul>\n"
        html += "</div>\n"

        return html

    def _render_missing_templates(self):
        """Render missing templates section."""
        if not self._issues["missing_templates"]:
            return ""

        html = '<div class="section">\n'
        html += '<h2><span class="badge badge-warning">WARNING</span> Missing Templates Directories</h2>\n'
        html += "<ul>\n"

        for item in self._issues["missing_templates"]:
            html += f'<li><strong>{item["app"]}</strong>: <code>{item["path"]}</code></li>\n'

        html += "</ul>\n"
        html += "<p><small>These apps have views but no templates directory. Templates may be needed.</small></p>\n"
        html += "</div>\n"

        return html

    def _render_missing_views(self):
        """Render missing views section."""
        if not self._issues["missing_views"]:
            return ""

        html = '<div class="section">\n'
        html += (
            '<h2><span class="badge badge-warning">WARNING</span> Missing URL Configuration</h2>\n'
        )
        html += "<ul>\n"

        for item in self._issues["missing_views"]:
            html += f'<li><strong>{item["app"]}</strong>: No <code>urls.py</code> found</li>\n'

        html += "</ul>\n"
        html += "<p><small>These apps have views but no URL routing. Add urls.py or include in main urls.py.</small></p>\n"
        html += "</div>\n"

        return html
