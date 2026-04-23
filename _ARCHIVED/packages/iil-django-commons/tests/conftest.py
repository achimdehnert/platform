import pytest
from django.test import RequestFactory


@pytest.fixture
def rf():
    return RequestFactory()
