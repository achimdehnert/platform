"""
WSGI config for CAD-Hub.
"""

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cad_services.django.settings")

application = get_wsgi_application()
