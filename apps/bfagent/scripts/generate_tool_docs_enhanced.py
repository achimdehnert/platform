#!/usr/bin/env python
"""
Enhanced Tool Documentation Generator with Deep Code Analysis
Automatically generates comprehensive documentation for all BF Agent tools including function analysis
"""

import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import django

# Setup Django
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django.setup()


class EnhancedToolDocumentationGenerator:
    def __init__(self):
        """Function description."""
        self.project_root = Path(__file__).resolve().parent.parent
        self.tools = {}
        self.function_patterns = {
            "formatters": ["format", "black", "isort", "style"],
            "scanners": ["scan", "check", "validate", "analyze"],
            "generators": ["generate", "create", "build", "make"],
            "fixers": ["fix", "repair", "resolve", "correct"],
            "exporters": ["export", "save", "write", "output"],
            "importers": ["import", "load", "read", "parse"],
            "validators": ["validate", "verify", "test", "assert"],
            "transformers": ["transform", "convert", "migrate", "update"],
        }

    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Deep analysis of Python file - functions, classes, imports"""
        analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "main_functions": [],
            "docstring": "",
            "complexity_score": 0,
            "function_categories": {},
            "file_size": 0,
            "line_count": 0,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            analysis["file_size"] = len(content)
            analysis["line_count"] = len(content.splitlines())

            # Parse AST
            tree = ast.parse(content)

            # Extract module docstring
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
            ):
                analysis["docstring"] = tree.body[0].value.value

            # Analyze nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node) or "",
                        "line_number": node.lineno,
                        "is_private": node.name.startswith("_"),
                        "is_main": node.name == "main",
                        "arg_count": len(node.args.args),
                    }

                    # Categorize function
                    func_category = self.categorize_function(node.name)
                    if func_category:
                        func_info["category"] = func_category
                        if func_category not in analysis["function_categories"]:
                            analysis["function_categories"][func_category] = []
                        analysis["function_categories"][func_category].append(node.name)

                    analysis["functions"].append(func_info)

                    if node.name == "main":
                        analysis["main_functions"].append(func_info)

                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "methods": [],
                        "docstring": ast.get_docstring(node) or "",
                        "line_number": node.lineno,
                    }

                    # Get methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append(item.name)

                    analysis["classes"].append(class_info)

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            analysis["imports"].append(f"{node.module}.{alias.name}")

            # Calculate complexity score
            analysis["complexity_score"] = len(analysis["functions"]) + len(analysis["classes"]) * 2

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    def categorize_function(self, func_name: str) -> Optional[str]:
        """Categorize function based on name patterns"""
        func_lower = func_name.lower()

        for category, patterns in self.function_patterns.items():
            if any(pattern in func_lower for pattern in patterns):
                return category

        return None

    def scan_makefile_commands(self) -> Dict[str, Any]:
        """Scan Makefile for available commands"""
        makefile_path = self.project_root / "Makefile"
        tools = {}

        if not makefile_path.exists():
            return tools

        with open(makefile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all make targets with descriptions
        pattern = r"^([a-zA-Z0-9_-]+):\s*##\s*(.+)$"
        for match in re.finditer(pattern, content, re.MULTILINE):
            target = match.group(1)
            description = match.group(2)

            tools[target] = {
                "name": target,
                "type": "make_command",
                "description": description,
                "command": f"make {target}",
                "source": "Makefile",
            }

        return tools

    def scan_script_directory(self) -> Dict[str, Any]:
        """Scan scripts directory for Python tools with deep analysis"""
        scripts_dir = self.project_root / "scripts"
        tools = {}

        if not scripts_dir.exists():
            return tools

        for script_file in scripts_dir.glob("*.py"):
            if script_file.name.startswith("__"):
                continue

            tool_name = script_file.stem
            tools[tool_name] = {
                "name": tool_name,
                "type": "python_script",
                "path": str(script_file.relative_to(self.project_root)),
                "command": f"python {script_file.relative_to(self.project_root)}",
                "source": "scripts directory",
            }

            # Deep code analysis
            code_analysis = self.analyze_python_file(script_file)
            tools[tool_name]["code_analysis"] = code_analysis

            # Extract description from docstring or help
            if code_analysis.get("docstring"):
                # Use first line of docstring as description
                first_line = code_analysis["docstring"].split("\n")[0].strip()
                if first_line:
                    tools[tool_name]["description"] = first_line

            # Try to get help text
            try:
                result = subprocess.run(
                    [sys.executable, str(script_file), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.project_root,
                )
                if result.returncode == 0:
                    tools[tool_name]["help_text"] = result.stdout
                    # Extract description from help if not from docstring
                    if not tools[tool_name].get("description"):
                        lines = result.stdout.split("\n")
                        for line in lines:
                            if line.strip() and not line.startswith("usage:"):
                                tools[tool_name]["description"] = line.strip()
                                break
            except Exception as e:
                tools[tool_name]["help_error"] = str(e)

        return tools

    def scan_registry_tools(self) -> Dict[str, Any]:
        """Scan Control Center registry for tools"""
        tools = {}

        try:
            from apps.control_center.registry import tool_registry

            for tool_name, tool_info in tool_registry.tools.items():
                tools[tool_name] = {
                    "name": tool_name,
                    "type": "registry_tool",
                    "description": tool_info.description,
                    "version": tool_info.version,
                    "category": tool_info.category,
                    "executable_path": tool_info.executable_path,
                    "make_command": tool_info.make_command,
                    "api_endpoint": tool_info.api_endpoint,
                    "parameters": tool_info.parameters,
                    "source": "Control Center Registry",
                }
        except Exception as e:
            print(f"Error scanning registry: {e}")

        return tools

    def find_duplicate_functions(self, tools: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find potentially duplicate functions across tools"""
        function_map = {}
        duplicates = {}

        for tool_name, tool_info in tools.items():
            if "code_analysis" not in tool_info:
                continue

            for func in tool_info["code_analysis"].get("functions", []):
                func_name = func["name"]
                if func_name.startswith("_"):  # Skip private functions
                    continue

                if func_name not in function_map:
                    function_map[func_name] = []
                function_map[func_name].append(tool_name)

        # Find duplicates
        for func_name, tools_list in function_map.items():
            if len(tools_list) > 1:
                duplicates[func_name] = tools_list

        return duplicates

    def analyze_tool_overlap(self, tools: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overlap and consolidation opportunities"""
        analysis = {
            "duplicate_functions": self.find_duplicate_functions(tools),
            "similar_tools": {},
            "consolidation_opportunities": [],
            "category_analysis": {},
        }

        # Group by function categories
        category_tools = {}
        for tool_name, tool_info in tools.items():
            if "code_analysis" not in tool_info:
                continue

            categories = tool_info["code_analysis"].get("function_categories", {})
            for category, functions in categories.items():
                if category not in category_tools:
                    category_tools[category] = {}
                category_tools[category][tool_name] = functions

        analysis["category_analysis"] = category_tools

        # Find consolidation opportunities
        for category, tools_in_category in category_tools.items():
            if len(tools_in_category) > 1:
                analysis["consolidation_opportunities"].append(
                    {
                        "category": category,
                        "tools": list(tools_in_category.keys()),
                        "function_count": sum(len(funcs) for funcs in tools_in_category.values()),
                    }
                )

        return analysis

    def merge_tool_info(self, *tool_dicts) -> Dict[str, Any]:
        """Merge tool information from different sources"""
        merged = {}

        for tool_dict in tool_dicts:
            for tool_name, tool_info in tool_dict.items():
                if tool_name not in merged:
                    merged[tool_name] = tool_info
                else:
                    # Merge information, registry takes precedence
                    existing = merged[tool_name]
                    if tool_info.get("type") == "registry_tool":
                        merged[tool_name] = {**existing, **tool_info}
                    else:
                        merged[tool_name] = {**tool_info, **existing}

        return merged

    def generate_enhanced_markdown_docs(
        self, tools: Dict[str, Any], analysis: Dict[str, Any]
    ) -> str:
        """Generate enhanced markdown documentation with function analysis"""
        doc = """# BF Agent Tools Documentation - Enhanced Analysis
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
This document provides comprehensive information about all available tools in the BF Agent system, including deep code analysis.

**Total Tools**: {len(tools)}
**Duplicate Functions Found**: {len(analysis['duplicate_functions'])}
**Consolidation Opportunities**: {len(analysis['consolidation_opportunities'])}

## Consolidation Analysis

### Duplicate Functions
The following functions appear in multiple tools and could be consolidated:

"""

        for func_name, tool_list in analysis["duplicate_functions"].items():
            doc += f"- **{func_name}**: Found in {', '.join(tool_list)}\n"

        doc += "\n### Consolidation Opportunities\n\n"

        for opportunity in analysis["consolidation_opportunities"]:
            doc += f"- **{opportunity['category'].title()}**: {len(opportunity['tools'])} tools with {opportunity['function_count']} total functions\n"
            doc += f"  - Tools: {', '.join(opportunity['tools'])}\n"

        doc += "\n## Tools by Category\n\n"

        # Group by category
        categories = {}
        for tool_name, tool_info in tools.items():
            category = tool_info.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append((tool_name, tool_info))

        for category, category_tools in sorted(categories.items()):
            doc += f"### {category.title()}\n\n"

            for tool_name, tool_info in sorted(category_tools):
                doc += f"#### {tool_name}\n\n"
                doc += f"**Description**: {tool_info.get('description', 'No description available')}\n\n"

                if tool_info.get("version"):
                    doc += f"**Version**: {tool_info['version']}\n\n"

                # Code analysis
                if "code_analysis" in tool_info:
                    analysis_data = tool_info["code_analysis"]
                    doc += "**Code Analysis**:\n"
                    doc += f"- Functions: {len(analysis_data.get('functions', []))}\n"
                    doc += f"- Classes: {len(analysis_data.get('classes', []))}\n"
                    doc += f"- Lines of Code: {analysis_data.get('line_count', 0)}\n"
                    doc += f"- Complexity Score: {analysis_data.get('complexity_score', 0)}\n"

                    # Function categories
                    if analysis_data.get("function_categories"):
                        doc += f"- Function Categories: {', '.join(analysis_data['function_categories'].keys())}\n"

                    doc += "\n"

                    # List main functions
                    public_functions = [
                        f for f in analysis_data.get("functions", []) if not f["is_private"]
                    ]
                    if public_functions:
                        doc += "**Main Functions**:\n"
                        for func in public_functions[:5]:  # Limit to first 5
                            doc += f"- `{func['name']}({', '.join(func['args'])})` - {func.get('docstring', 'No description')[:50]}...\n"
                        if len(public_functions) > 5:
                            doc += f"- ... and {len(public_functions) - 5} more functions\n"
                        doc += "\n"

                # Usage information
                doc += "**Usage**:\n"
                if tool_info.get("make_command"):
                    doc += f"- Make: `make {tool_info['make_command']}`\n"
                if tool_info.get("executable_path"):
                    doc += f"- Direct: `python {tool_info['executable_path']}`\n"
                if tool_info.get("command"):
                    doc += f"- Command: `{tool_info['command']}`\n"
                doc += "\n"

                # Integration status
                doc += "**Integration Status**:\n"
                doc += f"- Registry: {'✅' if tool_info.get('type') == 'registry_tool' else '❌'}\n"
                doc += f"- Make Command: {'✅' if tool_info.get('make_command') else '❌'}\n"
                doc += f"- Control Center: {'✅' if tool_info.get('api_endpoint') else '❌'}\n"
                doc += "\n---\n\n"

        return doc

    def run(self):
        """Main execution function"""
        print("🔍 Scanning for tools with deep analysis...")

        # Scan all sources
        makefile_tools = self.scan_makefile_commands()
        script_tools = self.scan_script_directory()
        registry_tools = self.scan_registry_tools()

        print(f"Found {len(makefile_tools)} Makefile commands")
        print(f"Found {len(script_tools)} Python scripts")
        print(f"Found {len(registry_tools)} Registry tools")

        # Merge all information
        all_tools = self.merge_tool_info(makefile_tools, script_tools, registry_tools)

        print(f"📊 Total unique tools: {len(all_tools)}")

        # Analyze overlaps and consolidation opportunities
        print("🔍 Analyzing tool overlaps...")
        overlap_analysis = self.analyze_tool_overlap(all_tools)

        print(f"Found {len(overlap_analysis['duplicate_functions'])} duplicate functions")
        print(
            f"Found {len(overlap_analysis['consolidation_opportunities'])} consolidation opportunities"
        )

        # Generate documentation
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Enhanced markdown documentation
        enhanced_doc = self.generate_enhanced_markdown_docs(all_tools, overlap_analysis)
        enhanced_path = docs_dir / "TOOLS_ENHANCED.md"
        with open(enhanced_path, "w", encoding="utf-8") as f:
            f.write(enhanced_doc)
        print(f"📝 Generated: {enhanced_path}")

        # Enhanced JSON documentation
        enhanced_json = {
            "generated": datetime.now().isoformat(),
            "total_tools": len(all_tools),
            "tools": all_tools,
            "analysis": overlap_analysis,
        }

        enhanced_json_path = docs_dir / "tools_enhanced.json"
        with open(enhanced_json_path, "w", encoding="utf-8") as f:
            json.dump(enhanced_json, f, indent=2)
        print(f"📊 Generated: {enhanced_json_path}")

        # Summary
        print("\n✅ Enhanced tool documentation generated successfully!")
        print(f"📋 {len(all_tools)} tools documented with deep analysis")
        print(f"🔍 {len(overlap_analysis['duplicate_functions'])} duplicate functions identified")
        print(
            f"🎯 {len(overlap_analysis['consolidation_opportunities'])} consolidation opportunities found"
        )
        print(f"📁 Documentation saved to: {docs_dir}")

        return all_tools, overlap_analysis


def main():
    """Function description."""
    generator = EnhancedToolDocumentationGenerator()
    generator.run()


if __name__ == "__main__":
    main()
