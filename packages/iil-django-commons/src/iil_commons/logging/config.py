import logging
import logging.config
from typing import Any

from iil_commons.settings import get_setting


def setup_logging() -> None:
    log_format = get_setting("LOG_FORMAT", "human")
    log_level = get_setting("LOG_LEVEL", "INFO")

    if log_format == "json":
        _setup_json_logging(log_level)
    else:
        _setup_human_logging(log_level)


def _setup_json_logging(log_level: str) -> None:
    try:
        from pythonjsonlogger import jsonlogger

        config: dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": jsonlogger.JsonFormatter,
                    "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
            "loggers": {
                "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
                "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
            },
        }
        logging.config.dictConfig(config)
    except ImportError:
        _setup_human_logging(log_level)


def _setup_human_logging(log_level: str) -> None:
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "human": {
                "format": "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "human",
            }
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        },
    }
    logging.config.dictConfig(config)
