SECRET_KEY = "test"
INSTALLED_APPS = ["iil_dienst", "tests.demo"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
USE_TZ = True
