# -*- coding: utf-8 -*-
"""
DjangoAgent - Guardrail Agent für Django Code-Qualität.

Validiert Code VOR dem Speichern auf:
- WSL/Umgebungs-Kompatibilität
- UTF-8 Korrektheit
- Naming Chain Konsistenz (DB → Model → Template → View → URL)
- URL-Namen Existenz

Nutzt LLMAgent für komplexe Validierungen.
"""
import re
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def _log_validation_async(
    agent: str,
    action: str,
    passed: bool,
    errors_count: int,
    warnings_count: int,
    errors_prevented: list,
    file_path: str = None,
):
    """Loggt Validierung asynchron in die DB."""
    def _save():
        try:
            from apps.bfagent.models_controlling import AgentValidationLog
            AgentValidationLog.objects.create(
                agent=agent,
                action=action,
                passed=passed,
                errors_count=errors_count,
                warnings_count=warnings_count,
                errors_prevented=errors_prevented,
                file_path=file_path,
            )
        except Exception as e:
            logger.warning(f"Failed to log validation: {e}")
    
    thread = threading.Thread(target=_save, daemon=True)
    thread.start()


# =============================================================================
# RULES DEFINITION
# =============================================================================

ENVIRONMENT_RULES = {
    "execution": {
        "rule": "IMMER WSL für Python/Django Commands",
        "pattern": r'wsl bash -c "cd ~/github/bfagent && .*"',
        "forbidden_patterns": [
            r"python manage\.py",  # Ohne WSL-Wrapper
            r"python -c ",  # Ohne WSL-Wrapper
        ],
    },
    "paths": {
        "windows_patterns": [
            r"[A-Z]:\\",  # C:\, U:\, etc.
            r"[A-Z]:/",   # C:/, U:/, etc.
        ],
        "rule": "Windows-Pfade NIE in Python-Code",
    },
}

UTF8_RULES = {
    "file_open": {
        "safe_pattern": r'open\([^)]+encoding=["\']utf-8["\']',
        "unsafe_pattern": r'open\([^)]+\)(?!.*encoding)',
        "rule": "Immer encoding='utf-8' bei open()",
    },
    "json_dumps": {
        "safe_pattern": r'json\.dumps\([^)]+ensure_ascii\s*=\s*False',
        "unsafe_pattern": r'json\.dumps\([^)]+\)(?!.*ensure_ascii)',
        "rule": "Immer ensure_ascii=False bei json.dumps()",
    },
}

NAMING_RULES = {
    "model": {
        "pattern": r"^[A-Z][a-zA-Z0-9]+$",
        "description": "PascalCase ohne Unterstriche",
        "examples": ["TestRequirement", "BookProject", "Chapter"],
    },
    "view_class": {
        "pattern": r"^[A-Z][a-zA-Z0-9]+View$",
        "description": "PascalCase endend mit 'View'",
        "examples": ["RequirementDetailView", "ProjectListView"],
    },
    "view_function": {
        "pattern": r"^[a-z][a-z0-9_]*$",
        "description": "snake_case",
        "examples": ["requirement_detail", "project_list"],
    },
    "url_name": {
        "pattern": r"^[a-z][a-z0-9\-]*$",
        "description": "kebab-case",
        "examples": ["requirement-detail", "project-list"],
    },
    "template": {
        "pattern": r"^[a-z][a-z0-9_]*\.html$",
        "description": "snake_case.html",
        "examples": ["requirement_detail.html", "project_list.html"],
    },
    "context_variable": {
        "pattern": r"^[a-z][a-z0-9_]*$",
        "description": "snake_case, Singular für Einzelobjekt",
        "examples": ["requirement", "project", "chapter"],
    },
}

URL_NAMESPACE_RULE = {
    "rule": "URL-Referenzen IMMER mit Namespace",
    "pattern": r"['\"][\w_]+:[\w\-]+['\"]",
    "forbidden": r"reverse\(['\"][a-z\-]+['\"]\)",  # Ohne Namespace
    "examples": {
        "correct": "{% url 'control_center:requirement-detail' pk=obj.id %}",
        "wrong": "{% url 'requirement-detail' pk=obj.id %}",
    },
}

# =============================================================================
# SECURITY RULES
# =============================================================================

SECURITY_RULES = {
    "sql_injection": {
        "patterns": [
            r"\.raw\s*\(",                    # Model.objects.raw()
            r"\.extra\s*\(",                  # QuerySet.extra() - deprecated
            r"cursor\.execute\s*\([^%]*%",    # cursor.execute mit % formatting
            r"f['\"].*SELECT.*FROM",          # f-strings mit SQL
            r"['\"].*SELECT.*FROM.*\+",       # String concat mit SQL
        ],
        "severity": "error",
        "message": "Potenzielle SQL Injection - verwende ORM oder parametrisierte Queries",
    },
    "xss": {
        "patterns": [
            r"mark_safe\s*\([^)]*\+",         # mark_safe mit String concat
            r"mark_safe\s*\(f['\"]",          # mark_safe mit f-string
            r"\|safe\s*}}.*\{\{",             # |safe gefolgt von Variable
        ],
        "severity": "warning",
        "message": "Potenzielle XSS - prüfe ob User-Input escaped wird",
    },
    "hardcoded_secrets": {
        "patterns": [
            r"['\"]sk-[a-zA-Z0-9]{20,}['\"]",      # OpenAI API Key
            r"['\"]ghp_[a-zA-Z0-9]{36}['\"]",      # GitHub Token
            r"password\s*=\s*['\"][^'\"]{8,}['\"]", # Hardcoded Password
            r"secret\s*=\s*['\"][^'\"]{8,}['\"]",   # Hardcoded Secret
            r"api_key\s*=\s*['\"][^'\"]{8,}['\"]",  # Hardcoded API Key
        ],
        "severity": "error",
        "message": "Hardcoded Secret gefunden - verwende Umgebungsvariablen",
    },
    "debug_code": {
        "patterns": [
            r"print\s*\(",                    # print() in Production Code
            r"import\s+pdb",                  # pdb import
            r"pdb\.set_trace\(",              # pdb breakpoint
            r"breakpoint\s*\(",               # Python breakpoint()
            r"DEBUG\s*=\s*True",              # DEBUG hardcoded
        ],
        "severity": "warning",
        "message": "Debug-Code gefunden - entfernen vor Production",
    },
    "insecure_deserialize": {
        "patterns": [
            r"pickle\.loads?\s*\(",           # pickle.load/loads
            r"yaml\.load\s*\([^)]*\)",        # yaml.load ohne Loader
            r"eval\s*\(",                     # eval()
            r"exec\s*\(",                     # exec()
        ],
        "severity": "error",
        "message": "Unsichere Deserialisierung - verwende sichere Alternative",
    },
    "csrf_exempt": {
        "patterns": [
            r"@csrf_exempt",                  # CSRF disabled
            r"csrf_exempt\s*\(",              # csrf_exempt decorator
        ],
        "severity": "warning",
        "message": "CSRF-Schutz deaktiviert - nur für APIs mit eigenem Auth verwenden",
    },
    "mass_assignment": {
        "patterns": [
            r"\.objects\.create\s*\(\*\*request\.(POST|GET)",  # Direct request data
            r"Model\s*\(\*\*request\.(POST|GET)",              # Model init with request
            r"form\.save\s*\(commit=False\).*\n.*\.save\(",    # Unsafe form save
        ],
        "severity": "warning",
        "message": "Potenzielle Mass Assignment - validiere Eingabedaten",
    },
    "path_traversal": {
        "patterns": [
            r"open\s*\([^)]*request\.",       # open() mit request data
            r"os\.path\.join\s*\([^)]*request\.",  # path.join mit request
            r"Path\s*\([^)]*request\.",       # Path() mit request
        ],
        "severity": "error",
        "message": "Potenzielle Path Traversal - validiere Dateipfade",
    },
    "insecure_redirect": {
        "patterns": [
            r"redirect\s*\(request\.(GET|POST)",  # Redirect mit request data
            r"HttpResponseRedirect\s*\(request\.", # Redirect mit request
        ],
        "severity": "warning",
        "message": "Potenzielle Open Redirect - validiere Redirect-URLs",
    },
    "shell_injection": {
        "patterns": [
            r"subprocess\.\w+\s*\([^)]*shell\s*=\s*True",  # shell=True
            r"os\.system\s*\(",               # os.system()
            r"os\.popen\s*\(",                # os.popen()
        ],
        "severity": "error",
        "message": "Potenzielle Shell Injection - verwende subprocess mit shell=False",
    },
}

IMPORT_RULES = {
    "circular_patterns": [
        r"from\s+apps\.\w+\.models\s+import.*(?:views|forms|serializers)",
        r"from\s+apps\.\w+\.views\s+import.*models",
    ],
    "forbidden_imports": [
        (r"from\s+django\.conf\s+import\s+settings", "warning", 
         "Verwende besser django.conf.settings direkt"),
    ],
}

PERFORMANCE_RULES = {
    "n_plus_one": {
        "patterns": [
            r"for\s+\w+\s+in\s+\w+\.objects\.all\(\):",  # Loop über alle Objekte
            r"\.filter\(.*__in=\[.*for\s+",              # Filter mit List Comprehension
        ],
        "severity": "warning", 
        "message": "Potenzielle N+1 Query - verwende select_related/prefetch_related",
    },
    "missing_index_hint": {
        "patterns": [
            r"\.filter\(\w+__contains=",      # contains ohne Index
            r"\.filter\(\w+__icontains=",     # icontains ohne Index
            r"\.filter\(\w+__startswith=",    # startswith
        ],
        "severity": "info",
        "message": "Text-Suche kann langsam sein - prüfe ob Index existiert",
    },
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ValidationError:
    """Ein einzelner Validierungsfehler."""
    rule: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # error, warning, info
    fixable: bool = False
    fix_suggestion: Optional[str] = None


@dataclass
class FixResult:
    """Ergebnis eines Auto-Fix."""
    success: bool
    original_code: str
    fixed_code: str
    fixes_applied: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def changed(self) -> bool:
        return self.original_code != self.fixed_code


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    @property
    def fixable_count(self) -> int:
        return sum(1 for e in self.errors + self.warnings if e.fixable)
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [
                {
                    "rule": e.rule,
                    "message": e.message,
                    "line": e.line,
                    "severity": e.severity,
                    "fixable": e.fixable,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "rule": w.rule,
                    "message": w.message,
                    "line": w.line,
                }
                for w in self.warnings
            ],
        }


# =============================================================================
# DJANGO AGENT
# =============================================================================

class DjangoAgent:
    """
    Guardrail Agent für Django Code-Qualität.
    
    Validiert Code VOR dem Speichern auf:
    - WSL/Umgebungs-Kompatibilität  
    - UTF-8 Korrektheit
    - Naming Chain Konsistenz
    - URL-Namen Existenz
    
    Usage:
        agent = DjangoAgent()
        result = agent.validate_python_file(code, "apps/bfagent/views.py")
        
        if not result.valid:
            for error in result.errors:
                print(f"❌ {error.rule}: {error.message}")
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialisiert den DjangoAgent.
        
        Args:
            project_root: Pfad zum Django-Projekt (für URL-Validierung)
        """
        self.project_root = project_root or "/home/dehnert/github/bfagent"
        self._url_cache: Optional[Dict[str, List[str]]] = None
        self._model_cache: Optional[Dict[str, List[str]]] = None
    
    # =========================================================================
    # MAIN VALIDATION METHODS
    # =========================================================================
    
    def validate_python_file(self, code: str, file_path: str) -> ValidationResult:
        """
        Validiert eine Python-Datei.
        
        Args:
            code: Der Python-Code
            file_path: Pfad zur Datei (für Kontext)
            
        Returns:
            ValidationResult mit Fehlern und Warnungen
        """
        errors = []
        warnings = []
        
        # 1. UTF-8 Checks
        utf8_errors = self._check_utf8_compliance(code)
        errors.extend(utf8_errors)
        
        # 2. Windows Path Checks
        path_errors = self._check_no_windows_paths(code)
        errors.extend(path_errors)
        
        # 3. URL Name Checks (nur für Views/Templates)
        if self._is_view_file(file_path) or "reverse(" in code:
            url_errors = self._check_url_names(code)
            errors.extend(url_errors)
        
        # 4. Naming Convention Checks
        if self._is_model_file(file_path):
            naming_errors = self._check_model_naming(code)
            errors.extend(naming_errors)
        elif self._is_view_file(file_path):
            naming_errors = self._check_view_naming(code)
            errors.extend(naming_errors)
        
        # 5. Security Checks
        security_errors = self._check_security(code)
        for err in security_errors:
            if err.severity == "error":
                errors.append(err)
            else:
                warnings.append(err)
        
        # 6. Import Checks
        import_errors = self._check_imports(code)
        warnings.extend(import_errors)
        
        # 7. Performance Checks (nur Warnings/Info)
        perf_errors = self._check_performance(code)
        warnings.extend(perf_errors)
        
        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
        
        # Log to Controlling DB
        _log_validation_async(
            agent="DjangoAgent",
            action="validate_python_file",
            passed=result.valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            errors_prevented=[{"rule": e.rule, "message": e.message} for e in errors],
            file_path=file_path,
        )
        
        return result
    
    def validate_template(self, html: str, file_path: str) -> ValidationResult:
        """
        Validiert eine Django Template-Datei.
        
        Args:
            html: Der Template-Code
            file_path: Pfad zur Datei
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # 1. {% static %} ohne {% load static %}
        static_errors = self._check_static_tag(html)
        errors.extend(static_errors)
        
        # 2. URL ohne Namespace
        url_errors = self._check_template_urls(html)
        errors.extend(url_errors)
        
        # 3. Template Naming
        template_name = Path(file_path).name
        if not re.match(NAMING_RULES["template"]["pattern"], template_name):
            errors.append(ValidationError(
                rule="template_naming",
                message=f"Template-Name '{template_name}' folgt nicht snake_case.html",
                severity="warning",
            ))
        
        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
        
        # Log to Controlling DB
        _log_validation_async(
            agent="DjangoAgent",
            action="validate_template",
            passed=result.valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            errors_prevented=[{"rule": e.rule, "message": e.message} for e in errors],
            file_path=file_path,
        )
        
        return result
    
    def validate_url_path(self, url_path: str, app_name: str = None) -> ValidationResult:
        """
        Validiert einen URL-Pfad gegen die Routing-Regeln.
        
        Args:
            url_path: Der zu prüfende URL-Pfad (z.B. '/bfagent/controlling/')
            app_name: Optional App-Name für Namespace-Prüfung
            
        Returns:
            ValidationResult mit Hinweisen zur korrekten URL
        """
        from .routing_rules import APP_URL_PREFIXES, validate_url_path as validate_path
        
        errors = []
        warnings = []
        
        # 1. Allgemeine URL-Validierung (kebab-case, forbidden patterns)
        valid, path_errors = validate_path(url_path)
        for err in path_errors:
            errors.append(ValidationError(
                rule="url_pattern_violation",
                message=err,
                severity="error",
            ))
        
        # 2. App-Prefix Prüfung
        parts = url_path.strip("/").split("/")
        if parts:
            first_part = parts[0]
            for app_name, correct_prefix in APP_URL_PREFIXES.items():
                # Wenn App-Name als Prefix verwendet wird (z.B. /bfagent/ statt /bookwriting/)
                if first_part == app_name and first_part != correct_prefix:
                    correct_path = "/" + correct_prefix + "/" + "/".join(parts[1:])
                    if not correct_path.endswith("/"):
                        correct_path += "/"
                    errors.append(ValidationError(
                        rule="url_prefix_mismatch",
                        message=f"URL '/{first_part}/' verwendet App-Name als Prefix",
                        severity="error",
                        fixable=True,
                        fix_suggestion=f"Korrekte URL: {correct_path}",
                    ))
                    break
                # Wenn Unterstrich-Version verwendet wird (z.B. /control_center/ statt /control-center/)
                elif first_part == app_name.replace("_", "-") != correct_prefix:
                    pass  # Schon korrekt
        
        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
        
        # Log to Controlling DB
        _log_validation_async(
            agent="DjangoAgent",
            action="validate_url_path",
            passed=result.valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            errors_prevented=[{"rule": e.rule, "message": e.message} for e in errors],
        )
        
        return result

    def validate_command(self, command: str) -> ValidationResult:
        """
        Validiert einen Terminal-Command.
        
        Args:
            command: Der auszuführende Command
            
        Returns:
            ValidationResult
        """
        errors = []
        
        # 1. Python/Django Commands ohne WSL?
        if self._is_python_command(command) and "wsl" not in command.lower():
            errors.append(ValidationError(
                rule="wsl_required",
                message="Python/Django Commands müssen in WSL ausgeführt werden",
                severity="error",
                fixable=True,
                fix_suggestion=f'wsl bash -c "cd ~/github/bfagent && {command}"',
            ))
        
        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )
        
        # Log to Controlling DB
        _log_validation_async(
            agent="DjangoAgent",
            action="validate_command",
            passed=result.valid,
            errors_count=len(errors),
            warnings_count=0,
            errors_prevented=[{"rule": e.rule, "message": e.message} for e in errors],
        )
        
        return result
    
    # =========================================================================
    # UTF-8 CHECKS
    # =========================================================================
    
    def _check_utf8_compliance(self, code: str) -> List[ValidationError]:
        """Prüft UTF-8 Compliance."""
        errors = []
        lines = code.split("\n")
        
        for i, line in enumerate(lines, 1):
            # open() ohne encoding
            if re.search(r'open\s*\([^)]+\)', line):
                if "encoding" not in line and "b'" not in line and 'b"' not in line:
                    errors.append(ValidationError(
                        rule="utf8_file_open",
                        message="open() ohne encoding='utf-8'",
                        line=i,
                        severity="warning",
                        fixable=True,
                        fix_suggestion="Füge encoding='utf-8' hinzu",
                    ))
            
            # json.dumps ohne ensure_ascii=False (bei deutschen Texten)
            if "json.dumps" in line and "ensure_ascii" not in line:
                errors.append(ValidationError(
                    rule="utf8_json_dumps",
                    message="json.dumps() ohne ensure_ascii=False",
                    line=i,
                    severity="warning",
                    fixable=True,
                    fix_suggestion="Füge ensure_ascii=False hinzu",
                ))
        
        return errors
    
    # =========================================================================
    # PATH CHECKS
    # =========================================================================
    
    def _check_no_windows_paths(self, code: str) -> List[ValidationError]:
        """Prüft auf Windows-Pfade im Code."""
        errors = []
        lines = code.split("\n")
        
        for i, line in enumerate(lines, 1):
            # Skip Kommentare
            if line.strip().startswith("#"):
                continue
            
            for pattern in ENVIRONMENT_RULES["paths"]["windows_patterns"]:
                if re.search(pattern, line):
                    errors.append(ValidationError(
                        rule="no_windows_paths",
                        message=f"Windows-Pfad gefunden in Zeile {i}",
                        line=i,
                        severity="error",
                        fixable=True,
                        fix_suggestion="Verwende Linux/WSL-Pfade (z.B. ~/github/bfagent)",
                    ))
                    break
        
        return errors
    
    # =========================================================================
    # URL CHECKS
    # =========================================================================
    
    def _check_url_names(self, code: str) -> List[ValidationError]:
        """Prüft URL-Namen auf Namespace und Existenz."""
        errors = []
        lines = code.split("\n")
        
        # Pattern für reverse() - fängt alle URL-Namen
        reverse_pattern = r"reverse\s*\(\s*['\"]([^'\"]+)['\"]"
        
        for i, line in enumerate(lines, 1):
            match = re.search(reverse_pattern, line)
            if match:
                url_name = match.group(1)
                # Prüfe ob es wirklich kein Namespace hat (kein : enthalten)
                if ":" not in url_name:
                    errors.append(ValidationError(
                        rule="url_namespace_required",
                        message=f"reverse('{url_name}') ohne Namespace",
                        line=i,
                        severity="error",
                        fixable=True,
                        fix_suggestion=f"Verwende reverse('app_name:{url_name}')",
                    ))
        
        return errors
    
    def _check_template_urls(self, html: str) -> List[ValidationError]:
        """Prüft Template URL-Tags auf Namespace."""
        errors = []
        lines = html.split("\n")
        
        # Pattern für {% url 'name' %} ohne Namespace
        url_no_ns = r"\{%\s*url\s+['\"]([a-z\-_]+)['\"]"
        
        for i, line in enumerate(lines, 1):
            match = re.search(url_no_ns, line)
            if match:
                url_name = match.group(1)
                if ":" not in url_name:
                    errors.append(ValidationError(
                        rule="template_url_namespace",
                        message=f"{{% url '{url_name}' %}} ohne Namespace",
                        line=i,
                        severity="error",
                        fixable=True,
                        fix_suggestion=f"Verwende {{% url 'app_name:{url_name}' %}}",
                    ))
        
        return errors
    
    # =========================================================================
    # STATIC TAG CHECK
    # =========================================================================
    
    def _check_static_tag(self, html: str) -> List[ValidationError]:
        """Prüft ob {% static %} ohne {% load static %} verwendet wird."""
        errors = []
        
        has_static_tag = "{% static" in html or "{%static" in html
        has_load_static = "{% load static" in html or "{%load static" in html
        
        if has_static_tag and not has_load_static:
            # Finde die Zeile mit {% static
            lines = html.split("\n")
            for i, line in enumerate(lines, 1):
                if "{% static" in line or "{%static" in line:
                    errors.append(ValidationError(
                        rule="static_load_required",
                        message="{% static %} verwendet ohne {% load static %}",
                        line=i,
                        severity="error",
                        fixable=True,
                        fix_suggestion="Füge {% load static %} am Anfang des Templates hinzu",
                    ))
                    break
        
        return errors
    
    # =========================================================================
    # NAMING CHECKS
    # =========================================================================
    
    def _check_model_naming(self, code: str) -> List[ValidationError]:
        """Prüft Model-Naming-Conventions."""
        errors = []
        
        # Finde class Definitionen
        class_pattern = r"class\s+(\w+)\s*\(.*models\.Model"
        matches = re.finditer(class_pattern, code)
        
        for match in matches:
            class_name = match.group(1)
            if not re.match(NAMING_RULES["model"]["pattern"], class_name):
                errors.append(ValidationError(
                    rule="model_naming",
                    message=f"Model '{class_name}' folgt nicht PascalCase",
                    severity="warning",
                ))
        
        return errors
    
    def _check_view_naming(self, code: str) -> List[ValidationError]:
        """Prüft View-Naming-Conventions."""
        errors = []
        
        # Class-Based Views
        cbv_pattern = r"class\s+(\w+)\s*\(.*View"
        for match in re.finditer(cbv_pattern, code):
            class_name = match.group(1)
            if not re.match(NAMING_RULES["view_class"]["pattern"], class_name):
                errors.append(ValidationError(
                    rule="view_class_naming",
                    message=f"View-Klasse '{class_name}' sollte mit 'View' enden",
                    severity="warning",
                ))
        
        # Function-Based Views (def mit request Parameter)
        fbv_pattern = r"def\s+(\w+)\s*\(\s*request"
        for match in re.finditer(fbv_pattern, code):
            func_name = match.group(1)
            if not re.match(NAMING_RULES["view_function"]["pattern"], func_name):
                errors.append(ValidationError(
                    rule="view_function_naming",
                    message=f"View-Funktion '{func_name}' folgt nicht snake_case",
                    severity="warning",
                ))
        
        return errors
    
    # =========================================================================
    # SECURITY CHECKS
    # =========================================================================
    
    def _check_security(self, code: str) -> List[ValidationError]:
        """Prüft Code auf Security-Probleme."""
        errors = []
        lines = code.split("\n")
        
        for rule_name, rule_config in SECURITY_RULES.items():
            for pattern in rule_config["patterns"]:
                for i, line in enumerate(lines, 1):
                    # Skip Kommentare
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append(ValidationError(
                            rule=f"security_{rule_name}",
                            message=rule_config["message"],
                            line=i,
                            severity=rule_config["severity"],
                        ))
                        break  # Nur einmal pro Regel pro Datei
        
        return errors
    
    def _check_imports(self, code: str) -> List[ValidationError]:
        """Prüft Import-Statements auf Probleme."""
        errors = []
        lines = code.split("\n")
        
        # Circular Import Detection
        for pattern in IMPORT_RULES["circular_patterns"]:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    errors.append(ValidationError(
                        rule="import_circular",
                        message="Potenzielle zirkuläre Abhängigkeit",
                        line=i,
                        severity="warning",
                    ))
        
        return errors
    
    def _check_performance(self, code: str) -> List[ValidationError]:
        """Prüft Code auf Performance-Probleme."""
        errors = []
        lines = code.split("\n")
        
        for rule_name, rule_config in PERFORMANCE_RULES.items():
            for pattern in rule_config["patterns"]:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        errors.append(ValidationError(
                            rule=f"perf_{rule_name}",
                            message=rule_config["message"],
                            line=i,
                            severity=rule_config["severity"],
                        ))
        
        return errors
    
    # =========================================================================
    # AUTO-FIX METHODS
    # =========================================================================
    
    def auto_fix(self, code: str, file_path: str = "unknown.py") -> FixResult:
        """
        Versucht automatisch Probleme im Code zu beheben.
        
        Args:
            code: Der zu fixende Code
            file_path: Pfad zur Datei (für Kontext)
            
        Returns:
            FixResult mit fixedCode und Liste der Fixes
            
        Usage:
            result = agent.auto_fix(code)
            if result.changed:
                print(f"Fixed: {result.fixes_applied}")
                save_file(result.fixed_code)
        """
        original = code
        fixed = code
        fixes = []
        errors = []
        
        # 1. Fix open() ohne encoding
        fixed, fix_count = self._fix_open_encoding(fixed)
        if fix_count:
            fixes.append(f"Added encoding='utf-8' to {fix_count} open() calls")
        
        # 2. Fix json.dumps ohne ensure_ascii
        fixed, fix_count = self._fix_json_dumps(fixed)
        if fix_count:
            fixes.append(f"Added ensure_ascii=False to {fix_count} json.dumps() calls")
        
        # 3. Remove print statements (optional - nur in views)
        if self._is_view_file(file_path):
            fixed, fix_count = self._fix_remove_prints(fixed)
            if fix_count:
                fixes.append(f"Commented out {fix_count} print() statements")
        
        # 4. Fix missing {% load static %}
        if file_path.endswith('.html'):
            fixed, did_fix = self._fix_load_static(fixed)
            if did_fix:
                fixes.append("Added {% load static %} to template")
        
        return FixResult(
            success=len(errors) == 0,
            original_code=original,
            fixed_code=fixed,
            fixes_applied=fixes,
            errors=errors,
        )
    
    def _fix_open_encoding(self, code: str) -> Tuple[str, int]:
        """Fügt encoding='utf-8' zu open() Aufrufen hinzu."""
        count = 0
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Suche open() ohne encoding (nicht binary mode)
            if re.search(r'open\s*\([^)]+\)', line):
                if 'encoding' not in line and "b'" not in line and 'b"' not in line:
                    # Füge encoding vor der schließenden Klammer hinzu
                    line = re.sub(
                        r'open\s*\(([^)]+)\)',
                        r"open(\1, encoding='utf-8')",
                        line
                    )
                    count += 1
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), count
    
    def _fix_json_dumps(self, code: str) -> Tuple[str, int]:
        """Fügt ensure_ascii=False zu json.dumps() hinzu."""
        count = 0
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            if 'json.dumps(' in line and 'ensure_ascii' not in line:
                # Füge ensure_ascii=False hinzu
                line = re.sub(
                    r'json\.dumps\(([^)]+)\)',
                    r'json.dumps(\1, ensure_ascii=False)',
                    line
                )
                count += 1
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), count
    
    def _fix_remove_prints(self, code: str) -> Tuple[str, int]:
        """Kommentiert print() Statements aus."""
        count = 0
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Nur standalone prints, nicht in Strings oder bereits kommentiert
            if stripped.startswith('print(') and not stripped.startswith('#'):
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + '# ' + stripped + '  # TODO: Remove debug')
                count += 1
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), count
    
    def _fix_load_static(self, html: str) -> Tuple[str, bool]:
        """Fügt {% load static %} zu Templates hinzu."""
        if '{% static' in html and '{% load static' not in html:
            # Füge nach {% extends %} oder am Anfang hinzu
            if '{% extends' in html:
                html = re.sub(
                    r'({% extends [^%]+%})',
                    r'\1\n{% load static %}',
                    html,
                    count=1
                )
            else:
                html = '{% load static %}\n' + html
            return html, True
        return html, False
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _is_view_file(self, file_path: str) -> bool:
        """Prüft ob eine Datei eine View-Datei ist."""
        return "views" in file_path.lower()
    
    def _is_model_file(self, file_path: str) -> bool:
        """Prüft ob eine Datei eine Model-Datei ist."""
        return "models" in file_path.lower()
    
    def _is_python_command(self, command: str) -> bool:
        """Prüft ob ein Command Python/Django ist."""
        python_indicators = [
            "python",
            "manage.py",
            "pytest",
            "pip",
            "celery",
        ]
        return any(ind in command.lower() for ind in python_indicators)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_before_edit(code: str, file_path: str) -> ValidationResult:
    """
    Convenience-Funktion für schnelle Validierung.
    
    Usage:
        from apps.bfagent.agents.django_agent import validate_before_edit
        
        result = validate_before_edit(new_code, "apps/myapp/views.py")
        if not result.valid:
            raise ValueError(f"Validation failed: {result.errors}")
    """
    agent = DjangoAgent()
    
    if file_path.endswith(".html"):
        return agent.validate_template(code, file_path)
    elif file_path.endswith(".py"):
        return agent.validate_python_file(code, file_path)
    else:
        return ValidationResult(valid=True)


def validate_command(command: str) -> ValidationResult:
    """
    Convenience-Funktion für Command-Validierung.
    
    Usage:
        from apps.bfagent.agents.django_agent import validate_command
        
        result = validate_command("python manage.py migrate")
        if not result.valid:
            # Command muss in WSL laufen
            fixed_command = result.errors[0].fix_suggestion
    """
    agent = DjangoAgent()
    return agent.validate_command(command)


def auto_fix_code(code: str, file_path: str = "unknown.py") -> FixResult:
    """
    Convenience-Funktion für automatische Code-Reparatur.
    
    Usage:
        from apps.bfagent.agents.django_agent import auto_fix_code
        
        result = auto_fix_code(code, "apps/myapp/views.py")
        if result.changed:
            print(f"Fixes: {result.fixes_applied}")
            # Speichere result.fixed_code
    """
    agent = DjangoAgent()
    return agent.auto_fix(code, file_path)


def validate_and_fix(code: str, file_path: str) -> Tuple[ValidationResult, FixResult]:
    """
    Validiert und fixt Code in einem Schritt.
    
    Usage:
        validation, fix = validate_and_fix(code, "views.py")
        if not validation.valid and fix.changed:
            print("Issues found and fixed!")
            new_code = fix.fixed_code
    """
    agent = DjangoAgent()
    validation = agent.validate_python_file(code, file_path)
    fix = agent.auto_fix(code, file_path)
    return validation, fix
