#!/usr/bin/env python3
"""Update production.py to add platform database."""
import re

settings_path = '/opt/weltenhub/repo/config/settings/production.py' # noqa: hardcode

with open(settings_path, 'r') as f:
    content = f.read()

new_databases = '''DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",
        },
    },
    "platform": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("PLATFORM_DB_NAME", default="platform"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("PLATFORM_DB_HOST", default="bfagent_db"),
        "PORT": config("DB_PORT", default="5432"),
        "OPTIONS": {
            "options": "-c search_path=platform,public"
        },
    }
}

DATABASE_ROUTERS = ["apps.governance.db_router.GovernanceRouter"]'''

# Replace DATABASES block
pattern = r'DATABASES = \{[^}]+\}[^}]+\}'
content = re.sub(pattern, new_databases, content)

with open(settings_path, 'w') as f:
    f.write(content)

print("Settings updated successfully!")
