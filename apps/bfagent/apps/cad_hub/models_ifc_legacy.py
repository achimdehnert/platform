# apps/cad_hub/models.py
"""
IFC Dashboard Models
"""
import uuid

from django.conf import settings
from django.db import models


class IFCProject(models.Model):
    """IFC Project - UI Cache Only

    IMPORTANT: This is NOT the source of truth!
    Real data lives in IFC MCP Backend (PostgreSQL).
    This model only caches data for UI performance.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Same UUID as IFC MCP Backend",
    )

    # Basic info (cached from IFC MCP)
    name = models.CharField(max_length=255, verbose_name="Projektname")

    # IFC MCP Backend reference
    mcp_project_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="IFC MCP Projekt-ID",
        help_text="Reference to IFC MCP Backend",
    )

    # Cached data from IFC MCP
    cached_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Cached Project Data",
        help_text="Cached data from IFC MCP API",
    )
    cached_at = models.DateTimeField(null=True, blank=True, verbose_name="Cache Timestamp")

    # UI-only fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="UI User",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "IFC Projekt (Cache)"
        verbose_name_plural = "IFC Projekte (Cache)"
        # managed = False  # Optional: Don't create migrations

    def __str__(self):
        return self.name

    @property
    def is_cache_valid(self):
        """Check if cache is still valid (< 1 hour)"""
        if not self.cached_at:
            return False
        from datetime import timedelta

        from django.utils import timezone

        return timezone.now() - self.cached_at < timedelta(hours=1)


class IFCModel(models.Model):
    """Eine Version eines IFC-Modells"""

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Wird hochgeladen"
        PROCESSING = "processing", "Wird verarbeitet"
        READY = "ready", "Bereit"
        ERROR = "error", "Fehler"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        IFCProject, on_delete=models.CASCADE, related_name="models", verbose_name="Projekt"
    )
    version = models.PositiveIntegerField(default=1, verbose_name="Version")

    # Files
    ifc_file = models.FileField(upload_to="ifc_models/%Y/%m/", verbose_name="IFC Datei")
    xkt_file = models.FileField(
        upload_to="ifc_models/%Y/%m/", blank=True, verbose_name="XKT Datei (3D Viewer)"
    )

    # Metadata aus IFC
    ifc_schema = models.CharField(max_length=20, blank=True, verbose_name="IFC Schema")
    application = models.CharField(max_length=100, blank=True, verbose_name="Erstellungs-Software")

    # Status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING, verbose_name="Status"
    )
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version"]
        unique_together = ["project", "version"]
        verbose_name = "IFC Modell"
        verbose_name_plural = "IFC Modelle"

    def __str__(self):
        return f"{self.project.name} v{self.version}"


class Floor(models.Model):
    """Geschoss (IfcBuildingStorey)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="floors", verbose_name="IFC Modell"
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Daten
    name = models.CharField(max_length=100, verbose_name="Name")
    code = models.CharField(max_length=20, blank=True, verbose_name="Kurzbezeichnung")
    elevation = models.FloatField(default=0, verbose_name="Höhe (m)")

    # Sortierung
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "elevation"]
        verbose_name = "Geschoss"
        verbose_name_plural = "Geschosse"

    def __str__(self):
        return f"{self.name} ({self.elevation:+.2f}m)"


class Room(models.Model):
    """Raum (IfcSpace)"""

    class UsageCategory(models.TextChoices):
        """DIN 277 Nutzungskategorien"""

        NF1_1 = "NF1.1", "NF 1.1 - Wohnen/Aufenthalt"
        NF1_2 = "NF1.2", "NF 1.2 - Büroarbeit"
        NF1_3 = "NF1.3", "NF 1.3 - Produktion"
        NF2 = "NF2", "NF 2 - Büroflächen"
        NF3 = "NF3", "NF 3 - Lager/Verteilen"
        NF4 = "NF4", "NF 4 - Bildung/Kultur"
        NF5 = "NF5", "NF 5 - Heilen/Pflegen"
        NF6 = "NF6", "NF 6 - Sonstige"
        TF7 = "TF7", "TF 7 - Technikflächen"
        VF8 = "VF8", "VF 8 - Verkehrsflächen"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="rooms", verbose_name="IFC Modell"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="rooms",
        null=True,
        blank=True,
        verbose_name="Geschoss",
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Stammdaten
    number = models.CharField(max_length=20, verbose_name="Raumnummer")
    name = models.CharField(max_length=100, verbose_name="Raumname")
    long_name = models.CharField(max_length=255, blank=True, verbose_name="Langname")

    # Geometrie (aus IFC BaseQuantities)
    area = models.FloatField(default=0, verbose_name="Fläche (m²)")
    height = models.FloatField(default=0, verbose_name="Höhe (m)")
    volume = models.FloatField(default=0, verbose_name="Volumen (m³)")
    perimeter = models.FloatField(default=0, verbose_name="Umfang (m)")

    # DIN 277 Klassifizierung
    usage_category = models.CharField(
        max_length=10,
        choices=UsageCategory.choices,
        blank=True,
        verbose_name="Nutzungsart (DIN 277)",
    )

    class Meta:
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Raum"
        verbose_name_plural = "Räume"

    def __str__(self):
        return f"{self.number} - {self.name}"


class Window(models.Model):
    """Fenster (IfcWindow)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="windows", verbose_name="IFC Modell"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="windows",
        verbose_name="Geschoss",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="windows",
        verbose_name="Raum",
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Stammdaten
    number = models.CharField(max_length=50, blank=True, verbose_name="Nummer")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    # Geometrie
    width = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Breite (m)"
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Höhe (m)"
    )
    area = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fläche (m²)"
    )

    # Position
    wall_position = models.CharField(max_length=50, blank=True, verbose_name="Wandposition")
    elevation = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Höhe (m)"
    )

    # Eigenschaften
    material = models.CharField(max_length=100, blank=True, verbose_name="Material")
    glazing_type = models.CharField(max_length=100, blank=True, verbose_name="Verglasungstyp")
    u_value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="U-Wert (W/m²K)"
    )

    # ALLE IFC Properties (ArchiCAD Properties, Pset_WindowCommon, etc.)
    properties = models.JSONField(default=dict, blank=True, verbose_name="IFC Properties")

    class Meta:
        db_table = "cad_hub_window"
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Fenster"
        verbose_name_plural = "Fenster"

    def __str__(self):
        return f"{self.number or self.name or self.ifc_guid[:8]}"


class Door(models.Model):
    """Tür (IfcDoor)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="doors", verbose_name="IFC Modell"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors",
        verbose_name="Geschoss",
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors_from",
        verbose_name="Von Raum",
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors_to",
        verbose_name="Nach Raum",
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Stammdaten
    number = models.CharField(max_length=50, blank=True, verbose_name="Nummer")
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    # Geometrie
    width = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Breite (m)"
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Höhe (m)"
    )

    # Eigenschaften
    door_type = models.CharField(max_length=50, blank=True, verbose_name="Türtyp")
    material = models.CharField(max_length=100, blank=True, verbose_name="Material")
    fire_rating = models.CharField(max_length=20, blank=True, verbose_name="Feuerwiderstand")

    # ALLE IFC Properties
    properties = models.JSONField(default=dict, blank=True, verbose_name="IFC Properties")

    class Meta:
        db_table = "cad_hub_door"
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Tür"
        verbose_name_plural = "Türen"

    def __str__(self):
        return f"{self.number or self.name or self.ifc_guid[:8]}"


class Wall(models.Model):
    """Wand (IfcWall)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="walls", verbose_name="IFC Modell"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="walls",
        verbose_name="Geschoss",
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Stammdaten
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")

    # Geometrie
    length = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Länge (m)"
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Höhe (m)"
    )
    width = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Dicke (m)"
    )
    gross_area = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Bruttofläche (m²)"
    )
    net_area = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Nettofläche (m²)"
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Volumen (m³)"
    )

    # Eigenschaften
    is_external = models.BooleanField(default=False, verbose_name="Außenwand")
    is_load_bearing = models.BooleanField(default=False, verbose_name="Tragend")
    material = models.CharField(max_length=100, blank=True, verbose_name="Material")

    # ALLE IFC Properties
    properties = models.JSONField(default=dict, blank=True, verbose_name="IFC Properties")

    class Meta:
        db_table = "cad_hub_wall"
        ordering = ["floor__sort_order", "name"]
        verbose_name = "Wand"
        verbose_name_plural = "Wände"

    def __str__(self):
        wall_type = "Außenwand" if self.is_external else "Innenwand"
        return f"{wall_type} - {self.name or self.ifc_guid[:8]}"


class Slab(models.Model):
    """Decke/Bodenplatte (IfcSlab)"""

    class SlabType(models.TextChoices):
        FLOOR = "FLOOR", "Geschossdecke"
        ROOF = "ROOF", "Dach"
        BASESLAB = "BASESLAB", "Bodenplatte"
        LANDING = "LANDING", "Podest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ifc_model = models.ForeignKey(
        IFCModel, on_delete=models.CASCADE, related_name="slabs", verbose_name="IFC Modell"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slabs",
        verbose_name="Geschoss",
    )

    # IFC Referenz
    ifc_guid = models.CharField(max_length=36, verbose_name="IFC GUID")

    # Stammdaten
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")
    slab_type = models.CharField(
        max_length=20, choices=SlabType.choices, default=SlabType.FLOOR, verbose_name="Typ"
    )

    # Geometrie
    area = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Fläche (m²)"
    )
    thickness = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Dicke (m)"
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Volumen (m³)"
    )
    perimeter = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Umfang (m)"
    )

    # Eigenschaften
    material = models.CharField(max_length=100, blank=True, verbose_name="Material")

    # ALLE IFC Properties
    properties = models.JSONField(default=dict, blank=True, verbose_name="IFC Properties")

    class Meta:
        db_table = "cad_hub_slab"
        ordering = ["floor__sort_order", "slab_type", "name"]
        verbose_name = "Decke/Platte"
        verbose_name_plural = "Decken/Platten"

    def __str__(self):
        return f"{self.get_slab_type_display()} - {self.name or self.ifc_guid[:8]}"


# Import AVB Models (Ausschreibung, Vergabe, Bauausführung)
from .models_avb import (
    Award,
    Bid,
    Bidder,
    BidPosition,
    BidStatus,
    ConstructionProject,
    CostEstimate,
    CostGroup,
    ProjectMilestone,
    ProjectPhase,
    Tender,
    TenderGroup,
    TenderPosition,
    TenderStatus,
)

__all__ = [
    # IFC Models
    "IFCProject",
    "IFCModel",
    "Floor",
    "Room",
    "Window",
    "Door",
    "Wall",
    "Slab",
    # AVB Models
    "ConstructionProject",
    "ProjectMilestone",
    "CostEstimate",
    "CostGroup",
    "ProjectPhase",
    "Tender",
    "TenderPosition",
    "TenderGroup",
    "TenderStatus",
    "Bidder",
    "Bid",
    "BidPosition",
    "BidStatus",
    "Award",
]
