"""
Rooms Router
ADR-009: API endpoints for Room queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from cad_services.api.database import fetch_all
from cad_services.api.schemas.room import (
    RoomListResponse,
    RoomResponse,
)


router = APIRouter()


def get_tenant_id() -> int:
    """Get tenant ID from request context (placeholder)."""
    return 1


@router.get("", response_model=RoomListResponse)
async def list_rooms(
    model_id: int | None = Query(None),
    floor_id: int | None = Query(None),
    min_area: float | None = Query(None, ge=0),
    max_area: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: int = Depends(get_tenant_id),
):
    """List rooms with optional filters."""
    offset = (page - 1) * page_size

    query = """
        SELECT r.id, r.number, r.name, r.area_m2, r.height_m, r.volume_m3,
               f.name as floor_name, m.name as model_name
        FROM cadhub_room r
        JOIN cadhub_cad_model m ON r.cad_model_id = m.id
        JOIN cadhub_project p ON m.project_id = p.id
        LEFT JOIN cadhub_floor f ON r.floor_id = f.id
        WHERE p.tenant_id = $1
    """
    params = [tenant_id]
    param_idx = 2

    if model_id:
        query += f" AND r.cad_model_id = ${param_idx}"
        params.append(model_id)
        param_idx += 1
    if floor_id:
        query += f" AND r.floor_id = ${param_idx}"
        params.append(floor_id)
        param_idx += 1
    if min_area:
        query += f" AND r.area_m2 >= ${param_idx}"
        params.append(min_area)
        param_idx += 1
    if max_area:
        query += f" AND r.area_m2 <= ${param_idx}"
        params.append(max_area)
        param_idx += 1

    query += f" ORDER BY r.number LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([page_size, offset])

    rows = await fetch_all(query, *params)

    items = [
        RoomResponse(
            id=r["id"],
            number=r["number"],
            name=r["name"],
            area_m2=float(r["area_m2"]),
            height_m=float(r["height_m"]),
            volume_m3=float(r["volume_m3"]),
            floor_name=r["floor_name"],
            model_name=r["model_name"],
        )
        for r in rows
    ]

    return RoomListResponse(
        items=items,
        total=len(items),
        page=page,
        page_size=page_size,
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get a room by ID."""
    raise HTTPException(status_code=404, detail="Room not found")


@router.get("/by-floor/{floor_id}", response_model=RoomListResponse)
async def get_rooms_by_floor(
    floor_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get all rooms on a specific floor."""
    return RoomListResponse(
        items=[],
        total=0,
        total_area=0.0,
        total_volume=0.0,
    )
