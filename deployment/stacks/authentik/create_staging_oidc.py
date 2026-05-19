"""Idempotent staging OIDC app provisioning for authentik (ADR-142).

Run inside the authentik server container:

    docker exec -i iil_authentik_server ak shell < create_staging_oidc.py

Or remotely:

    ssh root@88.198.191.108 'docker exec -i iil_authentik_server ak shell' \
        < create_staging_oidc.py

Parameters are read from env (set before piping):
    OIDC_NAME       display/provider base name      e.g. "risk-hub-staging"
    OIDC_SLUG       authentik application slug       e.g. "risk-hub-staging"
    OIDC_REDIRECT   strict redirect URI              e.g. "https://staging.schutztat.de/oidc/callback/"
    OIDC_LAUNCH     application launch URL           e.g. "https://staging.schutztat.de"
    OIDC_GROUP      application group (default: staging)

Prints `@@@{json}@@@` with client_id + client_secret on success.
"""

import json
import os

from authentik.core.models import Application
from authentik.crypto.models import CertificateKeyPair
from authentik.flows.models import Flow
from authentik.providers.oauth2.models import (
    OAuth2Provider,
    RedirectURI,
    RedirectURIMatchingMode,
    ScopeMapping,
)

name = os.environ["OIDC_NAME"]
slug = os.environ["OIDC_SLUG"]
redirect = os.environ["OIDC_REDIRECT"]
launch = os.environ["OIDC_LAUNCH"]
group = os.environ.get("OIDC_GROUP", "staging")

auth_flow = Flow.objects.get(slug="default-provider-authorization-implicit-consent")
try:
    inval_flow = Flow.objects.get(slug="default-provider-invalidation-flow")
except Flow.DoesNotExist:
    inval_flow = Flow.objects.get(slug="default-invalidation-flow")
signing_key = CertificateKeyPair.objects.first()

provider, created = OAuth2Provider.objects.get_or_create(
    client_id=slug,
    defaults={
        "name": f"{name} OIDC Provider",
        "authorization_flow": auth_flow,
        "invalidation_flow": inval_flow,
        "client_type": "confidential",
        "signing_key": signing_key,
    },
)
# Ensure signing key + flows even if provider pre-existed (idempotent repair)
if not provider.signing_key:
    provider.signing_key = signing_key
provider.authorization_flow = auth_flow
provider.invalidation_flow = inval_flow
provider.save()

# Scope mappings (PFLICHT — sonst leere userinfo)
for sc in ("openid", "email", "profile"):
    m = ScopeMapping.objects.get(scope_name=sc)
    provider.property_mappings.add(m)
provider.save()

# Strict redirect URI (idempotent)
if not any(r.url == redirect for r in provider.redirect_uris):
    RedirectURI.objects.create(
        provider=provider,
        matching_mode=RedirectURIMatchingMode.STRICT,
        url=redirect,
    )

app, app_created = Application.objects.get_or_create(
    slug=slug,
    defaults={
        "name": name,
        "provider": provider,
        "meta_launch_url": launch,
        "group": group,
    },
)
if app.provider_id != provider.pk:
    app.provider = provider
    app.save()

print(
    "@@@"
    + json.dumps(
        {
            "provider_created": created,
            "app_created": app_created,
            "name": name,
            "slug": slug,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "redirects": [r.url for r in provider.redirect_uris],
            "scopes": sorted(m.scope_name for m in provider.property_mappings.all()),
            "signing_key": bool(provider.signing_key),
        }
    )
    + "@@@"
)
