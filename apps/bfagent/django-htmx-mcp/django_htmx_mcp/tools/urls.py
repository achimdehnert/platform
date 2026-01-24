"""
URL Generation Tools.

Tools zum Generieren von Django URL Patterns.
"""

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize


@mcp.tool()
def generate_crud_urls(
    model: str,
    app_name: str,
    with_htmx_namespace: bool = True,
    pk_type: str = "int",
    extra_actions: list[dict] | None = None,
) -> str:
    """
    Generiert komplette CRUD URL Patterns.
    
    Args:
        model: Model Name
        app_name: Django App Name (für app_name und Namespace)
        with_htmx_namespace: Separaten Namespace für HTMX Partials
        pk_type: PK Type (int, uuid, slug)
        extra_actions: Zusätzliche Actions:
            - name: URL Name
            - path: URL Path
            - view: View Name
            
    Returns:
        Python Code für urls.py
    """
    logger.info(f"Generating CRUD URLs for {model}")
    
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    # PK converter
    pk_converter = {
        "int": "int:pk",
        "uuid": "uuid:pk",
        "slug": "slug:slug",
    }.get(pk_type, "int:pk")
    
    pk_kwarg = "slug" if pk_type == "slug" else "pk"
    
    lines = [
        "from django.urls import path",
        "",
        "from . import views",
        "",
        "",
        f'app_name = "{app_name}"',
        "",
        "urlpatterns = [",
        f"    # {model} CRUD",
        f'    path("{model_plural}/", views.{model}ListView.as_view(), name="{model_snake}_list"),',
        f'    path("{model_plural}/create/", views.{model}CreateView.as_view(), name="{model_snake}_create"),',
        f'    path("{model_plural}/<{pk_converter}>/", views.{model}DetailView.as_view(), name="{model_snake}_detail"),',
        f'    path("{model_plural}/<{pk_converter}>/update/", views.{model}UpdateView.as_view(), name="{model_snake}_update"),',
        f'    path("{model_plural}/<{pk_converter}>/delete/", views.{model}DeleteView.as_view(), name="{model_snake}_delete"),',
    ]
    
    # Extra actions
    if extra_actions:
        lines.append("")
        lines.append(f"    # Extra {model} actions")
        for action in extra_actions:
            name = action.get("name")
            path = action.get("path")
            view = action.get("view")
            lines.append(f'    path("{path}", views.{view}.as_view(), name="{name}"),')
    
    if with_htmx_namespace:
        lines.extend([
            "",
            f"    # HTMX Partials",
            f'    path("{model_plural}/search/", views.{model}SearchView.as_view(), name="{model_snake}_search"),',
        ])
    
    lines.append("]")
    
    return "\n".join(lines)


@mcp.tool()
def generate_urlpatterns(
    app_name: str,
    views: list[dict],
    include_api: bool = False,
    api_prefix: str = "api/v1",
) -> str:
    """
    Generiert flexible URL Patterns.
    
    Args:
        app_name: Django App Name
        views: Liste von View-Definitionen:
            - path: URL Path (z.B. "tasks/", "tasks/<int:pk>/")
            - view: View Name (z.B. "TaskListView")
            - name: URL Name (z.B. "task_list")
            - methods: Optional für API views
        include_api: API URLs mit DRF generieren
        api_prefix: Prefix für API URLs
        
    Returns:
        Python Code für urls.py
    """
    imports = ["from django.urls import path"]
    
    if include_api:
        imports.append("from django.urls import include")
        imports.append("from rest_framework.routers import DefaultRouter")
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.append("")
    lines.append("from . import views")
    lines.append("")
    lines.append("")
    lines.append(f'app_name = "{app_name}"')
    lines.append("")
    lines.append("urlpatterns = [")
    
    for v in views:
        path = v.get("path", "")
        view = v.get("view")
        name = v.get("name")
        
        # Detect if function or class view
        is_class = view[0].isupper()
        view_call = f"views.{view}.as_view()" if is_class else f"views.{view}"
        
        lines.append(f'    path("{path}", {view_call}, name="{name}"),')
    
    lines.append("]")
    
    if include_api:
        lines.extend([
            "",
            "",
            "# API Router",
            "router = DefaultRouter()",
            "# router.register('resource', views.ResourceViewSet)",
            "",
            "urlpatterns += [",
            f'    path("{api_prefix}/", include(router.urls)),',
            "]",
        ])
    
    return "\n".join(lines)


@mcp.tool()
def generate_htmx_action_urls(
    model: str,
    app_name: str,
    actions: list[str],
) -> str:
    """
    Generiert URLs für HTMX Actions (Toggle, Inline Edit, etc.).
    
    Args:
        model: Model Name
        app_name: Django App Name
        actions: Liste von Actions:
            - "toggle": Toggle-Aktion
            - "inline_edit": Inline Edit
            - "archive": Archive-Aktion
            - "duplicate": Duplicate-Aktion
            - "bulk": Bulk Actions
            
    Returns:
        URL Pattern Code
    """
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    lines = [
        "from django.urls import path",
        "",
        "from . import views",
        "",
        "",
        f"# HTMX Action URLs for {model}",
        f"# Include in main urlpatterns",
        "",
        f"{model_snake}_htmx_patterns = [",
    ]
    
    for action in actions:
        if action == "toggle":
            lines.append(
                f'    path("{model_plural}/<int:pk>/toggle/", '
                f'views.{model}ToggleView.as_view(), name="{model_snake}_toggle"),'
            )
        elif action == "inline_edit":
            lines.append(
                f'    path("{model_plural}/<int:pk>/inline-edit/", '
                f'views.{model}InlineEditView.as_view(), name="{model_snake}_inline_edit"),'
            )
        elif action == "archive":
            lines.append(
                f'    path("{model_plural}/<int:pk>/archive/", '
                f'views.{model}ArchiveView.as_view(), name="{model_snake}_archive"),'
            )
        elif action == "duplicate":
            lines.append(
                f'    path("{model_plural}/<int:pk>/duplicate/", '
                f'views.{model}DuplicateView.as_view(), name="{model_snake}_duplicate"),'
            )
        elif action == "bulk":
            lines.append(
                f'    path("{model_plural}/bulk-action/", '
                f'views.{model}BulkActionView.as_view(), name="{model_snake}_bulk_action"),'
            )
    
    lines.append("]")
    lines.append("")
    lines.append("# Add to urlpatterns:")
    lines.append(f"# urlpatterns += {model_snake}_htmx_patterns")
    
    return "\n".join(lines)


@mcp.tool()
def generate_api_urls(
    app_name: str,
    viewsets: list[dict],
    version: str = "v1",
) -> str:
    """
    Generiert DRF API URLs mit Router.
    
    Args:
        app_name: Django App Name
        viewsets: Liste von ViewSet-Definitionen:
            - model: Model Name
            - viewset: ViewSet Class Name (optional)
            - basename: URL basename (optional)
        version: API Version
        
    Returns:
        Python Code für api_urls.py
    """
    lines = [
        "from django.urls import path, include",
        "from rest_framework.routers import DefaultRouter",
        "",
        "from . import views",
        "",
        "",
        f'app_name = "{app_name}_api"',
        "",
        "router = DefaultRouter()",
        "",
    ]
    
    for vs in viewsets:
        model = vs.get("model")
        model_snake = snake_case(model)
        model_plural = pluralize(model_snake)
        viewset = vs.get("viewset", f"{model}ViewSet")
        basename = vs.get("basename", model_snake)
        
        lines.append(f'router.register("{model_plural}", views.{viewset}, basename="{basename}")')
    
    lines.extend([
        "",
        "urlpatterns = [",
        '    path("", include(router.urls)),',
        "]",
        "",
        "",
        "# Include in project urls.py:",
        f'# path("api/{version}/", include("{app_name}.api_urls")),',
    ])
    
    return "\n".join(lines)
