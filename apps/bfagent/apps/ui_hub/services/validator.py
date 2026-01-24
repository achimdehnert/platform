"""Validation service for guardrail rules."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from django.db import models

from apps.ui_hub.models import GuardrailRule, RuleViolation, ValidationSession


class ValidationService:
    """Service for validating code against guardrail rules."""

    def __init__(self):
        """Initialize validation service."""
        self.active_rules = GuardrailRule.objects.filter(is_active=True).select_related("category")

    def validate_name(self, name: str, category: str) -> Dict:
        """Validate a name against category rules.

        Args:
            name: The name to validate
            category: Category (views, templates, urls, services, selectors)

        Returns:
            Dict with valid, violations, suggestions
        """
        rules = self.active_rules.filter(category__code__startswith=f"naming.{category}")

        violations = []
        suggestions = []

        for rule in rules:
            try:
                if rule.pattern:
                    pattern = re.compile(rule.pattern)
                    if not pattern.match(name):
                        violations.append(
                            {
                                "rule": rule.name,
                                "message": rule.message,
                                "severity": rule.severity,
                            }
                        )
                        if rule.suggestion:
                            suggestions.append(rule.suggestion)
            except re.error:
                continue

        return {
            "valid": len(violations) == 0,
            "name": name,
            "category": category,
            "violations": violations,
            "suggestions": suggestions,
        }

    def suggest_name(self, entity: str, action: str, category: str) -> str:
        """Suggest a correct name based on entity and action.

        Args:
            entity: Entity name (e.g., 'client', 'invoice')
            action: Action (e.g., 'list', 'create', 'delete')
            category: Category (views, templates, urls, etc.)

        Returns:
            Suggested name following conventions
        """
        patterns = {
            "views": f"{entity}_{action}_view",
            "templates": f"{entity}/{action}.html",
            "urls": f"{entity}-{action}",
            "services": f"{entity}_{action}",
            "selectors": f"{entity}_get_{action}",
            "htmx_ids": f"htmx-{entity}-{action}",
        }

        return patterns.get(category, f"{entity}_{action}")

    def validate_code(self, code: str, layer: str) -> Dict:
        """Validate code for separation of concerns.

        Args:
            code: Python code to validate
            layer: Layer (views, services, selectors, templates)

        Returns:
            Dict with valid, violations
        """
        rules = self.active_rules.filter(category__code__startswith=f"separation.{layer}")

        violations = []

        for rule in rules:
            try:
                if rule.pattern:
                    pattern = re.compile(rule.pattern, re.MULTILINE)
                    matches = pattern.findall(code)
                    if matches:
                        violations.append(
                            {
                                "rule": rule.name,
                                "message": rule.message,
                                "severity": rule.severity,
                                "matches": matches[:5],  # First 5 matches
                            }
                        )
            except re.error:
                continue

        return {
            "valid": len(violations) == 0,
            "layer": layer,
            "violations": violations,
        }

    def validate_htmx(self, code: str) -> Dict:
        """Validate HTMX code for common mistakes.

        Args:
            code: HTML/template code to validate

        Returns:
            Dict with valid, violations
        """
        rules = self.active_rules.filter(category__code__startswith="htmx.")

        violations = []

        # Common HTMX anti-patterns
        anti_patterns = [
            (r'hx-get=["\'][^"\']*\?', "Use hx-vals instead of query params in hx-get"),
            (r'hx-swap=["\']innerHTML["\']', "innerHTML is default, omit hx-swap"),
            (r'hx-trigger=["\']click["\']', "click is default for buttons, omit hx-trigger"),
            (r"<form[^>]*hx-post", "Use hx-post on button, not form element"),
        ]

        for pattern, message in anti_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                matches = compiled.findall(code)
                if matches:
                    violations.append(
                        {
                            "rule": "htmx_anti_pattern",
                            "message": message,
                            "severity": "warning",
                            "matches": matches[:3],
                        }
                    )
            except re.error:
                continue

        return {
            "valid": len(violations) == 0,
            "violations": violations,
        }

    def validate_file(self, file_path: str, session_id: Optional[str] = None) -> Dict:
        """Validate a single file against all applicable rules.

        Args:
            file_path: Path to file to validate
            session_id: Optional validation session ID

        Returns:
            Dict with violations found
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}

        violations = []

        try:
            content = path.read_text(encoding="utf-8")

            # Determine file type and apply appropriate validations
            if path.suffix == ".py":
                # Python file - check naming and separation
                if "views.py" in str(path):
                    result = self.validate_code(content, "views")
                    violations.extend(result.get("violations", []))
                elif "services.py" in str(path):
                    result = self.validate_code(content, "services")
                    violations.extend(result.get("violations", []))

            elif path.suffix == ".html":
                # HTML template - check HTMX
                result = self.validate_htmx(content)
                violations.extend(result.get("violations", []))

            # Log violations to database if session provided
            if session_id and violations:
                for violation in violations:
                    RuleViolation.objects.create(
                        rule_id=1,  # Default rule, should lookup actual rule
                        file_path=str(path),
                        code_snippet=content[:500],
                        message=violation.get("message", ""),
                        severity=violation.get("severity", "warning"),
                    )

        except Exception as e:
            return {"error": str(e)}

        return {
            "file": str(path),
            "violations": violations,
            "count": len(violations),
        }

    def validate_directory(self, directory: str, app_name: str = "") -> Dict:
        """Validate all files in a directory.

        Args:
            directory: Path to directory
            app_name: Optional app name for scoping

        Returns:
            Dict with validation results
        """
        path = Path(directory)
        if not path.exists():
            return {"error": "Directory not found"}

        # Create validation session
        import uuid

        session_id = str(uuid.uuid4())[:8]

        session = ValidationSession.objects.create(
            session_id=session_id,
            target_path=str(path),
            app_name=app_name,
            status="running",
        )

        results = []
        total_violations = 0
        errors = 0
        warnings = 0

        # Validate Python files
        for py_file in path.rglob("*.py"):
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue

            result = self.validate_file(str(py_file), session_id)
            if "error" not in result:
                results.append(result)
                total_violations += result.get("count", 0)

                for v in result.get("violations", []):
                    if v.get("severity") == "error":
                        errors += 1
                    elif v.get("severity") == "warning":
                        warnings += 1

        # Validate HTML files
        for html_file in path.rglob("*.html"):
            result = self.validate_file(str(html_file), session_id)
            if "error" not in result:
                results.append(result)
                total_violations += result.get("count", 0)

                for v in result.get("violations", []):
                    if v.get("severity") == "error":
                        errors += 1
                    elif v.get("severity") == "warning":
                        warnings += 1

        # Update session
        session.total_files = len(results)
        session.violations_found = total_violations
        session.errors_count = errors
        session.warnings_count = warnings
        session.status = "completed"
        session.summary = {
            "results": results[:10],  # First 10 results
            "total_files": len(results),
            "total_violations": total_violations,
        }
        session.save()

        return {
            "session_id": session_id,
            "total_files": len(results),
            "total_violations": total_violations,
            "errors": errors,
            "warnings": warnings,
            "results": results,
        }
