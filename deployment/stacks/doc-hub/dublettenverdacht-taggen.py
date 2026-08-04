#!/usr/bin/env python3
"""Markiert die Dubletten-Kandidaten in Paperless: Tag + gespeicherte Ansicht.

Grundlage: document_fuzzy_match --ratio 98 vom 2026-07-29 (5 Paare, 3 Gruppen).
Idempotent — mehrfach ausfuehrbar. Rueckbau: Tag loeschen, dann ist alles weg.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")
import django  # noqa: E402

django.setup()

from documents.models import Document, SavedView, SavedViewFilterRule, Tag  # noqa: E402

TAG_NAME = "dublettenverdacht"
TAG_FARBE = "#e74c3c"

# Gruppen aus dem Aehnlichkeitslauf (>= 98 %)
GRUPPEN = {
    "A": [732, 846, 848],  # Rechnung Gemeinde Memmingerberg, 2026-03-16
    "B": [724, 740],  # Rechnung Prof. Dr. Achim Dehnert, 2022-03-08
    "C": [107, 123],  # Dr. Armin Dehnert, 2023-08-02
}

RULE_HAS_TAG = 6  # documents_savedviewfilterrule.rule_type


def main() -> int:
    tag, neu = Tag.objects.get_or_create(
        name=TAG_NAME,
        defaults={"color": TAG_FARBE, "is_inbox_tag": False, "matching_algorithm": 0},
    )
    print(
        f"Tag '{tag.name}' (id {tag.id}) — {'neu angelegt' if neu else 'bestand bereits'}"
    )

    gesetzt, fehlend = 0, []
    for gruppe, ids in GRUPPEN.items():
        for doc_id in ids:
            try:
                d = Document.objects.get(pk=doc_id)
            except Document.DoesNotExist:
                fehlend.append(doc_id)
                continue
            if not d.tags.filter(pk=tag.pk).exists():
                d.tags.add(tag)
                gesetzt += 1
            print(f"  Gruppe {gruppe}  #{doc_id:<5} {d.title[:52]}")

    print(f"\n{gesetzt} Zuordnung(en) neu gesetzt.")
    if fehlend:
        print(f"NICHT gefunden (evtl. schon geloescht): {fehlend}")

    # Gespeicherte Ansicht, damit die Gruppe mit einem Klick erreichbar ist
    # Die Ansicht braucht einen Besitzer — sie gehoert dem Konto, das ueber
    # Cloudflare Access hereinkommt, damit sie dort in der Seitenleiste steht.
    from django.contrib.auth.models import User

    besitzer = (
        User.objects.filter(username="achim.dehnert@iil.gmbh").first()
        or User.objects.filter(is_superuser=True).order_by("id").first()
    )
    try:
        view, view_neu = SavedView.objects.get_or_create(
            name="Dublettenverdacht",
            # 3.0.4: show_on_dashboard/show_in_sidebar gibt es am Modell nicht
            # mehr (Spalten geprueft gegen documents_savedview) — die Platzierung
            # wird nicht mehr hier gesteuert.
            defaults={
                "owner": besitzer,
                "sort_field": "created",
                "sort_reverse": True,
            },
        )
    except Exception as e:  # echte Ursache zeigen statt verschlucken
        print(f"  Ansicht konnte NICHT angelegt werden: {type(e).__name__}: {e}")
        view, view_neu = None, False
    if view is not None:
        if not SavedViewFilterRule.objects.filter(
            saved_view=view, rule_type=RULE_HAS_TAG, value=str(tag.id)
        ).exists():
            SavedViewFilterRule.objects.create(
                saved_view=view, rule_type=RULE_HAS_TAG, value=str(tag.id)
            )
        print(
            f"Ansicht 'Dublettenverdacht' (id {view.id}, Besitzer {besitzer}) — "
            f"{'neu angelegt' if view_neu else 'bestand bereits'}, "
            f""
        )

    # Gegenprobe gegen den Bestand, nicht gegen die eigene Absicht
    ist = set(Document.objects.filter(tags=tag).values_list("id", flat=True))
    soll = {i for ids in GRUPPEN.values() for i in ids}
    print(f"\nGegenprobe: {len(ist)} Dokumente tragen den Tag; erwartet {len(soll)}")
    if ist != soll:
        print(f"  ABWEICHUNG  zuviel={sorted(ist - soll)}  fehlt={sorted(soll - ist)}")
        return 1

    print("\nPaare zum Nebeneinanderlegen:")
    for a, b, wert in [
        (732, 848, "99,4 %"),
        (846, 848, "99,2 %"),
        (732, 846, "99,1 %"),
        (724, 740, "98,9 %"),
        (107, 123, "98,3 %"),
    ]:
        print(
            f"  {wert}  https://docs.iil.pet/documents/{a}/details"
            f"   |   https://docs.iil.pet/documents/{b}/details"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
