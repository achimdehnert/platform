"""Tests for the LLM-based DIATAXIS fallback classifier."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from docs_agent.analyzer.llm_classifier import (
    _parse_classification_response,
    reclassify_low_confidence,
)
from docs_agent.llm_client import LLMResponse
from docs_agent.models import DiaxisClassification, DiaxisQuadrant


@pytest.fixture()
def low_confidence_results(tmp_path: Path) -> list[DiaxisClassification]:
    """Create a mix of high and low confidence classifications."""
    doc1 = tmp_path / "tutorial.md"
    doc1.write_text("# Getting Started\nStep 1: install...")
    doc2 = tmp_path / "unclear.md"
    doc2.write_text("# Some Document\nThis is about things.")
    doc3 = tmp_path / "api-ref.md"
    doc3.write_text("# API Reference\nEndpoints and parameters.")

    return [
        DiaxisClassification(
            file_path=doc1,
            quadrant=DiaxisQuadrant.TUTORIAL,
            confidence=0.85,
        ),
        DiaxisClassification(
            file_path=doc2,
            quadrant=DiaxisQuadrant.UNKNOWN,
            confidence=0.3,
        ),
        DiaxisClassification(
            file_path=doc3,
            quadrant=DiaxisQuadrant.REFERENCE,
            confidence=0.9,
        ),
    ]


def test_should_parse_valid_classification_response(
    tmp_path: Path,
) -> None:
    """Parse a valid LLM JSON response."""
    content = {
        "quadrant": "tutorial",
        "confidence": 0.85,
        "reasoning": "step-by-step instructions",
    }
    result = _parse_classification_response(
        content, tmp_path / "doc.md"
    )

    assert result is not None
    assert result.quadrant == DiaxisQuadrant.TUTORIAL
    assert result.confidence == 0.85
    assert "llm:" in result.triggers[0]


def test_should_parse_string_json_response(
    tmp_path: Path,
) -> None:
    """Parse a string JSON response."""
    content = '{"quadrant": "guide", "confidence": 0.7}'
    result = _parse_classification_response(
        content, tmp_path / "doc.md"
    )

    assert result is not None
    assert result.quadrant == DiaxisQuadrant.GUIDE
    assert result.confidence == 0.7


def test_should_return_none_for_invalid_quadrant(
    tmp_path: Path,
) -> None:
    """Return None for unknown quadrant values."""
    content = {"quadrant": "invalid", "confidence": 0.5}
    result = _parse_classification_response(
        content, tmp_path / "doc.md"
    )

    assert result is None


def test_should_return_none_for_bad_json(
    tmp_path: Path,
) -> None:
    """Return None for unparseable content."""
    result = _parse_classification_response(
        "not json at all", tmp_path / "doc.md"
    )

    assert result is None


def test_should_return_none_for_non_dict(
    tmp_path: Path,
) -> None:
    """Return None for non-dict content."""
    result = _parse_classification_response(
        [1, 2, 3], tmp_path / "doc.md"
    )

    assert result is None


@patch("docs_agent.analyzer.llm_classifier.generate")
def test_should_keep_high_confidence_skip_llm(
    mock_generate: AsyncMock,
    low_confidence_results: list[DiaxisClassification],
) -> None:
    """High-confidence items should NOT trigger LLM calls."""
    mock_generate.return_value = LLMResponse(
        success=True,
        content={
            "quadrant": "explanation",
            "confidence": 0.8,
            "reasoning": "llm says explanation",
        },
    )

    results = asyncio.run(
        reclassify_low_confidence(
            low_confidence_results, threshold=0.7
        )
    )

    # Only the low-confidence one (0.3) should trigger LLM
    assert mock_generate.call_count == 1
    assert len(results) == 3
    # High confidence items preserved
    assert results[0].quadrant == DiaxisQuadrant.TUTORIAL
    assert results[0].confidence == 0.85
    assert results[2].quadrant == DiaxisQuadrant.REFERENCE
    assert results[2].confidence == 0.9


@patch("docs_agent.analyzer.llm_classifier.generate")
def test_should_replace_low_confidence_with_llm(
    mock_generate: AsyncMock,
    low_confidence_results: list[DiaxisClassification],
) -> None:
    """Low-confidence items should be replaced with LLM result."""
    mock_generate.return_value = LLMResponse(
        success=True,
        content={
            "quadrant": "explanation",
            "confidence": 0.82,
            "reasoning": "discusses concepts",
        },
    )

    results = asyncio.run(
        reclassify_low_confidence(
            low_confidence_results, threshold=0.7
        )
    )

    # The low-confidence item should be reclassified
    assert results[1].quadrant == DiaxisQuadrant.EXPLANATION
    assert results[1].confidence == 0.82


@patch("docs_agent.analyzer.llm_classifier.generate")
def test_should_keep_original_on_llm_failure(
    mock_generate: AsyncMock,
    low_confidence_results: list[DiaxisClassification],
) -> None:
    """Keep original classification if LLM fails."""
    mock_generate.return_value = LLMResponse(
        success=False,
        error="connection refused",
    )

    results = asyncio.run(
        reclassify_low_confidence(
            low_confidence_results, threshold=0.7
        )
    )

    # Original low-confidence classification preserved
    assert results[1].quadrant == DiaxisQuadrant.UNKNOWN
    assert results[1].confidence == 0.3
