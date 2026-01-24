"""
Research Views
==============

Views for the Research Hub.
"""

# Import main views (moved from views.py)
from .main_views import (
    dashboard,
    project_list,
    project_create,
    project_detail,
    project_edit,
    project_delete,
    perform_search,
    perform_fact_check,
    generate_summary,
    api_quick_search,
    api_fact_check,
    project_export,
)

# Import outline views
from .outline_views import (
    outline_generator_view,
    generate_outline_view,
    export_outline_view,
    list_frameworks_view,
)
