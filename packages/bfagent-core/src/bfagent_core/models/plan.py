"""
Plan model for subscription tiers.

Normalized table for plan definitions with FK support.
"""

from django.db import models


class Plan(models.Model):
    """
    Subscription plan definitions.
    
    Examples: free, professional, enterprise
    """
    
    code = models.CharField(
        primary_key=True,
        max_length=50,
        help_text="Unique plan identifier (e.g., 'free', 'professional')",
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Display name (English)",
    )
    
    name_de = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Display name (German)",
    )
    
    description = models.TextField(
        blank=True,
        default="",
        help_text="Plan description",
    )
    
    is_public = models.BooleanField(
        default=True,
        help_text="Show in pricing page",
    )
    
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order in UI",
    )
    
    # Pricing (optional)
    monthly_price_cents = models.IntegerField(
        null=True,
        blank=True,
        help_text="Monthly price in cents",
    )
    
    yearly_price_cents = models.IntegerField(
        null=True,
        blank=True,
        help_text="Yearly price in cents",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "core_plan"
        ordering = ["sort_order", "code"]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
    
    @property
    def monthly_price(self) -> float | None:
        if self.monthly_price_cents is None:
            return None
        return self.monthly_price_cents / 100
    
    @property
    def yearly_price(self) -> float | None:
        if self.yearly_price_cents is None:
            return None
        return self.yearly_price_cents / 100
