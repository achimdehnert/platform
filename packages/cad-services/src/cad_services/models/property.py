from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class PropertySource(str, Enum):
    IFC_PSET = "ifc_pset"
    IFC_QUANTITY = "ifc_quantity"
    IFC_ATTRIBUTE = "ifc_attribute"
    DXF_LAYER = "dxf_layer"
    DXF_BLOCK_ATTR = "dxf_block_attr"
    DXF_XDATA = "dxf_xdata"
    DXF_TEXT = "dxf_text"
    COMPUTED = "computed"
    MAPPED = "mapped"


class CADProperty(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    value: Any

    source: PropertySource
    source_name: str | None = None
    original_name: str | None = None

    data_type: str = "string"
    unit: str | None = None
