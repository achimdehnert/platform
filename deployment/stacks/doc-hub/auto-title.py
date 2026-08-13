#!/usr/bin/env python3
"""Post-consume script: Generate document title from OCR text + assign owner + auto-permissions."""

import datetime
import os
import re
import sys
import traceback

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
    sys.path.insert(0, "/usr/src/paperless/src")
    import django

    django.setup()
    from documents.models import Document, Tag
    from django.contrib.auth.models import User
    from django.utils import timezone
except Exception as e:
    print(f"Django setup error: {e}")
    sys.exit(0)

OWNER_MAP = {
    "achim": "achim",
    "bine": "bine",
    "mara": "mara",
}

# Convention: tag name = username -> auto-assign permissions
# No explicit map needed - if a tag matches a username, permissions are granted

DOC_TYPES = [
    "Rechnung",
    "Invoice",
    "Quittung",
    "Gutschrift",
    "Vertrag",
    "Kuendigung",
    "Mahnung",
    "Angebot",
    "Bescheid",
    "Mitteilung",
    "Bestaetigung",
    "Meldung",
    "Kontoauszug",
    "Abrechnung",
    "Beitragsbescheid",
    "Steuerbescheid",
    "Lohnabrechnung",
    "Gehaltsabrechnung",
    "Arztbrief",
    "Befund",
    "Rezept",
    "Ueberweisung",
    "Versicherungsschein",
    "Police",
    "Antrag",
]


def assign_owner(doc):
    tag_names = [t.name.lower() for t in doc.tags.all()]
    print(f"DB tags: {tag_names}")
    for tag in tag_names:
        if tag in OWNER_MAP:
            username = OWNER_MAP[tag]
            try:
                user = User.objects.get(username=username)
                if doc.owner != user:
                    doc.owner = user
                    doc.save(update_fields=["owner"])
                    print(f"Owner set: {username} (from DB tag '{tag}')")
                else:
                    print(f"Owner already {username}")
                return True
            except User.DoesNotExist:
                print(f"User '{username}' not found")
                return False
    tags_env = os.environ.get("DOCUMENT_TAGS", "")
    if tags_env:
        env_tags = [t.strip().lower() for t in tags_env.split(",") if t.strip()]
        print(f"Env tags: {env_tags}")
        for tag in env_tags:
            if tag in OWNER_MAP:
                username = OWNER_MAP[tag]
                try:
                    user = User.objects.get(username=username)
                    doc.owner = user
                    doc.save(update_fields=["owner"])
                    print(f"Owner set: {username} (from env tag '{tag}')")
                    return True
                except User.DoesNotExist:
                    pass
    print("No owner mapping found")
    return False


def assign_permissions(doc):
    """Auto-assign permissions: if tag name matches a username, grant view+change."""
    try:
        from guardian.shortcuts import assign_perm
    except ImportError:
        print("guardian not available, skipping permissions")
        return
    tag_names = [t.name.lower() for t in doc.tags.all()]
    granted = []
    for tag in tag_names:
        try:
            user = User.objects.get(username=tag)
            assign_perm("view_document", user, doc)
            assign_perm("change_document", user, doc)
            granted.append(tag)
        except User.DoesNotExist:
            pass
    if granted:
        print(f"Permissions granted: {', '.join(granted)}")
    else:
        print("No permission rules matched")

        print("No permission rules matched")


SCANNER_TITEL = re.compile(r"^[0-9][0-9_.\-\s]{5,}$")


def titel_ist_aussagelos(titel):
    """Nur nichtssagende Scanner-Namen duerfen ersetzt werden.

    Vorher wurde JEDER Titel ueberschrieben. Am 2026-07-30 trugen dadurch
    fuenf von sechs hochgeladenen Angeboten den Titel "Rechnung - ...",
    obwohl ihre Dateinamen ("Angebot_Marold_20250730.pdf") die richtige
    Auskunft gaben. Der Dateiname war besser als das Ergebnis.
    """
    t = (titel or "").strip()
    if not t:
        return True
    return bool(SCANNER_TITEL.match(t))


def datum_objekt_aus_text(content):
    """Erstes KALENDARISCH gueltiges Datum aus dem OCR-Text.

    Vorher wurde die erste datumsaehnliche Zeichenkette blind zusammengesetzt
    (f"{y}-{m}-{d}"), wodurch Titel wie "2025-09-31" entstanden - einen Tag,
    den es nicht gibt. Paperless konnte ihn nicht lesen und setzte created
    auf den Einlesetag.
    """
    for d, m, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", content):
        try:
            return datetime.date(int(y), int(m), int(d))
        except ValueError:
            continue
    return None


def datum_aus_text(content):
    """Dasselbe Datum als ISO-Zeichenkette - so braucht es der Titel."""
    datum = datum_objekt_aus_text(content)
    return datum.isoformat() if datum else None


FRUEHESTES_PLAUSIBLES_JAHR = 1900
JAHRES_TAG_FARBE = "#c9c9c9"


def datum_ist_plausibel(datum, heute):
    """Ein Datum, das als Dokumentdatum ueberhaupt in Frage kommt.

    Die Grenzen sind bewusst weit gezogen: der Bestand enthaelt echte Scans
    bis zurueck ins Jahr 1933. Ausgeschlossen wird nur, was nicht sein kann -
    ein Datum in der Zukunft (OCR liest Fristen, Gueltigkeits- und
    Faelligkeitsangaben gleichrangig mit) und ein Jahr vor 1900, wo es sich
    praktisch immer um verlesene Ziffern handelt.
    """
    return FRUEHESTES_PLAUSIBLES_JAHR <= datum.year and datum <= heute


def einlesetag(doc):
    """Der Tag, an dem Paperless das Dokument aufgenommen hat.

    ``added`` ist ein Zeitpunkt in UTC, ``created`` ein reines Datum in
    lokaler Zeit. Ohne die Umrechnung waeren die beiden am Tagesrand um
    einen Tag versetzt und der Vergleich unten liefe ins Leere.
    """
    return timezone.localtime(doc.added).date()


def dokumentdatum_bestimmen(doc, content, heute=None):
    """Das Datum, das dieses Dokument traegt - und ob es korrigiert wurde.

    Erste Quelle ist ``doc.created``: das ist, was Paperless selbst aus
    Dateiname und Text ermittelt hat, und es bestimmt ueber
    PAPERLESS_FILENAME_FORMAT={{ created_year }} schon heute den Ablagepfad.
    Solange Paperless etwas gefunden hat, wird daran nicht geruettelt.

    Findet Paperless nichts, faellt es auf den Einlesetag zurueck - und zwar
    stillschweigend, das Ergebnis sieht aus wie ein ermitteltes Datum. Genau
    dieser Fall ist hier der Aufhaenger: fallen ``created`` und Einlesetag
    zusammen, wird der OCR-Text noch einmal befragt. Traegt er ein
    plausibles, abweichendes Datum, gilt dieses.

    Rueckgabe: ``(datum, wurde_korrigiert)``.
    """
    heute = heute or timezone.localdate()
    created = doc.created
    if created != einlesetag(doc):
        return created, False

    aus_text = datum_objekt_aus_text(content or "")
    if aus_text is None or aus_text == created:
        return created, False
    if not datum_ist_plausibel(aus_text, heute):
        return created, False
    return aus_text, True


def jahres_tag_setzen(doc, datum):
    """Das Jahr des Dokumentdatums als Tag - ausschliesslich additiv.

    Es wird nur hinzugefuegt, nie etwas entfernt. Ein bereits vorhandener
    abweichender Jahres-Tag bleibt also stehen: bei einem Steuerbescheid aus
    2025 fuer das Jahr 2024 ist "2024" eine fachliche Angabe des Menschen und
    kein Fehler des Skripts - sie zu loeschen waere Informationsverlust.

    Neu angelegte Jahres-Tags bekommen ausdruecklich MATCH_NONE. Ohne das
    haengt Paperless den Tag spaeter von sich aus an jedes Dokument, in dem
    die Jahreszahl irgendwo im Text auftaucht.
    """
    name = str(datum.year)
    tag = Tag.objects.filter(name=name).first()
    if tag is None:
        # MATCH_NONE ist in Paperless 3.0.4 die 0 (nachgemessen, nicht geraten).
        # Der Ersatzwert ist derselbe: waere die Konstante eines Tages weg,
        # ist 0 immer noch das Feld-Default und damit die harmlose Wahl.
        tag = Tag.objects.create(
            name=name,
            matching_algorithm=getattr(Tag, "MATCH_NONE", 0),
            color=JAHRES_TAG_FARBE,
        )
        print(f"Jahres-Tag angelegt: {name}")
    if doc.tags.filter(pk=tag.pk).exists():
        print(f"Jahres-Tag bereits gesetzt: {name}")
        return False
    doc.tags.add(tag)
    print(f"Jahres-Tag gesetzt: {name}")
    return True


def jahr_taggen(doc, content):
    """Datum ermitteln, notfalls korrigieren, Jahr als Tag setzen.

    Eigener Fehlerschirm: dieses Skript laeuft als Post-Consume-Hook. Was
    hier schiefgeht, darf die Titel- und Owner-Zuweisung darunter nicht
    mitreissen.
    """
    try:
        datum, korrigiert = dokumentdatum_bestimmen(doc, content)
        if korrigiert:
            doc.created = datum
            doc.save(update_fields=["created"])
            print(f"Dokumentdatum korrigiert: {datum.isoformat()} (war Einlesetag)")
        else:
            print(f"Dokumentdatum: {datum.isoformat()}")
        jahres_tag_setzen(doc, datum)
    except Exception as e:
        print(f"Jahres-Tag uebersprungen: {e}")
        traceback.print_exc()


def extract_title(doc, content):
    """Titel NUR aus dem, was Paperless selbst festgestellt hat.

    Der Dokumenttyp wird NICHT mehr aus dem Text geraten - das machen die
    Zuordnungsregeln (matching_algorithm=regex). Vorher gewann hier die
    Position in einer Liste: DOC_TYPES beginnt mit "Rechnung", "Angebot"
    steht an achter Stelle. Ein Angebot, das "Rechnung" einmal erwaehnt,
    wurde zur Rechnung - bei Dokument 854 stand 9x "angebot" gegen 4x
    "rechnung", und "Rechnung" gewann trotzdem.
    """
    teile = []
    datum = datum_aus_text(content)
    if datum:
        teile.append(datum)
    if doc.correspondent_id:
        teile.append(doc.correspondent.name)
    if doc.document_type_id:
        teile.append(doc.document_type.name)
    if len(teile) < 2:
        return None
    return " - ".join(teile)


if __name__ == "__main__":
    doc_id = None
    try:
        doc_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DOCUMENT_ID", "")
        if not doc_id:
            sys.exit(0)

        doc = Document.objects.get(pk=int(doc_id))
        assign_owner(doc)
        assign_permissions(doc)

        content = doc.content or ""

        # Vor der Titelvergabe: der Titel traegt das Datum mit, und wenn
        # created hier korrigiert wird, soll der Titel dazu passen.
        jahr_taggen(doc, content)

        if len(content.strip()) < 10:
            print(f"Doc {doc_id}: too little content")
        else:
            print(f"Doc {doc_id}: content_len={len(content)}")
            if not titel_ist_aussagelos(doc.title):
                print("Title kept (aussagekraeftig): " + str(doc.title))
            else:
                title = extract_title(doc, content)
                if title:
                    doc.title = title
                    doc.save(update_fields=["title"])
                    print("Title set: " + title)
                else:
                    print("No title generated - original kept")

    except Exception as e:
        print(f"Script error: {e}")
        traceback.print_exc()

    # Forward to tax-hub (steuer-relevant)
    if doc_id:
        try:
            import subprocess

            subprocess.Popen(
                [
                    sys.executable,
                    "/usr/src/paperless/scripts/paperless-post-consume.py",
                    str(doc_id),
                ],
                env=os.environ.copy(),
            )
        except Exception:
            pass

    sys.exit(0)
