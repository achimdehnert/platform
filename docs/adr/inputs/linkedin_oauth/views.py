"""
linkedin_oauth/views.py

Thin Django views — all business logic in services/linkedin.py.

URL flow:
  1. /linkedin/login/       → redirects user to LinkedIn
  2. /linkedin/callback/    → LinkedIn redirects back here with ?code=&state=
  3. /linkedin/disconnect/  → soft-deletes token
  4. /linkedin/post/        → example: post a share (POST)
"""
from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST, require_GET

from .models import LinkedInToken
from .services.linkedin import (
    LinkedInService,
    TokenRefreshError,
    LinkedInAPIError,
    LinkedInOAuthError,
)

logger = logging.getLogger(__name__)

SESSION_STATE_KEY = "linkedin_oauth_state"
SESSION_NEXT_KEY  = "linkedin_oauth_next"


# ---------------------------------------------------------------------------
# Step 1 — Kick off OAuth flow
# ---------------------------------------------------------------------------

@login_required
@require_GET
def linkedin_login(request):
    """
    Redirect the user to LinkedIn's authorization page.
    Store CSRF `state` in session.

    Query params:
        next (optional): URL to redirect after successful auth.
    """
    svc = LinkedInService()
    auth_url, state = svc.build_auth_url()

    request.session[SESSION_STATE_KEY] = state
    request.session[SESSION_NEXT_KEY] = request.GET.get("next", "/dashboard/")

    logger.info("LinkedIn OAuth started for user=%s", request.user.pk)
    return redirect(auth_url)


# ---------------------------------------------------------------------------
# Step 2 — Handle callback from LinkedIn
# ---------------------------------------------------------------------------

@login_required
@require_GET
def linkedin_callback(request):
    """
    LinkedIn redirects here after user grants/denies access.
    Exchanges the code for tokens and persists them.
    """
    # --- CSRF check ---
    state_in_session = request.session.pop(SESSION_STATE_KEY, None)
    state_from_li    = request.GET.get("state")

    if not state_in_session or state_in_session != state_from_li:
        logger.warning("LinkedIn OAuth CSRF mismatch for user=%s", request.user.pk)
        return JsonResponse({"error": "State mismatch — possible CSRF attack."}, status=400)

    # --- User denied access ---
    if error := request.GET.get("error"):
        logger.info("LinkedIn OAuth denied: %s — %s", error, request.GET.get("error_description"))
        return redirect(f"/dashboard/?li_error={error}")

    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Missing authorization code."}, status=400)

    # --- Exchange code → tokens ---
    svc = LinkedInService()
    try:
        token_resp = svc.exchange_code(code)
    except LinkedInOAuthError as exc:
        logger.exception("Token exchange failed for user=%s", request.user.pk)
        return JsonResponse({"error": str(exc)}, status=502)

    # --- Fetch member URN / userinfo ---
    try:
        userinfo = svc.get_userinfo(token_resp.access_token)
    except LinkedInAPIError:
        logger.warning("Could not fetch userinfo after token exchange for user=%s", request.user.pk)
        userinfo = None

    # --- Persist token (upsert) ---
    tenant_id = getattr(request.user, "tenant_id", 0) or 0

    LinkedInToken.objects.update_or_create(
        user=request.user,
        defaults={
            "tenant_id": tenant_id,
            "access_token": token_resp.access_token,
            "access_token_expires_at": token_resp.access_token_expires_at,
            "refresh_token": token_resp.refresh_token,
            "refresh_token_expires_at": token_resp.refresh_token_expires_at,
            "scope": token_resp.scope,
            "linkedin_urn": userinfo.linkedin_urn if userinfo else "",
            "linkedin_sub": userinfo.sub if userinfo else "",
            "is_active": True,
        },
    )

    logger.info(
        "LinkedIn connected for user=%s urn=%s",
        request.user.pk,
        userinfo.linkedin_urn if userinfo else "unknown",
    )

    next_url = request.session.pop(SESSION_NEXT_KEY, "/dashboard/")
    return redirect(f"{next_url}?li_connected=1")


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------

@login_required
@require_POST
def linkedin_disconnect(request):
    """
    Soft-delete the stored token. User must re-authorize to reconnect.
    """
    updated = LinkedInToken.objects.filter(
        user=request.user, is_active=True
    ).update(is_active=False)

    if updated:
        logger.info("LinkedIn disconnected for user=%s", request.user.pk)
        return JsonResponse({"status": "disconnected"})
    return JsonResponse({"status": "not_connected"})


# ---------------------------------------------------------------------------
# Example: post a share
# ---------------------------------------------------------------------------

@login_required
@require_POST
def linkedin_post_share(request):
    """
    POST body (JSON): {"text": "Hello LinkedIn!"}
    Requires w_member_social scope.
    Auto-refreshes token if needed.
    """
    import json

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    text = (body.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "text is required."}, status=400)
    if len(text) > 3000:
        return JsonResponse({"error": "text exceeds 3000 characters."}, status=400)

    svc = LinkedInService()

    # --- Get valid (auto-refreshed) token ---
    try:
        access_token = svc.get_valid_token(request.user)
    except TokenRefreshError as exc:
        return JsonResponse({"error": str(exc), "reauth_required": True}, status=401)

    # --- Get user's LinkedIn URN ---
    try:
        token_obj = LinkedInToken.objects.get(user=request.user, is_active=True)
        author_urn = token_obj.linkedin_urn
    except LinkedInToken.DoesNotExist:
        return JsonResponse({"error": "LinkedIn not connected."}, status=401)

    if not author_urn:
        return JsonResponse({"error": "LinkedIn URN missing — reconnect required."}, status=400)

    # --- Post ---
    try:
        result = svc.post_share(access_token, author_urn, text)
    except LinkedInAPIError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"status": "posted", "post_urn": result.get("id", "")})


# ---------------------------------------------------------------------------
# Status endpoint (e.g. for settings page)
# ---------------------------------------------------------------------------

@login_required
@require_GET
def linkedin_status(request):
    """Returns connection status + token metadata for the logged-in user."""
    try:
        token_obj = LinkedInToken.objects.get(user=request.user, is_active=True)
        return JsonResponse({
            "connected": True,
            "linkedin_urn": token_obj.linkedin_urn,
            "scopes": token_obj.scopes_list,
            "access_token_expires_at": token_obj.access_token_expires_at.isoformat(),
            "access_token_expired": token_obj.is_access_token_expired,
            "has_refresh_token": bool(token_obj.refresh_token),
        })
    except LinkedInToken.DoesNotExist:
        return JsonResponse({"connected": False})
