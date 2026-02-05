"""
Calculations Router
ADR-009: API endpoints for DIN 277 and WoFlV calculations
"""

from fastapi import APIRouter, Depends

from cad_services.api.database import fetch_all
from cad_services.api.schemas.calculation import (
    DIN277Request,
    DIN277Response,
    WoFlVRequest,
    WoFlVResponse,
)


router = APIRouter()


def get_tenant_id() -> int:
    """Get tenant ID from request context (placeholder)."""
    return 1


@router.post("/din277", response_model=DIN277Response)
async def calculate_din277(
    request: DIN277Request,
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Calculate DIN 277 area breakdown from real room data.
    """
    rooms = await fetch_all(
        """
        SELECT r.name, r.area_m2, uc.din_category
        FROM cadhub_room r
        LEFT JOIN cadhub_usage_category uc ON r.usage_category_id = uc.id
        WHERE r.cad_model_id = $1
        """,
        request.model_id,
    )

    nuf_total = sum(float(r["area_m2"]) for r in rooms if r["din_category"] in ("NF", None))
    tf_total = sum(float(r["area_m2"]) for r in rooms if r["din_category"] == "TF")
    vf_total = sum(float(r["area_m2"]) for r in rooms if r["din_category"] == "VF")
    ngf_total = nuf_total + tf_total + vf_total

    return DIN277Response(
        model_id=request.model_id,
        nuf_total=round(nuf_total, 2),
        tf_total=round(tf_total, 2),
        vf_total=round(vf_total, 2),
        ngf_total=round(ngf_total, 2),
        bgf_total=round(ngf_total * 1.15, 2),
        categories=[],
    )


@router.post("/woflv", response_model=WoFlVResponse)
async def calculate_woflv(
    request: WoFlVRequest,
    tenant_id: int = Depends(get_tenant_id),
):
    """
    Calculate WoFlV living area.

    Applies WoFlV factors:
    - 1.0: Standard living areas
    - 0.5: Balconies, terraces (covered)
    - 0.25: Balconies (uncovered), storage
    """
    # Placeholder - will be connected to calculation service
    return WoFlVResponse(
        model_id=request.model_id,
        wohnflaeche_gesamt=0.0,
        grundflaeche_gesamt=0.0,
        factor_100=0.0,
        factor_50=0.0,
        factor_25=0.0,
        rooms=[],
    )


@router.get("/din277/export/{model_id}")
async def export_din277_excel(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Export DIN 277 calculation as Excel."""
    return {"message": "Excel export not implemented"}


@router.get("/woflv/export/{model_id}")
async def export_woflv_excel(
    model_id: int,
    tenant_id: int = Depends(get_tenant_id),
):
    """Export WoFlV calculation as Excel."""
    return {"message": "Excel export not implemented"}
