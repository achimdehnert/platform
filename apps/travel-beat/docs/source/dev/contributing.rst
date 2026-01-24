Contributing Guide
==================

Thank you for your interest in contributing to Travel Beat!

Development Setup
-----------------

1. Fork and clone the repository
2. Follow :doc:`../installation` for local setup
3. Create a feature branch

Code Style
----------

**Python:**

- Follow PEP 8
- Use type hints where practical
- Maximum line length: 100 characters
- Use Black for formatting

**Templates:**

- Use Django template language
- Keep logic minimal in templates
- Use template tags for complex logic

**JavaScript:**

- ES6+ syntax
- Prefer HTMX over custom JS

Running Tests
-------------

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=apps

   # Run specific app tests
   pytest apps/trips/

Writing Tests
-------------

- Place tests in ``tests/`` directory within each app
- Use pytest fixtures for common setup
- Test both happy path and edge cases

Example:

.. code-block:: python

   import pytest
   from apps.trips.models import Trip

   @pytest.fixture
   def trip(user):
       return Trip.objects.create(
           user=user,
           name="Test Trip",
           origin="Berlin"
       )

   def test_trip_str(trip):
       assert str(trip) == "Test Trip"

Pull Request Process
--------------------

1. Create a feature branch from ``main``
2. Make your changes with clear commits
3. Update documentation if needed
4. Run tests locally
5. Open a pull request

PR titles should follow conventional commits:

- ``feat: Add new feature``
- ``fix: Fix bug in wizard``
- ``docs: Update API documentation``
- ``refactor: Improve code structure``

Code Review
-----------

All PRs require review before merging:

- Code quality and style
- Test coverage
- Documentation updates
- No breaking changes (or properly documented)

Release Process
---------------

1. Merge approved PRs to ``main``
2. CI/CD automatically deploys to production
3. Monitor logs for issues
4. Tag release if significant

Getting Help
------------

- Open an issue for bugs
- Use discussions for questions
- Check existing issues before creating new ones
