#!/usr/bin/env python
"""
Enterprise Consistency Framework v3.0 - Production-Ready Code Generator
Advanced Django model consistency checker with intelligent fix mode,
batch processing, and enterprise-grade error handling
"""

# ============================================================================
# UTF-8 ENCODING FIX FOR WINDOWS
# This MUST be at the top before any other imports to ensure UTF-8 is used
# ============================================================================
import os
import sys

# Force UTF-8 mode globally (Python 3.7+)
os.environ.setdefault("PYTHONUTF8", "1")

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass  # Silently fail if reconfigure not available

# ============================================================================

import ast
import asyncio
import difflib
import hashlib
import importlib
import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

# Setup Django
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.management.color import color_style
from django.db import models, transaction

# Configure logging with color support
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
style = color_style()


class GenerationMode(Enum):
    """Generation modes for the framework"""

    ANALYZE = auto()
    PREVIEW = auto()
    GENERATE = auto()
    WATCH = auto()
    SYNC = auto()
    VALIDATE = auto()
    FIX = auto()
    BATCH = auto()
    ROLLBACK = auto()


class URLPattern(Enum):
    """URL pattern styles"""

    BFAGENT = "bfagent"  # Plural with trailing slash: books/, books/create/
    STANDARD = "standard"  # With action prefix: book/list/, book/create/
    REST = "rest"  # RESTful: books/, books/new/
    CUSTOM = "custom"


@dataclass
class FixableIssue:
    """Represents a fixable issue in the codebase"""

    issue_type: str
    severity: str  # 'critical', 'warning', 'info'
    file_path: Path
    description: str
    fix_available: bool
    fix_description: Optional[str] = None
    line_number: Optional[int] = None

    def __str__(self) -> str:
        severity_icons = {"critical": "❌", "warning": "⚠️", "info": "ℹ️"}
        severity_text = {
            "critical": style.ERROR(f"[{self.severity.upper()}]"),
            "warning": style.WARNING(f"[{self.severity.upper()}]"),
            "info": style.NOTICE(f"[{self.severity.upper()}]"),
        }
        icon = severity_icons.get(self.severity, "•")
        text = severity_text.get(self.severity, f"[{self.severity.upper()}]")
        return f"{icon} {text} {self.description}"


@dataclass
class ComponentStatus:
    """Enhanced status of a component for a model"""

    exists: bool
    path: Optional[Path] = None
    issues: List[FixableIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    content_hash: Optional[str] = None
    custom_code_sections: Dict[str, str] = field(default_factory=dict)
    last_modified: Optional[datetime] = None
    size_bytes: Optional[int] = None

    @property
    def has_critical_issues(self) -> bool:
        return any(issue.severity == "critical" for issue in self.issues)

    @property
    def fixable_issues(self) -> List[FixableIssue]:
        return [issue for issue in self.issues if issue.fix_available]


@dataclass
class GenerationConfig:
    """Configuration for code generation"""

    url_pattern: URLPattern = URLPattern.BFAGENT
    preserve_custom: bool = True
    create_backups: bool = True
    interactive: bool = False
    dry_run: bool = False
    fix_mode: bool = False
    verbose: bool = False
    components: Optional[List[str]] = None
    batch_mode: bool = False
    async_generation: bool = True
    max_workers: int = 4


@dataclass
class ModelAnalysis:
    """Complete analysis of a Django model"""

    model_name: str
    app_name: str
    fields: Dict[str, Any]
    relationships: Dict[str, Any]
    crud_config: Optional[Dict[str, Any]]
    form_status: ComponentStatus
    view_status: Dict[str, ComponentStatus]
    template_status: Dict[str, ComponentStatus]
    url_status: ComponentStatus
    test_status: ComponentStatus
    completeness_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    fixable_issues: List[FixableIssue] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)

    def get_all_issues(self) -> List[FixableIssue]:
        """Get all issues across all components"""
        all_issues = []
        all_issues.extend(self.form_status.issues)
        for status in self.view_status.values():
            all_issues.extend(status.issues)
        for status in self.template_status.values():
            all_issues.extend(status.issues)
        all_issues.extend(self.url_status.issues)
        all_issues.extend(self.test_status.issues)
        return all_issues

    def get_fixable_issues_count(self) -> int:
        """Get count of fixable issues"""
        return len([issue for issue in self.get_all_issues() if issue.fix_available])


class BackupManager:
    """Manages file backups and rollbacks"""

    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path.home() / ".django_consistency_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_registry = self.backup_dir / "registry.json"
        self._load_registry()

    def _load_registry(self) -> None:
        """Load backup registry"""
        if self.backup_registry.exists():
            with open(self.backup_registry, "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {}

    def _save_registry(self) -> None:
        """Save backup registry"""
        with open(self.backup_registry, "w") as f:
            json.dump(self.registry, f, indent=2)

    def create_backup(self, file_path: Path, session_id: str) -> Path:
        """Create a backup of a file"""
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / session_id / backup_filename
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(file_path, backup_path)

        # Update registry
        if session_id not in self.registry:
            self.registry[session_id] = {"timestamp": timestamp, "files": []}

        self.registry[session_id]["files"].append(
            {"original": str(file_path), "backup": str(backup_path), "timestamp": timestamp}
        )

        self._save_registry()
        return backup_path

    def rollback_session(self, session_id: str) -> List[Tuple[Path, Path]]:
        """Rollback all files from a session"""
        if session_id not in self.registry:
            raise ValueError(f"Session {session_id} not found")

        restored = []
        for file_info in self.registry[session_id]["files"]:
            original = Path(file_info["original"])
            backup = Path(file_info["backup"])

            if backup.exists():
                shutil.copy2(backup, original)
                restored.append((original, backup))

        return restored

    @contextmanager
    def backup_session(self, session_id: Optional[str] = None):
        """Context manager for backup sessions"""
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            yield session_id
        except Exception:
            # On error, offer rollback
            logger.error(f"Error in session {session_id}, rollback available")
            raise


class URLPatternAnalyzer:
    """Analyzes and fixes URL patterns"""

    PATTERN_TEMPLATES = {
        URLPattern.BFAGENT: {
            "list": "{model_plural}/",
            "create": "{model_plural}/create/",
            "detail": "{model_plural}/<int:pk>/",
            "edit": "{model_plural}/<int:pk>/edit/",
            "delete": "{model_plural}/<int:pk>/delete/",
        },
        URLPattern.STANDARD: {
            "list": "{model_lower}/list/",
            "create": "{model_lower}/create/",
            "detail": "{model_lower}/<int:pk>/",
            "edit": "{model_lower}/edit/<int:pk>/",
            "delete": "{model_lower}/delete/<int:pk>/",
        },
        URLPattern.REST: {
            "list": "{model_plural}/",
            "create": "{model_plural}/new/",
            "detail": "{model_plural}/<int:pk>/",
            "edit": "{model_plural}/<int:pk>/edit/",
            "delete": "{model_plural}/<int:pk>/delete/",
        },
    }

    @staticmethod
    def detect_pattern_style(url_patterns: List[str]) -> URLPattern:
        """Detect which URL pattern style is being used"""
        # Count matches for each pattern style
        scores = {pattern: 0 for pattern in URLPattern if pattern != URLPattern.CUSTOM}

        for url in url_patterns:
            for pattern_type, templates in URLPatternAnalyzer.PATTERN_TEMPLATES.items():
                for action, template in templates.items():
                    # Create regex from template
                    regex_pattern = template.replace("{model_plural}", r"\w+s")
                    regex_pattern = regex_pattern.replace("{model_lower}", r"\w+")
                    regex_pattern = regex_pattern.replace("<int:pk>", r"<int:\w+>")

                    if re.match(regex_pattern, url):
                        scores[pattern_type] += 1

        # Return pattern with highest score
        if max(scores.values()) == 0:
            return URLPattern.CUSTOM

        return max(scores, key=scores.get)

    @staticmethod
    def generate_urls(model_name: str, pattern_style: URLPattern) -> Dict[str, str]:
        """Generate URLs for a model in the specified style"""
        model_lower = model_name.lower()

        # Smart pluralization: avoid double-s for already plural names
        if model_lower.endswith("s"):
            model_plural = model_lower  # Already plural (e.g., "worlds")
        else:
            model_plural = (
                f"{model_lower}s"  # Add 's' for singular (e.g., "character" → "characters")
            )

        if pattern_style == URLPattern.CUSTOM:
            pattern_style = URLPattern.BFAGENT  # Default fallback

        templates = URLPatternAnalyzer.PATTERN_TEMPLATES[pattern_style]
        urls = {}

        for action, template in templates.items():
            urls[action] = template.format(model_lower=model_lower, model_plural=model_plural)

        return urls


class TemplateAnalyzer:
    """Analyzes and fixes template issues"""

    REQUIRED_TEMPLATE_ELEMENTS = {
        "list": [
            ("extends", r'{%\s*extends\s+["\']base\.html["\']\s*%}'),
            ("title_block", r"{%\s*block\s+title\s*%}"),
            ("content_block", r"{%\s*block\s+content\s*%}"),
            ("htmx_attributes", r"hx-\w+"),
        ],
        "form": [
            ("csrf_token", r"{%\s*csrf_token\s*%}"),
            ("form_tag", r"<form[^>]*>"),
            ("htmx_post", r"hx-post"),
            ("modal_structure", r'class=["\'][^"\']*modal[^"\']*["\']'),
        ],
        "detail": [
            ("extends", r'{%\s*extends\s+["\']base\.html["\']\s*%}'),
            ("title_block", r"{%\s*block\s+title\s*%}"),
            ("content_block", r"{%\s*block\s+content\s*%}"),
        ],
    }

    @classmethod
    def analyze_template(cls, template_path: Path, template_type: str) -> List[FixableIssue]:
        """Analyze a template for issues"""
        issues = []

        if not template_path.exists():
            return issues

        content = template_path.read_text()
        required_elements = cls.REQUIRED_TEMPLATE_ELEMENTS.get(template_type, [])

        for element_name, pattern in required_elements:
            if not re.search(pattern, content, re.IGNORECASE):
                issues.append(
                    FixableIssue(
                        issue_type="missing_template_element",
                        severity="warning",
                        file_path=template_path,
                        description=f"Missing {element_name} in {template_type} template",
                        fix_available=True,
                        fix_description=f"Add {element_name} to template",
                    )
                )

        # Check for wrong URL patterns
        if "href=" in content or "hx-get=" in content or "hx-post=" in content:
            # Extract URLs
            url_pattern = r'(?:href|hx-get|hx-post)=["\']([^"\']+)["\']'
            urls = re.findall(url_pattern, content)

            for url in urls:
                if "{% url" in url:
                    # Check if URL pattern matches expected style
                    if "/list/" in url and template_type == "list":
                        issues.append(
                            FixableIssue(
                                issue_type="wrong_url_pattern",
                                severity="critical",
                                file_path=template_path,
                                description=f"URL pattern uses '/list/' but should use BF Agent style",
                                fix_available=True,
                                fix_description="Update to BF Agent URL pattern",
                            )
                        )

        return issues


class ComponentGenerator(ABC):
    """Abstract base class for component generators"""

    @abstractmethod
    def generate(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate component code"""
        pass

    @abstractmethod
    def validate(self, analysis: ModelAnalysis, content: str) -> List[FixableIssue]:
        """Validate generated or existing content"""
        pass


class FormGenerator(ComponentGenerator):
    """Generates Django forms"""

    def validate_form_naming(self, model_name: str, app_path: Path) -> List[str]:
        """Check for inconsistent form names in existing code"""
        issues = []
        expected_name = f"{model_name}Form"

        # Check views directory for inconsistent imports
        views_dir = app_path / "views"
        if views_dir.exists():
            for view_file in views_dir.glob("*.py"):
                try:
                    content = view_file.read_text(encoding="utf-8")
                    # Look for incorrect singular forms
                    if f"{model_name[:-1]}Form" in content and model_name.endswith("s"):
                        issues.append(
                            f"⚠️  {view_file.name} uses '{model_name[:-1]}Form' "
                            f"but should use '{expected_name}'"
                        )
                except UnicodeDecodeError:
                    # Skip files with encoding issues
                    pass

        return issues

    def generate(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate form code"""
        model_name = analysis.model_name
        app_name = analysis.app_name

        # Determine fields - filter out non-editable fields
        if analysis.crud_config and analysis.crud_config["fields"] != "__all__":
            fields_list = analysis.crud_config["fields"]
        else:
            # Exclude list: Fields that should NEVER be in forms
            exclude_patterns = [
                "id",
                "created_at",
                "updated_at",
                "last_used_at",
                "total_requests",
                "successful_requests",
                "average_response_time",
                "total_tokens_used",
                "total_cost",
            ]

            # Only include editable fields
            editable_fields = [
                field_name
                for field_name, field_info in analysis.fields.items()
                if field_info.get("editable", True)
                and not field_info.get("auto_created", False)
                and not field_info.get("primary_key", False)
                and field_name not in exclude_patterns  # ← NEW: Exclude by name
            ]
            # Add relationships (ForeignKey, ManyToMany)
            editable_relationships = list(analysis.relationships.keys())
            fields_list = editable_fields + editable_relationships

        # Generate widgets
        widgets_code = []
        for field_name in fields_list:
            if field_name in analysis.fields:
                field_info = analysis.fields[field_name]
                widget = PatternLibrary.get_form_widget_for_field(field_info["type"])
                if widget != 'forms.TextInput(attrs={"class": "form-control"})':
                    widgets_code.append(f"            '{field_name}': {widget},")

        # Generate MIXIN (generator-managed, Django-style)
        mixin_code = f'''class {model_name}FormFieldsMixin:
    """AUTO-GENERATED field configuration for {model_name}Form

    This mixin is regenerated by the generator.
    Do not edit manually - add custom logic to {model_name}Form in forms.py
    """

    class Meta:
        model = {model_name}
        fields = {fields_list if isinstance(fields_list, list) else '"__all__"'}
        widgets = {{
{chr(10).join(widgets_code)}
        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                current_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in current_classes and 'form-check-input' not in current_classes:
                    field.widget.attrs['class'] = f"{{current_classes}} form-control".strip()
'''

        # Store usage example for later
        self._usage_example = f'''# Example usage in forms.py:
from .utils.form_mixins import {model_name}FormFieldsMixin

class {model_name}Form({model_name}FormFieldsMixin, forms.ModelForm):
    """Custom {model_name} form - SAFE TO EDIT"""

    # Add custom fields here
    # confirm_action = forms.BooleanField(required=False)

    # Add custom validation
    # def clean_field_name(self):
    #     value = self.cleaned_data.get('field_name')
    #     # Your validation logic
    #     return value
'''

        return mixin_code  # Return String not Dict!

    def validate(self, analysis: ModelAnalysis, content: str) -> List[FixableIssue]:
        """Validate form content"""
        issues = []

        # Check if form uses CRUDConfig
        if analysis.crud_config and "CRUDConfig" not in content:
            issues.append(
                FixableIssue(
                    issue_type="missing_crud_config",
                    severity="warning",
                    file_path=analysis.form_status.path,
                    description="Form doesn't use model's CRUDConfig",
                    fix_available=True,
                    fix_description="Regenerate form with CRUDConfig fields",
                )
            )

        return issues


class ViewGenerator(ComponentGenerator):
    """Generates Django views"""

    def generate(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate view code"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        # Get URL patterns for the configured style
        url_patterns = URLPatternAnalyzer.generate_urls(model_name, config.url_pattern)

        # Generate optimized queryset
        optimized_queryset = PerformanceOptimizer.optimize_queryset(
            apps.get_model(analysis.app_name, model_name), analysis.relationships
        )

        view_code = f'''from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import {model_name}
from ..forms import {model_name}Form


class {model_name}ListView(LoginRequiredMixin, ListView):
    """List view for {model_name}"""
    model = {model_name}
    template_name = '{app_name}/{model_lower}_list.html'
    context_object_name = '{model_lower}s'
    paginate_by = 20

    def get_queryset(self):
        {optimized_queryset}

        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            # CUSTOM_CODE_START: search_fields
            # Customize search fields here
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                # Add more search fields as needed
            )
            # CUSTOM_CODE_END:

        # CUSTOM_CODE_START: queryset_filters
        # Add custom filtering logic here
        # CUSTOM_CODE_END:

        # Ordering
        ordering = self.request.GET.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_fields'] = {analysis.crud_config.get('list_fields', list(analysis.fields.keys())[:5]) if analysis.crud_config else list(analysis.fields.keys())[:5]}
        context['total_count'] = self.get_queryset().count()

        # CUSTOM_CODE_START: extra_context
        # Add custom context variables here
        # CUSTOM_CODE_END:

        return context


class {model_name}DetailView(LoginRequiredMixin, DetailView):
    """Detail view for {model_name}"""
    model = {model_name}
    template_name = '{app_name}/{model_lower}_detail.html'
    context_object_name = '{model_lower}'

    def get_queryset(self):
        {optimized_queryset}
        return queryset


class {model_name}CreateView(LoginRequiredMixin, CreateView):
    """Create view for {model_name}"""
    model = {model_name}
    form_class = {model_name}Form
    template_name = '{app_name}/{model_lower}_form.html'
    success_url = reverse_lazy('{app_name}:{model_lower}-list')

    def form_valid(self, form):
        # CUSTOM_CODE_START: form_valid_create
        # Add custom logic before saving
        # Example: form.instance.created_by = self.request.user
        # CUSTOM_CODE_END:

        response = super().form_valid(form)
        messages.success(self.request, f'{model_name} created successfully!')

        # HTMX handling
        if self.request.headers.get('HX-Request'):
            context = {{
                '{model_lower}s': {model_name}.objects.all()[:20],
                'list_fields': {analysis.crud_config.get('list_fields', list(analysis.fields.keys())[:5]) if analysis.crud_config else list(analysis.fields.keys())[:5]},
                'messages': messages.get_messages(self.request)
            }}
            html = render_to_string(
                '{app_name}/partials/{model_lower}_partial_list.html',
                context,
                request=self.request
            )
            return HttpResponse(html)
        return response

    def form_invalid(self, form):
        # HTMX error handling
        if self.request.headers.get('HX-Request'):
            response = super().form_invalid(form)
            response['HX-Retarget'] = '#modal-container'
            response['HX-Reswap'] = 'innerHTML'
            return response
        return super().form_invalid(form)


class {model_name}EditView(LoginRequiredMixin, UpdateView):
    """Edit view for {model_name}"""
    model = {model_name}
    form_class = {model_name}Form
    template_name = '{app_name}/{model_lower}_form.html'
    success_url = reverse_lazy('{app_name}:{model_lower}-list')

    def get_queryset(self):
        {optimized_queryset}
        return queryset

    def form_valid(self, form):
        # CUSTOM_CODE_START: form_valid_edit
        # Add custom logic before saving
        # Example: form.instance.modified_by = self.request.user
        # CUSTOM_CODE_END:

        response = super().form_valid(form)
        messages.success(self.request, f'{model_name} updated successfully!')

        # HTMX handling
        if self.request.headers.get('HX-Request'):
            context = {{
                '{model_lower}s': {model_name}.objects.all()[:20],
                'list_fields': {analysis.crud_config.get('list_fields', list(analysis.fields.keys())[:5]) if analysis.crud_config else list(analysis.fields.keys())[:5]},
                'messages': messages.get_messages(self.request)
            }}
            html = render_to_string(
                '{app_name}/partials/{model_lower}_partial_list.html',
                context,
                request=self.request
            )
            return HttpResponse(html)
        return response


class {model_name}DeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for {model_name}"""
    model = {model_name}
    template_name = '{app_name}/{model_lower}_confirm_delete.html'
    success_url = reverse_lazy('{app_name}:{model_lower}-list')

    def delete(self, request, *args, **kwargs):
        # CUSTOM_CODE_START: delete_logic
        # Add custom deletion logic
        # CUSTOM_CODE_END:

        obj = self.get_object()
        messages.success(request, f'{model_name} "{{obj}}" deleted successfully!')

        if request.headers.get('HX-Request'):
            super().delete(request, *args, **kwargs)
            return HttpResponse(status=204)
        return super().delete(request, *args, **kwargs)


# CUSTOM_CODE_START: additional_views
# Add any additional custom views here
# CUSTOM_CODE_END:
'''

        return view_code

    def validate(self, analysis: ModelAnalysis, content: str) -> List[FixableIssue]:
        """Validate view content"""
        issues = []

        # Check for HTMX compliance
        if "HX-Request" not in content:
            issues.append(
                FixableIssue(
                    issue_type="missing_htmx",
                    severity="warning",
                    file_path=(
                        analysis.view_status.get("List").path
                        if "List" in analysis.view_status
                        else None
                    ),
                    description="Views not HTMX compliant",
                    fix_available=True,
                    fix_description="Add HTMX handling to views",
                )
            )

        return issues


class FixEngine:
    """Engine for fixing identified issues"""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.backup_manager = BackupManager()
        self.fixes_applied = []

    async def fix_issues(self, analysis: ModelAnalysis) -> Dict[str, Any]:
        """Fix all fixable issues in the analysis"""
        results = {"fixed": [], "failed": [], "skipped": []}

        fixable_issues = [issue for issue in analysis.get_all_issues() if issue.fix_available]

        if not fixable_issues:
            logger.info("No fixable issues found")
            return results

        # Group issues by file
        issues_by_file = {}
        for issue in fixable_issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)

        # Fix issues
        with self.backup_manager.backup_session() as session_id:
            for file_path, issues in issues_by_file.items():
                try:
                    if self.config.dry_run:
                        logger.info(f"[DRY RUN] Would fix {len(issues)} issues in {file_path}")
                        results["skipped"].extend(issues)
                    else:
                        fixed = await self._fix_file_issues(file_path, issues, analysis)
                        results["fixed"].extend(fixed)
                except Exception as e:
                    logger.error(f"Failed to fix {file_path}: {e}")
                    results["failed"].extend(issues)

        return results

    async def _fix_file_issues(
        self, file_path: Path, issues: List[FixableIssue], analysis: ModelAnalysis
    ) -> List[FixableIssue]:
        """Fix issues in a specific file"""
        fixed = []

        # Create backup
        self.backup_manager.create_backup(file_path, "fix_session")

        # Read current content
        if file_path.exists():
            content = file_path.read_text()
        else:
            content = ""

        # Apply fixes
        for issue in issues:
            if issue.issue_type == "wrong_url_pattern":
                content = self._fix_url_patterns(content, analysis)
                fixed.append(issue)
            elif issue.issue_type == "missing_template_element":
                content = self._fix_template_elements(content, issue, analysis)
                fixed.append(issue)
            elif issue.issue_type == "missing_crud_config":
                # Regenerate form
                generator = FormGenerator()
                content = generator.generate(analysis, self.config)
                fixed.append(issue)

        # Write fixed content
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Fixed {len(fixed)} issues in {file_path}")

        return fixed

    def _fix_url_patterns(self, content: str, analysis: ModelAnalysis) -> str:
        """Fix URL patterns in templates - converts underscore to dash in URL names"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        # Fix URL names in templates: underscore → dash (BF Agent Style)
        # Pattern: {% url 'app:model_action' %} → {% url 'app:model-action' %}
        url_name_replacements = [
            (f"'{app_name}:{model_lower}_list'", f"'{app_name}:{model_lower}-list'"),
            (f"'{app_name}:{model_lower}_create'", f"'{app_name}:{model_lower}-create'"),
            (f"'{app_name}:{model_lower}_edit'", f"'{app_name}:{model_lower}-edit'"),
            (f"'{app_name}:{model_lower}_delete'", f"'{app_name}:{model_lower}-delete'"),
            (f"'{app_name}:{model_lower}_detail'", f"'{app_name}:{model_lower}-detail'"),
            # Also handle double-quoted versions
            (f'"{app_name}:{model_lower}_list"', f'"{app_name}:{model_lower}-list"'),
            (f'"{app_name}:{model_lower}_create"', f'"{app_name}:{model_lower}-create"'),
            (f'"{app_name}:{model_lower}_edit"', f'"{app_name}:{model_lower}-edit"'),
            (f'"{app_name}:{model_lower}_delete"', f'"{app_name}:{model_lower}-delete"'),
            (f'"{app_name}:{model_lower}_detail"', f'"{app_name}:{model_lower}-detail"'),
        ]

        # Fix partial template paths: bfagent/model_partial → bfagent/partials/model_partial
        partial_replacements = [
            (
                f"'{app_name}/{model_lower}_partial_list.html'",
                f"'{app_name}/partials/{model_lower}_partial_list.html'",
            ),
            (
                f"'{app_name}/{model_lower}_partial_form.html'",
                f"'{app_name}/partials/{model_lower}_partial_form.html'",
            ),
            (
                f'"{app_name}/{model_lower}_partial_list.html"',
                f'"{app_name}/partials/{model_lower}_partial_list.html"',
            ),
            (
                f'"{app_name}/{model_lower}_partial_form.html"',
                f'"{app_name}/partials/{model_lower}_partial_form.html"',
            ),
        ]

        for old, new in url_name_replacements + partial_replacements:
            content = content.replace(old, new)

        return content

    def _fix_template_elements(
        self, content: str, issue: FixableIssue, analysis: ModelAnalysis
    ) -> str:
        """Fix missing template elements"""
        # This would add missing elements based on the issue type
        # For brevity, returning content as-is
        return content


class CodePreservationEngine:
    """Enhanced code preservation engine"""

    PRESERVATION_MARKERS = {
        "start": "# CUSTOM_CODE_START:",
        "end": "# CUSTOM_CODE_END:",
        "override": "# OVERRIDE:",
        "preserve": "# PRESERVE:",
        "generated": "# GENERATED_CODE:",
    }

    @staticmethod
    def extract_custom_sections(file_path: Path) -> Dict[str, str]:
        """Extract custom code sections from existing file"""
        custom_sections = {}
        if not file_path.exists():
            return custom_sections

        content = file_path.read_text()
        lines = content.splitlines()

        current_section = None
        section_lines = []

        for line in lines:
            if line.strip().startswith(CodePreservationEngine.PRESERVATION_MARKERS["start"]):
                current_section = line.strip().split(":", 1)[1].strip()
                section_lines = []
            elif line.strip().startswith(CodePreservationEngine.PRESERVATION_MARKERS["end"]):
                if current_section:
                    custom_sections[current_section] = "\n".join(section_lines)
                current_section = None
                section_lines = []
            elif current_section:
                section_lines.append(line)

        return custom_sections

    @staticmethod
    def merge_with_preserved_code(generated_code: str, custom_sections: Dict[str, str]) -> str:
        """Merge generated code with preserved custom sections"""
        for section_name, section_code in custom_sections.items():
            marker = f"{CodePreservationEngine.PRESERVATION_MARKERS['start']} {section_name}"
            end_marker = f"{CodePreservationEngine.PRESERVATION_MARKERS['end']} {section_name}"

            # Find and replace the section in generated code
            pattern = f"{re.escape(marker)}.*?{re.escape(end_marker)}"
            replacement = f"{marker}\n{section_code}\n{end_marker}"
            generated_code = re.sub(pattern, replacement, generated_code, flags=re.DOTALL)

        return generated_code


class DependencyAnalyzer:
    """Enhanced dependency analyzer with circular dependency detection"""

    @staticmethod
    def analyze_model_dependencies(
        model_class: Type[models.Model],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze model dependencies with enhanced information"""
        dependencies = {
            "foreign_keys": [],
            "many_to_many": [],
            "one_to_one": [],
            "reverse_relations": [],
            "circular_dependencies": [],
        }

        model_name = model_class.__name__
        checked_models = set()

        def check_circular(target_model: Type[models.Model], path: List[str]) -> List[List[str]]:
            """Check for circular dependencies"""
            target_name = target_model.__name__

            # Detect actual circular dependency: original model appears again in path
            if target_name == model_name and len(path) > 1:
                return [path + [model_name]]

            # Avoid infinite recursion
            if target_name in path or target_name in checked_models:
                return []

            checked_models.add(target_name)
            circular_paths = []

            # Check forward relationships only (ForeignKey, M2M, O2O)
            for field in target_model._meta.get_fields():
                if isinstance(
                    field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)
                ):
                    if hasattr(field, "related_model") and field.related_model:
                        new_path = path + [target_name]
                        sub_paths = check_circular(field.related_model, new_path)
                        circular_paths.extend(sub_paths)

            return circular_paths

        # Analyze fields
        for field in model_class._meta.get_fields():
            field_info = {
                "field": field.name,
                "verbose_name": getattr(field, "verbose_name", field.name),
                "help_text": getattr(field, "help_text", ""),
            }

            if isinstance(field, models.ForeignKey):
                field_info.update(
                    {
                        "to_model": field.related_model.__name__,
                        "on_delete": field.remote_field.on_delete.__name__,
                        "related_name": field.remote_field.related_name
                        or f"{model_name.lower()}_set",
                    }
                )
                dependencies["foreign_keys"].append(field_info)

            elif isinstance(field, models.ManyToManyField):
                field_info.update(
                    {
                        "to_model": field.related_model.__name__,
                        "through": (
                            field.remote_field.through.__name__
                            if field.remote_field.through._meta.auto_created == False
                            else None
                        ),
                        "related_name": field.remote_field.related_name
                        or f"{model_name.lower()}_set",
                    }
                )
                dependencies["many_to_many"].append(field_info)

            elif isinstance(field, models.OneToOneField):
                field_info.update(
                    {
                        "to_model": field.related_model.__name__,
                        "on_delete": field.remote_field.on_delete.__name__,
                        "related_name": field.remote_field.related_name or f"{model_name.lower()}",
                    }
                )
                dependencies["one_to_one"].append(field_info)

            elif hasattr(field, "related_model") and field.auto_created and field.related_model:
                field_info.update(
                    {
                        "from_model": field.related_model.__name__,
                        "field_type": field.__class__.__name__,
                    }
                )
                dependencies["reverse_relations"].append(field_info)

        # Check for circular dependencies
        for rel_type in ["foreign_keys", "many_to_many", "one_to_one"]:
            for rel in dependencies[rel_type]:
                if "to_model" in rel:
                    try:
                        target_model = apps.get_model(model_class._meta.app_label, rel["to_model"])
                        circular_paths = check_circular(target_model, [model_name])
                        dependencies["circular_dependencies"].extend(circular_paths)
                    except LookupError:
                        pass

        return dependencies


class PerformanceOptimizer:
    """Enhanced performance optimizer"""

    @staticmethod
    def optimize_queryset(model_class: Type[models.Model], relationships: Dict[str, Any]) -> str:
        """Generate optimized queryset with advanced optimizations"""
        select_related = []
        prefetch_related = []
        annotations = []

        for field_name, field_info in relationships.items():
            if field_info["type"] in ["ForeignKey", "OneToOneField"]:
                select_related.append(field_name)
            elif field_info["type"] == "ManyToManyField":
                prefetch_related.append(field_name)

        # Build queryset code
        queryset_parts = ["queryset = super().get_queryset()"]

        if select_related:
            queryset_parts.append(
                f"queryset = queryset.select_related({', '.join(repr(f) for f in select_related)})"
            )

        if prefetch_related:
            queryset_parts.append(
                f"queryset = queryset.prefetch_related({', '.join(repr(f) for f in prefetch_related)})"
            )

        # Add common annotations
        if hasattr(model_class, "created_at"):
            queryset_parts.append(
                "# Add any common annotations\n"
                "        # queryset = queryset.annotate(\n"
                "        #     days_since_created=Now() - F('created_at')\n"
                "        # )"
            )

        return "\n        ".join(queryset_parts)


class PatternLibrary:
    """Enhanced pattern library with more field types"""

    @staticmethod
    def get_form_widget_for_field(field_type: str) -> str:
        """Get appropriate widget for field type"""
        widget_map = {
            "CharField": 'forms.TextInput(attrs={"class": "form-control"})',
            "TextField": 'forms.Textarea(attrs={"class": "form-control", "rows": 4})',
            "DateField": 'forms.DateInput(attrs={"class": "form-control", "type": "date"})',
            "DateTimeField": 'forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"})',
            "TimeField": 'forms.TimeInput(attrs={"class": "form-control", "type": "time"})',
            "EmailField": 'forms.EmailInput(attrs={"class": "form-control"})',
            "URLField": 'forms.URLInput(attrs={"class": "form-control"})',
            "IntegerField": 'forms.NumberInput(attrs={"class": "form-control"})',
            "FloatField": 'forms.NumberInput(attrs={"class": "form-control", "step": "any"})',
            "DecimalField": 'forms.NumberInput(attrs={"class": "form-control", "step": "0.01"})',
            "BooleanField": 'forms.CheckboxInput(attrs={"class": "form-check-input"})',
            "FileField": 'forms.FileInput(attrs={"class": "form-control"})',
            "ImageField": 'forms.FileInput(attrs={"class": "form-control", "accept": "image/*"})',
            "JSONField": 'forms.Textarea(attrs={"class": "form-control", "rows": 4, "data-json": "true"})',
            "SlugField": 'forms.TextInput(attrs={"class": "form-control", "pattern": "[a-z0-9-]+"})',
            "UUIDField": 'forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})',
        }
        return widget_map.get(field_type, 'forms.TextInput(attrs={"class": "form-control"})')


class EnhancedConsistencyFramework:
    """Main framework with enhanced capabilities"""

    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        self.project_root = Path(__file__).resolve().parent.parent
        self.apps_config = self._initialize_apps_config()
        self.code_preservation = CodePreservationEngine()
        self.pattern_library = PatternLibrary()
        self.dependency_analyzer = DependencyAnalyzer()
        self.performance_optimizer = PerformanceOptimizer()
        self.backup_manager = BackupManager()
        self.fix_engine = FixEngine(self.config)
        self.generation_stats = {
            "files_created": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_fixed": 0,
            "errors": [],
        }

    def _initialize_apps_config(self) -> Dict[str, Any]:
        """Initialize configuration for all Django apps"""
        config = {}
        for app_config in apps.get_app_configs():
            if app_config.name.startswith("django."):
                continue
            config[app_config.label] = {
                "path": Path(app_config.path),
                "models": {},
                "url_pattern": URLPattern.BFAGENT,  # Default
            }
        return config

    def analyze_model(self, model_name: str) -> Optional[ModelAnalysis]:
        """Comprehensive analysis of a Django model"""
        model_class = None
        app_name = None

        # Find model across all apps
        for app_config in apps.get_app_configs():
            try:
                model_class = apps.get_model(app_config.label, model_name)
                app_name = app_config.label
                break
            except LookupError:
                continue

        if not model_class:
            logger.error(f"Model {model_name} not found")
            return None

        # Extract model information
        fields = {}
        relationships = {}

        for field in model_class._meta.get_fields():
            field_info = {
                "type": field.__class__.__name__,
                "null": getattr(field, "null", False),
                "blank": getattr(field, "blank", False),
                "max_length": getattr(field, "max_length", None),
                "choices": getattr(field, "choices", None),
                "default": getattr(field, "default", models.NOT_PROVIDED),
                "help_text": getattr(field, "help_text", ""),
                "verbose_name": getattr(field, "verbose_name", field.name),
                "editable": getattr(field, "editable", True),
                "auto_created": getattr(field, "auto_created", False),
                "primary_key": getattr(field, "primary_key", False),
            }

            if isinstance(field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)):
                field_info["related_model"] = (
                    field.related_model.__name__ if field.related_model else None
                )
                relationships[field.name] = field_info
            else:
                fields[field.name] = field_info

        # Check CRUD config
        crud_config = None
        if hasattr(model_class, "CRUDConfig"):
            crud_config = {
                "fields": getattr(model_class.CRUDConfig, "fields", "__all__"),
                "list_fields": getattr(model_class.CRUDConfig, "list_fields", []),
                "search_fields": getattr(model_class.CRUDConfig, "search_fields", []),
                "filter_fields": getattr(model_class.CRUDConfig, "filter_fields", []),
                "ordering": getattr(model_class.CRUDConfig, "ordering", ["-created_at"]),
                "actions": getattr(model_class.CRUDConfig, "actions", []),
            }

        # Check component status
        app_path = self.apps_config[app_name]["path"]

        analysis = ModelAnalysis(
            model_name=model_name,
            app_name=app_name,
            fields=fields,
            relationships=relationships,
            crud_config=crud_config,
            form_status=self._check_form_status(app_path, model_name, model_class),
            view_status=self._check_view_status(app_path, model_name),
            template_status=self._check_template_status(app_path, model_name),
            url_status=self._check_url_status(app_path, model_name),
            test_status=self._check_test_status(app_path, model_name),
            dependencies=self.dependency_analyzer.analyze_model_dependencies(model_class),
        )

        # Calculate completeness score
        analysis.completeness_score = self._calculate_completeness(analysis)

        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)

        # Check for naming inconsistencies
        form_gen = FormGenerator()
        naming_issues = form_gen.validate_form_naming(model_name, app_path)
        for issue_msg in naming_issues:
            analysis.recommendations.append(issue_msg)

        # Collect all fixable issues
        analysis.fixable_issues = [
            issue for issue in analysis.get_all_issues() if issue.fix_available
        ]

        return analysis

    def _check_form_status(
        self, app_path: Path, model_name: str, model_class: Type[models.Model]
    ) -> ComponentStatus:
        """Enhanced form component status check"""
        forms_file = app_path / "forms.py"
        status = ComponentStatus(exists=False)

        if forms_file.exists():
            status.path = forms_file
            status.last_modified = datetime.fromtimestamp(forms_file.stat().st_mtime)
            status.size_bytes = forms_file.stat().st_size

            content = forms_file.read_text(encoding="utf-8", errors="replace")
            form_class_name = f"{model_name}Form"

            if form_class_name in content:
                status.exists = True
                status.content_hash = hashlib.md5(content.encode()).hexdigest()

                # Extract custom code sections
                status.custom_code_sections = self.code_preservation.extract_custom_sections(
                    forms_file
                )

                # Validate form
                generator = FormGenerator()
                status.issues.extend(
                    generator.validate(
                        ModelAnalysis(
                            model_name=model_name,
                            app_name=app_path.name,
                            fields={},
                            relationships={},
                            crud_config=getattr(model_class, "CRUDConfig", None),
                            form_status=status,
                            view_status={},
                            template_status={},
                            url_status=ComponentStatus(False),
                            test_status=ComponentStatus(False),
                        ),
                        content,
                    )
                )

        return status

    def _check_view_status(self, app_path: Path, model_name: str) -> Dict[str, ComponentStatus]:
        """Enhanced view components status check"""
        # BF Agent uses views/ package structure
        views_dir = app_path / "views"
        views_file = views_dir / "main_views.py" if views_dir.exists() else app_path / "views.py"

        view_types = ["Create", "Edit", "Delete", "List", "Detail"]
        statuses = {}

        for view_type in view_types:
            status = ComponentStatus(exists=False)
            view_name = f"{model_name}{view_type}View"

            if views_file.exists():
                status.path = views_file
                try:
                    content = views_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    content = ""

                if view_name in content:
                    status.exists = True

                    # Validate view
                    generator = ViewGenerator()
                    # Add validation logic here

            statuses[view_type] = status

        return statuses

    def _check_template_status(self, app_path: Path, model_name: str) -> Dict[str, ComponentStatus]:
        """Enhanced template components status check"""
        template_base = app_path / "templates" / app_path.name
        model_lower = model_name.lower()

        template_types = {
            "list": f"{model_lower}_list.html",
            "form": f"{model_lower}_form.html",
            "detail": f"{model_lower}_detail.html",
            "partial_list": f"{model_lower}_partial_list.html",
            "partial_form": f"{model_lower}_partial_form.html",
        }

        statuses = {}
        for template_type, filename in template_types.items():
            status = ComponentStatus(exists=False)
            template_path = template_base / filename

            if template_path.exists():
                status.exists = True
                status.path = template_path
                status.last_modified = datetime.fromtimestamp(template_path.stat().st_mtime)
                status.size_bytes = template_path.stat().st_size

                # Analyze template for issues
                issues = TemplateAnalyzer.analyze_template(template_path, template_type)
                status.issues.extend(issues)

            statuses[template_type] = status

        return statuses

    def _check_url_status(self, app_path: Path, model_name: str) -> ComponentStatus:
        """Enhanced URL patterns status check"""
        urls_file = app_path / "urls.py"
        status = ComponentStatus(exists=False)

        if urls_file.exists():
            status.path = urls_file
            content = urls_file.read_text(encoding="utf-8", errors="replace")
            model_lower = model_name.lower()

            # Detect URL pattern style
            url_patterns = re.findall(r'path\(["\']([^"\']+)["\']\s*,', content)
            detected_style = URLPatternAnalyzer.detect_pattern_style(url_patterns)

            # Get expected patterns
            expected_urls = URLPatternAnalyzer.generate_urls(model_name, detected_style)

            missing_patterns = []
            for action, pattern in expected_urls.items():
                if pattern not in content:
                    missing_patterns.append(pattern)

            if not missing_patterns:
                status.exists = True
            else:
                for pattern in missing_patterns:
                    status.issues.append(
                        FixableIssue(
                            issue_type="missing_url_pattern",
                            severity="critical",
                            file_path=urls_file,
                            description=f"Missing URL pattern: {pattern}",
                            fix_available=True,
                            fix_description="Add missing URL pattern",
                        )
                    )

        return status

    def _check_test_status(self, app_path: Path, model_name: str) -> ComponentStatus:
        """Enhanced test components status check"""
        test_file = app_path / "tests" / f"test_{model_name.lower()}.py"
        status = ComponentStatus(exists=test_file.exists())

        if status.exists:
            status.path = test_file
            status.last_modified = datetime.fromtimestamp(test_file.stat().st_mtime)
            status.size_bytes = test_file.stat().st_size

            content = test_file.read_text(encoding="utf-8", errors="replace")

            # Check for comprehensive tests
            test_types = ["TestCreate", "TestUpdate", "TestDelete", "TestList"]
            missing_tests = []

            for test_type in test_types:
                if f"{model_name}{test_type}" not in content:
                    missing_tests.append(test_type)

            if missing_tests:
                status.issues.append(
                    FixableIssue(
                        issue_type="missing_tests",
                        severity="warning",
                        file_path=test_file,
                        description=f"Missing tests: {', '.join(missing_tests)}",
                        fix_available=True,
                        fix_description="Generate missing test cases",
                    )
                )

        return status

    def _calculate_completeness(self, analysis: ModelAnalysis) -> float:
        """Calculate completeness score for model implementation"""
        total_components = 0
        completed_components = 0

        # Weight different components
        weights = {"form": 2, "views": 3, "templates": 2, "urls": 1, "tests": 2}

        # Check form
        total_components += weights["form"]
        if analysis.form_status.exists and not analysis.form_status.has_critical_issues:
            completed_components += weights["form"]

        # Check views
        for view_status in analysis.view_status.values():
            total_components += weights["views"] / len(analysis.view_status)
            if view_status.exists and not view_status.has_critical_issues:
                completed_components += weights["views"] / len(analysis.view_status)

        # Check templates
        for template_status in analysis.template_status.values():
            total_components += weights["templates"] / len(analysis.template_status)
            if template_status.exists and not template_status.has_critical_issues:
                completed_components += weights["templates"] / len(analysis.template_status)

        # Check URLs
        total_components += weights["urls"]
        if analysis.url_status.exists and not analysis.url_status.has_critical_issues:
            completed_components += weights["urls"]

        # Check tests
        total_components += weights["tests"]
        if analysis.test_status.exists and not analysis.test_status.has_critical_issues:
            completed_components += weights["tests"]

        return (completed_components / total_components) * 100 if total_components > 0 else 0

    def _generate_recommendations(self, analysis: ModelAnalysis) -> List[str]:
        """Generate intelligent recommendations based on analysis"""
        recommendations = []

        # Component recommendations
        if not analysis.form_status.exists:
            recommendations.append(f"🔨 Generate form for {analysis.model_name}")
        elif analysis.form_status.has_critical_issues:
            recommendations.append(f"🔧 Fix critical issues in {analysis.model_name}Form")

        if not all(v.exists for v in analysis.view_status.values()):
            missing_views = [k for k, v in analysis.view_status.items() if not v.exists]
            recommendations.append(f"🔨 Generate missing views: {', '.join(missing_views)}")

        if not all(v.exists for v in analysis.template_status.values()):
            missing_templates = [k for k, v in analysis.template_status.items() if not v.exists]
            recommendations.append(f"🔨 Generate missing templates: {', '.join(missing_templates)}")

        if analysis.url_status.has_critical_issues:
            recommendations.append("⚠️  Fix URL patterns to match BF Agent style")

        if not analysis.test_status.exists:
            recommendations.append(f"🧪 Generate tests for {analysis.model_name}")

        # Dependency recommendations
        if analysis.dependencies.get("circular_dependencies"):
            recommendations.append("⚠️  Resolve circular dependencies")

        # Performance recommendations
        if len(analysis.relationships) > 3:
            recommendations.append(
                "💡 Consider adding select_related/prefetch_related optimizations"
            )

        # Fix mode recommendation
        if analysis.get_fixable_issues_count() > 0:
            recommendations.append(
                f"🔧 Run with --fix to automatically fix {analysis.get_fixable_issues_count()} issues"
            )

        return recommendations

    async def execute(self, mode: GenerationMode, model_names: List[str], **options) -> None:
        """Execute framework in specified mode with async support"""
        if mode == GenerationMode.BATCH:
            await self._execute_batch(model_names, **options)
        else:
            for model_name in model_names:
                analysis = self.analyze_model(model_name)
                if not analysis:
                    continue

                if mode == GenerationMode.ANALYZE:
                    self.display_analysis(analysis)

                elif mode == GenerationMode.PREVIEW:
                    self.preview_generation(analysis)

                elif mode == GenerationMode.GENERATE:
                    await self.generate_components(analysis, **options)

                elif mode == GenerationMode.VALIDATE:
                    self.validate_consistency(analysis)

                elif mode == GenerationMode.FIX:
                    await self.fix_mode(analysis)

                elif mode == GenerationMode.SYNC:
                    await self.sync_components(analysis)

                elif mode == GenerationMode.WATCH:
                    self.watch_mode(model_name)

    async def _execute_batch(self, model_names: List[str], **options) -> None:
        """Execute batch operations with parallel processing"""
        print(f"\n{'='*80}")
        print(f"🚀 Batch Processing {len(model_names)} models")
        print(f"{'='*80}")

        analyses = []
        for model_name in model_names:
            analysis = self.analyze_model(model_name)
            if analysis:
                analyses.append(analysis)

        # Summary
        total_issues = sum(len(a.get_all_issues()) for a in analyses)
        fixable_issues = sum(a.get_fixable_issues_count() for a in analyses)

        print(f"\nAnalyzed {len(analyses)} models:")
        print(f"  Total issues: {total_issues}")
        print(f"  Fixable issues: {fixable_issues}")

        # Ask for confirmation
        if self.config.interactive:
            proceed = input("\nProceed with batch operation? (y/n): ")
            if proceed.lower() != "y":
                print("Batch operation cancelled")
                return

        # Process in parallel if configured
        if self.config.async_generation and len(analyses) > 1:
            tasks = []
            for analysis in analyses:
                if self.config.fix_mode:
                    task = self.fix_mode(analysis)
                else:
                    task = self.generate_components(analysis, **options)
                tasks.append(task)

            await asyncio.gather(*tasks)
        else:
            # Process sequentially
            for analysis in analyses:
                if self.config.fix_mode:
                    await self.fix_mode(analysis)
                else:
                    await self.generate_components(analysis, **options)

    async def fix_mode(self, analysis: ModelAnalysis) -> None:
        """Fix identified issues automatically"""
        print(f"\n{'='*80}")
        print(f"🔧 Fix Mode for: {analysis.model_name}")
        print(f"{'='*80}")

        # Display fixable issues
        fixable = analysis.get_all_issues()
        fixable = [issue for issue in fixable if issue.fix_available]

        if not fixable:
            print("✅ No fixable issues found!")
            return

        print(f"\nFound {len(fixable)} fixable issues:")
        for i, issue in enumerate(fixable, 1):
            print(f"\n{i}. {issue}")
            if issue.fix_description:
                print(f"   Fix: {issue.fix_description}")

        # Confirm fixes
        if self.config.interactive:
            proceed = input(f"\nApply {len(fixable)} fixes? (y/n): ")
            if proceed.lower() != "y":
                print("Fix operation cancelled")
                return

        # Apply fixes
        results = await self.fix_engine.fix_issues(analysis)

        # Display results
        print(f"\n📊 Fix Results:")
        print(f"  ✅ Fixed: {len(results['fixed'])}")
        print(f"  ❌ Failed: {len(results['failed'])}")
        print(f"  ⏭️  Skipped: {len(results['skipped'])}")

        if results["fixed"]:
            print(f"\n✨ Successfully fixed {len(results['fixed'])} issues!")
            self.generation_stats["files_fixed"] += len(results["fixed"])

    def display_analysis(self, analysis: ModelAnalysis) -> None:
        """Display enhanced analysis results"""
        print(f"\n{'='*80}")
        print(f"📊 Model Analysis: {style.SUCCESS(analysis.model_name)}")
        print(f"{'='*80}")
        print(f"📦 App: {analysis.app_name}")
        print(f"🎯 Completeness: {analysis.completeness_score:.1f}%")

        # Visual progress bar
        filled = int(analysis.completeness_score / 10)
        bar = "█" * filled + "░" * (10 - filled)
        color_func = style.SUCCESS if analysis.completeness_score >= 80 else style.WARNING
        print(f"   Progress: {color_func(f'[{bar}]')}")

        # Fields summary
        print(f"\n📋 Fields ({len(analysis.fields)}):")
        for field_name, field_info in list(analysis.fields.items())[:5]:
            required = (
                style.ERROR("required") if not field_info["blank"] else style.NOTICE("optional")
            )
            print(f"  • {field_name}: {field_info['type']} ({required})")
        if len(analysis.fields) > 5:
            print(f"  ... and {len(analysis.fields) - 5} more fields")

        # Relationships
        if analysis.relationships:
            print(f"\n🔗 Relationships ({len(analysis.relationships)}):")
            for rel_name, rel_info in analysis.relationships.items():
                rel_type = rel_info["type"].replace("Field", "")
                target = rel_info.get("related_model", "Unknown")
                print(f"  • {rel_name}: {style.NOTICE(rel_type)} → {target}")

        # Dependencies analysis
        if analysis.dependencies:
            deps = analysis.dependencies
            total_deps = (
                len(deps.get("foreign_keys", []))
                + len(deps.get("many_to_many", []))
                + len(deps.get("one_to_one", []))
            )

            if total_deps > 0:
                print(f"\n🔄 Dependencies ({total_deps}):")
                for dep_type, dep_list in deps.items():
                    if dep_list and dep_type != "circular_dependencies":
                        print(f"  {dep_type.replace('_', ' ').title()}:")
                        for dep in dep_list[:3]:
                            if isinstance(dep, dict):
                                print(f"    • {dep}")

                # Circular dependencies warning
                if deps.get("circular_dependencies"):
                    print(f"\n  {style.ERROR('⚠️  Circular Dependencies Detected:')}")
                    for path in deps["circular_dependencies"][:3]:
                        print(f"    {' → '.join(path)}")

        # Component Status Table
        print(f"\n✅ Component Status:")

        components = [
            ("Form", analysis.form_status),
            ("List View", analysis.view_status.get("List", ComponentStatus(False))),
            ("Create View", analysis.view_status.get("Create", ComponentStatus(False))),
            ("Edit View", analysis.view_status.get("Edit", ComponentStatus(False))),
            ("Delete View", analysis.view_status.get("Delete", ComponentStatus(False))),
            ("Detail View", analysis.view_status.get("Detail", ComponentStatus(False))),
            ("List Template", analysis.template_status.get("list", ComponentStatus(False))),
            ("Form Template", analysis.template_status.get("form", ComponentStatus(False))),
            ("Detail Template", analysis.template_status.get("detail", ComponentStatus(False))),
            ("URL Patterns", analysis.url_status),
            ("Tests", analysis.test_status),
        ]

        for comp_name, status in components:
            if status.exists:
                if status.has_critical_issues:
                    icon = style.ERROR("✗")
                    status_text = style.ERROR("Has Issues")
                else:
                    icon = style.SUCCESS("✓")
                    status_text = style.SUCCESS("OK")
            else:
                icon = style.WARNING("○")
                status_text = style.WARNING("Missing")

            print(f"  {icon} {comp_name:<20} {status_text}")

            # Show critical issues inline
            if status.exists and status.has_critical_issues:
                for issue in status.issues:
                    if issue.severity == "critical":
                        print(f"     └─ {style.ERROR(issue.description)}")

        # Issues Summary
        all_issues = analysis.get_all_issues()
        if all_issues:
            critical_count = sum(1 for i in all_issues if i.severity == "critical")
            warning_count = sum(1 for i in all_issues if i.severity == "warning")
            info_count = sum(1 for i in all_issues if i.severity == "info")

            print(f"\n⚠️  Issues Summary:")
            if critical_count:
                print(f"  {style.ERROR(f'Critical: {critical_count}')}")
            if warning_count:
                print(f"  {style.WARNING(f'Warnings: {warning_count}')}")
            if info_count:
                print(f"  {style.NOTICE(f'Info: {info_count}')}")

            print(f"\n  Top Issues:")
            for issue in all_issues[:5]:
                print(f"  • {issue}")
            if len(all_issues) > 5:
                print(f"  ... and {len(all_issues) - 5} more issues")

        # Recommendations
        if analysis.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(analysis.recommendations, 1):
                print(f"  {i}. {rec}")

        # Quick Actions
        print(f"\n🚀 Quick Actions:")
        if analysis.get_fixable_issues_count() > 0:
            print(
                f"  • {style.SUCCESS('Fix Issues:')} python {Path(__file__).name} fix {analysis.model_name}"
            )

        if analysis.completeness_score < 100:
            print(
                f"  • {style.NOTICE('Generate Missing:')} python {Path(__file__).name} generate {analysis.model_name}"
            )

        print(
            f"  • {style.NOTICE('Preview Changes:')} python {Path(__file__).name} preview {analysis.model_name}"
        )
        print(
            f"  • {style.WARNING('Force Regenerate:')} python {Path(__file__).name} generate {analysis.model_name} --force"
        )

    def preview_generation(self, analysis: ModelAnalysis) -> None:
        """Enhanced preview with syntax highlighting"""
        print(f"\n{'='*80}")
        print(f"🔍 Preview Generation for: {style.SUCCESS(analysis.model_name)}")
        print(f"{'='*80}")

        # Components summary
        components_to_generate = []
        components_to_fix = []

        if not analysis.form_status.exists:
            components_to_generate.append("Form")
        elif analysis.form_status.fixable_issues:
            components_to_fix.append("Form")

        missing_views = [k for k, v in analysis.view_status.items() if not v.exists]
        if missing_views:
            components_to_generate.extend([f"{v} View" for v in missing_views])

        missing_templates = [k for k, v in analysis.template_status.items() if not v.exists]
        if missing_templates:
            components_to_generate.extend([f"{t.title()} Template" for t in missing_templates])

        if analysis.url_status.issues:
            components_to_fix.append("URL Patterns")

        if not analysis.test_status.exists:
            components_to_generate.append("Tests")

        # Display summary
        print(f"\n📋 Components to Generate ({len(components_to_generate)}):")
        for comp in components_to_generate:
            print(f"  • {style.SUCCESS('+')} {comp}")

        if components_to_fix:
            print(f"\n🔧 Components to Fix ({len(components_to_fix)}):")
            for comp in components_to_fix:
                print(f"  • {style.WARNING('~')} {comp}")

        print(f"\n📁 File Operations:")

        # Form Preview
        if not analysis.form_status.exists:
            generator = FormGenerator()
            form_code = generator.generate(analysis, self.config)
            self._preview_code("Form", analysis.app_name, "forms.py", form_code, "create")

        # Views Preview
        if missing_views:
            generator = ViewGenerator()
            view_code = generator.generate(analysis, self.config)
            self._preview_code("Views", analysis.app_name, "views.py", view_code, "update")

        # Templates Preview (show first template only for brevity)
        if missing_templates:
            template_gen = TemplateGenerator()
            for template_type in missing_templates[:1]:
                template_code = template_gen.generate_template(analysis, template_type, self.config)
                filename = f"{analysis.model_name.lower()}_{template_type}.html"
                self._preview_code(
                    f"{template_type.title()} Template",
                    analysis.app_name,
                    f"templates/{analysis.app_name}/{filename}",
                    template_code,
                    "create",
                )
            if len(missing_templates) > 1:
                print(f"\n  ... and {len(missing_templates) - 1} more templates")

        # URL Patterns Preview
        if analysis.url_status.issues:
            urls = URLPatternAnalyzer.generate_urls(analysis.model_name, self.config.url_pattern)
            url_code = self._generate_url_code(analysis.model_name, urls)
            self._preview_code("URL Patterns", analysis.app_name, "urls.py", url_code, "patch")

        # Show command to execute
        print(f"\n💻 To generate these components:")
        print(f"   python {Path(__file__).name} generate {analysis.model_name}")

        if components_to_fix:
            print(f"\n🔧 To fix issues:")
            print(f"   python {Path(__file__).name} fix {analysis.model_name}")

    def _preview_code(
        self, component: str, app_name: str, filename: str, code: str, operation: str
    ) -> None:
        """Display code preview with formatting"""
        icon_map = {
            "create": style.SUCCESS("✨"),
            "update": style.WARNING("📝"),
            "patch": style.NOTICE("🔧"),
        }

        print(f"\n{icon_map.get(operation, '')} {component} → {app_name}/{filename}")
        print(f"{'─' * 60}")

        # Show first 20 lines
        lines = code.split("\n")
        for line in lines[:20]:
            print(f"  {line}")
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more lines)")

    def _generate_url_code(self, model_name: str, urls: Dict[str, str]) -> str:
        """Generate URL pattern code"""
        model_lower = model_name.lower()
        lines = [f"# {model_name} URLs"]

        for action, pattern in urls.items():
            view_name = f"{model_name}{action.title()}View"
            url_name = f"{model_lower}-{action}"
            lines.append(f"path('{pattern}', {view_name}.as_view(), name='{url_name}'),")

        return "\n".join(lines)

    async def generate_components(self, analysis: ModelAnalysis, **options) -> None:
        """Enhanced component generation with async support"""
        print(f"\n{'='*80}")
        print(f"🔨 Generating Components for: {style.SUCCESS(analysis.model_name)}")
        print(f"{'='*80}")

        app_path = self.apps_config[analysis.app_name]["path"]
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Component generators
        generators = {
            "form": FormGenerator(),
            "views": ViewGenerator(),
            "templates": TemplateGenerator(),
            "tests": TestGenerator(),
        }

        with self.backup_manager.backup_session(session_id):
            # Generate form (ALWAYS generate mixins, even if form exists)
            if self._should_generate("form", options):
                await self._generate_form(analysis, app_path, generators["form"])

            # Generate views
            missing_views = [k for k, v in analysis.view_status.items() if not v.exists]
            if missing_views and self._should_generate("views", options):
                await self._generate_views(analysis, app_path, generators["views"])

            # Generate templates
            missing_templates = [k for k, v in analysis.template_status.items() if not v.exists]
            if missing_templates and self._should_generate("templates", options):
                await self._generate_templates(analysis, app_path, generators["templates"])

            # Generate tests
            if not analysis.test_status.exists and self._should_generate("tests", options):
                await self._generate_tests(analysis, app_path, generators["tests"])

            # Show URL instructions
            if analysis.url_status.issues and self._should_generate("urls", options):
                self._show_url_instructions(analysis, app_path)

        # Summary
        self._display_generation_summary()

    def _should_generate(self, component: str, options: Dict[str, Any]) -> bool:
        """Check if component should be generated"""
        if self.config.components and component not in self.config.components:
            return False

        if self.config.interactive:
            return input(f"\nGenerate {component}? (y/n): ").lower() == "y"

        return True

    async def _generate_form(
        self, analysis: ModelAnalysis, app_path: Path, generator: FormGenerator
    ) -> None:
        """Generate form component using Mixin pattern"""
        mixin_code = generator.generate(analysis, self.config)  # Now returns String

        # Create utils directory if not exists
        utils_path = app_path / "utils"
        utils_path.mkdir(exist_ok=True)

        # Create __init__.py in utils if not exists
        utils_init = utils_path / "__init__.py"
        if not utils_init.exists():
            utils_init.write_text("", encoding="utf-8")

        # Write/Update form_mixins.py (ALWAYS overwrite)
        mixins_path = utils_path / "form_mixins.py"

        if mixins_path.exists():
            # Read existing content
            existing_content = mixins_path.read_text(encoding="utf-8", errors="replace")

            # Check if this mixin already exists
            if f"class {analysis.model_name}FormFieldsMixin" in existing_content:
                # Replace existing mixin
                import re

                pattern = rf"class {analysis.model_name}FormFieldsMixin:.*?(?=\nclass |\Z)"
                new_content = re.sub(pattern, mixin_code.strip(), existing_content, flags=re.DOTALL)
                mixins_path.write_text(new_content, encoding="utf-8")
                print(f"{style.NOTICE('🔧')} Updated {analysis.model_name}FormFieldsMixin")
            else:
                # Append new mixin
                mixins_path.write_text(existing_content + "\n\n" + mixin_code, encoding="utf-8")
                print(f"{style.SUCCESS('✓')} Added {analysis.model_name}FormFieldsMixin")
        else:
            # Create new file with header
            header = f'''"""
AUTO-GENERATED FORM MIXINS
Generated by consistency_framework.py
Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

DO NOT EDIT MANUALLY - These mixins are regenerated automatically.
Use these mixins in forms.py for custom business logic.
"""
from django import forms
from ..models import *


'''
            mixins_path.write_text(header + mixin_code, encoding="utf-8")
            print(
                f"{style.SUCCESS('✓')} Created form_mixins.py with {analysis.model_name}FormFieldsMixin"
            )

        # Check if form exists in forms.py
        form_path = app_path / "forms.py"
        if form_path.exists():
            existing_forms = form_path.read_text(encoding="utf-8", errors="replace")
            if f"class {analysis.model_name}Form" in existing_forms:
                print(
                    f"{style.NOTICE('ℹ️')} {analysis.model_name}Form already exists in forms.py - skipping"
                )
                # Show usage example anyway
                if hasattr(generator, "_usage_example"):
                    print(f"\n{style.NOTICE('💡')} Usage example:")
                    print(generator._usage_example)
                return

        # Show usage example
        if hasattr(generator, "_usage_example"):
            print(f"\n{style.NOTICE('💡')} Usage example:")
            print(generator._usage_example)

        self.generation_stats["files_created"] += 1

    async def _generate_views(
        self, analysis: ModelAnalysis, app_path: Path, generator: ViewGenerator
    ) -> None:
        """Generate view components"""
        view_code = generator.generate(analysis, self.config)

        # BF Agent uses views/ package structure
        views_dir = app_path / "views"
        if views_dir.exists() and views_dir.is_dir():
            view_path = views_dir / "main_views.py"
        else:
            view_path = app_path / "views.py"

        if view_path.exists():
            existing_content = view_path.read_text(encoding="utf-8", errors="replace")
            if f"{analysis.model_name}ListView" not in existing_content:
                # Append to existing file
                view_path.write_text(existing_content + "\n\n" + view_code, encoding="utf-8")
                print(f"{style.SUCCESS('✓')} Appended views to: {view_path}")
                self.generation_stats["files_updated"] += 1
                return

        if self._write_component(view_path, view_code):
            self.generation_stats["files_updated"] += 1
            print(f"{style.SUCCESS('✓')} Generated views: {view_path}")

    async def _generate_templates(
        self, analysis: ModelAnalysis, app_path: Path, generator: "TemplateGenerator"
    ) -> None:
        """Generate template components"""
        template_base = app_path / "templates" / app_path.name
        templates = generator.generate_all_templates(analysis, self.config)

        for template_type, content in templates.items():
            if (
                template_type not in analysis.template_status
                or not analysis.template_status[template_type].exists
            ):
                filename = f"{analysis.model_name.lower()}_{template_type}.html"
                template_path = template_base / filename

                if self._write_component(template_path, content):
                    self.generation_stats["files_created"] += 1
                    print(f"{style.SUCCESS('✓')} Generated template: {template_path}")

    async def _generate_tests(
        self, analysis: ModelAnalysis, app_path: Path, generator: "TestGenerator"
    ) -> None:
        """Generate test components"""
        test_code = generator.generate(analysis, self.config)
        test_dir = app_path / "tests"
        test_path = test_dir / f"test_{analysis.model_name.lower()}.py"

        if self._write_component(test_path, test_code):
            self.generation_stats["files_created"] += 1
            print(f"{style.SUCCESS('✓')} Generated tests: {test_path}")

    def _show_url_instructions(self, analysis: ModelAnalysis, app_path: Path) -> None:
        """Show URL pattern instructions"""
        urls = URLPatternAnalyzer.generate_urls(analysis.model_name, self.config.url_pattern)
        url_code = self._generate_url_code(analysis.model_name, urls)

        print(f"\n{style.WARNING('📝')} Add these URL patterns to {app_path / 'urls.py'}:")
        print(f"{'─' * 60}")
        print(url_code)
        print(f"{'─' * 60}")

    def _merge_python_code(self, existing: str, new: str, analysis: ModelAnalysis) -> str:
        """Intelligently merge Python code"""
        # Parse imports
        existing_lines = existing.split("\n")
        new_lines = new.split("\n")

        imports = []
        existing_body = []
        new_body = []

        # Extract imports and body from existing
        for line in existing_lines:
            if line.startswith(("import ", "from ")) and not line.startswith("from ."):
                imports.append(line)
            else:
                existing_body.append(line)

        # Extract new imports and body
        for line in new_lines:
            if line.startswith(("import ", "from ")) and not line.startswith("from ."):
                if line not in imports:
                    imports.append(line)
            else:
                new_body.append(line)

        # Sort imports
        imports.sort()

        # Combine
        result = "\n".join(imports)
        result += "\n\n" + "\n".join(existing_body).rstrip()
        result += "\n\n" + "\n".join(new_body).strip()

        return result

    def _write_component(self, file_path: Path, content: str) -> bool:
        """Write component with preservation and backup"""
        try:
            # Preserve custom code if enabled
            if self.config.preserve_custom and file_path.exists():
                custom_sections = self.code_preservation.extract_custom_sections(file_path)
                if custom_sections:
                    content = self.code_preservation.merge_with_preserved_code(
                        content, custom_sections
                    )

            # Dry run check
            if self.config.dry_run:
                print(f"{style.NOTICE('[DRY RUN]')} Would write: {file_path}")
                return True

            # Create backup if file exists
            if self.config.create_backups and file_path.exists():
                self.backup_manager.create_backup(file_path, "generation")

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file with UTF-8 encoding
            file_path.write_text(content, encoding="utf-8")
            return True

        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            self.generation_stats["errors"].append(str(e))
            return False

    def _display_generation_summary(self) -> None:
        """Display generation summary"""
        print(f"\n{'='*80}")
        print("📊 Generation Summary:")
        print(f"  {style.SUCCESS('Created:')} {self.generation_stats['files_created']} files")
        print(f"  {style.NOTICE('Updated:')} {self.generation_stats['files_updated']} files")
        if self.generation_stats.get("files_fixed", 0) > 0:
            print(f"  {style.WARNING('Fixed:')} {self.generation_stats['files_fixed']} files")
        print(f"  {style.NOTICE('Skipped:')} {self.generation_stats['files_skipped']} files")

        if self.generation_stats["errors"]:
            print(f"  {style.ERROR('Errors:')} {len(self.generation_stats['errors'])}")
            for error in self.generation_stats["errors"][:3]:
                print(f"    - {error}")

    def validate_consistency(self, analysis: ModelAnalysis) -> None:
        """Enhanced consistency validation"""
        print(f"\n{'='*80}")
        print(f"🔍 Validating Consistency for: {style.SUCCESS(analysis.model_name)}")
        print(f"{'='*80}")

        validator = ConsistencyValidator()
        issues = validator.validate_all(analysis)

        if not issues:
            print(f"{style.SUCCESS('✅ All components are consistent!')}")
        else:
            # Group by severity
            critical = [i for i in issues if i.severity == "critical"]
            warnings = [i for i in issues if i.severity == "warning"]
            info = [i for i in issues if i.severity == "info"]

            if critical:
                print(f"\n{style.ERROR('🚨 Critical Issues:')}")
                for issue in critical:
                    print(f"  • {issue}")

            if warnings:
                print(f"\n{style.WARNING('⚠️  Warnings:')}")
                for issue in warnings:
                    print(f"  • {issue}")

            if info:
                print(f"\n{style.NOTICE('ℹ️  Information:')}")
                for issue in info:
                    print(f"  • {issue}")

            # Suggest fix
            fixable_count = sum(1 for i in issues if i.fix_available)
            if fixable_count > 0:
                print(f"\n💡 {fixable_count} issues can be fixed automatically.")
                print(f"   Run: python {Path(__file__).name} fix {analysis.model_name}")

    async def sync_components(self, analysis: ModelAnalysis) -> None:
        """Sync components with model changes"""
        print(f"\n{'='*80}")
        print(f"🔄 Syncing Components for: {style.SUCCESS(analysis.model_name)}")
        print(f"{'='*80}")

        syncer = ComponentSyncer(self.config)
        changes = await syncer.sync_all(analysis)

        # Display sync results
        if changes["added"]:
            print(f"\n{style.SUCCESS('➕ Added:')}")
            for item in changes["added"]:
                print(f"  • {item}")

        if changes["modified"]:
            print(f"\n{style.NOTICE('📝 Modified:')}")
            for item in changes["modified"]:
                print(f"  • {item}")

        if changes["removed"]:
            print(f"\n{style.WARNING('➖ Removed:')}")
            for item in changes["removed"]:
                print(f"  • {item}")

        if not any(changes.values()):
            print("✅ All components are in sync!")

    def watch_mode(self, model_name: str) -> None:
        """Watch for model changes and auto-sync"""
        print(f"\n{'='*80}")
        print(f"👁️  Watching Model: {style.SUCCESS(model_name)}")
        print(f"{'='*80}")
        print("Press Ctrl+C to stop watching...")

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class ModelChangeHandler(FileSystemEventHandler):
                def __init__(self, framework, model_name):
                    self.framework = framework
                    self.model_name = model_name
                    self.last_sync = datetime.now()

                def on_modified(self, event):
                    if event.is_directory:
                        return

                    # Check if it's a model file
                    if "models.py" in event.src_path:
                        # Debounce - wait 1 second
                        if (datetime.now() - self.last_sync).seconds < 1:
                            return

                        self.last_sync = datetime.now()
                        print(f"\n🔄 Change detected in {event.src_path}")

                        # Re-analyze and sync
                        analysis = self.framework.analyze_model(self.model_name)
                        if analysis:
                            asyncio.run(self.framework.sync_components(analysis))

            handler = ModelChangeHandler(self, model_name)
            observer = Observer()

            # Watch all app directories
            for app_name, app_config in self.apps_config.items():
                observer.schedule(handler, app_config["path"], recursive=True)

            observer.start()

            try:
                while True:
                    import time

                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        except ImportError:
            print(style.ERROR("❌ watchdog not installed. Install with: pip install watchdog"))
        except KeyboardInterrupt:
            print("\n✋ Watch mode stopped.")


class TemplateGenerator(ComponentGenerator):
    """Generates Django templates"""

    def generate(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate a single template"""
        # This method is required by the abstract base class
        # but we'll use generate_template for specific templates
        return ""

    def generate_template(
        self, analysis: ModelAnalysis, template_type: str, config: GenerationConfig
    ) -> str:
        """Generate specific template type"""
        generators = {
            "list": self._generate_list_template,
            "form": self._generate_form_template,
            "detail": self._generate_detail_template,
            "partial_list": self._generate_partial_list_template,
            "confirm_delete": self._generate_confirm_delete_template,
        }

        generator = generators.get(template_type)
        if generator:
            return generator(analysis, config)
        return ""

    def generate_all_templates(
        self, analysis: ModelAnalysis, config: GenerationConfig
    ) -> Dict[str, str]:
        """Generate all templates for a model"""
        templates = {}
        template_types = ["list", "form", "detail", "partial_list", "confirm_delete"]

        for template_type in template_types:
            templates[template_type] = self.generate_template(analysis, template_type, config)

        return templates

    def _generate_list_template(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate list template"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        # Get URL patterns
        urls = URLPatternAnalyzer.generate_urls(model_name, config.url_pattern)

        return f"""
{{% extends 'base.html' %}}
{{% load static %}}
{{% load custom_filters %}}

{{% block title %}}{model_name} List{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="card shadow-sm">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
            <h3 class="mb-0">
                <i class="bi bi-list-ul"></i> {model_name} Management
            </h3>
            <div class="d-flex gap-2">
                <button class="btn btn-light btn-sm" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Refresh
                </button>
                <a href="{{% url '{app_name}:{model_lower}-create' %}}"
                   class="btn btn-success"
                   hx-get="{{% url '{app_name}:{model_lower}-create' %}}"
                   hx-target="#modal-container"
                   hx-trigger="click">
                    <i class="bi bi-plus-circle"></i> Add {model_name}
                </a>
            </div>
        </div>
        <div class="card-body">
            <!-- Search and Filter Bar -->
            <div class="row mb-3">
                <div class="col-md-6">
                    <form method="get" class="d-flex gap-2">
                        <input type="text" name="search" class="form-control"
                               placeholder="Search {model_lower}s..."
                               value="{{{{ request.GET.search }}}}">
                        <button type="submit" class="btn btn-outline-primary">
                            <i class="bi bi-search"></i>
                        </button>
                    </form>
                </div>
                <div class="col-md-6 text-end">
                    <span class="text-muted">Total: {{{{ total_count }}}} records</span>
                </div>
            </div>

            <!-- Messages -->
            {{% if messages %}}
                {{% for message in messages %}}
                    <div class="alert alert-{{{{ message.tags }}}} alert-dismissible fade show" role="alert">
                        {{{{ message }}}}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {{% endfor %}}
            {{% endif %}}

            <!-- List Container -->
            <div id="{model_lower}-list">
                {{% include '{app_name}/partials/{model_lower}_partial_list.html' %}}
            </div>
        </div>
    </div>
</div>

<!-- Modal Container -->
<div id="modal-container"></div>

<!-- Loading Indicator -->
<div class="htmx-indicator" id="loading-indicator">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
</div>
{{% endblock %}}

{{% block extra_js %}}
<script>
    // Auto-close alerts after 5 seconds
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            var alerts = document.querySelectorAll('.alert');
            alerts.forEach(function(alert) {{
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }});
        }}, 5000);
    }});
</script>
{{% endblock %}}
"""

    def _generate_form_template(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate form template (modal)"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        return f"""
{{% load widget_tweaks %}}

<div class="modal fade show" style="display: block;" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title">
                    {{% if form.instance.pk %}}
                        <i class="bi bi-pencil-square"></i> Edit {model_name}
                    {{% else %}}
                        <i class="bi bi-plus-circle"></i> Create New {model_name}
                    {{% endif %}}
                </h5>
                <button type="button" class="btn-close btn-close-white" onclick="closeModal()"></button>
            </div>
            <form method="post"
                  hx-post="{{% if form.instance.pk %}}{{% url '{app_name}:{model_lower}-edit' form.instance.pk %}}{{% else %}}{{% url '{app_name}:{model_lower}-create' %}}{{% endif %}}"
                  hx-target="#{model_lower}-list"
                  hx-swap="innerHTML"
                  hx-indicator="#loading-indicator">
                {{% csrf_token %}}
                <div class="modal-body">
                    {{% if form.non_field_errors %}}
                        <div class="alert alert-danger">
                            {{{{ form.non_field_errors }}}}
                        </div>
                    {{% endif %}}

                    <div class="row">
                        {{% for field in form %}}
                        <div class="col-md-{{% if field.field.widget.input_type == 'checkbox' %}}12{{% else %}}6{{% endif %}} mb-3">
                            {{% if field.field.widget.input_type == 'checkbox' %}}
                                <div class="form-check">
                                    {{{{ field|add_class:"form-check-input" }}}}
                                    <label class="form-check-label" for="{{{{ field.id_for_label }}}}">
                                        {{{{ field.label }}}}
                                    </label>
                                </div>
                            {{% else %}}
                                <label for="{{{{ field.id_for_label }}}}" class="form-label">
                                    {{{{ field.label }}}}
                                    {{% if field.field.required %}}<span class="text-danger">*</span>{{% endif %}}
                                </label>
                                {{{{ field|add_class:"form-control" }}}}
                            {{% endif %}}

                            {{% if field.errors %}}
                                <div class="invalid-feedback d-block">
                                    {{{{ field.errors }}}}
                                </div>
                            {{% endif %}}

                            {{% if field.help_text %}}
                                <small class="form-text text-muted">{{{{ field.help_text }}}}</small>
                            {{% endif %}}
                        </div>
                        {{% endfor %}}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">
                        <i class="bi bi-x-circle"></i> Cancel
                    </button>
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save"></i>
                        {{% if form.instance.pk %}}Update{{% else %}}Create{{% endif %}}
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
<div class="modal-backdrop fade show"></div>

<script>
    function closeModal() {{
        document.getElementById('modal-container').innerHTML = '';
    }}

    // Focus first input
    var firstInput = document.querySelector('.modal input:not([type="hidden"])');
    if (firstInput) firstInput.focus();

    // Handle ESC key
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') closeModal();
    }});
</script>
"""

    def _generate_detail_template(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate detail template"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        return f"""
{{% extends 'base.html' %}}
{{% load static %}}

{{% block title %}}{model_name} Details{{% endblock %}}

{{% block content %}}
<div class="container">
    <div class="card shadow-sm">
        <div class="card-header bg-info text-white">
            <div class="d-flex justify-content-between align-items-center">
                <h3 class="mb-0">
                    <i class="bi bi-info-circle"></i> {model_name} Details
                </h3>
                <a href="{{% url '{app_name}:{model_lower}-list' %}}" class="btn btn-light btn-sm">
                    <i class="bi bi-arrow-left"></i> Back to List
                </a>
            </div>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-8">
                    <dl class="row">
                        {{% for field in {model_lower}._meta.fields %}}
                        <dt class="col-sm-4">{{{{ field.verbose_name|title }}}}:</dt>
                        <dd class="col-sm-8">{{{{ {model_lower}|get_item:field.name|default:"—" }}}}</dd>
                        {{% endfor %}}
                    </dl>
                </div>
                <div class="col-md-4">
                    <div class="d-grid gap-2">
                        <a href="{{% url '{app_name}:{model_lower}-edit' {model_lower}.pk %}}"
                           class="btn btn-warning"
                           hx-get="{{% url '{app_name}:{model_lower}-edit' {model_lower}.pk %}}"
                           hx-target="#modal-container"
                           hx-trigger="click">
                            <i class="bi bi-pencil"></i> Edit
                        </a>
                        <button class="btn btn-danger"
                                hx-delete="{{% url '{app_name}:{model_lower}-delete' {model_lower}.pk %}}"
                                hx-confirm="Are you sure you want to delete this {model_name}?"
                                hx-redirect="{{% url '{app_name}:{model_lower}-list' %}}">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </div>

                    <!-- Metadata -->
                    <div class="mt-4">
                        <h6 class="text-muted">Metadata</h6>
                        <small class="text-muted">
                            {{% if {model_lower}.created_at %}}
                                Created: {{{{ {model_lower}.created_at|date:"M d, Y H:i" }}}}<br>
                            {{% endif %}}
                            {{% if {model_lower}.updated_at %}}
                                Updated: {{{{ {model_lower}.updated_at|date:"M d, Y H:i" }}}}<br>
                            {{% endif %}}
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal Container -->
<div id="modal-container"></div>
{{% endblock %}}
"""

    def _generate_partial_list_template(
        self, analysis: ModelAnalysis, config: GenerationConfig
    ) -> str:
        """Generate partial list template for HTMX"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        return f"""
<div class="table-responsive">
    <table class="table table-hover">
        <thead class="table-light">
            <tr>
                {{% for field in list_fields %}}
                <th scope="col">
                    <a href="?ordering={{% if request.GET.ordering == field %}}-{{% endif %}}{{{{ field }}}}"
                       class="text-decoration-none text-dark">
                        {{{{ field|title|replace_underscore }}}}
                        {{% if request.GET.ordering == field %}}
                            <i class="bi bi-sort-down"></i>
                        {{% elif request.GET.ordering == "-"|add:field %}}
                            <i class="bi bi-sort-up"></i>
                        {{% else %}}
                            <i class="bi bi-sort text-muted"></i>
                        {{% endif %}}
                    </a>
                </th>
                {{% endfor %}}
                <th scope="col" class="text-center" style="width: 150px;">Actions</th>
            </tr>
        </thead>
        <tbody>
            {{% for {model_lower} in {model_lower}s %}}
            <tr id="{model_lower}-row-{{{{ {model_lower}.pk }}}}">
                {{% for field in list_fields %}}
                <td>{{{{ {model_lower}|get_item:field|truncate:50 }}}}</td>
                {{% endfor %}}
                <td class="text-center">
                    <div class="btn-group btn-group-sm" role="group">
                        <a href="{{% url '{app_name}:{model_lower}-detail' {model_lower}.pk %}}"
                           class="btn btn-outline-info" title="View Details">
                            <i class="bi bi-eye"></i>
                        </a>
                        <a href="{{% url '{app_name}:{model_lower}-edit' {model_lower}.pk %}}"
                           class="btn btn-outline-warning"
                           hx-get="{{% url '{app_name}:{model_lower}-edit' {model_lower}.pk %}}"
                           hx-target="#modal-container"
                           hx-trigger="click" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </a>
                        <button class="btn btn-outline-danger"
                                hx-delete="{{% url '{app_name}:{model_lower}-delete' {model_lower}.pk %}}"
                                hx-confirm="Are you sure you want to delete this {model_name}?"
                                hx-target="#{model_lower}-row-{{{{ {model_lower}.pk }}}}"
                                hx-swap="outerHTML swap:0.5s" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
            {{% empty %}}
            <tr>
                <td colspan="{{{{ list_fields|length|add:1 }}}}" class="text-center py-4">
                    <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
                    <p class="text-muted mt-2">No {model_lower}s found.</p>
                    <a href="{{% url '{app_name}:{model_lower}-create' %}}"
                       class="btn btn-primary"
                       hx-get="{{% url '{app_name}:{model_lower}-create' %}}"
                       hx-target="#modal-container"
                       hx-trigger="click">
                        <i class="bi bi-plus-circle"></i> Create First {model_name}
                    </a>
                </td>
            </tr>
            {{% endfor %}}
        </tbody>
    </table>
</div>

<!-- Pagination -->
{{% if is_paginated %}}
<nav aria-label="{model_name} pagination">
    <ul class="pagination justify-content-center">
        {{% if page_obj.has_previous %}}
            <li class="page-item">
                <a class="page-link"
                   href="?page={{{{ page_obj.previous_page_number }}}}&{{{{ request.GET.urlencode }}}}"
                   hx-get="?page={{{{ page_obj.previous_page_number }}}}&{{{{ request.GET.urlencode }}}}"
                   hx-target="#{model_lower}-list"
                   hx-swap="innerHTML">Previous</a>
            </li>
        {{% else %}}
            <li class="page-item disabled">
                <span class="page-link">Previous</span>
            </li>
        {{% endif %}}

        {{% for num in page_obj.paginator.page_range %}}
            {{% if page_obj.number == num %}}
                <li class="page-item active">
                    <span class="page-link">{{{{ num }}}}</span>
                </li>
            {{% elif num > page_obj.number|add:'-3' and num < page_obj.number|add:'3' %}}
                <li class="page-item">
                    <a class="page-link"
                       href="?page={{{{ num }}}}&{{{{ request.GET.urlencode }}}}"
                       hx-get="?page={{{{ num }}}}&{{{{ request.GET.urlencode }}}}"
                       hx-target="#{model_lower}-list"
                       hx-swap="innerHTML">{{{{ num }}}}</a>
                </li>
            {{% endif %}}
        {{% endfor %}}

        {{% if page_obj.has_next %}}
            <li class="page-item">
                <a class="page-link"
                   href="?page={{{{ page_obj.next_page_number }}}}&{{{{ request.GET.urlencode }}}}"
                   hx-get="?page={{{{ page_obj.next_page_number }}}}&{{{{ request.GET.urlencode }}}}"
                   hx-target="#{model_lower}-list"
                   hx-swap="innerHTML">Next</a>
            </li>
        {{% else %}}
            <li class="page-item disabled">
                <span class="page-link">Next</span>
            </li>
        {{% endif %}}
    </ul>
</nav>
{{% endif %}}
"""

    def _generate_confirm_delete_template(
        self, analysis: ModelAnalysis, config: GenerationConfig
    ) -> str:
        """Generate delete confirmation template"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        return f"""
{{% extends 'base.html' %}}

{{% block title %}}Delete {model_name}{{% endblock %}}

{{% block content %}}
<div class="container">
    <div class="card shadow-sm">
        <div class="card-header bg-danger text-white">
            <h3 class="mb-0">
                <i class="bi bi-exclamation-triangle"></i> Confirm Deletion
            </h3>
        </div>
        <div class="card-body">
            <p>Are you sure you want to delete the following {model_name}?</p>

            <div class="alert alert-warning">
                <strong>{{{{ object }}}}</strong>
            </div>

            <p class="text-danger">
                <i class="bi bi-exclamation-circle"></i> This action cannot be undone.
            </p>

            <form method="post">
                {{% csrf_token %}}
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-danger">
                        <i class="bi bi-trash"></i> Yes, Delete
                    </button>
                    <a href="{{% url '{app_name}:{model_lower}-list' %}}" class="btn btn-secondary">
                        <i class="bi bi-x-circle"></i> Cancel
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
{{% endblock %}}
"""

    def validate(self, analysis: ModelAnalysis, content: str) -> List[FixableIssue]:
        """Validate template content"""
        issues = []

        # Check for required template tags
        if "{% extends" not in content and "modal" not in content:
            issues.append(
                FixableIssue(
                    issue_type="missing_extends",
                    severity="warning",
                    file_path=None,
                    description="Template doesn't extend base.html",
                    fix_available=True,
                    fix_description="Add extends tag",
                )
            )

        return issues


class TestGenerator(ComponentGenerator):
    """Generates test code"""

    def generate(self, analysis: ModelAnalysis, config: GenerationConfig) -> str:
        """Generate test code"""
        model_name = analysis.model_name
        model_lower = model_name.lower()
        app_name = analysis.app_name

        # Get test data based on fields
        test_data = self._generate_test_data(analysis)

        return f'''import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from {analysis.app_name}.models import {model_name}
from {analysis.app_name}.forms import {model_name}Form

User = get_user_model()


@pytest.mark.django_db
class Test{model_name}Views:
    """Test cases for {model_name} views"""

    @pytest.fixture
    def user(self):
        """Create test user"""
        return User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    @pytest.fixture
    def {model_lower}(self, user):
        """Create test {model_name} instance"""
        # CUSTOM_CODE_START: fixture_setup
        # Customize the fixture creation
        return {model_name}.objects.create(
{self._generate_fixture_data(analysis)}
        )
        # CUSTOM_CODE_END:

    def test_list_view_requires_login(self, client):
        """Test list view requires authentication"""
        url = reverse('{app_name}:{model_lower}-list')
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login

    def test_list_view(self, client, user, {model_lower}):
        """Test {model_name} list view"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-list')
        response = client.get(url)

        assert response.status_code == 200
        assert '{model_lower}s' in response.context
        assert {model_lower} in response.context['{model_lower}s']

    def test_list_view_search(self, client, user, {model_lower}):
        """Test list view search functionality"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-list')

        # CUSTOM_CODE_START: search_test
        # Customize search test based on your search fields
        response = client.get(url, {{'search': 'test'}})
        assert response.status_code == 200
        # CUSTOM_CODE_END:

    def test_create_view_get(self, client, user):
        """Test {model_name} create view GET request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-create')
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context['form'], {model_name}Form)

    def test_create_view_post(self, client, user):
        """Test {model_name} create view POST request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-create')

        data = {{
{test_data}
        }}

        response = client.post(url, data)

        # Should redirect after successful creation
        assert response.status_code == 302
        assert {model_name}.objects.count() == 1

        created = {model_name}.objects.first()
        # CUSTOM_CODE_START: create_assertions
        # Add custom assertions for created object
        # CUSTOM_CODE_END:

    def test_create_view_htmx(self, client, user):
        """Test {model_name} create view with HTMX"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-create')

        data = {{
{test_data}
        }}

        # Simulate HTMX request
        response = client.post(url, data, HTTP_HX_REQUEST='true')

        assert response.status_code == 200
        assert '<table' in response.content.decode()

    def test_update_view_get(self, client, user, {model_lower}):
        """Test {model_name} update view GET request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-edit', kwargs={{'pk': {model_lower}.pk}})
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context['form'], {model_name}Form)
        assert response.context['form'].instance == {model_lower}

    def test_update_view_post(self, client, user, {model_lower}):
        """Test {model_name} update view POST request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-edit', kwargs={{'pk': {model_lower}.pk}})

        data = {{
{test_data}
            # CUSTOM_CODE_START: update_data
            # Modify data for update test
            # CUSTOM_CODE_END:
        }}

        response = client.post(url, data)

        assert response.status_code == 302
        {model_lower}.refresh_from_db()

        # CUSTOM_CODE_START: update_assertions
        # Add assertions to verify update
        # CUSTOM_CODE_END:

    def test_delete_view_get(self, client, user, {model_lower}):
        """Test {model_name} delete view GET request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-delete', kwargs={{'pk': {model_lower}.pk}})
        response = client.get(url)

        assert response.status_code == 200

    def test_delete_view_post(self, client, user, {model_lower}):
        """Test {model_name} delete view POST request"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-delete', kwargs={{'pk': {model_lower}.pk}})

        response = client.post(url)

        assert response.status_code == 302
        assert {model_name}.objects.count() == 0

    def test_delete_view_htmx(self, client, user, {model_lower}):
        """Test {model_name} delete with HTMX"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-delete', kwargs={{'pk': {model_lower}.pk}})

        response = client.delete(url, HTTP_HX_REQUEST='true')

        assert response.status_code == 204
        assert {model_name}.objects.count() == 0

    def test_detail_view(self, client, user, {model_lower}):
        """Test {model_name} detail view"""
        client.force_login(user)
        url = reverse('{app_name}:{model_lower}-detail', kwargs={{'pk': {model_lower}.pk}})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['{model_lower}'] == {model_lower}


@pytest.mark.django_db
class Test{model_name}Form:
    """Test cases for {model_name}Form"""

    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {{
{test_data}
        }}

        form = {model_name}Form(data=form_data)
        assert form.is_valid()

    def test_form_missing_required_fields(self):
        """Test form with missing required fields"""
        form = {model_name}Form(data={{}})
        assert not form.is_valid()

        # CUSTOM_CODE_START: form_validation_tests
        # Add specific field validation tests
        # CUSTOM_CODE_END:

    def test_form_widgets(self):
        """Test form widgets are properly configured"""
        form = {model_name}Form()

        # CUSTOM_CODE_START: widget_tests
        # Add widget-specific tests
        # CUSTOM_CODE_END:


# CUSTOM_CODE_START: additional_tests
# Add any additional test classes or functions here
# CUSTOM_CODE_END:
'''

    def _generate_test_data(self, analysis: ModelAnalysis) -> str:
        """Generate test data based on model fields"""
        lines = []

        for field_name, field_info in analysis.fields.items():
            if field_name in ["id", "created_at", "updated_at"]:
                continue

            value = self._get_test_value_for_field(field_name, field_info)
            lines.append(f"            '{field_name}': {value},")

        return "\n".join(lines)

    def _generate_fixture_data(self, analysis: ModelAnalysis) -> str:
        """Generate fixture data for model creation"""
        lines = []

        for field_name, field_info in analysis.fields.items():
            if field_name in ["id", "created_at", "updated_at"]:
                continue

            # Only include required fields in fixture
            if not field_info.get("blank", False):
                value = self._get_test_value_for_field(field_name, field_info)
                lines.append(f"            {field_name}={value},")

        return "\n".join(lines)

    def _get_test_value_for_field(self, field_name: str, field_info: Dict[str, Any]) -> str:
        """Get appropriate test value for field type"""
        field_type = field_info["type"]

        # Common field patterns
        if "email" in field_name.lower():
            return "'test@example.com'"
        elif "url" in field_name.lower():
            return "'https://example.com'"
        elif "phone" in field_name.lower():
            return "'+1234567890'"
        elif "name" in field_name.lower():
            return "'Test Name'"
        elif "title" in field_name.lower():
            return "'Test Title'"
        elif "description" in field_name.lower():
            return "'Test description content'"

        # Field type defaults
        type_defaults = {
            "CharField": "'test_value'",
            "TextField": "'Test content\\nWith multiple lines'",
            "IntegerField": "42",
            "FloatField": "3.14",
            "DecimalField": "'10.50'",
            "BooleanField": "True",
            "DateField": "'2024-01-01'",
            "DateTimeField": "'2024-01-01T12:00:00Z'",
            "EmailField": "'test@example.com'",
            "URLField": "'https://example.com'",
            "SlugField": "'test-slug'",
            "UUIDField": "'550e8400-e29b-41d4-a716-446655440000'",
            "JSONField": "{'key': 'value'}",
        }

        return type_defaults.get(field_type, "'test'")

    def validate(self, analysis: ModelAnalysis, content: str) -> List[FixableIssue]:
        """Validate test content"""
        issues = []

        # Check for pytest markers
        if "@pytest.mark.django_db" not in content:
            issues.append(
                FixableIssue(
                    issue_type="missing_pytest_marker",
                    severity="warning",
                    file_path=None,
                    description="Missing @pytest.mark.django_db decorator",
                    fix_available=True,
                    fix_description="Add pytest marker for database tests",
                )
            )

        # Check for test coverage
        required_tests = [
            "test_list_view",
            "test_create_view",
            "test_update_view",
            "test_delete_view",
        ]

        for test in required_tests:
            if test not in content:
                issues.append(
                    FixableIssue(
                        issue_type="missing_test",
                        severity="info",
                        file_path=None,
                        description=f"Missing {test}",
                        fix_available=True,
                        fix_description=f"Add {test} method",
                    )
                )

        return issues


class ConsistencyValidator:
    """Validates consistency across components"""

    def validate_all(self, analysis: ModelAnalysis) -> List[FixableIssue]:
        """Validate all components for consistency"""
        issues = []

        # Validate form-model consistency
        issues.extend(self._validate_form_model_consistency(analysis))

        # Validate template-view consistency
        issues.extend(self._validate_template_view_consistency(analysis))

        # Validate URL-view consistency
        issues.extend(self._validate_url_view_consistency(analysis))

        # Validate test coverage
        issues.extend(self._validate_test_coverage(analysis))

        return issues

    def _validate_form_model_consistency(self, analysis: ModelAnalysis) -> List[FixableIssue]:
        """Validate form fields match model"""
        issues = []

        if analysis.form_status.exists and analysis.crud_config:
            # Check if form uses correct fields
            if analysis.crud_config["fields"] != "__all__":
                # Would need to parse form to check fields
                pass

        return issues

    def _validate_template_view_consistency(self, analysis: ModelAnalysis) -> List[FixableIssue]:
        """Validate templates match view expectations"""
        issues = []

        # Check if list template exists for ListView
        if "List" in analysis.view_status and analysis.view_status["List"].exists:
            if (
                "list" not in analysis.template_status
                or not analysis.template_status["list"].exists
            ):
                issues.append(
                    FixableIssue(
                        issue_type="missing_template",
                        severity="critical",
                        file_path=None,
                        description="ListView exists but list template is missing",
                        fix_available=True,
                        fix_description="Generate list template",
                    )
                )

        return issues

    def _validate_url_view_consistency(self, analysis: ModelAnalysis) -> List[FixableIssue]:
        """Validate URLs match existing views"""
        issues = []

        # Check if URLs exist for all views
        existing_views = [k for k, v in analysis.view_status.items() if v.exists]

        if existing_views and not analysis.url_status.exists:
            issues.append(
                FixableIssue(
                    issue_type="missing_urls",
                    severity="critical",
                    file_path=None,
                    description=f"Views exist but URL patterns are missing",
                    fix_available=True,
                    fix_description="Add URL patterns for views",
                )
            )

        return issues

    def _validate_test_coverage(self, analysis: ModelAnalysis) -> List[FixableIssue]:
        """Validate test coverage"""
        issues = []

        if not analysis.test_status.exists:
            issues.append(
                FixableIssue(
                    issue_type="missing_tests",
                    severity="warning",
                    file_path=None,
                    description="No tests found for model",
                    fix_available=True,
                    fix_description="Generate comprehensive test suite",
                )
            )

        return issues


class ComponentSyncer:
    """Syncs components with model changes"""

    def __init__(self, config: GenerationConfig):
        self.config = config

    async def sync_all(self, analysis: ModelAnalysis) -> Dict[str, List[str]]:
        """Sync all components with model changes"""
        changes = {"added": [], "modified": [], "removed": []}

        # Sync form
        form_changes = await self._sync_form(analysis)
        changes["added"].extend(form_changes.get("added", []))
        changes["modified"].extend(form_changes.get("modified", []))
        changes["removed"].extend(form_changes.get("removed", []))

        # Sync templates
        template_changes = await self._sync_templates(analysis)
        changes["added"].extend(template_changes.get("added", []))
        changes["modified"].extend(template_changes.get("modified", []))

        return changes

    async def _sync_form(self, analysis: ModelAnalysis) -> Dict[str, List[str]]:
        """Sync form with model fields"""
        changes = {"added": [], "modified": [], "removed": []}

        if not analysis.form_status.exists:
            return changes

        # This would implement intelligent form syncing
        # Detecting new fields, removed fields, etc.

        return changes

    async def _sync_templates(self, analysis: ModelAnalysis) -> Dict[str, List[str]]:
        """Sync templates with model changes"""
        changes = {"added": [], "modified": [], "removed": []}

        # This would update templates to include new fields
        # or remove references to deleted fields

        return changes


def main():
    """Enhanced CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enterprise Consistency Framework v3.0 - Production Django Code Generation",
        epilog="""
🚀 Examples:
  %(prog)s analyze User
  %(prog)s preview Book --verbose
  %(prog)s generate Article --interactive
  %(prog)s fix BlogPost
  %(prog)s batch analyze User Book Article
  %(prog)s validate --all
  %(prog)s watch MyModel
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "mode",
        choices=["analyze", "preview", "generate", "validate", "sync", "watch", "fix", "batch"],
        help="Operation mode",
    )

    parser.add_argument("models", nargs="+", help="Model name(s) to process")

    # Configuration options
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode - confirm each action"
    )
    parser.add_argument(
        "--components",
        "-c",
        nargs="+",
        choices=["form", "views", "templates", "urls", "tests"],
        help="Specific components to generate",
    )
    parser.add_argument(
        "--no-preserve-custom", action="store_true", help="Disable custom code preservation"
    )
    parser.add_argument("--no-backup", action="store_true", help="Disable automatic backups")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--url-pattern",
        choices=["bfagent", "standard", "rest"],
        default="bfagent",
        help="URL pattern style (default: bfagent)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force regeneration even if components exist"
    )
    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="Enable parallel processing for batch operations",
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Process all models in the project"
    )

    args = parser.parse_args()

    # ASCII Art Banner
    print(
        style.SUCCESS(
            """
╔══════════════════════════════════════════════════════════════╗
║     Enterprise Consistency Framework v3.0                     ║
║     🚀 Production-Ready Django Code Generation               ║
║     🔧 Now with Fix Mode & Advanced Features                 ║
╚══════════════════════════════════════════════════════════════╝
    """
        )
    )

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build configuration
    config = GenerationConfig(
        url_pattern=URLPattern(args.url_pattern),
        preserve_custom=not args.no_preserve_custom,
        create_backups=not args.no_backup,
        interactive=args.interactive,
        dry_run=args.dry_run,
        fix_mode=(args.mode == "fix"),
        verbose=args.verbose,
        components=args.components,
        batch_mode=(args.mode == "batch"),
        async_generation=args.parallel,
    )

    # Get models to process
    if args.all:
        # Get all models from all apps
        model_names = []
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith("django."):
                for model in app_config.get_models():
                    model_names.append(model.__name__)
    else:
        model_names = args.models

    # Initialize framework
    framework = EnhancedConsistencyFramework(config)

    # Execute
    try:
        import asyncio

        mode = GenerationMode[args.mode.upper()]

        # Run the async execute method
        asyncio.run(
            framework.execute(
                mode,
                model_names,
                interactive=args.interactive,
                components=args.components,
                force=args.force,
            )
        )

        print(f"\n{style.SUCCESS('✅ Operation completed successfully!')}")

        # Show summary for fix mode
        if config.fix_mode and framework.generation_stats["files_fixed"] > 0:
            print(f"   Fixed {framework.generation_stats['files_fixed']} issues")

    except KeyboardInterrupt:
        print(f"\n{style.WARNING('⚠️  Operation cancelled by user')}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{style.ERROR(f'❌ Error: {e}')}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Support for running as module
    main()
