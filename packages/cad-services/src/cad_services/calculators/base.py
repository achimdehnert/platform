from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import CADElement


class BaseCalculator(ABC):
    @abstractmethod
    def calculate(self, elements: list[CADElement]) -> list[CADElement]:
        raise NotImplementedError
