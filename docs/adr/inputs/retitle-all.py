#!/usr/bin/env python3
"""Re-title all documents that have bad/auto-generated titles."""
import os
import re
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")

import django
django.setup()

from documents.models import Document

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
    if not content or len(content.strip()) < 10:
        return None
    lines = [
        ln.strip() for ln in content.split("\n")
        if ln.strip() and len(ln.strip()) > 3
    ]
    if not lines:
        return None

    doc_type = None
    for dt in DOC_TYPES:
        if re.search(rf"\b{dt}\b", content, re.IGNORECASE):
            doc_type = dt.capitalize()
            break

    sender = None
    for line in lines[:10]:
        if re.match(r"^[\d\s./-]+$", line):
            continue
        if len(line) < 5 or len(line) > 80:
            continue
        if re.search(
            r"(Dr\.|Prof\.|GmbH|AG|e\.V\.|Inc|Ltd|Versicherung|"
            r"Bank|Kasse|Sparkasse|Stadtwerke|Gemeinde|Finanzamt|"
            r"Krankenkasse|AOK|TK|Barmer|DAK|IKK|Allianz|ADAC|"
            r"Telekom|Vodafone|O2)",
            line,
        ):
            sender = re.sub(r"[\t]+", " ", line).strip()[:60]
            break

    date_match = re.search(
        r"(\d{1,2})[./](\d{1,2})[./](\d{4})", content
    )
    date_str = None
    if date_match:
        d, m, y = date_match.groups()
        date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

    parts = [p for p in [doc_type, sender, date_str] if p]
    if parts:
        return " - ".join(parts)

    for line in lines[:5]:
        if len(line) > 10 and not re.match(r"^[\d\s./-]+$", line):
            return line[:80]
    return None


def needs_retitle(title):
    if re.match(r"^\d{8,14}", title):
        return True
    if title.endswith(".pdf"):
        return True
    return False


updated = 0
skipped = 0
failed = 0

for doc in Document.objects.all():
    if not needs_retitle(doc.title):
        skipped += 1
        continue

    content = doc.content or ""
    title = extract_title(content)
    if title:
        doc.title = title
        doc.save(update_fields=["title"])
        updated += 1
        if updated <= 10:
            print(f"  {doc.pk}: {title}")
    else:
        failed += 1

print(f"\nDone: {updated} updated, {skipped} skipped, {failed} no title")
