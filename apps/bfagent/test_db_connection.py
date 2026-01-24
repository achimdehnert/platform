#!/usr/bin/env python
"""
Test PostgreSQL connection directly with our custom backend
"""
import os
import sys

import django

# Force UTF-8
os.environ["PYTHONUTF8"] = "1"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

# Now test the connection
from django.db import connection

print("=" * 80)
print("TESTING POSTGRESQL CONNECTION WITH CUSTOM BACKEND")
print("=" * 80)

try:
    print("\n1. Testing database backend...")
    print(f"   Engine: {connection.settings_dict['ENGINE']}")
    print(f"   Database: {connection.settings_dict['NAME']}")
    print(f"   Host: {connection.settings_dict['HOST']}")
    print(f"   Port: {connection.settings_dict['PORT']}")

    print("\n2. Getting connection parameters...")
    conn_params = connection.get_connection_params()
    print(f"   Parameters: {list(conn_params.keys())}")

    print("\n3. Attempting to connect...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   ✅ SUCCESS! PostgreSQL version: {version[0][:50]}...")

    print("\n" + "=" * 80)
    print("✅ CONNECTION TEST PASSED!")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ CONNECTION FAILED!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")

    # Show more details for UnicodeDecodeError
    if isinstance(e, UnicodeDecodeError):
        print(f"\nUnicodeDecodeError details:")
        print(f"  Encoding: {e.encoding}")
        print(f"  Position: {e.start}-{e.end}")
        print(f"  Reason: {e.reason}")
        if hasattr(e, "object"):
            print(f"  Object (first 200 bytes): {e.object[:200]}")

    import traceback

    print("\nFull traceback:")
    traceback.print_exc()

    print("\n" + "=" * 80)
    sys.exit(1)
