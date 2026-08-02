"""Erzeugt einen neuen Paperless-API-Token fuer einen Benutzer.

Schreibt den Wert AUSSCHLIESSLICH nach stdout, damit der Aufrufer ihn direkt in
eine Datei mit chmod 600 umleiten kann. Kein print, keine Zusatzausgabe — sonst
landet Beiwerk im Token.

Aufruf im Container:  python3 /usr/src/paperless/scripts/rotate_token.py <username>
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
sys.path.insert(0, "/usr/src/paperless/src")

import django

django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

if len(sys.argv) < 2:
    sys.stderr.write("Benutzername fehlt\n")
    sys.exit(2)

name = sys.argv[1]
trockenlauf = "--trocken" in sys.argv

try:
    u = User.objects.get(username=name)
except User.DoesNotExist:
    sys.stderr.write("Benutzer %r existiert nicht\n" % name)
    sys.exit(3)

vorhanden = Token.objects.filter(user=u).first()

if trockenlauf:
    sys.stderr.write(
        "TROCKENLAUF: Benutzer=%s vorhandener_Token=%s erstellt=%s — nichts geaendert\n"
        % (name, bool(vorhanden), vorhanden.created.strftime("%Y-%m-%d") if vorhanden else "-")
    )
    sys.exit(0)

Token.objects.filter(user=u).delete()
neu = Token.objects.create(user=u)
sys.stdout.write(neu.key)
