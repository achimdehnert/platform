import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAgentsHTMX422:
    def test_get_agent_create_form_contains_422_attrs(self, client):
        url = reverse("bfagent:agent-create")
        resp = client.get(url, HTTP_HX_REQUEST="true")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert 'hx-ext="response-targets"' in content
        assert 'hx-target-422="this"' in content
        assert 'hx-swap="outerHTML"' in content

    def test_post_invalid_agent_create_returns_422(self, client):
        url = reverse("bfagent:agent-create")
        # post with empty payload to trigger validation errors
        resp = client.post(url, data={}, HTTP_HX_REQUEST="true")
        assert resp.status_code == 422
        content = resp.content.decode()
        # form should be returned again
        assert "form" in content.lower() or "Please correct" in content
