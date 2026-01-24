"""
Quick script to reset presentation status
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.medtrans.models import Presentation

# Reset presentation 2 to uploaded status
p = Presentation.objects.get(id=2)
p.status = 'uploaded'
p.save()

print(f'✅ Presentation {p.id} status reset to: {p.status}')
print(f'   File: {p.filename}')
print(f'   Customer: {p.customer.customer_name}')
