"""Stufe 1 — Doppelgaenger-Konten zusammenfuehren. Laeuft IM Paperless-Container.

  ssh root@<host> "docker exec -i iil_dochub_web python3 manage.py shell" < paperless_stufe1.py
  (Trockenlauf ist der Standard; scharf ueber die Umgebungsvariable SCHARF=1)

Warum: Cloudflare Access liefert die E-Mail-Adresse als Anmeldenamen. Paperless legt
beim ersten Zutritt einen NEUEN Benutzer mit genau diesem Namen an — die vorhandenen
Konten `mara`, `bine`, `achim` blieben mitsamt ihren Dokumenten unerreichbar daneben
stehen. Deshalb VOR der ersten Anmeldung umbenennen.

Drei Faelle, zwei Arten:
  mara  -> md@dehnert.team          Umbenennung (Ziel existiert nicht)
  bine  -> sd@dehnert.team          Umbenennung (Ziel existiert nicht)
  achim -> achim.dehnert@iil.gmbh   Zusammenfuehrung (beide existieren)

Eine Umbenennung ist harmlos: die Benutzer-Kennung bleibt, also bleiben Dokumente,
Einzelrechte und die guardian-Eintraege unveraendert gueltig. Die Zusammenfuehrung
muss dagegen jeden Besitz-Verweis einzeln umhaengen.
"""

import os

from django.contrib.auth.models import Permission, User
from django.db import transaction
from guardian.models import UserObjectPermission

from documents.models import (
    Correspondent,
    Document,
    DocumentType,
    SavedView,
    StoragePath,
    Tag,
)

SCHARF = os.environ.get("SCHARF") == "1"

UMBENENNEN = [("mara", "md@dehnert.team"), ("bine", "sd@dehnert.team")]
ZUSAMMEN = ("achim", "achim.dehnert@iil.gmbh")

BESITZ_MODELLE = [Document, Tag, Correspondent, DocumentType, StoragePath, SavedView]


def hole(name):
    return User.objects.filter(username=name).first()


print(">>> SCHARFER LAUF" if SCHARF else ">>> TROCKENLAUF — es wird nichts geaendert")
print()

fehler = []

# ---------------------------------------------------------------- Umbenennungen
for alt, neu in UMBENENNEN:
    b = hole(alt)
    if not b:
        print("UEBERSPRUNGEN %-8s -> %-24s (Konto gibt es nicht)" % (alt, neu))
        continue
    if hole(neu):
        print("ABBRUCH       %-8s -> %-24s ZIEL EXISTIERT BEREITS" % (alt, neu))
        fehler.append("%s -> %s: Ziel existiert" % (alt, neu))
        continue
    n = Document.objects.filter(owner=b).count()
    print("umbenennen    %-8s -> %-24s (Kennung %s, %d Dokumente, %d Rechte)"
          % (alt, neu, b.id, n, b.user_permissions.count()))
    if SCHARF:
        b.username = neu
        b.save(update_fields=["username"])

# ---------------------------------------------------------------- Zusammenfuehrung
alt, neu = ZUSAMMEN
quelle, ziel = hole(alt), hole(neu)
print()
if not quelle:
    print("UEBERSPRUNGEN %-8s -> %-24s (Quellkonto gibt es nicht)" % (alt, neu))
elif not ziel:
    print("umbenennen    %-8s -> %-24s (Ziel existiert nicht, also nur Umbenennung)" % (alt, neu))
    if SCHARF:
        quelle.username = neu
        quelle.save(update_fields=["username"])
else:
    print("zusammenfuehren %s (Kennung %s) -> %s (Kennung %s)" % (alt, quelle.id, neu, ziel.id))
    umzug = {}
    for modell in BESITZ_MODELLE:
        n = modell.objects.filter(owner=quelle).count()
        if n:
            umzug[modell.__name__] = n
    gop = UserObjectPermission.objects.filter(user=quelle).count()
    rechte = list(quelle.user_permissions.values_list("id", flat=True))
    ziel_rechte = set(ziel.user_permissions.values_list("id", flat=True))
    neue_rechte = [r for r in rechte if r not in ziel_rechte]

    for name, n in sorted(umzug.items()):
        print("   Besitz umhaengen  %-16s %d" % (name, n))
    print("   Einzelrechte (guardian)   %d" % gop)
    print("   Rechte ergaenzen am Ziel  %d von %d" % (len(neue_rechte), len(rechte)))
    print("   danach: %s wird deaktiviert (nicht geloescht)" % alt)

    if SCHARF:
        with transaction.atomic():
            for modell in BESITZ_MODELLE:
                modell.objects.filter(owner=quelle).update(owner=ziel)
            UserObjectPermission.objects.filter(user=quelle).update(user=ziel)
            if neue_rechte:
                ziel.user_permissions.add(*Permission.objects.filter(id__in=neue_rechte))
            quelle.is_active = False
            quelle.username = "zusammengefuehrt-%s" % alt
            quelle.save(update_fields=["is_active", "username"])

# ---------------------------------------------------------------- Nachlese
print()
print("=== Stand danach")
for b in User.objects.order_by("id"):
    print("%-4s %-32s super=%-5s aktiv=%-5s rechte=%-3d dokumente=%d"
          % (b.id, b.username[:32], b.is_superuser, b.is_active,
             b.user_permissions.count(), Document.objects.filter(owner=b).count()))

if fehler:
    print()
    print("FEHLER: %s" % "; ".join(fehler))
