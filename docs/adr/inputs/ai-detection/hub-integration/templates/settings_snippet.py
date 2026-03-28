# =============================================================================
# Hub Visual Identity Integration — settings/base.py snippet (ADR-051)
# =============================================================================
# Add to each hub's settings/base.py:

# ── Hub Identity (ADR-051) ────────────────────────────────────────────────
# This is the single value that drives: CSS tokens, fonts, palette, Schema.org
HUB_NAME = "bieterpilot"  # ← Change per hub repo

# ── Template Context Processors ──────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # ── ADR-051: Hub Visual Identity ──
                "apps.core.context_processors.hub_identity",
                "apps.core.context_processors.seo_metadata",
            ],
        },
    },
]

# ── Static Files: where generated CSS lives ───────────────────────────────
# After running `make generate` in the platform repo, copy generated CSS:
#   cp platform/generated/pui-tokens-{hub}.css {hub}/static/css/
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# =============================================================================
# Per-Hub settings variants (copy-paste reference):
# =============================================================================
#
# bieterpilot:   HUB_NAME = "bieterpilot"
# risk-hub:      HUB_NAME = "risk-hub"
# travel-beat:   HUB_NAME = "travel-beat"
# weltenhub:     HUB_NAME = "weltenhub"
# pptx-hub:      HUB_NAME = "pptx-hub"
# coach-hub:     HUB_NAME = "coach-hub"
# billing-hub:   HUB_NAME = "billing-hub"
# trading-hub:   HUB_NAME = "trading-hub"
# cad-hub:       HUB_NAME = "cad-hub"
# research-hub:  HUB_NAME = "research-hub"
# mcp-hub:       HUB_NAME = "mcp-hub"
# doc-hub:       HUB_NAME = "doc-hub"
# bfagent:       HUB_NAME = "bfagent"
# dev-hub:       HUB_NAME = "dev-hub"
