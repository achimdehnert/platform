#!/usr/bin/env python
"""
BF Agent Code Formatter Tool
Comprehensive code formatting with isort, black, and auto-fixing
"""
import argparse
import subprocess
import sys
from pathlib import Path


class CodeFormatter:
    def __init__(self, project_root: str = ".", verbose: bool = False):
        """Function description."""
        self.project_root = Path(project_root)
        self.verbose = verbose
        self.stats = {"files_processed": 0, "files_modified": 0, "errors": 0, "skipped": 0}

    def log(self, message: str, level: str = "INFO"):
        """Log messages with optional verbosity"""
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "PROCESS": "🔄"}

        if level != "INFO" or self.verbose:
            print(f"{icons.get(level, '•')} {message}")

    def run_command(self, cmd: List[str], description: str) -> tuple[bool, str]:
        """Run a command and return success status and output"""
        self.log(f"Running: {description}", "PROCESS")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode == 0:
                self.log(f"Success: {description}", "SUCCESS")
                return True, result.stdout
            else:
                self.log(f"Failed: {description}", "ERROR")
                if self.verbose:
                    print(f"  Error: {result.stderr}")
                return False, result.stderr

        except Exception as e:
            self.log(f"Exception running {description}: {e}", "ERROR")
            return False, str(e)

    def format_imports(self, specific_files: Optional[List[str]] = None):
        """Format imports using isort"""
        print("\n📦 Formatting imports with isort...")

        cmd = [
            sys.executable,
            "-m",
            "isort",
            "--profile",
            "black",
            "--line-length",
            "100",
            "--multi-line",
            "3",  # Vertical hanging indent
            "--trailing-comma",
            "--force-grid-wrap",
            "0",
            "--use-parentheses",
            "--ensure-newline-before-comments",
            "--skip-gitignore",
            "--skip",
            "migrations",
            "--skip",
            ".venv",
            "--skip",
            "venv",
        ]

        if specific_files:
            cmd.extend(specific_files)
        else:
            cmd.append(".")

        # Add diff flag to see changes
        if self.verbose:
            cmd.append("--di")

        success, output = self.run_command(cmd, "isort formatting")

        if success:
            # Count modified files
            if "--di" in cmd and output:
                self.stats["files_modified"] += output.count("---")
        else:
            self.stats["errors"] += 1

        return success

    def format_code(self, specific_files: Optional[List[str]] = None):
        """Format code using black"""
        print("\n⚫ Formatting code with black...")

        cmd = [
            sys.executable,
            "-m",
            "black",
            "--line-length",
            "100",
            "--target-version",
            "py311",
            "--exclude",
            "/(migrations|\.venv|venv|build|dist)/",
        ]

        if specific_files:
            cmd.extend(specific_files)
        else:
            cmd.append(".")

        # Add diff flag to see changes
        if self.verbose:
            cmd.append("--di")
        else:
            cmd.append("--quiet")

        success, output = self.run_command(cmd, "black formatting")

        if success and "reformatted" in output:
            # Parse black output for stats
            import re

            match = re.search(r"(\d+) file[s]? reformatted", output)
            if match:
                self.stats["files_modified"] += int(match.group(1))
        elif not success:
            self.stats["errors"] += 1

        return success

    def check_flake8(self, specific_files: Optional[List[str]] = None):
        """Check code style with flake8"""
        print("\n🔍 Checking code style with flake8...")

        cmd = [
            sys.executable,
            "-m",
            "flake8",
            "--config",
            ".flake8",
            "--format",
            "%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
            "--statistics",
        ]

        if specific_files:
            cmd.extend(specific_files)
        else:
            cmd.append(".")

        success, output = self.run_command(cmd, "flake8 check")

        if not success and output:
            # Count issues
            issues = len(output.strip().split("\n"))
            self.log(f"Found {issues} style issues", "WARNING")

            if self.verbose:
                print("\nTop issues:")
                # Show first 10 issues
                for line in output.strip().split("\n")[:10]:
                    print(f"  {line}")

                if issues > 10:
                    print(f"  ... and {issues - 10} more issues")

        return success

    def fix_common_issues(self):
        """Fix common issues automatically"""
        print("\n🔧 Fixing common issues...")

        fixes_applied = 0

        # Fix f-strings without placeholders
        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            if any(skip in str(py_file) for skip in ["migrations", ".venv", "venv"]):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                original_content = content

                # Fix f-strings without placeholders
                import re

                # Find f-strings without any {} placeholders
                pattern = r'f(["\'])([^"\'{}]*)(\1)'

                def replace_f_string(match):
                    """Function description."""
                    quote = match.group(1)
                    content = match.group(2)
                    return f"{quote}{content}{quote}"

                content = re.sub(pattern, replace_f_string, content)

                # Fix trailing whitespace
                lines = content.split("\n")
                lines = [line.rstrip() for line in lines]
                content = "\n".join(lines)

                # Ensure file ends with newline
                if content and not content.endswith("\n"):
                    content += "\n"

                if content != original_content:
                    py_file.write_text(content, encoding="utf-8")
                    fixes_applied += 1
                    self.log(f"Fixed issues in {py_file.name}", "SUCCESS")

            except Exception as e:
                self.log(f"Error processing {py_file}: {e}", "ERROR")
                self.stats["errors"] += 1

        self.stats["files_modified"] += fixes_applied
        print(f"  Fixed {fixes_applied} files")

    def format_templates(self):
        """Format Django templates with djhtml"""
        print("\n🎨 Formatting Django templates...")

        cmd = [
            sys.executable,
            "-m",
            "djhtml",
            "--tabwidth",
            "4",
            "--in-place",
        ]

        template_files = list(self.project_root.rglob("*.html"))
        valid_templates = [
            str(f)
            for f in template_files
            if "site-packages" not in str(f) and ".venv" not in str(f)
        ]

        if not valid_templates:
            self.log("No templates found", "WARNING")
            return True

        cmd.extend(valid_templates[:50])  # Limit to 50 files at a time

        success, output = self.run_command(cmd, "djhtml formatting")

        if not success:
            self.stats["errors"] += 1

        return success

    def run_pre_commit_hooks(self, hooks: Optional[List[str]] = None):
        """Run specific pre-commit hooks"""
        print("\n🎣 Running pre-commit hooks...")

        if hooks:
            for hook in hooks:
                cmd = ["pre-commit", "run", hook, "--all-files"]
                success, output = self.run_command(cmd, f"pre-commit {hook}")
                if not success:
                    self.stats["errors"] += 1
        else:
            cmd = ["pre-commit", "run", "--all-files"]
            success, output = self.run_command(cmd, "all pre-commit hooks")
            if not success:
                self.stats["errors"] += 1

        return success

    def fix_precommit_issues(self):
        """Fix all pre-commit hook issues systematically"""
        print("\n🔧 Fixing Pre-commit Issues Systematically...")
        print("=" * 60)

        # Step 1: Fix trailing whitespace in templates and docs
        self.fix_trailing_whitespace()

        # Step 2: Fix common Python issues
        self.fix_common_issues()

        # Step 3: Format imports
        self.format_imports()

        # Step 4: Format code with black
        self.format_code()

        # Step 5: Check final result
        self.check_flake8()

        print("\n🎯 Pre-commit fixes completed!")
        self.print_summary()

    def fix_trailing_whitespace(self):
        """Fix trailing whitespace in templates and markdown files"""
        print("\n🧹 Fixing trailing whitespace...")

        files_fixed = 0

        # Fix HTML templates
        template_files = list(self.project_root.rglob("*.html"))
        for template_file in template_files:
            if any(skip in str(template_file) for skip in [".venv", "venv", "node_modules"]):
                continue

            try:
                content = template_file.read_text(encoding="utf-8")
                original_content = content

                # Remove trailing whitespace from each line
                lines = content.split("\n")
                lines = [line.rstrip() for line in lines]
                content = "\n".join(lines)

                # Ensure file ends with single newline
                if content and not content.endswith("\n"):
                    content += "\n"
                elif content.endswith("\n\n"):
                    content = content.rstrip("\n") + "\n"

                if content != original_content:
                    template_file.write_text(content, encoding="utf-8")
                    files_fixed += 1
                    self.log(f"Fixed trailing whitespace in {template_file.name}", "SUCCESS")

            except Exception as e:
                self.log(f"Error processing {template_file}: {e}", "ERROR")
                self.stats["errors"] += 1

        # Fix Markdown files
        md_files = list(self.project_root.rglob("*.md"))
        for md_file in md_files:
            if any(skip in str(md_file) for skip in [".venv", "venv", "node_modules"]):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                original_content = content

                # Remove trailing whitespace from each line
                lines = content.split("\n")
                lines = [line.rstrip() for line in lines]
                content = "\n".join(lines)

                # Ensure file ends with single newline
                if content and not content.endswith("\n"):
                    content += "\n"

                if content != original_content:
                    md_file.write_text(content, encoding="utf-8")
                    files_fixed += 1
                    self.log(f"Fixed trailing whitespace in {md_file.name}", "SUCCESS")

            except Exception as e:
                self.log(f"Error processing {md_file}: {e}", "ERROR")
                self.stats["errors"] += 1

        self.stats["files_modified"] += files_fixed
        print(f"  Fixed trailing whitespace in {files_fixed} files")

    def create_format_config(self):
        """Create formatting configuration files if they don't exist"""
        print("\n📝 Checking configuration files...")

        # pyproject.toml for black and isort
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            self.log("Creating pyproject.toml", "INFO")
            pyproject_content = """[tool.black]
line-length = 100
target-version = ['py311']
include = '\\.pyi?$'
extend-exclude = '''
/(
  # directories
  \\.eggs
  | \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
  | migrations
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
skip_gitignore = true
skip = ["migrations", ".venv", "venv"]
known_django = ["django"]
known_first_party = ["apps", "config"]
sections = ["FUTURE", "STDLIB", "DJANGO", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]

[tool.djhtml]
tabwidth = 4
"""
            pyproject_path.write_text(pyproject_content)
            self.log("Created pyproject.toml", "SUCCESS")

    def format_all(self, skip_templates: bool = False):
        """Run all formatting operations"""
        print("🚀 BF Agent Code Formatter")
        print("=" * 50)

        # Create config files if needed
        self.create_format_config()

        # Step 1: Fix common issues
        self.fix_common_issues()

        # Step 2: Format imports
        self.format_imports()

        # Step 3: Format code
        self.format_code()

        # Step 4: Format templates (optional)
        if not skip_templates:
            self.format_templates()

        # Step 5: Check with flake8
        self.check_flake8()

        # Print summary
        self.print_summary()

    def format_changed_files(self):
        """Format only files changed in git"""
        print("🚀 Formatting changed files only...")

        # Get list of changed files
        cmd = ["git", "di", "--name-only", "--cached", "--", "*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

        if result.returncode == 0 and result.stdout:
            changed_files = result.stdout.strip().split("\n")
            changed_files = [f for f in changed_files if f]  # Remove empty strings

            if changed_files:
                print(f"Found {len(changed_files)} changed Python files")

                # Format only these files
                self.fix_common_issues()
                self.format_imports(changed_files)
                self.format_code(changed_files)
                self.check_flake8(changed_files)
            else:
                print("No changed Python files found")
        else:
            print("Could not get changed files, formatting all files")
            self.format_all()

        self.print_summary()

    def print_summary(self):
        """Print formatting summary"""
        print("\n" + "=" * 50)
        print("📊 Formatting Summary")
        print("=" * 50)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files modified: {self.stats['files_modified']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Skipped: {self.stats['skipped']}")

        if self.stats["errors"] > 0:
            print("\n⚠️  Some errors occurred. Run with --verbose for details.")
        else:
            print("\n✅ Formatting completed successfully!")

    def watch_mode(self):
        """Watch for file changes and auto-format"""
        print("👁️  Watch mode - Press Ctrl+C to stop")
        print("Watching for file changes...")

        try:
        except ImportError:
            print("❌ watchdog not installed. Run: pip install watchdog")
            return

        class FormatHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, formatter):
                """Function description."""
                self.formatter = formatter
                self.last_formatted = {}

            def on_modified(self, event):
                """Function description."""
                if event.is_directory:
                    return

                path = Path(event.src_path)

                # Only format Python files
                if path.suffix == ".py":
                    # Debounce - don't format same file within 2 seconds
                    import time

                    now = time.time()
                    last = self.last_formatted.get(str(path), 0)

                    if now - last > 2:
                        print(f"\n📝 Formatting {path.name}...")
                        self.formatter.format_imports([str(path)])
                        self.formatter.format_code([str(path)])
                        self.last_formatted[str(path)] = now

        observer = watchdog.observers.Observer()
        handler = FormatHandler(self)

        # Watch specific directories
        watch_dirs = [
            self.project_root / "apps",
            self.project_root / "config",
            self.project_root / "scripts",
        ]

        for watch_dir in watch_dirs:
            if watch_dir.exists():
                observer.schedule(handler, str(watch_dir), recursive=True)

        observer.start()

        try:
            while True:
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\n✋ Watch mode stopped")

        observer.join()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BF Agent Code Formatter - Comprehensive code formatting tool"
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "imports", "code", "check", "fix", "changed", "watch", "precommit"],
        help="Command to run (default: all)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    parser.add_argument("--skip-templates", action="store_true", help="Skip template formatting")

    parser.add_argument("--files", nargs="+", help="Specific files to format")

    parser.add_argument("--hooks", nargs="+", help="Specific pre-commit hooks to run")

    args = parser.parse_args()

    formatter = CodeFormatter(verbose=args.verbose)

    try:
        if args.command == "all":
            formatter.format_all(skip_templates=args.skip_templates)
        elif args.command == "imports":
            formatter.format_imports(args.files)
        elif args.command == "code":
            formatter.format_code(args.files)
        elif args.command == "check":
            formatter.check_flake8(args.files)
        elif args.command == "fix":
            formatter.fix_common_issues()
        elif args.command == "changed":
            formatter.format_changed_files()
        elif args.command == "watch":
            formatter.watch_mode()
        elif args.command == "precommit":
            formatter.fix_precommit_issues()

        if args.hooks:
            formatter.run_pre_commit_hooks(args.hooks)

    except KeyboardInterrupt:
        print("\n\n✋ Formatting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
