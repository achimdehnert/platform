"""
Multi-Hub Framework - Domain Models
Extends existing system with hierarchical domain structure
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from .utils.crud_config import CRUDConfigBase

User = get_user_model()


# ============================================================================
# MULTI-HUB FRAMEWORK - DOMAIN HIERARCHY
# ============================================================================

class DomainArt(models.Model):
    """
    Top-level domain classification for Multi-Hub Framework
    
    Examples:
    - book_creation (Bücher-Hub)
    - expertise_management (Experten-Hub) 
    - customer_support (Support-Hub)
    - content_formatting (Format-Hub)
    - research_management (Research-Hub)
    """
    
    # === IDENTITY ===
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Domain name (e.g., 'book_creation')"
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-friendly identifier (e.g., 'book-creation')"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name (e.g., 'Bücher-Hub')"
    )
    description = models.TextField(
        blank=True,
        help_text="What this domain encompasses"
    )
    
    # === VISUAL ===
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bootstrap icon name (e.g., 'book', 'people')"
    )
    color = models.CharField(
        max_length=20,
        default="primary",
        help_text="Bootstrap color class (primary, success, info, etc.)"
    )
    
    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        help_text="Is this domain available for use?"
    )
    is_experimental = models.BooleanField(
        default=False,
        help_text="Is this domain in experimental phase?"
    )
    
    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'domain_arts'
        ordering = ['name']
        verbose_name = 'Domain Art'
        verbose_name_plural = 'Domain Arts'
    
    def __str__(self):
        status = " (experimental)" if self.is_experimental else ""
        return f"{self.display_name}{status}"


class DomainType(models.Model):
    """
    Second-level domain classification within a DomainArt
    
    Examples for book_creation:
    - fiction, non_fiction, technical, children
    
    Examples for expertise_management:
    - consultants, specialists, reviewers
    """
    
    # === RELATIONS ===
    domain_art = models.ForeignKey(
        DomainArt,
        on_delete=models.CASCADE,
        related_name='domain_types'
    )
    
    # === IDENTITY ===
    name = models.CharField(
        max_length=100,
        help_text="Type name (e.g., 'fiction', 'consultants')"
    )
    slug = models.SlugField(
        help_text="URL-friendly identifier"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True,
        help_text="What this type encompasses"
    )
    
    # === VISUAL ===
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bootstrap icon name (leave empty to inherit from domain_art)"
    )
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Bootstrap color class (leave empty to inherit from domain_art)"
    )
    
    # === CONFIGURATION ===
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific configuration"
    )
    
    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        help_text="Is this type available for use?"
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order within domain_art"
    )
    
    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'domain_types'
        ordering = ['domain_art', 'sort_order', 'name']
        unique_together = [['domain_art', 'slug']]
        verbose_name = 'Domain Type'
        verbose_name_plural = 'Domain Types'
    
    def __str__(self):
        return f"{self.domain_art.display_name} → {self.display_name}"
    
    @property
    def effective_color(self):
        """Return type color or inherit from domain_art"""
        return self.color or self.domain_art.color
    
    @property
    def effective_icon(self):
        """Return type icon or inherit from domain_art"""
        return self.icon or self.domain_art.icon


class DomainPhase(models.Model):
    """
    Third-level: Links DomainType to WorkflowPhase
    
    Defines which workflow phases are available for a specific domain type
    and in what order they should be executed.
    
    Example for Fiction (DomainType):
    - Planning Phase (order: 10)
    - Outline Phase (order: 20)
    - Writing Phase (order: 30)
    - Review Phase (order: 40)
    """
    
    # === RELATIONS ===
    domain_type = models.ForeignKey(
        DomainType,
        on_delete=models.CASCADE,
        related_name='domain_phases'
    )
    workflow_phase = models.ForeignKey(
        'WorkflowPhase',
        on_delete=models.CASCADE,
        related_name='domain_phases',
        help_text="Reference to existing WorkflowPhase"
    )
    
    # === CONFIGURATION ===
    sort_order = models.IntegerField(
        default=0,
        help_text="Execution order within domain_type"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Phase-specific configuration for this domain"
    )
    
    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        help_text="Is this phase active for this domain type?"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Is this phase required or optional?"
    )
    
    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'bfagent'
        db_table = 'domain_phases'
        ordering = ['domain_type', 'sort_order']
        unique_together = [['domain_type', 'workflow_phase']]
        verbose_name = 'Domain Phase'
        verbose_name_plural = 'Domain Phases'
    
    def __str__(self):
        required = "*" if self.is_required else ""
        return f"{self.domain_type.display_name} → {self.workflow_phase.name}{required}"
