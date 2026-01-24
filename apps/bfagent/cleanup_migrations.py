"""
Cleanup problematic migrations.
DA DIE DB LEER IST, können wir diese sicher löschen!
"""
import os
import shutil

# Lösche bfagent __pycache__
pycache = r"apps\bfagent\migrations\__pycache__"
if os.path.exists(pycache):
    shutil.rmtree(pycache)
    print(f"✅ Gelöscht: {pycache}")

# Lösche problematische Migrations
files_to_delete = [
    r"apps\bfagent\migrations\0002_chapterbeat_storybible_storychapter_storycharacter_and_more.py",
    r"apps\bfagent\migrations\0003_remove_location_parent_location_and_more.py",
]

for f in files_to_delete:
    if os.path.exists(f):
        os.remove(f)
        print(f"✅ Gelöscht: {f}")

print("\n✅ Cleanup fertig!")
print("✅ Jetzt: python manage.py migrate")
