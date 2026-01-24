#!/usr/bin/env python
"""
BF Agent Git Sync Tool with Auto-Fix V3
Improved handling of pre-commit conflicts
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class GitSyncAutoFix:
    def __init__(self, project_root: str = ".", verbose: bool = False, auto_fix: bool = True):
        """Function description."""
        self.project_root = Path(project_root)
        self.verbose = verbose
        self.auto_fix = auto_fix
        self.stats = {
            "files_added": 0,
            "files_modified": 0,
            "files_deleted": 0,
            "files_fixed": 0,
            "errors_fixed": 0,
            "total_changes": 0,
        }
        self.fixes_applied = []

    def log(self, message: str, level: str = "INFO"):
        """Log messages with optional verbosity"""
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROCESS": "🔄",
            "FIX": "🔧",
        }

        if level != "INFO" or self.verbose:
            print(f"{icons.get(level, '•')} {message}")

    def run_command(self, cmd: List[str], check_errors: bool = True) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout and stderr"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                encoding="utf-8",
                errors="replace",
            )

            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

        except Exception as e:
            self.log(f"Command failed: {e}", "ERROR")
            return False, "", str(e)

    def run_git_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Run a git command and return success status and output"""
        success, stdout, stderr = self.run_command(["git"] + cmd)
        output = stdout if success else f"{stdout}\n{stderr}".strip()
        return success, output

    def check_and_fix_pre_commit_v2(self) -> Tuple[bool, Dict[str, any]]:
        """Improved pre-commit check that handles conflicts better"""
        self.log("Running pre-commit checks with improved conflict handling...", "PROCESS")

        # First, check if there are any unstaged changes
        success, status_output = self.run_git_command(["status", "--porcelain"])
        has_unstaged = any(line[1] != " " for line in status_output.splitlines() if line)

        if has_unstaged:
            self.log("Detected unstaged changes, staging all files first...", "WARNING")
            # Stage all changes to avoid stash conflicts
            self.run_git_command(["add", "-A"])

        # Run pre-commit without stashing (since everything is staged)
        success, stdout, stderr = self.run_command(
            ["pre-commit", "run", "--all-files", "--show-diff-on-failure"], check_errors=False
        )

        issues = self.parse_pre_commit_output(stdout + "\n" + stderr)

        if success:
            self.log("All pre-commit checks passed!", "SUCCESS")
            return True, {"success": True, "issues": {}}

        # If auto-fixes were applied by hooks, stage them
        if "files were modified by this hook" in stdout + stderr:
            self.log("Pre-commit hooks applied automatic fixes", "FIX")
            self.run_git_command(["add", "-A"])
            self.stats["files_fixed"] += 1
            self.fixes_applied.append("Pre-commit auto-fixes")

            # Run pre-commit again to check if all issues are resolved
            success2, stdout2, stderr2 = self.run_command(
                ["pre-commit", "run", "--all-files"], check_errors=False
            )

            if success2:
                self.log("All issues resolved after auto-fixes!", "SUCCESS")
                return True, {"success": True, "issues": {}}

        return False, {"success": False, "issues": issues}

    def parse_pre_commit_output(self, output: str) -> Dict[str, List[str]]:
        """Parse pre-commit output to identify issues by hook"""
        issues = {
            "black": [],
            "isort": [],
            "flake8": [],
            "djlint": [],
            "yaml": [],
            "trailing-whitespace": [],
            "end-of-file-fixer": [],
            "debug-statements": [],
            "other": [],
        }

        lines = output.split("\n")
        current_hook = None

        for line in lines:
            # Detect hook names
            if "black...." in line:
                current_hook = "black"
            elif "isort...." in line:
                current_hook = "isort"
            elif "flake8..." in line:
                current_hook = "flake8"
            elif "djlint..." in line:
                current_hook = "djlint"
            elif "trailing-whitespace" in line:
                current_hook = "trailing-whitespace"
            elif "end-of-file-fixer" in line:
                current_hook = "end-of-file-fixer"
            elif "debug-statements" in line:
                current_hook = "debug-statements"
            elif "check-yaml" in line or "invalid yaml" in line.lower():
                current_hook = "yaml"

            # Collect error lines
            if current_hook and ("Failed" in line or "error" in line.lower() or "modified" in line):
                if current_hook in issues:
                    issues[current_hook].append(line.strip())
                else:
                    issues["other"].append(line.strip())

        # Clean up empty lists
        return {k: v for k, v in issues.items() if v}

    def sync_all_v2(self, custom_message: Optional[str] = None, push: bool = True) -> bool:
        """Improved sync workflow with better conflict handling"""
        print("🚀 BF Agent Git Sync Tool with Auto-Fix V3")
        print("=" * 50)

        # Get current status
        status = self.get_git_status()

        if "error" in status:
            self.log("Failed to get git status", "ERROR")
            return False

        # Check if there are changes
        total_changes = sum(len(files) for files in status.values())

        if total_changes == 0:
            self.log("No changes to commit", "INFO")
            return True

        self.log(f"\nFound {total_changes} changes to process", "INFO")

        # Run the improved pre-commit check and auto-fix
        if self.auto_fix:
            self.log("\n🔧 Running automatic fixes with improved conflict handling...", "PROCESS")
            check_success, check_result = self.check_and_fix_pre_commit_v2()

            if not check_success and check_result["issues"]:
                # Try to fix remaining issues
                self.log("Attempting to fix remaining issues...", "FIX")
                fix_success = self.auto_fix_specific_issues(check_result["issues"])

                if not fix_success:
                    response = input("\n⚠️  Some issues remain. Continue anyway? (y/n): ")
                    if response.lower() != "y":
                        self.log("Sync aborted", "WARNING")
                        return False

        # Stage all changes (if not already staged)
        self.log("\nStaging all changes...", "PROCESS")
        success, output = self.run_git_command(["add", "-A"])

        if not success:
            self.log(f"Failed to stage changes: {output}", "ERROR")
            return False

        # Generate commit message
        if custom_message:
            commit_message = custom_message
        else:
            analysis = self.analyze_changes(status)
            commit_message = self.generate_commit_message_with_fixes(analysis)

        if self.verbose:
            print("\nGenerated commit message:")
            print("-" * 30)
            print(commit_message)
            print("-" * 30)

        # Commit changes
        self.log("\nCommitting changes...", "PROCESS")
        success, output = self.run_git_command(["commit", "-m", commit_message])

        if not success:
            if "nothing to commit" in output:
                self.log("No changes to commit after fixes", "INFO")
                return True
            else:
                self.log(f"Failed to commit: {output}", "ERROR")
                return False

        self.log("Changes committed successfully", "SUCCESS")

        # Push changes if requested
        if push:
            self.log("\nPushing to remote...", "PROCESS")
            success, output = self.run_git_command(["push", "origin", "main"])

            if not success:
                # Try to push to current branch
                branch_success, current_branch = self.run_git_command(["branch", "--show-current"])
                if branch_success and current_branch:
                    success, output = self.run_git_command(["push", "origin", current_branch])

                if not success:
                    self.log(f"Failed to push: {output}", "ERROR")
                    return False

            self.log("Changes pushed successfully", "SUCCESS")

        print("\n✅ Git sync completed successfully!")

        # Show summary
        if self.fixes_applied:
            print("\n📊 Fix Summary:")
            print(f"- Automated fixes applied: {len(self.fixes_applied)}")
            print(f"- Files fixed: {self.stats['files_fixed']}")
            print(f"- Error types resolved: {self.stats['errors_fixed']}")

        return True

    def auto_fix_specific_issues(self, issues: Dict[str, List[str]]) -> bool:
        """Fix specific issues identified by pre-commit"""
        any_fixed = False

        # Fix trailing whitespace
        if issues.get("trailing-whitespace"):
            self.log("Fixing trailing whitespace...", "FIX")
            self.fix_trailing_whitespace()
            any_fixed = True

        # Fix end of file
        if issues.get("end-of-file-fixer"):
            self.log("Fixing end of file issues...", "FIX")
            self.fix_end_of_file()
            any_fixed = True

        # Fix debug statements
        if issues.get("debug-statements"):
            self.log("Removing debug statements...", "FIX")
            self.remove_debug_statements()
            any_fixed = True

        # Apply other fixes as in original
        if issues.get("black"):
            any_fixed = self.fix_black_issues() or any_fixed

        if issues.get("isort"):
            any_fixed = self.fix_isort_issues() or any_fixed

        if issues.get("flake8"):
            any_fixed = self.fix_flake8_issues() or any_fixed

        return any_fixed

    def fix_trailing_whitespace(self):
        """Fix trailing whitespace in all files"""
        for ext in ["*.py", "*.html", "*.js", "*.css", "*.md", "*.txt", "*.yml", "*.yaml"]:
            files = list(self.project_root.rglob(ext))
            for file in files:
                if any(
                    skip in str(file)
                    for skip in [".venv", "venv", "migrations", "static", "node_modules"]
                ):
                    continue
                try:
                    content = file.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    fixed_lines = [line.rstrip() for line in lines]
                    if lines != fixed_lines:
                        file.write_text("\n".join(fixed_lines), encoding="utf-8")
                        self.stats["files_fixed"] += 1
                except Exception as e:
                    self.log(f"Error fixing {file}: {e}", "ERROR")

    def fix_end_of_file(self):
        """Ensure files end with newline"""
        for ext in ["*.py", "*.html", "*.js", "*.css", "*.md", "*.txt", "*.yml", "*.yaml"]:
            files = list(self.project_root.rglob(ext))
            for file in files:
                if any(
                    skip in str(file)
                    for skip in [".venv", "venv", "migrations", "static", "node_modules"]
                ):
                    continue
                try:
                    content = file.read_text(encoding="utf-8")
                    if content and not content.endswith("\n"):
                        file.write_text(content + "\n", encoding="utf-8")
                        self.stats["files_fixed"] += 1
                except Exception as e:
                    self.log(f"Error fixing {file}: {e}", "ERROR")

    def remove_debug_statements(self):
        """Remove common debug statements from Python files"""
        debug_patterns = [
            r"^\s*print\s*\(",
            r"^\s*import\s+pdb",
            r"^\s*pdb\.set_trace\(",
            r"^\s*breakpoint\(",
            r"^\s*import\s+ipdb",
            r"^\s*ipdb\.set_trace\(",
        ]

        python_files = list(self.project_root.rglob("*.py"))
        for py_file in python_files:
            if any(skip in str(py_file) for skip in [".venv", "venv", "migrations"]):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                filtered_lines = []
                removed = False

                for line in lines:
                    should_remove = any(re.match(pattern, line) for pattern in debug_patterns)
                    if not should_remove:
                        filtered_lines.append(line)
                    else:
                        removed = True

                if removed:
                    py_file.write_text("\n".join(filtered_lines), encoding="utf-8")
                    self.stats["files_fixed"] += 1
                    self.fixes_applied.append(f"Removed debug statements from {py_file.name}")
            except Exception as e:
                self.log(f"Error processing {py_file}: {e}", "ERROR")

    # Include all other methods from the original class here...
    # (get_git_status, analyze_changes, generate_commit_message_with_fixes, etc.)
    # I'm keeping this focused on the key improvements


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BF Agent Git Sync Tool with Auto-Fix V3 - Improved conflict handling"
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="sync",
        choices=["sync", "fix", "check", "quick"],
        help="Command to run (default: sync)",
    )

    parser.add_argument("--message", "-m", help="Custom commit message")
    parser.add_argument("--no-push", action="store_true", help="Don't push changes to remote")
    parser.add_argument("--no-fix", action="store_true", help="Skip automatic error fixing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")

    args = parser.parse_args()

    sync_tool = GitSyncAutoFix(verbose=args.verbose, auto_fix=not args.no_fix)

    try:
        if args.command == "sync":
            # Use the improved sync method
            success = sync_tool.sync_all_v2(custom_message=args.message, push=not args.no_push)
        elif args.command == "fix":
            success = sync_tool.auto_fix_all()
        elif args.command == "check":
            success, result = sync_tool.check_and_fix_pre_commit_v2()
            if success:
                print("✅ All pre-commit checks pass!")
            else:
                print("❌ Pre-commit issues found:")
                for hook, issues in result["issues"].items():
                    if issues:
                        print(f"\n{hook}: {len(issues)} issues")
        elif args.command == "quick":
            success = sync_tool.sync_all_v2(
                custom_message=args.message
                or f"🔄 Quick sync - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                push=not args.no_push,
            )

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n✋ Git sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
