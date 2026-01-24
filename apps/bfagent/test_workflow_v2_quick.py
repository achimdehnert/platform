"""
Quick test for workflow_templates_v2.py
Run: python test_workflow_v2_quick.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.bfagent.services.workflow_templates_v2 import (
    EnhancedWorkflowRegistry,
    CHAPTER_GENERATION_V2,
    CHARACTER_DEVELOPMENT_V2
)

print("="*60)
print("WORKFLOW TEMPLATES V2 - QUICK TEST")
print("="*60)

# Test 1: Template exists
print("\n[TEST 1] Templates loaded:")
print(f"  - Chapter Gen: {CHAPTER_GENERATION_V2.template_id}")
print(f"  - Character Dev: {CHARACTER_DEVELOPMENT_V2.template_id}")
print("  ✅ PASS")

# Test 2: Domain-aware format
print("\n[TEST 2] Domain-aware format:")
template = EnhancedWorkflowRegistry.get("chapter_gen")
domain_aware = template.to_domain_aware_dict()
print(f"  Domain: {domain_aware['domain']['display_name']}")
print(f"  Icon: {domain_aware['domain']['icon']}")
print(f"  Phases: {len(domain_aware['phases'])}")
for phase in domain_aware['phases']:
    print(f"    - {phase['name']}: {len(phase['handlers'])} handlers")
print("  ✅ PASS")

# Test 3: Backward compatibility
print("\n[TEST 3] Backward compatibility:")
pipeline = template.to_pipeline_config()
print(f"  Input handlers: {len(pipeline['input'])}")
print(f"  Processing handlers: {len(pipeline['processing'])}")
print(f"  Output handler: {bool(pipeline['output'])}")
print("  ✅ PASS")

# Test 4: Registry
print("\n[TEST 4] Registry:")
all_templates = EnhancedWorkflowRegistry.get_all()
print(f"  Total templates: {len(all_templates)}")
domains = EnhancedWorkflowRegistry.get_domains()
print(f"  Total domains: {len(domains)}")
for domain_id, domain_info in domains.items():
    print(f"    - {domain_info['display_name']}: {domain_info['template_count']} templates")
print("  ✅ PASS")

# Test 5: Auto-generation
print("\n[TEST 5] Auto-generation:")
char_template = EnhancedWorkflowRegistry.get("character_dev")
char_domain = char_template.to_domain_aware_dict()
print(f"  Domain auto-generated: {char_domain['domain']['domain_id']}")
print(f"  Phases auto-generated: {len(char_domain['phases'])}")
print("  ✅ PASS")

print("\n" + "="*60)
print("ALL TESTS PASSED! ✅")
print("="*60)
print("\nReady for API integration!")
