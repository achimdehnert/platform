#!/usr/bin/env python
"""
Check available LLMs in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import Llms

print("=" * 70)
print("CHECKING AVAILABLE LLMs")
print("=" * 70)
print()

llms = Llms.objects.all()

if llms.count() == 0:
    print("❌ NO LLMs FOUND IN DATABASE!")
    print()
    print("Die 'llms' Tabelle ist leer.")
    print("Das erklärt warum das Dropdown leer ist.")
    print()
    print("LÖSUNG:")
    print("- LLMs müssen manuell in der Datenbank erstellt werden")
    print("- ODER über Admin Interface hinzugefügt werden")
    print("- ODER via Fixture/Script importiert werden")
else:
    print(f"✅ Found {llms.count()} LLMs:")
    print()
    for llm in llms:
        print(f"  ID: {llm.id}")
        print(f"  Name: {llm.name}")
        print(f"  Provider: {llm.provider}")
        print(f"  Model: {llm.model_name}")
        print(f"  Active: {llm.is_active}")
        print()

print("=" * 70)
