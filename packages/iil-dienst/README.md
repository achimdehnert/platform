# iil-dienst

Ein Dienst, zwei Zugänge (KONZ-platform-058, platform#3011). Der Vertrag sitzt an der
Service-Funktion; die App ruft sie direkt, das Gateway über `manage.py dienst_aufruf`.

```python
# apps/health/dienste.py  (wird beim Start automatisch eingesammelt)
from iil_dienst import dienst
from apps.health.services import plattform_status

dienst("plattform-status", datenklasse="intern", gate="keins",
       beschreibung="Zustand der Plattform-Dienste")(plattform_status)
```

```
INSTALLED_APPS += ["iil_dienst"]
python manage.py dienste_export                       # Verträge als JSON
python manage.py dienst_aufruf plattform-status       # {"dienst": …, "ergebnis": …}
python manage.py dienst_aufruf x --argumente '{"mandant": "devhub"}'
```

Regeln: nur Schlüsselwort-Argumente, JSON-fähige Ein- und Ausgabe, Datenklasse und Gate aus dem
Katalog; `personenbezogen`/`mandant` ohne Gate lehnt der Dekorator ab. Exit-Codes von
`dienst_aufruf`: 0 Ergebnis · 2 Vertrag verletzt · 3 der Dienst warf.

Installation bis zur PyPI-Veröffentlichung:
`pip install "iil-dienst @ git+https://github.com/achimdehnert/platform@<sha>#subdirectory=packages/iil-dienst"`
