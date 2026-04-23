"""
Pytest configuration for bfagent-core tests.
"""

import os
import sys
import django
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")


def pytest_configure():
    """Configure Django for pytest."""
    django.setup()
