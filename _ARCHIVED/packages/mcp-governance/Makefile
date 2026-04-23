# mcp-governance — Developer Makefile

.PHONY: install test test-v clean help

PYTHON := python3
PIP    := pip

help:
	@echo "Available targets:"
	@echo "  install   — pip install -e '.[dev]'"
	@echo "  test      — pytest (quiet)"
	@echo "  test-v    — pytest (verbose)"
	@echo "  clean     — remove __pycache__ + .pytest_cache"

install:
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ --tb=short -q

test-v:
	$(PYTHON) -m pytest tests/ --tb=short -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	@echo "Cleaned."
