"""PostgreSQL writer for normalized CAD data.

ADR-034 §2: Maps CADParseResult → cadhub_* tables via asyncpg.

Mapping:
    CADElement(category=WALL)    → cadhub_wall
    CADElement(category=SPACE)   → cadhub_room
    CADElement(category=WINDOW)  → cadhub_window
    CADElement(category=DOOR)    → cadhub_door
    CADElement(category=SLAB)    → cadhub_slab
    storey_name / storey_id      → cadhub_floor
    CADProperty                  → cadhub_element_property (EAV)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import asyncpg

from ..models import CADElement, CADParseResult, ElementCategory
from ..models.quantity import QuantityType
from .base import BaseWriter, WriteResult

logger = logging.getLogger(__name__)


def _get_quantity(element: CADElement, qtype: QuantityType) -> Decimal | None:
    """Extract first quantity of given type from element."""
    for q in element.quantities:
        if q.quantity_type == qtype:
            return q.value
    return None


def _get_property_value(element: CADElement, name: str) -> Any:
    """Extract property value by name (case-insensitive)."""
    lower = name.lower()
    for p in element.properties:
        if p.name.lower() == lower:
            return p.value
    return None


def _get_bool_property(element: CADElement, name: str) -> bool:
    """Extract boolean property, default False."""
    val = _get_property_value(element, name)
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "ja", ".t.")
    return bool(val)


def _first_material(element: CADElement) -> str | None:
    """Return first material name or None."""
    if element.materials:
        return element.materials[0].name
    return None


class PostgresWriter(BaseWriter):
    """Writes CADParseResult to normalized PostgreSQL tables.

    Uses asyncpg connection pool. All writes happen in a single
    transaction per CAD model to ensure consistency.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def write(
        self,
        result: CADParseResult,
        *,
        project_id: int,
        model_name: str,
        source_file_path: str | None = None,
        created_by_id: int,
    ) -> WriteResult:
        warnings: list[str] = []
        counts = {
            "floors": 0,
            "rooms": 0,
            "walls": 0,
            "windows": 0,
            "doors": 0,
            "slabs": 0,
            "properties": 0,
        }

        async with self._pool.acquire() as conn, conn.transaction():
            model_id = await self._upsert_cad_model(
                conn,
                project_id=project_id,
                model_name=model_name,
                source_file_path=source_file_path,
                source_format=result.source_format,
                file_size_bytes=result.statistics.file_size_bytes,
                ifc_schema=result.statistics.ifc_schema,
                ifc_application=result.statistics.ifc_application,
                created_by_id=created_by_id,
            )

            floor_map = await self._write_floors(
                conn, model_id, result.elements
            )
            counts["floors"] = len(floor_map)

            for element in result.elements:
                floor_id = floor_map.get(element.storey_id)
                cat = element.category

                try:
                    if cat == ElementCategory.WALL:
                        await self._write_wall(
                            conn, model_id, floor_id, element
                        )
                        counts["walls"] += 1
                    elif cat == ElementCategory.SPACE:
                        await self._write_room(
                            conn, model_id, floor_id, element
                        )
                        counts["rooms"] += 1
                    elif cat == ElementCategory.WINDOW:
                        await self._write_window(
                            conn, model_id, floor_id, element
                        )
                        counts["windows"] += 1
                    elif cat == ElementCategory.DOOR:
                        await self._write_door(
                            conn, model_id, floor_id, element
                        )
                        counts["doors"] += 1
                    elif cat == ElementCategory.SLAB:
                        await self._write_slab(
                            conn, model_id, floor_id, element
                        )
                        counts["slabs"] += 1
                except Exception:
                    msg = (
                        f"Failed to write {cat} element "
                        f"{element.external_id}: skipped"
                    )
                    logger.warning(msg, exc_info=True)
                    warnings.append(msg)

            await self._mark_model_ready(conn, model_id)

        logger.info(
            "CAD model %d written: %d floors, %d elements",
            model_id,
            counts["floors"],
            sum(counts.values()) - counts["floors"] - counts["properties"],
        )
        return WriteResult(
            cad_model_id=model_id,
            floors_written=counts["floors"],
            rooms_written=counts["rooms"],
            walls_written=counts["walls"],
            windows_written=counts["windows"],
            doors_written=counts["doors"],
            slabs_written=counts["slabs"],
            properties_written=counts["properties"],
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # CAD Model
    # ------------------------------------------------------------------

    async def _upsert_cad_model(
        self,
        conn: asyncpg.Connection,
        *,
        project_id: int,
        model_name: str,
        source_file_path: str | None,
        source_format: str,
        file_size_bytes: int,
        ifc_schema: str | None,
        ifc_application: str | None,
        created_by_id: int,
    ) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO cadhub_cad_model (
                project_id, version, name, source_file_path,
                source_format, file_size_bytes, ifc_schema,
                ifc_application, status, created_by_id
            )
            VALUES ($1, (
                SELECT COALESCE(MAX(version), 0) + 1
                FROM cadhub_cad_model WHERE project_id = $1
            ), $2, $3, $4, $5, $6, $7, 'processing', $8)
            RETURNING id
            """,
            project_id,
            model_name,
            source_file_path,
            source_format,
            file_size_bytes,
            ifc_schema,
            ifc_application,
            created_by_id,
        )
        return row["id"]

    async def _mark_model_ready(
        self, conn: asyncpg.Connection, model_id: int
    ) -> None:
        await conn.execute(
            """
            UPDATE cadhub_cad_model
            SET status = 'ready', processed_at = NOW()
            WHERE id = $1
            """,
            model_id,
        )

    # ------------------------------------------------------------------
    # Floors (extracted from element storey metadata)
    # ------------------------------------------------------------------

    async def _write_floors(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        elements: list[CADElement],
    ) -> dict[str | None, int]:
        """Extract unique floors from elements and write them.

        Returns:
            Mapping of storey_id → cadhub_floor.id
        """
        seen: dict[str, tuple[str, int]] = {}
        sort_idx = 0
        for el in elements:
            if el.storey_id and el.storey_id not in seen:
                seen[el.storey_id] = (el.storey_name or el.storey_id, sort_idx)
                sort_idx += 1

        floor_map: dict[str | None, int] = {}
        for storey_id, (name, order) in seen.items():
            row = await conn.fetchrow(
                """
                INSERT INTO cadhub_floor (
                    cad_model_id, ifc_guid, name, sort_order
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE
                    SET name = EXCLUDED.name
                RETURNING id
                """,
                model_id,
                storey_id,
                name,
                order,
            )
            floor_map[storey_id] = row["id"]

        return floor_map

    # ------------------------------------------------------------------
    # Walls
    # ------------------------------------------------------------------

    async def _write_wall(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        floor_id: int | None,
        element: CADElement,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO cadhub_wall (
                cad_model_id, floor_id, ifc_guid, name,
                length_m, height_m, thickness_m,
                gross_area_m2, net_area_m2, volume_m3,
                is_external, is_load_bearing, material
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE SET
                name = EXCLUDED.name,
                length_m = EXCLUDED.length_m,
                height_m = EXCLUDED.height_m,
                thickness_m = EXCLUDED.thickness_m,
                gross_area_m2 = EXCLUDED.gross_area_m2,
                net_area_m2 = EXCLUDED.net_area_m2,
                volume_m3 = EXCLUDED.volume_m3,
                is_external = EXCLUDED.is_external,
                is_load_bearing = EXCLUDED.is_load_bearing,
                material = EXCLUDED.material
            """,
            model_id,
            floor_id,
            element.external_id,
            element.name or None,
            _get_quantity(element, QuantityType.LENGTH),
            _get_quantity(element, QuantityType.HEIGHT),
            _get_quantity(element, QuantityType.THICKNESS),
            _get_quantity(element, QuantityType.AREA),
            None,  # net_area_m2 — not yet extracted
            _get_quantity(element, QuantityType.VOLUME),
            _get_bool_property(element, "IsExternal"),
            _get_bool_property(element, "LoadBearing"),
            _first_material(element),
        )

    # ------------------------------------------------------------------
    # Rooms (IfcSpace)
    # ------------------------------------------------------------------

    async def _write_room(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        floor_id: int | None,
        element: CADElement,
    ) -> None:
        number = element.number or _get_property_value(element, "Reference") or ""
        long_name = _get_property_value(element, "LongName")

        await conn.execute(
            """
            INSERT INTO cadhub_room (
                cad_model_id, floor_id, ifc_guid, number, name,
                long_name, area_m2, height_m, volume_m3, perimeter_m
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE SET
                number = EXCLUDED.number,
                name = EXCLUDED.name,
                long_name = EXCLUDED.long_name,
                area_m2 = EXCLUDED.area_m2,
                height_m = EXCLUDED.height_m,
                volume_m3 = EXCLUDED.volume_m3,
                perimeter_m = EXCLUDED.perimeter_m
            """,
            model_id,
            floor_id,
            element.external_id,
            str(number),
            element.name or "",
            str(long_name) if long_name else None,
            _get_quantity(element, QuantityType.AREA) or Decimal(0),
            _get_quantity(element, QuantityType.HEIGHT) or Decimal(0),
            _get_quantity(element, QuantityType.VOLUME) or Decimal(0),
            _get_quantity(element, QuantityType.PERIMETER) or Decimal(0),
        )

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------

    async def _write_window(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        floor_id: int | None,
        element: CADElement,
    ) -> None:
        u_value = _get_property_value(element, "ThermalTransmittance")
        if u_value is not None:
            try:
                u_value = Decimal(str(u_value))
            except Exception:
                u_value = None

        await conn.execute(
            """
            INSERT INTO cadhub_window (
                cad_model_id, floor_id, ifc_guid, number, name,
                width_m, height_m, area_m2,
                u_value_w_m2k, material, glazing_type
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE SET
                number = EXCLUDED.number,
                name = EXCLUDED.name,
                width_m = EXCLUDED.width_m,
                height_m = EXCLUDED.height_m,
                area_m2 = EXCLUDED.area_m2,
                u_value_w_m2k = EXCLUDED.u_value_w_m2k,
                material = EXCLUDED.material,
                glazing_type = EXCLUDED.glazing_type
            """,
            model_id,
            floor_id,
            element.external_id,
            element.number,
            element.name or None,
            _get_quantity(element, QuantityType.WIDTH),
            _get_quantity(element, QuantityType.HEIGHT),
            _get_quantity(element, QuantityType.AREA),
            u_value,
            _first_material(element),
            str(_get_property_value(element, "GlazingType") or ""),
        )

    # ------------------------------------------------------------------
    # Doors
    # ------------------------------------------------------------------

    async def _write_door(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        floor_id: int | None,
        element: CADElement,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO cadhub_door (
                cad_model_id, floor_id, ifc_guid, number, name,
                width_m, height_m,
                door_type, material, fire_rating
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE SET
                number = EXCLUDED.number,
                name = EXCLUDED.name,
                width_m = EXCLUDED.width_m,
                height_m = EXCLUDED.height_m,
                door_type = EXCLUDED.door_type,
                material = EXCLUDED.material,
                fire_rating = EXCLUDED.fire_rating
            """,
            model_id,
            floor_id,
            element.external_id,
            element.number,
            element.name or None,
            _get_quantity(element, QuantityType.WIDTH),
            _get_quantity(element, QuantityType.HEIGHT),
            str(_get_property_value(element, "OperationType") or ""),
            _first_material(element),
            str(_get_property_value(element, "FireRating") or ""),
        )

    # ------------------------------------------------------------------
    # Slabs
    # ------------------------------------------------------------------

    async def _write_slab(
        self,
        conn: asyncpg.Connection,
        model_id: int,
        floor_id: int | None,
        element: CADElement,
    ) -> None:
        slab_type = str(
            _get_property_value(element, "PredefinedType") or "FLOOR"
        ).upper()
        valid_types = {"FLOOR", "ROOF", "BASESLAB", "LANDING"}
        if slab_type not in valid_types:
            slab_type = "FLOOR"

        await conn.execute(
            """
            INSERT INTO cadhub_slab (
                cad_model_id, floor_id, ifc_guid, name,
                slab_type, area_m2, thickness_m, volume_m3,
                perimeter_m, material
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (cad_model_id, ifc_guid) DO UPDATE SET
                name = EXCLUDED.name,
                slab_type = EXCLUDED.slab_type,
                area_m2 = EXCLUDED.area_m2,
                thickness_m = EXCLUDED.thickness_m,
                volume_m3 = EXCLUDED.volume_m3,
                perimeter_m = EXCLUDED.perimeter_m,
                material = EXCLUDED.material
            """,
            model_id,
            floor_id,
            element.external_id,
            element.name or None,
            slab_type,
            _get_quantity(element, QuantityType.AREA),
            _get_quantity(element, QuantityType.THICKNESS),
            _get_quantity(element, QuantityType.VOLUME),
            _get_quantity(element, QuantityType.PERIMETER),
            _first_material(element),
        )
