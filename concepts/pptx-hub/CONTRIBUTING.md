# Contributing to PPTX-Hub

Thank you for your interest in contributing to PPTX-Hub! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/pptx-hub.git
   cd pptx-hub
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -e ".[dev,all]"
   ```

4. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Run tests to verify setup**

   ```bash
   pytest
   ```

## Development Workflow

### Creating a Branch

Create a branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### Making Changes

1. Write your code
2. Add or update tests as needed
3. Update documentation if necessary
4. Run the test suite: `pytest`
5. Run linting: `ruff check src tests`
6. Run type checking: `mypy src`

### Commit Messages

We follow conventional commits. Format your commit messages as:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(extractor): add support for table extraction
fix(repackager): preserve formatting in nested shapes
docs(readme): update installation instructions
```

### Pull Request Process

1. Update the CHANGELOG.md with your changes
2. Ensure all tests pass
3. Ensure code passes linting and type checking
4. Submit your pull request
5. Wait for review and address any feedback

## Code Style

### Python Style

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use `ruff` for linting and formatting

### Documentation

- Use Google-style docstrings
- Document all public APIs
- Include examples in docstrings where helpful

Example:
```python
def extract_text(self, source: str | Path) -> ExtractionResult:
    """
    Extract text from a PowerPoint presentation.
    
    Args:
        source: Path to the PPTX file
        
    Returns:
        ExtractionResult containing extracted content
        
    Raises:
        ValueError: If the file cannot be opened
        
    Example:
        >>> extractor = TextExtractor()
        >>> result = extractor.extract("presentation.pptx")
        >>> print(f"Found {len(result.slides)} slides")
    """
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific tests
pytest tests/core/test_extractor.py -v

# Run tests matching a pattern
pytest -k "test_extract"
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source structure (e.g., `tests/core/` for `src/pptx_hub/core/`)
- Use descriptive test names
- Use fixtures for common setup

## Documentation

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build and serve locally
mkdocs serve
```

### Documentation Structure

- `docs/getting-started/`: Installation and quick start guides
- `docs/guides/`: In-depth guides on specific topics
- `docs/api-reference/`: Auto-generated API documentation

## Release Process

Releases are handled by maintainers. The process is:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.1.0`
4. Push the tag: `git push origin v0.1.0`
5. GitHub Actions will automatically publish to PyPI

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas

Thank you for contributing! 🎉
