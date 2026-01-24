"""
Code Quality Analyzer MCP Server
================================
MCP Server für automatische Code-Analyse, Naming Convention Checks,
Architecture Pattern Validation und Refactoring-Vorschläge.

Basiert auf dem BF Agent consistency_framework.py Pattern.

Features:
- AST-basierte Python Code Analyse
- Naming Convention Enforcement (PEP 8, Django, BF Agent Patterns)
- Separation of Concerns Validation
- Database-Driven Architecture Checks
- Auto-Fix Suggestions mit Diff-Preview

Usage:
    # Als MCP Server (stdio)
    python code_quality_mcp.py
    
    # Mit spezifischem Projekt
    python code_quality_mcp.py --project-root /path/to/bf_agent
"""

import ast
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class NamingRules:
    """Configurable naming convention rules."""
    
    # Python/PEP 8
    class_pattern: str = r'^[A-Z][a-zA-Z0-9]+$'
    function_pattern: str = r'^[a-z_][a-z0-9_]*$'
    constant_pattern: str = r'^[A-Z][A-Z0-9_]*$'
    variable_pattern: str = r'^[a-z_][a-z0-9_]*$'
    module_pattern: str = r'^[a-z][a-z0-9_]*$'
    
    # Django Specific
    model_pattern: str = r'^[A-Z][a-zA-Z0-9]+$'
    model_suffix: str = ''  # No suffix required
    form_suffix: str = 'Form'
    serializer_suffix: str = 'Serializer'
    view_suffix: str = 'View'
    viewset_suffix: str = 'ViewSet'
    
    # BF Agent Specific
    handler_suffix: str = 'Handler'
    plugin_suffix: str = 'Plugin'
    service_suffix: str = 'Service'
    repository_suffix: str = 'Repository'
    
    # MCP Specific
    mcp_tool_prefix: str = ''  # e.g., 'myservice_'
    mcp_server_suffix: str = '_mcp'


@dataclass
class ArchitectureRules:
    """Architecture pattern validation rules."""
    
    # Layer Boundaries
    allowed_imports: Dict[str, List[str]] = field(default_factory=lambda: {
        'models': ['django', 'pydantic', 'sqlalchemy'],
        'views': ['models', 'forms', 'services', 'django'],
        'handlers': ['models', 'services', 'schemas'],
        'services': ['models', 'repositories'],
        'repositories': ['models', 'django.db'],
        'schemas': ['pydantic', 'enum'],
    })
    
    # Forbidden Patterns
    forbidden_in_models: List[str] = field(default_factory=lambda: [
        'requests', 'httpx', 'aiohttp',  # No HTTP in models
        'print(',  # No prints in models
    ])
    
    forbidden_in_views: List[str] = field(default_factory=lambda: [
        'cursor.execute',  # Raw SQL in views
        'open(',  # File I/O in views
    ])
    
    # Required Patterns
    handler_must_have: List[str] = field(default_factory=lambda: [
        'INPUT_SCHEMA',
        'OUTPUT_SCHEMA', 
        'execute',
    ])
    
    model_must_have: List[str] = field(default_factory=lambda: [
        '__str__',
        'class Meta',
    ])


# =============================================================================
# Enums
# =============================================================================

class IssueSeverity(str, Enum):
    """Severity levels for code issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


class IssueCategory(str, Enum):
    """Categories of code issues."""
    NAMING = "naming"
    ARCHITECTURE = "architecture"
    SEPARATION = "separation_of_concerns"
    DATABASE = "database"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STYLE = "style"
    DOCUMENTATION = "documentation"


class ComponentType(str, Enum):
    """Types of code components."""
    MODEL = "model"
    VIEW = "view"
    FORM = "form"
    HANDLER = "handler"
    SERVICE = "service"
    SERIALIZER = "serializer"
    SCHEMA = "schema"
    TEST = "test"
    MIGRATION = "migration"
    ADMIN = "admin"
    URL = "url"
    UNKNOWN = "unknown"


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


# =============================================================================
# Data Classes for Analysis Results
# =============================================================================

@dataclass
class CodeIssue:
    """Represents a single code issue found during analysis."""
    
    file_path: str
    line_number: int
    column: int
    severity: IssueSeverity
    category: IssueCategory
    message: str
    rule_id: str
    suggestion: Optional[str] = None
    fix_available: bool = False
    fix_code: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    
    file_path: str
    component_type: ComponentType
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['issues'] = [i.to_dict() for i in self.issues]
        return result


@dataclass
class ProjectAnalysis:
    """Complete project analysis result."""
    
    project_root: str
    analyzed_at: str
    total_files: int = 0
    total_issues: int = 0
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    files: List[FileAnalysis] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result['files'] = [f.to_dict() for f in self.files]
        return result


# =============================================================================
# AST Analyzers
# =============================================================================

class NamingConventionAnalyzer(ast.NodeVisitor):
    """AST visitor for checking naming conventions."""
    
    def __init__(self, rules: NamingRules, file_path: str):
        self.rules = rules
        self.file_path = file_path
        self.issues: List[CodeIssue] = []
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.current_class: Optional[str] = None
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        old_class = self.current_class
        self.current_class = node.name
        
        # Check class naming
        component_type = self._detect_component_type(node)
        expected_pattern = self._get_pattern_for_component(component_type)
        
        if not re.match(expected_pattern, node.name):
            self.issues.append(CodeIssue(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category=IssueCategory.NAMING,
                message=f"Class '{node.name}' doesn't match expected pattern for {component_type.value}",
                rule_id="NC001",
                suggestion=self._suggest_class_name(node.name, component_type),
                fix_available=True
            ))
        
        # Check for required suffix
        required_suffix = self._get_required_suffix(component_type)
        if required_suffix and not node.name.endswith(required_suffix):
            self.issues.append(CodeIssue(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category=IssueCategory.NAMING,
                message=f"{component_type.value} class '{node.name}' should end with '{required_suffix}'",
                rule_id="NC002",
                suggestion=f"{node.name}{required_suffix}",
                fix_available=True
            ))
        
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        
        # Skip dunder methods
        if node.name.startswith('__') and node.name.endswith('__'):
            self.generic_visit(node)
            return
        
        # Check function naming (snake_case)
        if not re.match(self.rules.function_pattern, node.name):
            self.issues.append(CodeIssue(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                severity=IssueSeverity.WARNING,
                category=IssueCategory.NAMING,
                message=f"Function '{node.name}' should use snake_case",
                rule_id="NC003",
                suggestion=self._to_snake_case(node.name),
                fix_available=True
            ))
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Check constant naming (module-level UPPER_CASE)."""
        # Only check module-level assignments
        if self.current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # Check if it looks like a constant (simple value assignment)
                    if self._is_constant_assignment(node.value):
                        if not re.match(self.rules.constant_pattern, name):
                            if not name.startswith('_'):  # Skip private
                                self.issues.append(CodeIssue(
                                    file_path=self.file_path,
                                    line_number=node.lineno,
                                    column=node.col_offset,
                                    severity=IssueSeverity.INFO,
                                    category=IssueCategory.NAMING,
                                    message=f"Module-level constant '{name}' should use UPPER_CASE",
                                    rule_id="NC004",
                                    suggestion=name.upper(),
                                    fix_available=True
                                ))
        
        self.generic_visit(node)
    
    def _detect_component_type(self, node: ast.ClassDef) -> ComponentType:
        """Detect component type from class definition."""
        bases = [self._get_base_name(b) for b in node.bases]
        name_lower = node.name.lower()
        
        # Check inheritance
        if any('Model' in b for b in bases):
            return ComponentType.MODEL
        if any('View' in b or 'ViewSet' in b for b in bases):
            return ComponentType.VIEW
        if any('Form' in b for b in bases):
            return ComponentType.FORM
        if any('Serializer' in b for b in bases):
            return ComponentType.SERIALIZER
        if any('Handler' in b or 'BaseHandler' in b for b in bases):
            return ComponentType.HANDLER
        
        # Check naming
        if 'handler' in name_lower:
            return ComponentType.HANDLER
        if 'service' in name_lower:
            return ComponentType.SERVICE
        if 'test' in name_lower:
            return ComponentType.TEST
        
        return ComponentType.UNKNOWN
    
    def _get_base_name(self, node: ast.expr) -> str:
        """Extract base class name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""
    
    def _get_pattern_for_component(self, component_type: ComponentType) -> str:
        """Get naming pattern for component type."""
        return self.rules.class_pattern
    
    def _get_required_suffix(self, component_type: ComponentType) -> str:
        """Get required suffix for component type."""
        suffix_map = {
            ComponentType.HANDLER: self.rules.handler_suffix,
            ComponentType.FORM: self.rules.form_suffix,
            ComponentType.VIEW: self.rules.view_suffix,
            ComponentType.SERIALIZER: self.rules.serializer_suffix,
            ComponentType.SERVICE: self.rules.service_suffix,
        }
        return suffix_map.get(component_type, '')
    
    def _suggest_class_name(self, name: str, component_type: ComponentType) -> str:
        """Suggest corrected class name."""
        # Convert to PascalCase
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
        pascal = ''.join(w.capitalize() for w in words)
        
        suffix = self._get_required_suffix(component_type)
        if suffix and not pascal.endswith(suffix):
            pascal += suffix
        
        return pascal
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _is_constant_assignment(self, node: ast.expr) -> bool:
        """Check if assignment value looks like a constant."""
        if isinstance(node, (ast.Constant, ast.Num, ast.Str)):
            return True
        if isinstance(node, ast.List) and len(node.elts) == 0:
            return False  # Empty list, might be mutable default
        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return False
        return False


class ArchitectureAnalyzer(ast.NodeVisitor):
    """AST visitor for checking architecture patterns."""
    
    def __init__(self, rules: ArchitectureRules, file_path: str, component_type: ComponentType):
        self.rules = rules
        self.file_path = file_path
        self.component_type = component_type
        self.issues: List[CodeIssue] = []
        self.imports: List[str] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.append(node.module)
            self._check_import(node.module, node.lineno)
        self.generic_visit(node)
    
    def _check_import(self, module: str, lineno: int) -> None:
        """Check if import is allowed for this component type."""
        component_key = self.component_type.value
        
        if component_key in self.rules.allowed_imports:
            allowed = self.rules.allowed_imports[component_key]
            
            # Check if module is allowed
            module_base = module.split('.')[0]
            if not any(module.startswith(a) or module_base == a for a in allowed):
                # Check if it's a local import (same project)
                if not module.startswith('apps.') and module_base not in ['typing', 'datetime', 'enum', 'dataclasses']:
                    self.issues.append(CodeIssue(
                        file_path=self.file_path,
                        line_number=lineno,
                        column=0,
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.ARCHITECTURE,
                        message=f"Import '{module}' may violate layer boundaries for {component_key}",
                        rule_id="AR001",
                        suggestion=f"Consider moving this logic to a service layer"
                    ))
    
    def check_forbidden_patterns(self, source_code: str) -> None:
        """Check for forbidden patterns in source code."""
        forbidden_list = []
        
        if self.component_type == ComponentType.MODEL:
            forbidden_list = self.rules.forbidden_in_models
        elif self.component_type == ComponentType.VIEW:
            forbidden_list = self.rules.forbidden_in_views
        
        for lineno, line in enumerate(source_code.split('\n'), 1):
            for pattern in forbidden_list:
                if pattern in line and not line.strip().startswith('#'):
                    self.issues.append(CodeIssue(
                        file_path=self.file_path,
                        line_number=lineno,
                        column=line.find(pattern),
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SEPARATION,
                        message=f"Forbidden pattern '{pattern}' found in {self.component_type.value}",
                        rule_id="SEP001",
                        suggestion=f"Move this logic to an appropriate layer"
                    ))


class SeparationOfConcernsAnalyzer:
    """Analyzer for separation of concerns violations."""
    
    def __init__(self, rules: ArchitectureRules):
        self.rules = rules
    
    def analyze_handler(self, file_path: str, source_code: str) -> List[CodeIssue]:
        """Check if handler follows proper patterns."""
        issues = []
        
        # Parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for required attributes
                has_input_schema = False
                has_output_schema = False
                has_execute = False
                
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == 'INPUT_SCHEMA':
                                    has_input_schema = True
                                elif target.id == 'OUTPUT_SCHEMA':
                                    has_output_schema = True
                    
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == 'execute':
                            has_execute = True
                
                # Report missing elements
                if 'Handler' in node.name:
                    if not has_input_schema:
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=0,
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.ARCHITECTURE,
                            message=f"Handler '{node.name}' missing INPUT_SCHEMA",
                            rule_id="HDL001",
                            suggestion="Add INPUT_SCHEMA = {...} class attribute"
                        ))
                    
                    if not has_output_schema:
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=0,
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.ARCHITECTURE,
                            message=f"Handler '{node.name}' missing OUTPUT_SCHEMA",
                            rule_id="HDL002",
                            suggestion="Add OUTPUT_SCHEMA = {...} class attribute"
                        ))
                    
                    if not has_execute:
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=0,
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.ARCHITECTURE,
                            message=f"Handler '{node.name}' missing execute() method",
                            rule_id="HDL003",
                            suggestion="Add async def execute(self, context) -> Result method"
                        ))
        
        return issues


# =============================================================================
# Main Analyzer Service
# =============================================================================

class CodeQualityAnalyzer:
    """Main service for code quality analysis."""
    
    def __init__(
        self,
        naming_rules: Optional[NamingRules] = None,
        architecture_rules: Optional[ArchitectureRules] = None
    ):
        self.naming_rules = naming_rules or NamingRules()
        self.architecture_rules = architecture_rules or ArchitectureRules()
        self.soc_analyzer = SeparationOfConcernsAnalyzer(self.architecture_rules)
    
    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file."""
        result = FileAnalysis(
            file_path=str(file_path),
            component_type=self._detect_file_type(file_path)
        )
        
        try:
            source_code = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source_code)
        except SyntaxError as e:
            result.issues.append(CodeIssue(
                file_path=str(file_path),
                line_number=e.lineno or 1,
                column=e.offset or 0,
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STYLE,
                message=f"Syntax error: {e.msg}",
                rule_id="SYN001"
            ))
            return result
        except Exception as e:
            return result
        
        # Naming convention analysis
        naming_analyzer = NamingConventionAnalyzer(self.naming_rules, str(file_path))
        naming_analyzer.visit(tree)
        result.classes = naming_analyzer.classes
        result.functions = naming_analyzer.functions
        result.issues.extend(naming_analyzer.issues)
        
        # Architecture analysis
        arch_analyzer = ArchitectureAnalyzer(
            self.architecture_rules, 
            str(file_path), 
            result.component_type
        )
        arch_analyzer.visit(tree)
        arch_analyzer.check_forbidden_patterns(source_code)
        result.imports = arch_analyzer.imports
        result.issues.extend(arch_analyzer.issues)
        
        # Separation of concerns (for handlers)
        if result.component_type == ComponentType.HANDLER:
            soc_issues = self.soc_analyzer.analyze_handler(str(file_path), source_code)
            result.issues.extend(soc_issues)
        
        # Metrics
        result.metrics = {
            'lines': len(source_code.split('\n')),
            'classes': len(result.classes),
            'functions': len(result.functions),
            'imports': len(result.imports),
            'issues': len(result.issues)
        }
        
        return result
    
    def analyze_project(self, project_root: Path, exclude_patterns: Optional[List[str]] = None) -> ProjectAnalysis:
        """Analyze an entire project."""
        exclude = exclude_patterns or ['migrations', '__pycache__', '.git', 'venv', 'node_modules']
        
        result = ProjectAnalysis(
            project_root=str(project_root),
            analyzed_at=datetime.utcnow().isoformat()
        )
        
        # Find all Python files
        python_files = []
        for py_file in project_root.rglob('*.py'):
            # Skip excluded directories
            if any(ex in str(py_file) for ex in exclude):
                continue
            python_files.append(py_file)
        
        result.total_files = len(python_files)
        
        # Analyze each file
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for py_file in python_files:
            file_analysis = self.analyze_file(py_file)
            result.files.append(file_analysis)
            
            for issue in file_analysis.issues:
                severity_counts[issue.severity.value] += 1
                category_counts[issue.category.value] += 1
        
        result.total_issues = sum(severity_counts.values())
        result.issues_by_severity = dict(severity_counts)
        result.issues_by_category = dict(category_counts)
        
        # Summary
        result.summary = {
            'total_classes': sum(len(f.classes) for f in result.files),
            'total_functions': sum(len(f.functions) for f in result.files),
            'total_lines': sum(f.metrics.get('lines', 0) for f in result.files),
            'files_with_issues': sum(1 for f in result.files if f.issues),
            'fixable_issues': sum(
                1 for f in result.files 
                for i in f.issues 
                if i.fix_available
            )
        }
        
        return result
    
    def _detect_file_type(self, file_path: Path) -> ComponentType:
        """Detect component type from file path and name."""
        name = file_path.stem
        parent = file_path.parent.name
        
        # By directory
        if parent == 'models' or name == 'models':
            return ComponentType.MODEL
        if parent == 'views' or name == 'views':
            return ComponentType.VIEW
        if parent == 'forms' or name == 'forms':
            return ComponentType.FORM
        if parent == 'handlers' or 'handler' in name:
            return ComponentType.HANDLER
        if parent == 'services' or 'service' in name:
            return ComponentType.SERVICE
        if parent == 'serializers' or name == 'serializers':
            return ComponentType.SERIALIZER
        if parent == 'tests' or name.startswith('test_'):
            return ComponentType.TEST
        if parent == 'migrations':
            return ComponentType.MIGRATION
        if name == 'admin':
            return ComponentType.ADMIN
        if name == 'urls':
            return ComponentType.URL
        
        return ComponentType.UNKNOWN


# =============================================================================
# Pydantic Input Schemas
# =============================================================================

class AnalyzeFileInput(BaseModel):
    """Input for single file analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    file_path: str = Field(..., description="Path to Python file to analyze")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class AnalyzeProjectInput(BaseModel):
    """Input for project analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    project_root: str = Field(..., description="Root directory of the project")
    exclude_patterns: Optional[List[str]] = Field(
        default=None,
        description="Patterns to exclude (e.g., ['migrations', 'tests'])"
    )
    max_files: int = Field(default=100, ge=1, le=1000, description="Maximum files to analyze")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class AnalyzeCodeInput(BaseModel):
    """Input for inline code analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    code: str = Field(..., description="Python code to analyze", min_length=1)
    file_name: str = Field(default="inline.py", description="Virtual filename for context")
    component_type: Optional[ComponentType] = Field(
        default=None,
        description="Override component type detection"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SuggestRefactoringInput(BaseModel):
    """Input for refactoring suggestions."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    file_path: str = Field(..., description="Path to file")
    issue_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific issue IDs to fix (None = all fixable)"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CheckNamingInput(BaseModel):
    """Input for naming convention check."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    name: str = Field(..., description="Name to check")
    expected_type: str = Field(
        ...,
        description="Expected type: class, function, constant, handler, model, etc."
    )


class ListRulesInput(BaseModel):
    """Input for listing active rules."""
    model_config = ConfigDict(extra='forbid')
    
    category: Optional[IssueCategory] = Field(
        default=None,
        description="Filter by category"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("code_quality_mcp")

# Global analyzer instance
analyzer = CodeQualityAnalyzer()


@mcp.tool(
    name="analyze_python_file",
    annotations={
        "title": "Analyze Python File",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_python_file(params: AnalyzeFileInput, ctx: Context) -> str:
    """
    Analyze a single Python file for code quality issues.
    
    Checks for:
    - Naming convention violations (PEP 8, Django, BF Agent patterns)
    - Architecture pattern violations
    - Separation of concerns issues
    - Missing required elements (for handlers, models, etc.)
    
    Returns issues with severity, suggestions, and fix availability.
    """
    file_path = Path(params.file_path)
    
    if not file_path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    if not file_path.suffix == '.py':
        return json.dumps({"success": False, "error": "Only Python files are supported"})
    
    await ctx.report_progress(0.2, "Parsing file...")
    result = analyzer.analyze_file(file_path)
    await ctx.report_progress(1.0, "Analysis complete")
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": True,
            "analysis": result.to_dict()
        }, indent=2)
    
    # Markdown format
    lines = [
        f"# 📊 Analysis: {file_path.name}",
        f"",
        f"**Component Type:** {result.component_type.value}",
        f"**Lines:** {result.metrics.get('lines', 0)}",
        f"**Classes:** {len(result.classes)}",
        f"**Functions:** {len(result.functions)}",
        f"**Issues Found:** {len(result.issues)}",
        ""
    ]
    
    if result.issues:
        lines.append("## Issues")
        lines.append("")
        
        for issue in sorted(result.issues, key=lambda x: (x.severity.value, x.line_number)):
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "style": "⚪"}.get(issue.severity.value, "⚪")
            lines.append(f"### {icon} Line {issue.line_number}: {issue.message}")
            lines.append(f"- **Rule:** `{issue.rule_id}` ({issue.category.value})")
            if issue.suggestion:
                lines.append(f"- **Suggestion:** `{issue.suggestion}`")
            if issue.fix_available:
                lines.append(f"- ✅ **Auto-fix available**")
            lines.append("")
    else:
        lines.append("✅ **No issues found!**")
    
    return "\n".join(lines)


@mcp.tool(
    name="analyze_python_project",
    annotations={
        "title": "Analyze Python Project",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_python_project(params: AnalyzeProjectInput, ctx: Context) -> str:
    """
    Analyze an entire Python/Django project for code quality issues.
    
    Provides:
    - Summary of all issues by severity and category
    - Per-file breakdown
    - Fixable issues count
    - Architecture recommendations
    """
    project_root = Path(params.project_root)
    
    if not project_root.exists():
        return json.dumps({"success": False, "error": f"Directory not found: {project_root}"})
    
    await ctx.report_progress(0.1, "Scanning project...")
    result = analyzer.analyze_project(project_root, params.exclude_patterns)
    await ctx.report_progress(1.0, "Analysis complete")
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "success": True,
            "analysis": result.to_dict()
        }, indent=2)
    
    # Markdown format
    lines = [
        f"# 📊 Project Analysis: {project_root.name}",
        f"",
        f"**Analyzed at:** {result.analyzed_at}",
        f"**Total Files:** {result.total_files}",
        f"**Total Issues:** {result.total_issues}",
        f"**Fixable Issues:** {result.summary.get('fixable_issues', 0)}",
        "",
        "## Summary by Severity",
        ""
    ]
    
    for severity, count in sorted(result.issues_by_severity.items()):
        icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "style": "⚪"}.get(severity, "⚪")
        lines.append(f"- {icon} **{severity.upper()}:** {count}")
    
    lines.append("")
    lines.append("## Summary by Category")
    lines.append("")
    
    for category, count in sorted(result.issues_by_category.items()):
        lines.append(f"- **{category}:** {count}")
    
    lines.append("")
    lines.append("## Files with Most Issues")
    lines.append("")
    
    # Top 10 files with issues
    files_with_issues = [(f.file_path, len(f.issues)) for f in result.files if f.issues]
    files_with_issues.sort(key=lambda x: x[1], reverse=True)
    
    for file_path, issue_count in files_with_issues[:10]:
        lines.append(f"- `{Path(file_path).name}`: {issue_count} issues")
    
    return "\n".join(lines)


@mcp.tool(
    name="analyze_code_snippet",
    annotations={
        "title": "Analyze Code Snippet",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_code_snippet(params: AnalyzeCodeInput) -> str:
    """
    Analyze inline Python code for quality issues.
    
    Useful for checking code before committing or during review.
    """
    import tempfile
    
    # Write to temp file for analysis
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(params.code)
        temp_path = Path(f.name)
    
    try:
        result = analyzer.analyze_file(temp_path)
        result.file_path = params.file_name
        
        # Override component type if specified
        if params.component_type:
            result.component_type = params.component_type
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "success": True,
                "analysis": result.to_dict()
            }, indent=2)
        
        # Simple markdown
        if not result.issues:
            return "✅ **No issues found in code snippet!**"
        
        lines = [f"# Issues Found: {len(result.issues)}", ""]
        for issue in result.issues:
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "style": "⚪"}.get(issue.severity.value, "⚪")
            lines.append(f"- {icon} **Line {issue.line_number}:** {issue.message}")
            if issue.suggestion:
                lines.append(f"  - Suggestion: `{issue.suggestion}`")
        
        return "\n".join(lines)
        
    finally:
        temp_path.unlink()


@mcp.tool(
    name="check_naming_convention",
    annotations={
        "title": "Check Naming Convention",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def check_naming_convention(params: CheckNamingInput) -> str:
    """
    Check if a name follows the expected convention.
    
    Supports: class, function, constant, variable, module,
    handler, model, form, view, service, serializer
    """
    rules = analyzer.naming_rules
    name = params.name
    expected = params.expected_type.lower()
    
    patterns = {
        'class': (rules.class_pattern, 'PascalCase'),
        'function': (rules.function_pattern, 'snake_case'),
        'constant': (rules.constant_pattern, 'UPPER_CASE'),
        'variable': (rules.variable_pattern, 'snake_case'),
        'module': (rules.module_pattern, 'snake_case'),
        'handler': (rules.class_pattern, f'PascalCase + {rules.handler_suffix}'),
        'model': (rules.model_pattern, 'PascalCase'),
        'form': (rules.class_pattern, f'PascalCase + {rules.form_suffix}'),
        'view': (rules.class_pattern, f'PascalCase + {rules.view_suffix}'),
        'service': (rules.class_pattern, f'PascalCase + {rules.service_suffix}'),
        'serializer': (rules.class_pattern, f'PascalCase + {rules.serializer_suffix}'),
    }
    
    if expected not in patterns:
        return json.dumps({
            "valid": False,
            "error": f"Unknown type: {expected}. Supported: {list(patterns.keys())}"
        })
    
    pattern, description = patterns[expected]
    matches = bool(re.match(pattern, name))
    
    # Check suffix for specific types
    suffix_check = True
    suffix_required = None
    
    if expected == 'handler' and rules.handler_suffix:
        suffix_required = rules.handler_suffix
        suffix_check = name.endswith(suffix_required)
    elif expected == 'form' and rules.form_suffix:
        suffix_required = rules.form_suffix
        suffix_check = name.endswith(suffix_required)
    elif expected == 'view' and rules.view_suffix:
        suffix_required = rules.view_suffix
        suffix_check = name.endswith(suffix_required)
    
    is_valid = matches and suffix_check
    
    result = {
        "name": name,
        "expected_type": expected,
        "valid": is_valid,
        "pattern": description,
        "matches_pattern": matches,
        "suffix_check": suffix_check,
    }
    
    if not is_valid:
        # Generate suggestion
        suggestion = name
        
        # Fix pattern
        if not matches:
            if expected in ['class', 'handler', 'model', 'form', 'view', 'service', 'serializer']:
                # To PascalCase
                words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
                suggestion = ''.join(w.capitalize() for w in words)
            else:
                # To snake_case
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                suggestion = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Add suffix
        if suffix_required and not suggestion.endswith(suffix_required):
            suggestion += suffix_required
        
        result["suggestion"] = suggestion
    
    return json.dumps(result, indent=2)


@mcp.tool(
    name="list_quality_rules",
    annotations={
        "title": "List Quality Rules",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_quality_rules(params: ListRulesInput) -> str:
    """
    List all active code quality rules.
    
    Shows rule IDs, descriptions, and categories.
    """
    rules = [
        ("NC001", IssueCategory.NAMING, "Class naming pattern"),
        ("NC002", IssueCategory.NAMING, "Required suffix for component type"),
        ("NC003", IssueCategory.NAMING, "Function must use snake_case"),
        ("NC004", IssueCategory.NAMING, "Module constant must use UPPER_CASE"),
        ("AR001", IssueCategory.ARCHITECTURE, "Import violates layer boundaries"),
        ("SEP001", IssueCategory.SEPARATION, "Forbidden pattern in component"),
        ("HDL001", IssueCategory.ARCHITECTURE, "Handler missing INPUT_SCHEMA"),
        ("HDL002", IssueCategory.ARCHITECTURE, "Handler missing OUTPUT_SCHEMA"),
        ("HDL003", IssueCategory.ARCHITECTURE, "Handler missing execute() method"),
        ("SYN001", IssueCategory.STYLE, "Python syntax error"),
    ]
    
    # Filter by category
    if params.category:
        rules = [(r, c, d) for r, c, d in rules if c == params.category]
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "rules": [
                {"id": r, "category": c.value, "description": d}
                for r, c, d in rules
            ]
        }, indent=2)
    
    lines = ["# 📋 Code Quality Rules", ""]
    
    current_category = None
    for rule_id, category, description in sorted(rules, key=lambda x: (x[1].value, x[0])):
        if category != current_category:
            lines.append(f"## {category.value.replace('_', ' ').title()}")
            lines.append("")
            current_category = category
        
        lines.append(f"- **{rule_id}:** {description}")
    
    return "\n".join(lines)


@mcp.tool(
    name="suggest_refactoring",
    annotations={
        "title": "Suggest Refactoring",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def suggest_refactoring(params: SuggestRefactoringInput, ctx: Context) -> str:
    """
    Generate refactoring suggestions for a file.
    
    Shows diff-style preview of suggested changes for fixable issues.
    """
    file_path = Path(params.file_path)
    
    if not file_path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})
    
    result = analyzer.analyze_file(file_path)
    
    # Filter to fixable issues
    fixable = [i for i in result.issues if i.fix_available]
    
    if params.issue_ids:
        fixable = [i for i in fixable if i.rule_id in params.issue_ids]
    
    if not fixable:
        return "✅ **No fixable issues found!**"
    
    source = file_path.read_text()
    lines = source.split('\n')
    
    output = [
        f"# 🔧 Refactoring Suggestions: {file_path.name}",
        f"",
        f"**Fixable Issues:** {len(fixable)}",
        ""
    ]
    
    for issue in fixable:
        output.append(f"## Line {issue.line_number}: {issue.rule_id}")
        output.append(f"**Issue:** {issue.message}")
        output.append("")
        
        # Show context
        start = max(0, issue.line_number - 2)
        end = min(len(lines), issue.line_number + 1)
        
        output.append("```diff")
        for i in range(start, end):
            prefix = "- " if i == issue.line_number - 1 else "  "
            output.append(f"{prefix}{lines[i]}")
        
        if issue.suggestion:
            output.append(f"+ {issue.suggestion}")
        
        output.append("```")
        output.append("")
    
    return "\n".join(output)


# =============================================================================
# HTMX VALIDATION TOOLS
# =============================================================================

# Valid HTMX attribute values
VALID_HX_SWAP = [
    'innerHTML', 'outerHTML', 'beforebegin', 'afterbegin', 
    'beforeend', 'afterend', 'delete', 'none',
    # With modifiers
    'innerHTML swap:', 'outerHTML swap:', 'innerHTML settle:',
]

VALID_HX_TRIGGER = [
    'click', 'change', 'submit', 'load', 'revealed', 'intersect',
    'keyup', 'keydown', 'focus', 'blur', 'mouseenter', 'mouseleave',
    # Special
    'every', 'sse:', 'ws:',
]

VALID_HX_ATTRIBUTES = {
    'hx-get': {'type': 'url', 'required': False},
    'hx-post': {'type': 'url', 'required': False},
    'hx-put': {'type': 'url', 'required': False},
    'hx-patch': {'type': 'url', 'required': False},
    'hx-delete': {'type': 'url', 'required': False},
    'hx-trigger': {'type': 'trigger', 'required': False},
    'hx-target': {'type': 'selector', 'required': False},
    'hx-swap': {'type': 'swap', 'required': False},
    'hx-select': {'type': 'selector', 'required': False},
    'hx-select-oob': {'type': 'selector', 'required': False},
    'hx-swap-oob': {'type': 'swap_oob', 'required': False},
    'hx-include': {'type': 'selector', 'required': False},
    'hx-indicator': {'type': 'selector', 'required': False},
    'hx-push-url': {'type': 'bool_or_url', 'required': False},
    'hx-confirm': {'type': 'string', 'required': False},
    'hx-disable': {'type': 'bool', 'required': False},
    'hx-disabled-elt': {'type': 'selector', 'required': False},
    'hx-ext': {'type': 'string', 'required': False},
    'hx-headers': {'type': 'json', 'required': False},
    'hx-history': {'type': 'bool', 'required': False},
    'hx-history-elt': {'type': 'bool', 'required': False},
    'hx-inherit': {'type': 'string', 'required': False},
    'hx-params': {'type': 'params', 'required': False},
    'hx-preserve': {'type': 'bool', 'required': False},
    'hx-prompt': {'type': 'string', 'required': False},
    'hx-replace-url': {'type': 'bool_or_url', 'required': False},
    'hx-request': {'type': 'string', 'required': False},
    'hx-sync': {'type': 'sync', 'required': False},
    'hx-validate': {'type': 'bool', 'required': False},
    'hx-vals': {'type': 'json', 'required': False},
    'hx-boost': {'type': 'bool', 'required': False},
    'hx-on': {'type': 'script', 'required': False},
    'hx-on:': {'type': 'script', 'required': False},  # hx-on:click etc
}


@dataclass
class HTMXIssue:
    """HTMX validation issue."""
    line_number: int
    attribute: str
    value: str
    message: str
    severity: str  # error, warning, info
    suggestion: Optional[str] = None


class HTMXValidator:
    """Validates HTMX attributes in HTML."""
    
    def validate_html(self, html: str) -> List[HTMXIssue]:
        """Validate HTMX attributes in HTML string."""
        issues = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
        except ImportError:
            return [HTMXIssue(
                line_number=0,
                attribute="",
                value="",
                message="BeautifulSoup not installed. Run: pip install beautifulsoup4",
                severity="error"
            )]
        
        # Find all elements with hx-* attributes
        for element in soup.find_all(True):
            for attr, value in element.attrs.items():
                if attr.startswith('hx-'):
                    line_num = self._estimate_line_number(html, str(element)[:50])
                    issues.extend(self._validate_attribute(attr, value, line_num))
        
        return issues
    
    def _validate_attribute(self, attr: str, value: str, line_num: int) -> List[HTMXIssue]:
        """Validate a single HTMX attribute."""
        issues = []
        
        # Handle hx-on:* attributes
        attr_key = attr if not attr.startswith('hx-on:') else 'hx-on:'
        
        if attr_key not in VALID_HX_ATTRIBUTES and not attr.startswith('hx-on:'):
            issues.append(HTMXIssue(
                line_number=line_num,
                attribute=attr,
                value=value,
                message=f"Unknown HTMX attribute '{attr}'",
                severity="warning",
                suggestion=f"Check HTMX docs: https://htmx.org/reference/"
            ))
            return issues
        
        # Validate hx-swap values
        if attr == 'hx-swap':
            base_value = value.split()[0] if value else ''
            if base_value and base_value not in VALID_HX_SWAP:
                valid_list = ', '.join(VALID_HX_SWAP[:8])
                issues.append(HTMXIssue(
                    line_number=line_num,
                    attribute=attr,
                    value=value,
                    message=f"Invalid hx-swap value '{base_value}'",
                    severity="error",
                    suggestion=f"Valid values: {valid_list}"
                ))
        
        # Validate hx-trigger
        if attr == 'hx-trigger':
            triggers = [t.strip().split()[0] for t in value.split(',')]
            for trigger in triggers:
                # Remove modifiers like [keyCode]
                base_trigger = trigger.split('[')[0]
                if base_trigger and not any(base_trigger.startswith(v) for v in VALID_HX_TRIGGER):
                    if not base_trigger.startswith('htmx:'):  # Custom events
                        issues.append(HTMXIssue(
                            line_number=line_num,
                            attribute=attr,
                            value=value,
                            message=f"Unusual trigger '{base_trigger}' - verify it's intentional",
                            severity="info"
                        ))
        
        # Validate hx-target selector
        if attr == 'hx-target':
            if value and not value.startswith(('#', '.', 'this', 'closest', 'find', 'next', 'previous', 'body')):
                issues.append(HTMXIssue(
                    line_number=line_num,
                    attribute=attr,
                    value=value,
                    message=f"hx-target '{value}' should be a CSS selector",
                    severity="warning",
                    suggestion="Use #id, .class, this, closest .class, etc."
                ))
        
        # Check for empty required URLs
        if attr in ['hx-get', 'hx-post', 'hx-put', 'hx-patch', 'hx-delete']:
            if not value or value.strip() == '':
                issues.append(HTMXIssue(
                    line_number=line_num,
                    attribute=attr,
                    value=value,
                    message=f"{attr} has empty URL",
                    severity="error",
                    suggestion="Provide a valid URL path"
                ))
        
        return issues
    
    def _estimate_line_number(self, html: str, element_snippet: str) -> int:
        """Estimate line number of element in HTML."""
        try:
            pos = html.find(element_snippet[:30])
            if pos >= 0:
                return html[:pos].count('\n') + 1
        except:
            pass
        return 1


# HTMX Validator instance
htmx_validator = HTMXValidator()


class ValidateHTMXInput(BaseModel):
    """Input for HTMX validation."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    
    html: str = Field(..., description="HTML content to validate", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListHTMXPatternsInput(BaseModel):
    """Input for listing HTMX patterns."""
    model_config = ConfigDict(extra='forbid')
    
    category: Optional[str] = Field(
        default=None,
        description="Filter by category: forms, lists, search, modals, etc."
    )


@mcp.tool(
    name="validate_htmx_attributes",
    annotations={
        "title": "Validate HTMX Attributes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def validate_htmx_attributes(params: ValidateHTMXInput) -> str:
    """
    Validate HTMX attributes in HTML for correctness.
    
    Checks for:
    - Invalid hx-swap values
    - Invalid hx-trigger events
    - Malformed hx-target selectors
    - Empty URLs in hx-get/post/etc
    - Unknown hx-* attributes
    
    Returns issues with suggestions for fixes.
    """
    issues = htmx_validator.validate_html(params.html)
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "valid": len([i for i in issues if i.severity == 'error']) == 0,
            "issues": [
                {
                    "line": i.line_number,
                    "attribute": i.attribute,
                    "value": i.value,
                    "message": i.message,
                    "severity": i.severity,
                    "suggestion": i.suggestion
                }
                for i in issues
            ]
        }, indent=2)
    
    if not issues:
        return "✅ **HTMX Validation Passed!** No issues found."
    
    lines = [
        f"# 🔍 HTMX Validation Results",
        f"",
        f"**Issues Found:** {len(issues)}",
        f"**Errors:** {len([i for i in issues if i.severity == 'error'])}",
        f"**Warnings:** {len([i for i in issues if i.severity == 'warning'])}",
        ""
    ]
    
    for issue in sorted(issues, key=lambda x: (x.severity != 'error', x.line_number)):
        icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "⚪")
        lines.append(f"### {icon} Line {issue.line_number}: `{issue.attribute}`")
        lines.append(f"**Value:** `{issue.value}`")
        lines.append(f"**Issue:** {issue.message}")
        if issue.suggestion:
            lines.append(f"**Fix:** {issue.suggestion}")
        lines.append("")
    
    return "\n".join(lines)


@mcp.tool(
    name="list_htmx_patterns",
    annotations={
        "title": "List HTMX Patterns",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_htmx_patterns(params: ListHTMXPatternsInput) -> str:
    """
    List common HTMX patterns for Django development.
    
    Provides ready-to-use code snippets for:
    - Click-to-Edit
    - Modal Forms
    - Active Search
    - Infinite Scroll
    - And more...
    """
    patterns = {
        "click_to_edit": {
            "name": "Click-to-Edit",
            "category": "forms",
            "description": "Inline editing of fields",
            "html": '''<div hx-get="/edit/{{ id }}/" hx-trigger="click" hx-swap="outerHTML">
  {{ value }}
</div>''',
            "view": '''def edit_field(request, pk):
    obj = get_object_or_404(Model, pk=pk)
    if request.method == "POST":
        form = FieldForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return render(request, "partials/field_display.html", {"obj": obj})
    return render(request, "partials/field_form.html", {"obj": obj})'''
        },
        "modal_form": {
            "name": "Modal Form",
            "category": "modals",
            "description": "Form in a modal dialog",
            "html": '''<button hx-get="/create/" hx-target="#modal-container" hx-swap="innerHTML">
  Add New
</button>
<div id="modal-container"></div>''',
            "view": '''def create_modal(request):
    if request.method == "POST":
        form = MyForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse(headers={"HX-Trigger": "closeModal, refreshList"})
    else:
        form = MyForm()
    return render(request, "partials/modal_form.html", {"form": form})'''
        },
        "active_search": {
            "name": "Active Search",
            "category": "search",
            "description": "Live search with debounce",
            "html": '''<input type="search" name="q"
       hx-get="/search/"
       hx-trigger="input changed delay:300ms, search"
       hx-target="#search-results"
       hx-indicator="#spinner">
<div id="search-results"></div>''',
            "view": '''def search(request):
    q = request.GET.get("q", "")
    results = Model.objects.filter(name__icontains=q)[:20]
    return render(request, "partials/search_results.html", {"results": results})'''
        },
        "infinite_scroll": {
            "name": "Infinite Scroll",
            "category": "lists",
            "description": "Load more on scroll",
            "html": '''<div id="items">
  {% for item in items %}
    {% include "partials/item.html" %}
  {% endfor %}
  <div hx-get="/items/?page={{ next_page }}"
       hx-trigger="revealed"
       hx-swap="outerHTML">
    Loading...
  </div>
</div>''',
            "view": '''def items_list(request):
    page = int(request.GET.get("page", 1))
    items = Model.objects.all()[(page-1)*20:page*20]
    has_more = Model.objects.count() > page * 20
    return render(request, "partials/items.html", {
        "items": items, "next_page": page + 1 if has_more else None
    })'''
        },
        "delete_confirm": {
            "name": "Delete with Confirm",
            "category": "forms",
            "description": "Delete with confirmation",
            "html": '''<button hx-delete="/delete/{{ id }}/"
        hx-confirm="Are you sure?"
        hx-target="closest tr"
        hx-swap="outerHTML swap:1s">
  Delete
</button>''',
            "view": '''def delete_item(request, pk):
    obj = get_object_or_404(Model, pk=pk)
    obj.delete()
    return HttpResponse("")  # Empty response removes element'''
        },
        "form_validation": {
            "name": "Inline Validation",
            "category": "forms",
            "description": "Real-time field validation",
            "html": '''<input type="email" name="email"
       hx-post="/validate/email/"
       hx-trigger="blur"
       hx-target="next .error">
<span class="error"></span>''',
            "view": '''def validate_email(request):
    email = request.POST.get("email", "")
    if Model.objects.filter(email=email).exists():
        return HttpResponse('<span class="error text-red-500">Email already exists</span>')
    return HttpResponse('<span class="error text-green-500">✓</span>')'''
        },
    }
    
    # Filter by category
    if params.category:
        patterns = {k: v for k, v in patterns.items() if v['category'] == params.category}
    
    if not patterns:
        return f"No patterns found for category '{params.category}'"
    
    lines = ["# 📚 HTMX Patterns for Django", ""]
    
    categories = {}
    for key, pattern in patterns.items():
        cat = pattern['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((key, pattern))
    
    for category, items in sorted(categories.items()):
        lines.append(f"## {category.title()}")
        lines.append("")
        
        for key, pattern in items:
            lines.append(f"### {pattern['name']}")
            lines.append(f"*{pattern['description']}*")
            lines.append("")
            lines.append("**HTML:**")
            lines.append(f"```html\n{pattern['html']}\n```")
            lines.append("")
            lines.append("**Django View:**")
            lines.append(f"```python\n{pattern['view']}\n```")
            lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# UI Consistency Checker
# =============================================================================

class CheckUIConsistencyInput(BaseModel):
    """Input for UI consistency check."""
    model_config = ConfigDict(extra='forbid')
    
    hub_path: str = Field(..., description="Path to hub app directory (e.g., 'apps/cad_hub')")
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


# Standard UI patterns for BF Agent hubs
UI_STANDARDS = {
    "base_template": {
        "standard": "base.html",
        "description": "All hubs should extend the central base.html template"
    },
    "css_framework": {
        "standard": "Bootstrap 5",
        "indicators": ["bootstrap", "btn-primary", "container", "row", "col-"],
        "non_standard": ["tailwindcss", "tailwind.config", "bg-slate", "text-slate"]
    },
    "navigation": {
        "standard": "Dynamic (NavigationSection/NavigationItem from DB)",
        "static_indicators": ["_nav.html", "hardcoded menu", "static navigation"],
        "dynamic_indicators": [
            "{% load navigation_tags %}",
            "{% dynamic_sidebar",
            "{% get_navigation_for_domain",
            "dynamic_navigation",
            "NavigationSection",
            "NavigationItem",
            "navigation_items"
        ],
        "description": "Navigation should be loaded from DB via context processor or template tags"
    },
    "theme": {
        "standard": "Light theme with hub-specific accent colors",
        "dark_indicators": ["bg-slate-950", "bg-slate-900", "dark:", "text-white"]
    },
    "js_framework": {
        "standard": "HTMX + jQuery/Vanilla JS",
        "non_standard": ["alpinejs", "alpine.js", "x-data", "x-show"]
    },
    "breadcrumbs": {
        "standard": "{% include 'bfagent/includes/breadcrumb.html' %}",
        "description": "All pages should include breadcrumb navigation",
        "indicators": ["breadcrumb", "bfagent/includes/breadcrumb"]
    },
    "bug_reporter": {
        "standard": "{% include 'bfagent/includes/bug_reporter.html' %}",
        "description": "All pages should include Bug/Feature reporter buttons",
        "indicators": ["bug_reporter", "bug-reporter-btn", "requirement-creator-btn"]
    }
}


@mcp.tool(
    name="check_ui_consistency",
    annotations={
        "title": "Check UI Consistency",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def check_ui_consistency(params: CheckUIConsistencyInput) -> str:
    """
    Check a hub's templates for UI consistency with BF Agent standards.
    
    Checks for:
    - Base template usage (should use central base.html)
    - CSS framework (should use Bootstrap 5, not Tailwind)
    - Navigation pattern (should use dynamic navigation from DB)
    - Theme consistency (light theme standard)
    - JavaScript framework (HTMX standard, not Alpine.js)
    
    Returns issues with suggestions for migration.
    """
    hub_path = Path(params.hub_path)
    
    if not hub_path.exists():
        # Try relative to common locations
        for base in [Path("."), Path("apps"), Path("/home/dehnert/github/bfagent")]:
            test_path = base / params.hub_path
            if test_path.exists():
                hub_path = test_path
                break
    
    if not hub_path.exists():
        return f"❌ Hub path not found: {params.hub_path}"
    
    # Find templates directory
    templates_dir = hub_path / "templates"
    if not templates_dir.exists():
        # Try nested structure
        for subdir in hub_path.iterdir():
            if subdir.is_dir() and (subdir / "templates").exists():
                templates_dir = subdir / "templates"
                break
    
    if not templates_dir.exists():
        return f"❌ No templates directory found in {hub_path}"
    
    issues = []
    warnings = []
    info = []
    
    # Scan all HTML templates
    template_files = list(templates_dir.rglob("*.html"))
    
    if not template_files:
        return f"❌ No HTML templates found in {templates_dir}"
    
    # Analysis results
    base_templates_used = set()
    css_frameworks = {"bootstrap": 0, "tailwind": 0}
    js_frameworks = {"htmx": 0, "alpine": 0, "jquery": 0}
    has_static_nav = False
    has_dynamic_nav = False
    has_dark_theme = False
    has_breadcrumbs = False
    has_bug_reporter = False
    templates_without_breadcrumbs = []
    dynamic_nav_indicators_found = []
    
    # Dynamic navigation indicators to check for
    dynamic_nav_patterns = [
        ("{% load navigation_tags %}", "navigation_tags loaded"),
        ("{% dynamic_sidebar", "dynamic_sidebar tag"),
        ("{% get_navigation_for_domain", "get_navigation_for_domain tag"),
        ("dynamic_navigation", "dynamic_navigation context"),
        ("navigation_items", "navigation_items iteration"),
        ("NavigationSection", "NavigationSection reference"),
        ("NavigationItem", "NavigationItem reference"),
    ]
    
    for template_file in template_files:
        try:
            content = template_file.read_text(encoding='utf-8', errors='ignore')
            rel_path = template_file.relative_to(templates_dir)
            
            # Check extends directive
            extends_match = re.search(r'{%\s*extends\s*["\']([^"\']+)["\']', content)
            if extends_match:
                base_templates_used.add(extends_match.group(1))
            
            # Check CSS framework
            if "tailwindcss" in content or "tailwind.config" in content or "cdn.tailwindcss.com" in content:
                css_frameworks["tailwind"] += 1
            if "bootstrap" in content.lower() or "btn-primary" in content or "container-fluid" in content:
                css_frameworks["bootstrap"] += 1
            
            # Check for dark theme indicators
            if any(ind in content for ind in ["bg-slate-950", "bg-slate-900", "bg-gray-900", "text-slate-100"]):
                has_dark_theme = True
            
            # Check JS frameworks
            if "htmx" in content.lower() or "hx-" in content:
                js_frameworks["htmx"] += 1
            if "alpinejs" in content.lower() or "alpine" in content.lower() or "x-data" in content:
                js_frameworks["alpine"] += 1
            
            # Check for dynamic navigation patterns
            for pattern, desc in dynamic_nav_patterns:
                if pattern in content:
                    has_dynamic_nav = True
                    if desc not in dynamic_nav_indicators_found:
                        dynamic_nav_indicators_found.append(desc)
            
            # Check for static navigation (hardcoded nav in _nav.html without dynamic elements)
            if "_nav.html" in str(rel_path) or ("nav" in str(rel_path).lower() and "partial" in str(rel_path).lower()):
                # Check if it's hardcoded vs dynamic
                is_dynamic = any(pattern in content for pattern, _ in dynamic_nav_patterns)
                if not is_dynamic and "{% for" not in content:
                    has_static_nav = True
            
            # Check for breadcrumbs (only in non-partial, non-base templates)
            if "breadcrumb" in content or "bfagent/includes/breadcrumb" in content:
                has_breadcrumbs = True
            elif extends_match and "partial" not in str(rel_path).lower() and "base" not in str(rel_path).lower():
                # This is a page template that should have breadcrumbs
                if "block content" in content:
                    templates_without_breadcrumbs.append(str(rel_path))
            
            # Check for bug reporter
            if "bug_reporter" in content or "bug-reporter-btn" in content or "bfagent/includes/bug_reporter" in content:
                has_bug_reporter = True
                    
        except Exception as e:
            warnings.append(f"Could not read {template_file}: {e}")
    
    # Analyze findings
    hub_name = hub_path.name
    
    # 1. Base template check
    non_standard_bases = [b for b in base_templates_used if b != "base.html" and "base.html" not in b]
    if non_standard_bases:
        for base in non_standard_bases:
            if hub_name in base:  # e.g., "cad_hub/base.html"
                issues.append({
                    "type": "BASE_TEMPLATE",
                    "severity": "high",
                    "message": f"Uses own base template: {base}",
                    "suggestion": "Migrate to: {% extends \"base.html\" %}",
                    "standard": UI_STANDARDS["base_template"]["standard"]
                })
    
    # 2. CSS framework check
    if css_frameworks["tailwind"] > 0 and css_frameworks["bootstrap"] == 0:
        issues.append({
            "type": "CSS_FRAMEWORK",
            "severity": "high",
            "message": f"Uses Tailwind CSS ({css_frameworks['tailwind']} files)",
            "suggestion": "Migrate to Bootstrap 5 for consistency",
            "standard": UI_STANDARDS["css_framework"]["standard"]
        })
    elif css_frameworks["tailwind"] > 0 and css_frameworks["bootstrap"] > 0:
        warnings.append({
            "type": "CSS_FRAMEWORK",
            "severity": "medium",
            "message": "Mixed CSS frameworks (Tailwind + Bootstrap)",
            "suggestion": "Consolidate to Bootstrap 5 only"
        })
    
    # 3. Navigation check
    if has_static_nav and not has_dynamic_nav:
        issues.append({
            "type": "NAVIGATION",
            "severity": "high",
            "message": "Uses static navigation (_nav.html with hardcoded items)",
            "suggestion": "Migrate to dynamic navigation: {% load navigation_tags %}{% dynamic_sidebar %}",
            "standard": UI_STANDARDS["navigation"]["standard"]
        })
    elif has_static_nav and has_dynamic_nav:
        warnings.append({
            "type": "NAVIGATION",
            "severity": "medium",
            "message": "Mixed navigation (some static, some dynamic)",
            "suggestion": "Consolidate all navigation to use dynamic DB-driven system"
        })
    elif not has_dynamic_nav:
        # No navigation at all detected - might be using base template nav
        info.append({
            "type": "NAVIGATION",
            "message": f"No explicit navigation found - may be inherited from base template",
            "dynamic_indicators": dynamic_nav_indicators_found
        })
    
    # 4. Theme check
    if has_dark_theme:
        issues.append({
            "type": "THEME",
            "severity": "medium",
            "message": "Uses dark theme (slate/gray-900 backgrounds)",
            "suggestion": "Use light theme with hub-specific accent colors",
            "standard": UI_STANDARDS["theme"]["standard"]
        })
    
    # 5. JS framework check
    if js_frameworks["alpine"] > 0 and js_frameworks["htmx"] == 0:
        issues.append({
            "type": "JS_FRAMEWORK",
            "severity": "medium",
            "message": f"Uses Alpine.js ({js_frameworks['alpine']} files) instead of HTMX",
            "suggestion": "Migrate to HTMX for consistency with other hubs",
            "standard": UI_STANDARDS["js_framework"]["standard"]
        })
    
    # 6. Breadcrumbs check
    if not has_breadcrumbs and templates_without_breadcrumbs:
        issues.append({
            "type": "BREADCRUMBS",
            "severity": "medium",
            "message": f"Missing breadcrumb navigation ({len(templates_without_breadcrumbs)} templates)",
            "suggestion": "Add: {% include 'bfagent/includes/breadcrumb.html' %}",
            "standard": UI_STANDARDS["breadcrumbs"]["standard"],
            "affected_templates": templates_without_breadcrumbs[:5]  # Show first 5
        })
    
    # 7. Bug Reporter check
    if not has_bug_reporter:
        issues.append({
            "type": "BUG_REPORTER",
            "severity": "low",
            "message": "Missing Bug/Feature reporter buttons",
            "suggestion": "Add: {% include 'bfagent/includes/bug_reporter.html' %}",
            "standard": UI_STANDARDS["bug_reporter"]["standard"]
        })
    
    # Format output
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "hub": hub_name,
            "templates_scanned": len(template_files),
            "issues": issues,
            "warnings": warnings,
            "info": info,
            "summary": {
                "base_templates": list(base_templates_used),
                "css_frameworks": css_frameworks,
                "js_frameworks": js_frameworks,
                "has_dark_theme": has_dark_theme,
                "has_static_nav": has_static_nav,
                "has_dynamic_nav": has_dynamic_nav,
                "dynamic_nav_indicators": dynamic_nav_indicators_found,
                "has_breadcrumbs": has_breadcrumbs,
                "has_bug_reporter": has_bug_reporter
            }
        }, indent=2)
    
    # Markdown output
    lines = [f"# 🎨 UI Consistency Report: {hub_name}", ""]
    lines.append(f"**Templates scanned:** {len(template_files)}")
    lines.append("")
    
    if not issues and not warnings:
        lines.append("✅ **All checks passed!** Hub follows UI standards.")
    else:
        if issues:
            lines.append("## ❌ Issues")
            lines.append("")
            for issue in issues:
                lines.append(f"### {issue['type']}")
                lines.append(f"**Severity:** {issue['severity'].upper()}")
                lines.append(f"**Problem:** {issue['message']}")
                lines.append(f"**Standard:** {issue['standard']}")
                lines.append(f"**Suggestion:** {issue['suggestion']}")
                lines.append("")
        
        if warnings:
            lines.append("## ⚠️ Warnings")
            lines.append("")
            for warn in warnings:
                if isinstance(warn, dict):
                    lines.append(f"- **{warn['type']}:** {warn['message']}")
                else:
                    lines.append(f"- {warn}")
            lines.append("")
    
    # Summary
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"- **Base templates used:** {', '.join(base_templates_used) or 'None detected'}")
    lines.append(f"- **CSS:** Bootstrap ({css_frameworks['bootstrap']}), Tailwind ({css_frameworks['tailwind']})")
    lines.append(f"- **JS:** HTMX ({js_frameworks['htmx']}), Alpine ({js_frameworks['alpine']})")
    lines.append(f"- **Dark theme:** {'Yes ⚠️' if has_dark_theme else 'No ✅'}")
    lines.append(f"- **Static nav:** {'Yes ⚠️' if has_static_nav else 'No ✅'}")
    lines.append(f"- **Dynamic nav:** {'Yes ✅' if has_dynamic_nav else 'No ⚠️'}")
    if dynamic_nav_indicators_found:
        lines.append(f"  - *Detected:* {', '.join(dynamic_nav_indicators_found)}")
    lines.append(f"- **Breadcrumbs:** {'Yes ✅' if has_breadcrumbs else 'No ⚠️'}")
    lines.append(f"- **Bug/Feature Reporter:** {'Yes ✅' if has_bug_reporter else 'No ⚠️'}")
    
    return "\n".join(lines)


class AnalyzeAllHubsInput(BaseModel):
    """Input for analyzing all hubs."""
    model_config = ConfigDict(extra='forbid')
    
    apps_path: str = Field(default="apps", description="Path to apps directory")
    response_format: ResponseFormat = ResponseFormat.MARKDOWN


@mcp.tool(
    name="analyze_all_hubs_ui",
    annotations={
        "title": "Analyze All Hubs UI",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def analyze_all_hubs_ui(params: AnalyzeAllHubsInput) -> str:
    """
    Analyze UI consistency across all hub applications.
    
    Scans all *_hub directories in the apps folder and checks each
    for UI consistency with BF Agent standards.
    """
    apps_path = Path(params.apps_path)
    
    if not apps_path.exists():
        for base in [Path("."), Path("/home/dehnert/github/bfagent")]:
            test_path = base / params.apps_path
            if test_path.exists():
                apps_path = test_path
                break
    
    if not apps_path.exists():
        return f"❌ Apps path not found: {params.apps_path}"
    
    # Find all hub directories
    hub_dirs = [d for d in apps_path.iterdir() if d.is_dir() and "_hub" in d.name]
    
    if not hub_dirs:
        return "❌ No hub directories found (looking for *_hub pattern)"
    
    results = []
    
    for hub_dir in sorted(hub_dirs):
        check_input = CheckUIConsistencyInput(
            hub_path=str(hub_dir),
            response_format=ResponseFormat.JSON
        )
        result_json = await check_ui_consistency(check_input)
        try:
            result = json.loads(result_json)
            results.append(result)
        except:
            results.append({"hub": hub_dir.name, "error": result_json})
    
    # Format summary
    lines = ["# 🏠 UI Consistency Analysis - All Hubs", ""]
    lines.append(f"**Hubs analyzed:** {len(results)}")
    lines.append("")
    
    # Summary table - Nav column now shows dynamic status
    lines.append("| Hub | Issues | CSS | Theme | Nav | Bread | Bug |")
    lines.append("|-----|--------|-----|-------|-----|-------|-----|")
    
    total_issues = 0
    for r in results:
        if "error" in r:
            lines.append(f"| {r['hub']} | ❌ Error | - | - | - | - | - |")
            continue
            
        issues = len(r.get('issues', []))
        warnings = len(r.get('warnings', []))
        total_issues += issues
        
        summary = r.get('summary', {})
        css = summary.get('css_frameworks', {})
        css_str = "✅ BS" if css.get('bootstrap', 0) > 0 and css.get('tailwind', 0) == 0 else "⚠️ TW" if css.get('tailwind', 0) > 0 else "?"
        theme = "⚠️ Dark" if summary.get('has_dark_theme') else "✅"
        
        # Navigation: show dynamic vs static status
        has_dynamic = summary.get('has_dynamic_nav', False)
        has_static = summary.get('has_static_nav', False)
        if has_dynamic and not has_static:
            nav = "✅ Dyn"
        elif has_static and not has_dynamic:
            nav = "⚠️ Static"
        elif has_static and has_dynamic:
            nav = "⚡ Mixed"
        else:
            nav = "? None"
        
        bread = "✅" if summary.get('has_breadcrumbs') else "⚠️"
        bug = "✅" if summary.get('has_bug_reporter') else "⚠️"
        
        status = "✅" if issues == 0 else f"❌ {issues}"
        lines.append(f"| {r['hub']} | {status} | {css_str} | {theme} | {nav} | {bread} | {bug} |")
    
    lines.append("")
    
    # Detailed issues per hub
    if total_issues > 0:
        lines.append("## 📋 Detailed Issues")
        lines.append("")
        
        for r in results:
            if "error" in r or not r.get('issues'):
                continue
            
            lines.append(f"### {r['hub']}")
            for issue in r['issues']:
                lines.append(f"- **{issue['type']}:** {issue['message']}")
                lines.append(f"  - *Suggestion:* {issue['suggestion']}")
            lines.append("")
    
    # Migration priority
    lines.append("## 🎯 Migration Priority")
    lines.append("")
    priority_hubs = [r for r in results if not "error" in r and len(r.get('issues', [])) > 0]
    priority_hubs.sort(key=lambda x: len(x.get('issues', [])), reverse=True)
    
    for i, hub in enumerate(priority_hubs, 1):
        lines.append(f"{i}. **{hub['hub']}** - {len(hub['issues'])} issues")
    
    if not priority_hubs:
        lines.append("✅ All hubs are consistent!")
    
    return "\n".join(lines)


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point for the MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Quality + HTMX MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mechanism"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port for HTTP transport"
    )
    
    args = parser.parse_args()
    
    if args.transport == "http":
        mcp.run(transport="streamable_http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
