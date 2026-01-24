import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.bfagent.forms import WorldsForm  # noqa: F401
from apps.bfagent.models import Worlds

User = get_user_model()


@pytest.mark.django_db
class TestWorldsViews:
    """Test cases for Worlds views"""

    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="testuser", password="testpass123")

    @pytest.fixture
    def worlds(self):
        # CUSTOM_CODE_START: fixture_setup
        # Customize the fixture creation
        return Worlds.objects.create(
            # Add required fields here
        )
        # CUSTOM_CODE_END:

    def test_list_view(self, client, user):
        """Test Worlds list view"""
        client.login(username="testuser", password="testpass123")
        url = reverse("bfagent:worlds_list")
        response = client.get(url)
        assert response.status_code == 200
        assert "worldss" in response.context

    def test_create_view(self, client, user):
        """Test Worlds create view"""
        client.login(username="testuser", password="testpass123")
        url = reverse("bfagent:worlds_create")
        response = client.get(url)
        assert response.status_code == 200

        # Test POST
        data = {
            # CUSTOM_CODE_START: test_data
            # Add test data here
            # CUSTOM_CODE_END:
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Worlds.objects.count() == 1

    def test_update_view(self, client, user, worlds):
        """Test Worlds update view"""
        client.login(username="testuser", password="testpass123")
        url = reverse("bfagent:worlds_edit", kwargs={"pk": worlds.pk})
        response = client.get(url)
        assert response.status_code == 200

        # Test POST
        data = {
            # CUSTOM_CODE_START: update_data
            # Add update data here
            # CUSTOM_CODE_END:
        }
        response = client.post(url, data)
        assert response.status_code == 302

    def test_delete_view(self, client, user, worlds):
        """Test Worlds delete view"""
        client.login(username="testuser", password="testpass123")
        url = reverse("bfagent:worlds_delete", kwargs={"pk": worlds.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert Worlds.objects.count() == 0

    def test_htmx_create(self, client, user):
        """Test HTMX create functionality"""
        client.login(username="testuser", password="testpass123")
        url = reverse("bfagent:worlds_create")
        data = {
            # CUSTOM_CODE_START: htmx_test_data
            # Add HTMX test data here
            # CUSTOM_CODE_END:
        }
        response = client.post(url, data, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert "<table" in response.content.decode()
