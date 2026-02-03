"""
Upload Router
ADR-009: IFC/DXF/CAD file upload and processing endpoints
"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from cad_services.api.database import execute, fetch_one


router = APIRouter()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/cadhub/uploads"))

SUPPORTED_FORMATS = {
    ".ifc": "ifc",
    ".ifczip": "ifc",
    ".dxf": "dxf",
    ".dwg": "dwg",
}


def get_tenant_id() -> int:
    """Get tenant ID from request context."""
    return 1


def get_user_id() -> int:
    """Get user ID from request context."""
    return 1


@router.post("/cad/{project_id}")
async def upload_cad_file(
    project_id: int,
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
):
    """
    Upload a CAD file (IFC, DXF, DWG) for a project.

    Supported formats: .ifc, .ifczip, .dxf, .dwg
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            400,
            f"Unsupported format: {ext}. Use: {list(SUPPORTED_FORMATS.keys())}",
        )

    project = await fetch_one(
        "SELECT id FROM cadhub_project WHERE id = $1 AND tenant_id = $2",
        project_id,
        tenant_id,
    )
    if not project:
        raise HTTPException(404, "Project not found")

    upload_path = UPLOAD_DIR / str(tenant_id) / str(project_id)
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    result = await fetch_one(
        """
        INSERT INTO cadhub_cad_model
            (project_id, name, source_file_path, file_size_bytes,
             source_format, status, created_by_id, created_at)
        VALUES ($1, $2, $3, $4, $5, 'pending', $6, NOW())
        RETURNING id
        """,
        project_id,
        file.filename,
        str(file_path),
        len(content),
        SUPPORTED_FORMATS[ext],
        user_id,
    )

    return {
        "model_id": result["id"],
        "filename": file.filename,
        "format": SUPPORTED_FORMATS[ext],
        "size_bytes": len(content),
        "status": "pending",
        "message": "File uploaded. Processing will start shortly.",
    }


@router.post("/ifc/{project_id}")
async def upload_ifc(
    project_id: int,
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_tenant_id),
    user_id: int = Depends(get_user_id),
):
    """Upload an IFC file (legacy endpoint, use /cad/{project_id})."""
    return await upload_cad_file(project_id, file, tenant_id, user_id)


@router.post("/process/{model_id}")
async def process_model(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Process an uploaded CAD model.

    Extracts floors, rooms, walls, doors, windows from IFC/DXF files.
    """
    model = await fetch_one(
        """
        SELECT m.id, m.source_file_path, m.source_format, m.status,
               p.tenant_id
        FROM cadhub_cad_model m
        JOIN cadhub_project p ON m.project_id = p.id
        WHERE m.id = $1 AND p.tenant_id = $2
        """,
        model_id,
        tenant_id,
    )
    if not model:
        raise HTTPException(404, "Model not found")

    if model["status"] == "ready":
        return {"status": "already_processed", "model_id": model_id}

    file_path = Path(model["source_file_path"])
    if not file_path.exists():
        raise HTTPException(404, "Source file not found")

    # Update status to processing
    await execute(
        "UPDATE cadhub_cad_model SET status = 'processing' WHERE id = $1",
        model_id,
    )

    source_format = model["source_format"]

    try:
        if source_format == "ifc":
            result = await _process_ifc(model_id, file_path)
        elif source_format == "dxf":
            result = await _process_dxf(model_id, file_path)
        else:
            raise HTTPException(400, f"Processing not supported: {source_format}")

        # Update status to ready
        await execute(
            """
            UPDATE cadhub_cad_model
            SET status = 'ready', processed_at = NOW()
            WHERE id = $1
            """,
            model_id,
        )

        return {
            "status": "success",
            "model_id": model_id,
            **result,
        }

    except Exception as e:
        # Update status to error
        await execute(
            """
            UPDATE cadhub_cad_model
            SET status = 'error', error_message = $2
            WHERE id = $1
            """,
            model_id,
            str(e),
        )
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e


async def _process_ifc(model_id: int, file_path: Path) -> dict:
    """Process IFC file and store extracted elements."""
    from cad_services.services.ifc_service import IFCService

    service = IFCService()
    result = service.parse_file(file_path)

    if result.errors:
        raise ValueError("; ".join(result.errors))

    # Store floors
    floor_map = {}
    for floor in result.floors:
        row = await fetch_one(
            """
            INSERT INTO cadhub_floor
                (cad_model_id, ifc_guid, name, code, elevation_m, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            model_id,
            floor.ifc_guid,
            floor.name,
            floor.code,
            float(floor.elevation_m),
            floor.sort_order,
        )
        floor_map[floor.ifc_guid] = row["id"]

    # Store rooms
    for room in result.rooms:
        floor_id = floor_map.get(room.floor_guid) if room.floor_guid else None
        await execute(
            """
            INSERT INTO cadhub_room
                (cad_model_id, floor_id, ifc_guid, number, name, long_name,
                 area_m2, height_m, volume_m3, perimeter_m)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            model_id,
            floor_id,
            room.ifc_guid,
            room.number,
            room.name,
            room.long_name,
            float(room.area_m2),
            float(room.height_m),
            float(room.volume_m3),
            float(room.perimeter_m),
        )

    # Store walls
    for wall in result.walls:
        floor_id = floor_map.get(wall.floor_guid) if wall.floor_guid else None
        await execute(
            """
            INSERT INTO cadhub_wall
                (cad_model_id, floor_id, ifc_guid, name,
                 length_m, height_m, thickness_m, area_m2, is_external)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            model_id,
            floor_id,
            wall.ifc_guid,
            wall.name,
            float(wall.length_m),
            float(wall.height_m),
            float(wall.thickness_m),
            float(wall.area_m2),
            wall.is_external,
        )

    # Store doors
    for door in result.doors:
        floor_id = floor_map.get(door.floor_guid) if door.floor_guid else None
        await execute(
            """
            INSERT INTO cadhub_door
                (cad_model_id, floor_id, ifc_guid, name, width_m, height_m)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            model_id,
            floor_id,
            door.ifc_guid,
            door.name,
            float(door.width_m),
            float(door.height_m),
        )

    # Store windows
    for window in result.windows:
        floor_id = floor_map.get(window.floor_guid) if window.floor_guid else None
        await execute(
            """
            INSERT INTO cadhub_window
                (cad_model_id, floor_id, ifc_guid, name,
                 width_m, height_m, area_m2)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            model_id,
            floor_id,
            window.ifc_guid,
            window.name,
            float(window.width_m),
            float(window.height_m),
            float(window.area_m2),
        )

    # Store slabs
    for slab in result.slabs:
        floor_id = floor_map.get(slab.floor_guid) if slab.floor_guid else None
        await execute(
            """
            INSERT INTO cadhub_slab
                (cad_model_id, floor_id, ifc_guid, name,
                 area_m2, thickness_m, is_floor)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            model_id,
            floor_id,
            slab.ifc_guid,
            slab.name,
            float(slab.area_m2),
            float(slab.thickness_m),
            slab.is_floor,
        )

    return {
        "format": "ifc",
        "schema": result.ifc_schema,
        "floors": len(result.floors),
        "rooms": len(result.rooms),
        "walls": len(result.walls),
        "doors": len(result.doors),
        "windows": len(result.windows),
        "slabs": len(result.slabs),
        "total_area_m2": float(result.total_area),
        "total_volume_m3": float(result.total_volume),
    }


async def _process_dxf(model_id: int, file_path: Path) -> dict:
    """Process DXF file and store extracted elements."""
    from cad_services.services.dxf_service import DXFService

    service = DXFService()
    result = service.parse_file(file_path)

    if result.errors:
        raise ValueError("; ".join(result.errors))

    # Store rooms extracted from DXF polylines
    import uuid

    for room in result.rooms:
        await execute(
            """
            INSERT INTO cadhub_room
                (cad_model_id, ifc_guid, number, name, area_m2, perimeter_m,
                 height_m, volume_m3)
            VALUES ($1, $2, $3, $4, $5, $6, 0, 0)
            """,
            model_id,
            str(uuid.uuid4())[:36],
            room.number or f"R{result.rooms.index(room) + 1}",
            room.name or room.layer,
            float(room.area_m2),
            float(room.perimeter_m),
        )

    return {
        "format": "dxf",
        "layers": len(result.layers),
        "rooms": len(result.rooms),
        "blocks": len(result.blocks),
        "texts": len(result.texts),
        "total_area_m2": float(result.total_area),
    }
