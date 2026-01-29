from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import CADParseResult


class BaseParser(ABC):
    max_file_size_mb: int = 500

    @abstractmethod
    def parse(self, file_path: Path) -> CADParseResult:
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self, file_path: Path) -> dict:
        raise NotImplementedError

    @abstractmethod
    def validate(self, file_path: Path) -> tuple[bool, list[str]]:
        raise NotImplementedError
