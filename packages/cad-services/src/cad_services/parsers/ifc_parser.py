from __future__ import annotations

from pathlib import Path

from ..exceptions import CADParseError, CADResourceError
from ..extractors import IFCExtractor
from ..models import CADParseResult, CADParseStatistics, SourceFormat
from ..utils.hash import sha256_file
from .base import BaseParser


class IFCParser(BaseParser):
    def parse(self, file_path: Path) -> CADParseResult:
        try:
            import ifcopenshell  # noqa: F401
        except Exception as e:
            raise CADParseError(
                code="IFC_DEPENDENCY_MISSING",
                message=(
                    "ifcopenshell ist nicht installiert (installiere Extras: cad-services[ifc])"
                ),
                file_path=str(file_path),
            ) from e

        try:
            file_size_bytes = file_path.stat().st_size
        except FileNotFoundError as e:
            raise CADParseError(
                code="FILE_NOT_FOUND",
                message="Datei nicht gefunden",
                file_path=str(file_path),
            ) from e
        except PermissionError as e:
            raise CADParseError(
                code="FILE_ACCESS_DENIED",
                message="Kein Zugriff auf Datei",
                file_path=str(file_path),
            ) from e

        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise CADResourceError(
                code="FILE_TOO_LARGE",
                message=f"Max {self.max_file_size_mb}MB, Datei hat {file_size_mb:.1f}MB",
                suggestion="Datei aufteilen oder Import im Job-Layer ausführen",
            )

        try:
            file_hash = sha256_file(file_path)
        except Exception as e:
            raise CADParseError(
                code="FILE_HASH_FAILED",
                message="Konnte Datei nicht hashen",
                file_path=str(file_path),
            ) from e

        try:
            import ifcopenshell

            ifc = ifcopenshell.open(str(file_path))
        except Exception as e:
            raise CADParseError(
                code="IFC_PARSE_FAILED",
                message=f"Ungültige IFC-Datei: {e}",
                file_path=str(file_path),
            ) from e

        extractor = IFCExtractor()
        elements = extractor.extract(ifc)

        elements_by_category: dict[str, int] = {}
        for e in elements:
            cat = e.category.value if hasattr(e.category, "value") else str(e.category)
            elements_by_category[cat] = elements_by_category.get(cat, 0) + 1

        ifc_schema = getattr(getattr(ifc, "schema", None), "name", None) or getattr(
            ifc, "schema", None
        )

        statistics = CADParseStatistics(
            total_elements=len(elements),
            elements_by_category=elements_by_category,
            file_size_bytes=file_size_bytes,
            ifc_schema=ifc_schema,
        )

        return CADParseResult(
            file_hash=file_hash,
            source_format=SourceFormat.IFC,
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
