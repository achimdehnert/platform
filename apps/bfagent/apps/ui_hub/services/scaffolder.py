"""Scaffolding service for generating views and templates."""

from pathlib import Path
from typing import Dict, Optional

from jinja2 import Template

from apps.ui_hub.models import CodeTemplate


class ScaffolderService:
    """Service for scaffolding views, templates, and partials."""

    # Built-in templates
    VIEW_TEMPLATE = """def {{ entity }}_{{ action }}_view(request{% if needs_pk %}, pk{% endif %}):
    \"\"\"{{ action|title }} {{ entity }}.\"\"\"
    {% if action == 'list' -%}
    {{ entity_plural }} = {{ entity|title }}.objects.all()

    if request.htmx:
        return render(request, '{{ app }}/{{ entity }}/partials/_list.html', {
            '{{ entity_plural }}': {{ entity_plural }},
        })

    return render(request, '{{ app }}/{{ entity }}/list.html', {
        '{{ entity_plural }}': {{ entity_plural }},
    })
    {%- elif action == 'detail' -%}
    {{ entity }} = get_object_or_404({{ entity|title }}, pk=pk)

    return render(request, '{{ app }}/{{ entity }}/detail.html', {
        '{{ entity }}': {{ entity }},
    })
    {%- elif action == 'create' -%}
    if request.method == 'POST':
        form = {{ entity|title }}Form(request.POST)
        if form.is_valid():
            {{ entity }} = form.save()

            if request.htmx:
                return render(request, '{{ app }}/{{ entity }}/partials/_row.html', {
                    '{{ entity }}': {{ entity }},
                })

            return redirect('{{ entity }}-detail', pk={{ entity }}.pk)
    else:
        form = {{ entity|title }}Form()

    return render(request, '{{ app }}/{{ entity }}/form.html', {
        'form': form,
    })
    {%- elif action == 'update' -%}
    {{ entity }} = get_object_or_404({{ entity|title }}, pk=pk)

    if request.method == 'POST':
        form = {{ entity|title }}Form(request.POST, instance={{ entity }})
        if form.is_valid():
            {{ entity }} = form.save()

            if request.htmx:
                return render(request, '{{ app }}/{{ entity }}/partials/_row.html', {
                    '{{ entity }}': {{ entity }},
                })

            return redirect('{{ entity }}-detail', pk={{ entity }}.pk)
    else:
        form = {{ entity|title }}Form(instance={{ entity }})

    return render(request, '{{ app }}/{{ entity }}/form.html', {
        'form': form,
        '{{ entity }}': {{ entity }},
    })
    {%- elif action == 'delete' -%}
    {{ entity }} = get_object_or_404({{ entity|title }}, pk=pk)

    if request.method == 'POST':
        {{ entity }}.delete()

        if request.htmx:
            return HttpResponse('')

        return redirect('{{ entity }}-list')

    return render(request, '{{ app }}/{{ entity }}/confirm_delete.html', {
        '{{ entity }}': {{ entity }},
    })
    {%- endif %}
"""

    TEMPLATE_LIST = """{% raw %}{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>{{ entity_title }} List</h1>

    <div id="{{ entity }}-list">
        {% include "{{ app }}/{{ entity }}/partials/_list.html" %}
    </div>
</div>
{% endblock %}{% endraw %}"""

    PARTIAL_ROW = """{% raw %}<tr id="{{ entity }}-{{ object.pk }}" hx-swap-oob="true">
    <td>{{ object.id }}</td>
    <td>{{ object.name }}</td>
    <td>
        <button hx-get="{% url 'htmx-{{ entity }}-edit' object.pk %}"
                hx-target="#{{ entity }}-{{ object.pk }}"
                hx-swap="outerHTML"
                class="btn btn-sm btn-primary">
            Edit
        </button>
        <button hx-delete="{% url 'htmx-{{ entity }}-delete' object.pk %}"
                hx-target="#{{ entity }}-{{ object.pk }}"
                hx-swap="delete"
                hx-confirm="Are you sure?"
                class="btn btn-sm btn-danger">
            Delete
        </button>
    </td>
</tr>{% endraw %}"""

    PARTIAL_FORM = """{% raw %}<form hx-post="{% url 'htmx-{{ entity }}-create' %}"
      hx-target="#{{ entity }}-list"
      hx-swap="beforeend">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Save</button>
    <button type="button" class="btn btn-secondary" onclick="this.closest('form').reset()">Cancel</button>
</form>{% endraw %}"""

    URL_PATTERNS = """# {{ entity|title }} URLs
path('{{ entity }}/', views.{{ entity }}_list_view, name='{{ entity }}-list'),
path('{{ entity }}/<int:pk>/', views.{{ entity }}_detail_view, name='{{ entity }}-detail'),
path('{{ entity }}/create/', views.{{ entity }}_create_view, name='{{ entity }}-create'),
path('{{ entity }}/<int:pk>/update/', views.{{ entity }}_update_view, name='{{ entity }}-update'),
path('{{ entity }}/<int:pk>/delete/', views.{{ entity }}_delete_view, name='{{ entity }}-delete'),

# HTMX endpoints
path('htmx/{{ entity }}/<int:pk>/row/', views.{{ entity }}_htmx_row_view, name='htmx-{{ entity }}-row'),
path('htmx/{{ entity }}/<int:pk>/edit/', views.{{ entity }}_htmx_edit_view, name='htmx-{{ entity }}-edit'),
path('htmx/{{ entity }}/<int:pk>/delete/', views.{{ entity }}_htmx_delete_view, name='htmx-{{ entity }}-delete'),
"""

    def scaffold_view(self, entity: str, action: str, app: str, with_htmx: bool = False) -> Dict:
        """Generate a view function.

        Args:
            entity: Entity name (e.g., 'client', 'invoice')
            action: Action (list, detail, create, update, delete)
            app: App name
            with_htmx: Whether to include HTMX support

        Returns:
            Dict with generated code
        """
        # Check for custom template in DB
        template_name = f"view_{action}"
        try:
            custom_template = CodeTemplate.objects.get(
                name=template_name, template_type="view", is_active=True
            )
            template_str = custom_template.content
        except CodeTemplate.DoesNotExist:
            template_str = self.VIEW_TEMPLATE

        # Prepare context
        entity_plural = entity + "s"  # Simple pluralization
        needs_pk = action in ["detail", "update", "delete"]

        context = {
            "entity": entity,
            "entity_plural": entity_plural,
            "action": action,
            "app": app,
            "needs_pk": needs_pk,
            "with_htmx": with_htmx,
        }

        # Render template
        template = Template(template_str)
        code = template.render(**context)

        return {
            "code": code,
            "file_name": f"{entity}_{action}_view",
            "entity": entity,
            "action": action,
        }

    def scaffold_template(self, entity: str, template_type: str, app: str) -> Dict:
        """Generate an HTML template.

        Args:
            entity: Entity name
            template_type: Type (list, detail, form)
            app: App name

        Returns:
            Dict with generated code
        """
        templates = {
            "list": self.TEMPLATE_LIST,
            "detail": '{% extends "base.html" %}\n\n{% block content %}\n<h1>{{ object }}</h1>\n{% endblock %}',
            "form": '{% extends "base.html" %}\n\n{% block content %}\n<form method="post">\n{% csrf_token %}\n{{ form.as_p }}\n<button type="submit">Save</button>\n</form>\n{% endblock %}',
        }

        template_str = templates.get(template_type, templates["list"])

        context = {
            "entity": entity,
            "entity_title": entity.replace("_", " ").title(),
            "app": app,
        }

        template = Template(template_str)
        code = template.render(**context)

        return {
            "code": code,
            "file_name": f"{entity}/{template_type}.html",
            "path": f"{app}/templates/{app}/{entity}/{template_type}.html",
        }

    def scaffold_htmx_partial(self, entity: str, partial_type: str, app: str) -> Dict:
        """Generate an HTMX partial template.

        Args:
            entity: Entity name
            partial_type: Type (row, form, list, search_results, detail)
            app: App name

        Returns:
            Dict with generated code
        """
        partials = {
            "row": self.PARTIAL_ROW,
            "form": self.PARTIAL_FORM,
            "list": '{% raw %}<div id="{{ entity }}-list">\n{% for object in objects %}\n{% include "partials/_row.html" %}\n{% endfor %}\n</div>{% endraw %}',
        }

        template_str = partials.get(partial_type, partials["row"])

        context = {
            "entity": entity,
            "app": app,
        }

        template = Template(template_str)
        code = template.render(**context)

        return {
            "code": code,
            "file_name": f"_{partial_type}.html",
            "path": f"{app}/templates/{app}/{entity}/partials/_{partial_type}.html",
        }

    def scaffold_urls(self, entity: str, app: str) -> Dict:
        """Generate URL patterns.

        Args:
            entity: Entity name
            app: App name

        Returns:
            Dict with generated code
        """
        context = {
            "entity": entity,
            "app": app,
        }

        template = Template(self.URL_PATTERNS)
        code = template.render(**context)

        return {
            "code": code,
            "file_name": f"{entity}_urls.py",
        }

    def scaffold_full_crud(self, entity: str, app: str, with_htmx: bool = True) -> Dict:
        """Generate full CRUD scaffold (views, templates, URLs).

        Args:
            entity: Entity name
            app: App name
            with_htmx: Include HTMX support

        Returns:
            Dict with all generated files
        """
        results = {
            "views": [],
            "templates": [],
            "partials": [],
            "urls": None,
        }

        # Generate views
        for action in ["list", "detail", "create", "update", "delete"]:
            view = self.scaffold_view(entity, action, app, with_htmx)
            results["views"].append(view)

        # Generate templates
        for template_type in ["list", "detail", "form"]:
            template = self.scaffold_template(entity, template_type, app)
            results["templates"].append(template)

        # Generate HTMX partials
        if with_htmx:
            for partial_type in ["row", "form", "list"]:
                partial = self.scaffold_htmx_partial(entity, partial_type, app)
                results["partials"].append(partial)

        # Generate URLs
        results["urls"] = self.scaffold_urls(entity, app)

        return results
