"""
Code Delegation Tool - Delegiert einfache Django-Tasks an Worker-LLMs

Unterstützte Task-Typen:
- django_view: Erstellt eine Django View
- django_template: Erstellt ein Django Template
- django_url: Erstellt URL-Patterns
- django_form: Erstellt ein Django Form
- django_model: Erstellt ein Django Model
- htmx_component: Erstellt HTMX-Komponenten
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# Task-Type Templates für Pattern-basierte Generierung
TASK_TEMPLATES = {
    "django_view": '''from django.views.generic import {view_type}
from django.http import JsonResponse
{imports}

class {class_name}({view_type}):
    """{description}"""
    template_name = "{template_name}"
    {model_line}
    {context_object_name}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Add custom context
        return context
''',

    "django_template": '''{% extends "base.html" %}
{% load static %}

{% block title %}{title}{% endblock %}

{% block content %}
<div class="container mt-4">
    <h1>{title}</h1>
    
    {content_placeholder}
</div>
{% endblock %}
''',

    "django_url": '''from django.urls import path
from . import views

app_name = "{app_name}"

urlpatterns = [
    {url_patterns}
]
''',

    "django_form": '''from django import forms
{model_import}

class {class_name}(forms.{form_type}):
    """{description}"""
    
    {meta_class}
    
    {field_definitions}
    
    def clean(self):
        cleaned_data = super().clean()
        # TODO: Add custom validation
        return cleaned_data
''',

    "django_model": '''from django.db import models
from django.utils import timezone
{imports}

class {class_name}(models.Model):
    """{description}"""
    
    {field_definitions}
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "{table_name}"
        ordering = ["-created_at"]
        verbose_name = "{verbose_name}"
        verbose_name_plural = "{verbose_name_plural}"
    
    def __str__(self):
        return {str_return}
''',

    "htmx_component": '''<div id="{component_id}" 
     hx-get="{url}"
     hx-trigger="{trigger}"
     hx-swap="{swap}"
     hx-target="#{target_id}">
    {content}
</div>
''',
}


async def delegate_to_worker_llm(
    task_type: str,
    task_description: str,
    context: Dict[str, Any],
    model: str = "auto"
) -> Dict[str, Any]:
    """
    Delegiert Task an Worker-LLM.
    
    Args:
        task_type: Art des Tasks (django_view, django_template, etc.)
        task_description: Natürlichsprachliche Beschreibung
        context: Zusätzlicher Kontext (app_name, model_name, etc.)
        model: LLM-Modell (auto = beste Wahl basierend auf verfügbaren Keys)
    
    Returns:
        Dict mit generiertem Code und Metadaten
    """
    start_time = datetime.now()
    
    try:
        # Versuche zuerst Pattern-basierte Generierung
        if task_type in TASK_TEMPLATES and _can_use_template(task_type, context):
            code = _generate_from_template(task_type, context)
            return {
                "success": True,
                "code": code,
                "method": "template",
                "task_type": task_type,
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        # Fallback zu LLM
        code = await _generate_with_llm(task_type, task_description, context, model)
        
        return {
            "success": True,
            "code": code,
            "method": "llm",
            "model": model,
            "task_type": task_type,
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
        
    except Exception as e:
        logger.error(f"Code delegation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "task_type": task_type,
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


def _can_use_template(task_type: str, context: Dict[str, Any]) -> bool:
    """Prüft ob Template-basierte Generierung möglich ist."""
    required_fields = {
        "django_view": ["class_name", "view_type"],
        "django_template": ["title"],
        "django_url": ["app_name"],
        "django_form": ["class_name"],
        "django_model": ["class_name", "table_name"],
        "htmx_component": ["component_id", "url"],
    }
    
    required = required_fields.get(task_type, [])
    return all(field in context for field in required)


def _generate_from_template(task_type: str, context: Dict[str, Any]) -> str:
    """Generiert Code aus Template."""
    template = TASK_TEMPLATES[task_type]
    
    # Defaults setzen
    defaults = {
        "imports": "",
        "model_line": "",
        "context_object_name": "",
        "content_placeholder": "<!-- Content here -->",
        "url_patterns": 'path("", views.IndexView.as_view(), name="index"),',
        "model_import": "",
        "form_type": "Form",
        "meta_class": "",
        "field_definitions": "# TODO: Add fields",
        "str_return": 'f"#{self.pk}"',
        "verbose_name": context.get("class_name", "Item"),
        "verbose_name_plural": context.get("class_name", "Item") + "s",
        "trigger": "click",
        "swap": "innerHTML",
        "target_id": context.get("component_id", "content"),
        "content": "Loading...",
        "template_name": f"{context.get('app_name', 'app')}/template.html",
        "view_type": "TemplateView",
        "description": "Auto-generated",
    }
    
    # Context mit Defaults mergen
    full_context = {**defaults, **context}
    
    try:
        return template.format(**full_context)
    except KeyError as e:
        logger.warning(f"Missing template key: {e}")
        return template


def _get_template_key(task_type: str) -> str:
    """Mappt Task-Type auf PromptTemplate key."""
    mapping = {
        "django_view": "code_django_view",
        "django_template": "code_django_template",
        "django_url": "code_django_url",
        "django_form": "code_django_form",
        "django_model": "code_django_model",
        "htmx_component": "code_htmx_component",
    }
    return mapping.get(task_type, f"code_{task_type}")


async def _get_prompt_from_template(
    task_type: str,
    description: str,
    context: Dict[str, Any]
) -> tuple:
    """Holt Prompt aus PromptTemplate DB."""
    try:
        bfagent_path = os.environ.get('BFAGENT_PATH', '/home/dehnert/github/bfagent')
        if bfagent_path not in sys.path:
            sys.path.insert(0, bfagent_path)
        
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django
        django.setup()
        
        from apps.bfagent.models_main import PromptTemplate
        
        template_key = _get_template_key(task_type)
        template = await asyncio.to_thread(
            lambda: PromptTemplate.objects.filter(
                template_key=template_key,
                is_active=True
            ).first()
        )
        
        if template:
            # Merge defaults mit context
            full_context = {**template.variable_defaults, **context}
            full_context["description"] = description
            
            # Render template
            system_prompt = template.system_prompt
            user_prompt = template.user_prompt_template.format(**full_context)
            
            return system_prompt, user_prompt, template.id
        
        return None, None, None
        
    except Exception as e:
        logger.warning(f"Could not load template: {e}")
        return None, None, None


async def _generate_with_llm(
    task_type: str,
    task_description: str,
    context: Dict[str, Any],
    model: str
) -> str:
    """Generiert Code mit Worker-LLM."""
    
    # Versuche zuerst PromptTemplate aus DB
    system_prompt, user_prompt, template_id = await _get_prompt_from_template(
        task_type, task_description, context
    )
    
    if system_prompt and user_prompt:
        prompt = f"{system_prompt}\n\n{user_prompt}"
        logger.info(f"Using PromptTemplate ID: {template_id}")
    else:
        # Fallback zu hardcoded Prompt
        prompt = _build_code_prompt(task_type, task_description, context)
        logger.info("Using fallback hardcoded prompt")
    
    # Hole OrchestrationService
    try:
        bfagent_path = os.environ.get('BFAGENT_PATH', '/home/dehnert/github/bfagent')
        if bfagent_path not in sys.path:
            sys.path.insert(0, bfagent_path)
        
        # Load .env for API keys
        from dotenv import load_dotenv
        load_dotenv(os.path.join(bfagent_path, '.env'))
        
        from apps.bfagent.services.orchestration_service import WorkerLLMClient
        
        client = WorkerLLMClient(model_name=model, task=f"code_delegation:{task_type}")
        # Set context metadata for logging
        client._context_metadata = {
            'task_type': task_type,
            'app_name': context.get('app_name'),
            'model_name': context.get('model_name'),
            'description': task_description[:200] if task_description else None,
        }
        result = await client.generate(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3  # Niedrig für Code-Generierung
        )
        
        # Extrahiere Code aus Response
        code = _extract_code_from_response(result.get("content", ""))
        return code
        
    except ImportError as e:
        logger.warning(f"OrchestrationService not available: {e}, using mock")
        return _generate_mock_code(task_type, context)
    except Exception as e:
        import traceback
        logger.error(f"LLM generation failed: {e}\n{traceback.format_exc()}")
        return _generate_mock_code(task_type, context)


def _build_code_prompt(task_type: str, description: str, context: Dict[str, Any]) -> str:
    """Baut Prompt für Code-Generierung."""
    
    type_instructions = {
        "django_view": "Create a Django class-based view following Django best practices.",
        "django_template": "Create a Django template using Bootstrap 5 and HTMX.",
        "django_url": "Create Django URL patterns following RESTful conventions.",
        "django_form": "Create a Django form with proper validation.",
        "django_model": "Create a Django model with appropriate fields and Meta class.",
        "htmx_component": "Create an HTMX component for dynamic updates.",
    }
    
    instruction = type_instructions.get(task_type, "Generate the requested code.")
    
    context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
    
    return f"""You are an expert Django developer. {instruction}

Task: {description}

Context:
{context_str}

Requirements:
- Follow PEP 8 style guide
- Use type hints where appropriate
- Include docstrings
- Follow Django conventions

Return ONLY the code, no explanations. Use proper formatting."""


def _extract_code_from_response(response: str) -> str:
    """Extrahiert Code aus LLM-Response."""
    # Entferne Markdown Code-Blocks
    if "```python" in response:
        start = response.find("```python") + 9
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    
    return response.strip()


def _generate_mock_code(task_type: str, context: Dict[str, Any]) -> str:
    """Generiert Mock-Code wenn LLM nicht verfügbar."""
    if task_type in TASK_TEMPLATES:
        return _generate_from_template(task_type, context)
    
    return f"# TODO: Implement {task_type}\n# Context: {context}"


async def _route_to_sql_tool(description: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Routet SQL-Anfragen zu bfagent-db MCP Tool."""
    try:
        # Analysiere ob es SELECT, INSERT, UPDATE etc. ist
        desc_lower = description.lower()
        
        if any(kw in desc_lower for kw in ["select", "query", "find", "get", "list", "show"]):
            # Read-only Query -> route to db_execute_query
            return {
                "success": True,
                "routed": True,
                "target_tool": "mcp1_db_execute_query",
                "message": "Use mcp1_db_execute_query for SELECT queries",
                "suggested_call": {
                    "tool": "mcp1_db_execute_query",
                    "params": {
                        "sql": f"-- Generated from: {description}\nSELECT * FROM ... LIMIT 10"
                    }
                }
            }
        
        elif any(kw in desc_lower for kw in ["table", "structure", "schema", "columns"]):
            # Schema info -> route to db_describe_table
            return {
                "success": True,
                "routed": True,
                "target_tool": "mcp1_db_describe_table",
                "message": "Use mcp1_db_describe_table for schema information",
                "suggested_call": {
                    "tool": "mcp1_db_describe_table",
                    "params": {
                        "table_name": context.get("table_name", "your_table_name")
                    }
                }
            }
        
        elif any(kw in desc_lower for kw in ["model", "django", "orm"]):
            # Django models -> route to db_django_models
            return {
                "success": True,
                "routed": True,
                "target_tool": "mcp1_db_django_models",
                "message": "Use mcp1_db_django_models for Django model info",
                "suggested_call": {
                    "tool": "mcp1_db_django_models",
                    "params": {
                        "app_label": context.get("app_name", "")
                    }
                }
            }
        
        else:
            # General SQL -> route to postgres MCP
            return {
                "success": True,
                "routed": True,
                "target_tool": "mcp9_query",
                "message": "Use mcp9_query for direct SQL queries",
                "suggested_call": {
                    "tool": "mcp9_query",
                    "params": {
                        "sql": f"-- {description}"
                    }
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"SQL routing failed: {str(e)}"
        }


async def handle_code_delegation(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP Tool Handler für Code-Delegation.
    
    Args:
        params: Dict mit:
            - task_type: Art des Tasks
            - description: Beschreibung
            - context: Zusätzlicher Kontext
            - model: LLM-Modell (optional)
    """
    task_type = params.get("task_type", "django_view")
    description = params.get("description", "")
    context = params.get("context", {})
    model = params.get("model", "auto")
    
    if not description:
        return {
            "success": False,
            "error": "description is required",
        }
    
    # SQL Tasks werden geroutet, nicht generiert
    if task_type == "sql_query":
        return await _route_to_sql_tool(description, context)
    
    return await delegate_to_worker_llm(
        task_type=task_type,
        task_description=description,
        context=context,
        model=model
    )
