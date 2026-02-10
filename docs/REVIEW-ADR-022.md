# Review: ADR-022 Platform Consistency Standard

- **Reviewer**: Cascade (Production-Critical Code Review)
- **Datum**: 2026-02-10
- **Gegenstand**: ADR-022 + alle 5 docker-compose.prod.yml + Health-Endpoints + Server-State
- **Methode**: ADR-Aussagen gegen tatsächlichen Code und Server-Infrastruktur geprüft

## Gesamturteil

**ADR-022 beschreibt einen sauberen Zielzustand, aber der IST-Zustand weicht in
12 produktionskritischen Punkten ab.** Mehrere ADR-Aussagen sind bereits als
Standard formuliert, obwohl die Realität weit davon entfernt ist. Das ADR muss
den IST-Zustand ehrlich dokumentieren und den SOLL-Zustand als Migrationsschritt
kennzeichnen.

---

## Befund 1: Health-Endpoints fehlen bei 3 von 5 Projekten (KRITISCH)

**Befund**: Die Compose-Healthchecks aller 5 Projekte referenzieren `/livez/`,
aber nur 2 Projekte haben den Endpoint tatsächlich implementiert.

| Projekt | healthz.py | urls.py Eintrag | Compose Healthcheck | Status |
|---------|-----------|-----------------|--------------------|---------| 
| risk-hub | `src/core/healthz.py` | `config/urls.py` | `/livez/` | OK |
| weltenhub | `apps/core/healthz.py` | `config/urls.py` | `/livez/` | OK |
| bfagent | FEHLT | FEHLT | `/livez/` | BROKEN |
| travel-beat | FEHLT | FEHLT | (kein Healthcheck) | FEHLT |
| pptx-hub | FEHLT | FEHLT | `/livez/` | BROKEN |

**Risiko**: HOCH. Container mit Healthcheck auf nicht-existierenden Endpoint
gehen nach `start_period` + `retries * interval` in Status `unhealthy`.
Docker Compose Dependency `condition: service_healthy` anderer Services
wird BLOCKIERT. Bei Neustart/Deploy werden bfagent und pptx-hub als
unhealthy markiert.

**Empfehlung**: SOFORT `/livez/` + `/healthz/` implementieren in bfagent,
travel-beat und pptx-hub. Nicht deployen bis Endpoints vorhanden.

---

## Befund 2: Port-Registry im ADR ist faktisch falsch (MITTEL)

**Befund**: Die Port-Tabelle im ADR stimmt bei 3 von 5 Projekten nicht.

| Projekt | ADR sagt | Compose tatsächlich | Problem |
|---------|----------|--------------------|---------| 
| bfagent | 8000 | Web: KEIN Port-Mapping, Caddy: 8088 | Web geht durch Caddy |
| pptx-hub | 8083 | 8020 | ADR-Wert falsch |
| travel-beat | 8082 | Web: KEIN Port-Mapping, Caddy: 8089 | Web geht durch Caddy |
| risk-hub | 8090 | 8090 | OK |
| weltenhub | 8081 | 8081 | OK |

**Risiko**: MITTEL. Falsche Port-Dokumentation führt zu Nginx-Fehlkonfiguration
bei Deploy. MCP-Tools mit hardcoded Ports werden fehlschlagen.

**Empfehlung**: Port-Registry korrigieren. Entscheiden ob Caddy-Proxy-Pattern
Standard ist (dann Caddy-Port dokumentieren) oder ob direktes Port-Mapping
Standard wird (dann Caddy entfernen).

Korrigierte Port-Registry:

```yaml
# Tatsächlicher IST-Zustand
8088: bfagent (via Caddy)
8081: weltenhub (direkt)
8089: travel-beat (via Caddy)  # oder 8082 laut deploy/compose
8090: risk-hub (direkt)
8020: pptx-hub (direkt)
```

---

## Befund 3: env_file vs. environment-Invariante wird von 4/5 Projekten verletzt (HOCH)

**Befund**: ADR-022 fordert `env_file: .env.prod` ohne `${VAR}`-Interpolation.
Realität:

| Projekt | Methode | Verletzung |
|---------|---------|------------|
| bfagent | NUR `environment:` mit 15+ `${VAR}` | env_file fehlt komplett |
| risk-hub | NUR `environment:` mit `${VAR}` | env_file fehlt komplett |
| travel-beat | BEIDES: `environment:` + `env_file:` | Doppel-Loading, Precedence-Risiko |
| weltenhub | `env_file: .env` (nicht `.env.prod`) | Dateiname weicht ab |
| pptx-hub | `env_file: .env.prod` | OK |

**Risiko**: HOCH.
- `${VAR}` in `environment:` erfordert `.env` im selben Verzeichnis beim
  `docker compose up`. Fehlt die Datei, werden Variablen leer → stille Fehler.
- Bei travel-beat: `environment:` überschreibt `env_file`-Werte gleichen Namens.
  Das ist ein stiller Precedence-Bug. Wer ändert `.env.prod`, erwartet Effekt,
  aber `environment:` gewinnt.

**Empfehlung**: Migration auf reines `env_file`-Pattern ist richtig, aber der
Migrationsaufwand ist erheblich (alle Compose-Files + Server-`.env`-Dateien
umschreiben). Als eigene Phase im Migrationsplan aufnehmen, nicht als
"Standard der bereits gilt" formulieren.

---

## Befund 4: Image-Naming ist nicht vereinheitlicht (MITTEL)

**Befund**: 5 verschiedene Namenskonventionen:

```bash
# bfagent (env-vars, mit service-suffix)
ghcr.io/${GHCR_OWNER}/${GHCR_REPO}/bfagent-web:${BFAgent_IMAGE_TAG:-latest}

# risk-hub (env-vars mit defaults, mit service-suffix)
ghcr.io/${GHCR_OWNER:-achimdehnert}/${GHCR_REPO:-risk-hub}/risk-hub-web:${IMAGE_TAG:-latest}

# travel-beat (hardcoded, OHNE service-suffix)
ghcr.io/achimdehnert/travel-beat:${TRAVELBEAT_IMAGE_TAG:-latest}

# weltenhub (hardcoded, OHNE service-suffix)
ghcr.io/achimdehnert/weltenhub:${IMAGE_TAG:-latest}

# pptx-hub (hardcoded, MIT service-suffix)
ghcr.io/achimdehnert/pptx-hub/pptx-hub-web:${PPTX_HUB_IMAGE_TAG:-latest}
```

ADR-022 Standard: `ghcr.io/achimdehnert/<app>/<app>-web:${IMAGE_TAG:-latest}`
— **nur pptx-hub** matcht das (fast).

**Risiko**: MITTEL. CI/CD-Workflows müssen pro Projekt individuell konfiguriert
werden. Kein Copy-Paste von Workflows möglich.

**Empfehlung**: Image-Tag-Variable vereinheitlichen auf `IMAGE_TAG` (ohne Prefix).
Image-Path vereinheitlichen auf `ghcr.io/achimdehnert/<app>/<app>-web`.
Migration erfordert: Compose-File ändern + GHCR-Images unter neuem Namen pushen +
Server-Compose synchronisieren. In eigener Phase.

---

## Befund 5: travel-beat hat KEIN docker-compose.prod.yml im Root (MITTEL)

**Befund**: ADR fordert "genau EINE Datei im Repo-Root". travel-beat hat:

```
travel-beat/
├── docker-compose.local.yml          # Dev (Root)
├── docker/docker-compose.prod.yml    # Prod (NICHT Root)
├── docker/docker-compose.dev.yml     # Dev Alt
├── docker/docker-compose.yml         # Default
├── deploy/docker-compose.prod.yml    # Alt Prod
└── scripts/docker-compose.prod.yml   # Alt Prod
```

**6 Compose-Dateien**, davon **3x docker-compose.prod.yml** an verschiedenen Orten
mit verschiedenem Inhalt. Keine im Root.

**Risiko**: HOCH. Unklar welche Datei auf dem Server liegt. Der _deploy-hetzner
Workflow referenziert `docker-compose.prod.yml` relativ zum Root — findet nichts.

**Empfehlung**: Kanonische Datei nach Root verschieben. Alle Duplikate löschen.
Muss VOR CI/CD-Migration passieren.

---

## Befund 6: Netzwerk-Naming-Konflikt travel-beat ↔ bfagent (KRITISCH)

**Befund**:

```yaml
# bfagent/docker-compose.prod.yml
networks:
  platform:
    name: bf_platform_prod

# weltenhub/docker-compose.prod.yml
networks:
  bf_platform_prod:
    external: true

# travel-beat/docker/docker-compose.prod.yml
networks:
  platform:
    external: true
    name: bfagent_platform    # ANDERER NAME!
```

travel-beat referenziert `bfagent_platform`, aber bfagent erstellt
`bf_platform_prod`. Das sind **zwei verschiedene Netzwerke**.

**Risiko**: KRITISCH. Wenn travel-beat das `platform`-Netzwerk nutzen soll
(z.B. für gemeinsame Services), funktioniert die Verbindung nicht. Wenn
`bfagent_platform` nicht existiert, startet der Container nicht.

**Empfehlung**: Einheitlichen Netzwerknamen festlegen (`bf_platform_prod`).
travel-beat korrigieren. Im ADR den kanonischen Netzwerknamen dokumentieren.

---

## Befund 7: Postgres-Version-Divergenz (NIEDRIG)

**Befund**: ADR und Global Rules fordern Postgres 16. travel-beat nutzt
Postgres 15:

```yaml
# travel-beat/docker/docker-compose.prod.yml:129
travel-beat-db:
  image: postgres:15-alpine    # <- NICHT 16
```

**Risiko**: NIEDRIG, aber bei pgbouncer oder Replikation problematisch.
Pg 15 erreicht EOL November 2027.

**Empfehlung**: Bei nächstem Major-Update auf 16 migrieren. Kein sofortiger
Handlungsbedarf.

---

## Befund 8: Shared DB ohne Connection Pooling (MITTEL)

**Befund**: bfagent und weltenhub teilen sich `bfagent_db` (Postgres).
ADR erwähnt "optional pgbouncer", aber:
- Kein pgbouncer deployed
- Keine Connection-Limits in Django-Settings
- Kein separates Schema — beide Apps schreiben in gleiche DB

**Risiko**: MITTEL.
- Migrations-Kollision: Wenn beide Apps gleichzeitig migrieren, können
  Lock-Timeouts entstehen.
- Connection-Exhaustion: Django default `CONN_MAX_AGE=0` öffnet pro Request
  eine neue Connection.

**Empfehlung**: Mindestens `CONN_MAX_AGE=600` in Django-Settings setzen.
Mittelfristig weltenhub in eigene DB migrieren (ADR erwähnt dies nicht).

---

## Befund 9: ADR deklariert `version: '3.8'` nicht als verboten (NIEDRIG)

**Befund**: travel-beat hat `version: '3.8'` (deprecated seit Compose V2).
ADR-022 Template hat kein `version:` Key — korrekt — aber verbietet es
auch nicht explizit.

**Risiko**: NIEDRIG. Kein funktionaler Impact, aber erzeugt Warnings.

**Empfehlung**: In Compliance-Checkliste aufnehmen: "Kein `version:` Key".

---

## Befund 10: Weltenhub-Migration rsync→Image hat keinen Rollback-Plan (HOCH)

**Befund**: ADR fordert "nur compose + .env auf Server". Weltenhub hat aktuell
vollen Source-Code auf dem Server. Phase 2.2 sagt "auf Image-Pull migrieren",
aber:
- Kein Dockerfile im weltenhub-Repo unter `docker/app/`
- Aktuelles Image (`ghcr.io/achimdehnert/weltenhub`) — unklar ob es existiert
  und aktuell ist
- Kein Rollback-Plan wenn Image-basierter Deploy fehlschlägt

**Risiko**: HOCH. Wenn die Migration scheitert, ist der Server-Source die
einzige funktionierende Version. Löschen VOR erfolgreichem Image-Deploy
ist gefährlich.

**Empfehlung**:
1. Erst Image bauen + auf GHCR pushen + verifizieren
2. Dann parallel testen (neuer Container neben bestehendem)
3. Erst nach Verifizierung alten Source-Code archivieren (nicht löschen)
4. Rollback-Anleitung in DEPLOYMENT.md

---

## Befund 11: PAT-Token in Git-History (KRITISCH)

**Befund**: bfagent und mcp-hub Remote-URLs enthalten PAT-Token:

```
origin  https://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@github.com/...
```

Der Token steht in `.git/config` und damit potenziell im `git reflog`.
Auch nach `git remote set-url` bleibt der alte Wert im Reflog.

**Risiko**: KRITISCH. Token-Leak-Risiko. GitHub sollte den Token automatisch
revoken wenn er in einem Push auftaucht, aber `.git/config` ist lokal.

**Empfehlung**:
1. Remote sofort auf SSH umstellen
2. Token auf GitHub rotieren (Settings → Developer Settings → PATs)
3. Reflog bereinigen: `git reflog expire --expire=now --all && git gc --prune=now`

---

## Befund 12: ADR fehlt Datenbank-Separierung als Standard (MITTEL)

**Befund**: ADR-022 Abschnitt 2.6 dokumentiert "Shared Services: bfagent_db ←
bfagent + weltenhub". Das widerspricht dem Prinzip "konsequente Normalisierung"
und "Separation of Concerns".

Aktueller DB-Zustand:

| App | DB-Instanz | DB-Name | Isolation |
|-----|-----------|---------|-----------|
| bfagent | bfagent_db | bfagent_prod | Shared Container |
| weltenhub | bfagent_db | weltenhub | Shared Container |
| risk-hub | risk_hub_db | risk_hub | Eigener Container |
| travel-beat | travel_beat_db | drifttales | Eigener Container |
| pptx-hub | pptx_hub_db | (geplant) | Eigener Container |

**Risiko**: MITTEL. bfagent + weltenhub teilen sich den Postgres-Prozess.
Ein `ALTER SYSTEM` oder `pg_terminate_backend()` in einer App trifft beide.

**Empfehlung**: Als explizite technische Schuld im ADR dokumentieren:
"weltenhub DB-Migration zu eigenem Container ist geplant für Phase X".
Zielzustand: Jede App hat ihren eigenen Postgres-Container.

---

## Zusammenfassung: Priorisierte Maßnahmen

### Sofort (vor nächstem Deploy)

| # | Maßnahme | Befund |
|---|----------|--------|
| S1 | `/livez/` in bfagent + travel-beat + pptx-hub implementieren | B1 |
| S2 | PAT-Token rotieren + Remotes auf SSH | B11 |
| S3 | travel-beat Netzwerk-Name korrigieren | B6 |

### Kurzfristig (diese Woche)

| # | Maßnahme | Befund |
|---|----------|--------|
| K1 | ADR Port-Registry korrigieren | B2 |
| K2 | travel-beat: Compose nach Root, Duplikate entfernen | B5 |
| K3 | ADR: IST vs SOLL klar trennen | Alle |

### Mittelfristig (2-4 Wochen)

| # | Maßnahme | Befund |
|---|----------|--------|
| M1 | env_file-Migration für bfagent + risk-hub | B3 |
| M2 | Image-Naming vereinheitlichen | B4 |
| M3 | weltenhub Image-basierter Deploy mit Rollback-Plan | B10 |
| M4 | weltenhub eigene DB-Instanz | B8, B12 |
