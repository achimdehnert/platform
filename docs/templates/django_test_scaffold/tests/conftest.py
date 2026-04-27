"""conftest.py — Django Repo Test-Konfiguration.

Kopiere diese Datei nach {repo}/tests/conftest.py.
Passe DJANGO_SETTINGS_MODULE in pyproject.toml an.

Voraussetzungen (requirements-test.txt):
    iil-testkit[smoke]>=0.4.0
    pytest-django>=4.8
    pytest-cov>=5.0
    beautifulsoup4>=4.12
"""
pytest_plugins = ["iil_testkit.fixtures"]
