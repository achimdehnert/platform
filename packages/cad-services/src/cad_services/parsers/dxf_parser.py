from __future__ import annotations

import time
from pathlib import Path

from .base import BaseParser
from ..exceptions import CADParseError, CADResourceError
from ..extractors import DXFExtractor
from ..mapping import MappingProfile
from ..models import CADParseResult, CADParseStatistics, SourceFormat
from ..utils.hash import sha256_file


class DXFParser(BaseParser):
    def __init__(self, profile: MappingProfile | None = None):
        self.profile = profile

    def parse(self, file_path: Path) -> CADParseResult:
        start = time.perf_counter()

        try:
            file_size_bytes = file_path.stat().st_size
        except FileNotFoundError as e:
            raise CADParseError(code="FILE_NOT_FOUND", message="Datei nicht gefunden", file_path=str(file_path)) from e
        except PermissionError as e:
            raise CADParseError(code="FILE_ACCESS_DENIED", message="Kein Zugriff auf Datei", file_path=str(file_path)) from e

        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise CADResourceError(
                code="FILE_TOO_LARGE",
                message=f"Max {self.max_file_size_mb}MB, Datei hat {file_size_mb:.1f}MB",
                suggestion="Datei aufteilen oder Import im Job-Layer ausführen",
            )

        try:
            import ezdxf

            doc = ezdxf.readfile(str(file_path))
            msp = doc.modelspace()
        except Exception as e:
            raise CADParseError(code="DXF_PARSE_FAILED", message=f"Ungültige DXF-Datei: {e}", file_path=str(file_path)) from e

        extractor = DXFExtractor(profile=self.profile)
        elements = extractor.extract(msp)

        duration_ms = int((time.perf_counter() - start) * 1000)

        elements_by_category: dict[str, int] = {}
        for e in elements:
            cat = e.category.value if hasattr(e.category, "value") else str(e.category)
            elements_by_category[cat] = elements_by_category.get(cat, 0) + 1

        statistics = CADParseStatistics(
            total_elements=len(elements),
            elements_by_category=elements_by_category,
            file_size_bytes=file_size_bytes,
            parse_duration_ms=duration_ms,
        )

        return CADParseResult(
            file_hash=sha256_file(file_path),
            source_format=SourceFormat.DXF,
            parser_version="0.1.0",
            elements=elements,
            warnings=[],
            statistics=statistics,
        )

    def get_metadata(self, file_path: Path) -> dict:
        return {}

    def validate(self, file_path: Path) -> tuple[bool, list[str]]:
        try:
            self.parse(file_path)
        except Exception as e:
            return False, [str(e)]
        return True, []
