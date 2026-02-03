from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import CADElement


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, raw_entities) -> list[CADElement]:
        raise NotImplementedError
