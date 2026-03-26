"""
linkedin_oauth/models.py

Stores LinkedIn OAuth tokens per user/tenant.
Follows iil.gmbh platform standards:
  - BigAutoField pk + public_id UUID
  - tenant_id as BigIntegerField
  - soft-delete via is_active
  - created_at / updated_at audit trail
"""
import uuid
from django.db import models
from django.conf import settings


class LinkedInToken(models.Model):
    """Persists OAuth 2.0 tokens for a LinkedIn-connected user."""

    # --- Platform standards ---
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    tenant_id = models.BigIntegerField(db_index=True)

    # --- Ownership ---
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="linkedin_token",
    )

    # --- Token data ---
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, default="")
    # LinkedIn access tokens expire after 60 days; refresh tokens after 1 year
    access_token_expires_at = models.DateTimeField()
    refresh_token_expires_at = models.DateTimeField(null=True, blank=True)

    # --- Granted scopes (space-separated, as returned by LinkedIn) ---
    scope = models.CharField(max_length=512, blank=True, default="")

    # --- LinkedIn member URN (e.g. "urn:li:person:ABC123") ---
    linkedin_urn = models.CharField(max_length=128, blank=True, default="")
    linkedin_sub = models.CharField(max_length=128, blank=True, default="")  # OIDC sub

    # --- Soft-delete + audit ---
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "linkedin_oauth_token"
        verbose_name = "LinkedIn Token"
        verbose_name_plural = "LinkedIn Tokens"
        indexes = [
            models.Index(fields=["tenant_id", "user"]),
            models.Index(fields=["access_token_expires_at"]),
        ]

    def __str__(self) -> str:
        return f"LinkedInToken(user={self.user_id}, urn={self.linkedin_urn})"

    @property
    def is_access_token_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() >= self.access_token_expires_at

    @property
    def is_refresh_token_expired(self) -> bool:
        from django.utils import timezone
        if not self.refresh_token_expires_at:
            return True
        return timezone.now() >= self.refresh_token_expires_at

    @property
    def scopes_list(self) -> list[str]:
        return [s for s in self.scope.split(" ") if s]
