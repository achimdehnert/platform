"""
Calculation Schemas (DIN 277, WoFlV)
ADR-009: Pydantic models with strict validation
"""

from pydantic import BaseModel, ConfigDict, Field


class DIN277Request(BaseModel):
    """Request for DIN 277 calculation."""

    model_id: int


class DIN277CategoryResult(BaseModel):
    """DIN 277 category result."""

    din_code: str
    name: str
    room_count: int
    area: float = Field(description="Area in m²")


class DIN277Response(BaseModel):
    """Response for DIN 277 calculation."""

    model_config = ConfigDict(from_attributes=True)

    model_id: int
    nuf_total: float = Field(description="Nutzungsfläche (NUF) in m²")
    tf_total: float = Field(description="Technische Funktionsfläche (TF) in m²")
    vf_total: float = Field(description="Verkehrsfläche (VF) in m²")
    ngf_total: float = Field(description="Netto-Grundfläche (NGF) in m²")
    bgf_total: float = Field(description="Brutto-Grundfläche (BGF) in m²")
    categories: list[DIN277CategoryResult]


class WoFlVRequest(BaseModel):
    """Request for WoFlV calculation."""

    model_id: int


class WoFlVRoomResult(BaseModel):
    """WoFlV room result."""

    room_number: str
    room_name: str
    grundflaeche: float = Field(description="Grundfläche in m²")
    factor: float = Field(description="Anrechnungsfaktor (1.0, 0.5, 0.25)")
    wohnflaeche: float = Field(description="Angerechnete Wohnfläche in m²")


class WoFlVResponse(BaseModel):
    """Response for WoFlV calculation."""

    model_config = ConfigDict(from_attributes=True)

    model_id: int
    wohnflaeche_gesamt: float = Field(description="Gesamte Wohnfläche in m²")
    grundflaeche_gesamt: float = Field(description="Gesamte Grundfläche in m²")
    factor_100: float = Field(description="Fläche mit Faktor 1.0")
    factor_50: float = Field(description="Fläche mit Faktor 0.5")
    factor_25: float = Field(description="Fläche mit Faktor 0.25")
    rooms: list[WoFlVRoomResult]
