from django.db import models
from django.utils import timezone


class Domain(models.Model):
    """
    Domain/App definition stored in database
    Sync with DomainRegistry for dynamic domain management
    """

    CATEGORY_CHOICES = [
        ("core", "Core"),
        ("ai", "AI"),
        ("medical", "Medical"),
        ("presentation", "Presentation"),
        ("content", "Content"),
        ("admin", "Admin"),
        ("integration", "Integration"),
    ]

    # Core fields
    domain_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique domain identifier (e.g., 'presentation_studio')",
    )
    name = models.CharField(max_length=100, help_text="Human-readable domain name")
    description = models.TextField(blank=True, help_text="Domain description")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="core", help_text="Domain category"
    )

    # Technical fields
    version = models.CharField(max_length=20, default="1.0.0", help_text="Domain version")
    base_path = models.CharField(
        max_length=200,
        blank=True,
        help_text="Base path to domain code (e.g., 'apps/presentation_studio')",
    )

    # Status
    is_active = models.BooleanField(default=True, help_text="Whether domain is active")

    # Dependencies
    dependencies = models.JSONField(
        default=list, blank=True, help_text="List of domain_ids this domain depends on"
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional domain metadata")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        db_table = "core_domain"
        verbose_name = "Domain"
        verbose_name_plural = "Domains"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.domain_id})"

    def get_dependent_domains(self):
        """Get all domains that depend on this domain"""
        return Domain.objects.filter(dependencies__contains=[self.domain_id])
