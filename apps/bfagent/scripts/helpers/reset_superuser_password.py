#!/usr/bin/env python
"""
Reset superuser password
Run with: python scripts/reset_superuser_password.py <username>
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

if len(sys.argv) < 2:
    print("\nUsage: python scripts/reset_superuser_password.py <username>")
    print("\nAvailable superusers:")
    superusers = User.objects.filter(is_superuser=True)
    if superusers.exists():
        for user in superusers:
            print(f"   - {user.username}")
    else:
        print("   (no superusers found)")
    sys.exit(1)

username = sys.argv[1]

try:
    user = User.objects.get(username=username)
    
    if not user.is_superuser:
        print(f"\n⚠️  User '{username}' exists but is not a superuser!")
        sys.exit(1)
    
    print(f"\n🔐 Resetting password for superuser: {username}")
    new_password = input("Enter new password: ")
    confirm_password = input("Confirm password: ")
    
    if new_password != confirm_password:
        print("\n❌ Passwords don't match!")
        sys.exit(1)
    
    user.set_password(new_password)
    user.save()
    
    print(f"\n✅ Password successfully reset for '{username}'")
    print(f"\nYou can now login at: http://127.0.0.1:8000/admin/")
    print(f"   Username: {username}")
    print(f"   Password: {new_password}")
    print()

except User.DoesNotExist:
    print(f"\n❌ User '{username}' not found!")
    print("\nCreate a new superuser with:")
    print("   python manage.py createsuperuser")
    sys.exit(1)
