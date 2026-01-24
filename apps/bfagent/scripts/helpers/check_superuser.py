#!/usr/bin/env python
"""
Check if superuser exists and list all superusers
Run with: python scripts/check_superuser.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*60)
print("DJANGO SUPERUSER CHECK")
print("="*60)

superusers = User.objects.filter(is_superuser=True)

if superusers.exists():
    print(f"\n✅ Found {superusers.count()} superuser(s):")
    for user in superusers:
        print(f"\n   Username: {user.username}")
        print(f"   Email: {user.email or '(not set)'}")
        print(f"   Active: {user.is_active}")
        print(f"   Last login: {user.last_login or 'Never'}")
else:
    print("\n❌ No superusers found!")
    print("\nCreate one with:")
    print("   python manage.py createsuperuser")

print("\n" + "="*60 + "\n")
