#!/usr/bin/env python3
"""Setup Paperless-ngx metadata: Document Types, Correspondents, Tags."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")

import django
django.setup()

from documents.models import Correspondent, Tag, DocumentType


# === DOCUMENT TYPES ===
# matching_algorithm: 0=none, 1=any, 2=all, 3=literal, 4=regex, 5=fuzzy, 6=auto
doc_types = [
    ("Rechnung", "rechnung invoice", 1),
    ("Bescheid", "bescheid", 1),
    ("Abrechnung", "abrechnung", 1),
    ("Vertrag", "vertrag", 1),
    ("Mitteilung", "mitteilung", 1),
    ("Mahnung", "mahnung", 1),
    ("Kontoauszug", "kontoauszug", 1),
    ("Angebot", "angebot", 1),
    ("Gutschrift", "gutschrift", 1),
    ("Versicherungsschein", "versicherungsschein police", 1),
    ("Steuerbescheid", "steuerbescheid", 1),
    ("Befund", "befund", 1),
    ("Quittung", "quittung", 1),
    ("Lohnabrechnung", "lohnabrechnung gehaltsabrechnung", 1),
    ("Arztbrief", "arztbrief", 1),
]

print("=== Document Types ===")
for name, match, algo in doc_types:
    obj, created = DocumentType.objects.get_or_create(
        name=name,
        defaults={"match": match, "matching_algorithm": algo, "is_insensitive": True},
    )
    status = "NEW" if created else "exists"
    print(f"  {status:6s}  {name}")


# === CORRESPONDENTS ===
correspondents = [
    ("Lechwerke AG (LEW)", "lechwerke lew", 1),
    ("LEW Verteilnetz GmbH", "lew verteilnetz", 1),
    ("BMW Bank GmbH", "bmw bank", 1),
    ("Deutsche Post AG", "deutsche post", 1),
    ("Raiffeisenbank Schwaben Mitte eG", "raiffeisenbank schwaben", 1),
    ("Media-Saturn Deutschland GmbH", "media-saturn mediamarkt saturn", 1),
    ("Haushahn GmbH", "haushahn", 1),
    ("Dr. Christoph Unsin", "christoph unsin", 1),
    ("Dr. Romy Metzger", "romy metzger", 1),
    ("Dr. Frederik Neyheusel", "frederik neyheusel", 1),
    ("Dr. Martin Riesner", "martin riesner", 1),
    ("Dr. Dietrich Gemmel", "dietrich gemmel", 1),
    ("Gemeinde Memmingerberg", "memmingerberg", 1),
    ("Stadtwerke Memmingen", "stadtwerke memmingen", 1),
    ("Finanzamt Memmingen", "finanzamt memmingen", 1),
    ("AOK Bayern", "aok", 1),
    ("Allianz Versicherung", "allianz", 1),
    ("ADAC", "adac", 1),
    ("Telekom", "telekom", 1),
    ("Vodafone", "vodafone", 1),
]

print("\n=== Correspondents ===")
for name, match, algo in correspondents:
    obj, created = Correspondent.objects.get_or_create(
        name=name,
        defaults={"match": match, "matching_algorithm": algo, "is_insensitive": True},
    )
    status = "NEW" if created else "exists"
    print(f"  {status:6s}  {name}")


# === TAGS ===
tags = [
    ("Steuer-relevant", "#e74c3c", "steuer finanzamt", 1),
    ("Versicherung", "#3498db", "versicherung versicherungsschein police", 1),
    ("Gesundheit", "#2ecc71", "arzt praxis patient rezept befund diagnose zahnarzt", 1),
    ("Energie", "#f39c12", "strom gas energie lechwerke lew stadtwerke kwh", 1),
    ("Bank/Finanzen", "#9b59b6", "konto kontoauszug bank raiffeisen sparkasse", 1),
    ("Auto", "#1abc9c", "bmw fahrzeug kfz auto werkstatt tuev zulassung", 1),
    ("Immobilie", "#e67e22", "miete wohnung haus grundsteuer nebenkosten", 1),
    ("Telekommunikation", "#34495e", "telekom vodafone internet mobilfunk", 1),
    ("Arbeitgeber", "#2980b9", "lohn gehalt arbeitgeber lohnabrechnung", 1),
    ("Wichtig", "#c0392b", "", 0),
]

print("\n=== Tags ===")
for name, color, match, algo in tags:
    defaults = {"color": color, "matching_algorithm": algo, "is_insensitive": True}
    if match:
        defaults["match"] = match
    obj, created = Tag.objects.get_or_create(name=name, defaults=defaults)
    status = "NEW" if created else "exists"
    print(f"  {status:6s}  {name}")

print("\n=== DONE ===")
print(f"Document Types: {DocumentType.objects.count()}")
print(f"Correspondents: {Correspondent.objects.count()}")
print(f"Tags: {Tag.objects.count()}")
