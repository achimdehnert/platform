#!/usr/bin/env python
"""
Simple test runner for domain system
Run with: python apps/genagent/domains/run_tests.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Now import test function
from test_domains import test_domain_system

if __name__ == '__main__':
    success = test_domain_system()
    sys.exit(0 if success else 1)
