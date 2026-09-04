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
    obwohl ihre Dateinamen ("Angebot_Kunde_20250730.pdf") die richtige
    Auskunft gaben. Der Dateiname war besser als das Ergebnis.
    """
    t = (titel or "").strip()
    if not t:
        return True
    return bool(SCANNER_TITEL.match(t))


MONATE = {
    "januar": 1,
    "jan": 1,
    "februar": 2,
    "feb": 2,
    "maerz": 3,
    "märz": 3,
    "mrz": 3,
    "april": 4,
    "apr": 4,
    "mai": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "november": 11,
    "nov": 11,
    "dezember": 12,
    "dez": 12,
}

# Laengste zuerst, sonst schluckt "jun" den Anfang von "juni".
_MONATSNAMEN = "|".join(sorted(MONATE, key=len, reverse=True))

# Reihenfolge egal - es gewinnt, was im Text zuerst steht, nicht was hier
# oben steht. Die Tupel benennen, welche Fundstelle Tag, Monat und Jahr ist.
VOLLE_DATEN = [
    (re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b"), ("d", "m", "y")),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), ("y", "m", "d")),
    (
        re.compile(rf"\b(\d{{1,2}})\.?\s+({_MONATSNAMEN})\.?\s+(\d{{4}})\b", re.I),
        ("d", "M", "y"),
    ),
]

NUR_MONAT_JAHR = re.compile(rf"\b({_MONATSNAMEN})\.?\s+(\d{{4}})\b", re.I)

# Grober Rahmen gegen Zeichenketten, die nur wie ein Datum aussehen -
# Rechnungsnummern der Form "1234-5-6" ergeben sonst das Jahr 1234.
JAHR_VON, JAHR_BIS = 1900, 2100


def _datum_bauen(fundstellen, rollen):
    """Aus den Fundstellen eines Musters ein Datum - oder nichts."""
    werte = dict(zip(rollen, fundstellen))
    jahr = int(werte["y"])
    if not (JAHR_VON <= jahr <= JAHR_BIS):
        return None
    monat = MONATE[werte["M"].lower()] if "M" in werte else int(werte["m"])
    try:
        return datetime.date(jahr, monat, int(werte["d"]))
    except ValueError:
        return None


def volle_daten_aus_text(content):
    """Alle kalendarisch gueltigen Volldaten, in der Reihenfolge im Text.

    Getrennt von ``datum_objekt_aus_text``, weil zwei Fragen daran haengen,
    die verschiedene Enden der Liste brauchen: welches Datum das Dokument
    traegt (das erste) und ob ein sehr altes ``created`` glaubwuerdig ist
    (dafuer zaehlt das spaeteste).
    """
    treffer = []
    for muster, rollen in VOLLE_DATEN:
        for fund in muster.finditer(content):
            datum = _datum_bauen(fund.groups(), rollen)
            if datum is not None:
                treffer.append((fund.start(), datum))
    treffer.sort(key=lambda t: t[0])
    return [datum for _, datum in treffer]


def datum_objekt_aus_text(content):
    """Das erste KALENDARISCH gueltige Datum im OCR-Text.

    Frueher wurde die erste datumsaehnliche Zeichenkette blind zusammengesetzt
    (f"{y}-{m}-{d}"), wodurch Titel wie "2025-09-31" entstanden - einen Tag,
    den es nicht gibt. Paperless konnte ihn nicht lesen und setzte created auf
    den Einlesetag.

    Massgeblich ist die Stelle im Text, nicht das Format: gesucht wird ueber
    alle Muster gleichzeitig, gewonnen hat der frueheste gueltige Fund. Sonst
    haette die Reihenfolge der Muster darueber entschieden, welches Datum ein
    Dokument traegt - und die ist willkuerlich.

    Monat und Jahr ohne Tag ("Maerz 2024") zaehlen nur, wenn sonst gar nichts
    zu finden war; das Ergebnis ist dann der Monatserste. Fuer den Jahres-Tag
    - den eigentlichen Zweck - reicht das, fuer den Tag im Monat ist es eine
    Annahme, und die soll kein vollstaendiges Datum verdraengen.
    """
    daten = volle_daten_aus_text(content)
    if daten:
        return daten[0]

    fund = NUR_MONAT_JAHR.search(content)
    if fund:
        jahr = int(fund.group(2))
        if JAHR_VON <= jahr <= JAHR_BIS:
            return datetime.date(jahr, MONATE[fund.group(1).lower()], 1)
    return None


def datum_aus_text(content):
    """Dasselbe Datum als ISO-Zeichenkette - so braucht es der Titel."""
    datum = datum_objekt_aus_text(content)
    return datum.isoformat() if datum else None


JAHRES_TAG_FARBE = "#c9c9c9"
MARKER_TAG = "jahr-unklar"
MARKER_TAG_FARBE = "#e8a33d"


def datum_ist_plausibel(datum, heute):
    """Ein Datum, das als Dokumentdatum ueberhaupt in Frage kommt.

    Die Grenzen sind bewusst weit gezogen: der Bestand enthaelt echte Scans
    bis zurueck ins Jahr 1933. Ausgeschlossen wird nur, was nicht sein kann -
    ein Datum in der Zukunft (OCR liest Fristen, Gueltigkeits- und
    Faelligkeitsangaben gleichrangig mit) und ein Jahr vor 1900, wo es sich
    praktisch immer um verlesene Ziffern handelt.
    """
    return JAHR_VON <= datum.year and datum <= heute


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

    Rueckgabe: ``(datum, quelle)`` mit quelle aus ``paperless`` (created ist
    belastbar), ``ocr`` (hier aus dem Text korrigiert) oder ``unklar`` (es
    gibt kein Datum, dem zu trauen waere).
    """
    heute = heute or timezone.localdate()
    created = doc.created
    aus_text = datum_objekt_aus_text(content or "")

    if created == einlesetag(doc):
        if (
            aus_text is not None
            and aus_text != created
            and datum_ist_plausibel(aus_text, heute)
        ):
            return aus_text, "ocr"
        return created, "unklar"

    if created_ist_zweifelhaft(doc, created, content or "", heute):
        return created, "unklar"
    return created, "paperless"


# Ein Dokument kann nichts nennen, was zu seiner Entstehung noch nicht
# geschehen war. Nennt der Text ein Datum, das so viele Jahre nach dem
# Dokumentdatum liegt, stimmt eines von beiden nicht.
TEXT_IST_NEUER_JAHRE = 5


def created_ist_zweifelhaft(doc, created, content, heute):
    """Ob ``created`` das Dokument beschreibt oder etwas anderes im Text.

    Der Anlass ist gemessen, nicht ausgedacht. Im Bestand tragen neun
    Rechnungen und Befunde das created 1933-01-17 und sieben Versicherungs-
    unterlagen die 1961-02-05 - beides Geburtsdaten, die eine fruehere
    Fassung dieses Skripts als Dokumentdatum uebernommen hat, weil sie
    schlicht die erste Zahlenfolge im Text nahm. Bei Dokument 683 liess es
    sich Zeile fuer Zeile nachsehen: das Briefdatum "02. Maerz 2023" steht
    im Briefkopf, die 17.01.1933 weiter unten als Geburtsdatum der
    begutachteten Person.

    Der Test ist das SPAETESTE Datum im Text, nicht das erste. Bei genau
    diesen Dokumenten steht das falsche Datum ganz oben - es ist also selbst
    der frueheste Fund, und ein Vergleich damit ginge im Kreis. Erst das
    Rechnungsdatum weiter unten verraet, dass 1933 nicht stimmen kann.

    Ein Abstand zum Scantag wird ausdruecklich NICHT mehr verlangt. Diese
    Zusatzbedingung stand hier zuerst und liess Dokument 870 durch: created
    2020-08-01, im Text aber nur 2024-12-18 und 2025-06-20 - ein Bescheid
    des Landratsamts, dessen 2020 nirgends belegt ist. Sie war ueberfluessig,
    weil ``datum_ist_plausibel`` kuenftige Daten ohnehin verwirft: Fristen
    und Laufzeiten, das eigentliche Gegenargument, zaehlen hier gar nicht
    erst mit. Ueber den Bestand kostet der Verzicht acht weitere Faelle.

    Umdatiert wird trotzdem nichts - dafuer ist die Heuristik zu grob. Die
    Faelle werden nur als unklar gemeldet und bekommen den Marker statt
    eines Jahres-Tags, den niemand geprueft hat.
    """
    daten = [d for d in volle_daten_aus_text(content) if datum_ist_plausibel(d, heute)]
    if not daten:
        return False
    return max(daten).year >= created.year + TEXT_IST_NEUER_JAHRE


def tag_holen(name, farbe):
    """Den Tag mit diesem Namen - angelegt, falls es ihn noch nicht gibt.

    Neu angelegte Tags bekommen ausdruecklich MATCH_NONE. Ohne das haengt
    Paperless sie spaeter von sich aus an jedes Dokument, in dem die
    Zeichenkette irgendwo im Text auftaucht - bei Jahreszahlen waere das
    so ziemlich jedes.
    """
    tag = Tag.objects.filter(name=name).first()
    if tag is None:
        # MATCH_NONE ist in Paperless 3.0.4 die 0 (nachgemessen, nicht geraten).
        # Der Ersatzwert ist derselbe: waere die Konstante eines Tages weg,
        # ist 0 immer noch das Feld-Default und damit die harmlose Wahl.
        tag = Tag.objects.create(
            name=name,
            matching_algorithm=getattr(Tag, "MATCH_NONE", 0),
            color=farbe,
        )
        print(f"Tag angelegt: {name}")
    return tag


def tag_anhaengen(doc, tag):
    """Tag setzen, falls er noch nicht dranhaengt."""
    if doc.tags.filter(pk=tag.pk).exists():
        print(f"Tag bereits gesetzt: {tag.name}")
        return False
    doc.tags.add(tag)
    print(f"Tag gesetzt: {tag.name}")
    return True


def jahres_tag_setzen(doc, datum):
    """Das Jahr des Dokumentdatums als Tag - ausschliesslich additiv.

    Es wird nur hinzugefuegt, nie ein anderer Jahres-Tag entfernt. Ein
    abweichender bleibt also stehen: bei einem Steuerbescheid aus 2025 fuer
    das Jahr 2024 ist "2024" eine fachliche Angabe des Menschen und kein
    Fehler des Skripts - sie zu loeschen waere Informationsverlust.
    """
    return tag_anhaengen(doc, tag_holen(str(datum.year), JAHRES_TAG_FARBE))


def marker_entfernen(doc):
    """Den Unklar-Marker abraeumen, sobald ein Datum feststeht.

    Anders als die Jahres-Tags ist der Marker eine Aussage dieses Skripts
    ueber sich selbst ("ich konnte es nicht bestimmen"). Stimmt sie nicht
    mehr, gehoert sie weg - sonst sammelt sich ein Filter voll Faelle an,
    die laengst erledigt sind.
    """
    tag = Tag.objects.filter(name=MARKER_TAG).first()
    if tag and doc.tags.filter(pk=tag.pk).exists():
        doc.tags.remove(tag)
        print(f"Marker entfernt: {MARKER_TAG}")
        return True
    return False


def jahr_taggen(doc, content):
    """Datum ermitteln, notfalls korrigieren, Jahr als Tag setzen.

    Ohne belastbares Datum wird ausdruecklich NICHT getaggt. Ein Jahres-Tag
    aus dem Scantag waere eine Behauptung ueber das Dokument, die niemand
    geprueft hat - und weil er aussieht wie jeder andere Jahres-Tag, wuerde
    er die Jahresfilter unbemerkt unzuverlaessig machen. Stattdessen setzt
    das Skript den Marker und macht die Luecke damit auffindbar.

    Eigener Fehlerschirm: dieses Skript laeuft als Post-Consume-Hook. Was
    hier schiefgeht, darf die Titel- und Owner-Zuweisung darunter nicht
    mitreissen.
    """
    try:
        datum, quelle = dokumentdatum_bestimmen(doc, content)

        if quelle == "unklar":
            print("Kein Dokumentdatum erkennbar - kein Jahres-Tag")
            tag_anhaengen(doc, tag_holen(MARKER_TAG, MARKER_TAG_FARBE))
            return

        if quelle == "ocr":
            doc.created = datum
            doc.save(update_fields=["created"])
            print(f"Dokumentdatum korrigiert: {datum.isoformat()} (war Einlesetag)")
        else:
            print(f"Dokumentdatum: {datum.isoformat()}")

        jahres_tag_setzen(doc, datum)
        marker_entfernen(doc)
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
