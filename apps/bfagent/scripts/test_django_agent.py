#!/usr/bin/env python
"""Test DjangoAgent security, import, performance checks and auto-fix."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.agents.django_agent import DjangoAgent, auto_fix_code, validate_and_fix

agent = DjangoAgent()

# Test cases
test_cases = [
    # Security Tests
    ("SQL Injection", """
def get_users(query):
    User.objects.raw(f"SELECT * FROM users WHERE name = '{query}'")
"""),
    ("XSS", """
from django.utils.safestring import mark_safe
html = mark_safe(f"<div>{user_input}</div>")
"""),
    ("Hardcoded Secret", """
API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
"""),
    ("Debug Code", """
def my_view(request):
    print(request.POST)
    return HttpResponse("OK")
"""),
    ("Insecure Deserialize", """
import pickle
data = pickle.loads(request.body)
"""),
    
    # Performance Tests
    ("N+1 Query", """
for book in Book.objects.all():
    print(book.author.name)
"""),
    
    # Good Code (should pass)
    ("Clean Code", """
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=200)
    
    class Meta:
        ordering = ['title']
"""),
]

print("=" * 60)
print("DjangoAgent Security & Performance Tests")
print("=" * 60)

for name, code in test_cases:
    result = agent.validate_python_file(code, "test.py")
    
    status = "✅ PASS" if result.valid else "❌ ISSUES"
    print(f"\n{status} - {name}")
    
    if result.errors:
        print("  Errors:")
        for e in result.errors:
            print(f"    - [{e.rule}] {e.message} (Line {e.line})")
    
    if result.warnings:
        print("  Warnings:")
        for w in result.warnings:
            print(f"    - [{w.rule}] {w.message} (Line {w.line})")

print("\n" + "=" * 60)
print("AUTO-FIX Tests")
print("=" * 60)

# Auto-Fix Test Cases
fix_cases = [
    ("open() ohne encoding", """
with open("file.txt") as f:
    data = f.read()
"""),
    ("json.dumps ohne ensure_ascii", """
import json
result = json.dumps({"name": "Müller"})
"""),
    ("print in view", """
def my_view(request):
    print("Debug info")
    return HttpResponse("OK")
"""),
]

for name, code in fix_cases:
    result = auto_fix_code(code, "views.py" if "view" in name else "utils.py")
    
    status = "🔧 FIXED" if result.changed else "✅ NO CHANGE"
    print(f"\n{status} - {name}")
    
    if result.fixes_applied:
        for fix in result.fixes_applied:
            print(f"  → {fix}")
        print(f"  Before: {code.strip()[:50]}...")
        print(f"  After:  {result.fixed_code.strip()[:50]}...")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
