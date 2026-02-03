from __future__ import annotations

from pathlib import Path

from ..mapping import MappingProfile
from .base import MappingProfileRepository


class FileProfileRepository(MappingProfileRepository):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get_by_name(self, name: str) -> MappingProfile:
        return MappingProfile.from_json(self.base_dir / f"{name}.json")

    def get_default(self) -> MappingProfile:
        return MappingProfile.default()
