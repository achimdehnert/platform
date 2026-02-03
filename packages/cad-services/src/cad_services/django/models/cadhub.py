"""
CAD-Hub Models
ADR-009: Database-driven, normalized, FK integers
Table naming: cadhub_{entity}
No JSONB for critical properties - use cadhub_element_property
"""

from django.db import models


class Unit(models.Model):
    """Measurement units - database-driven."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    unit_type = models.CharField(max_length=50)
    si_factor = models.DecimalField(max_digits=20, decimal_places=10, default=1)

    class Meta:
        db_table = "cadhub_unit"
        ordering = ["unit_type", "code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class UsageCategory(models.Model):
    """DIN 277 usage categories - database-driven."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    din_category = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "cadhub_usage_category"
        managed = False
        ordering = ["code"]
        verbose_name = "Usage Category (DIN 277)"
        verbose_name_plural = "Usage Categories (DIN 277)"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class PropertyDefinition(models.Model):
    """Property definitions - database-driven, not hardcoded."""

    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=20)
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_definitions",
    )
    is_required = models.BooleanField(default=False)
    default_value = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "cadhub_property_definition"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name


class Project(models.Model):
    """CAD Project - tenant-scoped."""

    tenant_id = models.IntegerField(db_column="tenant_id")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(db_column="created_by_id")

    class Meta:
        db_table = "cadhub_project"
        managed = False
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def model_count(self) -> int:
        return self.models.count()


class CADModel(models.Model):
    """CAD Model (IFC/DXF file) - matches cadhub_cad_model table."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("error", "Error"),
    ]

    SOURCE_FORMAT_CHOICES = [
        ("ifc", "IFC"),
        ("dxf", "DXF"),
        ("dwg", "DWG"),
        ("step", "STEP"),
        ("stl", "STL"),
        ("fbx", "FBX"),
        ("gltf", "GLTF"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="cad_models",
        db_column="project_id",
    )
    version = models.IntegerField(default=1)
    name = models.CharField(max_length=255)
    source_file_path = models.CharField(max_length=500, null=True, blank=True)
    source_format = models.CharField(max_length=20)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    ifc_schema = models.CharField(max_length=20, null=True, blank=True)
    ifc_application = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_by_id = models.IntegerField(db_column="created_by_id")

    class Meta:
        db_table = "cadhub_cad_model"
        managed = False
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size_bytes / (1024 * 1024), 2)


class Floor(models.Model):
    """Building floor/storey - matches cadhub_floor table."""

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="floors",
        db_column="cad_model_id",
    )
    ifc_guid = models.CharField(max_length=36)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)
    elevation_m = models.DecimalField(
        max_digits=10, decimal_places=3, default=0, db_column="elevation_m"
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "cadhub_floor"
        managed = False
        ordering = ["cad_model", "sort_order"]

    def __str__(self) -> str:
        return f"{self.name} ({self.elevation_m}m)"


class Room(models.Model):
    """Room/Space with DIN 277 classification - matches cadhub_room."""

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="rooms",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rooms",
        db_column="floor_id",
    )
    ifc_guid = models.CharField(max_length=36)
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    long_name = models.CharField(max_length=255, blank=True, null=True)
    area_m2 = models.DecimalField(max_digits=12, decimal_places=3, default=0, db_column="area_m2")
    height_m = models.DecimalField(max_digits=10, decimal_places=3, default=0, db_column="height_m")
    volume_m3 = models.DecimalField(
        max_digits=12, decimal_places=3, default=0, db_column="volume_m3"
    )
    perimeter_m = models.DecimalField(
        max_digits=12, decimal_places=3, default=0, db_column="perimeter_m"
    )
    usage_category = models.ForeignKey(
        UsageCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rooms",
        db_column="usage_category_id",
    )

    class Meta:
        db_table = "cadhub_room"
        managed = False
        ordering = ["floor", "number"]

    def __str__(self) -> str:
        return f"{self.number} - {self.name}"

    @property
    def woflv_area(self) -> float:
        return float(self.area_m2)


class Window(models.Model):
    """Window element."""

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="windows",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="windows",
    )
    ifc_guid = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    width = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    height = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    area = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    u_value = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    material = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "cadhub_window"
        managed = False
        ordering = ["floor", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.width}x{self.height})"


class Door(models.Model):
    """Door element."""

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="doors",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors",
    )
    ifc_guid = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    width = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    height = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    area = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    material = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "cadhub_door"
        managed = False
        ordering = ["floor", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.width}x{self.height})"


class Wall(models.Model):
    """Wall element."""

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="walls",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="walls",
    )
    ifc_guid = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    length = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    height = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    thickness = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    area = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    is_external = models.BooleanField(default=False)

    class Meta:
        db_table = "cadhub_wall"
        managed = False
        ordering = ["floor", "name"]

    def __str__(self) -> str:
        ext = "External" if self.is_external else "Internal"
        return f"{self.name} ({ext})"


class Slab(models.Model):
    """Slab/floor element."""

    SLAB_TYPE_CHOICES = [
        ("floor", "Floor"),
        ("ceiling", "Ceiling"),
        ("roof", "Roof"),
    ]

    cad_model = models.ForeignKey(
        CADModel,
        on_delete=models.CASCADE,
        related_name="slabs",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slabs",
    )
    ifc_guid = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    area = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    thickness = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    volume = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    slab_type = models.CharField(
        max_length=20,
        choices=SLAB_TYPE_CHOICES,
        default="floor",
    )

    class Meta:
        db_table = "cadhub_slab"
        managed = False
        ordering = ["floor", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.slab_type})"


class ElementProperty(models.Model):
    """
    Normalized element properties.
    Replaces JSONB for critical data - ADR-009 compliant.
    """

    ELEMENT_TYPE_CHOICES = [
        ("room", "Room"),
        ("window", "Window"),
        ("door", "Door"),
        ("wall", "Wall"),
        ("slab", "Slab"),
    ]

    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPE_CHOICES)
    element_id = models.IntegerField()
    property_def = models.ForeignKey(
        PropertyDefinition,
        on_delete=models.CASCADE,
        related_name="element_properties",
    )
    value_text = models.CharField(max_length=1024, blank=True)
    value_numeric = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )
    value_boolean = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "cadhub_element_property"
        unique_together = [["element_type", "element_id", "property_def"]]

    def __str__(self) -> str:
        return f"{self.element_type}:{self.element_id} - {self.property_def.name}"

    @property
    def value(self):
        if self.value_numeric is not None:
            return self.value_numeric
        if self.value_boolean is not None:
            return self.value_boolean
        return self.value_text
