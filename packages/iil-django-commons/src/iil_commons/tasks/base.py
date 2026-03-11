import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from celery import Task as _CeleryTask
except ImportError:
    _CeleryTask = object  # type: ignore[assignment,misc]


class BaseTask(_CeleryTask):
    """Celery base task with auto-retry, structured logging and correlation ID propagation.

    Usage:
        from iil_commons.tasks import BaseTask

        @app.task(base=BaseTask, bind=True, max_retries=3)
        def my_task(self, arg):
            ...

    Features:
    - Auto-retry on Exception with exponential backoff (2^retry * 60s)
    - Structured log on start/success/failure/retry
    - Propagates X-Correlation-ID from task headers into log context
    """

    abstract = True
    max_retries: int = 3
    _retry_backoff_base: int = 60

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        correlation_id = self._get_correlation_id()
        logger.info(
            "task_start",
            extra={
                "task": self.name,
                "task_id": self.request.id,
                "correlation_id": correlation_id,
                "retries": self.request.retries,
            },
        )
        try:
            result = self.run(*args, **kwargs)
            logger.info(
                "task_success",
                extra={"task": self.name, "task_id": self.request.id},
            )
            return result
        except Exception as exc:
            retries = self.request.retries
            if retries < self.max_retries:
                countdown = (2**retries) * self._retry_backoff_base
                logger.warning(
                    "task_retry",
                    extra={
                        "task": self.name,
                        "task_id": self.request.id,
                        "retries": retries,
                        "countdown": countdown,
                        "error": str(exc),
                    },
                )
                raise self.retry(exc=exc, countdown=countdown)
            logger.error(
                "task_failure",
                extra={
                    "task": self.name,
                    "task_id": self.request.id,
                    "retries": retries,
                    "error": str(exc),
                },
            )
            raise

    def _get_correlation_id(self) -> str:
        headers = getattr(self.request, "headers", {}) or {}
        return headers.get("X-Correlation-ID", "")
