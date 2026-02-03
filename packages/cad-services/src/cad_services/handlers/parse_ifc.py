"""
IFC Parse Handler - Application Layer.

Orchestriert IFC-Parsing mit klarer Separation of Concerns.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from cad_services.handlers.commands import ParseIFCCommand, ParseIFCResult


if TYPE_CHECKING:
    from pathlib import Path


class IFCDomainServiceProtocol(Protocol):
    """Protocol für IFC Domain Service."""

    def parse_file(self, file_path: Path) -> IFCParseServiceResult:
        """Parst IFC-Datei."""
        ...


class IFCParseServiceResult(Protocol):
    """Protocol für Parse Result vom Domain Service."""

    model_name: str
    ifc_schema: str | None
    floors: list
    rooms: list
    windows: list
    doors: list
    walls: list
    slabs: list
    total_area: Decimal
    total_volume: Decimal
    errors: list[str]
    warnings: list[str]


class CADModelRepositoryProtocol(Protocol):
    """Protocol für CAD Model Repository."""

    def create(
        self,
        project_id: int,
        name: str,
        source_format: str,
        ifc_schema: str | None,
        created_by_id: int,
    ) -> CADModelEntity:
        """Erstellt neues CAD-Modell."""
        ...

    def bulk_create_floors(self, model_id: int, floors: list) -> int:
        """Bulk-Insert für Geschosse."""
        ...

    def bulk_create_rooms(self, model_id: int, rooms: list) -> int:
        """Bulk-Insert für Räume."""
        ...

    def bulk_create_windows(self, model_id: int, windows: list) -> int:
        """Bulk-Insert für Fenster."""
        ...

    def bulk_create_doors(self, model_id: int, doors: list) -> int:
        """Bulk-Insert für Türen."""
        ...

    def bulk_create_walls(self, model_id: int, walls: list) -> int:
        """Bulk-Insert für Wände."""
        ...

    def bulk_create_slabs(self, model_id: int, slabs: list) -> int:
        """Bulk-Insert für Decken."""
        ...

    def update_status(self, model_id: int, status: str) -> None:
        """Aktualisiert Modell-Status."""
        ...


class CADModelEntity(Protocol):
    """Protocol für CAD Model Entity."""

    id: int


class ParseIFCHandler:
    """Handler für IFC-Parsing.

    Verantwortlichkeiten:
        - Orchestrierung des Use Cases
        - Transaction Management
        - Keine Business Logic (delegiert an Domain Service)

    Attributes:
        _ifc_service: Domain Service für IFC-Logik.
        _model_repo: Repository für CAD-Modelle.

    Example:
        >>> handler = ParseIFCHandler(ifc_service, model_repo)
        >>> result = handler.execute(command)
    """

    def __init__(
        self,
        ifc_service: IFCDomainServiceProtocol,
        model_repo: CADModelRepositoryProtocol,
    ) -> None:
        """Initialisiert Handler mit Dependencies.

        Args:
            ifc_service: Domain Service für IFC-Logik.
            model_repo: Repository für CAD-Modelle.
        """
        self._ifc_service = ifc_service
        self._model_repo = model_repo

    def execute(self, command: ParseIFCCommand) -> ParseIFCResult:
        """Führt IFC-Parsing aus.

        Args:
            command: Parse-Command mit Datei und Kontext.

        Returns:
            ParseIFCResult mit Statistiken und Ergebnis.

        Raises:
            ValueError: Bei ungültiger IFC-Datei.
            PermissionError: Bei fehlendem Tenant-Zugriff.
        """
        from pathlib import Path

        start_time = time.perf_counter()
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Domain Service: Parse & Extract
        parse_result = self._ifc_service.parse_file(Path(command.file_path))

        if parse_result.errors:
            errors.extend(parse_result.errors)
        if parse_result.warnings:
            warnings.extend(parse_result.warnings)

        # 2. Repository: Persist
        model = self._model_repo.create(
            project_id=command.project_id,
            name=parse_result.model_name,
            source_format="ifc",
            ifc_schema=parse_result.ifc_schema,
            created_by_id=command.user_id,
        )

        # 3. Persist extracted elements
        self._model_repo.bulk_create_floors(model.id, parse_result.floors)
        self._model_repo.bulk_create_rooms(model.id, parse_result.rooms)
        self._model_repo.bulk_create_windows(model.id, parse_result.windows)
        self._model_repo.bulk_create_doors(model.id, parse_result.doors)
        self._model_repo.bulk_create_walls(model.id, parse_result.walls)
        self._model_repo.bulk_create_slabs(model.id, parse_result.slabs)

        # 4. Update model status
        self._model_repo.update_status(model.id, "ready")

        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        return ParseIFCResult(
            model_id=model.id,
            floor_count=len(parse_result.floors),
            room_count=len(parse_result.rooms),
            window_count=len(parse_result.windows),
            door_count=len(parse_result.doors),
            wall_count=len(parse_result.walls),
            slab_count=len(parse_result.slabs),
            total_area_m2=parse_result.total_area,
            total_volume_m3=parse_result.total_volume,
            errors=errors,
            warnings=warnings,
            processing_time_ms=processing_time_ms,
        )
