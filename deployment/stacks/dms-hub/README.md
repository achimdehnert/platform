# dms-hub — Verbindung zu Paperless

## `paperless_interner_pfad.sh`

Stellt dms-hub vom öffentlichen auf den internen Weg zu Paperless um. Liegt auf dem
Prod-Host unter `/root/`, hier gespiegelt.

```
bash paperless_interner_pfad.sh            Trockenlauf
bash paperless_interner_pfad.sh --scharf   stellt um
```

### Warum

`PAPERLESS_URL` zeigte auf `https://docs.iil.pet`. Seit dort Cloudflare Access davorsteht,
bekommt dms-hub eine Weiterleitung auf die Anmeldeseite statt JSON.
`fetch_paperless_documents()` fängt jede Ausnahme ab und gibt `None` zurück — der Spiegel
stand vom 2026-07-19 bis 2026-08-02 still, **ohne einen einzigen Fehler im Log**.

Beide Container hängen im Netz `bf_platform_prod`. Der direkte Weg umgeht Cloudflare
vollständig, scheitert aber an Djangos `ALLOWED_HOSTS`, solange der Host-Kopf fehlt:

```
http://iil_dochub_web:8000/api/                        -> 400
http://iil_dochub_web:8000/api/  + Host: docs.iil.pet  -> 200
```

Gesetzt werden deshalb zwei Werte in `/opt/dms-hub/.env.prod`:
`PAPERLESS_URL=http://iil_dochub_web:8000` und `PAPERLESS_HOST_HEADER=docs.iil.pet`.
An doc-hub ändert sich nichts.

### Eine Falle, die zwei Anläufe gekostet hat

**`docker restart` reicht nicht.** Compose wertet `env_file` nur beim *Erzeugen* eines
Containers aus; ein Neustart läuft mit den alten Werten weiter. Der erste Anlauf meldete
deshalb einen erfolgreichen Durchlauf und trotzdem `FEHLGESCHLAGEN (None)` — im Container
stand unverändert die öffentliche Adresse. Das Skript benutzt jetzt
`docker compose up -d --force-recreate` und **liest die Werte danach aus dem Container
zurück**, statt den Neustart als Beweis zu nehmen.

Nach der Umstellung: `fetch_paperless_documents()` → 814 Dokumente,
`sync_paperless_documents()` → `45 created, 769 updated`.

### Offen

Der Abgleich läuft nirgends automatisch — kein Celery-Task, kein Zeitplan, und ein
Fehlschlag meldet sich als `None` statt zu scheitern: `achimdehnert/dms-hub#53`.
