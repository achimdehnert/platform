"""CADToolkit — DomainToolkit implementation for cad-hub.

Provides read-only query tools against IFC building data
using Django ORM. Per ADR-034 §3.5.

Copy this file to: cad-hub/apps/ifc/chat/toolkit.py
"""

from __future__ import annotations

import logging
from typing import Any

from chat_agent import AgentContext, DomainToolkit, ToolResult

logger = logging.getLogger(__name__)

CAD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_rooms",
            "description": (
                "Query rooms in a building model. "
                "Filter by floor, area range, usage category."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "IFC project UUID",
                    },
                    "floor_name": {
                        "type": "string",
                        "description": "Filter by floor name",
                    },
                    "min_area": {
                        "type": "number",
                        "description": "Min area in m2",
                    },
                    "max_area": {
                        "type": "number",
                        "description": "Max area in m2",
                    },
                    "usage_category": {
                        "type": "string",
                        "description": "DIN 277 category code",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_walls",
            "description": (
                "Query walls in a building model. "
                "Filter by floor, external/load-bearing, material."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "IFC project UUID",
                    },
                    "floor_name": {
                        "type": "string",
                        "description": "Filter by floor name",
                    },
                    "is_external": {
                        "type": "boolean",
                        "description": "Filter external walls",
                    },
                    "is_load_bearing": {
                        "type": "boolean",
                        "description": "Filter load-bearing walls",
                    },
                    "material": {
                        "type": "string",
                        "description": "Filter by material",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_windows",
            "description": (
                "Query windows in a building model. "
                "Filter by floor, U-value range, material."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "IFC project UUID",
                    },
                    "floor_name": {
                        "type": "string",
                        "description": "Filter by floor name",
                    },
                    "max_u_value": {
                        "type": "number",
                        "description": "Max U-value in W/m2K",
                    },
                    "material": {
                        "type": "string",
                        "description": "Filter by material",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_quantities",
            "description": (
                "Aggregate quantities (total area, volume, count) "
                "for an element type, optionally grouped."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "IFC project UUID",
                    },
                    "element_type": {
                        "type": "string",
                        "enum": [
                            "room", "wall", "window",
                            "door", "slab",
                        ],
                        "description": "Type of element",
                    },
                    "floor_name": {
                        "type": "string",
                        "description": "Filter by floor",
                    },
                    "group_by": {
                        "type": "string",
                        "enum": [
                            "floor", "material",
                            "usage_category", "type",
                        ],
                        "description": "Group results by",
                    },
                },
                "required": ["element_type"],
            },
        },
    },
]


class CADToolkit(DomainToolkit):
    """Read-only CAD data toolkit for building queries.

    Tools:
    - query_rooms: Rooms by floor/area/usage
    - query_walls: Walls by floor/external/material
    - query_windows: Windows by floor/u-value
    - aggregate_quantities: Aggregate counts/areas/volumes
    """

    @property
    def name(self) -> str:
        return "cad"

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return CAD_TOOLS

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        handlers = {
            "query_rooms": _query_rooms,
            "query_walls": _query_walls,
            "query_windows": _query_windows,
            "aggregate_quantities": _aggregate_quantities,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
        try:
            result = await handler(arguments, ctx)
            if "error" in result:
                return ToolResult(
                    success=False,
                    data=result,
                    error=result["error"],
                )
            return ToolResult(success=True, data=result)
        except Exception as exc:
            logger.exception(
                "Tool %s failed: %s", tool_name, exc
            )
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {exc}",
            )


def _get_tenant_filter(
    ctx: AgentContext,
) -> dict[str, Any]:
    """Build tenant filter kwargs."""
    if ctx.tenant_id:
        return {"tenant_id": ctx.tenant_id}
    return {}


async def _query_rooms(
    args: dict[str, Any], ctx: AgentContext
) -> dict[str, Any]:
    from asgiref.sync import sync_to_async
    from apps.ifc.models import Room

    def _do():
        qs = Room.objects.select_related(
            "floor", "ifc_model__project"
        )
        tf = _get_tenant_filter(ctx)
        if tf:
            qs = qs.filter(**tf)

        project_id = args.get("project_id")
        if project_id:
            qs = qs.filter(ifc_model__project_id=project_id)

        floor_name = args.get("floor_name")
        if floor_name:
            qs = qs.filter(floor__name__icontains=floor_name)

        min_area = args.get("min_area")
        if min_area is not None:
            qs = qs.filter(area__gte=min_area)

        max_area = args.get("max_area")
        if max_area is not None:
            qs = qs.filter(area__lte=max_area)

        usage = args.get("usage_category")
        if usage:
            qs = qs.filter(usage_category=usage)

        rooms = list(
            qs.values(
                "id", "number", "name", "area",
                "height", "volume", "usage_category",
                "floor__name",
            )[:50]
        )
        for r in rooms:
            r["id"] = str(r["id"])
            for k in ("area", "height", "volume"):
                if r[k] is not None:
                    r[k] = float(r[k])
        return {"rooms": rooms, "count": len(rooms)}

    return await sync_to_async(_do)()


async def _query_walls(
    args: dict[str, Any], ctx: AgentContext
) -> dict[str, Any]:
    from asgiref.sync import sync_to_async
    from apps.ifc.models_components import Wall

    def _do():
        qs = Wall.objects.select_related("floor")
        tf = _get_tenant_filter(ctx)
        if tf:
            qs = qs.filter(**tf)

        project_id = args.get("project_id")
        if project_id:
            qs = qs.filter(ifc_model__project_id=project_id)

        floor_name = args.get("floor_name")
        if floor_name:
            qs = qs.filter(floor__name__icontains=floor_name)

        is_ext = args.get("is_external")
        if is_ext is not None:
            qs = qs.filter(is_external=is_ext)

        is_lb = args.get("is_load_bearing")
        if is_lb is not None:
            qs = qs.filter(is_load_bearing=is_lb)

        mat = args.get("material")
        if mat:
            qs = qs.filter(material__icontains=mat)

        walls = list(
            qs.values(
                "id", "name", "length", "height",
                "width", "gross_area", "net_area",
                "volume", "is_external",
                "is_load_bearing", "material",
                "floor__name",
            )[:50]
        )
        for w in walls:
            w["id"] = str(w["id"])
            for k in (
                "length", "height", "width",
                "gross_area", "net_area", "volume",
            ):
                if w[k] is not None:
                    w[k] = float(w[k])
        return {"walls": walls, "count": len(walls)}

    return await sync_to_async(_do)()


async def _query_windows(
    args: dict[str, Any], ctx: AgentContext
) -> dict[str, Any]:
    from asgiref.sync import sync_to_async
    from apps.ifc.models_components import Window

    def _do():
        qs = Window.objects.select_related("floor")
        tf = _get_tenant_filter(ctx)
        if tf:
            qs = qs.filter(**tf)

        project_id = args.get("project_id")
        if project_id:
            qs = qs.filter(ifc_model__project_id=project_id)

        floor_name = args.get("floor_name")
        if floor_name:
            qs = qs.filter(floor__name__icontains=floor_name)

        max_u = args.get("max_u_value")
        if max_u is not None:
            qs = qs.filter(u_value__lte=max_u)

        mat = args.get("material")
        if mat:
            qs = qs.filter(material__icontains=mat)

        windows = list(
            qs.values(
                "id", "number", "name", "width",
                "height", "area", "u_value",
                "material", "glazing_type",
                "floor__name",
            )[:50]
        )
        for w in windows:
            w["id"] = str(w["id"])
            for k in ("width", "height", "area", "u_value"):
                if w[k] is not None:
                    w[k] = float(w[k])
        return {"windows": windows, "count": len(windows)}

    return await sync_to_async(_do)()


async def _aggregate_quantities(
    args: dict[str, Any], ctx: AgentContext
) -> dict[str, Any]:
    from asgiref.sync import sync_to_async
    from django.db.models import Avg, Count, Sum

    element_type = args.get("element_type", "room")
    group_by = args.get("group_by")

    def _do():
        model_info = _get_model_for_type(element_type)
        if not model_info:
            return {
                "error": f"Unknown element_type: {element_type}"
            }

        Model, area_field, volume_field = model_info
        qs = Model.objects.all()

        tf = _get_tenant_filter(ctx)
        if tf:
            qs = qs.filter(**tf)

        project_id = args.get("project_id")
        if project_id:
            qs = qs.filter(ifc_model__project_id=project_id)

        floor_name = args.get("floor_name")
        if floor_name:
            qs = qs.filter(floor__name__icontains=floor_name)

        agg = {"count": Count("id")}
        if area_field:
            agg["total_area_m2"] = Sum(area_field)
            agg["avg_area_m2"] = Avg(area_field)
        if volume_field:
            agg["total_volume_m3"] = Sum(volume_field)

        if group_by:
            group_field = _resolve_group_field(
                element_type, group_by
            )
            if group_field:
                rows = list(
                    qs.values(group_field)
                    .annotate(**agg)
                    .order_by("-count")[:20]
                )
                for r in rows:
                    for k, v in r.items():
                        if hasattr(v, "__float__"):
                            r[k] = round(float(v), 3)
                return {
                    "element_type": element_type,
                    "grouped_by": group_by,
                    "groups": rows,
                }

        result = qs.aggregate(**agg)
        for k, v in result.items():
            if hasattr(v, "__float__"):
                result[k] = round(float(v), 3)
        result["element_type"] = element_type
        return result

    return await sync_to_async(_do)()


def _get_model_for_type(element_type: str):
    """Return (Model, area_field, volume_field) tuple."""
    from apps.ifc.models import Room
    from apps.ifc.models_components import (
        Door, Slab, Wall, Window,
    )
    mapping = {
        "room": (Room, "area", "volume"),
        "wall": (Wall, "gross_area", "volume"),
        "window": (Window, "area", None),
        "door": (Door, None, None),
        "slab": (Slab, "area", "volume"),
    }
    return mapping.get(element_type)


def _resolve_group_field(
    element_type: str, group_by: str
) -> str | None:
    """Map group_by name to Django ORM field."""
    common = {
        "floor": "floor__name",
        "material": "material",
    }
    specific = {
        "room": {"usage_category": "usage_category"},
        "wall": {"type": "is_external"},
        "slab": {"type": "slab_type"},
    }
    field = common.get(group_by)
    if not field:
        extra = specific.get(element_type, {})
        field = extra.get(group_by)
    return field
