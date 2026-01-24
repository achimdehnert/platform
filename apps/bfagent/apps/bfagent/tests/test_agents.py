import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from bfagent.forms import AgentsForm
from bfagent.models import Agents

User = get_user_model()


@pytest.mark.django_db
class TestAgentsViews:
    """Test cases for Agents views"""

    @pytest.fixture
    def user(self):
        """Create test user"""
        return User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

    @pytest.fixture
    def agents(self, user):
        """Create test Agents instance"""
        # CUSTOM_CODE_START: fixture_setup
        # Customize the fixture creation
        return Agents.objects.create(
            agentexecutions="test",
            agentartifacts="test",
            name="Test Name",
            agent_type="test_value",
            status="test_value",
            system_prompt="Test content\nWith multiple lines",
            creativity_level="10.50",
            consistency_weight="10.50",
            total_requests="test",
            successful_requests="test",
            average_response_time="10.50",
        )
        # CUSTOM_CODE_END:

    def test_list_view_requires_login(self, client):
        """Test list view requires authentication"""
        url = reverse("bfagent:agents-list")
        response = client.get(url)
        assert response.status_code == 302  # Redirect to login

    def test_list_view(self, client, user, agents):
        """Test Agents list view"""
        client.force_login(user)
        url = reverse("bfagent:agents-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "agentss" in response.context
        assert agents in response.context["agentss"]

    def test_list_view_search(self, client, user, agents):
        """Test list view search functionality"""
        client.force_login(user)
        url = reverse("bfagent:agents-list")

        # CUSTOM_CODE_START: search_test
        # Customize search test based on your search fields
        response = client.get(url, {"search": "test"})
        assert response.status_code == 200
        # CUSTOM_CODE_END:

    def test_create_view_get(self, client, user):
        """Test Agents create view GET request"""
        client.force_login(user)
        url = reverse("bfagent:agents-create")
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context["form"], AgentsForm)

    def test_create_view_post(self, client, user):
        """Test Agents create view POST request"""
        client.force_login(user)
        url = reverse("bfagent:agents-create")

        data = {
            "agentexecutions": "test",
            "agentartifacts": "test",
            "name": "Test Name",
            "agent_type": "test_value",
            "status": "test_value",
            "description": "Test description content",
            "system_prompt": "Test content\nWith multiple lines",
            "instructions": "Test content\nWith multiple lines",
            "llm_model_id": "test",
            "creativity_level": "10.50",
            "consistency_weight": "10.50",
            "total_requests": "test",
            "successful_requests": "test",
            "average_response_time": "10.50",
            "last_used_at": "2024-01-01T12:00:00Z",
        }

        response = client.post(url, data)

        # Should redirect after successful creation
        assert response.status_code == 302
        assert Agents.objects.count() == 1

        created = Agents.objects.first()
        # CUSTOM_CODE_START: create_assertions
        # Add custom assertions for created object
        # CUSTOM_CODE_END:

    def test_create_view_htmx(self, client, user):
        """Test Agents create view with HTMX"""
        client.force_login(user)
        url = reverse("bfagent:agents-create")

        data = {
            "agentexecutions": "test",
            "agentartifacts": "test",
            "name": "Test Name",
            "agent_type": "test_value",
            "status": "test_value",
            "description": "Test description content",
            "system_prompt": "Test content\nWith multiple lines",
            "instructions": "Test content\nWith multiple lines",
            "llm_model_id": "test",
            "creativity_level": "10.50",
            "consistency_weight": "10.50",
            "total_requests": "test",
            "successful_requests": "test",
            "average_response_time": "10.50",
            "last_used_at": "2024-01-01T12:00:00Z",
        }

        # Simulate HTMX request
        response = client.post(url, data, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert "<table" in response.content.decode()

    def test_update_view_get(self, client, user, agents):
        """Test Agents update view GET request"""
        client.force_login(user)
        url = reverse("bfagent:agents-edit", kwargs={"pk": agents.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert isinstance(response.context["form"], AgentsForm)
        assert response.context["form"].instance == agents

    def test_update_view_post(self, client, user, agents):
        """Test Agents update view POST request"""
        client.force_login(user)
        url = reverse("bfagent:agents-edit", kwargs={"pk": agents.pk})

        data = {
            "agentexecutions": "test",
            "agentartifacts": "test",
            "name": "Test Name",
            "agent_type": "test_value",
            "status": "test_value",
            "description": "Test description content",
            "system_prompt": "Test content\nWith multiple lines",
            "instructions": "Test content\nWith multiple lines",
            "llm_model_id": "test",
            "creativity_level": "10.50",
            "consistency_weight": "10.50",
            "total_requests": "test",
            "successful_requests": "test",
            "average_response_time": "10.50",
            "last_used_at": "2024-01-01T12:00:00Z",
            # CUSTOM_CODE_START: update_data
            # Modify data for update test
            # CUSTOM_CODE_END:
        }

        response = client.post(url, data)

        assert response.status_code == 302
        agents.refresh_from_db()

        # CUSTOM_CODE_START: update_assertions
        # Add assertions to verify update
        # CUSTOM_CODE_END:

    def test_delete_view_get(self, client, user, agents):
        """Test Agents delete view GET request"""
        client.force_login(user)
        url = reverse("bfagent:agents-delete", kwargs={"pk": agents.pk})
        response = client.get(url)

        assert response.status_code == 200

    def test_delete_view_post(self, client, user, agents):
        """Test Agents delete view POST request"""
        client.force_login(user)
        url = reverse("bfagent:agents-delete", kwargs={"pk": agents.pk})

        response = client.post(url)

        assert response.status_code == 302
        assert Agents.objects.count() == 0

    def test_delete_view_htmx(self, client, user, agents):
        """Test Agents delete with HTMX"""
        client.force_login(user)
        url = reverse("bfagent:agents-delete", kwargs={"pk": agents.pk})

        response = client.delete(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 204
        assert Agents.objects.count() == 0

    def test_detail_view(self, client, user, agents):
        """Test Agents detail view"""
        client.force_login(user)
        url = reverse("bfagent:agents-detail", kwargs={"pk": agents.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["agents"] == agents


@pytest.mark.django_db
class TestAgentsForm:
    """Test cases for AgentsForm"""

    def test_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            "agentexecutions": "test",
            "agentartifacts": "test",
            "name": "Test Name",
            "agent_type": "test_value",
            "status": "test_value",
            "description": "Test description content",
            "system_prompt": "Test content\nWith multiple lines",
            "instructions": "Test content\nWith multiple lines",
            "llm_model_id": "test",
            "creativity_level": "10.50",
            "consistency_weight": "10.50",
            "total_requests": "test",
            "successful_requests": "test",
            "average_response_time": "10.50",
            "last_used_at": "2024-01-01T12:00:00Z",
        }

        form = AgentsForm(data=form_data)
        assert form.is_valid()

    def test_form_missing_required_fields(self):
        """Test form with missing required fields"""
        form = AgentsForm(data={})
        assert not form.is_valid()

        # CUSTOM_CODE_START: form_validation_tests
        # Add specific field validation tests
        # CUSTOM_CODE_END:

    def test_form_widgets(self):
        """Test form widgets are properly configured"""
        form = AgentsForm()

        # CUSTOM_CODE_START: widget_tests
        # Add widget-specific tests
        # CUSTOM_CODE_END:


# CUSTOM_CODE_START: additional_tests
# Add any additional test classes or functions here
# CUSTOM_CODE_END:
