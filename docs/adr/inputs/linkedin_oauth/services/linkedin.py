"""
linkedin_oauth/services/linkedin.py

Service layer for LinkedIn OAuth 2.0 + REST API.
All business logic lives here — views are thin wrappers.

Supported flows:
  • 3-legged OAuth (member authorization)
  • Token refresh (via refresh_token)
  • Token introspection
  • Post share (w_member_social)
  • User info / profile (openid, profile)
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (read from Django settings)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LinkedInSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email", "w_member_social"])

    @classmethod
    def from_django_settings(cls) -> "LinkedInSettings":
        cfg = getattr(settings, "LINKEDIN_OAUTH", {})
        return cls(
            client_id=cfg["CLIENT_ID"],
            client_secret=cfg["CLIENT_SECRET"],
            redirect_uri=cfg["REDIRECT_URI"],
            scopes=cfg.get("SCOPES", ["openid", "profile", "email", "w_member_social"]),
        )


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class TokenResponse:
    access_token: str
    expires_in: int               # seconds until access token expires
    refresh_token: str = ""
    refresh_token_expires_in: int = 0   # 0 means not provided
    scope: str = ""
    token_type: str = "Bearer"

    @property
    def access_token_expires_at(self):
        return timezone.now() + timedelta(seconds=self.expires_in)

    @property
    def refresh_token_expires_at(self):
        if not self.refresh_token_expires_in:
            return None
        return timezone.now() + timedelta(seconds=self.refresh_token_expires_in)


@dataclass
class UserInfo:
    sub: str                   # OIDC subject (LinkedIn member ID)
    name: str = ""
    given_name: str = ""
    family_name: str = ""
    email: str = ""
    email_verified: bool = False
    picture: str = ""
    linkedin_urn: str = ""     # "urn:li:person:<sub>"

    @classmethod
    def from_dict(cls, data: dict) -> "UserInfo":
        sub = data.get("sub", "")
        return cls(
            sub=sub,
            name=data.get("name", ""),
            given_name=data.get("given_name", ""),
            family_name=data.get("family_name", ""),
            email=data.get("email", ""),
            email_verified=data.get("email_verified", False),
            picture=data.get("picture", ""),
            linkedin_urn=f"urn:li:person:{sub}" if sub else "",
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LinkedInOAuthError(Exception):
    """Raised when LinkedIn returns an OAuth error."""

class LinkedInAPIError(Exception):
    """Raised when a LinkedIn API call fails."""

class TokenRefreshError(LinkedInOAuthError):
    """Raised when token refresh fails (e.g. refresh token expired)."""


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------

class LinkedInService:
    """
    Stateless service — instantiate per request or inject as singleton.
    All network calls are synchronous (httpx). For async Django, use
    asyncio.to_thread() or asgiref.sync_to_async().
    """

    AUTH_BASE = "https://www.linkedin.com/oauth/v2"
    API_BASE  = "https://api.linkedin.com"

    def __init__(self, config: LinkedInSettings | None = None):
        self._cfg = config or LinkedInSettings.from_django_settings()
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0),
            headers={"X-Restli-Protocol-Version": "2.0.0"},
        )

    def __enter__(self): return self
    def __exit__(self, *_): self._http.close()

    # ------------------------------------------------------------------
    # 1) OAuth flow helpers
    # ------------------------------------------------------------------

    def build_auth_url(self, state: str | None = None) -> tuple[str, str]:
        """
        Build the authorization URL to redirect the user to.

        Returns:
            (auth_url, state)  — store `state` in session for CSRF check
        """
        state = state or secrets.token_urlsafe(32)
        params = {
            "response_type": "code",
            "client_id": self._cfg.client_id,
            "redirect_uri": self._cfg.redirect_uri,
            "state": state,
            "scope": " ".join(self._cfg.scopes),
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.AUTH_BASE}/authorization?{qs}"
        logger.debug("LinkedIn auth URL built (state=%s)", state)
        return url, state

    def exchange_code(self, code: str) -> TokenResponse:
        """
        Exchange authorization code → access + refresh token.
        Call this once from your OAuth callback view.
        """
        resp = self._http.post(
            f"{self.AUTH_BASE}/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._cfg.redirect_uri,
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
            },
        )
        return self._parse_token_response(resp, "exchange_code")

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Use the refresh token to obtain a new access token.
        LinkedIn refresh tokens are valid for ~1 year.
        Raises TokenRefreshError if the refresh token is expired/revoked.
        """
        resp = self._http.post(
            f"{self.AUTH_BASE}/accessToken",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
            },
        )
        try:
            return self._parse_token_response(resp, "refresh_access_token")
        except LinkedInOAuthError as exc:
            raise TokenRefreshError(str(exc)) from exc

    def introspect_token(self, access_token: str) -> dict:
        """
        Inspect a token's validity and metadata via LinkedIn's introspection endpoint.
        Returns raw dict with `active`, `scope`, `expires_at`, etc.
        """
        resp = self._http.post(
            f"{self.AUTH_BASE}/introspectToken",
            data={
                "token": access_token,
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # 2) Token auto-refresh decorator
    # ------------------------------------------------------------------

    def get_valid_token(self, user) -> str:
        """
        Returns a valid access token for `user`, refreshing automatically
        if needed. Persists the refreshed token back to DB.

        Raises TokenRefreshError if re-auth is required.
        """
        from linkedin_oauth.models import LinkedInToken

        try:
            token_obj = LinkedInToken.objects.get(user=user, is_active=True)
        except LinkedInToken.DoesNotExist:
            raise TokenRefreshError("No LinkedIn token found — user must re-authorize.")

        if not token_obj.is_access_token_expired:
            return token_obj.access_token

        logger.info("LinkedIn access token expired for user=%s — refreshing", user.pk)

        if not token_obj.refresh_token or token_obj.is_refresh_token_expired:
            token_obj.is_active = False
            token_obj.save(update_fields=["is_active", "updated_at"])
            raise TokenRefreshError(
                "Refresh token expired or missing — user must re-authorize."
            )

        new_tokens = self.refresh_access_token(token_obj.refresh_token)
        self._persist_token(token_obj, new_tokens)
        logger.info("LinkedIn token refreshed for user=%s", user.pk)
        return new_tokens.access_token

    # ------------------------------------------------------------------
    # 3) API calls
    # ------------------------------------------------------------------

    def get_userinfo(self, access_token: str) -> UserInfo:
        """
        GET /v2/userinfo  (requires openid + profile scopes)
        Returns OIDC UserInfo object.
        """
        resp = self._http.get(
            f"{self.API_BASE}/v2/userinfo",
            headers=self._auth_headers(access_token),
        )
        self._raise_for_api_error(resp, "get_userinfo")
        return UserInfo.from_dict(resp.json())

    def post_share(
        self,
        access_token: str,
        author_urn: str,
        text: str,
        visibility: str = "PUBLIC",
    ) -> dict:
        """
        POST /v2/ugcPosts — share a text post on LinkedIn.

        Args:
            access_token: Valid 3-legged token with w_member_social scope.
            author_urn:   "urn:li:person:ABC123"
            text:         Post content (plain text, max ~3000 chars).
            visibility:   "PUBLIC" | "CONNECTIONS"

        Returns:
            {"id": "urn:li:ugcPost:...", ...}
        """
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            },
        }
        resp = self._http.post(
            f"{self.API_BASE}/v2/ugcPosts",
            json=payload,
            headers=self._auth_headers(access_token),
        )
        self._raise_for_api_error(resp, "post_share")
        return resp.json()

    def get_profile(self, access_token: str, fields: list[str] | None = None) -> dict:
        """
        GET /v2/me — basic profile data.
        Requires r_liteprofile scope (or openid+profile via OIDC).
        """
        projection = ",".join(fields or ["id", "localizedFirstName", "localizedLastName"])
        resp = self._http.get(
            f"{self.API_BASE}/v2/me",
            params={"projection": f"({projection})"},
            headers=self._auth_headers(access_token),
        )
        self._raise_for_api_error(resp, "get_profile")
        return resp.json()

    # ------------------------------------------------------------------
    # 4) Helpers
    # ------------------------------------------------------------------

    def _auth_headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _parse_token_response(self, resp: httpx.Response, context: str) -> TokenResponse:
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("LinkedIn OAuth error [%s]: %s", context, body)
            raise LinkedInOAuthError(f"LinkedIn OAuth failed [{context}]: {body}") from exc

        data = resp.json()
        return TokenResponse(
            access_token=data["access_token"],
            expires_in=data.get("expires_in", 5183944),       # ~60 days default
            refresh_token=data.get("refresh_token", ""),
            refresh_token_expires_in=data.get("refresh_token_expires_in", 0),
            scope=data.get("scope", ""),
            token_type=data.get("token_type", "Bearer"),
        )

    def _raise_for_api_error(self, resp: httpx.Response, context: str) -> None:
        if resp.is_error:
            logger.error(
                "LinkedIn API error [%s]: status=%s body=%s",
                context, resp.status_code, resp.text,
            )
            raise LinkedInAPIError(
                f"LinkedIn API [{context}] returned {resp.status_code}: {resp.text}"
            )

    @staticmethod
    def _persist_token(token_obj, new_tokens: TokenResponse) -> None:
        """Update token fields and save — idempotent."""
        token_obj.access_token = new_tokens.access_token
        token_obj.access_token_expires_at = new_tokens.access_token_expires_at
        if new_tokens.refresh_token:
            token_obj.refresh_token = new_tokens.refresh_token
        if new_tokens.refresh_token_expires_at:
            token_obj.refresh_token_expires_at = new_tokens.refresh_token_expires_at
        if new_tokens.scope:
            token_obj.scope = new_tokens.scope
        token_obj.save(update_fields=[
            "access_token",
            "access_token_expires_at",
            "refresh_token",
            "refresh_token_expires_at",
            "scope",
            "updated_at",
        ])
