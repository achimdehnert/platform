from django.conf import settings

DEFAULTS: dict = {
    "LOG_FORMAT": "human",
    "LOG_LEVEL": "INFO",
    "CACHE_DEFAULT_TTL": 300,
    "RATE_LIMIT_DEFAULT": "100/h",
    "RATE_LIMIT_PATHS": {},
    "HEALTH_CHECKS": ["db"],
    "EMAIL_PROVIDER": "smtp",
}


def get_setting(key: str, default=None):
    user_config: dict = getattr(settings, "IIL_COMMONS", {})
    if key in user_config:
        return user_config[key]
    if default is not None:
        return default
    return DEFAULTS.get(key)
