---
trigger: always_on
---

# Testing — Rules

> Glob-Activated: `**/tests/**`, `**/test_*.py`, `**/conftest.py`
> ADR-057, ADR-058 — Platform Test Strategy + Taxonomy

## Test Naming

- Functions: `test_should_{expected_behavior}` (NEVER `test_{thing}`)
- Example: `test_should_return_404_when_trip_not_found`
- Factory files: `factories.py` in each app's `tests/` dir

## pytest-django

```python
import pytest
from .factories import TripFactory, UserFactory


@pytest.mark.django_db
def test_should_create_trip_via_service(user_factory):
    user = user_factory()
    trip = trip_service.create_trip(user=user, title="Rome")
    assert trip.id is not None
    assert trip.user == user
```

## BANNED

- `unittest.TestCase` — use pytest functions
- `assert queryset.count() > 0` — use exact count
- Testing views with direct ORM — test through service layer
- Missing `@pytest.mark.django_db` on DB tests → silent failures
- More than 5 assertions per test function
- Test function longer than 30 lines

## Factory Boy

```python
import factory
from factory.django import DjangoModelFactory


class TripFactory(DjangoModelFactory):
    class Meta:
        model = Trip

    title = factory.Sequence(lambda n: f"Trip {n}")
    user = factory.SubFactory(UserFactory)
```

## Coverage

- Minimum: 80% per module
- Test views, services, and models separately
- Mock all external services (no real HTTP in unit tests)
