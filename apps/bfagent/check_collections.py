import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.presentation_studio.models import TemplateCollection, Presentation

print("\n=== TEMPLATE COLLECTIONS ===")
collections = TemplateCollection.objects.all()
print(f"Total: {collections.count()}")

for c in collections:
    print(f"\n  📦 {c.name}")
    print(f"     ID: {c.id}")
    print(f"     Templates: {c.template_count}")
    print(f"     Default: {c.is_default}")
    print(f"     Presentations using: {c.presentation_count}")

print("\n=== PRESENTATIONS ===")
presentations = Presentation.objects.all().order_by('-uploaded_at')[:3]
print(f"Total: {Presentation.objects.count()}")
print(f"Showing latest 3:")

for p in presentations:
    print(f"\n  📄 {p.title}")
    print(f"     ID: {p.id}")
    print(f"     Collection: {p.template_collection.name if p.template_collection else 'None'}")
    print(f"     Slides: {p.slide_count_enhanced or p.slide_count_original}")

print("\n")
