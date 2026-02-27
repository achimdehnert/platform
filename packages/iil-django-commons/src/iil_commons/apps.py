from django.apps import AppConfig


class IilCommonsConfig(AppConfig):
    name = "iil_commons"
    label = "iil_commons"
    verbose_name = "IIL Commons"

    def ready(self) -> None:
        from iil_commons.settings import get_setting

        log_format = get_setting("LOG_FORMAT", "human")
        if log_format:
            try:
                from iil_commons.logging.config import setup_logging

                setup_logging()
            except ImportError:
                pass
