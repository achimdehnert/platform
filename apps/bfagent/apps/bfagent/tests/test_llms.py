import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from bfagent.forms import LlmsForm
from bfagent.models import Llms

User = get_user_model()


@pytest.mark.django_db
class TestLlmsViews:
    """Test cases for Llms views"""

    @pytest.fixture
    def user(self):
        """Create test user"""
        return User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

    @pytest.fixture
    def llms(self, user):
        """Create test Llms instance"""
        # CUSTOM_CODE_START: fixture_setup
        # Customize the fixture creation
        return Llms.objects.create(
            name="Test Name",
            provider="test_value",
            llm_name="Test Name",
            api_key="Test content\nWith multiple lines",
            api_endpoint="Test content\nWith multiple lines",
            max_tokens=42,
            temperature=3.14,
            top_p=3.14,
            frequency_penalty=3.14,
            presence_penalty=3.14,
            total_tokens_used=42,
            total_requests=42,
            total_cost=3.14,
            cost_per_1k_tokens=3.14,
            is_active=True,
        )
        # CUSTOM_CODE_END:

    def test_list_view_requires_login(self, client):
        """Test list view requires authentication"""
        url = reverse("bfagent:llms-list")
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login

    def test_list_view(self, client, user, llms):
        """Test Llms list view"""
        client.force_login(user)
        url = reverse("bfagent:llms-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "llmss" in response.context
        assert llms in response.context["llmss"]

    def test_list_view_search(self, client, user, llms):
        """Test list view search functionality"""
        client.force_login(user)
        url = reverse("bfagent:llms-list")

        # CUSTOM_CODE_START: search_test
        # Customize search test based on your search fields
        response = client.get(url, {"search": "test"})
        assert response.status_code == 200
        # CUSTOM_CODE_END:

    def test_create_view_get(self, client, user):
        """Test Llms create view GET request"""
        client.force_login(user)
        url = reverse("bfagent:llms-create")
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context["form"], LlmsForm)

    def test_create_view_post(self, client, user):
        """Test Llms create view POST request"""
        client.force_login(user)
        url = reverse("bfagent:llms-create")

        data = {
            "name": "Test Name",
            "provider": "test_value",
            "llm_name": "Test Name",
            "api_key": "Test content\nWith multiple lines",
            "api_endpoint": "Test content\nWith multiple lines",
            "max_tokens": 42,
            "temperature": 3.14,
            "top_p": 3.14,
            "frequency_penalty": 3.14,
            "presence_penalty": 3.14,
            "total_tokens_used": 42,
            "total_requests": 42,
            "total_cost": 3.14,
            "cost_per_1k_tokens": 3.14,
            "description": "Test description content",
            "is_active": True,
        }

        response = client.post(url, data)

        # Should redirect after successful creation
        assert response.status_code == 302
        assert Llms.objects.count() == 1

        created = Llms.objects.first()
        # CUSTOM_CODE_START: create_assertions
        # Add custom assertions for created object
        # CUSTOM_CODE_END:

    def test_create_view_htmx(self, client, user):
        """Test Llms create view with HTMX"""
        client.force_login(user)
        url = reverse("bfagent:llms-create")

        data = {
            "name": "Test Name",
            "provider": "test_value",
            "llm_name": "Test Name",
            "api_key": "Test content\nWith multiple lines",
            "api_endpoint": "Test content\nWith multiple lines",
            "max_tokens": 42,
            "temperature": 3.14,
            "top_p": 3.14,
            "frequency_penalty": 3.14,
            "presence_penalty": 3.14,
            "total_tokens_used": 42,
            "total_requests": 42,
            "total_cost": 3.14,
            "cost_per_1k_tokens": 3.14,
            "description": "Test description content",
            "is_active": True,
        }

        # Simulate HTMX request
        response = client.post(url, data, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert "<table" in response.content.decode()

    def test_update_view_get(self, client, user, llms):
        """Test Llms update view GET request"""
        client.force_login(user)
        url = reverse("bfagent:llms-edit", kwargs={"pk": llms.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context["form"], LlmsForm)
        assert response.context["form"].instance == llms

    def test_update_view_post(self, client, user, llms):
        """Test Llms update view POST request"""
        client.force_login(user)
        url = reverse("bfagent:llms-edit", kwargs={"pk": llms.pk})

        data = {
            "name": "Test Name",
            "provider": "test_value",
            "llm_name": "Test Name",
            "api_key": "Test content\nWith multiple lines",
            "api_endpoint": "Test content\nWith multiple lines",
            "max_tokens": 42,
            "temperature": 3.14,
            "top_p": 3.14,
            "frequency_penalty": 3.14,
            "presence_penalty": 3.14,
            "total_tokens_used": 42,
            "total_requests": 42,
            "total_cost": 3.14,
            "cost_per_1k_tokens": 3.14,
            "description": "Test description content",
            "is_active": True,
            # CUSTOM_CODE_START: update_data
            # Modify data for update test
            # CUSTOM_CODE_END:
        }

        response = client.post(url, data)

        assert response.status_code == 302
        llms.refresh_from_db()

        # CUSTOM_CODE_START: update_assertions
        # Add assertions to verify update
        # CUSTOM_CODE_END:

    def test_delete_view_get(self, client, user, llms):
        """Test Llms delete view GET request"""
        client.force_login(user)
        url = reverse("bfagent:llms-delete", kwargs={"pk": llms.pk})
        response = client.get(url)

        assert response.status_code == 200

    def test_delete_view_post(self, client, user, llms):
        """Test Llms delete view POST request"""
        client.force_login(user)
        url = reverse("bfagent:llms-delete", kwargs={"pk": llms.pk})

        response = client.post(url)

        assert response.status_code == 302
        assert Llms.objects.count() == 0

    def test_delete_view_htmx(self, client, user, llms):
        """Test Llms delete with HTMX"""
        client.force_login(user)
        url = reverse("bfagent:llms-delete", kwargs={"pk": llms.pk})

        response = client.delete(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 204
        assert Llms.objects.count() == 0

    def test_detail_view(self, client, user, llms):
        """Test Llms detail view"""
        client.force_login(user)
        url = reverse("bfagent:llms-detail", kwargs={"pk": llms.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["llms"] == llms


@pytest.mark.django_db
class TestLlmsForm:
    """Test cases for LlmsForm"""

    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            "name": "Test Name",
            "provider": "test_value",
            "llm_name": "Test Name",
            "api_key": "Test content\nWith multiple lines",
            "api_endpoint": "Test content\nWith multiple lines",
            "max_tokens": 42,
            "temperature": 3.14,
            "top_p": 3.14,
            "frequency_penalty": 3.14,
            "presence_penalty": 3.14,
            "total_tokens_used": 42,
            "total_requests": 42,
            "total_cost": 3.14,
            "cost_per_1k_tokens": 3.14,
            "description": "Test description content",
            "is_active": True,
        }

        form = LlmsForm(data=form_data)
        assert form.is_valid()

    def test_form_missing_required_fields(self):
        """Test form with missing required fields"""
        form = LlmsForm(data={})
        assert not form.is_valid()

        # CUSTOM_CODE_START: form_validation_tests
        # Add specific field validation tests
        # CUSTOM_CODE_END:

    def test_form_widgets(self):
        """Test form widgets are properly configured"""
        form = LlmsForm()

        # CUSTOM_CODE_START: widget_tests
        # Add widget-specific tests
        # CUSTOM_CODE_END:


# CUSTOM_CODE_START: additional_tests
# Add any additional test classes or functions here
# CUSTOM_CODE_END:
