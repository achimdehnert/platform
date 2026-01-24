import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("DROP VIEW IF EXISTS characters")
cursor.execute("CREATE VIEW characters AS SELECT * FROM writing_characters")
print("✅ characters VIEW fixed → writing_characters")
