#!/usr/bin/env python3
"""gen_make_test_pg.py — patch a repo's Makefile so `make test` is self-contained.

Problem (verified 2026-06-01): 28/38 repo Makefiles have a bare `test: pytest -v`
target. For Django+Postgres repos that target FAILS — config/settings/test.py needs
a live Postgres + POSTGRES_* env and a SECRET_KEY guard. Hand-reconstructing that
env is error-prone (cost 6 failed runs in one session).

This generator injects an ephemeral-Postgres `test-pg` target (spin up pg16, export
the exact env test.py reads, run pytest, tear down via trap) — but ONLY for repos
that actually need Postgres. Pure packages keep bare pytest (correct for them).

SAFETY (per AD-5 of the self-improvement concept — bulk ops are the 🌀 risk):
  - DRY-RUN IS THE DEFAULT. --write is required to touch files.
  - Idempotent: skips a Makefile that already has a `test-pg` target.
  - Profile-aware: only patches profile == 'django-pg'. Never touches packages.
  - One repo at a time; intended to feed a per-repo PR, never a bulk direct push.

Usage:
    python3 scripts/gen_make_test_pg.py <repo>            # dry-run (default)
    python3 scripts/gen_make_test_pg.py <repo> --write    # actually patch
    python3 scripts/gen_make_test_pg.py --all             # classify all repos (dry)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

GITHUB_DIR = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))

# The injected target. Mirrors dev-hub's verified version (PR #68).
TEST_PG_BLOCK = """\
# --- injected by gen_make_test_pg.py: self-contained `make test` (PG + env) ---
# config/settings/test.py needs live Postgres + POSTGRES_* env + SECRET_KEY guard.
# Reconstructing that by hand is error-prone — use `make test`, never raw pytest.
TEST_PG_NAME := $(notdir $(CURDIR))-make-test-pg
TEST_PG_PORT := 5432
test: test-pg
test-pg:
	@docker rm -f $(TEST_PG_NAME) >/dev/null 2>&1 || true
	@docker run -d --rm --name $(TEST_PG_NAME) \\
		-e POSTGRES_USER=test_user -e POSTGRES_PASSWORD=test_pass -e POSTGRES_DB=test_db \\
		-p $(TEST_PG_PORT):5432 postgres:16-alpine >/dev/null
	@for i in $$(seq 1 30); do \\
		docker exec $(TEST_PG_NAME) pg_isready -U test_user >/dev/null 2>&1 && break; sleep 1; \\
	done
	@set -e; trap 'docker stop $(TEST_PG_NAME) >/dev/null 2>&1 || true' EXIT; \\
		DJANGO_SETTINGS_MODULE=config.settings.test \\
		SECRET_KEY="make-test-key-not-insecure-0123456789abcdef" \\
		POSTGRES_USER=test_user POSTGRES_PASSWORD=test_pass POSTGRES_DB=test_db \\
		POSTGRES_HOST=localhost POSTGRES_PORT=$(TEST_PG_PORT) \\
		$(VENV_BIN)/pytest $(if $(K),-k "$(K)",) $(if $(ARGS),$(ARGS),-q)
# --- end injected block ---
"""


def classify(repo: Path) -> str:
    """django-pg | django-other | package | no-test-target."""
    mk = repo / "Makefile"
    if not mk.exists():
        return "no-makefile"
    text = mk.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"^test:", text, re.M):
        return "no-test-target"
    # already self-contained?
    if re.search(r"^test-pg:", text, re.M) or "POSTGRES_" in text:
        return "already-patched"
    settings_test = repo / "config" / "settings" / "test.py"
    if settings_test.exists() and "postgresql" in settings_test.read_text(
        encoding="utf-8", errors="replace"
    ).lower():
        return "django-pg"
    if list(repo.glob("**/settings.py")):
        return "django-other"
    return "package"


def needs_venv_bin(text: str) -> bool:
    """The block references $(VENV_BIN); ensure the Makefile defines it."""
    return "VENV_BIN" not in text


def patch(repo: Path, write: bool) -> str:
    mk = repo / "Makefile"
    text = mk.read_text(encoding="utf-8", errors="replace")

    # Replace the existing bare `test:` recipe with our block.
    # Match `test:` and its indented recipe lines.
    pat = re.compile(r"^test:.*?(?=\n[^\t\n]|\Z)", re.S | re.M)
    if not pat.search(text):
        return "no-test-target-found"

    new_text = pat.sub(TEST_PG_BLOCK.rstrip(), text, count=1)
    if needs_venv_bin(new_text):
        # prepend a VENV_BIN default near the top (after first line)
        new_text = new_text.replace(
            "\n", "\nVENV_BIN ?= .venv/bin\n", 1
        )
    if not write:
        return "DRY-RUN: would patch (use --write)"
    mk.write_text(new_text, encoding="utf-8")
    return "PATCHED"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", help="repo name under $GITHUB_DIR")
    ap.add_argument("--all", action="store_true", help="classify all repos (dry)")
    ap.add_argument("--write", action="store_true", help="actually patch (default: dry-run)")
    args = ap.parse_args()

    if args.all:
        rows = []
        for d in sorted(GITHUB_DIR.iterdir()):
            if not d.is_dir() or "." in d.name:
                continue
            rows.append((d.name, classify(d)))
        targets = [n for n, p in rows if p == "django-pg"]
        for n, p in rows:
            if p in ("django-pg", "already-patched"):
                print(f"  {n:22} {p}")
        print(f"\n→ {len(targets)} repos need the patch: {', '.join(targets)}")
        print("Run per-repo: gen_make_test_pg.py <repo> --write  → then open a PR.")
        return 0

    if not args.repo:
        ap.error("repo required (or --all)")
    repo = GITHUB_DIR / args.repo
    prof = classify(repo)
    print(f"{args.repo}: profile={prof}")
    if prof != "django-pg":
        print(f"  SKIP — only 'django-pg' gets the PG target (got '{prof}').")
        return 0
    print("  " + patch(repo, args.write))
    return 0


if __name__ == "__main__":
    sys.exit(main())
