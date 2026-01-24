#!/usr/bin/env python3
"""
BF Agent HTMX Scanner v4 - Professional Edition
==============================================
Optimized for performance, maintainability, and accuracy

Key Improvements:
- Modular architecture with better separation of concerns
- Async I/O for improved performance
- Better error handling and recovery
- Reduced false positives
- Enhanced pattern matching
- Professional logging and reporting
"""

import argparse
import ast
import asyncio
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml

# Constants
HTMX_VERSION = "1.9.10"
SCANNER_VERSION = "4.0.0"
DEFAULT_NAMESPACE = "bfagent"


class Severity(Enum):
    """Issue severity levels"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(Enum):
    """Issue categories"""

    TEMPLATE = "template"
    VIEW = "view"
    JAVASCRIPT = "javascript"
    CONFIGURATION = "configuration"
    ARCHITECTURE = "architecture"


@dataclass(frozen=True)
class HTMXIssue:
    """Immutable issue representation"""

    file_path: str
    line_number: int
    issue_type: str
    description: str
    current_code: str
    suggested_fix: str
    severity: Severity
    category: IssueCategory
    auto_fixable: bool = False
    context_lines: Tuple[str, ...] = field(default_factory=tuple)

    def __hash__(self):
        return hash((self.file_path, self.line_number, self.issue_type))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'issue_type': self.issue_type,
            'description': self.description,
            'current_code': self.current_code,
            'suggested_fix': self.suggested_fix,
            'severity': self.severity.value,
            'category': self.category.value,
            'auto_fixable': self.auto_fixable,
            'context_lines': list(self.context_lines)
        }


@dataclass
class ScanStatistics:
    """Detailed scan statistics"""

    total_files: int = 0
    files_with_issues: int = 0
    total_lines_scanned: int = 0
    scan_duration: float = 0.0
    issues_by_type: Dict[str, int] = field(default_factory=dict)
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    auto_fixable_count: int = 0
    architecture_compliance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanConfig:
    """Scanner configuration"""

    project_path: Path
    ignore_patterns: Set[str] = field(
        default_factory=lambda: {
            "*/migrations/*",
            "*/static/vendor/*",
            "*/node_modules/*",
            "*/.venv/*",
            "*/venv/*",
            "*/__pycache__/*",
            "*.pyc",
        }
    )
    custom_targets: Set[str] = field(default_factory=set)
    check_javascript: bool = True
    check_views: bool = True
    parallel_scanning: bool = True
    max_workers: int = 4
    strict_mode: bool = False
    project_namespace: str = DEFAULT_NAMESPACE
    check_zero_hardcoding: bool = True
    output_format: str = "json"
    verbose: bool = False
    auto_fix: bool = False
    dry_run: bool = False


class PatternCache:
    """LRU cache for compiled regex patterns"""

    def __init__(self, max_size: int = 128):
        self._cache = {}
        self._max_size = max_size

    @lru_cache(maxsize=128)
    def get_pattern(self, pattern: str, flags: int = 0) -> re.Pattern:
        """Get or compile regex pattern"""
        return re.compile(pattern, flags)


class HTMXPatterns:
    """Centralized HTMX pattern definitions"""

    def __init__(self, namespace: str = DEFAULT_NAMESPACE):
        self.namespace = namespace
        self.cache = PatternCache()

    @property
    def htmx_attributes(self) -> Set[str]:
        """Core HTMX attributes"""
        return {
            "hx-get",
            "hx-post",
            "hx-put",
            "hx-delete",
            "hx-patch",
            "hx-trigger",
            "hx-target",
            "hx-swap",
            "hx-indicator",
            "hx-push-url",
            "hx-select",
            "hx-ext",
            "hx-headers",
            "hx-include",
            "hx-params",
            "hx-vals",
            "hx-confirm",
            "hx-disable",
            "hx-replace-url",
            "hx-swap-oob",
        }

    @property
    def security_patterns(self) -> Dict[str, re.Pattern]:
        """Security-related patterns"""
        return {
            "csrf_missing": self.cache.get_pattern(
                r"<form[^>]*(?:hx-post|hx-put|hx-delete|hx-patch)[^>]*>"
                r"(?:(?!{% csrf_token %}|{{\s*csrf_token\s*}})[\s\S])*?</form>",
                re.IGNORECASE | re.MULTILINE,
            ),
            "unsafe_target": self.cache.get_pattern(
                r'hx-target=["\']#?(user-input|dynamic-.*?)["\']', re.IGNORECASE
            ),
            "eval_usage": self.cache.get_pattern(
                r'hx-on[^=]*=["\']*.*?eval\s*\([^)]*\)', re.IGNORECASE
            ),
        }

    @property
    def architecture_patterns(self) -> Dict[str, re.Pattern]:
        """BF Agent architecture patterns"""
        return {
            "hardcoded_url": self.cache.get_pattern(
                rf'(?:href|hx-get|hx-post|hx-put|hx-delete)=["\']'
                rf'(?!.*{{% url|{{{{|#|javascript:|mailto:)(/[^"\']*)["\']',
                re.IGNORECASE,
            ),
            "missing_namespace": self.cache.get_pattern(
                rf'{{% url ["\'](?!{self.namespace}:)', re.IGNORECASE
            ),
            "hardcoded_id": self.cache.get_pattern(
                r'(?:id|hx-target)=["\']#?(?!{%|{{)[\w-]+["\']', re.IGNORECASE
            ),
        }


class FileScanner:
    """Efficient file scanning with caching"""

    def __init__(self, config: ScanConfig):
        self.config = config
        self.patterns = HTMXPatterns(config.project_namespace)
        self.logger = logging.getLogger(__name__)

    def should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned"""
        path_str = str(file_path)

        # Check ignore patterns
        for pattern in self.config.ignore_patterns:
            if file_path.match(pattern):
                return False

        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > 1_000_000:  # 1MB
                self.logger.warning(f"Skipping large file: {file_path}")
                return False
        except OSError:
            return False

        return True

    @lru_cache(maxsize=256)
    def read_file_cached(self, file_path: Path) -> Optional[str]:
        """Read file with caching"""
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None


class TemplateScanner(FileScanner):
    """Specialized template scanner"""

    def scan_file(self, file_path: Path) -> List[HTMXIssue]:
        """Scan a single template file"""
        if not self.should_scan_file(file_path):
            return []

        content = self.read_file_cached(file_path)
        if not content:
            return []

        issues = []
        lines = content.splitlines()

        # Check for HTMX library inclusion
        if self._is_main_template(content) and "htmx.org" not in content:
            issues.append(
                HTMXIssue(
                    file_path=str(file_path),
                    line_number=1,
                    issue_type="missing_htmx_library",
                    description="Main template missing HTMX library",
                    current_code="",
                    suggested_fix='<script src="https://unpkg.com/htmx.org@'
                    + HTMX_VERSION
                    + '"></script>',
                    severity=Severity.CRITICAL,
                    category=IssueCategory.TEMPLATE,
                    auto_fixable=True,
                )
            )

        # Security checks
        issues.extend(self._check_security_patterns(file_path, content, lines))

        # Architecture checks
        if self.config.check_zero_hardcoding:
            issues.extend(self._check_architecture_patterns(file_path, content, lines))

        # HTMX best practices
        issues.extend(self._check_htmx_patterns(file_path, content, lines))

        return issues

    def _is_main_template(self, content: str) -> bool:
        """Check if template is a main template (not partial)"""
        indicators = ["{% extends", "{% include", "_partial.html", "_form.html"]
        return not any(indicator in content for indicator in indicators)

    def _check_security_patterns(
        self, file_path: Path, content: str, lines: List[str]
    ) -> List[HTMXIssue]:
        """Check for security issues"""
        issues = []

        for pattern_name, pattern in self.patterns.security_patterns.items():
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1

                if pattern_name == "csrf_missing":
                    issues.append(
                        HTMXIssue(
                            file_path=str(file_path),
                            line_number=line_num,
                            issue_type="csrf_token_missing",
                            description="Form with HTMX POST/PUT/DELETE missing CSRF token",
                            current_code=(
                                lines[line_num - 1].strip() if line_num <= len(lines) else ""
                            ),
                            suggested_fix="Add {% csrf_token %} inside the form",
                            severity=Severity.CRITICAL,
                            category=IssueCategory.TEMPLATE,
                            auto_fixable=True,
                        )
                    )

        return issues

    def _check_architecture_patterns(
        self, file_path: Path, content: str, lines: List[str]
    ) -> List[HTMXIssue]:
        """Check for architecture compliance"""
        issues = []

        # Check for hardcoded URLs
        hardcoded_pattern = self.patterns.architecture_patterns["hardcoded_url"]
        for match in hardcoded_pattern.finditer(content):
            url = match.group(1)
            if not self._is_django_pattern(url):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    HTMXIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="hardcoded_url",
                        description=f"Hardcoded URL found: {url}",
                        current_code=lines[line_num - 1].strip() if line_num <= len(lines) else "",
                        suggested_fix=f"Use {{% url '{self.config.project_namespace}:view-name' %}}",
                        severity=Severity.WARNING,
                        category=IssueCategory.ARCHITECTURE,
                        auto_fixable=False,
                    )
                )

        return issues

    def _check_htmx_patterns(
        self, file_path: Path, content: str, lines: List[str]
    ) -> List[HTMXIssue]:
        """Check HTMX best practices"""
        issues = []

        # Check for corrupted URL tags (critical - from V3)
        corrupted_url_pattern = self.patterns.cache.get_pattern(
            r'{%\s*url\s+[\'"](?P<corrupted>.*?hx-[a-z]+.*?)[\'"](?P<params>.*?)%}', re.IGNORECASE
        )
        for match in corrupted_url_pattern.finditer(content):
            corrupted = match.group("corrupted")
            if "hx-" in corrupted:
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    HTMXIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="corrupted_url_tag",
                        description=f"Corrupted Django URL tag with embedded HTMX attributes: {corrupted[:50]}...",
                        current_code=lines[line_num - 1].strip() if line_num <= len(lines) else "",
                        suggested_fix="Separate HTMX attributes from {% url %} tag - put HTMX attributes as element attributes",
                        severity=Severity.CRITICAL,
                        category=IssueCategory.TEMPLATE,
                        auto_fixable=True,
                    )
                )

        # Check forms for response-targets extension
        form_pattern = self.patterns.cache.get_pattern(
            r"<form[^>]*hx-(?:post|put|patch)[^>]*>", re.IGNORECASE
        )

        for match in form_pattern.finditer(content):
            form_tag = match.group(0)
            if 'hx-ext="response-targets"' not in form_tag:
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    HTMXIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="missing_response_targets",
                        description="Form missing response-targets extension",
                        current_code=form_tag,
                        suggested_fix='Add hx-ext="response-targets" hx-target-422="this"',
                        severity=Severity.WARNING,
                        category=IssueCategory.TEMPLATE,
                        auto_fixable=True,
                    )
                )

        return issues

    def _is_django_pattern(self, url: str) -> bool:
        """Check if URL is a Django pattern"""
        django_indicators = ["{{", "{%", "static", "media"]
        return any(indicator in url for indicator in django_indicators)


class ViewScanner(FileScanner):
    """Specialized view scanner using AST"""

    def scan_file(self, file_path: Path) -> List[HTMXIssue]:
        """Scan a Python view file"""
        if not self.should_scan_file(file_path):
            return []

        content = self.read_file_cached(file_path)
        if not content:
            return []

        try:
            tree = ast.parse(content)
            return self._analyze_ast(file_path, tree, content.splitlines())
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path}: {e}")
            return []

    def _analyze_ast(self, file_path: Path, tree: ast.AST, lines: List[str]) -> List[HTMXIssue]:
        """Analyze AST for HTMX patterns"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for proper 422 handling in form views
                if self._is_form_view(node):
                    has_422 = self._check_422_response(node)
                    if not has_422:
                        issues.append(
                            HTMXIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                issue_type="missing_422_response",
                                description=f"Form view '{node.name}' should return 422 for validation errors",
                                current_code=f"def {node.name}(...)",
                                suggested_fix="Return HttpResponse(rendered_form, status=422) on validation errors",
                                severity=Severity.WARNING,
                                category=IssueCategory.VIEW,
                                auto_fixable=False,
                            )
                        )

        return issues

    def _is_form_view(self, node: ast.FunctionDef) -> bool:
        """Check if function is likely a form view"""
        # Look for form-related patterns
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if "form" in child.id.lower():
                    return True
            if isinstance(child, ast.Attribute):
                if "is_valid" in child.attr:
                    return True
        return False

    def _check_422_response(self, node: ast.FunctionDef) -> bool:
        """Check if function returns 422 status"""
        for child in ast.walk(node):
            if isinstance(child, ast.Num) and child.n == 422:
                return True
            if isinstance(child, ast.Constant) and child.value == 422:
                return True
        return False


class JavaScriptScanner(FileScanner):
    """JavaScript file scanner"""

    def scan_file(self, file_path: Path) -> List[HTMXIssue]:
        """Scan JavaScript file"""
        if not self.should_scan_file(file_path):
            return []

        content = self.read_file_cached(file_path)
        if not content:
            return []

        issues = []

        # Check for HTMX CSRF configuration
        if "htmx" in content.lower() and "configRequest" not in content:
            issues.append(
                HTMXIssue(
                    file_path=str(file_path),
                    line_number=1,
                    issue_type="missing_csrf_config",
                    description="JavaScript uses HTMX but lacks CSRF configuration",
                    current_code="",
                    suggested_fix="""document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;
});""",
                    severity=Severity.WARNING,
                    category=IssueCategory.JAVASCRIPT,
                    auto_fixable=False,
                )
            )

        return issues


class HTMXScanner:
    """Main scanner orchestrator"""

    def __init__(self, config: ScanConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.template_scanner = TemplateScanner(config)
        self.view_scanner = ViewScanner(config)
        self.js_scanner = JavaScriptScanner(config)

    def _setup_logging(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def scan_async(self) -> Tuple[List[HTMXIssue], ScanStatistics]:
        """Perform asynchronous scan"""
        start_time = datetime.now()
        all_issues = []
        stats = ScanStatistics()

        # Collect all files to scan
        template_files = list(self.config.project_path.rglob("*.html"))
        view_files = list(self.config.project_path.rglob("**/views*.py"))
        js_files = (
            list(self.config.project_path.rglob("*.js")) if self.config.check_javascript else []
        )

        all_files = template_files + view_files + js_files
        stats.total_files = len(all_files)

        # Scan files in parallel
        if self.config.parallel_scanning:
            all_issues = await self._scan_parallel(template_files, view_files, js_files)
        else:
            all_issues = self._scan_sequential(template_files, view_files, js_files)

        # Calculate statistics
        stats.scan_duration = (datetime.now() - start_time).total_seconds()
        stats.files_with_issues = len({issue.file_path for issue in all_issues})

        for issue in all_issues:
            stats.issues_by_type[issue.issue_type] = (
                stats.issues_by_type.get(issue.issue_type, 0) + 1
            )
            stats.issues_by_severity[issue.severity.value] = (
                stats.issues_by_severity.get(issue.severity.value, 0) + 1
            )
            stats.issues_by_category[issue.category.value] = (
                stats.issues_by_category.get(issue.category.value, 0) + 1
            )
            if issue.auto_fixable:
                stats.auto_fixable_count += 1

        return all_issues, stats

    async def _scan_parallel(self, template_files, view_files, js_files) -> List[HTMXIssue]:
        """Scan files in parallel using thread pool"""
        all_issues = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all scan tasks
            futures = []

            for file in template_files:
                futures.append(executor.submit(self.template_scanner.scan_file, file))
            for file in view_files:
                futures.append(executor.submit(self.view_scanner.scan_file, file))
            for file in js_files:
                futures.append(executor.submit(self.js_scanner.scan_file, file))

            # Collect results
            for future in futures:
                try:
                    issues = future.result()
                    all_issues.extend(issues)
                except Exception as e:
                    self.logger.error(f"Error in parallel scan: {e}")

        return all_issues

    def _scan_sequential(self, template_files, view_files, js_files) -> List[HTMXIssue]:
        """Scan files sequentially"""
        all_issues = []

        for file in template_files:
            all_issues.extend(self.template_scanner.scan_file(file))
        for file in view_files:
            all_issues.extend(self.view_scanner.scan_file(file))
        for file in js_files:
            all_issues.extend(self.js_scanner.scan_file(file))

        return all_issues

    def generate_report(self, issues: List[HTMXIssue], stats: ScanStatistics) -> Dict[str, Any]:
        """Generate comprehensive report"""
        # Calculate conformity score
        total_weight = 0
        penalty = 0

        for issue in issues:
            weight = (
                3
                if issue.severity == Severity.CRITICAL
                else 2 if issue.severity == Severity.WARNING else 1
            )
            total_weight += weight
            penalty += weight

        max_score = 100
        conformity_score = max(0, max_score - (penalty * 2))

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, stats)

        return {
            "version": SCANNER_VERSION,
            "scan_date": datetime.now().isoformat(),
            "project_path": str(self.config.project_path),
            "conformity_score": conformity_score,
            "statistics": asdict(stats),
            "issues": [issue.to_dict() for issue in issues],
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self, issues: List[HTMXIssue], stats: ScanStatistics
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Check for common patterns
        issue_types = Counter(issue.issue_type for issue in issues)

        if issue_types.get("hardcoded_url", 0) > 5:
            recommendations.append(
                f"Configure your IDE to use Django URL template tags. "
                f"Use the {self.config.project_namespace} namespace: "
                f"{{% url '{self.config.project_namespace}:view-name' %}}"
            )

        if issue_types.get("missing_response_targets", 0) > 0:
            recommendations.append(
                'For all forms, add: hx-ext="response-targets" hx-target-422="this" '
                "to enable proper validation error handling"
            )

        if issue_types.get("missing_422_response", 0) > 0:
            recommendations.append(
                "Update form views to return HttpResponse(rendered_form, status=422) "
                "when form validation fails"
            )

        if stats.auto_fixable_count > 0:
            recommendations.append(
                f"Run with --fix flag to automatically resolve {stats.auto_fixable_count} issues"
            )

        if self.config.check_zero_hardcoding:
            recommendations.append(
                "Review Zero-Hardcoding compliance: ensure all UI elements are "
                "generated from CRUDConfig, not hardcoded in templates"
            )

        return recommendations


class AutoFixer:
    """Automatic issue fixer"""

    def __init__(self, config: ScanConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.fixes_applied = 0

    def fix_issues(self, issues: List[HTMXIssue]) -> Dict[str, List[HTMXIssue]]:
        """Apply automatic fixes"""
        results = {"fixed": [], "skipped": [], "errors": []}

        # Group issues by file
        issues_by_file = defaultdict(list)
        for issue in issues:
            if issue.auto_fixable:
                issues_by_file[issue.file_path].append(issue)

        # Process each file
        for file_path, file_issues in issues_by_file.items():
            try:
                if self._fix_file(Path(file_path), file_issues):
                    results["fixed"].extend(file_issues)
                else:
                    results["skipped"].extend(file_issues)
            except Exception as e:
                self.logger.error(f"Error fixing {file_path}: {e}")
                results["errors"].extend(file_issues)

        return results

    def _fix_file(self, file_path: Path, issues: List[HTMXIssue]) -> bool:
        """Fix issues in a single file"""
        try:
            # Create backup
            if not self.config.dry_run:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')

            # Read file content
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            # Sort issues by line number (reverse order for safe replacement)
            issues_sorted = sorted(issues, key=lambda x: x.line_number, reverse=True)

            # Apply fixes
            for issue in issues_sorted:
                if issue.issue_type == "missing_htmx_library":
                    # Add HTMX library to head
                    lines = self._add_htmx_library(lines, issue.suggested_fix)
                elif issue.issue_type == "csrf_token_missing":
                    # Add CSRF token to form
                    lines = self._add_csrf_token(lines, issue.line_number)
                elif issue.issue_type == "missing_response_targets":
                    # Add response-targets to form
                    lines = self._add_response_targets(lines, issue.line_number)
                elif issue.issue_type == "corrupted_url_tag":
                    # Fix corrupted URL tags
                    lines = self._fix_corrupted_url_tag(
                        lines, issue.line_number, issue.current_code
                    )

            # Write fixed content
            if not self.config.dry_run:
                file_path.write_text("".join(lines), encoding="utf-8")

            self.fixes_applied += len(issues)
            return True

        except Exception as e:
            self.logger.error(f"Failed to fix {file_path}: {e}")
            return False

    def _add_htmx_library(self, lines: List[str], script_tag: str) -> List[str]:
        """Add HTMX library to template"""
        # Find </head> tag
        for i, line in enumerate(lines):
            if "</head>" in line.lower():
                # Insert before </head>
                lines.insert(i, f"    {script_tag}\n")
                break
        return lines

    def _add_csrf_token(self, lines: List[str], line_number: int) -> List[str]:
        """Add CSRF token to form"""
        if 0 < line_number <= len(lines):
            line = lines[line_number - 1]
            # Insert after opening form tag
            lines[line_number - 1] = line.rstrip() + "\n    {% csrf_token %}\n"
        return lines

    def _add_response_targets(self, lines: List[str], line_number: int) -> List[str]:
        """Add response-targets extension to form"""
        if 0 < line_number <= len(lines):
            line = lines[line_number - 1]
            # Add attributes to form tag
            lines[line_number - 1] = line.replace(
                "<form", '<form hx-ext="response-targets" hx-target-422="this"'
            )
        return lines

    def _fix_corrupted_url_tag(
        self, lines: List[str], line_number: int, current_code: str
    ) -> List[str]:
        """Fix corrupted URL tag by extracting HTMX attributes"""
        if 0 < line_number <= len(lines):
            line = lines[line_number - 1]

            # Pattern to find corrupted URL tags with HTMX attributes inside
            # Matches: {% url ' hx-xxx="yyy"bfagent:view-name' params %}
            pattern = r'{%\s*url\s+[\'"]([^\'"]*)hx-[^\'\"]*bfagent:([^\'\"]+)[\'"]'
            
            # Try to extract and fix
            match = re.search(pattern, line)
            if match:
                # Extract the view name (group 2 is the view name after 'bfagent:')
                view_name = match.group(2).strip()
                
                # Replace the corrupted URL tag with clean one
                # Keep everything after the URL tag (parameters, etc.)
                fixed_line = re.sub(
                    r'{%\s*url\s+[\'"][^\'\"]*hx-[^\'\"]*bfagent:([^\'\"]+)[\'"]',
                    r"{% url 'bfagent:\1'",
                    line
                )
                lines[line_number - 1] = fixed_line

        return lines


class ReportGenerator:
    """Generate reports in various formats"""

    def __init__(self, config: ScanConfig):
        self.config = config

    def generate(self, report: Dict[str, Any], format: str = "json") -> Path:
        """Generate report in specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            return self._generate_json(report, timestamp)
        elif format == "html":
            return self._generate_html(report, timestamp)
        elif format == "yaml":
            return self._generate_yaml(report, timestamp)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_json(self, report: Dict[str, Any], timestamp: str) -> Path:
        """Generate JSON report"""
        output_path = Path(f"htmx_report_{timestamp}.json")
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path

    def _generate_yaml(self, report: Dict[str, Any], timestamp: str) -> Path:
        """Generate YAML report"""
        output_path = Path(f"htmx_report_{timestamp}.yaml")
        output_path.write_text(yaml.dump(report, default_flow_style=False), encoding="utf-8")
        return output_path

    def _generate_html(self, report: Dict[str, Any], timestamp: str) -> Path:
        """Generate HTML report"""
        output_path = Path(f"htmx_report_{timestamp}.html")

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTMX Conformity Report - {timestamp}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        .score {{
            font-size: 3rem;
            font-weight: bold;
            margin: 1rem 0;
        }}
        .score.good {{ color: #10b981; }}
        .score.warning {{ color: #f59e0b; }}
        .score.critical {{ color: #ef4444; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .issue-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .issue-card.critical {{
            border-left: 4px solid #ef4444;
        }}
        .issue-card.warning {{
            border-left: 4px solid #f59e0b;
        }}
        .issue-card.info {{
            border-left: 4px solid #3b82f6;
        }}
        .code-block {{
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }}
        .recommendations {{
            background: #fef3c7;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #f59e0b;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>HTMX Conformity Report</h1>
        <p>Generated: {timestamp}</p>
        <div class="score {self._get_score_class(report['conformity_score'])}">
            Score: {report['conformity_score']}/100
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>Files Scanned</h3>
            <p>{report['statistics']['total_files']}</p>
        </div>
        <div class="stat-card">
            <h3>Issues Found</h3>
            <p>{sum(report['statistics']['issues_by_severity'].values())}</p>
        </div>
        <div class="stat-card">
            <h3>Auto-fixable</h3>
            <p>{report['statistics']['auto_fixable_count']}</p>
        </div>
        <div class="stat-card">
            <h3>Scan Duration</h3>
            <p>{report['statistics']['scan_duration']:.2f}s</p>
        </div>
    </div>

    <div class="recommendations">
        <h2>Recommendations</h2>
        <ol>
            {''.join(f"<li>{rec}</li>" for rec in report['recommendations'])}
        </ol>
    </div>

    <h2>Issues</h2>
    {self._generate_issues_html(report['issues'])}

</body>
</html>
"""
        output_path.write_text(html_content, encoding="utf-8")
        return output_path

    def _get_score_class(self, score: float) -> str:
        """Get CSS class for score"""
        if score >= 80:
            return "good"
        elif score >= 60:
            return "warning"
        else:
            return "critical"

    def _generate_issues_html(self, issues: List[Dict]) -> str:
        """Generate HTML for issues"""
        if not issues:
            return "<p>No issues found!</p>"

        html_parts = []
        for issue in issues[:50]:  # Limit to 50 issues in HTML
            severity_class = issue["severity"].lower()
            html_parts.append(
                f"""
<div class="issue-card {severity_class}">
    <h3>{issue['issue_type'].replace('_', ' ').title()}</h3>
    <p><strong>File:</strong> {issue['file_path']} (line {issue['line_number']})</p>
    <p><strong>Description:</strong> {issue['description']}</p>
    <div class="code-block">{issue['current_code']}</div>
    <p><strong>Fix:</strong> {issue['suggested_fix']}</p>
</div>
"""
            )

        if len(issues) > 50:
            html_parts.append(f"<p>... and {len(issues) - 50} more issues</p>")

        return "".join(html_parts)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="BF Agent HTMX Scanner v4 - Professional Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s .                    # Scan current directory
  %(prog)s /path/to/project     # Scan specific project
  %(prog)s . --fix              # Scan and auto-fix issues
  %(prog)s . --format html      # Generate HTML report
  %(prog)s . --parallel         # Enable parallel scanning
  %(prog)s . --strict           # Enable strict mode
""",
    )

    parser.add_argument("project_path", type=Path, help="Path to the project directory")

    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix issues where possible"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed without making changes"
    )

    parser.add_argument(
        "--format",
        choices=["json", "html", "yaml"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--parallel", action="store_true", help="Enable parallel scanning for better performance"
    )

    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )

    parser.add_argument(
        "--namespace",
        default=DEFAULT_NAMESPACE,
        help="Project namespace for URL patterns (default: bfagent)",
    )

    parser.add_argument("--no-js", action="store_true", help="Skip JavaScript file scanning")

    parser.add_argument("--no-views", action="store_true", help="Skip Python view file scanning")

    parser.add_argument("--strict", action="store_true", help="Enable strict mode (more checks)")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument("--ignore", action="append", help="Additional patterns to ignore")

    return parser


async def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Print banner
    print("🚀 BF Agent HTMX Scanner v4 - Professional Edition")
    print("=" * 50)

    # Create configuration
    config = ScanConfig(
        project_path=args.project_path.resolve(),
        check_javascript=not args.no_js,
        check_views=not args.no_views,
        parallel_scanning=args.parallel,
        max_workers=args.workers,
        strict_mode=args.strict,
        project_namespace=args.namespace,
        output_format=args.format,
        verbose=args.verbose,
        auto_fix=args.fix,
        dry_run=args.dry_run,
    )

    # Add custom ignore patterns
    if args.ignore:
        config.ignore_patterns.update(args.ignore)

    # Validate project path
    if not config.project_path.exists():
        print(f"❌ Error: Project path does not exist: {config.project_path}")
        sys.exit(1)

    print(f"Scanning {config.project_path}...")

    # Create scanner and run scan
    scanner = HTMXScanner(config)
    issues, stats = await scanner.scan_async()

    # Generate report
    report = scanner.generate_report(issues, stats)

    # Display summary
    print("\n📊 HTMX Conformity Report")
    print("=" * 50)

    score = report["conformity_score"]
    score_emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
    print(f"Conformity Score: {score_emoji} {score}/100")

    print(f"Files Scanned: {stats.total_files}")
    print(f"Total Issues: {len(issues)}")

    if stats.issues_by_severity:
        print(f"🚨 Critical: {stats.issues_by_severity.get('critical', 0)}")
        print(f"⚠️  Warnings: {stats.issues_by_severity.get('warning', 0)}")
        print(f"ℹ️  Info: {stats.issues_by_severity.get('info', 0)}")

    print(f"⚡ Scan Duration: {stats.scan_duration:.2f}s")

    # Display BF Agent specific stats
    if config.check_zero_hardcoding:
        hardcoding_issues = sum(1 for i in issues if "hardcoded" in i.issue_type)
        print(f"\n🏗️  BF Agent Architecture Compliance:")
        print(f"  Zero-Hardcoding Issues: {hardcoding_issues}")

    # Display recommendations
    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")

    # Save report
    report_gen = ReportGenerator(config)
    output_path = report_gen.generate(report, args.format)
    print(f"\n📄 Report saved as {output_path}")

    # Apply fixes if requested
    if args.fix or args.dry_run:
        fixable = [i for i in issues if i.auto_fixable]
        if fixable:
            print(f"\n🔧 {'Simulating' if args.dry_run else 'Applying'} automatic fixes...")

            fixer = AutoFixer(config)
            results = fixer.fix_issues(fixable)

            print(f"✅ Fixed: {len(results['fixed'])} issues")
            print(f"⏭️  Skipped: {len(results['skipped'])} issues")
            if results["errors"]:
                print(f"❌ Errors: {len(results['errors'])} issues")

            if not args.dry_run and results["fixed"]:
                print("\n✨ Fixes applied! Run the scanner again to verify.")

    # Exit with appropriate code
    exit_code = 0 if score >= 60 else 1
    if stats.issues_by_severity.get("critical", 0) > 0:
        exit_code = 1

    status_msg = (
        "✅ Scan completed successfully!" if exit_code == 0 else "⚠️  Issues found. Please review."
    )
    print(f"\n{status_msg}")

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
