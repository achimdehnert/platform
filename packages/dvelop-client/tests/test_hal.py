"""Tests for JSON-HAL response parsing."""

from dvelop_client.hal import extract_embedded, extract_links, extract_location


class TestExtractLinks:
    def test_simple_links(self):
        data = {
            "_links": {
                "self": {"href": "/dms/r/1"},
                "next": {"href": "/dms/r/1?page=2"},
            }
        }
        result = extract_links(data)
        assert result == {"self": "/dms/r/1", "next": "/dms/r/1?page=2"}

    def test_array_links_takes_first(self):
        data = {
            "_links": {
                "item": [{"href": "/a"}, {"href": "/b"}],
            }
        }
        result = extract_links(data)
        assert result == {"item": "/a"}

    def test_empty_links(self):
        assert extract_links({}) == {}
        assert extract_links({"_links": {}}) == {}

    def test_templated_links(self):
        data = {
            "_links": {
                "search": {"href": "/dms/r/{repo}/sr", "templated": True},
            }
        }
        result = extract_links(data)
        assert result == {"search": "/dms/r/{repo}/sr"}


class TestExtractEmbedded:
    def test_list_embedded(self):
        data = {
            "_embedded": {
                "repositories": [
                    {"id": "r1", "name": "Main"},
                    {"id": "r2", "name": "Archive"},
                ]
            }
        }
        result = extract_embedded(data, "repositories")
        assert len(result) == 2
        assert result[0]["id"] == "r1"

    def test_single_embedded_becomes_list(self):
        data = {
            "_embedded": {
                "repository": {"id": "r1", "name": "Main"},
            }
        }
        result = extract_embedded(data, "repository")
        assert len(result) == 1
        assert result[0]["id"] == "r1"

    def test_missing_key_returns_empty(self):
        data = {"_embedded": {"other": []}}
        assert extract_embedded(data, "repositories") == []

    def test_no_embedded_returns_empty(self):
        assert extract_embedded({}, "repositories") == []


class TestExtractLocation:
    def test_standard_header(self):
        headers = {"Location": "/dms/r/1/o/abc123"}
        assert extract_location(headers) == "/dms/r/1/o/abc123"

    def test_case_insensitive(self):
        headers = {"location": "/dms/r/1/b/xyz"}
        assert extract_location(headers) == "/dms/r/1/b/xyz"

    def test_missing_header(self):
        assert extract_location({}) == ""
        assert extract_location({"Content-Type": "text/html"}) == ""
