#!/usr/bin/env python3
"""
Pre-Deployment Validation Script

Run this script BEFORE pushing to main to catch deployment issues early.

Usage:
    python scripts/validate_deployment.py
    
    # With Docker test (slower but more thorough)
    python scripts/validate_deployment.py --docker
"""

import subprocess
import sys
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run_cmd(cmd: list[str], cwd: Path = None) -> tuple[int, str]:
    """Run command and return exit code + output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def check_git_status(project_root: Path) -> bool:
    """Check for untracked Python files in apps/."""
    print("\n📂 Checking for untracked Python files in apps/...")
    
    # Find all .py files in apps/
    py_files = list(project_root.glob("apps/**/*.py"))
    untracked = []
    
    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue
        rel_path = py_file.relative_to(project_root)
        code, output = run_cmd(["git", "ls-files", "--error-unmatch", str(rel_path)], cwd=project_root)
        if code != 0:
            untracked.append(rel_path)
    
    if untracked:
        print(f"{RED}❌ Untracked Python files found:{RESET}")
        for f in untracked[:10]:
            print(f"   - {f}")
        if len(untracked) > 10:
            print(f"   ... and {len(untracked) - 10} more")
        print(f"\n   Fix: git add -f <file>")
        return False
    
    print(f"{GREEN}✅ All Python files are tracked{RESET}")
    return True


def check_requirements(project_root: Path) -> bool:
    """Check that all imports can be resolved."""
    print("\n📦 Checking requirements.txt...")
    
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        print(f"{RED}❌ requirements.txt not found{RESET}")
        return False
    
    print(f"{GREEN}✅ requirements.txt exists{RESET}")
    return True


def check_django(project_root: Path) -> bool:
    """Run Django system check."""
    print("\n🔍 Running Django check...")
    
    code, output = run_cmd(
        [sys.executable, "manage.py", "check"],
        cwd=project_root
    )
    
    if code != 0:
        print(f"{RED}❌ Django check failed:{RESET}")
        # Show only error lines
        for line in output.split("\n"):
            if "Error" in line or "error" in line.lower():
                print(f"   {line}")
        return False
    
    print(f"{GREEN}✅ Django check passed{RESET}")
    return True


def check_migrations(project_root: Path) -> bool:
    """Check for uncommitted migration files."""
    print("\n🗄️ Checking migrations...")
    
    # Find all migration files
    migration_files = list(project_root.glob("apps/*/migrations/*.py"))
    untracked = []
    
    for mig_file in migration_files:
        if "__pycache__" in str(mig_file):
            continue
        rel_path = mig_file.relative_to(project_root)
        code, _ = run_cmd(["git", "ls-files", "--error-unmatch", str(rel_path)], cwd=project_root)
        if code != 0:
            untracked.append(rel_path)
    
    if untracked:
        print(f"{YELLOW}⚠️ Untracked migration files:{RESET}")
        for f in untracked:
            print(f"   - {f}")
        print(f"\n   Fix: git add {' '.join(str(f) for f in untracked)}")
        return False
    
    print(f"{GREEN}✅ All migrations are tracked{RESET}")
    return True


def check_docker_build(project_root: Path) -> bool:
    """Build Docker image and test Django check inside container."""
    print("\n🐳 Building Docker image...")
    
    code, output = run_cmd(
        ["docker", "build", "-t", "bfagent-web:validate", "."],
        cwd=project_root
    )
    
    if code != 0:
        print(f"{RED}❌ Docker build failed{RESET}")
        # Show last 10 lines
        lines = output.strip().split("\n")
        for line in lines[-10:]:
            print(f"   {line}")
        return False
    
    print(f"{GREEN}✅ Docker build successful{RESET}")
    
    print("\n🔍 Running Django check in container...")
    code, output = run_cmd([
        "docker", "run", "--rm",
        "-e", "DJANGO_SETTINGS_MODULE=config.settings.production",
        "-e", "SECRET_KEY=validation-test-key",
        "-e", "POSTGRES_HOST=localhost",
        "-e", "DEBUG=False",
        "bfagent-web:validate",
        "python", "manage.py", "check"
    ], cwd=project_root)
    
    if code != 0:
        print(f"{RED}❌ Django check in container failed:{RESET}")
        for line in output.split("\n"):
            if "Error" in line or "ModuleNotFoundError" in line:
                print(f"   {line}")
        return False
    
    print(f"{GREEN}✅ Django check in container passed{RESET}")
    return True


def main():
    project_root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("🚀 BF Agent Pre-Deployment Validation")
    print("=" * 60)
    
    use_docker = "--docker" in sys.argv
    
    checks = [
        ("Git Status", lambda: check_git_status(project_root)),
        ("Requirements", lambda: check_requirements(project_root)),
        ("Django Check", lambda: check_django(project_root)),
        ("Migrations", lambda: check_migrations(project_root)),
    ]
    
    if use_docker:
        checks.append(("Docker Build & Test", lambda: check_docker_build(project_root)))
    
    results = []
    for name, check_fn in checks:
        try:
            passed = check_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"{RED}❌ {name} failed with exception: {e}{RESET}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print(f"{GREEN}🎉 All checks passed! Safe to deploy.{RESET}")
        return 0
    else:
        print(f"{RED}⚠️ Some checks failed. Fix issues before deploying.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
