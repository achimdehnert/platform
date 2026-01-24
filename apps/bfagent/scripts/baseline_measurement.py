#!/usr/bin/env python
"""Baseline-Messung für DjangoAgent Erfolgs-Metriken."""
import os
import sys
import django

# Django Setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models_testing import TestRequirement
from django.utils import timezone
from datetime import timedelta

def measure_baseline():
    """Misst die Baseline für Django-bezogene Fehler."""
    since = timezone.now() - timedelta(days=30)
    reqs = TestRequirement.objects.filter(created_at__gte=since)
    
    print("=" * 60)
    print("BASELINE MESSUNG - DjangoAgent")
    print("=" * 60)
    print(f"Zeitraum: Letzte 30 Tage")
    print(f"Gesamt Requirements: {reqs.count()}")
    print()
    
    # Nach Kategorie
    print("Nach Kategorie:")
    for cat in ['bug', 'feature', 'enhancement']:
        count = reqs.filter(category=cat).count()
        print(f"  {cat}: {count}")
    
    print()
    print("Django-Fehler-Typen (Baseline):")
    print("-" * 40)
    
    # Template-Fehler
    template_count = reqs.filter(description__icontains='template').count()
    template_count += reqs.filter(name__icontains='template').count()
    print(f"  Template-bezogen: {template_count}")
    
    # URL-Fehler
    url_count = reqs.filter(description__icontains='url').count()
    url_count += reqs.filter(description__icontains='reverse').count()
    print(f"  URL/Reverse-bezogen: {url_count}")
    
    # Import-Fehler
    import_count = reqs.filter(description__icontains='import').count()
    print(f"  Import-bezogen: {import_count}")
    
    # Static-Fehler
    static_count = reqs.filter(description__icontains='static').count()
    print(f"  Static-bezogen: {static_count}")
    
    # Syntax-Fehler
    syntax_count = reqs.filter(description__icontains='syntax').count()
    print(f"  Syntax-bezogen: {syntax_count}")
    
    print()
    print("=" * 60)
    total_django = template_count + url_count + import_count + static_count + syntax_count
    print(f"GESAMT Django-bezogene Issues: {total_django}")
    print("=" * 60)
    
    # Speichere als JSON für späteren Vergleich
    import json
    baseline = {
        "date": timezone.now().isoformat(),
        "period_days": 30,
        "total_requirements": reqs.count(),
        "by_category": {
            "bug": reqs.filter(category='bug').count(),
            "feature": reqs.filter(category='feature').count(),
            "enhancement": reqs.filter(category='enhancement').count(),
        },
        "django_errors": {
            "template": template_count,
            "url": url_count,
            "import": import_count,
            "static": static_count,
            "syntax": syntax_count,
            "total": total_django,
        }
    }
    
    with open('docs/DJANGO_AGENT_BASELINE.json', 'w') as f:
        json.dump(baseline, f, indent=2)
    print(f"\nBaseline gespeichert: docs/DJANGO_AGENT_BASELINE.json")

if __name__ == '__main__':
    measure_baseline()
