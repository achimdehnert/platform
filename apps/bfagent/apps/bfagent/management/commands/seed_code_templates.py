"""
Seed PromptTemplates für Code-Delegation

Erstellt Templates für:
- django_view
- django_template
- django_url
- django_form
- django_model
- htmx_component
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models_main import PromptTemplate


CODE_TEMPLATES = [
    {
        "name": "Django View Generator",
        "template_key": "code_django_view",
        "category": "analysis",  # Closest match
        "system_prompt": """You are an expert Django developer specializing in class-based views.
Follow these rules:
- Use Django 5.x best practices
- Prefer class-based views (CBV) over function-based views
- Use type hints
- Include proper docstrings
- Follow PEP 8 style guide
- Use Bootstrap 5 compatible template names""",
        "user_prompt_template": """Create a Django view with the following requirements:

**Description:** {description}
**Class Name:** {class_name}
**App Name:** {app_name}
**View Type:** {view_type}
**Model:** {model_name}

Additional context:
{extra_context}

Return ONLY the Python code, no explanations.""",
        "required_variables": ["description", "class_name"],
        "optional_variables": ["app_name", "view_type", "model_name", "extra_context"],
        "variable_defaults": {
            "app_name": "app",
            "view_type": "TemplateView",
            "model_name": "",
            "extra_context": ""
        },
        "output_format": "text",
    },
    {
        "name": "Django Template Generator",
        "template_key": "code_django_template",
        "category": "analysis",
        "system_prompt": """You are an expert Django template developer.
Follow these rules:
- Use Django template language
- Extend from base.html
- Use Bootstrap 5 classes
- Include HTMX attributes where appropriate
- Use {% load static %} when needed
- Follow accessibility best practices""",
        "user_prompt_template": """Create a Django template with the following requirements:

**Title:** {title}
**Description:** {description}
**Template Type:** {template_type}

Context variables available:
{context_vars}

Return ONLY the HTML template code, no explanations.""",
        "required_variables": ["title", "description"],
        "optional_variables": ["template_type", "context_vars"],
        "variable_defaults": {
            "template_type": "page",
            "context_vars": "object, object_list"
        },
        "output_format": "text",
    },
    {
        "name": "Django URL Patterns Generator",
        "template_key": "code_django_url",
        "category": "analysis",
        "system_prompt": """You are an expert Django developer.
Follow these rules:
- Use path() not url()
- Use app_name for namespacing
- Follow RESTful conventions
- Use <int:pk> or <uuid:pk> for primary keys
- Include name parameter for all paths""",
        "user_prompt_template": """Create Django URL patterns for:

**App Name:** {app_name}
**Description:** {description}
**Views:** {view_names}

Return ONLY the Python code for urls.py, no explanations.""",
        "required_variables": ["app_name", "description"],
        "optional_variables": ["view_names"],
        "variable_defaults": {
            "view_names": "IndexView, DetailView, CreateView, UpdateView, DeleteView"
        },
        "output_format": "text",
    },
    {
        "name": "Django Form Generator",
        "template_key": "code_django_form",
        "category": "analysis",
        "system_prompt": """You are an expert Django form developer.
Follow these rules:
- Use ModelForm when a model is specified
- Add proper field widgets
- Include clean() methods for validation
- Use Bootstrap 5 compatible widgets
- Add helpful error messages""",
        "user_prompt_template": """Create a Django form with:

**Class Name:** {class_name}
**Description:** {description}
**Model:** {model_name}
**Fields:** {fields}

Return ONLY the Python code, no explanations.""",
        "required_variables": ["class_name", "description"],
        "optional_variables": ["model_name", "fields"],
        "variable_defaults": {
            "model_name": "",
            "fields": "__all__"
        },
        "output_format": "text",
    },
    {
        "name": "Django Model Generator",
        "template_key": "code_django_model",
        "category": "analysis",
        "system_prompt": """You are an expert Django model developer.
Follow these rules:
- Use appropriate field types
- Add created_at and updated_at fields
- Include Meta class with ordering
- Add __str__ method
- Use verbose_name and help_text
- Add indexes for frequently queried fields""",
        "user_prompt_template": """Create a Django model with:

**Class Name:** {class_name}
**Table Name:** {table_name}
**Description:** {description}
**Fields:** {fields}

Return ONLY the Python code, no explanations.""",
        "required_variables": ["class_name", "description"],
        "optional_variables": ["table_name", "fields"],
        "variable_defaults": {
            "table_name": "",
            "fields": "name, description, is_active"
        },
        "output_format": "text",
    },
    {
        "name": "HTMX Component Generator",
        "template_key": "code_htmx_component",
        "category": "analysis",
        "system_prompt": """You are an expert HTMX developer.
Follow these rules:
- Use hx-get, hx-post appropriately
- Include hx-target and hx-swap
- Add hx-indicator for loading states
- Use hx-trigger with appropriate events
- Include fallback for non-JS users""",
        "user_prompt_template": """Create an HTMX component:

**Component ID:** {component_id}
**Description:** {description}
**URL:** {url}
**Trigger:** {trigger}
**Swap Mode:** {swap}

Return ONLY the HTML code, no explanations.""",
        "required_variables": ["component_id", "description", "url"],
        "optional_variables": ["trigger", "swap"],
        "variable_defaults": {
            "trigger": "click",
            "swap": "innerHTML"
        },
        "output_format": "text",
    },
]


class Command(BaseCommand):
    help = "Seed PromptTemplates for Code Delegation"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        
        for template_data in CODE_TEMPLATES:
            template, was_created = PromptTemplate.objects.update_or_create(
                template_key=template_data["template_key"],
                defaults={
                    "name": template_data["name"],
                    "category": template_data["category"],
                    "system_prompt": template_data["system_prompt"],
                    "user_prompt_template": template_data["user_prompt_template"],
                    "required_variables": template_data["required_variables"],
                    "optional_variables": template_data["optional_variables"],
                    "variable_defaults": template_data["variable_defaults"],
                    "output_format": template_data["output_format"],
                    "is_active": True,
                }
            )
            
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {template.name}"))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f"🔄 Updated: {template.name}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"\n📊 Summary: {created} created, {updated} updated"
        ))
