"""
Autonomous Error Analyzer & Fix Suggester
Analyzes Django errors and provides automatic fix suggestions
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ErrorAnalysis:
    """Results of error analysis"""

    error_type: str
    error_message: str
    root_cause: str
    fix_suggestions: List[str]
    confidence: float  # 0.0 to 1.0
    auto_fixable: bool
    command_to_run: Optional[str] = None


class AutonomousErrorFixer:
    """
    Analyzes Django errors from logs and suggests fixes
    """

    def analyze_error(self, error_text: str) -> ErrorAnalysis:
        """
        Analyze error and provide fix suggestions
        """
        # Detect error type
        if "no such table:" in error_text:
            return self._analyze_missing_table(error_text)

        elif "NoReverseMatch" in error_text:
            return self._analyze_no_reverse_match(error_text)

        elif "KeyError:" in error_text:
            return self._analyze_key_error(error_text)

        elif "ModuleNotFoundError:" in error_text:
            return self._analyze_module_not_found(error_text)

        elif "TemplateDoesNotExist" in error_text:
            return self._analyze_template_not_found(error_text)

        else:
            return ErrorAnalysis(
                error_type="Unknown",
                error_message=error_text[:200],
                root_cause="Unable to determine root cause automatically",
                fix_suggestions=["Manual investigation required"],
                confidence=0.0,
                auto_fixable=False,
            )

    def _analyze_missing_table(self, error_text: str) -> ErrorAnalysis:
        """Analyze 'no such table' errors"""

        # Extract table name
        match = re.search(r"no such table: (\w+)", error_text)
        table_name = match.group(1) if match else "unknown"

        # Check if it's a migration issue
        suggestions = [
            f"✅ **RUN MIGRATIONS**: `python manage.py migrate`",
            f"📋 Check if migrations exist: `python manage.py showmigrations`",
            f"🔍 Search for migration files containing '{table_name}'",
            f"⚠️ Check if migration was backed up (.backup file)",
            f"🔧 Create migration if missing: `python manage.py makemigrations`",
        ]

        return ErrorAnalysis(
            error_type="OperationalError",
            error_message=f"Table '{table_name}' does not exist in database",
            root_cause=f"Migration for '{table_name}' table not applied or missing",
            fix_suggestions=suggestions,
            confidence=0.95,
            auto_fixable=True,
            command_to_run="python manage.py migrate",
        )

    def _analyze_no_reverse_match(self, error_text: str) -> ErrorAnalysis:
        """Analyze NoReverseMatch errors"""

        # Extract URL name
        match = re.search(r"Reverse for '([^']+)'", error_text)
        url_name = match.group(1) if match else "unknown"

        # Check if namespace issue
        namespace_issue = "is not a registered namespace" in error_text

        if namespace_issue:
            suggestions = [
                f"✅ **ADD NAMESPACE**: Include app URLs with namespace in `urls.py`",
                f"📝 Example: `path('app/', include(('apps.myapp.urls', 'myapp')))`",
                f"🔍 Check if app is in INSTALLED_APPS",
                f"📋 Verify `app_name = 'namespace'` in app's urls.py",
            ]
            root_cause = f"Namespace for '{url_name}' not registered"
        else:
            suggestions = [
                f"✅ **CREATE URL PATTERN**: Add pattern for '{url_name}' in urls.py",
                f"📝 Example: `path('.../', view, name='{url_name}')`",
                f"🔍 Check if URL name is correct in navigation/template",
                f"📋 Update navigation items to use correct URL name",
                f"❌ Deactivate navigation item if URL not needed",
            ]
            root_cause = f"URL pattern '{url_name}' not defined"

        return ErrorAnalysis(
            error_type="NoReverseMatch",
            error_message=f"Cannot reverse URL for '{url_name}'",
            root_cause=root_cause,
            fix_suggestions=suggestions,
            confidence=0.90,
            auto_fixable=False,
        )

    def _analyze_key_error(self, error_text: str) -> ErrorAnalysis:
        """Analyze KeyError exceptions"""

        match = re.search(r"KeyError: '([^']+)'", error_text)
        key = match.group(1) if match else "unknown"

        suggestions = [
            f"✅ **CHECK CONFIGURATION**: Verify '{key}' is defined",
            f"🔍 Search codebase for '{key}' references",
            f"📋 Add '{key}' to settings/configuration",
            f"⚠️ Use .get('{key}') instead of ['{key}'] for optional keys",
        ]

        return ErrorAnalysis(
            error_type="KeyError",
            error_message=f"Key '{key}' not found",
            root_cause=f"Configuration or dictionary key '{key}' missing",
            fix_suggestions=suggestions,
            confidence=0.80,
            auto_fixable=False,
        )

    def _analyze_module_not_found(self, error_text: str) -> ErrorAnalysis:
        """Analyze ModuleNotFoundError"""

        match = re.search(r"No module named '([^']+)'", error_text)
        module = match.group(1) if match else "unknown"

        suggestions = [
            f"✅ **INSTALL PACKAGE**: `pip install {module}`",
            f"📋 Check requirements.txt for '{module}'",
            f"🔍 Verify package name is correct",
            f"⚠️ Activate virtual environment if not active",
        ]

        return ErrorAnalysis(
            error_type="ModuleNotFoundError",
            error_message=f"Module '{module}' not found",
            root_cause=f"Package '{module}' not installed or import path wrong",
            fix_suggestions=suggestions,
            confidence=0.95,
            auto_fixable=True,
            command_to_run=f"pip install {module}",
        )

    def _analyze_template_not_found(self, error_text: str) -> ErrorAnalysis:
        """Analyze TemplateDoesNotExist errors"""

        match = re.search(r"TemplateDoesNotExist at [^\n]+\n([^\n]+)", error_text)
        template = match.group(1).strip() if match else "unknown"

        suggestions = [
            f"✅ **CREATE TEMPLATE**: Create file at `templates/{template}`",
            f"📋 Check TEMPLATES setting in settings.py",
            f"🔍 Verify template path is correct",
            f"📁 Check if app is in INSTALLED_APPS",
        ]

        return ErrorAnalysis(
            error_type="TemplateDoesNotExist",
            error_message=f"Template '{template}' not found",
            root_cause=f"Template file '{template}' missing or path incorrect",
            fix_suggestions=suggestions,
            confidence=0.85,
            auto_fixable=False,
        )

    def format_analysis(self, analysis: ErrorAnalysis) -> str:
        """Format analysis for display"""

        output = []
        output.append("\n" + "=" * 70)
        output.append("  🤖 AUTONOMOUS ERROR ANALYSIS")
        output.append("=" * 70 + "\n")

        output.append(f"🔴 **ERROR TYPE:** {analysis.error_type}")
        output.append(f"📝 **MESSAGE:** {analysis.error_message}")
        output.append(f"🔍 **ROOT CAUSE:** {analysis.root_cause}")
        output.append(f"📊 **CONFIDENCE:** {analysis.confidence*100:.0f}%")
        output.append(f"🔧 **AUTO-FIXABLE:** {'YES ✅' if analysis.auto_fixable else 'NO ❌'}\n")

        output.append("=" * 70)
        output.append("  💡 FIX SUGGESTIONS")
        output.append("=" * 70 + "\n")

        for i, suggestion in enumerate(analysis.fix_suggestions, 1):
            output.append(f"{i}. {suggestion}")

        if analysis.command_to_run:
            output.append("\n" + "=" * 70)
            output.append("  ⚡ AUTO-FIX COMMAND")
            output.append("=" * 70 + "\n")
            output.append(f"```bash")
            output.append(f"{analysis.command_to_run}")
            output.append(f"```\n")

        return "\n".join(output)


def analyze_from_file(error_file_path: str) -> Optional[ErrorAnalysis]:
    """
    Analyze error from error_alerts.txt file
    """
    try:
        with open(error_file_path, "r", encoding="utf-8") as f:
            error_text = f.read()

        fixer = AutonomousErrorFixer()
        analysis = fixer.analyze_error(error_text)

        print(fixer.format_analysis(analysis))
        return analysis

    except FileNotFoundError:
        print(f"❌ Error file not found: {error_file_path}")
        return None
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")
        return None


if __name__ == "__main__":
    # Test with current error
    error_file = r"C:\Users\achim\github\bfagent\error_alerts.txt"
    analyze_from_file(error_file)
