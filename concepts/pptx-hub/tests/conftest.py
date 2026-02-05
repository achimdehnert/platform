"""
Pytest configuration and fixtures.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_path() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pptx(fixtures_path: Path) -> Path:
    """Path to sample PPTX file."""
    return fixtures_path / "sample.pptx"
