#!/usr/bin/env python
"""
API Endpoint Checker for BF Agent v4.0.0
Comprehensive REST API validation with OpenAPI/Swagger generation

Key improvements in v4:
- Fixed regex errors
- Intelligent model name processing (BookProjects → projects)
- Smart pluralization that handles compound words
- Better endpoint matching
"""
import asyncio
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path

import django
import yaml
from django.apps import apps
from django.db import models
from django.urls import URLPattern, URLResolver, get_resolver

# Setup Django
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


django.setup()


# Optional imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

try:
    from openapi_spec_validator import validate_spec

    OPENAPI_VALIDATOR_AVAILABLE = True
except ImportError:
    OPENAPI_VALIDATOR_AVAILABLE = False
    validate_spec = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP methods enum for type safety"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass(slots=True)
class EndpointInfo:
    """Optimized endpoint information using slots"""

    path: str
    name: str
    view_name: str
    methods: List[HTTPMethod]
    namespace: str
    is_api: bool
    is_rest: bool
    is_async: bool = False
    view_class: Optional[str] = None
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get full namespaced name"""
        if self.namespace and self.view_name:
            return f"{self.namespace}:{self.view_name}"
        return self.view_name or self.name

    @property
    def operation_id(self) -> str:
        """Generate OpenAPI operation ID"""
        parts = []
        if self.namespace:
            parts.append(self.namespace)
        parts.append(self.view_name or self.name)
        return "_".join(parts).replace("-", "_")


@dataclass
class ModelEndpointCoverage:
    """Model endpoint coverage analysis"""

    model_name: str
    expected_endpoints: List[Dict[str, str]]
    found_endpoints: List[EndpointInfo]
    missing_endpoints: List[Dict[str, str]]
    coverage_percent: float = 0.0

    def calculate_coverage(self) -> None:
        """Calculate coverage percentage"""
        if self.expected_endpoints:
            found_count = len(self.expected_endpoints) - len(self.missing_endpoints)
            self.coverage_percent = (found_count / len(self.expected_endpoints)) * 100


@dataclass
class APIAnalysisReport:
    """Complete API analysis report"""

    generated_at: datetime
    app_name: str
    total_models: int
    total_endpoints: int
    api_endpoints: int
    rest_endpoints: int
    async_endpoints: int
    models: Dict[str, Any]
    endpoints: List[EndpointInfo]
    coverage: Dict[str, ModelEndpointCoverage]
    performance_metrics: Dict[str, float]
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class APIEndpointChecker:
    """
    Advanced API endpoint analysis and validation with performance optimizations
    """

    # Common prefixes to remove for intelligent model name processing
    MODEL_PREFIXES = ["book", "user", "agent", "system", "app"]

    # Irregular plural forms mapping
    IRREGULAR_PLURALS = {
        "person": "people",
        "child": "children",
        "man": "men",
        "woman": "women",
        "tooth": "teeth",
        "foot": "feet",
        "mouse": "mice",
        "goose": "geese",
        "ox": "oxen",
        "sheep": "sheep",
        "deer": "deer",
        "fish": "fish",
        "series": "series",
        "species": "species",
        "analysis": "analyses",
        "thesis": "theses",
        "crisis": "crises",
        "phenomenon": "phenomena",
        "criterion": "criteria",
        "datum": "data",
    }

    def __init__(
        self,
        app_name: str = "bfagent",
        include_admin: bool = False,
        profile_performance: bool = False,
    ):
        self.app_name = app_name
        self.include_admin = include_admin
        self.profile_performance = profile_performance
        self.models: Dict[str, Any] = {}
        self.endpoints: List[EndpointInfo] = []
        self.coverage: Dict[str, ModelEndpointCoverage] = {}
        self.performance_metrics: Dict[str, float] = {}
        self.console = Console() if RICH_AVAILABLE else None

    def analyze(self) -> APIAnalysisReport:
        """Run complete analysis with performance tracking"""
        start_time = time.time()

        if self.console:
            self.console.print("[bold blue]🔍 Starting API analysis...[/bold blue]")

        # Scan models
        self.scan_models()

        # Scan URLs
        self.scan_urls()

        # Generate report
        report = self.generate_report()

        if self.profile_performance:
            self.performance_metrics["total_time"] = time.time() - start_time
            report.performance_metrics = self.performance_metrics

        return report

    def scan_models(self) -> None:
        """Scan Django models for API expectations"""
        start_time = time.time()

        try:
            app = apps.get_app_config(self.app_name)
            models_list = list(app.get_models())  # Convert generator to list

            with (
                Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                )
                if self.console
                else nullcontext()
            ) as progress:
                if self.console:
                    task = progress.add_task("Scanning models...", total=len(models_list))

                for model in models_list:
                    if model._meta.abstract:
                        continue

                    model_data = {
                        "name": model.__name__,
                        "app_label": model._meta.app_label,
                        "db_table": model._meta.db_table,
                        "fields": [],
                        "relationships": [],
                        "expected_endpoints": self._get_expected_endpoints(model),
                        "has_crud_config": hasattr(model, "CRUDConfig"),
                    }

                    # Get CRUD configuration if available
                    if model_data["has_crud_config"]:
                        crud_config = model.CRUDConfig
                        model_data["crud_config"] = {
                            "viewset": getattr(crud_config, "viewset", None),
                            "serializer": getattr(crud_config, "serializer", None),
                            "permissions": getattr(crud_config, "permissions", []),
                        }

                    # Analyze fields
                    for field in model._meta.get_fields():
                        if not field.auto_created and not field.many_to_many:
                            model_data["fields"].append(
                                {
                                    "name": field.name,
                                    "type": field.__class__.__name__,
                                    "required": not getattr(field, "blank", True),
                                }
                            )

                    # Analyze relationships
                    for field in model._meta.get_fields():
                        if isinstance(
                            field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)
                        ):
                            model_data["relationships"].append(
                                {
                                    "field": field.name,
                                    "type": field.__class__.__name__,
                                    "related_model": field.related_model.__name__,
                                }
                            )

                    self.models[model.__name__] = model_data

                    if self.console:
                        progress.update(task, advance=1)

        except Exception as e:
            logger.error(f"Error scanning models: {e}")
            raise

        if self.profile_performance:
            self.performance_metrics["model_scan_time"] = time.time() - start_time

        logger.info(f"Scanned {len(self.models)} models")

    @lru_cache(maxsize=128)
    def _extract_model_base_name(self, model_name: str) -> str:
        """Extract base name from compound model names
        Examples:
            BookProjects → projects
            BookChapters → chapters
            AgentExecutions → executions
            Characters → characters
        """
        # Convert from CamelCase to lowercase
        name_lower = model_name[0].lower() + model_name[1:]

        # Convert CamelCase to snake_case
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", name_lower).lower()

        # Split into parts
        parts = snake_case.split("_")

        # Remove common prefixes
        if len(parts) > 1 and parts[0] in self.MODEL_PREFIXES:
            parts = parts[1:]

        # Rejoin
        return "_".join(parts)

    @lru_cache(maxsize=256)
    def _pluralize(self, word: str) -> str:
        """Smart pluralization with irregular forms support"""
        # Check for irregular plurals
        if word.lower() in self.IRREGULAR_PLURALS:
            return self.IRREGULAR_PLURALS[word.lower()]

        # Handle compound words (e.g., "book_project" → "book_projects")
        if "_" in word:
            parts = word.split("_")
            # Pluralize only the last part
            parts[-1] = self._pluralize(parts[-1])
            return "_".join(parts)

        # Standard pluralization rules
        if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
            return word[:-1] + "ies"
        elif word.endswith(("s", "ss", "sh", "ch", "x", "z", "o")):
            return word + "es"
        elif word.endswith("is"):
            return word[:-2] + "es"
        elif word.endswith("us"):
            return word[:-2] + "i"
        elif word.endswith("on"):
            return word[:-2] + "a"
        elif word.endswith("um"):
            return word[:-2] + "a"
        elif word.endswith(""):
            return word[:-1] + "ves"
        elif word.endswith("fe"):
            return word[:-2] + "ves"
        else:
            return word + "s"

    def _get_expected_endpoints(self, model) -> List[Dict[str, str]]:
        """Get expected REST endpoints for a model with intelligent naming"""
        # Extract base name and pluralize
        base_name = self._extract_model_base_name(model.__name__)
        plural_name = self._pluralize(base_name)

        return [
            {"method": "GET", "path": f"/api/{plural_name}/", "description": "List all items"},
            {"method": "POST", "path": f"/api/{plural_name}/", "description": "Create new item"},
            {
                "method": "GET",
                "path": f"/api/{plural_name}/{{id}}/",
                "description": "Get single item",
            },
            {"method": "PUT", "path": f"/api/{plural_name}/{{id}}/", "description": "Update item"},
            {
                "method": "PATCH",
                "path": f"/api/{plural_name}/{{id}}/",
                "description": "Partial update",
            },
            {
                "method": "DELETE",
                "path": f"/api/{plural_name}/{{id}}/",
                "description": "Delete item",
            },
        ]

    def scan_urls(self) -> None:
        """Scan all URL patterns with async detection"""
        start_time = time.time()

        try:
            resolver = get_resolver()
            self.endpoints = self._extract_urls(resolver.url_patterns)

            # Analyze API coverage
            self._analyze_api_coverage()

            if self.profile_performance:
                self.performance_metrics["url_scan_time"] = time.time() - start_time

            logger.info(f"Found {len(self.endpoints)} endpoints")

        except Exception as e:
            logger.error(f"Error scanning URLs: {e}")
            raise

    def _extract_urls(
        self, patterns: List[Union[URLResolver, URLPattern]], prefix: str = "", namespace: str = ""
    ) -> List[EndpointInfo]:
        """Recursively extract URL patterns with enhanced metadata"""
        endpoints = []

        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                # Handle included URLs
                sub_prefix = prefix + str(pattern.pattern)
                sub_namespace = (
                    f"{namespace}:{pattern.namespace}" if pattern.namespace else namespace
                )

                if not self.include_admin and "admin" in str(pattern.pattern):
                    continue

                endpoints.extend(
                    self._extract_urls(pattern.url_patterns, sub_prefix, sub_namespace)
                )

            elif isinstance(pattern, URLPattern):
                # Handle individual URL patterns
                path = prefix + str(pattern.pattern)
                view_name = getattr(pattern, "name", "")

                endpoint_info = self._analyze_endpoint(pattern, path, namespace, view_name)
                if endpoint_info:
                    endpoints.append(endpoint_info)

        return endpoints

    def _analyze_endpoint(
        self, pattern: URLPattern, path: str, namespace: str, view_name: str
    ) -> Optional[EndpointInfo]:
        """Analyze a single endpoint with detailed metadata"""
        try:
            # Clean path
            clean_path = self._clean_path(path)

            # Get HTTP methods and view info
            methods, view_class, is_async = self._get_view_info(pattern)

            # Get docstring
            docstring = None
            if hasattr(pattern.callback, "__doc__"):
                docstring = pattern.callback.__doc__
            elif hasattr(pattern.callback, "view_class") and hasattr(
                pattern.callback.view_class, "__doc__"
            ):
                docstring = pattern.callback.view_class.__doc__

            # Extract parameters from path
            parameters = self._extract_path_parameters(clean_path)

            return EndpointInfo(
                path=clean_path,
                name=pattern.name or "",
                view_name=view_name,
                methods=[HTTPMethod(m) for m in methods],
                namespace=namespace,
                is_api=self._is_api_endpoint(clean_path),
                is_rest=self._is_rest_endpoint(clean_path),
                is_async=is_async,
                view_class=view_class,
                docstring=docstring,
                parameters=parameters,
            )

        except Exception as e:
            logger.warning(f"Error analyzing endpoint {path}: {e}")
            return None

    def _get_view_info(self, pattern: URLPattern) -> Tuple[List[str], Optional[str], bool]:
        """Get HTTP methods, view class name, and async status"""
        try:
            view = pattern.callback
            methods = ["GET"]  # Default
            view_class = None
            is_async = False

            # Check if it's an async view
            if asyncio.iscoroutinefunction(view):
                is_async = True

            if hasattr(view, "view_class"):
                # Class-based view
                view_cls = view.view_class
                view_class = f"{view_cls.__module__}.{view_cls.__name__}"

                # Get HTTP methods from view class
                http_method_names = getattr(view_cls, "http_method_names", [])
                methods = [m.upper() for m in http_method_names if m != "options"]

                # Check for ViewSet actions
                if hasattr(view, "actions"):
                    # DRF ViewSet
                    methods = list(view.actions.keys())
                    methods = [m.upper() for m in methods]

            elif hasattr(view, "__name__"):
                # Function-based view
                view_class = f"{view.__module__}.{view.__name__}"
                # Try to infer methods from decorators or name
                if "api_view" in str(view):
                    # DRF function-based view
                    if hasattr(view, "_method_names"):
                        methods = list(view._method_names)

            return methods, view_class, is_async

        except Exception:
            return ["GET"], None, False

    @lru_cache(maxsize=512)
    def _clean_path(self, path: str) -> str:
        """Clean and normalize URL path with improved regex handling"""
        # Remove regex patterns safely
        path = re.sub(r"\^", "", path)  # Remove start anchor
        path = re.sub(r"\$", "", path)  # Remove end anchor
        path = re.sub(r"\?P<(\w+)>[^)]+\)", r"{\1}", path)  # Convert named groups
        path = re.sub(r"\(\?P<(\w+)>[^)]+\)", r"{\1}", path)  # Alternative format
        path = re.sub(r"\([^)]+\)", r"{param}", path)  # Convert unnamed groups
        path = re.sub(r"\\/", "/", path)  # Unescape slashes
        path = re.sub(r"/+", "/", path)  # Remove duplicate slashes

        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        return path

    def _extract_path_parameters(self, path: str) -> List[Dict[str, Any]]:
        """Extract parameters from path pattern"""
        parameters = []

        # Find all {param} patterns
        param_pattern = re.compile(r"\{(\w+)\}")
        for match in param_pattern.finditer(path):
            param_name = match.group(1)
            parameters.append(
                {
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string" if param_name != "id" else "integer"},
                }
            )

        return parameters

    @lru_cache(maxsize=256)
    def _is_api_endpoint(self, path: str) -> bool:
        """Check if endpoint is an API endpoint"""
        api_patterns = ("/api/", "/rest/", "/v1/", "/v2/", "/v3/", "/graphql/", "/ws/")
        return any(pattern in path.lower() for pattern in api_patterns)

    @lru_cache(maxsize=256)
    def _is_rest_endpoint(self, path: str) -> bool:
        """Check if endpoint follows REST conventions with improved regex"""
        if not self._is_api_endpoint(path):
            return False

        # Improved REST patterns with proper escaping
        rest_patterns = [
            r"^/api/[\w\-]+/?$",  # Collection endpoint
            r"^/api/[\w\-]+/\{[\w]+\}/?$",  # Item endpoint
            r"^/api/v\d+/[\w\-]+/?$",  # Versioned collection
            r"^/api/v\d+/[\w\-]+/\{[\w]+\}/?$",  # Versioned item
            r"^/api/[\w\-]+/\{[\w]+\}/[\w\-]+/?$",  # Nested resource
        ]

        return any(re.match(pattern, path) for pattern in rest_patterns)

    def _analyze_api_coverage(self) -> None:
        """Analyze API coverage for each model"""
        for model_name, model_data in self.models.items():
            coverage = ModelEndpointCoverage(
                model_name=model_name,
                expected_endpoints=model_data["expected_endpoints"],
                found_endpoints=[],
                missing_endpoints=[],
            )

            # Extract base name for matching
            base_name = self._extract_model_base_name(model_name)
            plural_name = self._pluralize(base_name)

            # Find matching endpoints
            for endpoint in self.endpoints:
                if self._endpoint_matches_model(endpoint, plural_name, base_name):
                    coverage.found_endpoints.append(endpoint)

            # Find missing endpoints
            for expected in model_data["expected_endpoints"]:
                found = False
                for actual in coverage.found_endpoints:
                    if expected["method"] in [
                        m.value for m in actual.methods
                    ] and self._paths_match(expected["path"], actual.path):
                        found = True
                        break

                if not found:
                    coverage.missing_endpoints.append(expected)

            coverage.calculate_coverage()
            self.coverage[model_name] = coverage

    def _endpoint_matches_model(
        self, endpoint: EndpointInfo, plural_name: str, base_name: str
    ) -> bool:
        """Check if endpoint matches a model with improved matching"""
        path = endpoint.path.lower()

        # Check for exact plural match
        if f"/{plural_name}/" in path or path.endswith(f"/{plural_name}"):
            return True

        # Check for base name match (singular)
        if f"/{base_name}/" in path or path.endswith(f"/{base_name}"):
            return True

        return False

    def _paths_match(self, expected: str, actual: str) -> bool:
        """Compare expected and actual paths with parameter substitution"""
        # Normalize paths
        expected = expected.replace("{id}", "{param}").replace("{pk}", "{param}")
        actual = actual.replace("{id}", "{param}").replace("{pk}", "{param}")

        # Replace any parameter with generic placeholder
        expected = re.sub(r"\{[^}]+\}", "{param}", expected)
        actual = re.sub(r"\{[^}]+\}", "{param}", actual)

        return expected == actual

    def generate_report(self) -> APIAnalysisReport:
        """Generate comprehensive analysis report"""
        return APIAnalysisReport(
            generated_at=datetime.now(),
            app_name=self.app_name,
            total_models=len(self.models),
            total_endpoints=len(self.endpoints),
            api_endpoints=sum(1 for e in self.endpoints if e.is_api),
            rest_endpoints=sum(1 for e in self.endpoints if e.is_rest),
            async_endpoints=sum(1 for e in self.endpoints if e.is_async),
            models=self.models,
            endpoints=self.endpoints,
            coverage=self.coverage,
            performance_metrics=self.performance_metrics,
        )

    def generate_openapi_spec(self, title: str = None, version: str = "1.0.0") -> Dict[str, Any]:
        """Generate OpenAPI 3.1 specification"""
        if not title:
            title = f"{self.app_name.title()} API"

        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": title,
                "version": version,
                "description": f"REST API for {self.app_name}",
                "contact": {"name": "API Support", "email": "api@example.com"},
            },
            "servers": [{"url": "http://localhost:8000", "description": "Development server"}],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
                },
            },
            "security": [{"bearerAuth": []}],
        }

        # Group endpoints by path
        paths_dict = defaultdict(dict)

        for endpoint in self.endpoints:
            if not endpoint.is_api:
                continue

            path = endpoint.path

            for method in endpoint.methods:
                operation = {
                    "operationId": f"{endpoint.operation_id}_{method.value.lower()}",
                    "summary": (
                        endpoint.docstring.split("\n")[0]
                        if endpoint.docstring
                        else f"{method.value} {path}"
                    ),
                    "tags": [endpoint.namespace] if endpoint.namespace else ["default"],
                    "parameters": endpoint.parameters,
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Bad request"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not found"},
                    },
                }

                # Add request body for POST/PUT/PATCH
                if method.value in ["POST", "PUT", "PATCH"]:
                    operation["requestBody"] = {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }

                paths_dict[path][method.value.lower()] = operation

        spec["paths"] = dict(paths_dict)

        # Add model schemas
        for model_name, model_data in self.models.items():
            schema = {"type": "object", "properties": {}, "required": []}

            for field in model_data["fields"]:
                field_schema = {"type": "string"}  # Default

                if field["type"] in ["IntegerField", "AutoField", "BigAutoField"]:
                    field_schema = {"type": "integer"}
                elif field["type"] in ["FloatField", "DecimalField"]:
                    field_schema = {"type": "number"}
                elif field["type"] == "BooleanField":
                    field_schema = {"type": "boolean"}
                elif field["type"] in ["DateTimeField", "DateField"]:
                    field_schema = {"type": "string", "format": "date-time"}
                elif field["type"] == "EmailField":
                    field_schema = {"type": "string", "format": "email"}

                schema["properties"][field["name"]] = field_schema

                if field["required"]:
                    schema["required"].append(field["name"])

            spec["components"]["schemas"][model_name] = schema

        return spec

    def validate_openapi_spec(self, spec: Union[Dict[str, Any], str]) -> Tuple[bool, List[str]]:
        """Validate OpenAPI specification"""
        errors = []

        if not OPENAPI_VALIDATOR_AVAILABLE:
            errors.append(
                "openapi-spec-validator not installed. Run: pip install openapi-spec-validator"
            )
            return False, errors

        try:
            if isinstance(spec, str):
                # Load from file
                with open(spec, "r") as f:
                    spec_data = yaml.safe_load(f) if spec.endswith(".yaml") else json.load(f)
            else:
                spec_data = spec

            # Validate
            validate_spec(spec_data)
            return True, []

        except Exception as e:
            errors.append(str(e))
            return False, errors

    def export_report(self, output_file: str, format: str = "yaml") -> None:
        """Export analysis report to file"""
        report = self.generate_report()

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                # Convert dataclasses to dict
                report_dict = asdict(report)
                # Convert EndpointInfo objects
                report_dict["endpoints"] = [asdict(e) for e in report.endpoints]
                # Convert HTTPMethod enums
                for endpoint in report_dict["endpoints"]:
                    endpoint["methods"] = [m.value for m in endpoint["methods"]]

                json.dump(report_dict, f, indent=2, default=str)

        elif format.lower() == "yaml":
            with open(output_path, "w", encoding="utf-8") as f:
                report_dict = asdict(report)
                report_dict["endpoints"] = [asdict(e) for e in report.endpoints]
                for endpoint in report_dict["endpoints"]:
                    endpoint["methods"] = [m.value for m in endpoint["methods"]]

                yaml.dump(report_dict, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Report exported to {output_path}")

        if self.console:
            self.console.print(f"[green]✔ Report exported to {output_path}[/green]")

    def print_analysis(self) -> None:
        """Print comprehensive analysis to console"""
        report = self.generate_report()

        if self.console and RICH_AVAILABLE:
            # Summary panel
            summary_table = Table(title="📊 API Analysis Summary")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")

            summary_data = [
                ("Total Models", str(report.total_models)),
                ("Total Endpoints", str(report.total_endpoints)),
                ("API Endpoints", str(report.api_endpoints)),
                ("REST Endpoints", str(report.rest_endpoints)),
                ("Async Endpoints", str(report.async_endpoints)),
                (
                    "Models with CRUDConfig",
                    str(sum(1 for m in self.models.values() if m["has_crud_config"])),
                ),
            ]

            for metric, value in summary_data:
                summary_table.add_row(metric, value)

            self.console.print(summary_table)

            # Coverage table
            coverage_table = Table(title="🎯 API Coverage by Model")
            coverage_table.add_column("Model", style="cyan")
            coverage_table.add_column("Coverage", style="green")
            coverage_table.add_column("Found/Expected", style="yellow")
            coverage_table.add_column("Status", style="bold")

            for model_name, coverage in self.coverage.items():
                if coverage.expected_endpoints:
                    status = "✅" if coverage.coverage_percent == 100 else "⚠️"
                    coverage_table.add_row(
                        model_name,
                        f"{coverage.coverage_percent:.1f}%",
                        f"{len(coverage.found_endpoints)}/{len(coverage.expected_endpoints)}",
                        status,
                    )

            self.console.print(coverage_table)

            # Missing endpoints
            if any(c.missing_endpoints for c in self.coverage.values()):
                missing_panel = Panel(
                    self._format_missing_endpoints(),
                    title="🚨 Missing Endpoints",
                    title_align="left",
                    border_style="red",
                )
                self.console.print(missing_panel)

            # Performance metrics
            if self.performance_metrics:
                perf_table = Table(title="⚡ Performance Metrics")
                perf_table.add_column("Metric", style="cyan")
                perf_table.add_column("Time (seconds)", style="green")

                for metric, time_val in self.performance_metrics.items():
                    perf_table.add_row(metric, f"{time_val:.3f}")

                self.console.print(perf_table)

        else:
            # Fallback to simple print
            print("\n📊 API Analysis Report")
            print(f"{'='*50}")
            print(f"App: {report.app_name}")
            print(f"Generated: {report.generated_at}")
            print("\n📈 Summary:")
            print(f"Total Models: {report.total_models}")
            print(f"Total Endpoints: {report.total_endpoints}")
            print(f"API Endpoints: {report.api_endpoints}")
            print(f"REST Endpoints: {report.rest_endpoints}")
            print(f"Async Endpoints: {report.async_endpoints}")

            print("\n🎯 API Coverage by Model:")
            for model_name, coverage in self.coverage.items():
                if coverage.expected_endpoints:
                    print(
                        f"{model_name}: {coverage.coverage_percent:.1f}% ({len(coverage.found_endpoints)}/{len(coverage.expected_endpoints)})"
                    )

            if any(c.missing_endpoints for c in self.coverage.values()):
                print("\n🚨 Missing Endpoints:")
                for model_name, coverage in self.coverage.items():
                    if coverage.missing_endpoints:
                        print(f"\n{model_name}:")
                        for missing in coverage.missing_endpoints:
                            print(
                                f"  {missing['method']} {missing['path']} - {missing['description']}"
                            )

    def _format_missing_endpoints(self) -> str:
        """Format missing endpoints for display"""
        lines = []
        for model_name, coverage in self.coverage.items():
            if coverage.missing_endpoints:
                lines.append(f"[bold]{model_name}:[/bold]")
                for missing in coverage.missing_endpoints:
                    lines.append(
                        f"  • {missing['method']} {missing['path']} - {missing['description']}"
                    )
                lines.append("")
        return "\n".join(lines)

    def get_endpoint_by_path(self, path: str) -> Optional[EndpointInfo]:
        """Find endpoint by path"""
        for endpoint in self.endpoints:
            if endpoint.path == path:
                return endpoint
        return None

    def get_endpoints_by_model(self, model_name: str) -> List[EndpointInfo]:
        """Get all endpoints for a specific model"""
        coverage = self.coverage.get(model_name)
        if coverage:
            return coverage.found_endpoints
        return []


# Null context manager for when Rich is not available


@contextmanager
def nullcontext():
    """Function description."""
    yield


def main():
    """Enhanced CLI with more options"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Advanced API Endpoint Checker for Django",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s check --app myapp
  %(prog)s report --app myapp --output report.json
  %(prog)s openapi --app myapp --output openapi.yaml
  %(prog)s validate --app myapp --spec openapi.yaml
        """,
    )

    parser.add_argument(
        "command", choices=["check", "report", "openapi", "validate"], help="Command to execute"
    )
    parser.add_argument("--app", default="bfagent", help="Django app name (default: bfagent)")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument(
        "--format", choices=["json", "yaml"], default="yaml", help="Output format (default: yaml)"
    )
    parser.add_argument("--include-admin", action="store_true", help="Include admin endpoints")
    parser.add_argument("--profile", action="store_true", help="Profile performance")
    parser.add_argument("--spec", help="OpenAPI spec file to validate")
    parser.add_argument("--title", help="API title for OpenAPI spec")
    parser.add_argument("--version", default="1.0.0", help="API version for OpenAPI spec")

    args = parser.parse_args()

    # Create checker instance
    checker = APIEndpointChecker(
        app_name=args.app, include_admin=args.include_admin, profile_performance=args.profile
    )

    try:
        # Analyze
        report = checker.analyze()

        if args.command == "check":
            # Print analysis
            checker.print_analysis()

        elif args.command == "report":
            # Export report
            if args.output:
                checker.export_report(args.output, format=args.format)
            else:
                checker.print_analysis()

        elif args.command == "openapi":
            # Generate OpenAPI spec
            spec = checker.generate_openapi_spec(title=args.title, version=args.version)

            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w") as f:
                    if args.format == "json":
                        json.dump(spec, f, indent=2)
                    else:
                        yaml.dump(spec, f, default_flow_style=False)

                if checker.console:
                    checker.console.print(
                        f"[green]✔ OpenAPI spec exported to {output_path}[/green]"
                    )
                else:
                    print(f"✔ OpenAPI spec exported to {output_path}")
            else:
                # Print to stdout
                if args.format == "json":
                    print(json.dumps(spec, indent=2))
                else:
                    print(yaml.dump(spec, default_flow_style=False))

        elif args.command == "validate":
            # Validate OpenAPI spec
            if args.spec:
                # Validate existing spec
                is_valid, errors = checker.validate_openapi_spec(args.spec)

                if is_valid:
                    if checker.console:
                        checker.console.print("[green]✔ OpenAPI spec is valid![/green]")
                    else:
                        print("✔ OpenAPI spec is valid!")
                else:
                    if checker.console:
                        checker.console.print("[red]✗ OpenAPI spec validation errors:[/red]")
                        for error in errors:
                            checker.console.print(f"  • {error}")
                    else:
                        print("✗ OpenAPI spec validation errors:")
                        for error in errors:
                            print(f"  • {error}")
            else:
                # Generate and validate
                spec = checker.generate_openapi_spec()
                is_valid, errors = checker.validate_openapi_spec(spec)

                if is_valid:
                    if checker.console:
                        checker.console.print("[green]✔ Generated OpenAPI spec is valid![/green]")
                    else:
                        print("✔ Generated OpenAPI spec is valid!")
                else:
                    if checker.console:
                        checker.console.print("[red]✗ Validation errors in generated spec:[/red]")
                        for error in errors:
                            checker.console.print(f"  • {error}")
                    else:
                        print("✗ Validation errors in generated spec:")
                        for error in errors:
                            print(f"  • {error}")

    except Exception as e:
        logger.error(f"Error: {e}")
        if checker.console:
            checker.console.print(f"[red]✗ Error: {e}[/red]")
        else:
            print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
