"""Tests for DvelopClient using pytest-httpx mocks."""

import pytest
import httpx

from dvelop_client.client import DvelopClient
from dvelop_client.exceptions import (
    DvelopAuthError,
    DvelopError,
    DvelopForbiddenError,
    DvelopNotFoundError,
    DvelopRateLimitError,
)


BASE_URL = "https://iil.d-velop.cloud"
API_KEY = "test-api-key"
REPO_ID = "repo-abc-123"


@pytest.fixture
def client():
    with DvelopClient(
        base_url=BASE_URL, api_key=API_KEY,
    ) as c:
        yield c


class TestListRepositories:
    def test_should_return_repositories(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            json={
                "repositories": [
                    {
                        "id": "r1",
                        "name": "Main Archive",
                        "_links": {
                            "self": {"href": "/dms/r/r1"},
                        },
                    },
                    {
                        "id": "r2",
                        "name": "Backup",
                        "_links": {
                            "self": {"href": "/dms/r/r2"},
                        },
                    },
                ]
            },
        )
        repos = client.list_repositories()
        assert len(repos) == 2
        assert repos[0].id == "r1"
        assert repos[0].name == "Main Archive"
        assert repos[1].id == "r2"

    def test_should_return_empty_on_no_repos(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            json={"repositories": []},
        )
        repos = client.list_repositories()
        assert repos == []


class TestListCategories:
    def test_should_return_categories(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/objdef",
            json={
                "objectDefinitions": [
                    {
                        "key": "DSGVO_AUDIT",
                        "displayName": "Datenschutz-Audit",
                    },
                    {
                        "key": "INVOICE",
                        "displayName": "Rechnung",
                    },
                ]
            },
        )
        cats = client.list_categories(REPO_ID)
        assert len(cats) == 2
        assert cats[0].key == "DSGVO_AUDIT"
        assert cats[0].display_name == "Datenschutz-Audit"


class TestUploadBlob:
    def test_should_upload_and_return_blob_ref(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/b",
            status_code=201,
            headers={
                "Location": f"/dms/r/{REPO_ID}/b/blob-xyz",
            },
        )
        blob = client.upload_blob(
            REPO_ID, b"fake-pdf-bytes", "test.pdf",
        )
        assert blob.blob_id == "blob-xyz"
        assert blob.location_uri == (
            f"/dms/r/{REPO_ID}/b/blob-xyz"
        )
        assert blob.content_type == "application/pdf"


class TestCreateDocument:
    def test_should_create_dms_object(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/b",
            status_code=201,
            headers={
                "Location": f"/dms/r/{REPO_ID}/b/blob-1",
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/o2",
            status_code=201,
            headers={
                "Location": f"/dms/r/{REPO_ID}/o2/doc-42",
            },
        )
        doc = client.upload_document(
            repo_id=REPO_ID,
            filename="Audit_2026-03-26.pdf",
            content=b"pdf-content",
            category="DSGVO_AUDIT",
            properties={
                "Mandant": "Landratsamt",
                "Datum": "2026-03-26",
            },
        )
        assert doc.id == "doc-42"
        assert doc.repo_id == REPO_ID
        assert doc.category == "DSGVO_AUDIT"
        assert len(doc.properties) == 2

    def test_should_send_correct_payload(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/b",
            status_code=201,
            headers={
                "Location": f"/dms/r/{REPO_ID}/b/b1",
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/o2",
            status_code=201,
            headers={
                "Location": f"/dms/r/{REPO_ID}/o2/d1",
            },
        )
        client.upload_document(
            repo_id=REPO_ID,
            filename="test.pdf",
            content=b"data",
            category="CAT1",
            properties={"key1": "val1"},
        )
        requests = httpx_mock.get_requests()
        post_obj = [
            r for r in requests
            if r.url.path.endswith("/o2")
        ][0]
        import json
        payload = json.loads(post_obj.content)
        assert payload["sourceCategory"] == "CAT1"
        assert payload["contentLocationUri"] == (
            f"/dms/r/{REPO_ID}/b/b1"
        )
        assert payload["sourceProperties"] == [
            {"key": "key1", "value": "val1"},
        ]


class TestSearch:
    def test_should_return_search_results(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=httpx.URL(
                f"{BASE_URL}/dms/r/{REPO_ID}/sr",
                params={
                    "fulltext": "Datenpanne",
                    "maxresults": "50",
                },
            ),
            json={
                "total": 1,
                "_embedded": {
                    "searchResults": [
                        {
                            "id": "sr-1",
                            "title": "Datenpanne 2026-03",
                            "sourceCategory": "BREACH",
                            "_links": {
                                "self": {
                                    "href": "/dms/r/x/o/sr-1",
                                },
                            },
                        }
                    ]
                },
            },
        )
        result = client.search(REPO_ID, "Datenpanne")
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == "sr-1"
        assert result.items[0].title == "Datenpanne 2026-03"


class TestErrorHandling:
    def test_should_raise_auth_error_on_401(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            status_code=401,
            text="Unauthorized",
        )
        with pytest.raises(DvelopAuthError) as exc_info:
            client.list_repositories()
        assert exc_info.value.status_code == 401

    def test_should_raise_forbidden_on_403(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            status_code=403,
            text="Missing Origin header",
        )
        with pytest.raises(DvelopForbiddenError) as exc_info:
            client.list_repositories()
        assert exc_info.value.status_code == 403

    def test_should_raise_not_found_on_404(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r/{REPO_ID}/o2/nonexist",
            status_code=404,
            text="Not found",
        )
        with pytest.raises(DvelopNotFoundError):
            client.get_document(REPO_ID, "nonexist")

    def test_should_raise_rate_limit_on_429(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            status_code=429,
            text="Too many requests",
            headers={"Retry-After": "60"},
        )
        with pytest.raises(DvelopRateLimitError) as exc_info:
            client.list_repositories()
        assert exc_info.value.retry_after == 60

    def test_should_raise_generic_error_on_500(
        self, client, httpx_mock,
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/dms/r",
            status_code=500,
            text="Internal Server Error",
        )
        with pytest.raises(DvelopError) as exc_info:
            client.list_repositories()
        assert exc_info.value.status_code == 500


class TestContextManager:
    def test_should_fail_without_context_manager(self):
        client = DvelopClient(
            base_url=BASE_URL, api_key=API_KEY,
        )
        with pytest.raises(RuntimeError, match="context manager"):
            client.list_repositories()
