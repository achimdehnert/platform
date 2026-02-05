"""
Windows Router
ADR-009: API endpoints for Window queries (Fensterliste)
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from cad_services.api.schemas.window import WindowListResponse, WindowResponse


router = APIRouter()


def get_tenant_id() -> int:
    """Get tenant ID from request context (placeholder)."""
    return 1


@router.get("", response_model=WindowListResponse)
async def list_windows(
    model_id: int = Query(..., description="Model ID to query windows from"),
    floor_id: int | None = Query(None),
    material: str | None = Query(None),
    min_area: float | None = Query(None, ge=0),
    max_area: float | None = Query(None, ge=0),
    tenant_id: int = Depends(get_tenant_id),
):
    """List all windows for a model (Fensterliste)."""
    # Placeholder - will be connected to repository
    return WindowListResponse(
        items=[],
        total=0,
        total_area=0.0,
    )


@router.get("/{window_id}", response_model=WindowResponse)
async def get_window(
    window_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get a window by ID."""
    raise HTTPException(status_code=404, detail="Window not found")


@router.get("/by-floor/{floor_id}", response_model=WindowListResponse)
async def get_windows_by_floor(
    floor_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get all windows on a specific floor."""
    return WindowListResponse(
        items=[],
        total=0,
        total_area=0.0,
    )


@router.get("/export/csv")
async def export_windows_csv(
    model_id: int = Query(...),
    tenant_id: int = Depends(get_tenant_id),
):
    """Export window list as CSV."""
    # Placeholder - will generate CSV
    return {"message": "CSV export not implemented"}
