"""
Projects Router
ADR-009: API endpoints for Project management
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from cad_services.api.database import fetch_all, fetch_one
from cad_services.api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)


router = APIRouter()


def get_tenant_id() -> int:
    """Get tenant ID from request context (placeholder)."""
    return 1


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: str | None = Query(None, pattern="^(active|archived)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int = Depends(get_tenant_id),
):
    """List all projects for the current tenant."""
    offset = (page - 1) * page_size

    rows = await fetch_all(
        """
        SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
               t.name as tenant_name,
               (SELECT COUNT(*) FROM cadhub_cad_model m WHERE m.project_id = p.id) as model_count
        FROM cadhub_project p
        JOIN core_tenant t ON p.tenant_id = t.id
        WHERE p.tenant_id = $1
        ORDER BY p.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        tenant_id,
        page_size,
        offset,
    )

    total_row = await fetch_one(
        "SELECT COUNT(*) as cnt FROM cadhub_project WHERE tenant_id = $1", tenant_id
    )
    total = total_row["cnt"] if total_row else 0

    items = [
        ProjectResponse(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            model_count=r["model_count"],
        )
        for r in rows
    ]

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    tenant_id: int = Depends(get_tenant_id),
):
    """Create a new project."""
    # Placeholder - will be connected to repository
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Get a project by ID."""
    # Placeholder - will be connected to repository
    raise HTTPException(status_code=404, detail="Project not found")


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    tenant_id: int = Depends(get_tenant_id),
):
    """Update a project."""
    # Placeholder - will be connected to repository
    raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Delete (archive) a project."""
    # Placeholder - will be connected to repository
    raise HTTPException(status_code=404, detail="Project not found")
