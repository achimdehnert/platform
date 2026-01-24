#!/usr/bin/env python3
"""
🚀 BF Agent One-Click Deployment

Führt das komplette Deployment automatisch durch:
1. Lokale Validierung
2. Git commit & push
3. Warten auf GitHub Actions
4. Deploy auf Hetzner
5. Migrations ausführen
6. Health Check

Usage:
    python scripts/deploy.py
    python scripts/deploy.py --skip-docker    # Schneller, ohne Docker-Test
    python scripts/deploy.py --dry-run        # Nur prüfen, nichts deployen
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Configuration
HETZNER_HOST = "root@bfagent.iil.pet"
HETZNER_APP_DIR = "/opt/bfagent-app"
HEALTH_CHECK_URL = "https://bfagent.iil.pet/login/"
GITHUB_ACTIONS_URL = "https://github.com/achimdehnert/bfagent/actions"

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_step(step: int, total: int, msg: str):
    """Print step header."""
    print(f"\n{BLUE}{BOLD}[{step}/{total}] {msg}{RESET}")
    print("=" * 60)


def print_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠️ {msg}{RESET}")


def run_cmd(cmd: list[str], cwd: Path = None, check: bool = True) -> tuple[int, str]:
    """Run command and return exit code + output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if check and result.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}\n{output}")
    return result.returncode, output


def run_ssh(command: str) -> tuple[int, str]:
    """Run command on Hetzner via SSH."""
    return run_cmd(["ssh", HETZNER_HOST, command], check=False)


def step_validate_local(project_root: Path, skip_docker: bool) -> bool:
    """Step 1: Local validation."""
    
    # Check for untracked Python files
    print("Checking for untracked Python files...")
    py_files = list(project_root.glob("apps/**/*.py"))
    untracked = []
    
    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue
        rel_path = py_file.relative_to(project_root)
        code, _ = run_cmd(["git", "ls-files", "--error-unmatch", str(rel_path)], 
                          cwd=project_root, check=False)
        if code != 0:
            untracked.append(rel_path)
    
    if untracked:
        print_error(f"Untracked Python files found:")
        for f in untracked[:5]:
            print(f"   - {f}")
        print(f"\nFix with: git add -f <file>")
        return False
    print_success("All Python files tracked")
    
    # Django check
    print("\nRunning Django check...")
    code, output = run_cmd([sys.executable, "manage.py", "check"], 
                           cwd=project_root, check=False)
    if code != 0:
        print_error("Django check failed")
        for line in output.split("\n"):
            if "Error" in line:
                print(f"   {line}")
        return False
    print_success("Django check passed")
    
    # Docker test (optional)
    if not skip_docker:
        print("\nBuilding Docker image...")
        code, _ = run_cmd(["docker", "build", "-t", "bfagent-web:deploy-test", "."],
                          cwd=project_root, check=False)
        if code != 0:
            print_error("Docker build failed")
            return False
        print_success("Docker build successful")
        
        print("\nTesting Django in container...")
        code, output = run_cmd([
            "docker", "run", "--rm",
            "-e", "DJANGO_SETTINGS_MODULE=config.settings.production",
            "-e", "SECRET_KEY=deploy-test-key",
            "-e", "DEBUG=False",
            "bfagent-web:deploy-test",
            "python", "manage.py", "check"
        ], cwd=project_root, check=False)
        if code != 0:
            print_error("Django check in container failed")
            for line in output.split("\n"):
                if "ModuleNotFoundError" in line or "Error" in line:
                    print(f"   {line}")
            return False
        print_success("Docker container test passed")
    
    return True


def step_git_push(project_root: Path) -> str:
    """Step 2: Commit and push changes."""
    
    # Check if there are changes
    code, output = run_cmd(["git", "status", "--porcelain"], cwd=project_root)
    
    if output.strip():
        print("Uncommitted changes found, committing...")
        run_cmd(["git", "add", "-A"], cwd=project_root)
        run_cmd(["git", "commit", "-m", "Deployment commit"], cwd=project_root)
        print_success("Changes committed")
    else:
        print_success("No uncommitted changes")
    
    # Push
    print("\nPushing to origin/main...")
    run_cmd(["git", "push", "origin", "main"], cwd=project_root)
    print_success("Pushed to GitHub")
    
    # Get commit SHA
    _, sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=project_root)
    return sha.strip()


def step_wait_github_actions(timeout_minutes: int = 5) -> bool:
    """Step 3: Wait for GitHub Actions to complete."""
    
    print(f"Waiting for GitHub Actions build...")
    print(f"   Monitor: {GITHUB_ACTIONS_URL}")
    print(f"   Timeout: {timeout_minutes} minutes")
    
    # Simple wait - GitHub Actions typically takes 2-3 minutes
    wait_seconds = 120  # 2 minutes initial wait
    
    for i in range(wait_seconds):
        remaining = wait_seconds - i
        print(f"\r   Waiting... {remaining}s remaining", end="", flush=True)
        time.sleep(1)
    
    print()
    print_success(f"Waited {wait_seconds}s for GitHub Actions")
    print_warning("Verify build is complete: " + GITHUB_ACTIONS_URL)
    
    # Ask user to confirm
    response = input(f"\n{YELLOW}Is the GitHub Actions build complete? [Y/n]: {RESET}")
    if response.lower() == 'n':
        print_error("Deployment aborted - GitHub Actions not complete")
        return False
    
    return True


def step_deploy_hetzner(commit_sha: str) -> bool:
    """Step 4: Deploy to Hetzner."""
    
    print("Connecting to Hetzner...")
    
    # Update .env.prod with latest tag
    commands = [
        f"cd {HETZNER_APP_DIR}",
        "sed -i 's/BFAgent_IMAGE_TAG=.*/BFAgent_IMAGE_TAG=latest/' .env.prod",
        "docker compose -f docker-compose.prod.yml --env-file .env.prod pull bfagent-web",
        "docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate bfagent-web",
    ]
    
    full_cmd = " && ".join(commands)
    code, output = run_ssh(full_cmd)
    
    if code != 0:
        print_error("Deploy failed")
        print(output)
        return False
    
    print_success("Container deployed")
    
    # Wait for container to start
    print("\nWaiting for container to start (30s)...")
    time.sleep(30)
    
    return True


def step_run_migrations() -> bool:
    """Step 5: Run migrations on Hetzner."""
    
    print("Running migrations...")
    
    cmd = f"cd {HETZNER_APP_DIR} && docker compose -f docker-compose.prod.yml exec -T bfagent-web python manage.py migrate"
    code, output = run_ssh(cmd)
    
    if code != 0:
        print_error("Migrations failed")
        print(output)
        return False
    
    if "No migrations to apply" in output:
        print_success("No migrations needed")
    else:
        print_success("Migrations applied")
    
    return True


def step_health_check() -> bool:
    """Step 6: Verify deployment."""
    
    print(f"Checking {HEALTH_CHECK_URL}...")
    
    cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {HEALTH_CHECK_URL}"
    code, output = run_ssh(cmd)
    
    status_code = output.strip().replace("'", "")
    
    if status_code == "200":
        print_success(f"Health check passed (HTTP {status_code})")
        return True
    else:
        print_error(f"Health check failed (HTTP {status_code})")
        return False


def main():
    parser = argparse.ArgumentParser(description="🚀 BF Agent One-Click Deployment")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker build test")
    parser.add_argument("--dry-run", action="store_true", help="Only validate, don't deploy")
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    
    print(f"\n{BOLD}🚀 BF Agent One-Click Deployment{RESET}")
    print("=" * 60)
    
    total_steps = 3 if args.dry_run else 6
    
    # Step 1: Local Validation
    print_step(1, total_steps, "Local Validation")
    if not step_validate_local(project_root, args.skip_docker):
        print_error("\nDeployment aborted - validation failed")
        return 1
    
    # Step 2: Git Push
    print_step(2, total_steps, "Git Push")
    try:
        commit_sha = step_git_push(project_root)
        print(f"   Commit: {commit_sha[:8]}")
    except Exception as e:
        print_error(f"Git push failed: {e}")
        return 1
    
    if args.dry_run:
        print_step(3, total_steps, "Dry Run Complete")
        print_success("Validation passed - ready for deployment")
        print(f"\nTo deploy, run: python scripts/deploy.py")
        return 0
    
    # Step 3: Wait for GitHub Actions
    print_step(3, total_steps, "Wait for GitHub Actions")
    if not step_wait_github_actions():
        return 1
    
    # Step 4: Deploy to Hetzner
    print_step(4, total_steps, "Deploy to Hetzner")
    if not step_deploy_hetzner(commit_sha):
        print_error("\nDeployment failed - check Hetzner logs")
        return 1
    
    # Step 5: Run Migrations
    print_step(5, total_steps, "Run Migrations")
    if not step_run_migrations():
        print_warning("Migrations failed - check manually")
    
    # Step 6: Health Check
    print_step(6, total_steps, "Health Check")
    if not step_health_check():
        print_error("\nDeployment may have failed - check Hetzner")
        return 1
    
    print("\n" + "=" * 60)
    print(f"{GREEN}{BOLD}🎉 DEPLOYMENT SUCCESSFUL!{RESET}")
    print("=" * 60)
    print(f"\n   URL: {HEALTH_CHECK_URL}")
    print(f"   Commit: {commit_sha[:8]}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
