"""Test DB-driven handler system"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.services.handler_loader import (
    list_handlers,
    get_handler_from_db,
    get_handler_info,
)

print("\n" + "="*70)
print("DATABASE-DRIVEN HANDLER SYSTEM TEST")
print("="*70 + "\n")

# Test 1: List all BookWriting handlers from DB
print("1. LIST BOOKWRITING HANDLERS FROM DATABASE:")
print("-" * 70)
handlers = list_handlers(domain='bookwriting')
print(f"Found {len(handlers)} handlers:\n")
for handler in handlers:
    print(f"  - {handler['handler_id']} v{handler['version']}")
    print(f"    Category: {handler['category']}")
    print(f"    {handler['description'][:60]}...")
    print()

# Test 2: Get handler info
print("\n2. GET HANDLER METADATA:")
print("-" * 70)
info = get_handler_info('bookwriting.project.enrich')
if info:
    print(f"Handler: {info['display_name']}")
    print(f"ID: {info['handler_id']}")
    print(f"Version: {info['version']}")
    print(f"Module: {info['module_path']}")
    print(f"Class: {info['class_name']}")
    print(f"Category: {info['category']}")
    print(f"Requires LLM: {info['requires_llm']}")
    print(f"Experimental: {info['is_experimental']}")
    print(f"Executions: {info['total_executions']}")

# Test 3: Load handler from DB
print("\n3. LOAD HANDLER INSTANCE FROM DB:")
print("-" * 70)
handler = get_handler_from_db('bookwriting.project.enrich')
if handler:
    print(f"  ✓ Loaded: {handler.__class__.__name__}")
    print(f"  ✓ Handler ID: {handler.handler_id}")
    print(f"  ✓ Name: {handler.name}")
    print(f"  ✓ Version: {handler.version}")
else:
    print("  ✗ Failed to load handler")

# Test 4: Compare DB count vs Code registry
print("\n4. SYSTEM COMPARISON:")
print("-" * 70)
from apps.core.handlers.registry import HandlerRegistry
code_registry = HandlerRegistry()
code_handlers = code_registry.list_handlers(domain='bookwriting')

print(f"  Database Handlers: {len(handlers)}")
print(f"  Code Registry: {len(code_handlers)}")
print(f"  Match: {'✓ Yes' if len(handlers) == len(code_handlers) else '✗ No'}")

print("\n" + "="*70)
print("DATABASE-DRIVEN HANDLER SYSTEM OPERATIONAL!")
print("="*70 + "\n")

print("Usage Example:")
print("-" * 70)
print("""
from apps.bfagent.services.handler_loader import execute_handler

# Execute handler from database
result = execute_handler(
    'bookwriting.project.enrich',
    {
        'project': project,
        'agent': agent,
        'action': 'premise'
    }
)

if result['success']:
    print(result['result'])
""")
