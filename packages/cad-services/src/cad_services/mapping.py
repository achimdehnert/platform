from __future__ import annotations

import json
import re
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import ElementCategory


class LayerMapping(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    pattern: str
    category: ElementCategory
    properties: dict = Field(default_factory=dict)


class MappingProfile(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    version: str = "1.0"

    layer_mappings: list[LayerMapping] = Field(default_factory=list)
    property_aliases: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> "MappingProfile":
        return cls.default_de()

    @classmethod
    def default_de(cls) -> "MappingProfile":
        return cls(
            name="default_de",
            layer_mappings=[
                LayerMapping(pattern=r"WAND.*", category=ElementCategory.WALL),
                LayerMapping(pattern=r"MAUER.*", category=ElementCategory.WALL),
                LayerMapping(pattern=r"FENSTER.*", category=ElementCategory.WINDOW),
                LayerMapping(pattern=r"T(UE|Ü)R.*", category=ElementCategory.DOOR),
            ],
        )

    @classmethod
    def from_json(cls, path: Path) -> "MappingProfile":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @cached_property
    def _compiled_patterns(self) -> list[tuple[re.Pattern, ElementCategory]]:
        return [(re.compile(m.pattern, re.IGNORECASE), m.category) for m in self.layer_mappings]

    def get_category_for_layer(self, layer: str) -> ElementCategory:
        for pattern, category in self._compiled_patterns:
            if pattern.match(layer):
                return category
        return ElementCategory.UNKNOWN
