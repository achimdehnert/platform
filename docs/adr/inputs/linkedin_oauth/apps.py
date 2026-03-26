"""
=======================================================================
linkedin_oauth — Django App
=======================================================================

INSTALLATION
------------

1. Add to INSTALLED_APPS:

    INSTALLED_APPS = [
        ...
        "linkedin_oauth",
    ]

2. Add to your root urls.py:

    urlpatterns = [
        ...
        path("linkedin/", include("linkedin_oauth.urls", namespace="linkedin")),
    ]

3. Configure in settings.py:

    # --- LinkedIn OAuth ---
    LINKEDIN_OAUTH = {
        "CLIENT_ID":     env("LINKEDIN_CLIENT_ID"),       # from developer.linkedin.com
        "CLIENT_SECRET": env("LINKEDIN_CLIENT_SECRET"),
        "REDIRECT_URI":  env("LINKEDIN_REDIRECT_URI",
                              default="https://yourapp.com/linkedin/callback/"),
        # Self-serve scopes (no partner approval needed):
        "SCOPES": [
            "openid",          # OIDC id
            "profile",         # name, picture
            "email",           # email address
            "w_member_social", # post shares
        ],
    }

    # --- Celery beat (token refresh) ---
    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        "refresh-linkedin-tokens": {
            "task": "linkedin_oauth.tasks.refresh_expiring_tokens",
            "schedule": crontab(hour=2, minute=0),  # daily at 02:00
        },
    }

4. Store secrets via SOPS/age (ADR-106 standard):

    # .env (decrypted at runtime)
    LINKEDIN_CLIENT_ID=86xxxxx
    LINKEDIN_CLIENT_SECRET=xxxxxxxxxxxxxxxx
    LINKEDIN_REDIRECT_URI=https://yourapp.com/linkedin/callback/

5. Run migrations:

    python manage.py migrate linkedin_oauth


OAUTH FLOW
----------

    User → GET /linkedin/login/
         → redirect → LinkedIn consent page
         → LinkedIn → GET /linkedin/callback/?code=X&state=Y
         → Token stored → redirect to /dashboard/?li_connected=1


API SURFACE
-----------

    from linkedin_oauth.services.linkedin import LinkedInService

    svc = LinkedInService()

    # Get valid (auto-refreshed) token for a user
    token = svc.get_valid_token(request.user)

    # Fetch profile info
    userinfo = svc.get_userinfo(token)

    # Post a share
    result = svc.post_share(token, "urn:li:person:ABC123", "Hello!")

    # Introspect token
    meta = svc.introspect_token(token)


DIRECTORY STRUCTURE
-------------------

    linkedin_oauth/
    ├── __init__.py
    ├── apps.py
    ├── models.py               ← LinkedInToken model
    ├── views.py                ← OAuth views (login / callback / status / post)
    ├── urls.py                 ← URL routing
    ├── tasks.py                ← Celery beat: proactive token refresh
    ├── migrations/
    │   └── 0001_initial.py
    └── services/
        ├── __init__.py
        └── linkedin.py         ← All business logic (LinkedInService)


NOTES
-----

- All tokens are stored encrypted at rest if you use Django-encrypted-fields
  (recommended for production). Wrap access_token / refresh_token fields with
  EncryptedTextField from django-fernet-fields or similar.

- For async Django (ASGI), wrap service calls with:
      from asgiref.sync import sync_to_async
      get_userinfo = sync_to_async(svc.get_userinfo)

- Rate limits: LinkedIn enforces per-member and per-app limits.
  Add exponential backoff for production use:
      from tenacity import retry, stop_after_attempt, wait_exponential

"""

# apps.py  -------------------------------------------------------------------

from django.apps import AppConfig


class LinkedInOAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "linkedin_oauth"
    verbose_name = "LinkedIn OAuth"

    def ready(self):
        # Register signal handlers here if needed
        pass
