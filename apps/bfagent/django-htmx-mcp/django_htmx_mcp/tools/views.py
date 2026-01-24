"""
View Generation Tools.

Tools zum Generieren von Django Class-Based Views mit HTMX Support.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize


@mcp.tool()
def generate_cbv(
    view_name: str,
    view_type: Literal["ListView", "DetailView", "CreateView", "UpdateView", "DeleteView", "FormView"],
    model: str,
    app_name: str = "app",
    template_name: str | None = None,
    htmx_enabled: bool = True,
    htmx_partial_template: str | None = None,
    login_required: bool = False,
    permission_required: str | None = None,
    paginate_by: int | None = None,
    ordering: list[str] | None = None,
    fields: list[str] | None = None,
    form_class: str | None = None,
    success_url: str | None = None,
    success_message: str | None = None,
    context_object_name: str | None = None,
    extra_context: dict | None = None,
) -> str:
    """
    Generiert eine Django Class-Based View mit optionalem HTMX Support.
    
    Args:
        view_name: Name der View (PascalCase, z.B. "TaskListView")
        view_type: Typ der CBV (ListView, DetailView, CreateView, etc.)
        model: Model Name (z.B. "Task")
        app_name: Django App Name
        template_name: Custom Template (default: auto-generated)
        htmx_enabled: HTMX Response Handling aktivieren
        htmx_partial_template: Separates Template für HTMX Requests
        login_required: LoginRequiredMixin hinzufügen
        permission_required: Permission String (z.B. "app.change_task")
        paginate_by: Pagination für ListView
        ordering: Default Ordering für ListView
        fields: Fields für CreateView/UpdateView
        form_class: Custom Form Class
        success_url: Redirect URL nach Success
        success_message: Success Message (django.contrib.messages)
        context_object_name: Custom Context Variable Name
        extra_context: Zusätzliche Context-Daten
        
    Returns:
        Python Code für die View
        
    Example:
        generate_cbv(
            view_name="TaskListView",
            view_type="ListView",
            model="Task",
            htmx_enabled=True,
            paginate_by=25,
            ordering=["-created_at"]
        )
    """
    logger.info(f"Generating {view_type}: {view_name}")
    
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    # Imports sammeln
    imports = []
    mixins = []
    
    # Base view import
    if view_type in ("ListView", "DetailView"):
        imports.append(f"from django.views.generic import {view_type}")
    elif view_type in ("CreateView", "UpdateView", "DeleteView"):
        imports.append(f"from django.views.generic.edit import {view_type}")
    elif view_type == "FormView":
        imports.append("from django.views.generic import FormView")
    
    # Mixins
    if login_required:
        imports.append("from django.contrib.auth.mixins import LoginRequiredMixin")
        mixins.append("LoginRequiredMixin")
    
    if permission_required:
        imports.append("from django.contrib.auth.mixins import PermissionRequiredMixin")
        mixins.append("PermissionRequiredMixin")
    
    if success_message:
        imports.append("from django.contrib.messages.views import SuccessMessageMixin")
        mixins.append("SuccessMessageMixin")
    
    # HTMX imports
    if htmx_enabled:
        imports.append("from django.http import HttpResponse")
    
    # Model import
    imports.append(f"from .models import {model}")
    
    # Form import
    if form_class:
        imports.append(f"from .forms import {form_class}")
    
    # URL reverse
    if success_url and "reverse" in success_url:
        imports.append("from django.urls import reverse_lazy")
    
    # Build class definition
    base_classes = mixins + [view_type]
    bases_str = ", ".join(base_classes)
    
    # Default template name
    if not template_name:
        if view_type == "ListView":
            template_name = f"{app_name}/{model_snake}_list.html"
        elif view_type == "DetailView":
            template_name = f"{app_name}/{model_snake}_detail.html"
        elif view_type == "CreateView":
            template_name = f"{app_name}/{model_snake}_form.html"
        elif view_type == "UpdateView":
            template_name = f"{app_name}/{model_snake}_form.html"
        elif view_type == "DeleteView":
            template_name = f"{app_name}/{model_snake}_confirm_delete.html"
        elif view_type == "FormView":
            template_name = f"{app_name}/{model_snake}_form.html"
    
    # Default partial template
    if htmx_enabled and not htmx_partial_template:
        if view_type == "ListView":
            htmx_partial_template = f"{app_name}/partials/{model_snake}_list_partial.html"
        elif view_type == "DetailView":
            htmx_partial_template = f"{app_name}/partials/{model_snake}_detail_partial.html"
        else:
            htmx_partial_template = f"{app_name}/partials/{model_snake}_form_partial.html"
    
    # Default context_object_name
    if not context_object_name:
        if view_type == "ListView":
            context_object_name = model_plural
        else:
            context_object_name = model_snake
    
    # Build code
    lines = []
    
    # Imports
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    # Class definition
    lines.append(f"class {view_name}({bases_str}):")
    lines.append(f'    """')
    if view_type == "ListView":
        lines.append(f"    Display a list of {model} objects.")
    elif view_type == "DetailView":
        lines.append(f"    Display a single {model} object.")
    elif view_type == "CreateView":
        lines.append(f"    Create a new {model} object.")
    elif view_type == "UpdateView":
        lines.append(f"    Update an existing {model} object.")
    elif view_type == "DeleteView":
        lines.append(f"    Delete a {model} object.")
    if htmx_enabled:
        lines.append(f"    ")
        lines.append(f"    Supports HTMX requests with partial template rendering.")
    lines.append(f'    """')
    lines.append(f"")
    
    # Class attributes
    lines.append(f"    model = {model}")
    lines.append(f'    template_name = "{template_name}"')
    lines.append(f'    context_object_name = "{context_object_name}"')
    
    if htmx_enabled and htmx_partial_template:
        lines.append(f'    partial_template_name = "{htmx_partial_template}"')
    
    if permission_required:
        lines.append(f'    permission_required = "{permission_required}"')
    
    if paginate_by:
        lines.append(f"    paginate_by = {paginate_by}")
    
    if ordering:
        lines.append(f"    ordering = {ordering}")
    
    if form_class:
        lines.append(f"    form_class = {form_class}")
    elif fields:
        lines.append(f"    fields = {fields}")
    
    if success_url:
        if success_url.startswith("reverse"):
            lines.append(f"    success_url = {success_url}")
        else:
            lines.append(f'    success_url = "{success_url}"')
    elif view_type in ("CreateView", "UpdateView", "DeleteView"):
        lines.append(f'    success_url = reverse_lazy("{app_name}:{model_snake}_list")')
        if "reverse_lazy" not in "\n".join(imports):
            imports.append("from django.urls import reverse_lazy")
    
    if success_message:
        lines.append(f'    success_message = "{success_message}"')
    
    if extra_context:
        lines.append(f"    extra_context = {extra_context}")
    
    # HTMX methods
    if htmx_enabled:
        lines.append("")
        
        if view_type == "ListView":
            lines.append("    def get_template_names(self):")
            lines.append('        """Return partial template for HTMX requests."""')
            lines.append('        if self.request.headers.get("HX-Request"):')
            lines.append("            return [self.partial_template_name]")
            lines.append("        return [self.template_name]")
        
        elif view_type in ("CreateView", "UpdateView"):
            lines.append("    def get_template_names(self):")
            lines.append('        """Return partial template for HTMX requests."""')
            lines.append('        if self.request.headers.get("HX-Request"):')
            lines.append("            return [self.partial_template_name]")
            lines.append("        return [self.template_name]")
            lines.append("")
            lines.append("    def form_valid(self, form):")
            lines.append('        """Handle successful form submission."""')
            lines.append("        response = super().form_valid(form)")
            lines.append('        if self.request.headers.get("HX-Request"):')
            lines.append('            # Trigger event for HTMX listeners')
            lines.append(f'            response["HX-Trigger"] = "{model_snake}Changed"')
            lines.append("        return response")
            lines.append("")
            lines.append("    def form_invalid(self, form):")
            lines.append('        """Handle form validation errors."""')
            lines.append("        response = super().form_invalid(form)")
            lines.append('        if self.request.headers.get("HX-Request"):')
            lines.append('            # Return 422 for HTMX to handle as error')
            lines.append("            response.status_code = 422")
            lines.append("        return response")
        
        elif view_type == "DeleteView":
            lines.append("    def delete(self, request, *args, **kwargs):")
            lines.append('        """Handle deletion with HTMX support."""')
            lines.append("        self.object = self.get_object()")
            lines.append("        self.object.delete()")
            lines.append('        if request.headers.get("HX-Request"):')
            lines.append('            response = HttpResponse(status=200)')
            lines.append(f'            response["HX-Trigger"] = "{model_snake}Deleted"')
            lines.append("            return response")
            lines.append("        return super().delete(request, *args, **kwargs)")
    
    # Re-add missing imports at top
    code = "\n".join(lines)
    if "reverse_lazy" in code and "reverse_lazy" not in code.split("\n\n")[0]:
        first_import = code.split("\n")[0]
        if "django.urls" in first_import:
            code = code.replace(
                "from django.urls import reverse_lazy",
                "from django.urls import reverse_lazy"
            )
        else:
            code = "from django.urls import reverse_lazy\n" + code
    
    return code


@mcp.tool()
def generate_htmx_action_view(
    view_name: str,
    model: str,
    action: Literal["toggle", "inline_edit", "quick_action", "bulk_action"],
    field: str | None = None,
    app_name: str = "app",
    login_required: bool = True,
) -> str:
    """
    Generiert eine spezialisierte HTMX Action View.
    
    Args:
        view_name: Name der View
        model: Model Name
        action: Art der Aktion:
            - toggle: Boolean Feld togglen (z.B. is_active, is_complete)
            - inline_edit: Einzelnes Feld inline editieren
            - quick_action: Schnelle Aktion (z.B. Archive, Duplicate)
            - bulk_action: Mehrere Objekte auf einmal bearbeiten
        field: Feld für toggle/inline_edit
        app_name: Django App Name
        login_required: LoginRequiredMixin
        
    Returns:
        Python Code für die Action View
    """
    logger.info(f"Generating HTMX action view: {view_name}")
    
    model_snake = snake_case(model)
    
    imports = [
        "from django.http import HttpResponse",
        "from django.views import View",
        "from django.shortcuts import get_object_or_404",
        f"from .models import {model}",
    ]
    
    if login_required:
        imports.append("from django.contrib.auth.mixins import LoginRequiredMixin")
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    base = "LoginRequiredMixin, View" if login_required else "View"
    lines.append(f"class {view_name}({base}):")
    
    if action == "toggle":
        lines.append(f'    """Toggle {field} field via HTMX."""')
        lines.append("")
        lines.append("    def post(self, request, pk):")
        lines.append(f"        obj = get_object_or_404({model}, pk=pk)")
        lines.append(f"        obj.{field} = not obj.{field}")
        lines.append(f"        obj.save(update_fields=['{field}'])")
        lines.append("")
        lines.append("        # Return updated partial")
        lines.append(f'        response = HttpResponse()')
        lines.append(f'        response["HX-Trigger"] = "{model_snake}Updated"')
        lines.append("        return response")
    
    elif action == "inline_edit":
        lines.append(f'    """Inline edit {field} field via HTMX."""')
        lines.append("")
        lines.append("    def get(self, request, pk):")
        lines.append('        """Return edit form."""')
        lines.append(f"        obj = get_object_or_404({model}, pk=pk)")
        lines.append("        # Render inline edit form partial")
        lines.append(f'        from django.template.loader import render_to_string')
        lines.append(f'        html = render_to_string(')
        lines.append(f'            "{app_name}/partials/{model_snake}_inline_edit.html",')
        lines.append(f'            {{"object": obj, "field": "{field}"}},')
        lines.append(f'            request=request')
        lines.append(f'        )')
        lines.append(f'        return HttpResponse(html)')
        lines.append("")
        lines.append("    def post(self, request, pk):")
        lines.append('        """Save inline edit."""')
        lines.append(f"        obj = get_object_or_404({model}, pk=pk)")
        lines.append(f"        value = request.POST.get('{field}')")
        lines.append(f"        setattr(obj, '{field}', value)")
        lines.append(f"        obj.save(update_fields=['{field}'])")
        lines.append("")
        lines.append("        # Return display partial")
        lines.append(f'        from django.template.loader import render_to_string')
        lines.append(f'        html = render_to_string(')
        lines.append(f'            "{app_name}/partials/{model_snake}_inline_display.html",')
        lines.append(f'            {{"object": obj}},')
        lines.append(f'            request=request')
        lines.append(f'        )')
        lines.append(f'        return HttpResponse(html)')
    
    elif action == "quick_action":
        lines.append(f'    """Quick action on {model} via HTMX."""')
        lines.append("")
        lines.append("    def post(self, request, pk, action):")
        lines.append(f"        obj = get_object_or_404({model}, pk=pk)")
        lines.append("")
        lines.append('        if action == "archive":')
        lines.append("            obj.is_archived = True")
        lines.append("            obj.save(update_fields=['is_archived'])")
        lines.append('        elif action == "duplicate":')
        lines.append("            obj.pk = None")
        lines.append("            obj.save()")
        lines.append("")
        lines.append(f'        response = HttpResponse()')
        lines.append(f'        response["HX-Trigger"] = "{model_snake}ActionComplete"')
        lines.append("        return response")
    
    elif action == "bulk_action":
        lines.append(f'    """Bulk action on multiple {model} objects via HTMX."""')
        lines.append("")
        lines.append("    def post(self, request):")
        lines.append('        """Process bulk action."""')
        lines.append("        ids = request.POST.getlist('ids')")
        lines.append("        action = request.POST.get('action')")
        lines.append("")
        lines.append(f"        queryset = {model}.objects.filter(pk__in=ids)")
        lines.append("")
        lines.append('        if action == "delete":')
        lines.append("            count = queryset.count()")
        lines.append("            queryset.delete()")
        lines.append('        elif action == "archive":')
        lines.append("            count = queryset.update(is_archived=True)")
        lines.append("")
        lines.append(f'        response = HttpResponse(f"{{count}} items processed")')
        lines.append(f'        response["HX-Trigger"] = "{model_snake}BulkActionComplete"')
        lines.append("        return response")
    
    return "\n".join(lines)


@mcp.tool()
def generate_htmx_search_view(
    view_name: str,
    model: str,
    search_fields: list[str],
    app_name: str = "app",
    result_template: str | None = None,
    min_chars: int = 2,
    debounce_ms: int = 300,
) -> str:
    """
    Generiert eine HTMX Live Search View.
    
    Args:
        view_name: Name der View
        model: Model Name
        search_fields: Felder die durchsucht werden
        app_name: Django App Name
        result_template: Template für Suchergebnisse
        min_chars: Minimale Zeichen für Suche
        debounce_ms: Debounce in Millisekunden
        
    Returns:
        Python Code für die Search View + Template Hint
    """
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    if not result_template:
        result_template = f"{app_name}/partials/{model_snake}_search_results.html"
    
    # Build Q filter
    q_parts = [f'Q({f}__icontains=query)' for f in search_fields]
    q_filter = " | ".join(q_parts)
    
    lines = [
        "from django.db.models import Q",
        "from django.http import HttpResponse",
        "from django.template.loader import render_to_string",
        "from django.views import View",
        f"from .models import {model}",
        "",
        "",
        f"class {view_name}(View):",
        f'    """',
        f'    Live search for {model} objects.',
        f'    ',
        f'    Template should use:',
        f'        hx-get="{{{{ url \'{app_name}:{model_snake}_search\' }}}}"',
        f'        hx-trigger="keyup changed delay:{debounce_ms}ms"',
        f'        hx-target="#search-results"',
        f'        name="q"',
        f'    """',
        f'    ',
        f'    template_name = "{result_template}"',
        f'    min_chars = {min_chars}',
        f'    ',
        f'    def get(self, request):',
        f'        query = request.GET.get("q", "").strip()',
        f'        ',
        f'        if len(query) < self.min_chars:',
        f'            return HttpResponse("")',
        f'        ',
        f'        {model_plural} = {model}.objects.filter(',
        f'            {q_filter}',
        f'        )[:20]  # Limit results',
        f'        ',
        f'        html = render_to_string(',
        f'            self.template_name,',
        f'            {{"{model_plural}": {model_plural}, "query": query}},',
        f'            request=request',
        f'        )',
        f'        return HttpResponse(html)',
    ]
    
    return "\n".join(lines)
