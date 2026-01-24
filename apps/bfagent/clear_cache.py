import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache
cache.clear()
print("[OK] Cache cleared!")

# Also clear template cache
from django.template.loader import get_template
from django.template.loaders import cached
print("[OK] Template loaders reset!")
