#!/usr/bin/env python
"""Test CodeQualityAgent - Complexity, Code Smells, Dead Code Detection."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.bfagent.agents import CodeQualityAgent, analyze_code_quality, quick_quality_check

agent = CodeQualityAgent()

# =============================================================================
# TEST CASES
# =============================================================================

test_cases = [
    ("Simple Clean Code", """
def greet(name: str) -> str:
    \"\"\"Greet a person.\"\"\"
    return f"Hello, {name}!"
"""),

    ("Complex Function", """
def complex_logic(data, options=None):
    result = []
    if options:
        if options.get('filter'):
            for item in data:
                if item.get('active'):
                    if item.get('value') > 10:
                        if item.get('type') == 'A':
                            result.append(item)
                        elif item.get('type') == 'B':
                            result.append(item)
                        else:
                            pass
    return result
"""),

    ("Code Smells", """
def process(items=[]):  # Mutable default!
    pass

def unused_function():
    pass

# def old_code():
#     return True

result = 12345  # Magic number
"""),

    ("Empty Exception", """
def risky():
    try:
        do_something()
    except:
        pass
"""),

    ("Good Documentation", '''
class UserService:
    """Service for user operations."""
    
    def get_user(self, user_id: int):
        """Get user by ID."""
        pass
    
    def create_user(self, data: dict):
        """Create a new user."""
        pass
'''),
]

print("=" * 60)
print("CODE QUALITY AGENT TESTS")
print("=" * 60)

for name, code in test_cases:
    report = agent.analyze(code, f"{name.lower().replace(' ', '_')}.py")
    
    print(f"\n{'=' * 50}")
    print(f"TEST: {name}")
    print(f"{'=' * 50}")
    print(f"Grade: {report.overall_grade}")
    print(f"Complexity: {report.complexity_score:.1f}")
    print(f"Doc Coverage: {report.doc_coverage:.0f}%")
    
    if report.complexity_details:
        print(f"\nFunctions:")
        for c in report.complexity_details:
            print(f"  - {c.function_name}: CC={c.complexity} ({c.rating})")
    
    if report.code_smells:
        print(f"\nCode Smells ({len(report.code_smells)}):")
        for smell in report.code_smells:
            print(f"  ⚠️ [{smell['type']}] {smell['message']}")
    
    if report.dead_code:
        print(f"\nDead Code ({len(report.dead_code)}):")
        for dead in report.dead_code:
            print(f"  💀 {dead['name']} at line {dead['line']}")

# Test quick_quality_check
print("\n" + "=" * 60)
print("QUICK CHECK TEST")
print("=" * 60)

grade, issues = quick_quality_check("""
def bad_code(items=[]):
    x = 99999
    print("debug")
    try:
        pass
    except:
        pass
""")

print(f"Grade: {grade}")
print(f"Issues: {len(issues)}")
for issue in issues:
    print(f"  - {issue}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE! ✅")
print("=" * 60)
