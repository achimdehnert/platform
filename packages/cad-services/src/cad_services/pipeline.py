from __future__ import annotations

from pathlib import Path

from .calculators import QuantityEngine
from .models import CADParseResult
from .parsers import BaseParser


def run_pipeline(
    *,
    parser: BaseParser,
    file_path: Path,
    quantity_engine: QuantityEngine | None = None,
) -> CADParseResult:
    result = parser.parse(file_path)

    if quantity_engine is not None:
        quantity_engine.apply(result.elements)

    return result
