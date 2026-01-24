"""
Template Generation Tools.

Tools zum Generieren von Django Templates mit HTMX Support.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize


@mcp.tool()
def generate_htmx_list_template(
    model: str,
    app_name: str = "app",
    columns: list[dict] | None = None,
    with_search: bool = True,
    with_pagination: bool = True,
    with_sorting: bool = True,
    with_create_button: bool = True,
    with_inline_actions: bool = True,
    row_click_url: str | None = None,
    infinite_scroll: bool = False,
) -> dict:
    """
    Generiert ein HTMX-fähiges List Template mit Partial.
    
    Args:
        model: Model Name
        app_name: Django App Name
        columns: Spalten-Definitionen:
            - field: Model Field Name
            - label: Column Header (optional)
            - sortable: Sortierbar (default: False)
        with_search: Live Search hinzufügen
        with_pagination: Pagination hinzufügen
        with_sorting: Sortierbare Spalten
        with_create_button: Create Button hinzufügen
        with_inline_actions: Edit/Delete Buttons pro Zeile
        row_click_url: URL für Klick auf Zeile
        infinite_scroll: Infinite Scroll statt Pagination
        
    Returns:
        Dict mit 'page_template' und 'partial_template'
    """
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    # Default columns
    if not columns:
        columns = [
            {"field": "name", "label": "Name", "sortable": True},
            {"field": "created_at", "label": "Created", "sortable": True},
        ]
    
    # === PAGE TEMPLATE ===
    page_lines = [
        '{% extends "base.html" %}',
        f'{{% load static %}}',
        '',
        f'{{% block title %}}{model} List{{% endblock %}}',
        '',
        '{% block content %}',
        f'<div class="container mx-auto px-4 py-8">',
        f'    <div class="flex justify-between items-center mb-6">',
        f'        <h1 class="text-2xl font-bold">{model} List</h1>',
    ]
    
    if with_create_button:
        page_lines.extend([
            f'        <a href="{{{{ url \'{app_name}:{model_snake}_create\' }}}}"',
            f'           class="btn btn-primary"',
            f'           hx-get="{{{{ url \'{app_name}:{model_snake}_create\' }}}}"',
            f'           hx-target="#modal-container"',
            f'           hx-swap="innerHTML">',
            f'            + New {model}',
            f'        </a>',
        ])
    
    page_lines.append('    </div>')
    
    if with_search:
        page_lines.extend([
            '',
            '    <!-- Search -->',
            '    <div class="mb-4">',
            '        <input type="text"',
            '               name="q"',
            '               placeholder="Search..."',
            '               class="input input-bordered w-full max-w-xs"',
            f'               hx-get="{{{{ url \'{app_name}:{model_snake}_list\' }}}}"',
            '               hx-trigger="keyup changed delay:300ms"',
            f'               hx-target="#{model_snake}-list"',
            '               hx-swap="innerHTML"',
            '               hx-include="[name=\'ordering\']">',
            '    </div>',
        ])
    
    page_lines.extend([
        '',
        '    <!-- List Container -->',
        f'    <div id="{model_snake}-list"',
        f'         hx-get="{{{{ url \'{app_name}:{model_snake}_list\' }}}}"',
        '         hx-trigger="load, ' + model_snake + 'Changed from:body"',
        '         hx-swap="innerHTML">',
        '        {% include "' + app_name + '/partials/' + model_snake + '_list_partial.html" %}',
        '    </div>',
        '',
        '    <!-- Modal Container -->',
        '    <div id="modal-container"></div>',
        '</div>',
        '{% endblock %}',
    ])
    
    page_template = "\n".join(page_lines)
    
    # === PARTIAL TEMPLATE ===
    partial_lines = [
        '<!-- Partial: Loaded via HTMX -->',
        '',
        '<table class="table w-full">',
        '    <thead>',
        '        <tr>',
    ]
    
    # Header row
    for col in columns:
        field = col.get("field")
        label = col.get("label", field.replace("_", " ").title())
        sortable = col.get("sortable", False)
        
        if sortable and with_sorting:
            partial_lines.extend([
                f'            <th>',
                f'                <a href="#"',
                f'                   hx-get="{{{{ url \'{app_name}:{model_snake}_list\' }}}}?ordering={field}"',
                f'                   hx-target="#{model_snake}-list"',
                f'                   hx-swap="innerHTML"',
                f'                   class="flex items-center gap-1">',
                f'                    {label}',
                f'                    <span class="sort-indicator">↕</span>',
                f'                </a>',
                f'            </th>',
            ])
        else:
            partial_lines.append(f'            <th>{label}</th>')
    
    if with_inline_actions:
        partial_lines.append('            <th class="text-right">Actions</th>')
    
    partial_lines.extend([
        '        </tr>',
        '    </thead>',
        '    <tbody>',
        f'        {{% for {model_snake} in {model_plural} %}}',
    ])
    
    # Row
    row_attrs = ''
    if row_click_url:
        row_attrs = f' class="cursor-pointer hover:bg-base-200" hx-get="{{{{ {model_snake}.get_absolute_url }}}}" hx-target="#content" hx-swap="innerHTML"'
    
    partial_lines.append(f'        <tr id="{model_snake}-{{{{ {model_snake}.pk }}}}"{row_attrs}>')
    
    for col in columns:
        field = col.get("field")
        partial_lines.append(f'            <td>{{{{ {model_snake}.{field} }}}}</td>')
    
    if with_inline_actions:
        partial_lines.extend([
            '            <td class="text-right">',
            f'                <a href="{{{{ url \'{app_name}:{model_snake}_update\' {model_snake}.pk }}}}"',
            f'                   hx-get="{{{{ url \'{app_name}:{model_snake}_update\' {model_snake}.pk }}}}"',
            '                   hx-target="#modal-container"',
            '                   class="btn btn-sm btn-ghost">',
            '                    Edit',
            '                </a>',
            f'                <button hx-delete="{{{{ url \'{app_name}:{model_snake}_delete\' {model_snake}.pk }}}}"',
            '                        hx-confirm="Are you sure?"',
            f'                        hx-target="#{model_snake}-{{{{ {model_snake}.pk }}}}"',
            '                        hx-swap="outerHTML"',
            '                        class="btn btn-sm btn-ghost text-error">',
            '                    Delete',
            '                </button>',
            '            </td>',
        ])
    
    partial_lines.extend([
        '        </tr>',
        '        {% empty %}',
        '        <tr>',
        f'            <td colspan="{len(columns) + (1 if with_inline_actions else 0)}" class="text-center py-8 text-gray-500">',
        f'                No {model_plural} found.',
        '            </td>',
        '        </tr>',
        '        {% endfor %}',
        '    </tbody>',
        '</table>',
    ])
    
    if with_pagination and not infinite_scroll:
        partial_lines.extend([
            '',
            '<!-- Pagination -->',
            '{% if page_obj.has_other_pages %}',
            '<div class="flex justify-center mt-4 gap-2">',
            '    {% if page_obj.has_previous %}',
            f'    <a href="?page={{{{ page_obj.previous_page_number }}}}"',
            f'       hx-get="{{{{ url \'{app_name}:{model_snake}_list\' }}}}?page={{{{ page_obj.previous_page_number }}}}"',
            f'       hx-target="#{model_snake}-list"',
            '       class="btn btn-sm">Previous</a>',
            '    {% endif %}',
            '    <span class="btn btn-sm btn-disabled">',
            '        Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}',
            '    </span>',
            '    {% if page_obj.has_next %}',
            f'    <a href="?page={{{{ page_obj.next_page_number }}}}"',
            f'       hx-get="{{{{ url \'{app_name}:{model_snake}_list\' }}}}?page={{{{ page_obj.next_page_number }}}}"',
            f'       hx-target="#{model_snake}-list"',
            '       class="btn btn-sm">Next</a>',
            '    {% endif %}',
            '</div>',
            '{% endif %}',
        ])
    
    if infinite_scroll:
        partial_lines.extend([
            '',
            '<!-- Infinite Scroll Trigger -->',
            '{% if page_obj.has_next %}',
            '<div hx-get="{{ url \'' + app_name + ':' + model_snake + '_list\' }}?page={{ page_obj.next_page_number }}"',
            '     hx-trigger="revealed"',
            '     hx-swap="afterend"',
            '     class="htmx-indicator py-4 text-center">',
            '    <span class="loading loading-spinner"></span>',
            '</div>',
            '{% endif %}',
        ])
    
    partial_template = "\n".join(partial_lines)
    
    return {
        "page_template": page_template,
        "page_template_path": f"{app_name}/{model_snake}_list.html",
        "partial_template": partial_template,
        "partial_template_path": f"{app_name}/partials/{model_snake}_list_partial.html",
    }


@mcp.tool()
def generate_htmx_form_template(
    model: str,
    app_name: str = "app",
    form_type: Literal["page", "modal", "inline"] = "page",
    fields: list[str] | None = None,
    with_validation_errors: bool = True,
    with_loading_indicator: bool = True,
    cancel_url: str | None = None,
) -> str:
    """
    Generiert ein HTMX Form Template.
    
    Args:
        model: Model Name
        app_name: Django App Name
        form_type: page (volle Seite), modal (in Modal), inline (inline edit)
        fields: Explizite Felder (None = alle aus form)
        with_validation_errors: Inline Validation Errors
        with_loading_indicator: Loading Spinner beim Submit
        cancel_url: URL für Cancel Button
        
    Returns:
        Template Code
    """
    model_snake = snake_case(model)
    
    if form_type == "modal":
        return _generate_modal_form(model, model_snake, app_name, with_loading_indicator)
    elif form_type == "inline":
        return _generate_inline_form(model, model_snake, app_name)
    else:
        return _generate_page_form(model, model_snake, app_name, cancel_url, with_loading_indicator)


def _generate_page_form(model: str, model_snake: str, app_name: str, cancel_url: str | None, with_loading: bool) -> str:
    cancel = cancel_url or f"{{{{ url '{app_name}:{model_snake}_list' }}}}"
    
    lines = [
        '{% extends "base.html" %}',
        '',
        '{% block title %}',
        f'    {{{{ object.pk|yesno:"Edit,Create" }}}} {model}',
        '{% endblock %}',
        '',
        '{% block content %}',
        '<div class="container mx-auto px-4 py-8 max-w-2xl">',
        f'    <h1 class="text-2xl font-bold mb-6">',
        f'        {{{{ object.pk|yesno:"Edit,Create" }}}} {model}',
        f'    </h1>',
        '',
        f'    <form method="post"',
        f'          hx-post="{{{{ request.path }}}}"',
        f'          hx-target="this"',
        f'          hx-swap="outerHTML"',
        f'          class="space-y-4">',
        '        {% csrf_token %}',
        '',
        '        {% for field in form %}',
        '        <div class="form-control">',
        '            <label class="label" for="{{ field.id_for_label }}">',
        '                <span class="label-text">{{ field.label }}</span>',
        '                {% if field.field.required %}',
        '                <span class="text-error">*</span>',
        '                {% endif %}',
        '            </label>',
        '            {{ field }}',
        '            {% if field.errors %}',
        '            <label class="label">',
        '                <span class="label-text-alt text-error">{{ field.errors.0 }}</span>',
        '            </label>',
        '            {% endif %}',
        '            {% if field.help_text %}',
        '            <label class="label">',
        '                <span class="label-text-alt">{{ field.help_text }}</span>',
        '            </label>',
        '            {% endif %}',
        '        </div>',
        '        {% endfor %}',
        '',
        '        <div class="flex gap-4 pt-4">',
        f'            <button type="submit" class="btn btn-primary">',
    ]
    
    if with_loading:
        lines.extend([
            '                <span class="htmx-indicator loading loading-spinner loading-sm"></span>',
            '                Save',
        ])
    else:
        lines.append('                Save')
    
    lines.extend([
        '            </button>',
        f'            <a href="{cancel}" class="btn btn-ghost">Cancel</a>',
        '        </div>',
        '    </form>',
        '</div>',
        '{% endblock %}',
    ])
    
    return "\n".join(lines)


def _generate_modal_form(model: str, model_snake: str, app_name: str, with_loading: bool) -> str:
    lines = [
        '<!-- Modal Form - Loaded via HTMX -->',
        '<div class="modal modal-open">',
        '    <div class="modal-box">',
        f'        <h3 class="font-bold text-lg mb-4">',
        f'            {{{{ object.pk|yesno:"Edit,Create" }}}} {model}',
        f'        </h3>',
        '',
        '        <form method="post"',
        '              hx-post="{{ request.path }}"',
        '              hx-target="#modal-container"',
        '              hx-swap="innerHTML">',
        '            {% csrf_token %}',
        '',
        '            {% for field in form %}',
        '            <div class="form-control mb-4">',
        '                <label class="label" for="{{ field.id_for_label }}">',
        '                    <span class="label-text">{{ field.label }}</span>',
        '                </label>',
        '                {{ field }}',
        '                {% if field.errors %}',
        '                <label class="label">',
        '                    <span class="label-text-alt text-error">{{ field.errors.0 }}</span>',
        '                </label>',
        '                {% endif %}',
        '            </div>',
        '            {% endfor %}',
        '',
        '            <div class="modal-action">',
        '                <button type="submit" class="btn btn-primary">',
    ]
    
    if with_loading:
        lines.append('                    <span class="htmx-indicator loading loading-spinner loading-sm"></span>')
    
    lines.extend([
        '                    Save',
        '                </button>',
        '                <button type="button"',
        '                        class="btn"',
        '                        onclick="this.closest(\'.modal\').remove()">',
        '                    Cancel',
        '                </button>',
        '            </div>',
        '        </form>',
        '    </div>',
        '    <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>',
        '</div>',
    ])
    
    return "\n".join(lines)


def _generate_inline_form(model: str, model_snake: str, app_name: str) -> str:
    lines = [
        '<!-- Inline Edit Form -->',
        '<form hx-post="{{ request.path }}"',
        '      hx-target="this"',
        '      hx-swap="outerHTML"',
        '      class="flex items-center gap-2">',
        '    {% csrf_token %}',
        '    {{ form.as_p }}',
        '    <button type="submit" class="btn btn-sm btn-primary">Save</button>',
        '    <button type="button"',
        '            hx-get="{{ object.get_absolute_url }}"',
        '            hx-target="this"',
        '            hx-swap="outerHTML"',
        '            class="btn btn-sm btn-ghost">Cancel</button>',
        '</form>',
    ]
    
    return "\n".join(lines)


@mcp.tool()
def generate_htmx_detail_template(
    model: str,
    app_name: str = "app",
    fields: list[str] | None = None,
    with_edit_button: bool = True,
    with_delete_button: bool = True,
    with_back_button: bool = True,
    related_lists: list[dict] | None = None,
) -> str:
    """
    Generiert ein HTMX Detail Template.
    
    Args:
        model: Model Name
        app_name: Django App Name
        fields: Anzuzeigende Felder
        with_edit_button: Edit Button
        with_delete_button: Delete Button
        with_back_button: Back to List Button
        related_lists: Related Objects anzeigen:
            - relation: Name der Relation (z.B. "comments")
            - label: Anzeige-Label
            
    Returns:
        Template Code
    """
    model_snake = snake_case(model)
    
    lines = [
        '{% extends "base.html" %}',
        '',
        f'{{% block title %}}{{{{ {model_snake} }}}}{{% endblock %}}',
        '',
        '{% block content %}',
        '<div class="container mx-auto px-4 py-8">',
        '    <!-- Header -->',
        '    <div class="flex justify-between items-center mb-6">',
        f'        <h1 class="text-2xl font-bold">{{{{ {model_snake} }}}}</h1>',
        '        <div class="flex gap-2">',
    ]
    
    if with_back_button:
        lines.extend([
            f'            <a href="{{{{ url \'{app_name}:{model_snake}_list\' }}}}"',
            '               class="btn btn-ghost">',
            '                ← Back to List',
            '            </a>',
        ])
    
    if with_edit_button:
        lines.extend([
            f'            <a href="{{{{ url \'{app_name}:{model_snake}_update\' {model_snake}.pk }}}}"',
            '               class="btn btn-primary">',
            '                Edit',
            '            </a>',
        ])
    
    if with_delete_button:
        lines.extend([
            f'            <button hx-delete="{{{{ url \'{app_name}:{model_snake}_delete\' {model_snake}.pk }}}}"',
            '                    hx-confirm="Are you sure you want to delete this?"',
            f'                    hx-redirect="{{{{ url \'{app_name}:{model_snake}_list\' }}}}"',
            '                    class="btn btn-error">',
            '                Delete',
            '            </button>',
        ])
    
    lines.extend([
        '        </div>',
        '    </div>',
        '',
        '    <!-- Detail Card -->',
        '    <div class="card bg-base-100 shadow-xl">',
        '        <div class="card-body">',
        '            <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">',
    ])
    
    if fields:
        for field in fields:
            label = field.replace("_", " ").title()
            lines.extend([
                '                <div>',
                f'                    <dt class="text-sm font-medium text-gray-500">{label}</dt>',
                f'                    <dd class="mt-1">{{{{ {model_snake}.{field} }}}}</dd>',
                '                </div>',
            ])
    else:
        lines.extend([
            '                <!-- Add your fields here -->',
            '                {% comment %}',
            '                <div>',
            f'                    <dt class="text-sm font-medium text-gray-500">Field Label</dt>',
            f'                    <dd class="mt-1">{{{{ {model_snake}.field_name }}}}</dd>',
            '                </div>',
            '                {% endcomment %}',
        ])
    
    lines.extend([
        '            </dl>',
        '        </div>',
        '    </div>',
    ])
    
    # Related lists
    if related_lists:
        for rel in related_lists:
            relation = rel.get("relation")
            label = rel.get("label", relation.replace("_", " ").title())
            
            lines.extend([
                '',
                f'    <!-- Related: {label} -->',
                '    <div class="mt-8">',
                f'        <h2 class="text-xl font-bold mb-4">{label}</h2>',
                f'        <div id="{relation}-list"',
                f'             hx-get="{{{{ url \'{app_name}:{relation}_list\' }}}}?{model_snake}={{{{ {model_snake}.pk }}}}"',
                '             hx-trigger="load"',
                '             hx-swap="innerHTML">',
                '            <span class="loading loading-spinner"></span>',
                '        </div>',
                '    </div>',
            ])
    
    lines.extend([
        '</div>',
        '{% endblock %}',
    ])
    
    return "\n".join(lines)


@mcp.tool()
def generate_htmx_component(
    component_type: Literal[
        "toast",
        "confirmation_modal",
        "loading_indicator",
        "empty_state",
        "error_message",
        "success_message",
    ],
    **kwargs,
) -> str:
    """
    Generiert wiederverwendbare HTMX UI-Komponenten.
    
    Args:
        component_type: Art der Komponente
        **kwargs: Komponenten-spezifische Parameter
        
    Returns:
        Template Code für die Komponente
    """
    if component_type == "toast":
        return _generate_toast(**kwargs)
    elif component_type == "confirmation_modal":
        return _generate_confirmation_modal(**kwargs)
    elif component_type == "loading_indicator":
        return _generate_loading_indicator(**kwargs)
    elif component_type == "empty_state":
        return _generate_empty_state(**kwargs)
    elif component_type == "error_message":
        return _generate_error_message(**kwargs)
    elif component_type == "success_message":
        return _generate_success_message(**kwargs)
    
    return f"<!-- Unknown component type: {component_type} -->"


def _generate_toast(message: str = "{{ message }}", toast_type: str = "info") -> str:
    type_classes = {
        "info": "alert-info",
        "success": "alert-success",
        "warning": "alert-warning",
        "error": "alert-error",
    }
    cls = type_classes.get(toast_type, "alert-info")
    
    return f'''<!-- Toast Notification -->
<div class="toast toast-end"
     x-data="{{ show: true }}"
     x-show="show"
     x-init="setTimeout(() => show = false, 3000)">
    <div class="alert {cls}">
        <span>{message}</span>
    </div>
</div>'''


def _generate_confirmation_modal(title: str = "Confirm", message: str = "Are you sure?") -> str:
    return f'''<!-- Confirmation Modal -->
<div class="modal modal-open" id="confirm-modal">
    <div class="modal-box">
        <h3 class="font-bold text-lg">{title}</h3>
        <p class="py-4">{message}</p>
        <div class="modal-action">
            <button class="btn btn-error" id="confirm-yes">Yes, proceed</button>
            <button class="btn" onclick="document.getElementById('confirm-modal').remove()">
                Cancel
            </button>
        </div>
    </div>
    <div class="modal-backdrop" onclick="this.parentElement.remove()"></div>
</div>'''


def _generate_loading_indicator(size: str = "md") -> str:
    return f'''<!-- Loading Indicator -->
<div class="htmx-indicator flex items-center justify-center p-4">
    <span class="loading loading-spinner loading-{size}"></span>
</div>'''


def _generate_empty_state(message: str = "No items found", icon: str = "📭") -> str:
    return f'''<!-- Empty State -->
<div class="text-center py-12">
    <div class="text-4xl mb-4">{icon}</div>
    <p class="text-gray-500">{message}</p>
</div>'''


def _generate_error_message(message: str = "{{ error }}") -> str:
    return f'''<!-- Error Message -->
<div class="alert alert-error" role="alert">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <span>{message}</span>
</div>'''


def _generate_success_message(message: str = "{{ message }}") -> str:
    return f'''<!-- Success Message -->
<div class="alert alert-success" role="alert">
    <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <span>{message}</span>
</div>'''
