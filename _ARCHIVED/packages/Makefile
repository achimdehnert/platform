# platform/packages — Top-level Makefile
# Runs tests for all packages that have a tests/ directory.

.PHONY: test-all clean-all help

PYTHON := python3

help:
	@echo "Targets:"
	@echo "  test-all   — run pytest for every package with tests/"
	@echo "  clean-all  — clean __pycache__ in all packages"

test-all:
	@echo "\n=== mcp-governance ==="
	@cd mcp-governance && pip install -e ".[dev]" -q && $(PYTHON) -m pytest tests/ --tb=short -q
	@echo "\nAll package tests done."

clean-all:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned all packages."
