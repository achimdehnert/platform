#!/usr/bin/env python
"""Run the NANO-SEIN import"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    call_command('import_nano_sein', dry_run=dry_run, verbosity=2)
