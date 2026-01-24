"""
Writing Hub - Lookup Tables
============================

DB-driven Lookups für Writing Hub statt hardcoded choices.

Created: 2024-12-06
Purpose: Hardcoded → DB Migration
"""

from django.db import models


class ContentRating(models.Model):
    """
    Content Rating Lookup (G, PG, PG-13, R, NC-17)
    
    Ersetzt hardcoded choices in BookProjectsForm
    """
    
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code (G, PG, PG-13, R, NC-17)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'General Audiences')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of rating"
    )
    min_age = models.IntegerField(
        default=0,
        help_text="Minimum recommended age"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_content_ratings'
        ordering = ['sort_order', 'min_age']
        verbose_name = 'Content Rating'
        verbose_name_plural = 'Content Ratings'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class WritingStage(models.Model):
    """
    Writing Stage Lookup (planning, outlining, drafting, etc.)
    
    Ersetzt hardcoded choices in BookProjects Model
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Stage code (planning, outlining, drafting, etc.)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name"
    )
    description = models.TextField(
        blank=True,
        help_text="Stage description"
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        help_text="Typical progress % when entering this stage"
    )
    
    # Visual
    color = models.CharField(
        max_length=20,
        default='secondary',
        help_text="Bootstrap color class"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-pencil',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_stages'
        ordering = ['sort_order']
        verbose_name = 'Writing Stage'
        verbose_name_plural = 'Writing Stages'
    
    def __str__(self):
        return self.name


class ArcType(models.Model):
    """
    Story Arc Type Lookup (main, subplot, character)
    
    Ersetzt hardcoded choices in StoryArc Model
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Arc type code (main, subplot, character)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name"
    )
    description = models.TextField(
        blank=True,
        help_text="Arc type description"
    )
    
    # Visual
    color = models.CharField(
        max_length=20,
        default='primary',
        help_text="Bootstrap color class"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-diagram-3',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_arc_types'
        ordering = ['sort_order']
        verbose_name = 'Arc Type'
        verbose_name_plural = 'Arc Types'
    
    def __str__(self):
        return self.name


class ImportanceLevel(models.Model):
    """
    Importance Level Lookup (critical, major, minor)
    
    Wiederverwendbar für verschiedene Entitäten
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Level code (critical, major, minor)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name"
    )
    description = models.TextField(
        blank=True,
        help_text="Level description"
    )
    
    # Visual
    color = models.CharField(
        max_length=20,
        default='secondary',
        help_text="Bootstrap color class"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-flag',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_importance_levels'
        ordering = ['sort_order']
        verbose_name = 'Importance Level'
        verbose_name_plural = 'Importance Levels'
    
    def __str__(self):
        return self.name


class WorldType(models.Model):
    """
    World Type Lookup (primary, secondary, parallel, pocket, mirror, etc.)
    
    DB-driven world types for World Building.
    """
    
    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Type code (primary, secondary, parallel, pocket, mirror)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (English)"
    )
    name_de = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name (German)"
    )
    description = models.TextField(
        blank=True,
        help_text="Type description"
    )
    
    # Visual
    color = models.CharField(
        max_length=20,
        default='primary',
        help_text="Bootstrap color class"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-globe',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_world_types'
        ordering = ['sort_order', 'name']
        verbose_name = 'World Type'
        verbose_name_plural = 'World Types'
    
    def __str__(self):
        return self.name_de or self.name


class CharacterRole(models.Model):
    """
    Character Role Lookup (protagonist, antagonist, mentor, sidekick, etc.)
    
    DB-driven character roles.
    """
    
    code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Role code (protagonist, antagonist, mentor, sidekick)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (English)"
    )
    name_de = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name (German)"
    )
    description = models.TextField(
        blank=True,
        help_text="Role description"
    )
    
    # Visual
    color = models.CharField(
        max_length=20,
        default='secondary',
        help_text="Bootstrap color class"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-person',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_character_roles'
        ordering = ['sort_order', 'name']
        verbose_name = 'Character Role'
        verbose_name_plural = 'Character Roles'
    
    def __str__(self):
        return self.name_de or self.name
