#!/usr/bin/env python
"""
Enterprise Template URL Validator
Automatically detects and fixes invalid URL patterns in Django templates
"""
import argparse
import sys
from pathlib import Path
from typing import List, Tuple


# Color codes for output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


class TemplateURLValidator:
    """Enterprise-grade template URL validator"""

    def __init__(self):
        """Function description."""
        self.invalid_patterns = []
        self.fixed_patterns = []

    def scan_templates(self, template_dir: str) -> List[Tuple[str, int, str]]:
        """Scan all templates for invalid URL patterns"""
        issues = []
        template_path = Path(template_dir)

        if not template_path.exists():
            print(f"{Colors.RED}❌ Template directory not found: {template_dir}{Colors.END}")
            return issues

        print(f"{Colors.BLUE}🔍 Scanning templates in: {template_dir}{Colors.END}")

        # Find all HTML template files
        html_files = list(template_path.rglob("*.html"))

        for file_path in html_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    # Check for invalid URL patterns
                    if "{% url '...' %}" in line:
                        issues.append((str(file_path), line_num, line.strip()))

            except Exception as e:
                print(f"{Colors.YELLOW}⚠️ Could not read {file_path}: {e}{Colors.END}")

        return issues

    def fix_template_urls(self, template_dir: str, dry_run: bool = True) -> int:
        """Fix invalid URL patterns in templates"""
        issues = self.scan_templates(template_dir)

        if not issues:
            print(f"{Colors.GREEN}✅ No invalid URL patterns found!{Colors.END}")
            return 0

        print(f"{Colors.YELLOW}Found {len(issues)} invalid URL patterns:{Colors.END}")

        fixes_applied = 0

        for file_path, line_num, line_content in issues:
            print(f"{Colors.RED}❌ {file_path}:{line_num}{Colors.END}")
            print(f"   {line_content}")

            if not dry_run:
                # Try to suggest a fix based on context
                suggested_fix = self._suggest_url_fix(file_path, line_content)
                if suggested_fix:
                    print(f"{Colors.GREEN}   Suggested fix: {suggested_fix}{Colors.END}")

                    # Apply the fix
                    if self._apply_fix(file_path, line_num, line_content, suggested_fix):
                        fixes_applied += 1
                        print(f"{Colors.GREEN}   ✅ Fixed!{Colors.END}")
                    else:
                        print(f"{Colors.RED}   ❌ Could not apply fix{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}   ⚠️ Manual fix required{Colors.END}")

        if dry_run:
            print(f"\n{Colors.CYAN}💡 Run with --fix to apply automatic fixes{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}✅ Applied {fixes_applied} fixes{Colors.END}")

        return len(issues)

    def _suggest_url_fix(self, file_path: str, line_content: str) -> str:
        """Suggest a fix based on file context and common patterns"""

        # Common URL pattern mappings
        url_mappings = {
            "project_list.html": "bfagent:project-delete",
            "chapter_list.html": "bfagent:chapter-delete",
            "character_list.html": "bfagent:character-delete",
            "agent_list.html": "bfagent:agent-delete",
        }

        file_name = Path(file_path).name

        # Check if we have a known mapping
        if file_name in url_mappings:
            url_name = url_mappings[file_name]
            return line_content.replace("{% url '...' %}", f"{{% url '{url_name}' object.pk %}}")

        # Try to infer from context
        if "delete" in line_content.lower():
            if "project" in file_path.lower():
                return line_content.replace(
                    "{% url '...' %}", "{% url 'bfagent:project-delete' project.pk %}"
                )
            elif "chapter" in file_path.lower():
                return line_content.replace(
                    "{% url '...' %}", "{% url 'bfagent:chapter-delete' chapter.pk %}"
                )
            elif "character" in file_path.lower():
                return line_content.replace(
                    "{% url '...' %}", "{% url 'bfagent:character-delete' character.pk %}"
                )

        return None

    def _apply_fix(self, file_path: str, line_num: int, old_line: str, new_line: str) -> bool:
        """Apply the fix to the file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Replace the specific line
            if line_num <= len(lines):
                lines[line_num - 1] = new_line + "\n"

                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                return True

        except Exception as e:
            print(f"{Colors.RED}Error applying fix: {e}{Colors.END}")

        return False


def main():
    """Function description."""
    parser = argparse.ArgumentParser(description="Enterprise Template URL Validator")
    parser.add_argument("command", choices=["scan", "fix"], help="Command to execute")
    parser.add_argument("--templates", default="templates/", help="Templates directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed without applying changes"
    )

    args = parser.parse_args()

    validator = TemplateURLValidator()

    if args.command == "scan":
        issues = validator.scan_templates(args.templates)
        if issues:
            print(f"\n{Colors.RED}Found {len(issues)} invalid URL patterns{Colors.END}")
            sys.exit(1)
        else:
            print(f"\n{Colors.GREEN}✅ All URL patterns are valid{Colors.END}")

    elif args.command == "fix":
        issues_count = validator.fix_template_urls(args.templates, dry_run=args.dry_run)
        if issues_count > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
