"""
Weltenhub Location Models
=========================

Hierarchical location system for story worlds.
Locations can be nested (continent > country > city > building).

Tables:
    - wh_location: Main location entity (tenant-aware)
"""

from django.db import models

from apps.core.models import TenantAwareModel


class Location(TenantAwareModel):
    """
    A location within a world.

    Locations are hierarchical:
    - Continent > Country > Region > City > District > Building

    Each location belongs to a world and optionally has a parent location.
    """

    world = models.ForeignKey(
        "worlds.World",
        on_delete=models.CASCADE,
        related_name="locations",
        help_text="World this location belongs to"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent location in hierarchy"
    )
    location_type = models.ForeignKey(
        "lookups.LocationType",
        on_delete=models.PROTECT,
        related_name="locations",
        help_text="Type of location (city, building, etc.)"
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the location"
    )
    slug = models.SlugField(
        max_length=200,
        help_text="URL-safe identifier"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the location"
    )
    significance = models.TextField(
        blank=True,
        help_text="Story significance of this location"
    )
    atmosphere = models.TextField(
        blank=True,
        help_text="Mood and atmosphere of this location"
    )
    coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text="Map coordinates: {'x': 0, 'y': 0, 'z': 0}"
    )
    real_world_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Real-world location this is based on (if any)"
    )
    image = models.ImageField(
        upload_to="locations/",
        blank=True,
        null=True,
        help_text="Image of the location"
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Can be used by other tenants"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order among siblings"
    )

    class Meta:
        db_table = "wh_location"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ["world", "order", "name"]
        indexes = [
            models.Index(fields=["tenant", "world"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["location_type"]),
            models.Index(fields=["is_public"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "world", "slug"],
                name="unique_location_slug_per_world"
            )
        ]

    def __str__(self):
        return f"{self.world.name} > {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def full_path(self) -> str:
        """Return full hierarchical path: Continent > Country > City."""
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(parts)

    @property
    def depth(self) -> int:
        """Return depth in hierarchy (0 = top level)."""
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth

    def get_ancestors(self):
        """Return list of ancestor locations from root to parent."""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.insert(0, parent)
            parent = parent.parent
        return ancestors

    def get_descendants(self):
        """Return all descendant locations (recursive)."""
        descendants = list(self.children.all())
        for child in self.children.all():
            descendants.extend(child.get_descendants())
        return descendants
