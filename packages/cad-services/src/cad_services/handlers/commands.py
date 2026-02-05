"""
Pydantic Command/Result Models.

Alle Commands und Results MÜSSEN Pydantic BaseModel verwenden.
Type Hints für alle Felder, Google-Style Docstrings.
"""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParseIFCCommand(BaseModel):
    """Command für IFC-Parsing.

    Attributes:
        file_path: Pfad zur IFC-Datei (absolut oder relativ).
        project_id: Ziel-Projekt für das Modell.
        tenant_id: Aktueller Tenant (aus Context).
        user_id: Ausführender Benutzer.

    Example:
        >>> cmd = ParseIFCCommand(
        ...     file_path="/data/model.ifc",
        ...     project_id=1,
        ...     tenant_id=1,
        ...     user_id=1,
        ... )
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )

    file_path: str = Field(..., min_length=1, max_length=500)
    project_id: int = Field(..., gt=0)
    tenant_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)

    @field_validator("file_path")
    @classmethod
    def validate_file_extension(cls, v: str) -> str:
        """Validiert IFC-Dateiendung."""
        if not v.lower().endswith(".ifc"):
            raise ValueError("Nur IFC-Dateien erlaubt")
        return v


class ParseIFCResult(BaseModel):
    """Result für IFC-Parsing.

    Attributes:
        model_id: ID des erstellten CAD-Modells.
        floor_count: Anzahl extrahierter Geschosse.
        room_count: Anzahl extrahierter Räume.
        window_count: Anzahl extrahierter Fenster.
        door_count: Anzahl extrahierter Türen.
        wall_count: Anzahl extrahierter Wände.
        slab_count: Anzahl extrahierter Decken.
        total_area_m2: Gesamtfläche aller Räume.
        total_volume_m3: Gesamtvolumen aller Räume.
        errors: Liste von Fehlern während des Parsings.
        warnings: Liste von Warnungen.
        processing_time_ms: Verarbeitungszeit in Millisekunden.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_id: int
    floor_count: int = Field(..., ge=0)
    room_count: int = Field(..., ge=0)
    window_count: int = Field(..., ge=0)
    door_count: int = Field(..., ge=0)
    wall_count: int = Field(..., ge=0)
    slab_count: int = Field(..., ge=0)
    total_area_m2: Decimal = Field(..., ge=0)
    total_volume_m3: Decimal = Field(..., ge=0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_time_ms: int = Field(..., ge=0)


class ListRoomsCommand(BaseModel):
    """Command für Raumliste.

    Attributes:
        model_id: CAD-Modell ID.
        floor_id: Optional Filter nach Geschoss.
        usage_category_id: Optional Filter nach DIN 277 Kategorie.
        tenant_id: Aktueller Tenant.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True)

    model_id: int = Field(..., gt=0)
    floor_id: int | None = Field(default=None, gt=0)
    usage_category_id: int | None = Field(default=None, gt=0)
    tenant_id: int = Field(..., gt=0)


class RoomDTO(BaseModel):
    """Data Transfer Object für Raum.

    Attributes:
        id: Raum-ID.
        number: Raumnummer.
        name: Raumname.
        floor_name: Geschossname.
        area_m2: Fläche in m².
        height_m: Höhe in m.
        volume_m3: Volumen in m³.
        usage_category: DIN 277 Kategorie.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: int
    number: str
    name: str
    floor_name: str | None = None
    area_m2: Decimal
    height_m: Decimal
    volume_m3: Decimal
    usage_category: str | None = None


class ListRoomsResult(BaseModel):
    """Result für Raumliste.

    Attributes:
        rooms: Liste der Räume.
        total_count: Gesamtanzahl.
        total_area_m2: Gesamtfläche.
        total_volume_m3: Gesamtvolumen.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    rooms: list[RoomDTO]
    total_count: int = Field(..., ge=0)
    total_area_m2: Decimal = Field(..., ge=0)
    total_volume_m3: Decimal = Field(..., ge=0)


class ListWindowsCommand(BaseModel):
    """Command für Fensterliste.

    Attributes:
        model_id: CAD-Modell ID.
        floor_id: Optional Filter nach Geschoss.
        tenant_id: Aktueller Tenant.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True)

    model_id: int = Field(..., gt=0)
    floor_id: int | None = Field(default=None, gt=0)
    tenant_id: int = Field(..., gt=0)


class WindowDTO(BaseModel):
    """Data Transfer Object für Fenster.

    Attributes:
        id: Fenster-ID.
        number: Fensternummer.
        name: Fenstername.
        floor_name: Geschossname.
        width_m: Breite in m.
        height_m: Höhe in m.
        area_m2: Fläche in m².
        u_value_w_m2k: U-Wert in W/(m²·K).
        material: Material.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: int
    number: str | None = None
    name: str | None = None
    floor_name: str | None = None
    width_m: Decimal | None = None
    height_m: Decimal | None = None
    area_m2: Decimal | None = None
    u_value_w_m2k: Decimal | None = None
    material: str | None = None


class ListWindowsResult(BaseModel):
    """Result für Fensterliste.

    Attributes:
        windows: Liste der Fenster.
        total_count: Gesamtanzahl.
        total_area_m2: Gesamtfläche.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    windows: list[WindowDTO]
    total_count: int = Field(..., ge=0)
    total_area_m2: Decimal = Field(..., ge=0)


class CalculateDIN277Command(BaseModel):
    """Command für DIN 277 Berechnung.

    Attributes:
        model_id: CAD-Modell ID.
        tenant_id: Aktueller Tenant.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True)

    model_id: int = Field(..., gt=0)
    tenant_id: int = Field(..., gt=0)


class CalculateDIN277Result(BaseModel):
    """Result für DIN 277 Flächenberechnung.

    Attributes:
        bgf: Brutto-Grundfläche in m².
        kgf: Konstruktions-Grundfläche in m².
        nrf: Netto-Raumfläche in m².
        nf1: Nutzfläche 1 (Wohnen/Aufenthalt) in m².
        nf2: Nutzfläche 2 (Büroarbeit) in m².
        nf3: Nutzfläche 3 (Lager/Verteilen) in m².
        nf4: Nutzfläche 4 (Bildung/Kultur) in m².
        nf5: Nutzfläche 5 (Heilen/Pflegen) in m².
        nf6: Nutzfläche 6 (Sonstige) in m².
        tf7: Technikflächen in m².
        vf8: Verkehrsflächen in m².
        bri: Brutto-Rauminhalt (umbauter Raum) in m³.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    bgf: Decimal = Field(..., ge=0)
    kgf: Decimal = Field(..., ge=0)
    nrf: Decimal = Field(..., ge=0)
    nf1: Decimal = Field(default=Decimal("0"), ge=0)
    nf2: Decimal = Field(default=Decimal("0"), ge=0)
    nf3: Decimal = Field(default=Decimal("0"), ge=0)
    nf4: Decimal = Field(default=Decimal("0"), ge=0)
    nf5: Decimal = Field(default=Decimal("0"), ge=0)
    nf6: Decimal = Field(default=Decimal("0"), ge=0)
    tf7: Decimal = Field(default=Decimal("0"), ge=0)
    vf8: Decimal = Field(default=Decimal("0"), ge=0)
    bri: Decimal = Field(..., ge=0)


class CalculateWoFlVCommand(BaseModel):
    """Command für WoFlV Berechnung.

    Attributes:
        model_id: CAD-Modell ID.
        tenant_id: Aktueller Tenant.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True)

    model_id: int = Field(..., gt=0)
    tenant_id: int = Field(..., gt=0)


class CalculateWoFlVResult(BaseModel):
    """Result für WoFlV Wohnflächenberechnung.

    Attributes:
        grundflaeche_gesamt: Grundfläche gesamt in m².
        wohnflaeche_gesamt: Wohnfläche gesamt in m².
        wohnflaeche_100: Fläche mit 100% Anrechnung in m².
        wohnflaeche_50: Fläche mit 50% Anrechnung in m².
        wohnflaeche_25: Fläche mit 25% Anrechnung in m².
        nicht_angerechnet: Nicht angerechnete Fläche in m².
        anrechnungsquote: Anrechnungsquote in Prozent.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    grundflaeche_gesamt: Decimal = Field(..., ge=0)
    wohnflaeche_gesamt: Decimal = Field(..., ge=0)
    wohnflaeche_100: Decimal = Field(default=Decimal("0"), ge=0)
    wohnflaeche_50: Decimal = Field(default=Decimal("0"), ge=0)
    wohnflaeche_25: Decimal = Field(default=Decimal("0"), ge=0)
    nicht_angerechnet: Decimal = Field(default=Decimal("0"), ge=0)
    anrechnungsquote: Decimal = Field(..., ge=0, le=100)
