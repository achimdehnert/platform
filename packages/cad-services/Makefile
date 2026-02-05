# CAD-Services Makefile
# Development and CI/CD automation

.PHONY: help install lint lint-fix format test clean dev

# Default target
help:
	@echo "CAD-Services Development Commands"
	@echo "================================="
	@echo "  make install     - Install dependencies"
	@echo "  make lint        - Run linter (check only)"
	@echo "  make lint-fix    - Run linter with auto-fix"
	@echo "  make format      - Format code with Ruff"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Remove cache files"
	@echo "  make dev         - Start development server"
	@echo "  make pre-commit  - Install pre-commit hooks"

# Install dependencies
install:
	pip install -e ".[dev,ifc]"
	pip install pre-commit

# Lint check (no changes)
lint:
	ruff check src/ --config pyproject.toml
	ruff format --check src/ --config pyproject.toml

# Lint with auto-fix
lint-fix:
	ruff check src/ --fix --config pyproject.toml
	ruff format src/ --config pyproject.toml

# Format only
format:
	ruff format src/ --config pyproject.toml

# Run tests
test:
	pytest tests/ -v

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Development server (Django)
dev:
	cd src && python -m cad_services.django.manage runserver 0.0.0.0:8000

# Install pre-commit hooks
pre-commit:
	pre-commit install
	pre-commit run --all-files

# Quick check before commit
check: lint-fix test
	@echo "All checks passed!"

# CI pipeline simulation
ci: clean install lint test
	@echo "CI pipeline completed successfully!"
