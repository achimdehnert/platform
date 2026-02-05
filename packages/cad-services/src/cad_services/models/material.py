from __future__ import annotations

from pydantic import BaseModel


class CADMaterial(BaseModel):
    name: str
