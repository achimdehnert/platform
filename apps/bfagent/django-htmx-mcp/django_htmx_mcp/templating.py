"""
Jinja2 Template Engine für Code-Generierung.
"""

from pathlib import Path
from typing import Any

import inflect
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Inflect Engine für Pluralisierung
_inflect = inflect.engine()


def pluralize(word: str) -> str:
    """Pluralisiert ein Wort."""
    return _inflect.plural(word) or f"{word}s"


def singularize(word: str) -> str:
    """Singularisiert ein Wort."""
    result = _inflect.singular_noun(word)
    return result if result else word


def snake_case(name: str) -> str:
    """Konvertiert PascalCase/camelCase zu snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def pascal_case(name: str) -> str:
    """Konvertiert snake_case zu PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def camel_case(name: str) -> str:
    """Konvertiert snake_case zu camelCase."""
    words = name.split("_")
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])


def kebab_case(name: str) -> str:
    """Konvertiert PascalCase/snake_case zu kebab-case."""
    return snake_case(name).replace("_", "-")


def model_to_verbose(name: str) -> str:
    """Konvertiert ModelName zu 'model name' (verbose)."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append(" ")
        result.append(char.lower())
    return "".join(result)


# Template Directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Jinja2 Environment
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

# Custom Filters registrieren
env.filters["pluralize"] = pluralize
env.filters["singularize"] = singularize
env.filters["snake_case"] = snake_case
env.filters["pascal_case"] = pascal_case
env.filters["camel_case"] = camel_case
env.filters["kebab_case"] = kebab_case
env.filters["verbose"] = model_to_verbose


def render_template(template_name: str, **context: Any) -> str:
    """
    Rendert ein Jinja2 Template mit dem gegebenen Context.
    
    Args:
        template_name: Name des Templates (relativ zu templates/)
        **context: Template-Variablen
        
    Returns:
        Gerenderter Code als String
    """
    template = env.get_template(template_name)
    return template.render(**context)


def render_string(template_str: str, **context: Any) -> str:
    """
    Rendert einen Template-String mit dem gegebenen Context.
    
    Args:
        template_str: Template als String
        **context: Template-Variablen
        
    Returns:
        Gerenderter Code als String
    """
    template = env.from_string(template_str)
    return template.render(**context)


# === Code Formatting Utilities ===

def indent(code: str, spaces: int = 4) -> str:
    """Indentiert Code um n Spaces."""
    prefix = " " * spaces
    lines = code.split("\n")
    return "\n".join(prefix + line if line.strip() else line for line in lines)


def dedent(code: str) -> str:
    """Entfernt gemeinsame Leading Whitespace."""
    lines = code.split("\n")
    if not lines:
        return code
    
    # Finde minimale Indentation (ignoriere leere Zeilen)
    min_indent = float("inf")
    for line in lines:
        if line.strip():
            leading = len(line) - len(line.lstrip())
            min_indent = min(min_indent, leading)
    
    if min_indent == float("inf"):
        return code
    
    return "\n".join(line[int(min_indent):] if line.strip() else "" for line in lines)


def format_imports(imports: list[str]) -> str:
    """
    Formatiert und sortiert Import-Statements.
    
    Gruppiert nach:
    1. Standard Library
    2. Third Party
    3. Django
    4. Local
    """
    stdlib = []
    third_party = []
    django_imports = []
    local = []
    
    for imp in sorted(set(imports)):
        if imp.startswith("from django") or imp.startswith("import django"):
            django_imports.append(imp)
        elif imp.startswith("from .") or imp.startswith("import ."):
            local.append(imp)
        elif any(imp.startswith(f"from {pkg}") or imp.startswith(f"import {pkg}") 
                 for pkg in ["os", "sys", "re", "json", "typing", "datetime", "uuid", "decimal"]):
            stdlib.append(imp)
        else:
            third_party.append(imp)
    
    groups = []
    if stdlib:
        groups.append("\n".join(sorted(stdlib)))
    if third_party:
        groups.append("\n".join(sorted(third_party)))
    if django_imports:
        groups.append("\n".join(sorted(django_imports)))
    if local:
        groups.append("\n".join(sorted(local)))
    
    return "\n\n".join(groups)
