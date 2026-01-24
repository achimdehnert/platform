#!/usr/bin/env python3
"""
Beispiel: Django-HTMX MCP Server Tools direkt verwenden.

Dieses Skript zeigt, wie man die Tools ohne MCP Client nutzen kann.
"""

from django_htmx_mcp.tools.models import (
    generate_django_model,
    generate_choices_class,
    generate_model_manager,
)
from django_htmx_mcp.tools.views import (
    generate_cbv,
    generate_htmx_action_view,
    generate_htmx_search_view,
)
from django_htmx_mcp.tools.templates import (
    generate_htmx_list_template,
    generate_htmx_form_template,
    generate_htmx_component,
)
from django_htmx_mcp.tools.forms import (
    generate_model_form,
    generate_filter_form,
)
from django_htmx_mcp.tools.urls import generate_crud_urls
from django_htmx_mcp.tools.tests import generate_model_tests, generate_view_tests
from django_htmx_mcp.tools.scaffolding import scaffold_django_app


def main():
    """Demonstriert die Hauptfunktionen."""
    
    print("=" * 60)
    print("Django-HTMX MCP Server - Beispiel")
    print("=" * 60)
    
    # 1. Model generieren
    print("\n1. MODEL GENERIEREN")
    print("-" * 40)
    
    model_code = generate_django_model(
        model_name="Task",
        fields=[
            {"name": "title", "type": "CharField", "max_length": 200},
            {"name": "description", "type": "TextField", "blank": True},
            {"name": "status", "type": "CharField", "max_length": 20, 
             "choices": [("todo", "To Do"), ("in_progress", "In Progress"), ("done", "Done")],
             "default": "todo"},
            {"name": "priority", "type": "IntegerField", "default": 1},
            {"name": "due_date", "type": "DateField", "null": True, "blank": True},
            {"name": "assignee", "type": "ForeignKey", "to": "auth.User", 
             "on_delete": "SET_NULL", "null": True, "blank": True},
        ],
        app_name="tasks",
        with_timestamps=True,
        with_soft_delete=True,
        ordering=["-created_at"],
    )
    print(model_code[:500] + "...\n")
    
    # 2. Choices Klasse
    print("\n2. CHOICES KLASSE")
    print("-" * 40)
    
    choices_code = generate_choices_class(
        name="TaskPriority",
        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("URGENT", "Urgent")],
    )
    print(choices_code)
    
    # 3. View generieren
    print("\n3. VIEW GENERIEREN")
    print("-" * 40)
    
    view_code = generate_cbv(
        view_name="TaskListView",
        view_type="ListView",
        model="Task",
        app_name="tasks",
        htmx_enabled=True,
        paginate_by=20,
        ordering=["-created_at"],
    )
    print(view_code[:600] + "...\n")
    
    # 4. HTMX Templates
    print("\n4. HTMX LIST TEMPLATE")
    print("-" * 40)
    
    templates = generate_htmx_list_template(
        model="Task",
        app_name="tasks",
        columns=[
            {"field": "title", "label": "Title", "sortable": True},
            {"field": "status", "label": "Status"},
            {"field": "priority", "label": "Priority", "sortable": True},
            {"field": "due_date", "label": "Due Date", "sortable": True},
        ],
        with_search=True,
        with_pagination=True,
    )
    print(f"Page Template Path: {templates['page_template_path']}")
    print(f"Partial Template Path: {templates['partial_template_path']}")
    print("\nPage Template (Auszug):")
    print(templates['page_template'][:400] + "...\n")
    
    # 5. Form Template
    print("\n5. MODAL FORM TEMPLATE")
    print("-" * 40)
    
    form_template = generate_htmx_form_template(
        model="Task",
        app_name="tasks",
        form_type="modal",
    )
    print(form_template[:400] + "...\n")
    
    # 6. ModelForm
    print("\n6. MODEL FORM")
    print("-" * 40)
    
    form_code = generate_model_form(
        model="Task",
        fields=["title", "description", "status", "priority", "due_date", "assignee"],
        widgets={"description": "Textarea(attrs={'rows': 3})"},
    )
    print(form_code)
    
    # 7. Filter Form
    print("\n7. FILTER FORM")
    print("-" * 40)
    
    filter_code = generate_filter_form(
        model="Task",
        filter_fields=[
            {"field": "status", "lookup": "exact"},
            {"field": "priority", "lookup": "gte"},
            {"field": "title", "lookup": "icontains", "label": "Search"},
        ],
    )
    print(filter_code)
    
    # 8. URLs
    print("\n8. CRUD URLs")
    print("-" * 40)
    
    urls_code = generate_crud_urls(
        model="Task",
        app_name="tasks",
        with_htmx_namespace=True,
    )
    print(urls_code)
    
    # 9. Tests
    print("\n9. VIEW TESTS")
    print("-" * 40)
    
    test_code = generate_view_tests(
        model="Task",
        app_name="tasks",
        view_type="list",
        with_htmx=True,
    )
    print(test_code[:600] + "...\n")
    
    # 10. UI Komponente
    print("\n10. TOAST KOMPONENTE")
    print("-" * 40)
    
    toast = generate_htmx_component(
        component_type="toast",
        message="{{ message }}",
        toast_type="success",
    )
    print(toast)
    
    # 11. HTMX Search View
    print("\n11. HTMX SEARCH VIEW")
    print("-" * 40)
    
    search_view = generate_htmx_search_view(
        view_name="TaskSearchView",
        model="Task",
        search_fields=["title", "description"],
        app_name="tasks",
    )
    print(search_view)
    
    print("\n" + "=" * 60)
    print("Fertig! Alle Code-Snippets wurden generiert.")
    print("=" * 60)


def demo_full_scaffold():
    """Demonstriert das vollständige App-Scaffolding."""
    
    print("\n" + "=" * 60)
    print("VOLLSTÄNDIGES APP SCAFFOLDING")
    print("=" * 60)
    
    result = scaffold_django_app(
        app_name="tasks",
        models=[
            {
                "name": "Task",
                "fields": [
                    {"name": "title", "type": "CharField", "max_length": 200},
                    {"name": "description", "type": "TextField", "blank": True},
                    {"name": "completed", "type": "BooleanField", "default": False},
                ],
            },
            {
                "name": "Tag",
                "fields": [
                    {"name": "name", "type": "CharField", "max_length": 50, "unique": True},
                    {"name": "color", "type": "CharField", "max_length": 7, "default": "#3b82f6"},
                ],
            },
        ],
        with_admin=True,
        with_tests=True,
        template_style="htmx",
    )
    
    print(f"\nApp: {result['app_name']}")
    print(f"\nGenerierte Dateien:")
    for filepath in result["files"].keys():
        print(f"  - {filepath}")
    
    print(result["instructions"])


if __name__ == "__main__":
    main()
    
    # Uncomment für vollständiges Scaffolding-Demo:
    # demo_full_scaffold()
