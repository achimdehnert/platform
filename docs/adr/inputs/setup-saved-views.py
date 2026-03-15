#!/usr/bin/env python3
"""Create saved views in Paperless-ngx."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")

import django
django.setup()

from documents.models import SavedView, SavedViewFilterRule, Tag, DocumentType

# Helper: get IDs
tag_ids = {t.name: t.pk for t in Tag.objects.all()}
dt_ids = {d.name: d.pk for d in DocumentType.objects.all()}

# rule_type reference:
# 0 = title contains, 3 = correspondent is, 6 = has tag, 7 = does not have tag
# 8 = doc type is, 17 = has any tag, 20 = added after, 22 = created year

VIEWS = [
    {
        "name": "Alle Rechnungen",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": True,
        "show_in_sidebar": True,
        "rules": [
            (8, str(dt_ids.get("Rechnung", ""))),
        ],
    },
    {
        "name": "Steuer-relevant",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": True,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Steuer-relevant", ""))),
        ],
    },
    {
        "name": "Versicherungen",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": False,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Versicherung", ""))),
        ],
    },
    {
        "name": "Gesundheit",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": False,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Gesundheit", ""))),
        ],
    },
    {
        "name": "Bank & Finanzen",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": False,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Bank/Finanzen", ""))),
        ],
    },
    {
        "name": "Auto & Mobilität",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": False,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Auto", ""))),
        ],
    },
    {
        "name": "Energie & Strom",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": False,
        "show_in_sidebar": True,
        "rules": [
            (6, str(tag_ids.get("Energie", ""))),
        ],
    },
    {
        "name": "Verträge",
        "sort_field": "created",
        "sort_reverse": True,
        "show_on_dashboard": True,
        "show_in_sidebar": True,
        "rules": [
            (8, str(dt_ids.get("Vertrag", ""))),
        ],
    },
    {
        "name": "Ungetaggt",
        "sort_field": "added",
        "sort_reverse": True,
        "show_on_dashboard": True,
        "show_in_sidebar": True,
        "rules": [
            (17, "false"),
        ],
    },
    {
        "name": "Zuletzt hinzugefügt",
        "sort_field": "added",
        "sort_reverse": True,
        "show_on_dashboard": True,
        "show_in_sidebar": True,
        "rules": [],
    },
]


for view_def in VIEWS:
    name = view_def["name"]
    view, created = SavedView.objects.get_or_create(
        name=name,
        defaults={
            "sort_field": view_def["sort_field"],
            "sort_reverse": view_def["sort_reverse"],
            "show_on_dashboard": view_def["show_on_dashboard"],
            "show_in_sidebar": view_def["show_in_sidebar"],
        },
    )
    status = "NEW" if created else "exists"

    if created:
        for rule_type, value in view_def["rules"]:
            if value:
                SavedViewFilterRule.objects.create(
                    saved_view=view,
                    rule_type=rule_type,
                    value=value,
                )

    print(f"  {status:6s}  {name}")

print(f"\nTotal saved views: {SavedView.objects.count()}")
