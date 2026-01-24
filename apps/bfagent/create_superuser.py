#!/usr/bin/env python
"""
Quick Superuser Creator
=======================

Creates or resets Django superuser with known credentials.
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Superuser credentials
USERNAME = "admin"
EMAIL = "admin@bfagent.local"
PASSWORD = "admin"

print("\n" + "=" * 60)
print("🔧 Django Superuser Setup")
print("=" * 60 + "\n")

# Check if user exists
try:
    user = User.objects.get(username=USERNAME)
    print(f"ℹ️  User '{USERNAME}' already exists")

    # Reset password
    user.set_password(PASSWORD)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.email = EMAIL
    user.save()

    print(f"✅ Password reset to: {PASSWORD}")
    print(f"✅ Superuser status: Enabled")
    print(f"✅ Staff status: Enabled")

except User.DoesNotExist:
    # Create new superuser
    print(f"📝 Creating new superuser '{USERNAME}'...")

    user = User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)

    print(f"✅ Superuser created!")

print("\n" + "=" * 60)
print("🎉 READY TO LOGIN")
print("=" * 60)
print(f"\n📍 URL: http://localhost:8000/admin/")
print(f"👤 Username: {USERNAME}")
print(f"🔑 Password: {PASSWORD}")
print("\n" + "=" * 60 + "\n")
