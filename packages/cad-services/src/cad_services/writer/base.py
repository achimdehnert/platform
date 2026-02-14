"""Abstract base for CAD data writers.

ADR-034 §2: ETL Pipeline — Writer takes CADParseResult and persists
normalized data to a storage backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..models import CADParseResult


@dataclass(frozen=True)
class WriteResult:
    """Result of a write operation."""

    cad_model_id: int
    floors_written: int = 0
    rooms_written: int = 0
    walls_written: int = 0
    windows_written: int = 0
    doors_written: int = 0
    slabs_written: int = 0
    properties_written: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_elements(self) -> int:
        return (
            self.rooms_written
            + self.walls_written
            + self.windows_written
            + self.doors_written
            + self.slabs_written
        )


class BaseWriter(ABC):
    """Abstract writer for persisting CADParseResult to storage."""

    @abstractmethod
    async def write(
        self,
        result: CADParseResult,
        *,
        project_id: int,
        model_name: str,
        source_file_path: str | None = None,
        created_by_id: int,
    ) -> WriteResult:
        """Persist a CADParseResult to storage.

        Args:
            result: Parsed CAD data.
            project_id: FK to cadhub_project.
            model_name: Display name for the CAD model.
            source_file_path: Original file path (optional).
            created_by_id: FK to core_user.

        Returns:
            WriteResult with counts of persisted records.
        """
        ...
