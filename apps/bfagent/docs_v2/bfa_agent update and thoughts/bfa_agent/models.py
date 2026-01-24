"""Pydantic Models für strukturierte Agent-Outputs."""

from pydantic import BaseModel, Field
from enum import Enum


class ZoneType(str, Enum):
    """Ex-Zonen Typen nach ATEX/IECEx."""
    ZONE_0 = "Zone 0"
    ZONE_1 = "Zone 1"
    ZONE_2 = "Zone 2"
    ZONE_20 = "Zone 20"
    ZONE_21 = "Zone 21"
    ZONE_22 = "Zone 22"
    NONE = "Keine Ex-Zone"


class RiskLevel(str, Enum):
    """Risikostufen."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExZoneClassification(BaseModel):
    """Ergebnis einer Ex-Zonen Klassifizierung."""
    
    room_name: str = Field(description="Name des analysierten Raums")
    zone_type: ZoneType = Field(description="Klassifizierte Ex-Zone")
    zone_category: str = Field(description="'Gas' oder 'Staub'")
    risk_level: RiskLevel = Field(description="Risikobewertung")
    zone_extent_m: float | None = Field(default=None, description="Zonenausdehnung in Metern")
    justification: str = Field(description="Begründung mit Normbezug")
    recommendations: list[str] = Field(default_factory=list, description="Maßnahmenempfehlungen")


class EquipmentCheckResult(BaseModel):
    """Ergebnis einer Equipment-Prüfung."""
    
    equipment_name: str = Field(description="Name des Betriebsmittels")
    ex_marking: str | None = Field(default=None, description="Ex-Kennzeichnung")
    required_category: str = Field(description="Erforderliche Gerätekategorie")
    is_suitable: bool = Field(description="Für Zone geeignet?")
    issues: list[str] = Field(default_factory=list, description="Festgestellte Mängel")
    recommendations: list[str] = Field(default_factory=list, description="Empfehlungen")


class VentilationAnalysis(BaseModel):
    """Ergebnis einer Lüftungsanalyse."""
    
    room_name: str
    volume_m3: float
    air_changes_per_hour: float
    ventilation_type: str = Field(description="'natürlich', 'technisch', 'keine'")
    is_adequate: bool
    effectiveness: str = Field(description="'hoch', 'mittel', 'gering'")
    recommendation: str


class BFAReport(BaseModel):
    """Vollständiger BFA-Bericht."""
    
    title: str
    project_name: str
    date: str
    zones: list[ExZoneClassification]
    equipment_checks: list[EquipmentCheckResult]
    ventilation: list[VentilationAnalysis]
    summary: str
    overall_risk: RiskLevel
    action_items: list[str]
