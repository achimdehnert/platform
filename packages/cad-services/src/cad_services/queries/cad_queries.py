"""Async query service for normalized CAD data.

ADR-034 §2: Tenant-filtered queries against cadhub_v_* views.
Designed as backend for CADToolkit (chat-agent DomainToolkit).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


_PROJECT_FILTER = (
    "cad_model_id IN ("
    "SELECT id FROM cadhub_cad_model WHERE project_id = $2"
    ")"
)


class CADQueryService:
    """Tenant-scoped queries against normalized CAD data.

    All methods require tenant_id to enforce multi-tenant isolation.
    Queries run against the SQL views from 007_chat_query_views.sql.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------

    async def query_rooms(
        self,
        *,
        tenant_id: int,
        project_id: int,
        floor_name: str | None = None,
        min_area_m2: Decimal | None = None,
        max_area_m2: Decimal | None = None,
        usage_category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query rooms with optional filters."""
        conditions = ["tenant_id = $1", _PROJECT_FILTER]
        params: list[Any] = [tenant_id, project_id]
        idx = 3

        if floor_name:
            conditions.append(f"floor_name ILIKE ${idx}")
            params.append(f"%{floor_name}%")
            idx += 1

        if min_area_m2 is not None:
            conditions.append(f"area_m2 >= ${idx}")
            params.append(min_area_m2)
            idx += 1

        if max_area_m2 is not None:
            conditions.append(f"area_m2 <= ${idx}")
            params.append(max_area_m2)
            idx += 1

        if usage_category:
            conditions.append(f"usage_code = ${idx}")
            params.append(usage_category)
            idx += 1

        where = " AND ".join(conditions)
        query = f"""
            SELECT room_number, room_name, floor_name,
                   area_m2, height_m, volume_m3,
                   usage_code, usage_name
            FROM cadhub_v_room_summary
            WHERE {where}
            ORDER BY floor_name, room_number
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Walls
    # ------------------------------------------------------------------

    async def query_walls(
        self,
        *,
        tenant_id: int,
        project_id: int,
        floor_name: str | None = None,
        is_load_bearing: bool | None = None,
        is_external: bool | None = None,
        material: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query walls with optional filters."""
        conditions = ["tenant_id = $1", _PROJECT_FILTER]
        params: list[Any] = [tenant_id, project_id]
        idx = 3

        if floor_name:
            conditions.append(f"floor_name ILIKE ${idx}")
            params.append(f"%{floor_name}%")
            idx += 1

        if is_load_bearing is not None:
            conditions.append(f"is_load_bearing = ${idx}")
            params.append(is_load_bearing)
            idx += 1

        if is_external is not None:
            conditions.append(f"is_external = ${idx}")
            params.append(is_external)
            idx += 1

        if material:
            conditions.append(f"material ILIKE ${idx}")
            params.append(f"%{material}%")
            idx += 1

        where = " AND ".join(conditions)
        query = f"""
            SELECT wall_name, floor_name,
                   length_m, height_m, thickness_m,
                   gross_area_m2, volume_m3,
                   is_external, is_load_bearing, material
            FROM cadhub_v_wall_summary
            WHERE {where}
            ORDER BY floor_name, wall_name
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------

    async def query_windows(
        self,
        *,
        tenant_id: int,
        project_id: int,
        floor_name: str | None = None,
        min_u_value: Decimal | None = None,
        max_u_value: Decimal | None = None,
    ) -> list[dict[str, Any]]:
        """Query windows with optional filters."""
        conditions = ["tenant_id = $1", _PROJECT_FILTER]
        params: list[Any] = [tenant_id, project_id]
        idx = 3

        if floor_name:
            conditions.append(f"floor_name ILIKE ${idx}")
            params.append(f"%{floor_name}%")
            idx += 1

        if min_u_value is not None:
            conditions.append(f"u_value_w_m2k >= ${idx}")
            params.append(min_u_value)
            idx += 1

        if max_u_value is not None:
            conditions.append(f"u_value_w_m2k <= ${idx}")
            params.append(max_u_value)
            idx += 1

        where = " AND ".join(conditions)
        query = f"""
            SELECT window_number, window_name, floor_name,
                   room_number, room_name,
                   width_m, height_m, area_m2,
                   u_value_w_m2k, material, glazing_type
            FROM cadhub_v_window_summary
            WHERE {where}
            ORDER BY floor_name, window_number
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Floor aggregation
    # ------------------------------------------------------------------

    async def query_floor_aggregation(
        self,
        *,
        tenant_id: int,
        project_id: int,
    ) -> list[dict[str, Any]]:
        """Get per-floor summary statistics."""
        query = """
            SELECT floor_name, elevation_m, sort_order,
                   room_count, total_room_area_m2,
                   wall_count, load_bearing_wall_count,
                   window_count, door_count
            FROM cadhub_v_floor_aggregation
            WHERE tenant_id = $1
              AND cad_model_id IN (
                  SELECT id FROM cadhub_cad_model
                  WHERE project_id = $2
              )
            ORDER BY sort_order
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, tenant_id, project_id)
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Element counts (generic aggregation)
    # ------------------------------------------------------------------

    async def aggregate_quantities(
        self,
        *,
        tenant_id: int,
        project_id: int,
        element_type: str,
        floor_name: str | None = None,
        group_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate element counts and quantities.

        Args:
            element_type: room, wall, window, door, slab
            floor_name: Optional floor filter.
            group_by: floor, material, usage_category, type
        """
        view_map = {
            "room": ("cadhub_v_room_summary", "area_m2"),
            "wall": ("cadhub_v_wall_summary", "gross_area_m2"),
            "window": ("cadhub_v_window_summary", "area_m2"),
            "door": ("cadhub_v_door_summary", None),
            "slab": None,
        }

        spec = view_map.get(element_type)
        if spec is None:
            return [{"error": f"Unknown element_type: {element_type}"}]

        view_name, area_col = spec
        conditions = [
            "tenant_id = $1",
            "cad_model_id IN ("
            "SELECT id FROM cadhub_cad_model WHERE project_id = $2"
            ")",
        ]
        params: list[Any] = [tenant_id, project_id]
        idx = 3

        if floor_name:
            conditions.append(f"floor_name ILIKE ${idx}")
            params.append(f"%{floor_name}%")
            idx += 1

        where = " AND ".join(conditions)

        group_col_map = {
            "floor": "floor_name",
            "material": "material",
            "usage_category": "usage_code",
        }
        group_col = group_col_map.get(group_by or "", None)

        if group_col:
            area_select = (
                f", SUM({area_col}) AS total_area_m2"
                if area_col
                else ""
            )
            query = f"""
                SELECT {group_col} AS group_key,
                       COUNT(*) AS count
                       {area_select}
                FROM {view_name}
                WHERE {where}
                GROUP BY {group_col}
                ORDER BY count DESC
            """
        else:
            area_select = (
                f", SUM({area_col}) AS total_area_m2"
                if area_col
                else ""
            )
            query = f"""
                SELECT COUNT(*) AS count
                       {area_select}
                FROM {view_name}
                WHERE {where}
            """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
