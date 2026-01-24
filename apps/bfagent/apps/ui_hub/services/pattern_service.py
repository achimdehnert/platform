"""HTMX pattern service."""

from typing import Dict, List

from apps.ui_hub.models import HTMXPattern


class HTMXPatternService:
    """Service for managing HTMX patterns."""

    INLINE_EDIT_PATTERN = {
        "view": '''def {{ entity }}_htmx_edit_view(request, pk):
    """HTMX inline edit for {{ entity }}."""
    {{ entity }} = get_object_or_404({{ entity|title }}, pk=pk)

    if request.method == 'POST':
        form = {{ entity|title }}Form(request.POST, instance={{ entity }})
        if form.is_valid():
            {{ entity }} = form.save()
            return render(request, '{{ app }}/{{ entity }}/partials/_row.html', {
                '{{ entity }}': {{ entity }},
            })
    else:
        form = {{ entity|title }}Form(instance={{ entity }})

    return render(request, '{{ app }}/{{ entity }}/partials/_edit_form.html', {
        'form': form,
        '{{ entity }}': {{ entity }},
    })''',
        "partial": """{% raw %}<tr id="{{ entity }}-{{ object.pk }}">
    <td>
        <span class="editable"
              hx-get="{% url 'htmx-{{ entity }}-edit' object.pk %}"
              hx-target="closest tr"
              hx-swap="outerHTML">
            {{ object.name }}
        </span>
    </td>
</tr>{% endraw %}""",
    }

    DELETE_ROW_PATTERN = {
        "view": '''def {{ entity }}_htmx_delete_view(request, pk):
    """HTMX delete for {{ entity }}."""
    {{ entity }} = get_object_or_404({{ entity|title }}, pk=pk)

    if request.method == 'DELETE':
        {{ entity }}.delete()
        return HttpResponse('')

    return HttpResponse(status=405)''',
        "partial": """{% raw %}<button hx-delete="{% url 'htmx-{{ entity }}-delete' object.pk %}"
        hx-target="closest tr"
        hx-swap="delete"
        hx-confirm="Are you sure you want to delete this {{ entity }}?"
        class="btn btn-sm btn-danger">
    Delete
</button>{% endraw %}""",
    }

    SEARCH_FILTER_PATTERN = {
        "view": '''def {{ entity }}_htmx_search_view(request):
    """HTMX search/filter for {{ entity }}."""
    query = request.GET.get('q', '')

    {{ entity_plural }} = {{ entity|title }}.objects.all()
    if query:
        {{ entity_plural }} = {{ entity_plural }}.filter(name__icontains=query)

    return render(request, '{{ app }}/{{ entity }}/partials/_search_results.html', {
        '{{ entity_plural }}': {{ entity_plural }},
        'query': query,
    })''',
        "partial": """{% raw %}<input type="search"
       name="q"
       placeholder="Search {{ entity_plural }}..."
       hx-get="{% url 'htmx-{{ entity }}-search' %}"
       hx-trigger="keyup changed delay:500ms"
       hx-target="#search-results"
       class="form-control">

<div id="search-results">
    {% include "{{ app }}/{{ entity }}/partials/_list.html" %}
</div>{% endraw %}""",
    }

    MODAL_FORM_PATTERN = {
        "view": '''def {{ entity }}_htmx_modal_view(request):
    """HTMX modal form for {{ entity }}."""
    if request.method == 'POST':
        form = {{ entity|title }}Form(request.POST)
        if form.is_valid():
            {{ entity }} = form.save()

            response = render(request, '{{ app }}/{{ entity }}/partials/_row.html', {
                '{{ entity }}': {{ entity }},
            })
            response['HX-Trigger'] = 'closeModal'
            return response
    else:
        form = {{ entity|title }}Form()

    return render(request, '{{ app }}/{{ entity }}/partials/_modal_form.html', {
        'form': form,
    })''',
        "partial": """{% raw %}<div class="modal" id="{{ entity }}-modal">
    <div class="modal-dialog">
        <div class="modal-content"
             hx-get="{% url 'htmx-{{ entity }}-modal' %}"
             hx-swap="innerHTML">
            <!-- Form will be loaded here -->
        </div>
    </div>
</div>{% endraw %}""",
    }

    PAGINATION_PATTERN = {
        "view": '''def {{ entity }}_htmx_pagination_view(request):
    """HTMX pagination for {{ entity }}."""
    page = request.GET.get('page', 1)

    {{ entity_plural }} = {{ entity|title }}.objects.all()
    paginator = Paginator({{ entity_plural }}, 25)
    page_obj = paginator.get_page(page)

    return render(request, '{{ app }}/{{ entity }}/partials/_page.html', {
        'page_obj': page_obj,
    })''',
        "partial": """{% raw %}<div id="{{ entity }}-list">
    {% for object in page_obj %}
        {% include "partials/_row.html" %}
    {% endfor %}
</div>

{% if page_obj.has_next %}
<button hx-get="{% url 'htmx-{{ entity }}-pagination' %}?page={{ page_obj.next_page_number }}"
        hx-target="#{{ entity }}-list"
        hx-swap="beforeend"
        class="btn btn-primary">
    Load More
</button>
{% endif %}{% endraw %}""",
    }

    def get_pattern(self, pattern_name: str, entity: str = "item", app: str = "myapp") -> Dict:
        """Get HTMX pattern template.

        Args:
            pattern_name: Pattern name (inline_edit, delete_row, etc.)
            entity: Entity name for template variables
            app: App name for template variables

        Returns:
            Dict with view and partial code
        """
        patterns = {
            "inline_edit": self.INLINE_EDIT_PATTERN,
            "delete_row": self.DELETE_ROW_PATTERN,
            "search_filter": self.SEARCH_FILTER_PATTERN,
            "modal_form": self.MODAL_FORM_PATTERN,
            "pagination": self.PAGINATION_PATTERN,
        }

        pattern = patterns.get(pattern_name, self.INLINE_EDIT_PATTERN)

        # Try to get from database first
        try:
            db_pattern = HTMXPattern.objects.get(pattern_type=pattern_name, is_active=True)
            return {
                "pattern_name": pattern_name,
                "view": db_pattern.view_template,
                "html": db_pattern.html_template,
                "partial": db_pattern.partial_template,
                "javascript": db_pattern.javascript,
                "description": db_pattern.description,
            }
        except HTMXPattern.DoesNotExist:
            pass

        return {
            "pattern_name": pattern_name,
            "view": pattern.get("view", ""),
            "partial": pattern.get("partial", ""),
            "entity": entity,
            "app": app,
        }

    def list_patterns(self) -> List[Dict]:
        """List all available HTMX patterns.

        Returns:
            List of pattern info dicts
        """
        patterns = []

        # Database patterns
        db_patterns = HTMXPattern.objects.filter(is_active=True)
        for pattern in db_patterns:
            patterns.append(
                {
                    "name": pattern.name,
                    "type": pattern.pattern_type,
                    "description": pattern.description,
                    "source": "database",
                }
            )

        # Built-in patterns
        builtin = [
            {
                "name": "inline_edit",
                "description": "Inline editing with row replacement",
                "source": "builtin",
            },
            {
                "name": "delete_row",
                "description": "Delete row with confirmation",
                "source": "builtin",
            },
            {
                "name": "search_filter",
                "description": "Live search/filter with debounce",
                "source": "builtin",
            },
            {
                "name": "modal_form",
                "description": "Modal form with HTMX",
                "source": "builtin",
            },
            {
                "name": "pagination",
                "description": "Load more pagination",
                "source": "builtin",
            },
        ]

        patterns.extend(builtin)

        return patterns
