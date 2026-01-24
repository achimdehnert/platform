"""
Travel Beat - Development Settings
"""

from .base import *

DEBUG = True

# Debug Toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Email - Console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allauth - No email verification in dev
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Celery - Eager execution for easier debugging
# CELERY_TASK_ALWAYS_EAGER = True  # Uncomment for sync debugging
