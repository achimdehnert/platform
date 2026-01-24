"""
Test script for Domain Template System

Run with: python manage.py shell < apps/genagent/domains/test_domains.py
Or: python manage.py shell -c "exec(open('apps/genagent/domains/test_domains.py', encoding='utf-8').read())"
"""

def test_domain_system():
    """Test the domain template system"""
    print("\n" + "="*70)
    print("TESTING GENAGENT DOMAIN SYSTEM")
    print("="*70)
    
    # Test 1: Import and Registry
    print("\n1. Testing Domain Template Import...")
    try:
        from apps.genagent.domains import DomainRegistry
        from apps.genagent.domains.templates import book
        print("   [OK] Imports successful")
    except Exception as e:
        print(f"   [ERROR] Import failed: {e}")
        return False

    # Test 2: Check Registry
    print("\n2. Testing Domain Registry...")
    try:
        count = DomainRegistry.count()
        print(f"   [OK] Registry contains {count} templates")

        if count > 0:
            print(f"   [INFO] Available domains: {', '.join(DomainRegistry.list_ids())}")
    except Exception as e:
        print(f"   [ERROR] Registry check failed: {e}")
        return False

    # Test 3: Get Book Template
    print("\n3. Testing Book Template Retrieval...")
    try:
        template = DomainRegistry.get('book')
        print(f"   [OK] Retrieved template: {template.display_name}")
        print(f"   [INFO] Phases: {len(template.phases)}")
        print(f"   [INFO] Total Actions: {len(template.get_all_actions())}")
    except Exception as e:
        print(f"   [ERROR] Template retrieval failed: {e}")
        return False

    # Test 4: Validate Template
    print("\n4. Testing Template Validation...")
    try:
        is_valid = template.validate()
        print(f"   [OK] Template validation: {is_valid}")
    except Exception as e:
        print(f"   [ERROR] Validation failed: {e}")
        return False

    # Test 5: Get Statistics
    print("\n5. Testing Template Statistics...")
    try:
        stats = template.get_statistics()
        print("   [OK] Statistics:")
        print(f"      - Total Phases: {stats['total_phases']}")
        print(f"      - Total Actions: {stats['total_actions']}")
        print(f"      - Required Phases: {stats['required_phases']}")
        print(f"      - Est. Duration: {stats['estimated_duration_hours']:.2f} hours")
    except Exception as e:
        print(f"   [ERROR] Statistics failed: {e}")
        return False

    # Test 6: Print Summary
    print("\n6. Domain Registry Summary:")
    try:
        DomainRegistry.print_summary()
    except Exception as e:
        print(f"   [ERROR] Summary failed: {e}")
        return False

    # Test 7: Installer Dry Run
    print("\n7. Testing Domain Installer (Dry Run)...")
    try:
        from apps.genagent.domains import install_domain

        test_context = {
            'title': 'My Test Novel',
            'genre': 'fantasy',
            'target_audience': 'young_adult',
            'name': 'Test User'
        }

        install_domain('book', test_context, dry_run=True)
        print("   [OK] Installer dry run complete (see output above)")
    except Exception as e:
        print(f"   [ERROR] Installer test failed: {e}")
        return False

    print("\n" + "="*70)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("="*70)
    print("\n[INFO] Next Steps:")
    print("   1. Run real installation: install_domain('book', context, dry_run=False)")
    print("   2. Create more domain templates")
    print("   3. Integrate with workflow UI")
    print("\n")

    return True




if __name__ == '__main__':
    test_domain_system()
