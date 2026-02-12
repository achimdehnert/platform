"""Tests for platform_context.middleware module."""

from platform_context.middleware import _parse_subdomain


class TestParseSubdomain:
    """Tests for subdomain extraction."""

    def test_should_extract_subdomain(self):
        assert _parse_subdomain("demo.risk-hub.de", "risk-hub.de") == "demo"

    def test_should_return_none_for_base_domain(self):
        assert _parse_subdomain("risk-hub.de", "risk-hub.de") is None

    def test_should_handle_localhost(self):
        assert _parse_subdomain("demo.localhost", "localhost") == "demo"

    def test_should_strip_port(self):
        assert _parse_subdomain("demo.localhost:8000", "localhost") == "demo"

    def test_should_be_case_insensitive(self):
        assert _parse_subdomain("Demo.Risk-Hub.DE", "risk-hub.de") == "demo"

    def test_should_return_none_for_unrelated_domain(self):
        assert _parse_subdomain("other.com", "risk-hub.de") is None
