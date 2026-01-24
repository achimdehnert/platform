"""
HTMX Pattern Tools.

Tools zum Generieren von HTMX Patterns:
- Click-to-Edit
- Modal Forms
- Infinite Scroll
- HTMX Validation
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pascal_case


# =============================================================================
# CLICK-TO-EDIT PATTERN
# =============================================================================

@mcp.tool()
def generate_click_to_edit(
    model: str,
    field: str,
    app_name: str = "app",
    field_type: Literal["text", "textarea", "select", "number"] = "text",
    select_choices: list[dict] | None = None,
    validation_url: str | None = None,
    on_save_trigger: str | None = None,
) -> dict:
    """
    Generiert Click-to-Edit Pattern für ein Model-Feld.
    
    Perfekt für PromptTemplate, Konfigurationen, etc.
    
    Args:
        model: Model Name (z.B. "PromptTemplate")
        field: Feld Name (z.B. "system_prompt")
        app_name: Django App Name
        field_type: Feldtyp (text, textarea, select, number)
        select_choices: Optionen für Select [{value: str, label: str}]
        validation_url: URL für Live-Validierung
        on_save_trigger: HTMX Trigger nach Speichern (z.B. "promptUpdated")
        
    Returns:
        Dict mit view_code, template_code, url_code
    """
    model_snake = snake_case(model)
    field_snake = snake_case(field)
    
    # === VIEW CODE ===
    view_code = f'''
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from .models import {model}


def {model_snake}_{field_snake}_display(request, pk):
    """Display mode für {field}."""
    obj = get_object_or_404({model}, pk=pk)
    return render(request, "{app_name}/partials/{model_snake}_{field_snake}_display.html", {{
        "obj": obj,
    }})


@require_http_methods(["GET", "POST"])
def {model_snake}_{field_snake}_edit(request, pk):
    """Edit mode für {field}."""
    obj = get_object_or_404({model}, pk=pk)
    
    if request.method == "POST":
        value = request.POST.get("{field_snake}", "")
        obj.{field_snake} = value
        obj.save(update_fields=["{field_snake}"])
        
        response = render(request, "{app_name}/partials/{model_snake}_{field_snake}_display.html", {{
            "obj": obj,
            "just_saved": True,
        }})
        {"response['HX-Trigger'] = '" + on_save_trigger + "'" if on_save_trigger else ""}
        return response
    
    return render(request, "{app_name}/partials/{model_snake}_{field_snake}_edit.html", {{
        "obj": obj,
    }})
'''

    # === DISPLAY TEMPLATE ===
    display_template = f'''<!-- {model_snake}_{field_snake}_display.html -->
<div id="{model_snake}-{field_snake}-{{{{ obj.pk }}}}"
     class="click-to-edit-display {{% if just_saved %}}just-saved{{% endif %}}"
     hx-get="{{% url '{app_name}:{model_snake}_{field_snake}_edit' obj.pk %}}"
     hx-trigger="click"
     hx-swap="outerHTML"
     title="Click to edit">
    '''
    
    if field_type == "textarea":
        display_template += f'''
    <div class="editable-content">
        {{{{ obj.{field_snake}|default:"Click to add {field}..."|linebreaks }}}}
    </div>
    <small class="text-muted"><i class="bi bi-pencil"></i> Click to edit</small>
'''
    else:
        display_template += f'''
    <span class="editable-value">{{{{ obj.{field_snake}|default:"Click to add..." }}}}</span>
    <i class="bi bi-pencil text-muted ms-2"></i>
'''
    
    display_template += '</div>'

    # === EDIT TEMPLATE ===
    edit_template = f'''<!-- {model_snake}_{field_snake}_edit.html -->
<form id="{model_snake}-{field_snake}-{{{{ obj.pk }}}}"
      hx-post="{{% url '{app_name}:{model_snake}_{field_snake}_edit' obj.pk %}}"
      hx-swap="outerHTML"
      class="click-to-edit-form">
    '''
    
    if field_type == "textarea":
        edit_template += f'''
    <textarea name="{field_snake}" 
              class="form-control" 
              rows="5"
              autofocus
              {"hx-post='" + validation_url + "' hx-trigger='keyup changed delay:500ms'" if validation_url else ""}>{{{{ obj.{field_snake} }}}}</textarea>
'''
    elif field_type == "select":
        edit_template += f'''
    <select name="{field_snake}" class="form-select" autofocus>
        {{% for choice in choices %}}
        <option value="{{{{ choice.value }}}}" {{% if choice.value == obj.{field_snake} %}}selected{{% endif %}}>
            {{{{ choice.label }}}}
        </option>
        {{% endfor %}}
    </select>
'''
    elif field_type == "number":
        edit_template += f'''
    <input type="number" 
           name="{field_snake}" 
           class="form-control" 
           value="{{{{ obj.{field_snake} }}}}"
           autofocus>
'''
    else:
        edit_template += f'''
    <input type="text" 
           name="{field_snake}" 
           class="form-control" 
           value="{{{{ obj.{field_snake} }}}}"
           autofocus
           {"hx-post='" + validation_url + "' hx-trigger='keyup changed delay:500ms'" if validation_url else ""}>
'''
    
    edit_template += f'''
    <div class="mt-2">
        <button type="submit" class="btn btn-sm btn-primary">
            <i class="bi bi-check"></i> Save
        </button>
        <button type="button" 
                class="btn btn-sm btn-outline-secondary"
                hx-get="{{% url '{app_name}:{model_snake}_{field_snake}_display' obj.pk %}}"
                hx-swap="outerHTML">
            <i class="bi bi-x"></i> Cancel
        </button>
    </div>
</form>
'''

    # === URL CODE ===
    url_code = f'''
from django.urls import path
from . import views

urlpatterns = [
    # Click-to-edit for {model}.{field}
    path("{model_snake}/<int:pk>/{field_snake}/", 
         views.{model_snake}_{field_snake}_display, 
         name="{model_snake}_{field_snake}_display"),
    path("{model_snake}/<int:pk>/{field_snake}/edit/", 
         views.{model_snake}_{field_snake}_edit, 
         name="{model_snake}_{field_snake}_edit"),
]
'''

    # === CSS ===
    css_code = '''
/* Click-to-Edit Styles */
.click-to-edit-display {
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s;
}

.click-to-edit-display:hover {
    background-color: var(--bs-light);
}

.click-to-edit-display.just-saved {
    animation: highlight-save 1s ease-out;
}

@keyframes highlight-save {
    0% { background-color: var(--bs-success-bg-subtle); }
    100% { background-color: transparent; }
}

.click-to-edit-form textarea,
.click-to-edit-form input {
    font-family: inherit;
}
'''

    return {
        "view_code": view_code.strip(),
        "display_template": display_template.strip(),
        "edit_template": edit_template.strip(),
        "url_code": url_code.strip(),
        "css_code": css_code.strip(),
        "usage": f"Add click-to-edit for {model}.{field}. Include both templates and add URLs.",
    }


# =============================================================================
# MODAL FORM PATTERN
# =============================================================================

@mcp.tool()
def generate_modal_form(
    model: str,
    app_name: str = "app",
    form_fields: list[str] | None = None,
    modal_size: Literal["sm", "md", "lg", "xl"] = "lg",
    on_success_action: Literal["close", "redirect", "refresh_list"] = "refresh_list",
    list_target_id: str = "item-list",
) -> dict:
    """
    Generiert Modal Form Pattern für CRUD-Operationen.
    
    Args:
        model: Model Name
        app_name: Django App Name
        form_fields: Felder im Formular (None = alle)
        modal_size: Bootstrap Modal Größe
        on_success_action: Was nach erfolgreichem Submit passiert
        list_target_id: ID des Listen-Elements für refresh_list
        
    Returns:
        Dict mit view_code, modal_template, trigger_button, url_code
    """
    model_snake = snake_case(model)
    model_pascal = pascal_case(model)
    
    # === VIEW CODE ===
    view_code = f'''
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import {model}
from .forms import {model}Form


def {model_snake}_modal_form(request, pk=None):
    """Modal form für Create/Edit."""
    if pk:
        obj = get_object_or_404({model}, pk=pk)
        form = {model}Form(request.POST or None, instance=obj)
        title = "Edit {model}"
    else:
        obj = None
        form = {model}Form(request.POST or None)
        title = "Create {model}"
    
    if request.method == "POST" and form.is_valid():
        instance = form.save()
        
        response = HttpResponse()
        response["HX-Trigger"] = "{model_snake}Changed"
        '''
    
    if on_success_action == "close":
        view_code += '''
        # Close modal
        response["HX-Trigger"] = "closeModal"
        '''
    elif on_success_action == "redirect":
        view_code += f'''
        # Redirect to detail
        response["HX-Redirect"] = reverse("{app_name}:{model_snake}_detail", args=[instance.pk])
        '''
    
    view_code += f'''
        return response
    
    return render(request, "{app_name}/partials/{model_snake}_modal_form.html", {{
        "form": form,
        "obj": obj,
        "title": title,
    }})
'''

    # === MODAL TEMPLATE ===
    modal_template = f'''<!-- {model_snake}_modal_form.html -->
<div class="modal-dialog modal-{modal_size}">
    <div class="modal-content">
        <div class="modal-header">
            <h5 class="modal-title">{{{{ title }}}}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <form hx-post="{{% if obj %}}{{% url '{app_name}:{model_snake}_modal_edit' obj.pk %}}{{% else %}}{{% url '{app_name}:{model_snake}_modal_create' %}}{{% endif %}}"
              hx-target="#{list_target_id}"
              hx-swap="innerHTML">
            <div class="modal-body">
                {{% csrf_token %}}
                {{% for field in form %}}
                <div class="mb-3">
                    <label class="form-label">{{{{ field.label }}}}</label>
                    {{{{ field }}}}
                    {{% if field.errors %}}
                    <div class="invalid-feedback d-block">{{{{ field.errors.0 }}}}</div>
                    {{% endif %}}
                </div>
                {{% endfor %}}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Cancel
                </button>
                <button type="submit" class="btn btn-primary">
                    <span class="htmx-indicator spinner-border spinner-border-sm me-1"></span>
                    {{% if obj %}}Update{{% else %}}Create{{% endif %}}
                </button>
            </div>
        </form>
    </div>
</div>
'''

    # === TRIGGER BUTTON ===
    trigger_button = f'''<!-- Trigger Button for Modal -->
<button type="button" 
        class="btn btn-primary"
        hx-get="{{% url '{app_name}:{model_snake}_modal_create' %}}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        data-bs-toggle="modal"
        data-bs-target="#htmx-modal">
    <i class="bi bi-plus"></i> Create {model}
</button>

<!-- Edit Button (in list row) -->
<button type="button"
        class="btn btn-sm btn-outline-primary"
        hx-get="{{% url '{app_name}:{model_snake}_modal_edit' obj.pk %}}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        data-bs-toggle="modal"
        data-bs-target="#htmx-modal">
    <i class="bi bi-pencil"></i>
</button>

<!-- Modal Container (einmal im Base Template) -->
<div class="modal fade" id="htmx-modal" tabindex="-1">
    <div id="modal-container">
        <!-- Modal content loaded via HTMX -->
    </div>
</div>
'''

    # === URL CODE ===
    url_code = f'''
urlpatterns = [
    # Modal CRUD for {model}
    path("{model_snake}/modal/create/", 
         views.{model_snake}_modal_form, 
         name="{model_snake}_modal_create"),
    path("{model_snake}/modal/<int:pk>/edit/", 
         views.{model_snake}_modal_form, 
         name="{model_snake}_modal_edit"),
]
'''

    return {
        "view_code": view_code.strip(),
        "modal_template": modal_template.strip(),
        "trigger_button": trigger_button.strip(),
        "url_code": url_code.strip(),
        "usage": f"Modal form pattern for {model}. Add modal container to base template.",
    }


# =============================================================================
# INFINITE SCROLL PATTERN
# =============================================================================

@mcp.tool()
def generate_infinite_scroll(
    model: str,
    app_name: str = "app",
    items_per_page: int = 20,
    sort_field: str = "-created_at",
    filter_fields: list[str] | None = None,
) -> dict:
    """
    Generiert Infinite Scroll Pattern für Listen.
    
    Args:
        model: Model Name
        app_name: Django App Name
        items_per_page: Items pro Seite/Load
        sort_field: Sortierfeld (mit - für DESC)
        filter_fields: Felder die gefiltert werden können
        
    Returns:
        Dict mit view_code, list_template, item_partial, url_code
    """
    model_snake = snake_case(model)
    model_plural = model_snake + "s"
    
    # === VIEW CODE ===
    view_code = f'''
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import {model}


def {model_snake}_infinite_list(request):
    """Liste mit Infinite Scroll."""
    page = int(request.GET.get("page", 1))
    
    queryset = {model}.objects.all().order_by("{sort_field}")
    '''
    
    if filter_fields:
        for field in filter_fields:
            view_code += f'''
    # Filter by {field}
    {field}_filter = request.GET.get("{field}")
    if {field}_filter:
        queryset = queryset.filter({field}={field}_filter)
    '''
    
    view_code += f'''
    paginator = Paginator(queryset, {items_per_page})
    page_obj = paginator.get_page(page)
    
    # Partial für HTMX Request
    if request.headers.get("HX-Request"):
        return render(request, "{app_name}/partials/{model_snake}_items.html", {{
            "page_obj": page_obj,
            "{model_plural}": page_obj.object_list,
        }})
    
    # Full page
    return render(request, "{app_name}/{model_snake}_list.html", {{
        "page_obj": page_obj,
        "{model_plural}": page_obj.object_list,
    }})
'''

    # === LIST TEMPLATE ===
    list_template = f'''<!-- {model_snake}_list.html -->
{{% extends "base.html" %}}

{{% block content %}}
<div class="container">
    <h1>{model} List</h1>
    
    <div id="{model_snake}-list">
        {{% include "{app_name}/partials/{model_snake}_items.html" %}}
    </div>
</div>
{{% endblock %}}
'''

    # === ITEMS PARTIAL ===
    item_partial = f'''<!-- {model_snake}_items.html -->
{{% for obj in {model_plural} %}}
<div class="card mb-3 {model_snake}-item">
    <div class="card-body">
        <h5 class="card-title">{{{{ obj.name|default:obj }}}}</h5>
        <!-- Add more fields as needed -->
    </div>
</div>
{{% endfor %}}

{{% if page_obj.has_next %}}
<!-- Infinite Scroll Trigger -->
<div hx-get="?page={{{{ page_obj.next_page_number }}}}"
     hx-trigger="revealed"
     hx-swap="afterend"
     hx-target="this"
     class="infinite-scroll-trigger">
    <div class="d-flex justify-content-center py-4">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
</div>
{{% endif %}}

{{% if not {model_plural} and page_obj.number == 1 %}}
<div class="text-center text-muted py-5">
    <i class="bi bi-inbox fs-1"></i>
    <p class="mt-2">No items found</p>
</div>
{{% endif %}}
'''

    # === URL CODE ===
    url_code = f'''
urlpatterns = [
    path("{model_plural}/", views.{model_snake}_infinite_list, name="{model_snake}_list"),
]
'''

    return {
        "view_code": view_code.strip(),
        "list_template": list_template.strip(),
        "item_partial": item_partial.strip(),
        "url_code": url_code.strip(),
        "usage": f"Infinite scroll for {model}. Items load as user scrolls down.",
    }


# =============================================================================
# HTMX VALIDATION TOOLS
# =============================================================================

@mcp.tool()
def validate_htmx_attributes(
    html_content: str,
) -> dict:
    """
    Validiert HTMX-Attribute in HTML Content.
    
    Prüft auf:
    - Ungültige hx-swap Werte
    - Ungültige hx-trigger Events
    - Fehlende hx-target bei bestimmten Patterns
    - Leere URLs in hx-get/post
    - Unbekannte hx-* Attribute
    
    Args:
        html_content: HTML Content zu validieren
        
    Returns:
        Dict mit issues, warnings, valid_count
    """
    import re
    
    issues = []
    warnings = []
    valid_count = 0
    
    # Valid hx-swap values
    valid_swaps = {
        "innerHTML", "outerHTML", "beforebegin", "afterbegin",
        "beforeend", "afterend", "delete", "none"
    }
    
    # Valid hx-trigger events
    valid_triggers = {
        "click", "change", "submit", "keyup", "keydown", "keypress",
        "load", "revealed", "intersect", "every", "mouseenter", "mouseleave",
        "focus", "blur", "input"
    }
    
    # Known hx-* attributes
    known_attrs = {
        "hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete",
        "hx-trigger", "hx-target", "hx-swap", "hx-select", "hx-select-oob",
        "hx-indicator", "hx-push-url", "hx-confirm", "hx-disable",
        "hx-disabled-elt", "hx-ext", "hx-headers", "hx-history",
        "hx-history-elt", "hx-include", "hx-params", "hx-preserve",
        "hx-prompt", "hx-replace-url", "hx-request", "hx-sync",
        "hx-validate", "hx-vals", "hx-boost", "hx-on", "hx-sse", "hx-ws"
    }
    
    # Check hx-swap values
    swap_pattern = r'hx-swap=["\']([^"\']+)["\']'
    for match in re.finditer(swap_pattern, html_content):
        swap_value = match.group(1).split()[0]  # Get first word
        if swap_value not in valid_swaps:
            issues.append({
                "type": "invalid_swap",
                "value": swap_value,
                "message": f"Invalid hx-swap value: '{swap_value}'. Valid: {', '.join(valid_swaps)}",
                "position": match.start(),
            })
        else:
            valid_count += 1
    
    # Check hx-trigger events
    trigger_pattern = r'hx-trigger=["\']([^"\']+)["\']'
    for match in re.finditer(trigger_pattern, html_content):
        trigger_value = match.group(1)
        # Extract event name (before modifiers)
        event = trigger_value.split()[0].split(",")[0]
        if event not in valid_triggers and not event.startswith("every"):
            warnings.append({
                "type": "unknown_trigger",
                "value": event,
                "message": f"Uncommon hx-trigger event: '{event}'. Check if intentional.",
                "position": match.start(),
            })
        else:
            valid_count += 1
    
    # Check for empty URLs
    url_pattern = r'hx-(get|post|put|patch|delete)=["\']["\']'
    for match in re.finditer(url_pattern, html_content):
        issues.append({
            "type": "empty_url",
            "value": match.group(0),
            "message": f"Empty URL in hx-{match.group(1)}",
            "position": match.start(),
        })
    
    # Check for unknown hx-* attributes
    attr_pattern = r'(hx-[a-z-]+)='
    for match in re.finditer(attr_pattern, html_content):
        attr = match.group(1)
        if attr not in known_attrs and not attr.startswith("hx-on:"):
            warnings.append({
                "type": "unknown_attribute",
                "value": attr,
                "message": f"Unknown HTMX attribute: '{attr}'",
                "position": match.start(),
            })
        else:
            valid_count += 1
    
    # Check for hx-post without hx-target (potential issue)
    if "hx-post" in html_content and "hx-target" not in html_content:
        warnings.append({
            "type": "missing_target",
            "value": "hx-post without hx-target",
            "message": "hx-post found without hx-target. Response will replace trigger element.",
            "position": 0,
        })
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "valid_count": valid_count,
        "summary": f"Found {len(issues)} errors, {len(warnings)} warnings, {valid_count} valid attributes",
    }


@mcp.tool()
def suggest_htmx_improvements(
    html_content: str,
) -> dict:
    """
    Schlägt HTMX-Verbesserungen für HTML Content vor.
    
    Args:
        html_content: HTML Content zu analysieren
        
    Returns:
        Dict mit suggestions
    """
    import re
    
    suggestions = []
    
    # Suggest loading indicators
    if "hx-post" in html_content or "hx-get" in html_content:
        if "hx-indicator" not in html_content and "htmx-indicator" not in html_content:
            suggestions.append({
                "type": "add_indicator",
                "message": "Consider adding loading indicators with hx-indicator or .htmx-indicator class",
                "example": '<span class="htmx-indicator spinner-border spinner-border-sm"></span>',
            })
    
    # Suggest hx-swap for forms
    form_pattern = r'<form[^>]*hx-post[^>]*>'
    for match in re.finditer(form_pattern, html_content):
        if "hx-swap" not in match.group(0):
            suggestions.append({
                "type": "add_swap",
                "message": "Form with hx-post could benefit from explicit hx-swap",
                "example": 'hx-swap="outerHTML" or hx-swap="innerHTML"',
            })
    
    # Suggest debounce for search inputs
    if 'hx-trigger="keyup"' in html_content or "hx-trigger='keyup'" in html_content:
        if "delay:" not in html_content:
            suggestions.append({
                "type": "add_debounce",
                "message": "Consider adding debounce to keyup triggers",
                "example": 'hx-trigger="keyup changed delay:300ms"',
            })
    
    # Suggest hx-push-url for navigation
    if "hx-get" in html_content and "hx-push-url" not in html_content:
        suggestions.append({
            "type": "consider_push_url",
            "message": "Consider hx-push-url for navigation links to update browser history",
            "example": 'hx-push-url="true"',
        })
    
    # Suggest hx-confirm for delete actions
    delete_pattern = r'hx-delete|delete|remove|destroy'
    if re.search(delete_pattern, html_content, re.IGNORECASE):
        if "hx-confirm" not in html_content:
            suggestions.append({
                "type": "add_confirm",
                "message": "Consider adding hx-confirm for delete actions",
                "example": 'hx-confirm="Are you sure you want to delete this?"',
            })
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
    }
