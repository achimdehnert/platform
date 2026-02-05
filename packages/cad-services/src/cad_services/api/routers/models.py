"""
Models Router
ADR-009: API endpoints for CAD Model (IFC/DXF) management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from cad_services.api.schemas.model import (
    ModelResponse,
    ModelStatsResponse,
    ModelUploadResponse,
)


router = APIRouter()


def get_tenant_id() -> int:
    """Get tenant ID from request context (placeholder)."""
    return 1


@router.get("")
async def list_models(
    project_id: int | None = Query(None),
    parse_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int = Depends(get_tenant_id),
):
    """List all models, optionally filtered by project."""
    return {"items": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/upload", response_model=ModelUploadResponse, status_code=201)
async def upload_model(
    project_id: int,
    file: UploadFile,
    tenant_id: int = Depends(get_tenant_id),
):
    """Upload a new CAD model (IFC/DXF)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.lower().split(".")[-1]
    if ext not in ["ifc", "dxf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Supported: IFC, DXF",
        )

    # Placeholder - will save file and trigger parsing
    return ModelUploadResponse(
        id=1,
        name=file.filename,
        file_path=f"/uploads/{file.filename}",
        file_size_bytes=0,
        parse_status="pending",
        message="File uploaded, parsing queued",
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get a model by ID."""
    raise HTTPException(status_code=404, detail="Model not found")


@router.get("/{model_id}/stats", response_model=ModelStatsResponse)
async def get_model_stats(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get statistics for a parsed model."""
    raise HTTPException(status_code=404, detail="Model not found")


@router.post("/{model_id}/parse")
async def trigger_parse(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Trigger (re-)parsing of a model."""
    return {"status": "queued", "model_id": model_id}


@router.delete("/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Delete a model and its parsed data."""
    raise HTTPException(status_code=404, detail="Model not found")
