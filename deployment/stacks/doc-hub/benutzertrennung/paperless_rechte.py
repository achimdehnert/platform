"""Maras Rechte auf Bines Satz anheben. Laeuft IM Paperless-Container.

  ssh root@<host> "docker exec -i [-e SCHARF=1] iil_dochub_web python3 manage.py shell" < paperless_rechte.py

Beide arbeiten gleichartig, hatten aber unterschiedliche Rechte-Saetze (24 gegen 40) —
Mara fehlten unter anderem add_tag, add_correspondent, add_note. Das ist Altbestand,
keine Folge der Kontentrennung. Es werden nur Rechte ERGAENZT, nie entzogen.
"""

import os

from django.contrib.auth.models import User

SCHARF = os.environ.get("SCHARF") == "1"
VORBILD = "sd@dehnert.team"
ZIEL = "md@dehnert.team"

print(">>> SCHARFER LAUF" if SCHARF else ">>> TROCKENLAUF — es wird nichts geaendert")
print()

vorbild = User.objects.filter(username=VORBILD).first()
ziel = User.objects.filter(username=ZIEL).first()
if not vorbild or not ziel:
    raise SystemExit("ABBRUCH: %s oder %s gibt es nicht" % (VORBILD, ZIEL))

hat = set(ziel.user_permissions.values_list("id", flat=True))
soll = vorbild.user_permissions.all()
fehlend = [p for p in soll if p.id not in hat]

print("%-24s %d Rechte (Vorbild)" % (VORBILD, soll.count()))
print("%-24s %d Rechte" % (ZIEL, len(hat)))
print()
if not fehlend:
    print("nichts zu ergaenzen")
else:
    print("ergaenzen (%d):" % len(fehlend))
    for p in sorted(fehlend, key=lambda x: x.codename):
        print("   %s.%s" % (p.content_type.app_label, p.codename))
    if SCHARF:
        ziel.user_permissions.add(*fehlend)

print()
print("=== Stand danach")
for name in (VORBILD, ZIEL):
    b = User.objects.get(username=name)
    print("   %-24s %d Rechte" % (name, b.user_permissions.count()))
