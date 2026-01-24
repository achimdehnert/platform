import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models_domains import DomainArt
from django.db import connection

print("=== Testing DomainArt Model ===\n")

# Test 1: Count
count = DomainArt.objects.count()
print(f"1. Django ORM Count: {count}")

# Test 2: Try to get expert-hub
try:
    domain = DomainArt.objects.get(slug='expert-hub')
    print(f"2. ✅ Found expert-hub: {domain.display_name}")
except DomainArt.DoesNotExist:
    print("2. ❌ Django ORM: expert-hub NOT FOUND")

# Test 3: List all domains
all_domains = DomainArt.objects.all()
print(f"\n3. All domains from Django ORM:")
for d in all_domains:
    print(f"   - {d.slug}: {d.display_name}")

# Test 4: Raw SQL
print(f"\n4. Raw SQL Query:")
with connection.cursor() as cursor:
    cursor.execute("SELECT id, slug, display_name FROM domain_arts LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f"   - {row[1]}: {row[2]}")

# Test 5: Check model metadata
print(f"\n5. Model Metadata:")
print(f"   - Table: {DomainArt._meta.db_table}")
print(f"   - Fields: {[f.name for f in DomainArt._meta.fields]}")
