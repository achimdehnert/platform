# ═══════════════════════════════════════════════════════════════════════════════
# core/auth.py — OIDC Authentication Backend Template (ADR-142)
# ═══════════════════════════════════════════════════════════════════════════════
# Copy to: <hub>/core/auth.py
# Requires: pip install mozilla-django-oidc
# Settings: see settings_oidc.py template
# ═══════════════════════════════════════════════════════════════════════════════
import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class IILOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Plattform-weites OIDC-Backend mit authentik (ADR-142 + ADR-109).

    - Soft-Delete-aware User-Lookup (is_active=True)
    - Tenant-Zuordnung über OIDC-Claims (Hub-spezifisch überschreibbar)
    - Konformes super() Chaining
    """

    def filter_users_by_claims(self, claims):
        """Sucht aktive (nicht deaktivierte) User per E-Mail."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(
            email__iexact=email,
            is_active=True,
        )

    def create_user(self, claims):
        """Erstellt neuen User bei erstem OIDC-Login (JIT-Provisioning)."""
        email = claims.get("email", "")
        if not email:
            logger.warning("OIDC create_user: no email in claims")
            return None

        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")[:150]
        user.last_name = claims.get("family_name", "")[:150]
        user.is_active = True
        user.save(update_fields=["first_name", "last_name", "is_active"])

        logger.info(
            "OIDC user created",
            extra={"email": email, "sub": claims.get("sub", "")},
        )
        return user

    def update_user(self, user, claims):
        """Aktualisiert bestehenden User bei jedem Login."""
        user = super().update_user(user, claims)
        updated = False
        new_first = claims.get("given_name", "")[:150]
        new_last = claims.get("family_name", "")[:150]

        if new_first and user.first_name != new_first:
            user.first_name = new_first
            updated = True
        if new_last and user.last_name != new_last:
            user.last_name = new_last
            updated = True

        if updated:
            user.save(update_fields=["first_name", "last_name"])
        return user

    def get_or_create_user(self, access_token, id_token, payload):
        """Hook: Tenant-Zuordnung nach User-Erstellung (ADR-109)."""
        user = super().get_or_create_user(access_token, id_token, payload)
        if user:
            self._assign_tenant(user, payload)
        return user

    @staticmethod
    def _assign_tenant(user, claims):
        """Ordnet User dem korrekten Tenant zu.

        Default: No-op. Jeder Hub überschreibt diese Methode wenn nötig.
        Claims können `tenant_id` Claim von authentik enthalten.
        """
        pass
