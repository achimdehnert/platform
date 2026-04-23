"""Tests for platform_context.htmx (ADR-048)."""

import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory

from platform_context.htmx import (
    HtmxErrorMiddleware,
    HtmxResponseMixin,
    is_htmx_request,
)


@pytest.fixture()
def rf() -> RequestFactory:
    """Django request factory."""
    return RequestFactory()


class TestIsHtmxRequest:
    """Tests for is_htmx_request()."""

    def test_should_detect_htmx_request(self, rf: RequestFactory) -> None:
        request = rf.get("/", HTTP_HX_REQUEST="true")
        assert is_htmx_request(request) is True

    def test_should_reject_normal_request(self, rf: RequestFactory) -> None:
        request = rf.get("/")
        assert is_htmx_request(request) is False

    def test_should_reject_false_header(self, rf: RequestFactory) -> None:
        request = rf.get("/", HTTP_HX_REQUEST="false")
        assert is_htmx_request(request) is False

    def test_should_reject_empty_header(self, rf: RequestFactory) -> None:
        request = rf.get("/", HTTP_HX_REQUEST="")
        assert is_htmx_request(request) is False


class TestHtmxErrorMiddleware:
    """Tests for HtmxErrorMiddleware."""

    @staticmethod
    def _make_middleware(status_code: int) -> HtmxErrorMiddleware:
        """Create middleware that returns a response with given status."""
        def get_response(request):
            return HttpResponse(status=status_code)
        return HtmxErrorMiddleware(get_response)

    def test_should_pass_through_non_htmx(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(500)
        request = rf.get("/")
        response = middleware(request)
        assert response.status_code == 500
        assert "HX-Reswap" not in response

    def test_should_intercept_500_for_htmx(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(500)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        assert response["HX-Reswap"] == "none"
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["showToast"]["level"] == "error"

    def test_should_intercept_404_as_warning(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(404)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        assert response["HX-Reswap"] == "none"
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["showToast"]["level"] == "warning"
        assert "not found" in trigger["showToast"]["message"].lower()

    def test_should_skip_422_validation_error(
        self, rf: RequestFactory,
    ) -> None:
        middleware = self._make_middleware(422)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        assert response.status_code == 422
        assert "HX-Reswap" not in response

    def test_should_pass_through_200(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(200)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        assert response.status_code == 200
        assert "HX-Reswap" not in response

    def test_should_intercept_403(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(403)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        trigger = json.loads(response["HX-Trigger"])
        assert "permission" in trigger["showToast"]["message"].lower()

    def test_should_intercept_429(self, rf: RequestFactory) -> None:
        middleware = self._make_middleware(429)
        request = rf.get("/", HTTP_HX_REQUEST="true")
        response = middleware(request)
        trigger = json.loads(response["HX-Trigger"])
        assert "wait" in trigger["showToast"]["message"].lower()


class TestHtmxResponseMixin:
    """Tests for HtmxResponseMixin."""

    def test_should_return_partial_for_htmx(self, rf: RequestFactory) -> None:
        class TestView(HtmxResponseMixin):
            partial_template_name = "trips/partials/_list.html"
            request = rf.get("/", HTTP_HX_REQUEST="true")

            def get_template_names(self_inner):
                return super(
                    HtmxResponseMixin, self_inner,
                ).get_template_names()

        mixin = TestView()
        mixin.request = rf.get("/", HTTP_HX_REQUEST="true")
        assert is_htmx_request(mixin.request) is True
        assert mixin.partial_template_name == "trips/partials/_list.html"

    def test_should_raise_without_partial_name(
        self, rf: RequestFactory,
    ) -> None:
        class BadView(HtmxResponseMixin):
            partial_template_name = ""

        view = BadView()
        view.request = rf.get("/", HTTP_HX_REQUEST="true")
        with pytest.raises(ImproperlyConfigured):
            HtmxResponseMixin.get_template_names(view)
