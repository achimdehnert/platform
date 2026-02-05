.PHONY: help install dev test lint format typecheck docs clean build publish

help:
	@echo "PPTX-Hub Development Commands"
	@echo ""
	@echo "  install     Install package"
	@echo "  dev         Install with dev dependencies"
	@echo "  test        Run tests"
	@echo "  lint        Run linting"
	@echo "  format      Format code"
	@echo "  typecheck   Run type checking"
	@echo "  docs        Build documentation"
	@echo "  clean       Clean build artifacts"
	@echo "  build       Build package"
	@echo "  publish     Publish to PyPI (requires credentials)"

install:
	pip install -e .

dev:
	pip install -e ".[dev,all]"
	pre-commit install

test:
	pytest -v

test-cov:
	pytest --cov --cov-report=html --cov-report=term-missing

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy src

docs:
	mkdocs serve

docs-build:
	mkdocs build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build: clean
	python -m build

publish: build
	twine upload dist/*
