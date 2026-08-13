#!/usr/bin/env python3
"""Jahres-Tags fuer den Bestand nachziehen.

Der Post-Consume-Hook (``auto-title.py``) taggt ab sofort jeden neuen Scan mit
dem Jahr seines Dokumentdatums. Der Bestand kennt diese Regel nicht: die
Jahres-Tags, die es dort gibt, wurden von Hand vergeben und sind lueckenhaft -
am 2026-08-13 existierten 2019, 2020, 2022, 2024, 2025 und 2026, waehrend fuer
2018, 2021 und 2023 Dokumente vorlagen, aber kein Tag.

Dieses Skript zieht das nach. Es teilt sich die Logik mit dem Hook, statt sie
zu wiederholen: ``dokumentdatum_bestimmen`` und ``jahres_tag_setzen`` werden
aus ``auto-title.py`` importiert. Eine zweite Kopie waere die naheliegende
Fehlerquelle - sie wuerde beim naechsten Eingriff an einer der beiden Stellen
auseinanderlaufen, und der Unterschied faellt erst Monate spaeter auf.

Der Trockenlauf ist die Voreinstellung. Er schreibt nichts und weist aus, was
ein echter Lauf tun wuerde - einschliesslich der beiden Dinge, die man vorher
gesehen haben will: wie viele Dokumentdaten korrigiert wuerden (das benennt
ueber PAPERLESS_FILENAME_FORMAT auch Dateien um) und bei wie vielen Dokumenten
ein abweichender Jahres-Tag bereits von Hand gesetzt ist.

    docker exec iil_dochub_web python /usr/src/paperless/scripts/jahres-tag-backfill.py
    docker exec iil_dochub_web python /usr/src/paperless/scripts/jahres-tag-backfill.py --apply
"""

import argparse
import collections
import importlib.util
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")

import django  # noqa: E402

django.setup()

from documents.models import Document  # noqa: E402

AUTO_TITLE_PFAD = "/usr/src/paperless/scripts/auto-title.py"


def lade_hook_logik(pfad=AUTO_TITLE_PFAD):
    """Die Funktionen des Post-Consume-Hooks als Modul.

    ``auto-title.py`` traegt einen Bindestrich im Namen und ist damit nicht
    ueber ``import`` erreichbar; der Umweg ueber importlib holt es trotzdem.
    Sein ``__main__``-Block laeuft dabei nicht mit.
    """
    spec = importlib.util.spec_from_file_location("auto_title", pfad)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"auto-title.py nicht ladbar: {pfad}")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def ist_jahres_tag(name):
    """Vierstellige Zahl - so heissen die Jahres-Tags."""
    return len(name) == 4 and name.isdigit()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Aenderungen wirklich schreiben (ohne dieses Flag: Trockenlauf)",
    )
    p.add_argument(
        "--nur-tags",
        action="store_true",
        help="Dokumentdaten unangetastet lassen, nur nach vorhandenem created taggen",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Nur die ersten N Dokumente betrachten (Probelauf)",
    )
    p.add_argument(
        "--auto-title",
        default=AUTO_TITLE_PFAD,
        help="Pfad zu auto-title.py - erlaubt den Trockenlauf gegen eine "
        "Fassung, die noch nicht ausgerollt ist",
    )
    args = p.parse_args()

    hook = lade_hook_logik(args.auto_title)

    docs = Document.objects.all().order_by("pk").prefetch_related("tags")
    if args.limit:
        docs = docs[: args.limit]

    neue_tags = collections.Counter()
    datums_korrekturen = []
    konflikte = []
    ohne_datum = []
    schon_getaggt = 0
    betrachtet = 0

    modus = "SCHREIBEND" if args.apply else "TROCKENLAUF"
    print(f"=== Jahres-Tag-Backfill ({modus}) ===")

    # chunk_size ist Pflicht, sobald iterator() auf prefetch_related trifft -
    # ohne sie lehnt Django den Aufruf ab.
    for doc in docs.iterator(chunk_size=200):
        betrachtet += 1
        content = doc.content or ""

        if args.nur_tags:
            datum, quelle = doc.created, "paperless"
        else:
            datum, quelle = hook.dokumentdatum_bestimmen(doc, content)

        vorhandene = [t.name for t in doc.tags.all()]

        # Ohne belastbares Datum wird nicht getaggt: der Jahres-Tag waere das
        # Scanjahr und damit eine Behauptung ueber das Dokument, die niemand
        # geprueft hat. Der Marker macht die Luecke stattdessen auffindbar.
        if quelle == "unklar":
            ohne_datum.append((doc.pk, doc.created))
            if args.apply and hook.MARKER_TAG not in vorhandene:
                hook.tag_anhaengen(
                    doc, hook.tag_holen(hook.MARKER_TAG, hook.MARKER_TAG_FARBE)
                )
            continue

        if quelle == "ocr":
            datums_korrekturen.append((doc.pk, doc.created, datum))

        jahr = str(datum.year)
        fremde_jahre = [n for n in vorhandene if ist_jahres_tag(n) and n != jahr]
        if fremde_jahre:
            konflikte.append((doc.pk, jahr, fremde_jahre))

        if jahr in vorhandene:
            schon_getaggt += 1
            continue

        neue_tags[jahr] += 1

        if args.apply:
            if quelle == "ocr":
                doc.created = datum
                doc.save(update_fields=["created"])
            hook.jahres_tag_setzen(doc, datum)
            hook.marker_entfernen(doc)

    print(f"\nBetrachtet:            {betrachtet}")
    print(f"Jahres-Tag schon da:   {schon_getaggt}")
    print(f"Tag zu setzen:         {sum(neue_tags.values())}")
    print("\nJe Jahr:")
    for jahr, anzahl in sorted(neue_tags.items()):
        print(f"  {jahr}: {anzahl}")

    print(f"\nOhne Dokumentdatum:    {len(ohne_datum)}")
    if ohne_datum:
        print(f"  (kein Jahres-Tag, bekommen stattdessen '{hook.MARKER_TAG}')")
        for pk, created in ohne_datum[:20]:
            print(f"  Doc {pk}: created {created} nicht belastbar")
        if len(ohne_datum) > 20:
            print(f"  ... und {len(ohne_datum) - 20} weitere")

    print(f"\nDatumskorrekturen:     {len(datums_korrekturen)}")
    if datums_korrekturen:
        print("  (aendert ueber PAPERLESS_FILENAME_FORMAT auch den Ablagepfad)")
        for pk, alt, neu in datums_korrekturen[:20]:
            print(f"  Doc {pk}: {alt} -> {neu}")
        if len(datums_korrekturen) > 20:
            print(f"  ... und {len(datums_korrekturen) - 20} weitere")

    print(f"\nAbweichender Jahres-Tag von Hand: {len(konflikte)}")
    if konflikte:
        print("  (bleibt stehen - wird nur ergaenzt, nie ersetzt)")
        for pk, jahr, fremde in konflikte[:20]:
            print(f"  Doc {pk}: hat {fremde}, bekommt {jahr}")
        if len(konflikte) > 20:
            print(f"  ... und {len(konflikte) - 20} weitere")

    if not args.apply:
        print("\nTrockenlauf - nichts geschrieben. Echter Lauf: --apply")


if __name__ == "__main__":
    main()
