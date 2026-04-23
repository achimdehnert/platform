import logging
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
_CTX_VAR_NAME = "_iil_correlation_id"


def get_correlation_id(request: HttpRequest) -> str:
    return getattr(request, _CTX_VAR_NAME, "")


class CorrelationIDMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        setattr(request, _CTX_VAR_NAME, correlation_id)
        response = self.get_response(request)
        response[CORRELATION_ID_HEADER] = correlation_id
        return response


_SKIP_LOG_PATHS = frozenset({"/livez/", "/healthz/", "/readyz/", "/health/"})


class RequestLogMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.monotonic()
        response = self.get_response(request)

        if request.path in _SKIP_LOG_PATHS:
            return response

        duration_ms = round((time.monotonic() - start) * 1000, 1)

        user = getattr(request, "user", None)
        user_id = user.pk if user and user.is_authenticated else None

        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "correlation_id": get_correlation_id(request),
            },
        )
        return response
