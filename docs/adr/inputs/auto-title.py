#!/usr/bin/env python3
"""Post-consume script: Generate document title from OCR text."""
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
except Exception as e:
    print(f"Django setup error: {e}")
    sys.exit(0)

DOC_TYPES = [
    "Rechnung", "Invoice", "Quittung", "Gutschrift",
    "Vertrag", "Kuendigung", "Mahnung", "Angebot",
    "Bescheid", "Mitteilung", "Bestaetigung", "Meldung",
    "Kontoauszug", "Abrechnung", "Beitragsbescheid",
    "Steuerbescheid", "Lohnabrechnung", "Gehaltsabrechnung",
    "Arztbrief", "Befund", "Rezept", "Ueberweisung",
    "Versicherungsschein", "Police", "Antrag",
]


def extract_title(content):
    """Extract a meaningful title from OCR text using heuristics."""
    if not content or len(content.strip()) < 10:
        return None

    lines = [l.strip() for l in content.split("\n") if l.strip() and len(l.strip()) > 3]
    if not lines:
        return None

    # Find document type
    doc_type = None
    for dt in DOC_TYPES:
        if re.search(rf"\b{dt}\b", content, re.IGNORECASE):
            doc_type = dt.capitalize()
            break

    # Find sender (company/person)
    sender = None
    for line in lines[:10]:
        if re.match(r"^[\d\s./-]+$", line):
            continue
        if len(line) < 5 or len(line) > 80:
            continue
        if re.search(
            r"(Dr\.|Prof\.|GmbH|AG|e\.V\.|Inc|Ltd|Versicherung|Bank|Kasse|"
            r"Sparkasse|Stadtwerke|Gemeinde|Finanzamt|Krankenkasse|AOK|TK|"
            r"Barmer|DAK|IKK|Allianz|ADAC|Telekom|Vodafone|O2)",
            line,
        ):
            sender = re.sub(r"[\t]+", " ", line).strip()[:60]
            break

    # Find date
    date_match = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", content)
    date_str = None
    if date_match:
        d, m, y = date_match.groups()
        date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    # Build title
    parts = [p for p in [doc_type, sender, date_str] if p]
    if parts:
        return " - ".join(parts)

    # Fallback: first meaningful line
    for line in lines[:5]:
        if len(line) > 10 and not re.match(r"^[\d\s./-]+$", line):
            return line[:80]

    return None


if __name__ == "__main__":
    try:
        doc_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DOCUMENT_ID", "")
        if not doc_id:
            sys.exit(0)

        doc = Document.objects.get(pk=int(doc_id))
        content = doc.content or ""

        if len(content.strip()) < 10:
            print(f"Doc {doc_id}: too little content")
            sys.exit(0)

        print(f"Doc {doc_id}: content_len={len(content)}")

        title = extract_title(content)
        if title:
            doc.title = title
            doc.save(update_fields=["title"])
            print(f"Title set: {title}")
        else:
            print("No title generated")

    except Exception as e:
        print(f"Script error: {e}")
        traceback.print_exc()

    # Always exit 0 to not block Paperless consumer
    sys.exit(0)
