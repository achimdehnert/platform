#!/usr/bin/env python
"""Liste alle Domains im System"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models_domains import DomainArt

def list_domains():
    domains = DomainArt.objects.all().order_by('id')
    
    print("\n" + "="*90)
    print("ALLE DOMAINS IM SYSTEM")
    print("="*90 + "\n")
    
    for d in domains:
        status = "AKTIV" if d.is_active else "INAKTIV"
        exp = " [EXPERIMENTAL]" if d.is_experimental else ""
        
        print(f"{d.display_name}")
        print(f"  ID:        {d.id}")
        print(f"  Slug:      {d.slug}")
        print(f"  Status:    {status}{exp}")
        print(f"  Icon:      {d.icon if d.icon else '-'}")
        print(f"  Color:     {d.color if d.color else '-'}")
        if d.description:
            print(f"  Info:      {d.description[:80]}...")
        print()
    
    print("="*90)
    active_count = len([d for d in domains if d.is_active])
    inactive_count = len([d for d in domains if not d.is_active])
    print(f"Gesamt: {domains.count()} Domains ({active_count} aktiv, {inactive_count} inaktiv)")
    print("="*90)

if __name__ == "__main__":
    list_domains()
