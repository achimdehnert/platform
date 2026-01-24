#!/usr/bin/env python
"""Check feedback content in database"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.bfagent.models_testing import RequirementFeedback

fb = RequirementFeedback.objects.filter(
    feedback_type='solution', 
    is_from_cascade=True
).last()

if fb:
    print("=" * 60)
    print(f"ID: {fb.id}")
    print(f"Type: {fb.feedback_type}")
    print(f"is_from_cascade: {fb.is_from_cascade}")
    print("=" * 60)
    print("Content (first 500 chars):")
    print(fb.content[:500])
    print("=" * 60)
    print("Content repr (first 200 chars):")
    print(repr(fb.content[:200]))
else:
    print("No feedback found")
