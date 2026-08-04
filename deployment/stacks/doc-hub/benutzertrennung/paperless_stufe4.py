"""Stufe 4 — alle Dokumente ausser Maras und Bines auf das Arbeitskonto. Laeuft IM Container.

  ssh root@<host> "docker exec -i [-e SCHARF=1] iil_dochub_web python3 manage.py shell" < paperless_stufe4.py

Regel (Owner-Entscheid 2026-08-02): alles, was nicht md@dehnert.team oder sd@dehnert.team
gehoert, geht an achim.dehnert@iil.gmbh — einschliesslich der Dokumente ohne Besitzer.
In Paperless heisst "kein Besitzer" naemlich *fuer alle sichtbar*; Mara und Bine saehen
sie sonst, obwohl sie ihnen nicht gehoeren.
"""

import os

from django.contrib.auth.models import User
from django.db import transaction

from documents.models import Document

SCHARF = os.environ.get("SCHARF") == "1"
ZIEL = "achim.dehnert@iil.gmbh"
BEHALTEN = ["md@dehnert.team", "sd@dehnert.team"]

print(">>> SCHARFER LAUF" if SCHARF else ">>> TROCKENLAUF — es wird nichts geaendert")
print()

ziel = User.objects.filter(username=ZIEL).first()
if not ziel:
    raise SystemExit("ABBRUCH: Zielkonto %s gibt es nicht" % ZIEL)

behalten_ids = list(
    User.objects.filter(username__in=BEHALTEN).values_list("id", flat=True)
)
if len(behalten_ids) != len(BEHALTEN):
    raise SystemExit("ABBRUCH: nicht alle Konten gefunden: %s" % ", ".join(BEHALTEN))

umzug = Document.objects.exclude(owner_id__in=behalten_ids).exclude(owner=ziel)

print("bleibt bei:")
for name in BEHALTEN:
    b = User.objects.get(username=name)
    print("   %-32s %d" % (name, Document.objects.filter(owner=b).count()))
print()
print("geht an %s:" % ZIEL)
for b in User.objects.order_by("id"):
    n = umzug.filter(owner=b).count()
    if n:
        print("   von %-30s %d" % (b.username[:30], n))
ohne = umzug.filter(owner__isnull=True).count()
if ohne:
    print("   %-34s %d" % ("ohne Besitzer", ohne))
print("   %-34s %d" % ("SUMME", umzug.count()))

if SCHARF:
    with transaction.atomic():
        n = umzug.update(owner=ziel)
    print()
    print("uebertragen: %d Dokumente" % n)

print()
print("=== Stand danach")
print(
    "Dokumente gesamt=%d  ohne Besitzer=%d"
    % (Document.objects.count(), Document.objects.filter(owner__isnull=True).count())
)
for b in User.objects.order_by("id"):
    n = Document.objects.filter(owner=b).count()
    if n:
        print("   %-32s super=%-5s %d" % (b.username[:32], b.is_superuser, n))
