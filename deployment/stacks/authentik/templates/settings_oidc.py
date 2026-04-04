# ═══════════════════════════════════════════════════════════════════════════════
# settings.py OIDC-Snippet — authentik Integration (ADR-142)
# ═══════════════════════════════════════════════════════════════════════════════
# Add to your hub's settings.py (after INSTALLED_APPS).
# Requires: pip install mozilla-django-oidc
#
# Environment support (Staging + Production):
#   Production: OIDC_IDP_BASE_URL not set → defaults to https://id.iil.pet
#   Staging:    OIDC_IDP_BASE_URL=https://id.iil.pet (same Authentik, different app slug)
#   Local:      OIDC_ENABLED=false → disables OIDC entirely
# ═══════════════════════════════════════════════════════════════════════════════
from config.secrets import read_secret  # ADR-045

# --- authentik OIDC (ADR-142) ---
# Set OIDC_ENABLED=false to disable OIDC (e.g. local dev without Authentik)
_OIDC_ENABLED = read_secret("OIDC_ENABLED", default="true").lower() in ("true", "1", "yes")

AUTHENTICATION_BACKENDS = (
    [
        "core.auth.IILOIDCAuthenticationBackend",   # ADR-142 Custom Backend
        "django.contrib.auth.backends.ModelBackend",  # Fallback für Admin/Shell
    ]
    if _OIDC_ENABLED
    else [
        "django.contrib.auth.backends.ModelBackend",
    ]
)

if _OIDC_ENABLED:
    # Credentials via read_secret() — ADR-045
    OIDC_RP_CLIENT_ID = read_secret("OIDC_RP_CLIENT_ID", required=True)
    OIDC_RP_CLIENT_SECRET = read_secret(
        "OIDC_RP_CLIENT_SECRET", required=True,
    )

    # IDP Base URL — configurable per environment (default: production)
    _OIDC_IDP_BASE_URL = read_secret(
        "OIDC_IDP_BASE_URL", default="https://id.iil.pet",
    )

    # App-spezifische OIDC-Endpoints — jeder Hub hat eigenen Application-Slug
    # Staging uses "{hub}-staging" slug, Production uses "{hub}" slug
    _OIDC_APP_SLUG = read_secret("OIDC_APP_SLUG", required=True)

    _IDP = f"{_OIDC_IDP_BASE_URL}/application/o/{_OIDC_APP_SLUG}"
    OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_IDP}/authorize/"
    OIDC_OP_TOKEN_ENDPOINT = f"{_IDP}/token/"
    OIDC_OP_USER_ENDPOINT = f"{_IDP}/userinfo/"
    OIDC_OP_JWKS_ENDPOINT = f"{_IDP}/jwks/"
    OIDC_RP_SIGN_ALGO = "RS256"
    OIDC_RP_SCOPES = "openid email profile"

LOGIN_REDIRECT_URL = read_secret(
    "LOGIN_REDIRECT_URL", default="/dashboard/",
)
LOGOUT_REDIRECT_URL = "/"
