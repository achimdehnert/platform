"""Stufe 3 — Superuser-Rechte entziehen. Laeuft IM Paperless-Container.

  ssh root@<host> "docker exec -i [-e SCHARF=1] iil_dochub_web python3 manage.py shell" < paperless_stufe3.py

Ein Superuser sieht in Paperless jedes Dokument, unabhaengig vom Besitzer. Solange
es fuenf davon gibt, ist die Trennung eine Zuordnung, aber keine Grenze.

Entzogen wird bei vier Konten ohne eigenen Bestand:
  akadmin                Ueberbleibsel der authentik-Zeit
  ad@dehnert.team        private Adresse, kein Arbeitskonto
  pg@dehnert.team        keine Dokumente
  admin@wir-digital.de   eingezogen (Owner-Entscheid 2026-08-02); die 7 Dokumente
                         dieses Kontos liegen seit Stufe 4 beim Arbeitskonto

Behalten:
  achim.dehnert@iil.gmbh   das Arbeitskonto, dem 776 Dokumente gehoeren
  admin                    Notzugang — bricht die Kopfzeilen-Anmeldung ueber
                           Cloudflare, ist das lokale Konto der einzige Weg zurueck

Die Konten bleiben aktiv, nur die Superuser-Eigenschaft faellt. Ruecknahme ist ein
Einzeiler, siehe Ausgabe am Ende.
"""

import os

from django.contrib.auth.models import Permission, User

from documents.models import Document

SCHARF = os.environ.get("SCHARF") == "1"
ENTZIEHEN = ["akadmin", "ad@dehnert.team", "pg@dehnert.team", "admin@wir-digital.de"]
BEHALTEN = ["achim.dehnert@iil.gmbh", "admin"]

print(">>> SCHARFER LAUF" if SCHARF else ">>> TROCKENLAUF — es wird nichts geaendert")
print()

print("Superuser vorher:")
for b in User.objects.filter(is_superuser=True).order_by("id"):
    print(
        "   %-4s %-30s dokumente=%d"
        % (b.id, b.username[:30], Document.objects.filter(owner=b).count())
    )
print()

for name in ENTZIEHEN:
    b = User.objects.filter(username=name).first()
    if not b:
        print("UEBERSPRUNGEN %-24s (Konto gibt es nicht)" % name)
        continue
    if not b.is_superuser:
        print("bereits ohne  %-24s" % name)
        continue
    n = Document.objects.filter(owner=b).count()
    if n:
        print("ABBRUCH       %-24s besitzt %d Dokumente — erst umhaengen" % (name, n))
        continue
    print("entziehen     %-24s (Kennung %s, 0 Dokumente)" % (name, b.id))
    if SCHARF:
        b.is_superuser = False
        b.is_staff = False
        b.save(update_fields=["is_superuser", "is_staff"])

print()
print("behalten:")
for name in BEHALTEN:
    b = User.objects.filter(username=name).first()
    if b:
        print(
            "   %-30s dokumente=%d" % (name, Document.objects.filter(owner=b).count())
        )

# ----------------------------------------------- Rechte-Abgleich der echten Nutzer
print()
print("=== Rechte-Abgleich der Personenkonten")
personen = ["md@dehnert.team", "sd@dehnert.team"]
mengen = {}
for name in personen:
    b = User.objects.filter(username=name).first()
    if b:
        mengen[name] = {
            "%s.%s" % (p.content_type.app_label, p.codename)
            for p in b.user_permissions.select_related("content_type")
        }
for name, m in mengen.items():
    print("   %-24s %d Rechte" % (name, len(m)))
if len(mengen) == 2:
    a, c = personen
    fehlt_a = sorted(mengen[c] - mengen[a])
    fehlt_c = sorted(mengen[a] - mengen[c])
    if fehlt_a:
        print("   %s fehlt gegenueber %s: %s" % (a, c, ", ".join(fehlt_a)))
    if fehlt_c:
        print("   %s fehlt gegenueber %s: %s" % (c, a, ", ".join(fehlt_c)))
    if not fehlt_a and not fehlt_c:
        print("   beide identisch")

print()
print("=== Stand danach")
for b in User.objects.order_by("id"):
    print(
        "%-4s %-32s super=%-5s aktiv=%-5s rechte=%-3d dokumente=%d"
        % (
            b.id,
            b.username[:32],
            b.is_superuser,
            b.is_active,
            b.user_permissions.count(),
            Document.objects.filter(owner=b).count(),
        )
    )
print()
print("Ruecknahme fuer ein Konto:")
print(
    "  User.objects.filter(username='<name>').update(is_superuser=True, is_staff=True)"
)
