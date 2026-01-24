"""
Scaffolding Tools.

Tools zum Scaffolden kompletter Django Apps und Komponenten.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize
from django_htmx_mcp.tools.models import generate_django_model
from django_htmx_mcp.tools.views import generate_cbv
from django_htmx_mcp.tools.forms import generate_model_form
from django_htmx_mcp.tools.urls import generate_crud_urls
from django_htmx_mcp.tools.templates import generate_htmx_list_template, generate_htmx_form_template
from django_htmx_mcp.tools.tests import generate_model_tests


@mcp.tool()
def scaffold_django_app(
    app_name: str,
    models: list[dict],
    with_admin: bool = True,
    with_api: bool = False,
    with_tests: bool = True,
    template_style: Literal["htmx", "traditional"] = "htmx",
) -> dict:
    """
    Scaffolded eine komplette Django App.
    
    Args:
        app_name: Name der App
        models: Liste von Model-Definitionen:
            - name: Model Name
            - fields: Field-Definitionen
        with_admin: Admin generieren
        with_api: DRF API generieren
        with_tests: Tests generieren
        template_style: htmx oder traditional
        
    Returns:
        Dict mit allen generierten Dateien
        
    Example:
        scaffold_django_app(
            app_name="tasks",
            models=[{
                "name": "Task",
                "fields": [
                    {"name": "title", "type": "CharField", "max_length": 200},
                    {"name": "completed", "type": "BooleanField", "default": False},
                ]
            }]
        )
    """
    logger.info(f"Scaffolding Django app: {app_name}")
    
    files = {}
    
    # models.py
    models_code = [
        "from django.db import models",
        "from django.urls import reverse",
        "",
    ]
    
    for model_def in models:
        model_code = generate_django_model(
            model_name=model_def["name"],
            fields=model_def.get("fields", []),
            app_name=app_name,
            with_timestamps=model_def.get("with_timestamps", True),
        )
        # Skip imports from individual model (we have them at top)
        lines = model_code.split("\n")
        class_start = next(i for i, l in enumerate(lines) if l.startswith("class "))
        models_code.append("\n".join(lines[class_start:]))
        models_code.append("")
    
    files["models.py"] = "\n".join(models_code)
    
    # views.py
    views_imports = [
        "from django.views.generic import ListView, DetailView",
        "from django.views.generic.edit import CreateView, UpdateView, DeleteView",
        "from django.urls import reverse_lazy",
        "from django.http import HttpResponse",
        "",
    ]
    views_imports.append(f"from .models import {', '.join(m['name'] for m in models)}")
    views_imports.append(f"from .forms import {', '.join(m['name'] + 'Form' for m in models)}")
    views_imports.extend(["", ""])
    
    views_code = views_imports
    
    for model_def in models:
        model = model_def["name"]
        model_snake = snake_case(model)
        
        for vtype in ["ListView", "DetailView", "CreateView", "UpdateView", "DeleteView"]:
            view_code = generate_cbv(
                view_name=f"{model}{vtype}",
                view_type=vtype,
                model=model,
                app_name=app_name,
                htmx_enabled=(template_style == "htmx"),
                fields=["__all__"] if vtype in ["CreateView", "UpdateView"] else None,
            )
            # Extract just the class (skip imports)
            lines = view_code.split("\n")
            class_start = next(i for i, l in enumerate(lines) if l.startswith("class "))
            views_code.append("\n".join(lines[class_start:]))
            views_code.append("")
    
    files["views.py"] = "\n".join(views_code)
    
    # forms.py
    forms_code = [
        "from django import forms",
        "",
        f"from .models import {', '.join(m['name'] for m in models)}",
        "",
        "",
    ]
    
    for model_def in models:
        form_code = generate_model_form(
            model=model_def["name"],
            fields="__all__",
        )
        lines = form_code.split("\n")
        class_start = next(i for i, l in enumerate(lines) if l.startswith("class "))
        forms_code.append("\n".join(lines[class_start:]))
        forms_code.append("")
    
    files["forms.py"] = "\n".join(forms_code)
    
    # urls.py
    urls_parts = [
        "from django.urls import path",
        "",
        "from . import views",
        "",
        "",
        f'app_name = "{app_name}"',
        "",
        "urlpatterns = [",
    ]
    
    for model_def in models:
        model = model_def["name"]
        model_snake = snake_case(model)
        model_plural = pluralize(model_snake)
        
        urls_parts.extend([
            f"    # {model}",
            f'    path("{model_plural}/", views.{model}ListView.as_view(), name="{model_snake}_list"),',
            f'    path("{model_plural}/create/", views.{model}CreateView.as_view(), name="{model_snake}_create"),',
            f'    path("{model_plural}/<int:pk>/", views.{model}DetailView.as_view(), name="{model_snake}_detail"),',
            f'    path("{model_plural}/<int:pk>/update/", views.{model}UpdateView.as_view(), name="{model_snake}_update"),',
            f'    path("{model_plural}/<int:pk>/delete/", views.{model}DeleteView.as_view(), name="{model_snake}_delete"),',
            "",
        ])
    
    urls_parts.append("]")
    files["urls.py"] = "\n".join(urls_parts)
    
    # admin.py
    if with_admin:
        admin_code = [
            "from django.contrib import admin",
            "",
            f"from .models import {', '.join(m['name'] for m in models)}",
            "",
            "",
        ]
        
        for model_def in models:
            model = model_def["name"]
            fields = model_def.get("fields", [])
            list_display = ["pk"]
            for f in fields[:4]:  # Max 4 fields in list
                if f.get("type") not in ("TextField", "ForeignKey", "ManyToManyField"):
                    list_display.append(f["name"])
            
            admin_code.extend([
                f"@admin.register({model})",
                f"class {model}Admin(admin.ModelAdmin):",
                f"    list_display = {list_display}",
                f'    search_fields = ["{fields[0]["name"] if fields else "pk"}"]',
                "",
                "",
            ])
        
        files["admin.py"] = "\n".join(admin_code)
    
    # Templates
    for model_def in models:
        model = model_def["name"]
        model_snake = snake_case(model)
        
        if template_style == "htmx":
            templates = generate_htmx_list_template(
                model=model,
                app_name=app_name,
                with_search=True,
                with_pagination=True,
            )
            files[f"templates/{app_name}/{model_snake}_list.html"] = templates["page_template"]
            files[f"templates/{app_name}/partials/{model_snake}_list_partial.html"] = templates["partial_template"]
        
        form_template = generate_htmx_form_template(
            model=model,
            app_name=app_name,
            form_type="page",
        )
        files[f"templates/{app_name}/{model_snake}_form.html"] = form_template
    
    # Tests
    if with_tests:
        test_code = [
            "import pytest",
            "from django.urls import reverse",
            "",
            f"from {app_name}.models import {', '.join(m['name'] for m in models)}",
            "",
            "",
        ]
        
        for model_def in models:
            model = model_def["name"]
            model_test = generate_model_tests(
                model=model,
                app_name=app_name,
                with_factory=False,
            )
            lines = model_test.split("\n")
            class_start = next(i for i, l in enumerate(lines) if l.startswith("@pytest"))
            test_code.append("\n".join(lines[class_start:]))
            test_code.append("")
        
        files["tests/test_models.py"] = "\n".join(test_code)
        files["tests/__init__.py"] = ""
    
    # __init__.py
    files["__init__.py"] = f'"""Django app: {app_name}."""'
    
    # apps.py
    files["apps.py"] = f'''from django.apps import AppConfig


class {app_name.title().replace("_", "")}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app_name}"
'''
    
    return {
        "app_name": app_name,
        "files": files,
        "instructions": f"""
App '{app_name}' scaffolded successfully!

Next steps:
1. Add '{app_name}' to INSTALLED_APPS in settings.py
2. Add URL pattern: path('{app_name}/', include('{app_name}.urls'))
3. Run migrations: python manage.py makemigrations {app_name} && python manage.py migrate
4. Create templates directory: mkdir -p {app_name}/templates/{app_name}/partials
        """,
    }


@mcp.tool()
def scaffold_htmx_component(
    component_name: str,
    component_type: Literal[
        "searchable_select",
        "infinite_scroll",
        "live_search",
        "dependent_dropdown",
        "inline_edit",
        "toast_notifications",
        "modal_form",
        "sortable_table",
        "tabs",
        "accordion",
    ],
    model: str | None = None,
    app_name: str = "app",
) -> dict:
    """
    Scaffolded eine wiederverwendbare HTMX-Komponente.
    
    Args:
        component_name: Name der Komponente
        component_type: Typ der Komponente
        model: Model für datengebundene Komponenten
        app_name: Django App Name
        
    Returns:
        Dict mit view, template, url, und usage instructions
    """
    logger.info(f"Scaffolding HTMX component: {component_name} ({component_type})")
    
    model_snake = snake_case(model) if model else "item"
    
    components = {
        "searchable_select": _scaffold_searchable_select,
        "infinite_scroll": _scaffold_infinite_scroll,
        "live_search": _scaffold_live_search,
        "dependent_dropdown": _scaffold_dependent_dropdown,
        "inline_edit": _scaffold_inline_edit,
        "toast_notifications": _scaffold_toast_notifications,
        "modal_form": _scaffold_modal_form,
        "sortable_table": _scaffold_sortable_table,
        "tabs": _scaffold_tabs,
        "accordion": _scaffold_accordion,
    }
    
    scaffold_fn = components.get(component_type)
    if scaffold_fn:
        return scaffold_fn(component_name, model, model_snake, app_name)
    
    return {"error": f"Unknown component type: {component_type}"}


def _scaffold_searchable_select(name: str, model: str, model_snake: str, app_name: str) -> dict:
    view = f'''from django.http import JsonResponse
from django.views import View
from .models import {model}


class {name}View(View):
    """Searchable select dropdown via HTMX."""
    
    def get(self, request):
        query = request.GET.get("q", "")
        results = {model}.objects.filter(name__icontains=query)[:20]
        
        options = [{{"id": obj.pk, "text": str(obj)}} for obj in results]
        return JsonResponse({{"results": options}})
'''
    
    template = f'''<!-- Searchable Select Component -->
<div class="searchable-select" x-data="{{open: false, search: '', selected: null}}">
    <input type="hidden" name="{model_snake}_id" :value="selected?.id">
    
    <div class="relative">
        <input type="text"
               x-model="search"
               @focus="open = true"
               @input.debounce.300ms="$refs.results.innerHTML = '...'"
               hx-get="{{{{ url '{app_name}:{model_snake}_search' }}}}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#search-results"
               name="q"
               placeholder="Search {model}..."
               class="input input-bordered w-full">
        
        <div x-show="open"
             @click.outside="open = false"
             class="absolute z-10 w-full bg-base-100 border rounded-lg mt-1 max-h-60 overflow-auto"
             id="search-results"
             x-ref="results">
            <!-- Results loaded via HTMX -->
        </div>
    </div>
</div>
'''
    
    return {
        "view": view,
        "template": template,
        "url": f'path("{model_snake}/search/", views.{name}View.as_view(), name="{model_snake}_search"),',
        "usage": f"Include the template partial and add the URL pattern.",
    }


def _scaffold_infinite_scroll(name: str, model: str, model_snake: str, app_name: str) -> dict:
    view = f'''from django.views.generic import ListView
from .models import {model}


class {name}View(ListView):
    """Infinite scroll list view."""
    
    model = {model}
    paginate_by = 20
    template_name = "{app_name}/{model_snake}_infinite.html"
    
    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["{app_name}/partials/{model_snake}_items.html"]
        return [self.template_name]
'''
    
    template = f'''<!-- Items Partial for Infinite Scroll -->
{{% for {model_snake} in object_list %}}
<div class="{model_snake}-item p-4 border-b">
    {{{{ {model_snake} }}}}
</div>
{{% endfor %}}

{{% if page_obj.has_next %}}
<div hx-get="{{{{ url '{app_name}:{model_snake}_list' }}}}?page={{{{ page_obj.next_page_number }}}}"
     hx-trigger="revealed"
     hx-swap="afterend"
     class="loading-trigger">
    <span class="loading loading-spinner"></span>
</div>
{{% endif %}}
'''
    
    return {
        "view": view,
        "template": template,
        "url": f'path("{model_snake}s/", views.{name}View.as_view(), name="{model_snake}_list"),',
        "usage": "The list loads more items as user scrolls to the bottom.",
    }


def _scaffold_live_search(name: str, model: str, model_snake: str, app_name: str) -> dict:
    view = f'''from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from .models import {model}


class {name}View(View):
    """Live search with instant results."""
    
    def get(self, request):
        query = request.GET.get("q", "").strip()
        
        if len(query) < 2:
            return HttpResponse("")
        
        results = {model}.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:10]
        
        html = render_to_string(
            "{app_name}/partials/{model_snake}_search_results.html",
            {{"results": results, "query": query}},
            request=request
        )
        return HttpResponse(html)
'''
    
    template = f'''<!-- Search Results Partial -->
{{% if results %}}
<ul class="menu bg-base-100 rounded-box">
    {{% for item in results %}}
    <li>
        <a href="{{{{ item.get_absolute_url }}}}">
            {{{{ item.name }}}}
        </a>
    </li>
    {{% endfor %}}
</ul>
{{% else %}}
<p class="p-4 text-gray-500">No results for "{{{{ query }}}}"</p>
{{% endif %}}
'''
    
    return {
        "view": view,
        "template": template,
        "url": f'path("search/", views.{name}View.as_view(), name="{model_snake}_search"),',
        "usage": '''
<input type="text"
       name="q"
       hx-get="{{ url 'app:search' }}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#results">
<div id="results"></div>
''',
    }


def _scaffold_dependent_dropdown(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return {
        "view": f'''from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View


class {name}View(View):
    """Dependent dropdown - second dropdown depends on first."""
    
    def get(self, request):
        parent_id = request.GET.get("parent_id")
        
        if not parent_id:
            return HttpResponse('<option value="">Select parent first</option>')
        
        # Replace with your actual dependent model query
        children = ChildModel.objects.filter(parent_id=parent_id)
        
        html = render_to_string(
            "{app_name}/partials/dependent_options.html",
            {{"children": children}}
        )
        return HttpResponse(html)
''',
        "template": '''<!-- Parent Select -->
<select name="parent_id"
        hx-get="{{ url 'app:get_children' }}"
        hx-target="#child-select"
        hx-trigger="change">
    <option value="">Select Parent</option>
    {% for parent in parents %}
    <option value="{{ parent.pk }}">{{ parent }}</option>
    {% endfor %}
</select>

<!-- Child Select (populated via HTMX) -->
<select name="child_id" id="child-select">
    <option value="">Select parent first</option>
</select>
''',
        "url": f'path("get-children/", views.{name}View.as_view(), name="get_children"),',
        "usage": "Parent dropdown triggers HTMX request to populate child dropdown.",
    }


def _scaffold_inline_edit(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return {
        "view": f'''from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views import View
from .models import {model}


class {name}View(View):
    """Inline edit field."""
    
    def get(self, request, pk, field):
        """Show edit form."""
        obj = get_object_or_404({model}, pk=pk)
        html = render_to_string(
            "{app_name}/partials/{model_snake}_inline_edit.html",
            {{"object": obj, "field": field, "value": getattr(obj, field)}}
        )
        return HttpResponse(html)
    
    def post(self, request, pk, field):
        """Save edit."""
        obj = get_object_or_404({model}, pk=pk)
        value = request.POST.get("value")
        setattr(obj, field, value)
        obj.save(update_fields=[field])
        
        html = render_to_string(
            "{app_name}/partials/{model_snake}_inline_display.html",
            {{"object": obj, "field": field, "value": value}}
        )
        return HttpResponse(html)
''',
        "template": '''<!-- Inline Display (click to edit) -->
<span class="inline-editable"
      hx-get="{{ url 'app:inline_edit' object.pk field }}"
      hx-trigger="click"
      hx-swap="outerHTML">
    {{ value }}
</span>

<!-- Inline Edit Form (shown on click) -->
<form hx-post="{{ url 'app:inline_edit' object.pk field }}"
      hx-swap="outerHTML"
      class="inline-flex gap-2">
    <input type="text" name="value" value="{{ value }}" class="input input-sm">
    <button type="submit" class="btn btn-sm btn-primary">Save</button>
    <button type="button"
            hx-get="{{ object.get_absolute_url }}"
            hx-target="this"
            hx-swap="outerHTML"
            class="btn btn-sm">Cancel</button>
</form>
''',
        "url": f'path("{model_snake}/<int:pk>/edit/<str:field>/", views.{name}View.as_view(), name="inline_edit"),',
        "usage": "Click on a field value to edit it inline.",
    }


# Simplified placeholders for remaining components
def _scaffold_toast_notifications(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return {
        "view": "# Toast notifications are typically handled client-side",
        "template": '''<!-- Toast Container -->
<div id="toast-container" class="toast toast-end"></div>

<!-- Toast Template (shown via HTMX HX-Trigger) -->
<template id="toast-template">
    <div class="alert" x-data="{show: true}" x-show="show" 
         x-init="setTimeout(() => show = false, 3000)">
        <span class="toast-message"></span>
    </div>
</template>

<script>
document.body.addEventListener("showToast", function(evt) {
    const container = document.getElementById("toast-container");
    const template = document.getElementById("toast-template");
    const toast = template.content.cloneNode(true);
    toast.querySelector(".toast-message").textContent = evt.detail.message;
    toast.querySelector(".alert").classList.add("alert-" + (evt.detail.type || "info"));
    container.appendChild(toast);
});
</script>
''',
        "url": "# No URL needed - triggered via HX-Trigger header",
        "usage": 'Add HX-Trigger: {"showToast": {"message": "Saved!", "type": "success"}} to response headers.',
    }


def _scaffold_modal_form(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return _scaffold_searchable_select(name, model, model_snake, app_name)


def _scaffold_sortable_table(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return _scaffold_infinite_scroll(name, model, model_snake, app_name)


def _scaffold_tabs(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return {
        "view": "# Tabs can be pure HTMX without server view",
        "template": '''<!-- Tabs Component -->
<div class="tabs tabs-boxed">
    <a class="tab tab-active"
       hx-get="{{ url 'app:tab_content' }}?tab=1"
       hx-target="#tab-content"
       hx-swap="innerHTML">Tab 1</a>
    <a class="tab"
       hx-get="{{ url 'app:tab_content' }}?tab=2"
       hx-target="#tab-content"
       hx-swap="innerHTML">Tab 2</a>
</div>
<div id="tab-content" class="p-4">
    <!-- Tab content loaded here -->
</div>
''',
        "url": 'path("tab-content/", views.TabContentView.as_view(), name="tab_content"),',
        "usage": "Tabs load content via HTMX on click.",
    }


def _scaffold_accordion(name: str, model: str, model_snake: str, app_name: str) -> dict:
    return {
        "view": "# Accordion can be pure CSS/JS or HTMX-powered",
        "template": '''<!-- Accordion Component -->
<div class="accordion">
    {% for item in items %}
    <div class="collapse collapse-arrow border border-base-300 bg-base-100 rounded-box mb-2">
        <input type="radio" name="accordion-{{ forloop.counter }}" />
        <div class="collapse-title text-xl font-medium"
             hx-get="{{ url 'app:accordion_content' item.pk }}"
             hx-target="#content-{{ item.pk }}"
             hx-trigger="click once">
            {{ item.title }}
        </div>
        <div class="collapse-content" id="content-{{ item.pk }}">
            <!-- Content loaded on first expand -->
        </div>
    </div>
    {% endfor %}
</div>
''',
        "url": 'path("accordion/<int:pk>/", views.AccordionContentView.as_view(), name="accordion_content"),',
        "usage": "Accordion items load content lazily when expanded.",
    }
