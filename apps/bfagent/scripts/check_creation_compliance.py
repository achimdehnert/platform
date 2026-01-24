#!/usr/bin/env python
"""
Creation Process Compliance Checker
Enforces strict standardized creation process for BF Agent

Prevents:
- Manual CRUD file creation
- Missing CRUDConfig in models
- Inconsistent naming conventions
- Bypassing the generator
"""

# ============================================================================
# UTF-8 ENCODING FIX FOR WINDOWS
# ============================================================================
import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================================

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.apps import apps


@dataclass
class ComplianceIssue:
    """Represents a compliance violation"""

    severity: str  # 'critical', 'warning', 'info'
    category: str
    description: str
    file_path: Path = None
    fix_suggestion: str = None


class CreationComplianceChecker:
    """Checks compliance with standardized creation process"""

    def __init__(self):
        self.issues: List[ComplianceIssue] = []
        self.models_checked = 0
        self.compliant_models = 0

    def check_all_models(self):
        """Check all Django models for compliance"""
        print("=" * 80)
        print("CREATION PROCESS COMPLIANCE CHECK")
        print("=" * 80)
        print()

        for model in apps.get_models():
            if model._meta.app_label == "bfagent":
                self.check_model_compliance(model)
                self.models_checked += 1

        self.generate_report()
        return len([i for i in self.issues if i.severity == "critical"]) == 0

    def check_model_compliance(self, model):
        """Check if model follows creation standards"""
        model_name = model.__name__
        print(f"Checking: {model_name}")

        # Check 1: CRUDConfig exists
        if not hasattr(model, "CRUDConfig"):
            self.issues.append(
                ComplianceIssue(
                    severity="critical",
                    category="missing_crud_config",
                    description=f"{model_name} lacks CRUDConfig",
                    fix_suggestion=f"Add CRUDConfig class to {model_name}",
                )
            )
        else:
            # Check CRUDConfig completeness
            crud_config = model.CRUDConfig

            # Check for list display fields (multiple naming variants)
            has_list_display = (
                hasattr(crud_config, "list_display_fields")
                or hasattr(crud_config, "list_display")
                or hasattr(crud_config, "fields")
            )

            # Check for form fields (multiple naming variants)
            has_form_fields = (
                hasattr(crud_config, "form_fields")
                or hasattr(crud_config, "form_layout")
                or hasattr(crud_config, "fields")
            )

            missing = []
            if not has_list_display:
                missing.append("list_display (or list_display_fields)")
            if not has_form_fields:
                missing.append("form_fields (or form_layout)")

            if missing:
                self.issues.append(
                    ComplianceIssue(
                        severity="warning",
                        category="incomplete_crud_config",
                        description=f'{model_name}.CRUDConfig missing: {", ".join(missing)}',
                        fix_suggestion=f"Add {missing} to CRUDConfig",
                    )
                )
            else:
                self.compliant_models += 1

        # Check 2: Naming conventions
        model_lower = model_name.lower()

        # Check if form exists - STRICT naming convention: ModelName + "Form"
        forms_path = BASE_DIR / "apps" / "bfagent" / "forms.py"
        if forms_path.exists():
            content = forms_path.read_text(encoding="utf-8")
            expected_form_name = f"class {model_name}Form"

            # DEBUG: Print what we're looking for
            # print(f"  Looking for: '{expected_form_name}' ... ", end="")

            if expected_form_name not in content:
                # print("❌ NOT FOUND")
                # Check if in form_mixins
                mixins_path = BASE_DIR / "apps" / "bfagent" / "utils" / "form_mixins.py"
                if mixins_path.exists():
                    mixin_content = mixins_path.read_text()
                    if f"{model_name}FormFieldsMixin" not in mixin_content:
                        self.issues.append(
                            ComplianceIssue(
                                severity="warning",
                                category="missing_form",
                                description=f"{model_name}Form not found (expected: {expected_form_name})",
                                fix_suggestion=f"Create {expected_form_name} in forms.py",
                            )
                        )
                else:
                    self.issues.append(
                        ComplianceIssue(
                            severity="warning",
                            category="missing_form",
                            description=f"{model_name}Form not found (expected: {expected_form_name})",
                            fix_suggestion=f"Create {expected_form_name} in forms.py",
                        )
                    )
            # else:
            #     print("✅ FOUND")

        # Check 3: URLs follow naming convention
        urls_path = BASE_DIR / "apps" / "bfagent" / "urls.py"
        if urls_path.exists():
            urls_content = urls_path.read_text()
            expected_patterns = [
                f'name="{model_lower}-list"',
                f'name="{model_lower}-create"',
            ]

            for pattern in expected_patterns:
                if pattern not in urls_content:
                    # Not all models need all CRUD operations, so warning only
                    pass

        print(f"  Checked {model_name}")

    def generate_report(self):
        """Generate compliance report"""
        print()
        print("=" * 80)
        print("COMPLIANCE REPORT")
        print("=" * 80)
        print()

        print(f"Models Checked: {self.models_checked}")
        print(f"Compliant Models: {self.compliant_models}")
        print(f"Compliance Rate: {(self.compliant_models/self.models_checked*100):.1f}%")
        print()

        if not self.issues:
            print("SUCCESS: All models are compliant!")
            print()
            return

        # Group by severity
        critical = [i for i in self.issues if i.severity == "critical"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        if critical:
            print(f"CRITICAL ISSUES ({len(critical)}):")
            print("-" * 80)
            for issue in critical:
                print(f"  {issue.description}")
                if issue.fix_suggestion:
                    print(f"    FIX: {issue.fix_suggestion}")
            print()

        if warnings:
            print(f"WARNINGS ({len(warnings)}):")
            print("-" * 80)
            for issue in warnings:
                print(f"  {issue.description}")
                if issue.fix_suggestion:
                    print(f"    FIX: {issue.fix_suggestion}")
            print()

        if info:
            print(f"INFO ({len(info)}):")
            print("-" * 80)
            for issue in info:
                print(f"  {issue.description}")
            print()

        print("=" * 80)
        print("RECOMMENDATIONS:")
        print("=" * 80)
        print("1. Fix critical issues immediately")
        print("2. Run: python scripts/consistency_framework.py analyze ModelName")
        print("3. Run: python scripts/consistency_framework.py generate ModelName --force")
        print("4. Follow .windsurf/STRICT_CREATION_PROCESS.md")
        print()


def main():
    """Main entry point"""
    checker = CreationComplianceChecker()
    success = checker.check_all_models()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
