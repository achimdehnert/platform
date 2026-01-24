"""
Code Validator
==============

Validiert Python Code gegen BF Agent Standards.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from . import STANDARDS, Standard, get_all_standards


@dataclass
class ValidationIssue:
    """Ein gefundenes Problem"""
    standard_id: str
    standard_name: str
    severity: str
    message: str
    line_number: Optional[int] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """Gesamtergebnis der Validierung"""
    valid: bool
    score: float
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        if not self.errors and not self.warnings:
            return "✅ Alle Standards erfüllt!"
        parts = []
        if self.errors:
            parts.append(f"❌ {len(self.errors)} Fehler")
        if self.warnings:
            parts.append(f"⚠️ {len(self.warnings)} Warnungen")
        return " | ".join(parts)


class CodeValidator:
    """Validiert Code gegen alle BF Agent Standards"""
    
    def validate(self, code: str, strict: bool = False) -> ValidationResult:
        """
        Validiert Code gegen alle Standards.
        
        Args:
            code: Python Code
            strict: Warnings als Errors behandeln
        """
        issues = []
        
        for standard in get_all_standards():
            issue = self._check_standard(code, standard)
            if issue:
                issues.append(issue)
        
        # Gruppieren
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        
        if strict:
            errors.extend(warnings)
            warnings = []
        
        # Score
        total = len(get_all_standards())
        failed = len(errors) + len(warnings) * 0.5
        score = max(0, 100 - (failed / total * 100))
        
        return ValidationResult(
            valid=len(errors) == 0,
            score=round(score, 1),
            errors=errors,
            warnings=warnings,
        )
    
    def _check_standard(self, code: str, std: Standard) -> Optional[ValidationIssue]:
        """Prüft einen Standard"""
        
        if std.check_pattern:
            if not re.search(std.check_pattern, code, re.MULTILINE):
                return ValidationIssue(
                    standard_id=std.id,
                    standard_name=std.name,
                    severity=std.severity,
                    message=std.description,
                    auto_fixable=std.auto_fixable,
                )
        
        if std.anti_pattern:
            match = re.search(std.anti_pattern, code, re.MULTILINE)
            if match:
                return ValidationIssue(
                    standard_id=std.id,
                    standard_name=std.name,
                    severity=std.severity,
                    message=f"Anti-pattern: {std.description}",
                    line_number=code[:match.start()].count('\n') + 1,
                )
        
        return None
    
    def format_report(self, result: ValidationResult) -> str:
        """Formatiert Validation Report"""
        
        lines = [
            "# 📋 Validation Report",
            "",
            f"**Status:** {'✅ PASSED' if result.valid else '❌ FAILED'}",
            f"**Score:** {result.score}/100",
            f"**Summary:** {result.summary}",
            "",
        ]
        
        if result.errors:
            lines.append("## ❌ Errors")
            for e in result.errors:
                lines.append(f"- **[{e.standard_id}]** {e.message}")
        
        if result.warnings:
            lines.append("")
            lines.append("## ⚠️ Warnings")
            for w in result.warnings:
                lines.append(f"- **[{w.standard_id}]** {w.message}")
        
        return "\n".join(lines)
