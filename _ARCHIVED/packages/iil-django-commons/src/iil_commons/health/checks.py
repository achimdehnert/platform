import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class HealthCheck(ABC):
    name: str = ""

    @abstractmethod
    def check(self) -> tuple[bool, str]:
        """Returns (ok, detail_message)."""


class DatabaseCheck(HealthCheck):
    name = "db"

    def check(self) -> tuple[bool, str]:
        try:
            from django.db import connection

            connection.ensure_connection()
            return True, "ok"
        except Exception as exc:
            logger.warning("health db check failed: %s", exc)
            return False, str(exc)


class RedisCheck(HealthCheck):
    name = "redis"

    def __init__(self, alias: str = "default") -> None:
        self.alias = alias

    def check(self) -> tuple[bool, str]:
        try:
            from django.core.cache import caches

            cache = caches[self.alias]
            cache.get("__iil_health_ping__")
            return True, "ok"
        except Exception as exc:
            logger.warning("health redis check failed: %s", exc)
            return False, str(exc)


class CeleryCheck(HealthCheck):
    name = "celery"

    def __init__(self, app_path: str = "config.celery_app") -> None:
        self.app_path = app_path

    def check(self) -> tuple[bool, str]:
        try:
            import importlib

            module_path, attr = self.app_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            app = getattr(module, attr)
            inspect = app.control.inspect(timeout=1.0)
            stats = inspect.ping()
            if stats:
                return True, "ok"
            return False, "no workers responded"
        except Exception as exc:
            logger.warning("health celery check failed: %s", exc)
            return False, str(exc)


REGISTRY: dict[str, type[HealthCheck]] = {
    "db": DatabaseCheck,
    "redis": RedisCheck,
    "celery": CeleryCheck,
}
