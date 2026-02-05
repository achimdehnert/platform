"""
Dashboard View
ADR-009: Database-driven dashboard
"""

from typing import Any

from cad_services.django.views.base import BaseView, HTMXMixin


class DashboardView(HTMXMixin, BaseView):
    """Main dashboard view."""

    template_name = "cadhub/dashboard.html"
    partial_template_name = "cadhub/partials/dashboard_content.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Stats will be loaded from repositories
        context["stats"] = {
            "project_count": 0,
            "model_count": 0,
            "room_count": 0,
            "window_count": 0,
        }

        context["recent_projects"] = []
        context["recent_activity"] = []

        return context
