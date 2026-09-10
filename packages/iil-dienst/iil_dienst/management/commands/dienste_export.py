"""``manage.py dienste_export`` — alle Vertraege des Hubs als JSON (fuer das Gateway)."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from iil_dienst import __version__, katalog


class Command(BaseCommand):
    help = "Vertraege aller registrierten Dienste als JSON ausgeben (iil-dienst)"

    def handle(self, *args, **options):
        self.stdout.write(json.dumps({"iil_dienst": __version__, "dienste": katalog()}, ensure_ascii=False))
