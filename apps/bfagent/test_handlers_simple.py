"""Simple handler test"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.handlers.registry import HandlerRegistry

print("\n" + "="*60)
print("BOOKWRITING HANDLERS TEST")
print("="*60 + "\n")

registry = HandlerRegistry()

print("1. List all BookWriting handlers:")
handlers = registry.list_handlers(domain="bookwriting")
for name, info in handlers.items():
    print(f"  - {name} v{info['version']}")

print("\n2. Get a handler:")
handler = registry.get("bookwriting.project.enrich")
if handler:
    print(f"  - Retrieved: {handler.name}")
    print(f"  - Handler ID: {handler.handler_id}")
else:
    print("  - ERROR: Handler not found!")

print("\n3. List all domains:")
domains = registry.list_domains()
for domain in domains:
    count = len(registry.list_by_domain(domain))
    print(f"  - {domain}: {count} handlers")

print("\n" + "="*60)
print("TEST COMPLETE!")
print("="*60 + "\n")
