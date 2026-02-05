"""
CoreUser model for SSO-ready user management.

Bridges Django auth_user with external identity providers.
"""

import uuid
from django.db import models
from django.conf import settings


class CoreUserManager(models.Manager):
    """Custom manager for CoreUser."""
    
    def get_or_create_from_auth_user(self, auth_user) -> "CoreUser":
        """
        Get or create CoreUser from Django auth_user.
        
        Used for bridging existing users to the new system.
        """
        core_user, created = self.get_or_create(
            legacy_user_id=auth_user.id,
            defaults={
                "provider": "local",
                "email": auth_user.email,
                "display_name": auth_user.get_full_name() or auth_user.username,
            }
        )
        return core_user
    
    def get_by_external_id(self, provider: str, external_id: str) -> "CoreUser | None":
        """Get user by external provider ID (SSO)."""
        return self.filter(provider=provider, external_id=external_id).first()


class CoreUser(models.Model):
    """
    Platform user with SSO support.
    
    Design decisions:
    - UUID as PK: Prevents ID guessing, SSO-compatible
    - Bridge to auth_user: Backwards compatibility
    - External ID: Auth0/Okta/SAML integration
    
    Example:
        # From Django user
        core_user = CoreUser.objects.get_or_create_from_auth_user(request.user)
        
        # From SSO
        core_user = CoreUser.objects.get_by_external_id('auth0', 'auth0|123456')
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ══════════════════════════════════════════════════════════════════════════
    
    # SSO Integration
    external_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="External provider ID (e.g., Auth0 sub, Okta uid)",
    )
    
    provider = models.CharField(
        max_length=50,
        blank=True,
        default="local",
        help_text="Identity provider: local, auth0, okta, saml",
    )
    
    # Bridge to Django auth_user
    legacy_user_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Django auth_user.id for backwards compatibility",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # PROFILE (cached, not authoritative)
    # ══════════════════════════════════════════════════════════════════════════
    
    email = models.EmailField(
        blank=True,
        default="",
        db_index=True,
        help_text="Email (may be synced from provider)",
    )
    
    display_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Display name for UI",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════════════
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    objects = CoreUserManager()
    
    class Meta:
        db_table = "core_user"
        indexes = [
            models.Index(fields=["provider", "external_id"]),
            models.Index(fields=["legacy_user_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(legacy_user_id__isnull=False) | models.Q(external_id__isnull=False),
                name="user_identity_chk",
            )
        ]
    
    def __str__(self) -> str:
        return self.display_name or self.email or str(self.id)
    
    @property
    def auth_user(self):
        """Get linked Django auth_user if exists."""
        if self.legacy_user_id is None:
            return None
        User = settings.AUTH_USER_MODEL
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(id=self.legacy_user_id)
        except UserModel.DoesNotExist:
            return None
