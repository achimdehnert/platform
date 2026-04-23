"""Tests for DvelopAuth header construction."""

import httpx

from dvelop_client.auth import DvelopAuth


class TestDvelopAuth:
    def setup_method(self):
        self.auth = DvelopAuth(
            api_key="test-key-123",
            base_url="https://iil.d-velop.cloud",
        )

    def _make_request(
        self, method: str,
        url: str = "https://iil.d-velop.cloud/dms",
    ):
        request = httpx.Request(method, url)
        flow = self.auth.auth_flow(request)
        return next(flow)

    def test_get_has_bearer_and_accept(self):
        req = self._make_request("GET")
        assert req.headers["Authorization"] == "Bearer test-key-123"
        assert req.headers["Accept"] == "application/hal+json"

    def test_get_has_no_origin(self):
        req = self._make_request("GET")
        assert "Origin" not in req.headers

    def test_post_has_origin_header(self):
        req = self._make_request("POST")
        assert req.headers["Origin"] == "https://iil.d-velop.cloud"

    def test_post_has_content_type(self):
        req = self._make_request("POST")
        assert req.headers["Content-Type"] == "application/hal+json"

    def test_put_has_origin(self):
        req = self._make_request("PUT")
        assert req.headers["Origin"] == "https://iil.d-velop.cloud"

    def test_delete_has_origin(self):
        req = self._make_request("DELETE")
        assert req.headers["Origin"] == "https://iil.d-velop.cloud"

    def test_patch_has_origin(self):
        req = self._make_request("PATCH")
        assert req.headers["Origin"] == "https://iil.d-velop.cloud"

    def test_base_url_trailing_slash_stripped(self):
        auth = DvelopAuth(
            api_key="key",
            base_url="https://example.com/",
        )
        request = httpx.Request("POST", "https://example.com/dms")
        flow = auth.auth_flow(request)
        req = next(flow)
        assert req.headers["Origin"] == "https://example.com"

    def test_post_preserves_existing_content_type(self):
        request = httpx.Request(
            "POST",
            "https://iil.d-velop.cloud/dms/r/1/b",
            headers={"Content-Type": "application/pdf"},
        )
        flow = self.auth.auth_flow(request)
        req = next(flow)
        assert req.headers["Content-Type"] == "application/pdf"
