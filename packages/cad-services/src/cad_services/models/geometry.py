from __future__ import annotations

from pydantic import BaseModel


class Point3D(BaseModel):
    x: float
    y: float
    z: float = 0.0


class BoundingBox(BaseModel):
    min_point: Point3D
    max_point: Point3D

    @property
    def width(self) -> float:
        return self.max_point.x - self.min_point.x

    @property
    def depth(self) -> float:
        return self.max_point.y - self.min_point.y

    @property
    def height(self) -> float:
        return self.max_point.z - self.min_point.z


class CADGeometry(BaseModel):
    bbox: BoundingBox | None = None
    centroid: Point3D | None = None

    footprint_points: list[Point3D] | None = None
    footprint_area: float | None = None
