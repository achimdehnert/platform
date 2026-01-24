"""
Form Generation Tools.

Tools zum Generieren von Django Forms.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case


@mcp.tool()
def generate_model_form(
    model: str,
    form_name: str | None = None,
    fields: list[str] | Literal["__all__"] = "__all__",
    exclude: list[str] | None = None,
    widgets: dict | None = None,
    labels: dict | None = None,
    help_texts: dict | None = None,
    with_crispy: bool = False,
    layout: Literal["vertical", "horizontal", "inline"] | None = None,
) -> str:
    """
    Generiert ein Django ModelForm.
    
    Args:
        model: Model Name
        form_name: Name der Form-Klasse (default: {Model}Form)
        fields: Felder oder "__all__"
        exclude: Auszuschließende Felder
        widgets: Custom Widgets {field: "WidgetClass"}
        labels: Custom Labels {field: "Label"}
        help_texts: Custom Help Texts {field: "Text"}
        with_crispy: django-crispy-forms Layout
        layout: Layout-Typ für crispy
        
    Returns:
        Python Code für die Form
    """
    logger.info(f"Generating ModelForm for {model}")
    
    if not form_name:
        form_name = f"{model}Form"
    
    imports = [
        "from django import forms",
        f"from .models import {model}",
    ]
    
    if with_crispy:
        imports.extend([
            "from crispy_forms.helper import FormHelper",
            "from crispy_forms.layout import Layout, Submit, Row, Column, Field",
        ])
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    lines.append(f"class {form_name}(forms.ModelForm):")
    lines.append(f'    """Form for {model} model."""')
    lines.append("")
    lines.append("    class Meta:")
    lines.append(f"        model = {model}")
    
    if fields == "__all__":
        lines.append('        fields = "__all__"')
    else:
        lines.append(f"        fields = {fields}")
    
    if exclude:
        lines.append(f"        exclude = {exclude}")
    
    if widgets:
        lines.append("        widgets = {")
        for field, widget in widgets.items():
            if "(" in widget:
                lines.append(f'            "{field}": forms.{widget},')
            else:
                lines.append(f'            "{field}": forms.{widget}(),')
        lines.append("        }")
    
    if labels:
        lines.append("        labels = {")
        for field, label in labels.items():
            lines.append(f'            "{field}": "{label}",')
        lines.append("        }")
    
    if help_texts:
        lines.append("        help_texts = {")
        for field, text in help_texts.items():
            lines.append(f'            "{field}": "{text}",')
        lines.append("        }")
    
    if with_crispy:
        lines.append("")
        lines.append("    def __init__(self, *args, **kwargs):")
        lines.append("        super().__init__(*args, **kwargs)")
        lines.append("        self.helper = FormHelper()")
        lines.append("        self.helper.form_method = 'post'")
        
        if layout == "horizontal":
            lines.append("        self.helper.form_horizontal = True")
            lines.append("        self.helper.label_class = 'col-lg-2'")
            lines.append("        self.helper.field_class = 'col-lg-8'")
        elif layout == "inline":
            lines.append("        self.helper.form_class = 'form-inline'")
        
        lines.append("        self.helper.add_input(Submit('submit', 'Save'))")
    
    return "\n".join(lines)


@mcp.tool()
def generate_filter_form(
    model: str,
    filter_fields: list[dict],
    form_name: str | None = None,
    app_name: str = "app",
) -> str:
    """
    Generiert ein django-filter FilterSet.
    
    Args:
        model: Model Name
        filter_fields: Filter-Definitionen:
            - field: Model Field Name
            - lookup: Filter Lookup (exact, icontains, gte, lte, range, etc.)
            - label: Custom Label (optional)
            - choices: Für ChoiceFilter
        form_name: Name der FilterSet-Klasse
        app_name: Django App Name
        
    Returns:
        Python Code für FilterSet
        
    Example:
        generate_filter_form(
            model="Task",
            filter_fields=[
                {"field": "status", "lookup": "exact"},
                {"field": "title", "lookup": "icontains", "label": "Search"},
                {"field": "created_at", "lookup": "range"},
                {"field": "priority", "lookup": "gte"},
            ]
        )
    """
    logger.info(f"Generating FilterSet for {model}")
    
    model_snake = snake_case(model)
    if not form_name:
        form_name = f"{model}Filter"
    
    imports = [
        "import django_filters",
        f"from .models import {model}",
    ]
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    lines.append(f"class {form_name}(django_filters.FilterSet):")
    lines.append(f'    """FilterSet for {model} model."""')
    lines.append("")
    
    # Generate filter fields
    for fdef in filter_fields:
        field = fdef["field"]
        lookup = fdef.get("lookup", "exact")
        label = fdef.get("label")
        choices = fdef.get("choices")
        
        filter_type = _get_filter_type(lookup, choices)
        
        args = []
        args.append(f'field_name="{field}"')
        args.append(f'lookup_expr="{lookup}"')
        
        if label:
            args.append(f'label="{label}"')
        
        if choices:
            choices_str = ", ".join(f'("{v}", "{l}")' for v, l in choices)
            args.append(f"choices=[{choices_str}]")
        
        args_str = ", ".join(args)
        lines.append(f"    {field} = django_filters.{filter_type}({args_str})")
    
    lines.append("")
    lines.append("    class Meta:")
    lines.append(f"        model = {model}")
    field_names = [f['field'] for f in filter_fields]
    lines.append(f"        fields = {field_names}")
    
    # Add template hint
    lines.extend([
        "",
        "",
        f"# Usage in view:",
        f"# from .filters import {form_name}",
        f"#",
        f"# class {model}ListView(FilterView):",
        f"#     model = {model}",
        f"#     filterset_class = {form_name}",
        f"#     template_name = '{app_name}/{model_snake}_list.html'",
    ])
    
    return "\n".join(lines)


def _get_filter_type(lookup: str, choices: list | None) -> str:
    """Bestimmt den django-filter Filter-Typ."""
    if choices:
        return "ChoiceFilter"
    
    lookup_map = {
        "exact": "CharFilter",
        "iexact": "CharFilter",
        "contains": "CharFilter",
        "icontains": "CharFilter",
        "in": "BaseInFilter",
        "gt": "NumberFilter",
        "gte": "NumberFilter",
        "lt": "NumberFilter",
        "lte": "NumberFilter",
        "range": "RangeFilter",
        "date": "DateFilter",
        "date__range": "DateFromToRangeFilter",
        "year": "NumberFilter",
        "isnull": "BooleanFilter",
    }
    
    return lookup_map.get(lookup, "CharFilter")


@mcp.tool()
def generate_search_form(
    search_fields: list[str],
    form_name: str = "SearchForm",
    placeholder: str = "Search...",
    with_htmx: bool = True,
    target_id: str = "search-results",
    search_url: str | None = None,
) -> str:
    """
    Generiert ein einfaches Search Form mit HTMX.
    
    Args:
        search_fields: Felder die durchsucht werden (für Docstring)
        form_name: Name der Form-Klasse
        placeholder: Placeholder Text
        with_htmx: HTMX Attribute im Template generieren
        target_id: HTMX Target ID
        search_url: URL für HTMX GET Request
        
    Returns:
        Python Code für Form + Template Snippet
    """
    # Form Code
    form_code = f'''from django import forms


class {form_name}(forms.Form):
    """
    Search form.
    
    Searches in: {", ".join(search_fields)}
    """
    
    q = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={{
            "placeholder": "{placeholder}",
            "class": "input input-bordered w-full",
            "autocomplete": "off",
        }})
    )
'''
    
    # Template snippet
    if with_htmx:
        template_code = f'''
<!-- Search Form Template -->
<form class="mb-4">
    <input type="text"
           name="q"
           placeholder="{placeholder}"
           class="input input-bordered w-full max-w-xs"
           hx-get="{search_url or '{{ search_url }}'}"
           hx-trigger="keyup changed delay:300ms, search"
           hx-target="#{target_id}"
           hx-swap="innerHTML"
           hx-indicator=".search-indicator">
    <span class="search-indicator htmx-indicator loading loading-spinner loading-sm ml-2"></span>
</form>
'''
    else:
        template_code = f'''
<!-- Search Form Template -->
<form method="get" class="mb-4">
    <input type="text"
           name="q"
           placeholder="{placeholder}"
           value="{{{{ request.GET.q }}}}"
           class="input input-bordered w-full max-w-xs">
    <button type="submit" class="btn btn-primary">Search</button>
</form>
'''
    
    return f"{form_code}\n\n# Template:\n'''{template_code}'''"


@mcp.tool()
def generate_bulk_action_form(
    model: str,
    actions: list[dict],
    form_name: str | None = None,
) -> str:
    """
    Generiert ein Bulk Action Form für Listen.
    
    Args:
        model: Model Name
        actions: Liste von Actions:
            - value: Action Value
            - label: Display Label
            - confirm: Bestätigungstext (optional)
        form_name: Name der Form-Klasse
        
    Returns:
        Python Code für Form + Template Snippet
    """
    model_snake = snake_case(model)
    if not form_name:
        form_name = f"{model}BulkActionForm"
    
    # Generate choices
    choices_str = ", ".join(f'("{a["value"]}", "{a["label"]}")' for a in actions)
    
    form_code = f'''from django import forms


class {form_name}(forms.Form):
    """Bulk action form for {model} objects."""
    
    ACTION_CHOICES = [
        ("", "-- Select Action --"),
        {choices_str},
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={{
            "class": "select select-bordered",
        }})
    )
    
    ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
    )
'''
    
    # Template
    template_code = f'''
<!-- Bulk Action Form Template -->
<form id="bulk-action-form"
      hx-post="{{{{ url 'app:{model_snake}_bulk_action' }}}}"
      hx-target="#{model_snake}-list"
      hx-swap="innerHTML">
    {{% csrf_token %}}
    
    <div class="flex items-center gap-2 mb-4">
        <input type="checkbox" id="select-all" class="checkbox"
               onclick="toggleAll(this)">
        <label for="select-all">Select All</label>
        
        <select name="action" class="select select-bordered select-sm ml-4">
            <option value="">-- Select Action --</option>
'''
    
    for action in actions:
        confirm = action.get("confirm", "")
        data_confirm = f' data-confirm="{confirm}"' if confirm else ""
        template_code += f'            <option value="{action["value"]}"{data_confirm}>{action["label"]}</option>\n'
    
    template_code += f'''        </select>
        
        <button type="submit" class="btn btn-sm btn-primary">Apply</button>
    </div>
    
    <input type="hidden" name="ids" id="selected-ids">
</form>

<script>
function toggleAll(checkbox) {{
    document.querySelectorAll('.item-checkbox').forEach(cb => {{
        cb.checked = checkbox.checked;
    }});
    updateSelectedIds();
}}

function updateSelectedIds() {{
    const ids = Array.from(document.querySelectorAll('.item-checkbox:checked'))
        .map(cb => cb.value);
    document.getElementById('selected-ids').value = ids.join(',');
}}

document.querySelectorAll('.item-checkbox').forEach(cb => {{
    cb.addEventListener('change', updateSelectedIds);
}});
</script>
'''
    
    return f"{form_code}\n\n# Template:\n'''{template_code}'''"
