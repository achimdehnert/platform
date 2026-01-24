# Local Development Settings Override
# Using PostgreSQL for local development

import os

# Use PostgreSQL (matches main settings.py)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "bfagent_dev"),
        "USER": os.environ.get("POSTGRES_USER", "bfagent"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "bfagent_dev_2024"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

print("✅ Using PostgreSQL Database (settings_local.py)")
print(
    f"📁 Database: {DATABASES['default']['NAME']} @ {DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}"
)
