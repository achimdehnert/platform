"""
Test script for BookWriting handlers.

Usage:
    python manage.py shell < scripts/test_bookwriting_handlers.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.handlers.registry import HandlerRegistry
from apps.bfagent.models import BookProjects, Agents

print("\n" + "="*80)
print("TESTING BOOKWRITING HANDLERS")
print("="*80 + "\n")

# Initialize registry
registry = HandlerRegistry()

# Test 1: List registered handlers
print("1. REGISTERED HANDLERS:")
print("-" * 80)
handlers = registry.list_handlers(domain="bookwriting")
for handler_name, handler_info in handlers.items():
    print(f"  ✓ {handler_name} v{handler_info['version']}")
    print(f"    {handler_info['description']}")
print()

# Test 2: Get a handler
print("2. GET HANDLER TEST:")
print("-" * 80)
try:
    handler = registry.get("bookwriting.project.enrich")
    print(f"  ✓ Retrieved: {handler.name}")
    print(f"    ID: {handler.handler_id}")
    print(f"    Version: {handler.version}")
except Exception as e:
    print(f"  ✗ Error: {e}")
print()

# Test 3: Handler execution (if project and agent exist)
print("3. HANDLER EXECUTION TEST:")
print("-" * 80)

try:
    # Get first project and agent
    project = BookProjects.objects.first()
    agent = Agents.objects.first()
    
    if project and agent:
        print(f"  Using Project: {project.title}")
        print(f"  Using Agent: {agent.name}")
        
        # Test enrichment handler
        handler = registry.get("bookwriting.project.enrich")
        
        context = {
            'project': project,
            'agent': agent,
            'action': 'premise',
        }
        
        # Validate input
        is_valid, error = handler.validate_input(context)
        if is_valid:
            print(f"  ✓ Input validation passed")
        else:
            print(f"  ✗ Input validation failed: {error}")
        
    else:
        print("  ⚠ Skipping execution test (no project or agent in DB)")
        
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Domain handlers
print("4. DOMAIN ORGANIZATION:")
print("-" * 80)
domains = registry.list_domains()
for domain in domains:
    handlers = registry.list_by_domain(domain)
    print(f"  Domain: {domain}")
    print(f"  Handlers: {len(handlers)}")
    for handler_name in handlers:
        print(f"    - {handler_name}")
print()

print("="*80)
print("HANDLER TESTS COMPLETE")
print("="*80 + "\n")

print("Next steps:")
print("1. Test handler execution with real LLM")
print("2. Integrate handlers into views")
print("3. Create handler-specific tests")
print("4. Update documentation")
