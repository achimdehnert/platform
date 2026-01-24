#!/usr/bin/env python
"""
Real installation test for domain system
Run with: python apps/genagent/domains/test_real_install.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.genagent.domains import install_domain, DomainRegistry
from apps.genagent.models import Phase, Action

# Import book template to trigger auto-registration
from apps.genagent.domains.templates import book  # noqa: F401


def test_real_installation():
    """Test real database installation"""
    print("\n" + "="*70)
    print("REAL INSTALLATION TEST - Book Domain")
    print("="*70)
    
    # Test context
    context = {
        'title': 'My Epic Fantasy Novel',
        'genre': 'fantasy',
        'target_audience': 'young_adult',
        'name': 'Test Author'
    }
    
    print("\n[INFO] Context:")
    for key, value in context.items():
        print(f"   - {key}: {value}")
    
    # Verify domain is registered
    print("\n[INFO] Checking domain registration...")
    if not DomainRegistry.exists('book'):
        print("[ERROR] Book domain not registered!")
        print(f"Available domains: {DomainRegistry.list_ids()}")
        return False
    print("[OK] Book domain is registered")
    
    # Get initial counts
    initial_phase_count = Phase.objects.count()
    initial_action_count = Action.objects.count()
    
    print(f"\n[INFO] Database before installation:")
    print(f"   - Phases: {initial_phase_count}")
    print(f"   - Actions: {initial_action_count}")
    
    # Install domain
    print("\n[INFO] Installing book domain...")
    try:
        phase_id = install_domain('book', context, dry_run=False)
        print(f"[SUCCESS] Domain installed! First phase ID: {phase_id}")
    except Exception as e:
        print(f"[ERROR] Installation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Get final counts
    final_phase_count = Phase.objects.count()
    final_action_count = Action.objects.count()
    
    print(f"\n[INFO] Database after installation:")
    print(f"   - Phases: {final_phase_count} (+{final_phase_count - initial_phase_count})")
    print(f"   - Actions: {final_action_count} (+{final_action_count - initial_action_count})")
    
    # Display created objects
    if phase_id:
        print("\n[INFO] Created phases:")
        # Get the newly created phases (starting from phase_id)
        phases = Phase.objects.filter(id__gte=phase_id).order_by('order')
        for phase in phases:
            print(f"   [{phase.id}] {phase.name}")
            print(f"       Order: {phase.order}, Color: {phase.color}")
            
            actions = phase.actions.all()
            if actions:
                print(f"       Actions ({actions.count()}):")
                for action in actions:
                    print(f"         - [{action.id}] {action.name}")
                    print(f"           Handler: {action.handler_class}")
    
    print("\n" + "="*70)
    print("[SUCCESS] REAL INSTALLATION TEST COMPLETED!")
    print("="*70)
    print("\n[INFO] Next steps:")
    print("   1. Check Django admin: http://127.0.0.1:8000/admin/genagent/phase/")
    print("   2. Execute workflow with these phases")
    print("   3. Create more domain templates")
    print("\n")
    
    return True


if __name__ == '__main__':
    success = test_real_installation()
    sys.exit(0 if success else 1)
