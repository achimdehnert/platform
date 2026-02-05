from __future__ import annotations

from abc import ABC, abstractmethod

from ..mapping import MappingProfile


class MappingProfileRepository(ABC):
    @abstractmethod
    def get_by_name(self, name: str) -> MappingProfile:
        raise NotImplementedError

    @abstractmethod
    def get_default(self) -> MappingProfile:
        raise NotImplementedError
