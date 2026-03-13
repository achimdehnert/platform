# ═══════════════════════════════════════════════════════════════════════════════
# settings.py OIDC-Snippet — authentik Integration (ADR-142)
# ═══════════════════════════════════════════════════════════════════════════════
# Add to your hub's settings.py (after INSTALLED_APPS).
# Requires: pip install mozilla-django-oidc
# ═══════════════════════════════════════════════════════════════════════════════
from config.secrets import read_secret  # ADR-045

# --- authentik OIDC (ADR-142) ---
AUTHENTICATION_BACKENDS = [
    "core.auth.IILOIDCAuthenticationBackend",   # ADR-142 Custom Backend
    "django.contrib.auth.backends.ModelBackend",  # Fallback für Admin/Shell
]

# Credentials via read_secret() — ADR-045
OIDC_RP_CLIENT_ID = read_secret("OIDC_RP_CLIENT_ID", required=True)
OIDC_RP_CLIENT_SECRET = read_secret(
    "OIDC_RP_CLIENT_SECRET", required=True,
)

# App-spezifische OIDC-Endpoints — jeder Hub hat eigenen Application-Slug
_OIDC_APP_SLUG = read_secret("OIDC_APP_SLUG", required=True)

_IDP = f"https://id.iil.pet/application/o/{_OIDC_APP_SLUG}"
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
