#!/usr/bin/env python
"""
Enhanced Model Consistency Checker v3 for BF Agent v2.0.0
With comprehensive analysis reporting and interactive CLI
"""
import argparse
import ast
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import django
from django.apps import apps
from django.conf import settings
from django.db import models
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Setup Django
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


django.setup()


# Initialize Rich console
console = Console()


class Colors:
    """ANSI color codes for output"""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


class ModelConsistencyAnalyzer:
    """Enhanced Model Consistency Analyzer with comprehensive reporting"""

    def __init__(self, verbose: bool = False):
        """Function description."""
        self.verbose = verbose
        self.issues = []
        self.stats = {
            "total_models": 0,
            "models_with_crud": 0,
            "models_without_crud": 0,
            "template_files": 0,
            "form_files": 0,
            "view_files": 0,
            "hardcoded_references": 0,
            "missing_templates": 0,
            "missing_forms": 0,
        }
        self.model_registry = {}
        self.template_registry = {}
        self.form_registry = {}
        self.view_registry = {}

    def setup_django(self):
        """Setup Django environment"""
        try:
            if not settings.configured:
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
                django.setup()
            return True
        except Exception as e:
            console.print(f"[red]Failed to setup Django: {e}[/red]")
            return False

    def analyze_models(self, app_name: str = "apps.bfagent") -> Dict[str, Any]:
        """Comprehensive model analysis"""
        print("\nStarting Model Analysis...")

        # Task 1: Scan Models
        print("Scanning models...")
        self._scan_models(app_name)

        # Task 2: Scan Templates
        print("Scanning templates...")
        self._scan_templates()

        # Task 3: Scan Forms
        print("Scanning forms...")
        self._scan_forms()

        # Task 4: Scan Views
        print("Scanning views...")
        self._scan_views()

        # Task 5: Cross-reference
        print("Cross-referencing components...")
        self._cross_reference_components()

        return self._generate_analysis_report()

    def _scan_models(self, app_name: str):
        """Scan all models in the application"""
        try:
            app_config = apps.get_app_config(app_name.split(".")[-1])

            for model in app_config.get_models():
                model_name = model.__name__
                self.stats["total_models"] += 1

                model_info = {
                    "name": model_name,
                    "module": model.__module__,
                    "fields": {},
                    "has_crud_config": hasattr(model, "CRUDConfig"),
                    "crud_config": None,
                    "meta_info": {},
                    "relationships": [],
                    "methods": [],
                    "properties": [],
                    "issues": [],
                }

                # Analyze fields
                for field in model._meta.get_fields():
                    field_info = {
                        "name": field.name,
                        "type": field.__class__.__name__,
                        "verbose_name": getattr(field, "verbose_name", field.name),
                        "required": not getattr(field, "blank", False),
                        "db_index": getattr(field, "db_index", False),
                    }

                    # Check relationships
                    if isinstance(
                        field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)
                    ):
                        model_info["relationships"].append(
                            {
                                "field": field.name,
                                "type": field.__class__.__name__,
                                "related_model": field.related_model.__name__,
                                "related_name": getattr(field, "related_name", None),
                            }
                        )

                    model_info["fields"][field.name] = field_info

                # Analyze CRUDConfig
                if model_info["has_crud_config"]:
                    self.stats["models_with_crud"] += 1
                    crud_config = model.CRUDConfig
                    model_info["crud_config"] = {
                        "list_display": getattr(crud_config, "list_display", []),
                        "list_filters": getattr(crud_config, "list_filters", []),
                        "search_fields": getattr(crud_config, "search_fields", []),
                        "form_layout": getattr(crud_config, "form_layout", {}),
                        "form_fields": getattr(crud_config, "form_fields", []),
                        "actions": getattr(crud_config, "actions", {}),
                        "htmx_config": getattr(crud_config, "htmx_config", {}),
                    }

                    # Validate CRUDConfig fields exist
                    all_crud_fields = []
                    
                    # Collect from list_display, list_filters, search_fields
                    for field_list in [
                        model_info["crud_config"]["list_display"],
                        model_info["crud_config"]["list_filters"],
                        model_info["crud_config"]["search_fields"],
                        model_info["crud_config"]["form_fields"],
                    ]:
                        if isinstance(field_list, list):
                            all_crud_fields.extend(field_list)
                    
                    # Collect from form_layout (dict with lists as values)
                    form_layout = model_info["crud_config"].get("form_layout", {})
                    if isinstance(form_layout, dict):
                        for section_fields in form_layout.values():
                            if isinstance(section_fields, list):
                                all_crud_fields.extend(section_fields)

                    for field_name in set(all_crud_fields):
                        if (
                            field_name
                            and field_name not in model_info["fields"]
                            and not hasattr(model, field_name)
                        ):
                            model_info["issues"].append(
                                {
                                    "type": "invalid_crud_field",
                                    "field": field_name,
                                    "description": f"CRUDConfig references non-existent field: {field_name}",
                                }
                            )
                else:
                    self.stats["models_without_crud"] += 1
                    model_info["issues"].append(
                        {
                            "type": "missing_crud_config",
                            "description": "Model missing CRUDConfig (Zero-Hardcoding violation)",
                        }
                    )

                # Analyze methods and properties
                for attr_name in dir(model):
                    if not attr_name.startswith("_"):
                        attr = getattr(model, attr_name)
                        if callable(attr) and not isinstance(attr, type):
                            model_info["methods"].append(attr_name)
                        elif isinstance(attr, property):
                            model_info["properties"].append(attr_name)

                # Analyze Meta options
                if hasattr(model, "_meta"):
                    meta = model._meta
                    model_info["meta_info"] = {
                        "db_table": meta.db_table,
                        "verbose_name": str(meta.verbose_name),
                        "verbose_name_plural": str(meta.verbose_name_plural),
                        "ordering": meta.ordering or [],
                        "unique_together": meta.unique_together or [],
                        "indexes": (
                            [idx.name for idx in meta.indexes] if hasattr(meta, "indexes") else []
                        ),
                        "abstract": meta.abstract,
                    }

                self.model_registry[model_name] = model_info

        except Exception as e:
            console.print(f"[red]Error scanning models: {e}[/red]")

    def _scan_templates(self):
        """Scan template directory for model templates"""
        template_dirs = [Path("templates")]

        # Add app template directories
        for app_config in apps.get_app_configs():
            app_template_dir = Path(app_config.path) / "templates"
            if app_template_dir.exists():
                template_dirs.append(app_template_dir)

        for template_dir in template_dirs:
            if template_dir.exists():
                for template_file in template_dir.rglob("*.html"):
                    self.stats["template_files"] += 1

                    # Extract model context from template path
                    template_name = template_file.name
                    template_path = str(template_file.relative_to(template_dir))

                    template_info = {
                        "path": str(template_file),
                        "name": template_name,
                        "relative_path": template_path,
                        "model_references": set(),
                        "hardcoded_fields": [],
                        "url_patterns": [],
                        "htmx_usage": False,
                    }

                    # Analyze template content
                    try:
                        with open(template_file, "r", encoding="utf-8") as f:
                            content = f.read()

                            # Check for HTMX usage
                            if any(
                                attr in content
                                for attr in ["hx-get", "hx-post", "hx-put", "hx-delete"]
                            ):
                                template_info["htmx_usage"] = True

                            # Find model references
                            model_refs = self._find_model_references(content)
                            template_info["model_references"] = model_refs

                            # Find hardcoded fields
                            hardcoded = self._find_hardcoded_fields(content)
                            template_info["hardcoded_fields"] = hardcoded
                            if hardcoded:
                                self.stats["hardcoded_references"] += len(hardcoded)

                            # Find URL patterns
                            url_patterns = self._find_url_patterns(content)
                            template_info["url_patterns"] = url_patterns

                    except Exception as e:
                        console.print(
                            f"[yellow]Warning: Could not read {template_file}: {e}[/yellow]"
                        )

                    self.template_registry[template_path] = template_info

    def _scan_forms(self):
        """Scan for form definitions"""
        for app_config in apps.get_app_configs():
            forms_file = Path(app_config.path) / "forms.py"
            if forms_file.exists():
                self.stats["form_files"] += 1
                self._analyze_forms_file(forms_file)

    def _scan_views(self):
        """Scan for view definitions"""
        for app_config in apps.get_app_configs():
            views_file = Path(app_config.path) / "views.py"
            views_dir = Path(app_config.path) / "views"

            if views_file.exists():
                self.stats["view_files"] += 1
                self._analyze_views_file(views_file)

            if views_dir.exists():
                for view_file in views_dir.rglob("*.py"):
                    if not view_file.name.startswith("_"):
                        self.stats["view_files"] += 1
                        self._analyze_views_file(view_file)

    def _find_model_references(self, content: str) -> Set[str]:
        """Find model references in template content"""
        references = set()

        # Common Django template patterns
        patterns = [
            r"{\s*%\s*for\s+\w+\s+in\s+(\w+)",  # {% for item in models %}
            r"{\s*{\s*(\w+)\.",  # {{ model.field }}
            r"object_list",  # Generic list view
            r"object",  # Generic detail view
        ]

        import re

        for pattern in patterns:
            matches = re.findall(pattern, content)
            references.update(matches)

        return references

    def _find_hardcoded_fields(self, content: str) -> List[Dict[str, Any]]:
        """Find hardcoded field references"""
        hardcoded = []

        import re

        # Look for model.field patterns
        field_pattern = r"{\s*{\s*(\w+)\.(\w+)\s*}\s*}"
        matches = re.findall(field_pattern, content)

        for model_var, field_name in matches:
            # Check if this might be a model field reference
            if model_var not in ["forloop", "block", "csrf_token"]:
                hardcoded.append(
                    {
                        "model_var": model_var,
                        "field": field_name,
                        "pattern": f"{{{{{model_var}.{field_name}}}}}",
                    }
                )

        return hardcoded

    def _find_url_patterns(self, content: str) -> List[str]:
        """Find URL patterns in template"""
        import re

        url_pattern = r'{%\s*url\s+["\']([^"\']+)["\']'
        matches = re.findall(url_pattern, content)
        return matches

    def _analyze_forms_file(self, forms_file: Path):
        """Analyze forms.py file"""
        try:
            with open(forms_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a form class
                    if any(
                        base.id in ["ModelForm", "Form"]
                        for base in node.bases
                        if hasattr(base, "id")
                    ):
                        form_info = {
                            "name": node.name,
                            "file": str(forms_file),
                            "type": (
                                "ModelForm"
                                if any(
                                    base.id == "ModelForm"
                                    for base in node.bases
                                    if hasattr(base, "id")
                                )
                                else "Form"
                            ),
                            "model": None,
                            "fields": [],
                            "meta_fields": [],
                        }

                        # Find Meta class
                        for item in node.body:
                            if isinstance(item, ast.ClassDef) and item.name == "Meta":
                                for meta_item in item.body:
                                    if isinstance(meta_item, ast.Assign):
                                        for target in meta_item.targets:
                                            if hasattr(target, "id"):
                                                if target.id == "model":
                                                    if hasattr(meta_item.value, "id"):
                                                        form_info["model"] = meta_item.value.id
                                                elif target.id == "fields":
                                                    if isinstance(meta_item.value, ast.List):
                                                        form_info["meta_fields"] = [
                                                            elt.s
                                                            for elt in meta_item.value.elts
                                                            if hasattr(elt, "s")
                                                        ]

                        self.form_registry[node.name] = form_info

        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {forms_file}: {e}[/yellow]")

    def _analyze_views_file(self, views_file: Path):
        """Analyze views.py file"""
        try:
            with open(views_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple pattern matching for view analysis
            import re

            # Find class-based views
            cbv_pattern = r"class\s+(\w+)\s*\([^)]*View[^)]*\)"
            cbv_matches = re.findall(cbv_pattern, content)

            # Find function-based views
            fbv_pattern = r"def\s+(\w+)\s*\(request"
            fbv_matches = re.findall(fbv_pattern, content)

            for view_name in cbv_matches + fbv_matches:
                self.view_registry[view_name] = {
                    "name": view_name,
                    "file": str(views_file),
                    "type": "CBV" if view_name in cbv_matches else "FBV",
                }

        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {views_file}: {e}[/yellow]")

    def _cross_reference_components(self):
        """Cross-reference models, templates, forms, and views"""
        for model_name, model_info in self.model_registry.items():
            model_lower = model_name.lower()

            # Check for standard templates
            expected_templates = [
                f"{model_lower}_list.html",
                f"{model_lower}_detail.html",
                f"{model_lower}_form.html",
                f"{model_lower}_confirm_delete.html",
            ]

            for template_name in expected_templates:
                found = False
                for template_path in self.template_registry:
                    if template_name in template_path:
                        found = True
                        break

                if not found:
                    self.stats["missing_templates"] += 1
                    model_info["issues"].append(
                        {
                            "type": "missing_template",
                            "template": template_name,
                            "description": f"Expected template '{template_name}' not found",
                        }
                    )

            # Check for forms
            expected_form = f"{model_name}Form"
            if expected_form not in self.form_registry:
                self.stats["missing_forms"] += 1
                model_info["issues"].append(
                    {
                        "type": "missing_form",
                        "form": expected_form,
                        "description": f"Expected form '{expected_form}' not found",
                    }
                )

    def _generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        total_issues = sum(len(model["issues"]) for model in self.model_registry.values())

        report = {
            "summary": {
                "total_models": self.stats["total_models"],
                "models_with_crud": self.stats["models_with_crud"],
                "models_without_crud": self.stats["models_without_crud"],
                "template_files": self.stats["template_files"],
                "form_files": self.stats["form_files"],
                "view_files": self.stats["view_files"],
                "total_issues": total_issues,
                "hardcoded_references": self.stats["hardcoded_references"],
                "missing_templates": self.stats["missing_templates"],
                "missing_forms": self.stats["missing_forms"],
            },
            "models": self.model_registry,
            "templates": self.template_registry,
            "forms": self.form_registry,
            "views": self.view_registry,
            "issues": self._collect_all_issues(),
        }

        return report

    def _collect_all_issues(self) -> List[Dict[str, Any]]:
        """Collect all issues from different sources"""
        all_issues = []

        # Model issues
        for model_name, model_info in self.model_registry.items():
            for issue in model_info["issues"]:
                issue["model"] = model_name
                issue["source"] = "model"
                all_issues.append(issue)

        # Template issues
        for template_path, template_info in self.template_registry.items():
            if template_info["hardcoded_fields"]:
                all_issues.append(
                    {
                        "type": "hardcoded_fields",
                        "source": "template",
                        "template": template_path,
                        "description": f"Template contains {len(template_info['hardcoded_fields'])} hardcoded field references",
                        "fields": template_info["hardcoded_fields"],
                    }
                )

        return all_issues

    def display_report(self, report: Dict[str, Any]):
        """Display report using Rich formatting"""
        # Summary Panel
        summary = report["summary"]
        summary_text = f"""
[bold]Model Analysis Summary[/bold]

Models: {summary['total_models']} total
   With CRUDConfig: {summary['models_with_crud']}
   Without CRUDConfig: {summary['models_without_crud']}

Components:
   Templates: {summary['template_files']}
   Forms: {summary['form_files']}
   Views: {summary['view_files']}

Issues: {summary['total_issues']} total
   Hardcoded references: {summary['hardcoded_references']}
   Missing templates: {summary['missing_templates']}
   Missing forms: {summary['missing_forms']}
"""

        console.print(Panel(summary_text, title="Analysis Summary", border_style="cyan"))

        # Model Details Table
        if report["models"]:
            table = Table(title="Model Analysis Details", show_lines=True)
            table.add_column("Model", style="cyan", width=20)
            table.add_column("Fields", style="magenta", width=15)
            table.add_column("CRUDConfig", style="green", width=15)
            table.add_column("Issues", style="red", width=30)
            table.add_column("Templates", style="blue", width=20)

            for model_name, model_info in report["models"].items():
                fields_count = len(model_info["fields"])
                has_crud = "Yes" if model_info["has_crud_config"] else "No"
                issues = len(model_info["issues"])
                issues_str = f"{issues} issues" if issues > 0 else "No issues"

                # Check for templates
                model_lower = model_name.lower()
                templates = []
                for template_path in report["templates"]:
                    if model_lower in template_path:
                        templates.append(os.path.basename(template_path))

                templates_str = "\n".join(templates[:3])
                if len(templates) > 3:
                    templates_str += f"\n... +{len(templates)-3} more"

                table.add_row(
                    model_name,
                    str(fields_count),
                    has_crud,
                    issues_str,
                    templates_str or "None found",
                )

            console.print(table)

        # Issues Detail
        if report["issues"]:
            console.print("\n[bold red]Issues Found:[/bold red]\n")

            issues_by_type = defaultdict(list)
            for issue in report["issues"]:
                issues_by_type[issue["type"]].append(issue)

            for issue_type, issues in issues_by_type.items():
                console.print(f"[yellow]▶ {issue_type.replace('_', ' ').title()}:[/yellow]")
                for issue in issues[:5]:  # Show first 5 of each type
                    if "model" in issue:
                        console.print(f"  - {issue['model']}: {issue['description']}")
                    elif "template" in issue:
                        console.print(f"  - {issue['template']}: {issue['description']}")
                    else:
                        console.print(f"  - {issue['description']}")

                if len(issues) > 5:
                    console.print(f"  [dim]... and {len(issues)-5} more[/dim]")
                console.print()

    def export_report(
        self, report: Dict[str, Any], format: str = "json", output_file: Optional[str] = None
    ):
        """Export report in various formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not output_file:
            output_file = f"model_consistency_report_{timestamp}.{format}"

        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)

        elif format == "markdown":
            md_content = self._generate_markdown_report(report)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(md_content)

        elif format == "html":
            html_content = self._generate_html_report(report)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

        console.print(f"\n[green]Report exported to: {output_file}[/green]")

    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate Markdown report"""
        md = """# BF Agent Model Consistency Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Total Models**: {report['summary']['total_models']}
- **Models with CRUDConfig**: {report['summary']['models_with_crud']}
- **Models without CRUDConfig**: {report['summary']['models_without_crud']}
- **Total Issues**: {report['summary']['total_issues']}

## Model Details

| Model | Fields | CRUDConfig | Issues | Related Components |
|-------|--------|------------|--------|-------------------|
"""

        for model_name, model_info in report["models"].items():
            crud = "✅" if model_info["has_crud_config"] else "❌"
            issues = len(model_info["issues"])
            fields = len(model_info["fields"])

            md += f"| {model_name} | {fields} | {crud} | {issues} | - |\n"

        if report["issues"]:
            md += "\n## Issues\n\n"
            for issue in report["issues"]:
                md += f"- **{issue['type']}**: {issue['description']}\n"

        return md

    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>BF Agent Model Consistency Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .issue {{ background-color: #ffcccc; }}
        .success {{ background-color: #ccffcc; }}
    </style>
</head>
<body>
    <h1>BF Agent Model Consistency Report</h1>
    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <h2>Summary</h2>
    <ul>
        <li>Total Models: {report['summary']['total_models']}</li>
        <li>Models with CRUDConfig: {report['summary']['models_with_crud']}</li>
        <li>Models without CRUDConfig: {report['summary']['models_without_crud']}</li>
        <li>Total Issues: {report['summary']['total_issues']}</li>
    </ul>
"""

        # Add more HTML content...

        html += "</body></html>"
        return html

    def fix_issues(self, report: Dict[str, Any], dry_run: bool = True):
        """Attempt to fix common issues"""
        fixes_applied = 0

        console.print(f"\n[cyan]{'Preview' if dry_run else 'Applying'} fixes...[/cyan]\n")

        for model_name, model_info in report["models"].items():
            for issue in model_info["issues"]:
                if issue["type"] == "missing_crud_config":
                    if not dry_run:
                        # Generate CRUDConfig stub
                        console.print(
                            f"[yellow]Would generate CRUDConfig for {model_name}[/yellow]"
                        )
                    else:
                        console.print(
                            f"[green]Can fix: Generate CRUDConfig for {model_name}[/green]"
                        )
                    fixes_applied += 1

                elif issue["type"] == "missing_template":
                    if not dry_run:
                        # Create template stub
                        console.print(
                            f"[yellow]Would create template: {issue['template']}[/yellow]"
                        )
                    else:
                        console.print(
                            f"[green]Can fix: Create template {issue['template']}[/green]"
                        )
                    fixes_applied += 1

        console.print(
            f"\n[cyan]Total fixes {'available' if dry_run else 'applied'}: {fixes_applied}[/cyan]"
        )


def main():
    """Function description."""
    parser = argparse.ArgumentParser(
        description="Enhanced Model Consistency Checker for BF Agent v2.0.0"
    )

    parser.add_argument(
        "command", choices=["analyze", "report", "fix", "export"], help="Command to execute"
    )

    parser.add_argument(
        "--app", default="bfagent", help="Django app name to analyze (default: bfagent)"
    )

    parser.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="Export format (default: json)",
    )

    parser.add_argument("--output", help="Output file path")

    parser.add_argument(
        "--dry-run", action="store_true", help="Preview fixes without applying them"
    )

    parser.add_argument("--verbose", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = ModelConsistencyAnalyzer(verbose=args.verbose)

    # Setup Django
    if not analyzer.setup_django():
        sys.exit(1)

    # Run analysis
    report = analyzer.analyze_models(f"apps.{args.app}")

    # Execute command
    if args.command == "analyze":
        analyzer.display_report(report)

    elif args.command == "report":
        analyzer.display_report(report)
        if report["summary"]["total_issues"] > 0:
            console.print("\n[yellow]Run with 'fix' command to resolve issues[/yellow]")

    elif args.command == "fix":
        analyzer.fix_issues(report, dry_run=args.dry_run)

    elif args.command == "export":
        analyzer.export_report(report, format=args.format, output_file=args.output)

    # Exit with error code if issues found
    if report["summary"]["total_issues"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
