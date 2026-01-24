"""
Clear translation cache and reset presentation status
"""
import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.medtrans.models import Presentation

# Clear cache
cache_file = r'C:\Users\achim\github\bfagent\cache\translation_cache.json'
if os.path.exists(cache_file):
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({}, f)
    print(f'✅ Cache cleared: {cache_file}')
else:
    print(f'⚠️  Cache file not found: {cache_file}')

# Reset presentation 2 to uploaded status
p = Presentation.objects.get(id=2)
p.status = 'uploaded'
p.save()

print(f'✅ Presentation {p.id} status reset to: {p.status}')
print(f'   File: {p.filename}')
print(f'   Customer: {p.customer.customer_name}')
