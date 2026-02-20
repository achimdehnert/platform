# tests/conftest.py — ADR-057 §2.5 base fixture template
# Copy to tests/conftest.py in each service repo
# Adjust imports to match actual model paths

import pytest

# ---------------------------------------------------------------------------
# Adjust these imports to match your service's actual models
# ---------------------------------------------------------------------------
# from tests.factories import UserFactory, AssessmentFactory


@pytest.fixture
def user(db):
    """Standard authenticated user."""
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Admin user with superuser rights."""
    from tests.factories import UserFactory
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def authenticated_client(client, user):
    """Pre-authenticated Django test client."""
    client.force_login(user)
    return client
