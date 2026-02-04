"""
Weltenhub World Models
======================

Core world-building models for story universes.

Tables:
    - wh_world: Main world definition
    - wh_world_rule: Rules/constraints of a world
    - wh_world_setting: World settings (magic, technology, etc.)
"""

from django.db import models

from apps.core.models import TenantAwareModel


class World(TenantAwareModel):
    """
    A fictional world/universe for stories.

    Worlds are tenant-isolated and can be shared (is_public).
    """

    name = models.CharField(
        max_length=200,
        help_text="Name of the world"
    )
    slug = models.SlugField(
        max_length=200,
        help_text="URL-safe identifier"
    )
    genre = models.ForeignKey(
        "lookups.Genre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worlds",
        help_text="Primary genre of this world"
    )
    description = models.TextField(
        blank=True,
        help_text="General description of the world"
    )
    setting_era = models.CharField(
        max_length=200,
        blank=True,
        help_text="Time period (e.g., 'Medieval', '2050', 'Timeless')"
    )
    geography = models.TextField(
        blank=True,
        help_text="Geography, landscapes, climate"
    )
    inhabitants = models.TextField(
        blank=True,
        help_text="Peoples, races, species"
    )
    culture = models.TextField(
        blank=True,
        help_text="Traditions, religion, values"
    )
    technology_level = models.CharField(
        max_length=200,
        blank=True,
        help_text="Technology level description"
    )
    magic_system = models.TextField(
        blank=True,
        help_text="Magic system if applicable"
    )
    history = models.TextField(
        blank=True,
        help_text="Important historical events"
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Can be used by other tenants"
    )
    is_template = models.BooleanField(
        default=False,
        help_text="Is this a template world?"
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number for tracking changes"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for search and filtering"
    )
    cover_image = models.ImageField(
        upload_to="worlds/covers/",
        blank=True,
        null=True,
        help_text="Cover image for the world"
    )

    class Meta:
        db_table = "wh_world"
        verbose_name = "World"
        verbose_name_plural = "Worlds"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["genre"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "slug"],
                name="unique_world_slug_per_tenant"
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WorldRule(TenantAwareModel):
    """
    Rules and constraints of a world.

    Formalizes the "laws" of the world for consistency.
    Uses database-driven lookups for category and importance (Database-First).
    """

    world = models.ForeignKey(
        World,
        on_delete=models.CASCADE,
        related_name="rules"
    )
    category = models.ForeignKey(
        "lookups.RuleCategory",
        on_delete=models.PROTECT,
        related_name="rules",
        help_text="Rule category (from lookup table)"
    )
    rule = models.CharField(
        max_length=500,
        help_text="The rule itself"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Explanation/reasoning"
    )
    importance = models.ForeignKey(
        "lookups.RuleImportance",
        on_delete=models.PROTECT,
        related_name="rules",
        help_text="How strictly this rule should be followed"
    )

    class Meta:
        db_table = "wh_world_rule"
        verbose_name = "World Rule"
        verbose_name_plural = "World Rules"
        ordering = ["world", "category__order", "-importance__severity"]

    def __str__(self):
        return f"[{self.category.name}] {self.rule[:50]}..."
