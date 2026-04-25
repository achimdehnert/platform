#!/usr/bin/env python3
"""
docu_update_agent.py — Docu-Update für docu-update GitHub Issues.

Stufe 1 (deterministisch, kein LLM):
- README.md Version aus pyproject.toml synchronisieren
- CHANGELOG.md Eintrag aus git log generieren

Stufe 2 (--llm, gpt-4o-mini):
- LLM-generierte CHANGELOG-Zusammenfassungen statt roher Commit-Messages
- README.md Version-Injection wenn keine Version im Header
- Bessere Commit-Messages

Verwendung:
    python .github/scripts/docu_update_agent.py \\
        --issue-number 46 \\
        --llm              # optional: LLM-enhanced (Stufe 2)
        --dry-run          # optional: kein push/close
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"
ORG = "achimdehnert"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _gh_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_get_issue(repo: str, issue_number: int, token: str) -> dict:
    url = f"{GITHUB_API}/repos/{ORG}/{repo}/issues/{issue_number}"
    resp = httpx.get(url, headers=_gh_headers(token), timeout=15)
    resp.raise_for_status()
    return resp.json()


def gh_close_issue(repo: str, issue_number: int, token: str) -> None:
    url = f"{GITHUB_API}/repos/{ORG}/{repo}/issues/{issue_number}"
    httpx.patch(url, headers=_gh_headers(token), json={"state": "closed"}, timeout=15).raise_for_status()


def gh_comment(repo: str, issue_number: int, body: str, token: str) -> None:
    url = f"{GITHUB_API}/repos/{ORG}/{repo}/issues/{issue_number}/comments"
    httpx.post(url, headers=_gh_headers(token), json={"body": body}, timeout=15).raise_for_status()


# ---------------------------------------------------------------------------
# Issue Parsing
# ---------------------------------------------------------------------------

def parse_issue(title: str, body: str) -> tuple[str | None, str | None]:
    """Return (repo_name, target_version) from issue title + body."""

    # Repo name from title: "[docu-update] travel-beat — ..."
    repo_name = None
    m = re.search(r"\[docu-update\]\s+([a-zA-Z0-9_-]+)", title)
    if m:
        repo_name = m.group(1)

    # Fallback: body header "## docu-update: travel-beat"
    if not repo_name:
        m = re.search(r"##\s*docu-update:\s*([a-zA-Z0-9_-]+)", body)
        if m:
            repo_name = m.group(1)

    # Version: v_code=0.4.1
    version = None
    m = re.search(r"v_code[=:]\s*([0-9]+\.[0-9]+\.[0-9]+)", body)
    if m:
        version = m.group(1)

    # Fallback: "README.md Version = `0.4.1`"
    if not version:
        m = re.search(r"Version\s*=\s*`([0-9]+\.[0-9]+\.[0-9]+)`", body)
        if m:
            version = m.group(1)

    # Fallback: "Version:** 0.4.1"
    if not version:
        m = re.search(r"Version.*?([0-9]+\.[0-9]+\.[0-9]+)", body)
        if m:
            version = m.group(1)

    return repo_name, version


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def get_version_from_pyproject(repo_path: Path) -> str | None:
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        return None
    content = pyproject.read_text()
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    return m.group(1) if m else None


def update_readme_version(repo_path: Path, new_version: str) -> bool:
    readme = repo_path / "README.md"
    if not readme.exists():
        return False

    content = readme.read_text()
    original = content

    # Replace version badge / inline: v1.2.3 or 1.2.3 (first occurrence)
    # Pattern 1: v1.2.3
    content, n1 = re.subn(
        r"\bv([0-9]+\.[0-9]+\.[0-9]+)\b",
        f"v{new_version}",
        content,
        count=1,
    )
    # Pattern 2: standalone "1.2.3" in Version: or **Version** lines
    if n1 == 0:
        content, _ = re.subn(
            r"((?:Version|version)\s*[:\|]\s*)([0-9]+\.[0-9]+\.[0-9]+)",
            lambda m: m.group(1) + new_version,
            content,
            count=1,
        )

    if content != original:
        readme.write_text(content)
        return True
    return False


def _get_commit_lines(repo_path: Path, count: int = 20) -> list[str]:
    """Get recent commit messages, excluding auto-commits."""
    result = subprocess.run(
        ["git", "log", "--oneline", f"-{count}", "--no-merges",
         "--invert-grep", "--grep=session-ende", "--grep=auto-sync",
         "--grep=docu-update-agent"],
        cwd=repo_path, capture_output=True, text=True,
    )
    return [
        re.sub(r"^[a-f0-9]{7,}\s+", "", line.strip())
        for line in result.stdout.strip().splitlines()
        if line.strip()
    ][:15]


def _llm_summarize_changelog(repo_name: str, version: str, commits: list[str]) -> str | None:
    """Use gpt-4o-mini to generate a structured CHANGELOG entry."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    commit_text = "\n".join(f"- {c}" for c in commits)
    prompt = (
        f"Generate a CHANGELOG entry for version {version} of the project '{repo_name}'.\n"
        f"Use Keep a Changelog format with sections: Added, Changed, Fixed (only include non-empty sections).\n"
        f"Be concise. Group related commits. Write in English.\n"
        f"Do NOT include the version header — only the bullet points grouped by section.\n\n"
        f"Raw commits:\n{commit_text}"
    )

    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"  LLM call failed: {exc} — falling back to raw commits")
        return None


def update_changelog(repo_path: Path, version: str, *, use_llm: bool = False, repo_name: str = "") -> bool:
    changelog = repo_path / "CHANGELOG.md"
    log_lines = _get_commit_lines(repo_path)

    if not log_lines:
        return False

    today = date.today().isoformat()

    # Stufe 2: LLM-enhanced changelog
    llm_content = None
    if use_llm:
        llm_content = _llm_summarize_changelog(repo_name or repo_path.name, version, log_lines)

    if llm_content:
        new_entry = f"## [{version}] — {today}\n\n{llm_content}\n\n"
    else:
        new_entry = f"## [{version}] — {today}\n\n"
        for line in log_lines[:10]:
            new_entry += f"- {line}\n"
        new_entry += "\n"

    if changelog.exists():
        existing = changelog.read_text()
        if f"[{version}]" in existing:
            return False  # entry already present
        # Prepend after top-level header
        if re.match(r"^#\s", existing):
            first_newline = existing.index("\n")
            content = existing[: first_newline + 1] + "\n" + new_entry + existing[first_newline + 1 :]
        else:
            content = new_entry + existing
    else:
        content = f"# CHANGELOG\n\n{new_entry}"

    changelog.write_text(content)
    return True


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_update(
    repo_name: str,
    issue_version: str | None,
    token: str,
    dry_run: bool,
    issue_number: int,
    platform_repo: str,
    use_llm: bool = False,
) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_url = f"https://x-access-token:{token}@github.com/{ORG}/{repo_name}.git"

        clone = subprocess.run(
            ["git", "clone", "--depth=50", repo_url, repo_name],
            cwd=tmpdir, capture_output=True, text=True,
        )
        if clone.returncode != 0:
            return {"success": False, "error": f"Clone failed: {clone.stderr[:300]}"}

        repo_path = Path(tmpdir) / repo_name

        # Authoritative version: pyproject.toml > issue_version
        version = get_version_from_pyproject(repo_path) or issue_version
        if not version:
            return {"success": False, "error": "Cannot determine version — no pyproject.toml and no version in issue"}

        subprocess.run(["git", "config", "user.email", "cascade-agent@iil.pet"], cwd=repo_path)
        subprocess.run(["git", "config", "user.name", "Cascade Agent [docu-update]"], cwd=repo_path)

        readme_changed = update_readme_version(repo_path, version)
        changelog_changed = update_changelog(repo_path, version, use_llm=use_llm, repo_name=repo_name)

        changes = []
        if readme_changed:
            changes.append(f"README.md → v{version}")
        if changelog_changed:
            changes.append(f"CHANGELOG.md → [{version}]")

        if not changes:
            return {"success": True, "version": version, "changes": [], "skipped": True}

        if dry_run:
            return {"success": True, "version": version, "changes": changes, "dry_run": True}

        subprocess.run(
            ["git", "add", "README.md", "CHANGELOG.md"],
            cwd=repo_path, capture_output=True,
        )
        stufe = "Stufe 2, gpt-4o-mini" if use_llm else "Stufe 1, no-LLM"
        commit_msg = (
            f"docs({repo_name}): sync README + CHANGELOG to v{version}\n\n"
            f"Automated via docu-update-agent ({stufe})\n"
            f"Triggered by: {ORG}/platform#{issue_number}"
        )
        commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path, capture_output=True, text=True,
        )
        if commit.returncode != 0:
            return {"success": False, "error": f"Commit failed: {commit.stderr[:200]}"}

        # Try main, then master
        pushed = False
        for branch in ("main", "master"):
            push = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=repo_path, capture_output=True, text=True,
            )
            if push.returncode == 0:
                pushed = True
                break

        if not pushed:
            return {"success": False, "error": "Push failed on both main and master"}

        return {"success": True, "version": version, "changes": changes}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Docu-Update Agent — Stufe 1+2")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--llm", action="store_true", default=False,
                        help="Stufe 2: Use gpt-4o-mini for CHANGELOG generation")
    args = parser.parse_args()

    token = os.environ.get("PROJECT_PAT") or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: PROJECT_PAT or GITHUB_TOKEN not set", file=sys.stderr)
        return 1

    platform_repo = os.environ.get("GITHUB_REPOSITORY", f"{ORG}/platform").split("/")[-1]

    # Fetch issue from GitHub API (avoids multiline env-var quoting issues)
    print(f"Fetching issue #{args.issue_number} from {ORG}/{platform_repo}...")
    issue = gh_get_issue(platform_repo, args.issue_number, token)
    title = issue.get("title", "")
    body = issue.get("body", "") or ""

    # Safety gate: only process issues with docu-update label
    labels = [lbl["name"] for lbl in issue.get("labels", [])]
    if "docu-update" not in labels:
        print(f"SKIP: Issue #{args.issue_number} hat kein 'docu-update' Label (Labels: {labels})")
        return 0

    repo_name, issue_version = parse_issue(title, body)
    if not repo_name:
        print(f"ERROR: Cannot parse repo_name from issue title: {title!r}", file=sys.stderr)
        return 1

    use_llm = args.llm and bool(os.environ.get("OPENAI_API_KEY"))
    print(f"  Repo    : {repo_name}")
    print(f"  Version : {issue_version or '(from pyproject.toml)'}")
    print(f"  Stufe   : {'2 (LLM)' if use_llm else '1 (deterministisch)'}")
    print(f"  Dry-run : {args.dry_run}")

    result = run_update(
        repo_name=repo_name,
        issue_version=issue_version,
        token=token,
        dry_run=args.dry_run,
        issue_number=args.issue_number,
        platform_repo=platform_repo,
        use_llm=use_llm,
    )

    if not result["success"]:
        error_msg = result.get("error", "unknown error")
        print(f"FAILED: {error_msg}", file=sys.stderr)
        gh_comment(
            platform_repo, args.issue_number,
            f"❌ docu-update-agent fehlgeschlagen\n\n```\n{error_msg}\n```\n\nManuelle Bearbeitung erforderlich.",
            token,
        )
        return 1

    if result.get("skipped"):
        print(f"SKIP: {repo_name} — nichts zu aktualisieren (bereits auf v{result['version']})")
        gh_comment(
            platform_repo, args.issue_number,
            f"ℹ️ Kein Update nötig — `{repo_name}` README + CHANGELOG bereits auf v{result['version']}.",
            token,
        )
        gh_close_issue(platform_repo, args.issue_number, token)
        return 0

    changes_str = "\n".join(f"- {c}" for c in result["changes"])
    dry_note = " *(dry-run — kein Push)*" if result.get("dry_run") else ""

    print(f"SUCCESS{dry_note}: {repo_name} v{result['version']}")
    for c in result["changes"]:
        print(f"  ✅ {c}")

    if not args.dry_run:
        gh_comment(
            platform_repo, args.issue_number,
            f"✅ docu-update-agent erledigt{dry_note}\n\n"
            f"**Repo:** `{repo_name}` | **Version:** `{result['version']}`\n\n"
            f"**Änderungen:**\n{changes_str}\n\n"
            f"Modell: `{'stufe-2 (gpt-4o-mini)' if use_llm else 'stufe-1 (deterministisch)'}`",
            token,
        )
        gh_close_issue(platform_repo, args.issue_number, token)
        print(f"  Issue #{args.issue_number} geschlossen.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
