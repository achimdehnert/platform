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
    from documents.models import Document
    from django.contrib.auth.models import User
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
    "Rechnung", "Invoice", "Quittung", "Gutschrift",
    "Vertrag", "Kuendigung", "Mahnung", "Angebot",
    "Bescheid", "Mitteilung", "Bestaetigung", "Meldung",
    "Kontoauszug", "Abrechnung", "Beitragsbescheid",
    "Steuerbescheid", "Lohnabrechnung", "Gehaltsabrechnung",
    "Arztbrief", "Befund", "Rezept", "Ueberweisung",
    "Versicherungsschein", "Police", "Antrag",
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
        print(f"Permissions granted: {", ".join(granted)}")
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


def datum_aus_text(content):
    """Erstes KALENDARISCH gueltiges Datum.

    Vorher wurde die erste datumsaehnliche Zeichenkette blind zusammengesetzt
    (f"{y}-{m}-{d}"), wodurch Titel wie "2025-09-31" entstanden - einen Tag,
    den es nicht gibt. Paperless konnte ihn nicht lesen und setzte created
    auf den Einlesetag.
    """
    for d, m, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", content):
        try:
            return datetime.date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            continue
    return None


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
                [sys.executable,
                 '/usr/src/paperless/scripts/paperless-post-consume.py',
                 str(doc_id)],
                env=os.environ.copy(),
            )
        except Exception:
            pass

    sys.exit(0)
