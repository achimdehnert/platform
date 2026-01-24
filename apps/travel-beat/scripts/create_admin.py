#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@travel-beat.iil.pet", "is_staff": True, "is_superuser": True}
)
u.set_password("TravelBeat2026!")
u.is_staff = True
u.is_superuser = True
u.save()
print(f"Superuser admin {'created' if created else 'updated'}")
