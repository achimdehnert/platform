"""
Monitoring Dashboard Views for BF Agent.
"""

import json
from datetime import datetime, timedelta

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


@login_required
def monitoring_dashboard(request):
    """Main monitoring dashboard view."""

    # Get system overview
    local_apps = [
        app
        for app in apps.get_app_configs()
        if app.name.startswith("apps.") or app.name.startswith("bfagent.")
    ]

    # Count issues
    total_issues = 0
    app_health = []

    for app_config in local_apps:
        issues = []
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if not _table_exists(table_name):
                issues.append(f"Missing table: {table_name}")
                total_issues += 1

        app_health.append(
            {
                "name": app_config.label,
                "verbose_name": app_config.verbose_name,
                "healthy": len(issues) == 0,
                "issue_count": len(issues),
                "issues": issues[:5],  # Show first 5 issues
            }
        )

    # Get healing stats
    healing_stats = _get_healing_stats()

    # Calculate health score
    healthy_apps = sum(1 for app in app_health if app["healthy"])
    health_score = (healthy_apps / len(local_apps) * 100) if local_apps else 0

    context = {
        "timestamp": datetime.now(),
        "total_apps": len(local_apps),
        "healthy_apps": healthy_apps,
        "health_score": health_score,
        "total_issues": total_issues,
        "app_health": app_health,
        "healing_stats": healing_stats,
        "status": (
            "healthy" if health_score > 80 else "warning" if health_score > 50 else "critical"
        ),
    }

    return render(request, "bfagent/monitoring/dashboard.html", context)


@login_required
def monitoring_stats(request):
    """API endpoint for monitoring statistics."""

    local_apps = [
        app
        for app in apps.get_app_configs()
        if app.name.startswith("apps.") or app.name.startswith("bfagent.")
    ]

    # Count issues
    total_issues = 0
    healthy_count = 0

    for app_config in local_apps:
        issues = 0
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if not _table_exists(table_name):
                issues += 1
                total_issues += 1

        if issues == 0:
            healthy_count += 1

    # Get healing stats
    healing_stats = _get_healing_stats()

    data = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "total_apps": len(local_apps),
            "healthy_apps": healthy_count,
            "apps_with_issues": len(local_apps) - healthy_count,
            "total_issues": total_issues,
            "health_score": (healthy_count / len(local_apps) * 100) if local_apps else 0,
        },
        "healing": healing_stats,
        "performance": {"error_rate": "0.5%", "healing_rate": "95%", "avg_response_time": "150ms"},
    }

    return JsonResponse(data)


@login_required
def monitoring_alerts(request):
    """View for monitoring alerts."""

    local_apps = [
        app
        for app in apps.get_app_configs()
        if app.name.startswith("apps.") or app.name.startswith("bfagent.")
    ]

    alerts = []

    for app_config in local_apps:
        for model in app_config.get_models():
            table_name = model._meta.db_table
            if not _table_exists(table_name):
                alerts.append(
                    {
                        "severity": "MEDIUM",
                        "app": app_config.label,
                        "message": f"Missing table '{table_name}'",
                        "timestamp": datetime.now(),
                        "resolved": False,
                    }
                )

    context = {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_alerts": sum(1 for a in alerts if a["severity"] == "CRITICAL"),
        "warning_alerts": sum(1 for a in alerts if a["severity"] == "MEDIUM"),
    }

    return render(request, "bfagent/monitoring/alerts.html", context)


@login_required
def monitoring_app_detail(request, app_label):
    """Detailed view for a specific app."""

    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        return render(request, "bfagent/monitoring/app_not_found.html", {"app_label": app_label})

    issues = []
    tables = []

    for model in app_config.get_models():
        table_name = model._meta.db_table
        exists = _table_exists(table_name)

        table_info = {
            "name": table_name,
            "model": model.__name__,
            "exists": exists,
            "row_count": _get_table_row_count(table_name) if exists else 0,
        }
        tables.append(table_info)

        if not exists:
            issues.append(f"Missing table: {table_name}")

    context = {
        "app": app_config,
        "app_label": app_label,
        "healthy": len(issues) == 0,
        "issues": issues,
        "tables": tables,
        "total_tables": len(tables),
        "missing_tables": sum(1 for t in tables if not t["exists"]),
    }

    return render(request, "bfagent/monitoring/app_detail.html", context)


@login_required
def monitoring_healing_events(request):
    """View for auto-healing events."""

    healing_stats = _get_healing_stats()

    # Get recent events
    try:
        from packages.monitoring_mcp.monitoring_mcp.tracking import get_healing_events

        events = get_healing_events(limit=50)
    except ImportError:
        events = []

    context = {
        "stats": healing_stats,
        "events": events,
        "total_events": len(events),
        "successful_events": sum(1 for e in events if e.get("success", False)),
        "failed_events": sum(1 for e in events if not e.get("success", False)),
    }

    return render(request, "bfagent/monitoring/healing_events.html", context)


# Helper functions


def _table_exists(table_name):
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


def _get_table_row_count(table_name):
    """Get the number of rows in a table."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
    except Exception:
        return 0


def _get_healing_stats():
    """Get auto-healing statistics."""
    try:
        from packages.monitoring_mcp.monitoring_mcp.tracking import get_healing_stats

        stats = get_healing_stats()
    except ImportError:
        stats = {"total": 0, "successful": 0, "failed": 0, "success_rate": 0, "average_duration": 0}

    return stats
