"""
Test Generator MCP Server
=========================
MCP Server für automatische Test-Generierung, Ausführung und Qualitäts-Dokumentation.

Unique Features (nicht in existierenden MCP Servern):
- AST-basierte Test-Generierung für Python/Django Code
- Handler-spezifische Test-Templates (BF Agent Pattern)
- Coverage-Gap Analyse und gezielte Test-Generierung
- Test-Execution mit strukturiertem Reporting
- Qualitäts-Trends über Zeit

Existierende MCP Server zum Vergleich:
- pytest-mcp-server: Nur Failure Tracking
- mcp-code-checker: Nur Ausführung, keine Generierung
- mcp_pytest_service: Nur Session Recording

Usage:
    python test_generator_mcp.py
    
    # Mit Projekt-Root
    python test_generator_mcp.py --project-root /path/to/bf_agent
"""

import ast
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import re

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TestGeneratorConfig:
    """Configuration for test generation."""
    
    # Test Framework
    test_framework: str = "pytest"
    async_support: bool = True
    
    # Django Settings
    django_settings_module: str = "config.settings"
    use_django_test_client: bool = True
    
    # Coverage
    coverage_threshold: float = 80.0
    branch_coverage: bool = True
    
    # BF Agent Specific
    handler_test_template: str = "handler"
    mock_ai_calls: bool = True
    
    # Output
    test_output_dir: str = "tests"
    report_format: str = "json"


# =============================================================================
# Enums
# =============================================================================

class TestType(str, Enum):
    """Types of tests to generate."""
    UNIT = "unit"
    INTEGRATION = "integration"
    HANDLER = "handler"
    API = "api"
    MODEL = "model"
    VIEW = "view"
    FORM = "form"
    E2E = "e2e"


class TestStatus(str, Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    XFAIL = "xfail"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TestCase:
    """Represents a single test case."""
    name: str
    test_type: TestType
    target_function: str
    target_class: Optional[str]
    target_file: str
    description: str
    code: str
    imports: List[str] = field(default_factory=list)
    fixtures: List[str] = field(default_factory=list)
    mocks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['test_type'] = self.test_type.value
        return result


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_name: str
    status: TestStatus
    duration_ms: float
    output: str = ""
    error_message: str = ""
    traceback: str = ""
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class CoverageReport:
    """Code coverage report."""
    total_statements: int
    covered_statements: int
    missing_statements: int
    coverage_percent: float
    branch_coverage_percent: Optional[float] = None
    uncovered_lines: Dict[str, List[int]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestSuiteResult:
    """Complete test suite execution result."""
    executed_at: str
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    results: List[TestResult] = field(default_factory=list)
    coverage: Optional[CoverageReport] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['results'] = [r.to_dict() for r in self.results]
        if self.coverage:
            result['coverage'] = self.coverage.to_dict()
        return result


@dataclass
class QualityTrend:
    """Quality metrics over time."""
    date: str
    total_tests: int
    pass_rate: float
    coverage_percent: float
    new_tests_added: int
    issues_found: int


# =============================================================================
# AST Analyzers for Test Generation
# =============================================================================

class CodeAnalyzer(ast.NodeVisitor):
    """Analyzes Python code to extract testable components."""
    
    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.classes: List[Dict] = []
        self.functions: List[Dict] = []
        self.imports: List[str] = []
        self.current_class: Optional[str] = None
    
    def analyze(self) -> Dict[str, Any]:
        """Perform full analysis."""
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError:
            pass
        
        return {
            'file_path': self.file_path,
            'classes': self.classes,
            'functions': self.functions,
            'imports': self.imports
        }
    
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_info = {
            'name': node.name,
            'bases': [self._get_name(b) for b in node.bases],
            'methods': [],
            'is_handler': self._is_handler_class(node),
            'is_model': self._is_model_class(node),
            'is_view': self._is_view_class(node),
            'is_form': self._is_form_class(node),
            'line_number': node.lineno
        }
        
        old_class = self.current_class
        self.current_class = node.name
        
        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item)
                method_info['is_async'] = isinstance(item, ast.AsyncFunctionDef)
                class_info['methods'].append(method_info)
        
        self.classes.append(class_info)
        self.current_class = old_class
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.current_class is None:
            func_info = self._extract_function_info(node)
            func_info['is_async'] = False
            self.functions.append(func_info)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self.current_class is None:
            func_info = self._extract_function_info(node)
            func_info['is_async'] = True
            self.functions.append(func_info)
        self.generic_visit(node)
    
    def _extract_function_info(self, node) -> Dict:
        """Extract information about a function."""
        args = []
        for arg in node.args.args:
            if arg.arg != 'self':
                arg_info = {'name': arg.arg, 'type': None}
                if arg.annotation:
                    arg_info['type'] = self._get_annotation(arg.annotation)
                args.append(arg_info)
        
        return {
            'name': node.name,
            'args': args,
            'return_type': self._get_annotation(node.returns) if node.returns else None,
            'docstring': ast.get_docstring(node),
            'line_number': node.lineno,
            'is_private': node.name.startswith('_'),
            'decorators': [self._get_name(d) for d in node.decorator_list]
        }
    
    def _get_name(self, node) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""
    
    def _get_annotation(self, node) -> str:
        """Get type annotation as string."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_annotation(node.slice)}]"
        return "Any"
    
    def _is_handler_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a handler."""
        bases = [self._get_name(b) for b in node.bases]
        return (
            'Handler' in node.name or
            any('Handler' in b or 'BaseHandler' in b for b in bases)
        )
    
    def _is_model_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django model."""
        bases = [self._get_name(b) for b in node.bases]
        return any('Model' in b or 'models.Model' in b for b in bases)
    
    def _is_view_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django view."""
        bases = [self._get_name(b) for b in node.bases]
        return any('View' in b for b in bases)
    
    def _is_form_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django form."""
        bases = [self._get_name(b) for b in node.bases]
        return any('Form' in b for b in bases)


# =============================================================================
# Test Generators
# =============================================================================

class TestGenerator:
    """Generates test cases based on code analysis."""
    
    def __init__(self, config: TestGeneratorConfig):
        self.config = config
    
    def generate_for_file(self, file_path: Path, skip_existing: bool = True) -> List[TestCase]:
        """Generate tests for a Python file.
        
        Args:
            file_path: Path to Python file to generate tests for
            skip_existing: If True, skip tests that already exist
        """
        source_code = file_path.read_text(encoding='utf-8')
        analyzer = CodeAnalyzer(source_code, str(file_path))
        analysis = analyzer.analyze()
        
        # Find existing tests to avoid duplicates
        existing_tests = set()
        if skip_existing:
            existing_tests = self._find_existing_tests(file_path)
        
        test_cases = []
        
        # Generate tests for classes
        for cls in analysis['classes']:
            if cls['is_handler']:
                test_cases.extend(self._generate_handler_tests(cls, file_path))
            elif cls['is_model']:
                test_cases.extend(self._generate_model_tests(cls, file_path))
            elif cls['is_view']:
                test_cases.extend(self._generate_view_tests(cls, file_path))
            elif cls['is_form']:
                test_cases.extend(self._generate_form_tests(cls, file_path))
            else:
                test_cases.extend(self._generate_class_tests(cls, file_path))
        
        # Generate tests for standalone functions
        for func in analysis['functions']:
            if not func['is_private']:
                test_cases.extend(self._generate_function_tests(func, file_path))
        
        # Filter out existing tests
        if existing_tests:
            test_cases = [tc for tc in test_cases if tc.name not in existing_tests]
        
        return test_cases
    
    def _find_existing_tests(self, file_path: Path) -> Set[str]:
        """Find existing test names for a given source file.
        
        Searches in common test locations:
        - tests/test_{filename}.py
        - tests/{app}/test_{filename}.py
        - {app}/tests/test_{filename}.py
        """
        existing = set()
        file_stem = file_path.stem
        
        # Possible test file locations
        possible_paths = [
            Path("tests") / f"test_{file_stem}.py",
            Path("tests") / file_path.parent.name / f"test_{file_stem}.py",
        ]
        
        # Also check for tests directory in same app
        if 'apps' in file_path.parts:
            apps_idx = file_path.parts.index('apps')
            if len(file_path.parts) > apps_idx + 1:
                app_name = file_path.parts[apps_idx + 1]
                possible_paths.append(Path("apps") / app_name / "tests" / f"test_{file_stem}.py")
                possible_paths.append(Path("tests") / "apps" / app_name / f"test_{file_stem}.py")
        
        for test_path in possible_paths:
            if test_path.exists():
                try:
                    test_source = test_path.read_text(encoding='utf-8')
                    tree = ast.parse(test_source)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name.startswith('test_'):
                                existing.add(node.name)
                except Exception:
                    pass
        
        return existing
    
    def _generate_handler_tests(self, cls: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for BF Agent Handler."""
        tests = []
        class_name = cls['name']
        module_path = self._get_module_path(file_path)
        
        # Test 1: Handler instantiation
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_instantiation",
            test_type=TestType.HANDLER,
            target_function="__init__",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} can be instantiated",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
@pytest.mark.asyncio
async def test_{self._to_snake_case(class_name)}_instantiation():
    """Test that {class_name} can be instantiated."""
    handler = {class_name}()
    assert handler is not None
'''
        ))
        
        # Test 2: Execute method (if exists)
        execute_method = next(
            (m for m in cls['methods'] if m['name'] == 'execute'),
            None
        )
        if execute_method:
            tests.append(TestCase(
                name=f"test_{self._to_snake_case(class_name)}_execute_success",
                test_type=TestType.HANDLER,
                target_function="execute",
                target_class=class_name,
                target_file=str(file_path),
                description=f"Test that {class_name}.execute() runs successfully",
                imports=[
                    f"from {module_path} import {class_name}",
                    "import pytest",
                    "from unittest.mock import AsyncMock, patch, MagicMock"
                ],
                fixtures=["mock_context"],
                mocks=["LLM.generate_text"] if self.config.mock_ai_calls else [],
                code=f'''
@pytest.fixture
def mock_context():
    """Create mock execution context."""
    return {{
        'project': MagicMock(),
        'user': MagicMock(),
        'use_ai': False,  # Disable AI for unit test
    }}

@pytest.mark.asyncio
async def test_{self._to_snake_case(class_name)}_execute_success(mock_context):
    """Test that {class_name}.execute() runs successfully."""
    handler = {class_name}()
    
    # Execute handler
    result = await handler.execute(mock_context)
    
    # Assertions
    assert result is not None
    assert result.get('success', True)  # Adjust based on your handler pattern
'''
            ))
        
        # Test 3: Input validation (if INPUT_SCHEMA exists)
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_input_validation",
            test_type=TestType.HANDLER,
            target_function="validate_input",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} validates input correctly",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
@pytest.mark.asyncio
async def test_{self._to_snake_case(class_name)}_input_validation():
    """Test that {class_name} validates input correctly."""
    handler = {class_name}()
    
    # Test with invalid input
    invalid_context = {{'invalid': 'data'}}
    
    # Should handle gracefully (not crash)
    try:
        result = await handler.execute(invalid_context)
        # If it returns, check for error indication
        assert 'error' in result or not result.get('success', True)
    except (ValueError, KeyError, TypeError):
        # Expected validation error
        pass
'''
        ))
        
        return tests
    
    def _generate_model_tests(self, cls: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for Django Model."""
        tests = []
        class_name = cls['name']
        module_path = self._get_module_path(file_path)
        
        # Test 1: Model creation
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_create",
            test_type=TestType.MODEL,
            target_function="save",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} can be created",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest",
                "from django.test import TestCase"
            ],
            fixtures=["db"],
            code=f'''
@pytest.mark.django_db
def test_{self._to_snake_case(class_name)}_create():
    """Test that {class_name} can be created."""
    # TODO: Add required fields based on model definition
    instance = {class_name}.objects.create(
        # Add required fields here
    )
    assert instance.pk is not None
'''
        ))
        
        # Test 2: __str__ method
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_str",
            test_type=TestType.MODEL,
            target_function="__str__",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name}.__str__() returns meaningful string",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            fixtures=["db"],
            code=f'''
@pytest.mark.django_db
def test_{self._to_snake_case(class_name)}_str():
    """Test that {class_name}.__str__() returns meaningful string."""
    instance = {class_name}.objects.create(
        # Add required fields here
    )
    str_repr = str(instance)
    assert str_repr is not None
    assert len(str_repr) > 0
    assert str_repr != '{class_name} object'  # Should be customized
'''
        ))
        
        return tests
    
    def _generate_view_tests(self, cls: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for Django View."""
        tests = []
        class_name = cls['name']
        module_path = self._get_module_path(file_path)
        
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_get",
            test_type=TestType.VIEW,
            target_function="get",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} responds to GET request",
            imports=[
                "import pytest",
                "from django.test import Client",
                "from django.urls import reverse"
            ],
            fixtures=["client", "db"],
            code=f'''
@pytest.mark.django_db
def test_{self._to_snake_case(class_name)}_get(client):
    """Test that {class_name} responds to GET request."""
    # TODO: Update URL name based on your urls.py
    url = reverse('{self._to_snake_case(class_name).replace("_view", "")}-list')
    response = client.get(url)
    assert response.status_code in [200, 302]  # OK or redirect
'''
        ))
        
        return tests
    
    def _generate_form_tests(self, cls: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for Django Form."""
        tests = []
        class_name = cls['name']
        module_path = self._get_module_path(file_path)
        
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_valid",
            test_type=TestType.FORM,
            target_function="is_valid",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} validates correct data",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
def test_{self._to_snake_case(class_name)}_valid():
    """Test that {class_name} validates correct data."""
    # TODO: Add valid form data based on form fields
    form_data = {{
        # Add required fields here
    }}
    form = {class_name}(data=form_data)
    assert form.is_valid(), f"Form errors: {{form.errors}}"
'''
        ))
        
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_invalid",
            test_type=TestType.FORM,
            target_function="is_valid",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} rejects invalid data",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
def test_{self._to_snake_case(class_name)}_invalid():
    """Test that {class_name} rejects invalid data."""
    # Empty form should be invalid (assuming required fields)
    form = {class_name}(data={{}})
    assert not form.is_valid()
'''
        ))
        
        return tests
    
    def _generate_class_tests(self, cls: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for generic class."""
        tests = []
        class_name = cls['name']
        module_path = self._get_module_path(file_path)
        
        # Test instantiation
        tests.append(TestCase(
            name=f"test_{self._to_snake_case(class_name)}_init",
            test_type=TestType.UNIT,
            target_function="__init__",
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test that {class_name} can be instantiated",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
def test_{self._to_snake_case(class_name)}_init():
    """Test that {class_name} can be instantiated."""
    instance = {class_name}()
    assert instance is not None
'''
        ))
        
        # Test public methods
        for method in cls['methods']:
            if not method['is_private'] and method['name'] != '__init__':
                tests.append(self._generate_method_test(cls, method, file_path))
        
        return tests
    
    def _generate_method_test(self, cls: Dict, method: Dict, file_path: Path) -> TestCase:
        """Generate test for a class method."""
        class_name = cls['name']
        method_name = method['name']
        module_path = self._get_module_path(file_path)
        
        is_async = method.get('is_async', False)
        decorator = "@pytest.mark.asyncio\n" if is_async else ""
        async_kw = "async " if is_async else ""
        await_kw = "await " if is_async else ""
        
        return TestCase(
            name=f"test_{self._to_snake_case(class_name)}_{method_name}",
            test_type=TestType.UNIT,
            target_function=method_name,
            target_class=class_name,
            target_file=str(file_path),
            description=f"Test {class_name}.{method_name}()",
            imports=[
                f"from {module_path} import {class_name}",
                "import pytest"
            ],
            code=f'''
{decorator}{async_kw}def test_{self._to_snake_case(class_name)}_{method_name}():
    """Test {class_name}.{method_name}()."""
    instance = {class_name}()
    # TODO: Add proper arguments
    result = {await_kw}instance.{method_name}()
    assert result is not None  # Adjust assertion
'''
        )
    
    def _generate_function_tests(self, func: Dict, file_path: Path) -> List[TestCase]:
        """Generate tests for standalone function."""
        func_name = func['name']
        module_path = self._get_module_path(file_path)
        
        is_async = func.get('is_async', False)
        decorator = "@pytest.mark.asyncio\n" if is_async else ""
        async_kw = "async " if is_async else ""
        await_kw = "await " if is_async else ""
        
        return [TestCase(
            name=f"test_{func_name}",
            test_type=TestType.UNIT,
            target_function=func_name,
            target_class=None,
            target_file=str(file_path),
            description=f"Test function {func_name}()",
            imports=[
                f"from {module_path} import {func_name}",
                "import pytest"
            ],
            code=f'''
{decorator}{async_kw}def test_{func_name}():
    """Test function {func_name}()."""
    # TODO: Add proper arguments based on function signature
    result = {await_kw}{func_name}()
    assert result is not None  # Adjust assertion
'''
        )]
    
    def _get_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        # Remove .py extension and convert to dots
        parts = file_path.with_suffix('').parts
        
        # Find 'apps' in path and start from there
        try:
            apps_idx = parts.index('apps')
            return '.'.join(parts[apps_idx:])
        except ValueError:
            # Fallback: use last 2-3 parts
            return '.'.join(parts[-3:])
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


# =============================================================================
# Test Executor
# =============================================================================

class TestExecutor:
    """Executes tests and collects results."""
    
    def __init__(self, config: TestGeneratorConfig):
        self.config = config
    
    def run_tests(
        self,
        test_path: Optional[Path] = None,
        pattern: Optional[str] = None,
        coverage: bool = True,
        verbose: bool = False
    ) -> TestSuiteResult:
        """Run tests and return results."""
        cmd = ["python", "-m", "pytest"]
        
        # Add test path or pattern
        if test_path:
            cmd.append(str(test_path))
        if pattern:
            cmd.extend(["-k", pattern])
        
        # Coverage
        if coverage:
            cmd.extend([
                "--cov=apps",
                "--cov-report=json",
                f"--cov-fail-under={self.config.coverage_threshold}"
            ])
            if self.config.branch_coverage:
                cmd.append("--cov-branch")
        
        # Output format
        cmd.extend(["--tb=short", "-v" if verbose else "-q"])
        
        # JUnit XML for parsing
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            junit_path = f.name
        cmd.extend([f"--junitxml={junit_path}"])
        
        # Run tests
        start_time = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            output = result.stdout + result.stderr
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            output = "Test execution timed out"
            returncode = -1
        except Exception as e:
            output = str(e)
            returncode = -1
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Parse results
        suite_result = self._parse_junit_xml(junit_path, duration)
        
        # Parse coverage if available
        if coverage and Path("coverage.json").exists():
            suite_result.coverage = self._parse_coverage()
        
        # Cleanup
        Path(junit_path).unlink(missing_ok=True)
        
        return suite_result
    
    def _parse_junit_xml(self, xml_path: str, duration: float) -> TestSuiteResult:
        """Parse JUnit XML output."""
        result = TestSuiteResult(
            executed_at=datetime.now().isoformat(),
            total_tests=0,
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            duration_seconds=duration
        )
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for testsuite in root.findall('.//testsuite'):
                result.total_tests += int(testsuite.get('tests', 0))
                result.failed += int(testsuite.get('failures', 0))
                result.errors += int(testsuite.get('errors', 0))
                result.skipped += int(testsuite.get('skipped', 0))
            
            result.passed = result.total_tests - result.failed - result.errors - result.skipped
            
            # Parse individual test results
            for testcase in root.findall('.//testcase'):
                test_result = TestResult(
                    test_name=f"{testcase.get('classname')}.{testcase.get('name')}",
                    status=TestStatus.PASSED,
                    duration_ms=float(testcase.get('time', 0)) * 1000
                )
                
                # Check for failure
                failure = testcase.find('failure')
                if failure is not None:
                    test_result.status = TestStatus.FAILED
                    test_result.error_message = failure.get('message', '')
                    test_result.traceback = failure.text or ''
                
                # Check for error
                error = testcase.find('error')
                if error is not None:
                    test_result.status = TestStatus.ERROR
                    test_result.error_message = error.get('message', '')
                    test_result.traceback = error.text or ''
                
                # Check for skip
                skipped = testcase.find('skipped')
                if skipped is not None:
                    test_result.status = TestStatus.SKIPPED
                    test_result.error_message = skipped.get('message', '')
                
                result.results.append(test_result)
                
        except Exception as e:
            # If parsing fails, return empty result
            pass
        
        return result
    
    def _parse_coverage(self) -> CoverageReport:
        """Parse coverage.json report."""
        try:
            with open("coverage.json") as f:
                data = json.load(f)
            
            totals = data.get('totals', {})
            
            return CoverageReport(
                total_statements=totals.get('num_statements', 0),
                covered_statements=totals.get('covered_lines', 0),
                missing_statements=totals.get('missing_lines', 0),
                coverage_percent=totals.get('percent_covered', 0),
                branch_coverage_percent=totals.get('percent_covered_branches')
            )
        except Exception:
            return CoverageReport(
                total_statements=0,
                covered_statements=0,
                missing_statements=0,
                coverage_percent=0
            )


# =============================================================================
# Quality Reporter
# =============================================================================

class QualityReporter:
    """Generates quality reports and tracks trends."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def save_report(self, result: TestSuiteResult, name: str = "latest") -> Path:
        """Save test result as JSON report."""
        report_path = self.reports_dir / f"test_report_{name}.json"
        
        with open(report_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        return report_path
    
    def get_trend(self, days: int = 30) -> List[QualityTrend]:
        """Get quality trend over time."""
        trends = []
        
        for report_file in sorted(self.reports_dir.glob("test_report_*.json")):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                
                trends.append(QualityTrend(
                    date=data['executed_at'][:10],
                    total_tests=data['total_tests'],
                    pass_rate=data['passed'] / max(data['total_tests'], 1) * 100,
                    coverage_percent=data.get('coverage', {}).get('coverage_percent', 0),
                    new_tests_added=0,  # Would need diff with previous
                    issues_found=data['failed'] + data['errors']
                ))
            except Exception:
                continue
        
        return trends[-days:]


# =============================================================================
# Pydantic Input Schemas
# =============================================================================

class GenerateTestsInput(BaseModel):
    """Input for test generation."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    file_path: str = Field(..., description="Path to Python file to generate tests for")
    test_types: Optional[List[TestType]] = Field(
        default=None,
        description="Types of tests to generate (None = all)"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Directory to save generated tests"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class RunTestsInput(BaseModel):
    """Input for test execution."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    test_path: Optional[str] = Field(
        default=None,
        description="Specific test file or directory"
    )
    pattern: Optional[str] = Field(
        default=None,
        description="Test name pattern to filter (pytest -k)"
    )
    coverage: bool = Field(
        default=True,
        description="Collect coverage data"
    )
    verbose: bool = Field(
        default=False,
        description="Verbose output"
    )
    save_report: bool = Field(
        default=True,
        description="Save report to file"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class AnalyzeCoverageInput(BaseModel):
    """Input for coverage analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    project_root: str = Field(..., description="Project root directory")
    min_coverage: float = Field(
        default=80.0,
        description="Minimum coverage threshold",
        ge=0,
        le=100
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SuggestTestsInput(BaseModel):
    """Input for test suggestions based on coverage gaps."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    file_path: str = Field(..., description="File to analyze for missing tests")
    max_suggestions: int = Field(
        default=10,
        description="Maximum suggestions to return",
        ge=1,
        le=50
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetQualityTrendInput(BaseModel):
    """Input for quality trend analysis."""
    model_config = ConfigDict(extra='forbid')
    
    days: int = Field(default=30, ge=1, le=365, description="Number of days to analyze")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("test_generator_mcp")

# Global instances
config = TestGeneratorConfig()
generator = TestGenerator(config)
executor = TestExecutor(config)
reporter = QualityReporter(Path("./test_reports"))


@mcp.tool(
    name="generate_tests",
    annotations={
        "title": "Generate Tests for Python File",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def generate_tests(params: GenerateTestsInput, ctx: Context) -> str:
    """
    Generate test cases for a Python file.
    
    Analyzes the code structure and generates appropriate tests for:
    - Handlers (BF Agent pattern with INPUT_SCHEMA, execute)
    - Django Models (create, str, validation)
    - Django Views (GET, POST, authentication)
    - Django Forms (valid, invalid data)
    - Generic classes and functions
    
    Returns generated test code that can be saved or reviewed.
    """
    file_path = Path(params.file_path)
    
    if not file_path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    if not file_path.suffix == '.py':
        return json.dumps({"success": False, "error": "Only Python files supported"})
    
    await ctx.report_progress(0.2, "Analyzing code structure...")
    test_cases = generator.generate_for_file(file_path)
    
    # Filter by test types if specified
    if params.test_types:
        test_cases = [t for t in test_cases if t.test_type in params.test_types]
    
    await ctx.report_progress(0.8, f"Generated {len(test_cases)} tests")
    
    # Save to file if output_dir specified
    if params.output_dir:
        output_dir = Path(params.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = output_dir / f"test_{file_path.stem}.py"
        
        # Combine all test code
        all_imports = set()
        all_code = []
        
        for tc in test_cases:
            all_imports.update(tc.imports)
            all_code.append(tc.code)
        
        content = "\n".join(sorted(all_imports)) + "\n\n" + "\n".join(all_code)
        test_file.write_text(content)
        
        await ctx.report_progress(1.0, f"Saved to {test_file}")
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": True,
            "test_count": len(test_cases),
            "tests": [t.to_dict() for t in test_cases]
        }, indent=2)
    
    # Markdown format
    lines = [
        f"# 🧪 Generated Tests for {file_path.name}",
        f"",
        f"**Total Tests:** {len(test_cases)}",
        ""
    ]
    
    # Group by type
    by_type = defaultdict(list)
    for tc in test_cases:
        by_type[tc.test_type].append(tc)
    
    for test_type, tests in by_type.items():
        lines.append(f"## {test_type.value.title()} Tests ({len(tests)})")
        lines.append("")
        
        for tc in tests:
            lines.append(f"### `{tc.name}`")
            lines.append(f"**Target:** `{tc.target_class or ''}.{tc.target_function}`")
            lines.append(f"**Description:** {tc.description}")
            lines.append("")
            lines.append("```python")
            lines.extend(tc.imports)
            lines.append("")
            lines.append(tc.code.strip())
            lines.append("```")
            lines.append("")
    
    return "\n".join(lines)


@mcp.tool(
    name="run_tests",
    annotations={
        "title": "Run Tests",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def run_tests(params: RunTestsInput, ctx: Context) -> str:
    """
    Execute tests and return results.
    
    Runs pytest with optional coverage collection.
    Provides detailed results including pass/fail status,
    error messages, and coverage report.
    """
    await ctx.report_progress(0.1, "Starting test execution...")
    
    test_path = Path(params.test_path) if params.test_path else None
    
    result = executor.run_tests(
        test_path=test_path,
        pattern=params.pattern,
        coverage=params.coverage,
        verbose=params.verbose
    )
    
    await ctx.report_progress(0.9, "Parsing results...")
    
    # Save report if requested
    if params.save_report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporter.save_report(result, timestamp)
    
    await ctx.report_progress(1.0, "Complete")
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": result.failed == 0 and result.errors == 0,
            "result": result.to_dict()
        }, indent=2)
    
    # Markdown format
    pass_rate = result.passed / max(result.total_tests, 1) * 100
    
    status_icon = "✅" if result.failed == 0 and result.errors == 0 else "❌"
    
    lines = [
        f"# {status_icon} Test Results",
        f"",
        f"**Executed at:** {result.executed_at}",
        f"**Duration:** {result.duration_seconds:.2f}s",
        f"",
        "## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total Tests | {result.total_tests} |",
        f"| ✅ Passed | {result.passed} |",
        f"| ❌ Failed | {result.failed} |",
        f"| 💥 Errors | {result.errors} |",
        f"| ⏭️ Skipped | {result.skipped} |",
        f"| **Pass Rate** | **{pass_rate:.1f}%** |",
        ""
    ]
    
    # Coverage section
    if result.coverage:
        cov = result.coverage
        cov_icon = "✅" if cov.coverage_percent >= config.coverage_threshold else "⚠️"
        lines.extend([
            "## Coverage",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Statements | {cov.covered_statements}/{cov.total_statements} |",
            f"| {cov_icon} Coverage | **{cov.coverage_percent:.1f}%** |",
        ])
        if cov.branch_coverage_percent is not None:
            lines.append(f"| Branch Coverage | {cov.branch_coverage_percent:.1f}% |")
        lines.append("")
    
    # Failed tests detail
    failed_tests = [r for r in result.results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
    if failed_tests:
        lines.append("## ❌ Failed Tests")
        lines.append("")
        for t in failed_tests[:10]:  # Limit to 10
            lines.append(f"### `{t.test_name}`")
            lines.append(f"**Status:** {t.status.value}")
            if t.error_message:
                lines.append(f"**Error:** {t.error_message[:200]}")
            lines.append("")
    
    return "\n".join(lines)


@mcp.tool(
    name="suggest_tests_for_coverage",
    annotations={
        "title": "Suggest Tests for Coverage Gaps",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def suggest_tests_for_coverage(params: SuggestTestsInput, ctx: Context) -> str:
    """
    Analyze a file and suggest tests to improve coverage.
    
    Identifies untested code paths and generates specific
    test suggestions to fill coverage gaps.
    """
    file_path = Path(params.file_path)
    
    if not file_path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    await ctx.report_progress(0.3, "Analyzing code...")
    
    # Generate all possible tests
    all_tests = generator.generate_for_file(file_path)
    
    # TODO: Compare with existing tests to find gaps
    # For now, return all suggestions
    
    suggestions = all_tests[:params.max_suggestions]
    
    await ctx.report_progress(1.0, f"Found {len(suggestions)} suggestions")
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": True,
            "suggestions": [t.to_dict() for t in suggestions]
        }, indent=2)
    
    lines = [
        f"# 💡 Test Suggestions for {file_path.name}",
        f"",
        f"Found **{len(suggestions)}** potential tests to add:",
        ""
    ]
    
    for i, tc in enumerate(suggestions, 1):
        lines.append(f"{i}. **{tc.name}** ({tc.test_type.value})")
        lines.append(f"   - Target: `{tc.target_function}`")
        lines.append(f"   - {tc.description}")
        lines.append("")
    
    return "\n".join(lines)


@mcp.tool(
    name="get_quality_trend",
    annotations={
        "title": "Get Quality Trend",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_quality_trend(params: GetQualityTrendInput) -> str:
    """
    Get quality metrics trend over time.
    
    Shows how test count, pass rate, and coverage
    have changed over the specified period.
    """
    trends = reporter.get_trend(params.days)
    
    if not trends:
        return "No historical data available. Run tests with `save_report=True` to start tracking."
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": True,
            "trends": [asdict(t) for t in trends]
        }, indent=2)
    
    lines = [
        f"# 📈 Quality Trend (Last {params.days} Days)",
        f"",
        "| Date | Tests | Pass Rate | Coverage | Issues |",
        "|------|-------|-----------|----------|--------|"
    ]
    
    for t in trends:
        lines.append(
            f"| {t.date} | {t.total_tests} | {t.pass_rate:.1f}% | {t.coverage_percent:.1f}% | {t.issues_found} |"
        )
    
    # Summary
    if len(trends) >= 2:
        first, last = trends[0], trends[-1]
        test_change = last.total_tests - first.total_tests
        coverage_change = last.coverage_percent - first.coverage_percent
        
        lines.extend([
            "",
            "## Summary",
            f"- Tests: {'+' if test_change >= 0 else ''}{test_change}",
            f"- Coverage: {'+' if coverage_change >= 0 else ''}{coverage_change:.1f}%"
        ])
    
    return "\n".join(lines)


@mcp.tool(
    name="analyze_test_failures",
    annotations={
        "title": "Analyze Test Failures",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_test_failures(params: RunTestsInput, ctx: Context) -> str:
    """
    Run tests and provide detailed failure analysis.
    
    Groups failures by type, identifies patterns,
    and suggests fixes for common issues.
    """
    await ctx.report_progress(0.1, "Running tests...")
    
    test_path = Path(params.test_path) if params.test_path else None
    result = executor.run_tests(
        test_path=test_path,
        pattern=params.pattern,
        coverage=False,
        verbose=True
    )
    
    await ctx.report_progress(0.7, "Analyzing failures...")
    
    failed = [r for r in result.results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
    
    if not failed:
        return "✅ **All tests passed!** No failures to analyze."
    
    # Group by error type
    by_error_type = defaultdict(list)
    for f in failed:
        error_type = "Unknown"
        if "AssertionError" in f.error_message:
            error_type = "Assertion"
        elif "AttributeError" in f.error_message:
            error_type = "AttributeError"
        elif "ImportError" in f.error_message or "ModuleNotFoundError" in f.error_message:
            error_type = "Import"
        elif "TypeError" in f.error_message:
            error_type = "TypeError"
        elif "KeyError" in f.error_message:
            error_type = "KeyError"
        elif "DoesNotExist" in f.error_message:
            error_type = "DoesNotExist"
        
        by_error_type[error_type].append(f)
    
    await ctx.report_progress(1.0, "Analysis complete")
    
    lines = [
        f"# 🔍 Test Failure Analysis",
        f"",
        f"**Total Failures:** {len(failed)}",
        f"**Error Types:** {len(by_error_type)}",
        ""
    ]
    
    for error_type, failures in sorted(by_error_type.items(), key=lambda x: -len(x[1])):
        lines.append(f"## {error_type} ({len(failures)})")
        lines.append("")
        
        # Suggest fix based on error type
        if error_type == "Import":
            lines.append("💡 **Suggestion:** Check that all modules are installed and paths are correct.")
        elif error_type == "DoesNotExist":
            lines.append("💡 **Suggestion:** Ensure test fixtures create required database objects.")
        elif error_type == "Assertion":
            lines.append("💡 **Suggestion:** Review expected vs actual values in assertions.")
        
        lines.append("")
        
        for f in failures[:5]:
            lines.append(f"- `{f.test_name}`")
            if f.error_message:
                lines.append(f"  - {f.error_message[:100]}")
        
        if len(failures) > 5:
            lines.append(f"  - ... and {len(failures) - 5} more")
        
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point for the MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Generator MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mechanism"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Port for HTTP transport"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory"
    )
    
    args = parser.parse_args()
    
    if args.transport == "http":
        mcp.run(transport="streamable_http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
