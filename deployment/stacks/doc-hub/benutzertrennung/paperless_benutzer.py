"""Wird IM Paperless-Container ausgefuehrt (django shell) — listet Benutzer, Gruppen, Besitz.

Aufruf von aussen:
  ssh root@<host> "docker exec -i iil_dochub_web python3 manage.py shell" < paperless_benutzer.py
"""

from django.contrib.auth.models import Group, User

from documents.models import Document

print("=== Benutzer")
for b in User.objects.order_by("id"):
    eigene = Document.objects.filter(owner=b).count()
    print(
        "%-4s %-32s super=%-5s aktiv=%-5s gruppen=%-18s rechte=%-3d dokumente=%d"
        % (
            b.id,
            b.username[:32],
            b.is_superuser,
            b.is_active,
            ",".join(g.name for g in b.groups.all())[:18] or "-",
            b.user_permissions.count(),
            eigene,
        )
    )

print()
print("=== Gruppen")
for g in Group.objects.order_by("id"):
    print("%-4s %-32s rechte=%d  mitglieder=%d" % (g.id, g.name[:32], g.permissions.count(), g.user_set.count()))

print()
print("=== Dokumente nach Besitzer")
gesamt = Document.objects.count()
ohne = Document.objects.filter(owner__isnull=True).count()
print("gesamt=%d  ohne Besitzer=%d" % (gesamt, ohne))
for b in User.objects.order_by("id"):
    n = Document.objects.filter(owner=b).count()
    if n:
        print("  %-32s %d" % (b.username[:32], n))
