"""
Fire Safety Django Models
ADR-009: Database-driven fire safety analysis
Tables: cadhub_fire_compartment, cadhub_fire_rated_element, cadhub_escape_route
"""

from django.db import models


class FireRatingRef(models.Model):
    """Reference data: Fire rating classifications."""

    code = models.CharField(max_length=20, primary_key=True)
    standard = models.CharField(max_length=20)  # din4102, en13501
    minutes = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    element_types = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "cadhub_fire_rating_ref"
        managed = False
        verbose_name = "Feuerwiderstandsklasse"
        verbose_name_plural = "Feuerwiderstandsklassen"

    def __str__(self) -> str:
        return f"{self.code} ({self.standard})"


class EscapeParamsRef(models.Model):
    """Reference data: Escape route parameters by building type."""

    building_type = models.CharField(max_length=50, primary_key=True)
    max_distance_m = models.DecimalField(max_digits=8, decimal_places=2)
    max_distance_sprinkler_m = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    min_door_width_m = models.DecimalField(max_digits=5, decimal_places=2, default=0.90)
    min_corridor_width_m = models.DecimalField(max_digits=5, decimal_places=2, default=1.20)
    persons_per_stair_width_m = models.IntegerField(default=150)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "cadhub_escape_params_ref"
        managed = False
        verbose_name = "Fluchtweg-Parameter"
        verbose_name_plural = "Fluchtweg-Parameter"

    def __str__(self) -> str:
        return f"{self.building_type}: max {self.max_distance_m}m"


class FireCompartment(models.Model):
    """Fire compartment (Brandabschnitt)."""

    STATUS_CHOICES = [
        ("pending", "Ausstehend"),
        ("compliant", "Konform"),
        ("warning", "Warnung"),
        ("violation", "Verstoß"),
    ]

    cad_model = models.ForeignKey(
        "CADModel",
        on_delete=models.CASCADE,
        related_name="fire_compartments",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        "Floor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fire_compartments",
        db_column="floor_id",
    )

    name = models.CharField(max_length=255)
    ifc_zone_guid = models.CharField(max_length=36, blank=True, null=True)

    area_m2 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_area_m2 = models.DecimalField(max_digits=12, decimal_places=2, default=1600)
    has_sprinkler = models.BooleanField(default=False)
    fire_load_mj_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cadhub_fire_compartment"
        managed = False
        verbose_name = "Brandabschnitt"
        verbose_name_plural = "Brandabschnitte"

    def __str__(self) -> str:
        return f"{self.name} ({self.area_m2}m²)"

    @property
    def is_compliant(self) -> bool:
        """Check if compartment area is within limits."""
        return self.area_m2 <= self.max_area_m2


class FireRatedElement(models.Model):
    """Element with fire protection requirements."""

    ELEMENT_TYPE_CHOICES = [
        ("wall", "Wand"),
        ("door", "Tür"),
        ("slab", "Decke"),
        ("window", "Fenster"),
    ]

    STANDARD_CHOICES = [
        ("din4102", "DIN 4102"),
        ("en13501", "EN 13501"),
    ]

    cad_model = models.ForeignKey(
        "CADModel",
        on_delete=models.CASCADE,
        related_name="fire_rated_elements",
        db_column="cad_model_id",
    )
    compartment = models.ForeignKey(
        FireCompartment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="elements",
        db_column="compartment_id",
    )

    element_type = models.CharField(max_length=50, choices=ELEMENT_TYPE_CHOICES)
    element_id = models.IntegerField(blank=True, null=True)
    ifc_guid = models.CharField(max_length=36, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    required_rating = models.CharField(max_length=20, blank=True, null=True)
    required_standard = models.CharField(max_length=20, choices=STANDARD_CHOICES, default="din4102")
    requirement_source = models.CharField(max_length=255, blank=True, null=True)

    actual_rating = models.CharField(max_length=20, blank=True, null=True)
    actual_standard = models.CharField(max_length=20, blank=True, null=True)

    is_compliant = models.BooleanField(blank=True, null=True)
    compliance_note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cadhub_fire_rated_element"
        managed = False
        verbose_name = "Brandschutz-Element"
        verbose_name_plural = "Brandschutz-Elemente"

    def __str__(self) -> str:
        rating = self.actual_rating or "k.A."
        return f"{self.name or self.element_type} ({rating})"


class EscapeRoute(models.Model):
    """Calculated escape route from room to exit."""

    EXIT_TYPE_CHOICES = [
        ("external", "Außenausgang"),
        ("stairway", "Treppenhaus"),
        ("compartment", "Brandabschnitt"),
        ("window", "Rettungsfenster"),
    ]

    ROUTE_TYPE_CHOICES = [
        ("primary", "Primär"),
        ("secondary", "Sekundär"),
    ]

    cad_model = models.ForeignKey(
        "CADModel",
        on_delete=models.CASCADE,
        related_name="escape_routes",
        db_column="cad_model_id",
    )
    floor = models.ForeignKey(
        "Floor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escape_routes",
        db_column="floor_id",
    )
    from_room = models.ForeignKey(
        "Room",
        on_delete=models.CASCADE,
        related_name="escape_routes",
        db_column="from_room_id",
    )

    to_exit_type = models.CharField(max_length=50, choices=EXIT_TYPE_CHOICES)
    to_element_id = models.IntegerField(blank=True, null=True)

    distance_m = models.DecimalField(max_digits=8, decimal_places=2)
    max_distance_m = models.DecimalField(max_digits=8, decimal_places=2, default=35)

    min_width_m = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    required_width_m = models.DecimalField(max_digits=5, decimal_places=2, default=0.90)

    is_compliant = models.BooleanField(blank=True, null=True)
    route_type = models.CharField(max_length=20, choices=ROUTE_TYPE_CHOICES, default="primary")

    path_points = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cadhub_escape_route"
        managed = False
        verbose_name = "Fluchtweg"
        verbose_name_plural = "Fluchtwege"

    def __str__(self) -> str:
        status = "✓" if self.is_compliant else "✗"
        return f"{self.from_room} → {self.to_exit_type} ({self.distance_m}m) {status}"
