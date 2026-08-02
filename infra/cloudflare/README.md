# Cloudflare Access — Anmeldedienste je Anwendung

## `cf_access_idp_pin.py`

```
./cf_access_idp_pin.py --trocken     zeigt alle drei Schritte, ändert nichts
./cf_access_idp_pin.py --schritt 1   nagelt alle Anwendungen auf GitHub fest
./cf_access_idp_pin.py --schritt 2   legt den Einmal-PIN-Anbieter an
./cf_access_idp_pin.py --schritt 3   öffnet nur docs.iil.pet für PIN + zwei Adressen
```

Liest `~/.secrets/cloudflare_write_token` und `~/.secrets/cloudflare_account_id`.

## Der Anlass

Mara und Bine brauchten Zugang zu `docs.iil.pet`, haben aber kein GitHub-Konto — und
GitHub war der einzige konfigurierte Anmeldedienst im Konto.

## Warum die Reihenfolge zwingend ist

Alle 16 Access-Anwendungen hatten `allowed_idps` **leer**. Leer heißt bei Cloudflare
nicht „keiner", sondern *alle im Konto konfigurierten Anbieter*. Ein neu angelegter
Einmal-PIN hätte damit voraussichtlich sofort überall gegolten — auch für
`praes.iil.ai` (LRA) und `schulungspass.de`. Deshalb erst festnageln, dann anlegen,
dann gezielt **eine** Anwendung öffnen. Schritt 2 verweigert den Dienst, solange auch
nur eine Anwendung offen ist.

## Zwei Fallen

- **Der Endpunkt kennt kein `PATCH`.** Ein erster Anlauf mit `PATCH` scheiterte an allen
  16 Anwendungen mit `HTTP 405 — 10405 Method not allowed for this authentication
  scheme`. Die Fehlermeldung liest sich wie ein Berechtigungsproblem, ist aber keins:
  der Endpunkt nimmt nur `PUT`. Weil `PUT` **ersetzt**, schickt das Skript den gelesenen
  Stand vollständig zurück und tauscht nur `allowed_idps` aus; die Richtlinien gehen als
  Referenz (`id` + Reihenfolge) mit, nicht als Inhalt.
- **Schreibrechte nie ungeprüft auf 16 Objekte loslassen.** Schritt 1 schreibt zuerst
  eine einzige Anwendung als Probe und bricht bei Fehlschlag ab — die anderen 15 bleiben
  unberührt.

Vor jedem Schritt wird der Vorher-Stand nach `~/cf_access_sicherung/` gesichert.

## Stand 2026-08-02

16 Anwendungen auf GitHub festgenagelt. Einmal-PIN existiert, gilt aber ausschließlich
auf `docs.iil.pet`. Dessen Richtlinie *Owner (Achim)* erlaubt vier Adressen:
`achim.dehnert@iil.gmbh`, `admin@wir-digital.de`, `md@dehnert.team`, `sd@dehnert.team`.
