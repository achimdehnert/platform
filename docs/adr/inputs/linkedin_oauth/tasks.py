"""
linkedin_oauth/tasks.py

Celery beat task: proactively refresh LinkedIn access tokens
before they expire (run daily via beat schedule).

Beat schedule entry (settings.py):
    CELERY_BEAT_SCHEDULE = {
        "refresh-linkedin-tokens": {
            "task": "linkedin_oauth.tasks.refresh_expiring_tokens",
            "schedule": crontab(hour=2, minute=0),   # daily at 02:00
        },
    }
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="linkedin_oauth.tasks.refresh_expiring_tokens",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min
    acks_late=True,
)
def refresh_expiring_tokens(self):
    """
    Find tokens that expire within the next 7 days and refresh them
    using the stored refresh_token.

    Tokens whose refresh_token is also expired/missing are deactivated
    so users are prompted to re-authorize.
    """
    from linkedin_oauth.models import LinkedInToken
    from linkedin_oauth.services.linkedin import LinkedInService, TokenRefreshError

    window = timezone.now() + timedelta(days=7)

    expiring = LinkedInToken.objects.filter(
        is_active=True,
        access_token_expires_at__lte=window,
    ).select_related("user")

    total = expiring.count()
    logger.info("LinkedIn token refresh task: %d tokens to process", total)

    refreshed = 0
    deactivated = 0

    svc = LinkedInService()

    for token_obj in expiring:
        try:
            # get_valid_token handles refresh + DB persistence
            svc.get_valid_token(token_obj.user)
            refreshed += 1
        except TokenRefreshError:
            logger.warning(
                "Cannot refresh token for user=%s — deactivating (re-auth required)",
                token_obj.user_id,
            )
            token_obj.is_active = False
            token_obj.save(update_fields=["is_active", "updated_at"])
            deactivated += 1
        except Exception as exc:
            logger.error(
                "Unexpected error refreshing token for user=%s: %s",
                token_obj.user_id, exc,
            )

    logger.info(
        "LinkedIn token refresh complete: refreshed=%d deactivated=%d / total=%d",
        refreshed, deactivated, total,
    )
    return {"refreshed": refreshed, "deactivated": deactivated, "total": total}
