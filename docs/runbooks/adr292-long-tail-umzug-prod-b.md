# Runbook: Long-Tail-Umzug von `prod` nach `prod-b` (ADR-292)

> Stand 2026-08-04. Alle Zahlen sind gemessen, nicht geschätzt — Erhebung siehe
> Abschnitt „Messbasis". Dieses Runbook beschreibt ein Verfahren; es ist **nicht**
> ausgeführt.

## Warum es dieses Runbook braucht

ADR-292 beschloss die Umzugswelle und formulierte als Invariante 2:

> **Placement-SSoT:** `infra/ports.yaml` Feld `prod_host` (Default `prod`).
> Deploy-Workflows lesen es; Handverteilung ist ein Regelverstoß.

**Das trifft nicht zu.** `prod_host` kommt im gesamten Repo nur an drei Stellen
vor: als Kommentar in `ports.yaml`, als eine einzige Zuweisung bei
`illustration-hub` und im Fließtext von `hosts.yaml`. Kein Workflow, kein Skript
und kein Deploy-Pfad wertet es aus (`grep -rl prod_host .github/ tools/ infra/`).

Was den Zielhost tatsächlich bestimmt, ist der **self-hosted Actions-Runner**:
auf `prod` liegt für praktisch jedes Repo ein eigener Runner
(`/opt/actions-runner-<app>`, 25 Stück gezählt). Der Deploy-Job läuft dort, wo
sein Runner läuft. Ein Umzug ist damit kein Konfigurationswert, sondern eine
Ummeldung — und die vier Arbeitsschritte darunter (Verzeichnis, Datenbank,
Ingress, DNS) sind Handarbeit auf zwei Produktionshosts.

Der Umzug von `illustration-hub` lief genau so. Er ist der einzige Präzedenzfall
und die Vorlage für die Schritte unten.

## Messbasis (2026-08-04)

| Host | Typ | Preis brutto | Belegt | Container |
|---|---|---:|---:|---:|
| `prod` (88.198.191.108) | cpx52, 24 GB | 100,49 EUR/M | 43,3 % | 77 |
| `prod-b` (89.167.43.30) | cpx42, 16 GB | 69,49 EUR/M | 2,1 % | 6 |

Erhoben mit `docker stats --no-stream` je Host, Preise aus der Hetzner-API
(`/v1/servers` → `server_type.prices[].price_monthly.gross`).

## Kandidaten

**Ziehen um** (Long Tail, unkritisch nach ADR-292; Helsinki ist für alles außer
Gov-Workloads freigegeben, Owner-Auflage 2026-07-22):

| App | RAM (MiB) | Container | Anmerkung |
|---|---:|---:|---|
| trading-hub | 998 | 3 | größter Einzelgewinn |
| writing-hub | 812 | 4 | in der Ausgangsfrage genannt |
| research-hub | 696 | 4 | |
| weltenhub | 488 | 5 | |
| cad-hub | 408 | 4 | |
| dms-hub | 387 | 5 | ⚠ Dokumentenbestand vor Umzug sichten |
| wedding-hub | 372 | 5 | |
| coach-hub | 287 | 5 | |
| pptx-hub | 230 | 4 | |
| apo-hub | 203 | 3 | **Pilot-Empfehlung** — kleinster, kein Worker |
| **Summe** | **4881** | | ≈ 4,8 GiB |

**Bleiben auf `prod`** (Prod-Kern laut ADR-292):

- `risk-hub` (1220 MiB) — Lane G, Kundendaten
- `iil-authentik` + `iil-authentik-server` (981 MiB) — Plattform-Identität
- `iil-knowledge-outline` (416 MiB) — Plattform-Identität
- `mcp-hub` (347 MiB) — Plattform-Identität
- `devhub` (1083 MiB) — Kern-Hub
- `iil-dochub` inkl. tika/gotenberg (1279 MiB) — **Streitfall**: größter
  Einzelposten und damit der wirksamste Umzug, aber der Dokumentenbestand ist
  nicht gesichtet. Owner-Entscheidung, kein Automatismus.

**Erwarteter Effekt** bei Umzug aller zehn Kandidaten:
`prod` 43,3 % → ca. 23,5 %, `prod-b` 2,1 % → ca. 31,8 %. Beide Hosts kosten
unverändert; gewonnen wird Arbeitsspeicher, nicht Geld. `prod` steht heute im
Swap — das ist der eigentliche Zweck.

## Verfahren je App

Sieben Schritte. Schritt 0 und 7 sind die, die beim Präzedenzfall gefehlt haben.

### 0. Messen und sichern

```bash
# Datenmenge bestimmt Ausfallzeit — vor allem anderen messen
ssh root@88.198.191.108 "docker exec <app>_db psql -U <user> -d <db> -c \
  \"SELECT pg_size_pretty(pg_database_size(current_database()))\""
# Verifiziertes Backup nach ADR-241, NICHT nur ein Dump ins /tmp
```

### 1. Runner ummelden

Auf `prod-b` einen Runner für das Repo registrieren (Labels wie auf `prod`
übernehmen — sie steuern `runs-on`), auf `prod` erst **nach** erfolgreichem
Deploy deregistrieren. Vorlage: `/opt/actions-runner-illustration-hub`.

### 2. Verzeichnis und Umgebung übertragen

```bash
rsync -a --exclude '.git' root@88.198.191.108:/opt/<app>/ root@89.167.43.30:/opt/<app>/
```

Die `.env` enthält Zugangsdaten — nicht in Logs, nicht in Tickets, nicht in
Chat-Verläufe. Nach dem Umzug auf `prod` löschen, nicht liegen lassen.

### 3. Datenbank umziehen

```bash
ssh root@88.198.191.108 "docker exec <app>_db pg_dump -U <user> -Fc <db>" > /tmp/<app>.dump
scp /tmp/<app>.dump root@89.167.43.30:/tmp/
# Zielcontainer hochfahren, dann:
ssh root@89.167.43.30 "docker exec -i <app>_db pg_restore -U <user> -d <db> --clean" < /tmp/<app>.dump
```

Ab hier läuft die Ausfallzeit: Schreibzugriffe auf die alte Instanz gehen
verloren. Deshalb vorher Schritt 6 vorbereiten und die alte Instanz während
Dump/Restore stilllegen.

### 4. Container starten und prüfen

```bash
ssh root@89.167.43.30 "cd /opt/<app> && docker compose -f docker-compose.prod.yml up -d"
```

Port aus `infra/ports.yaml` — er bleibt gleich, weil die Hosts getrennt sind
(ADR-164). Health-Endpunkt gegen `localhost:<port>` prüfen, noch ohne DNS.

### 5. Ingress anlegen

nginx-vhost auf `prod-b` nach dem Muster
`/etc/nginx/sites-enabled/illustration.iil.pet.conf`. TLS-Kette und
Cloudflare-Einstellung der Zone gegenprüfen, bevor umgeschaltet wird.

### 6. DNS umschalten und beweisen

Cloudflare-Record auf `prod-b` zeigen lassen, dann **Marker-Request**: eine
eindeutige Anfrage absetzen und in den Zugriffsprotokollen **beider** Hosts
nachsehen, welcher sie beantwortet hat. Erst dieser Nachweis zählt als
„umgezogen" — nicht ein grüner Deploy und nicht ein 200er.

### 7. Alte Instanz stoppen und Register nachziehen

```bash
ssh root@88.198.191.108 "cd /opt/<app> && docker compose -f docker-compose.prod.yml down"
```

Im selben Zug in `infra/ports.yaml` `prod_host: prod-b` setzen und den
`hosts.yaml`-Eintrag ergänzen. **Genau dieser Schritt ist bei `illustration-hub`
unterblieben**: das Register meldet seit dem 2026-08-02 „prod-Kopie gestoppt",
während beide Instanzen weiterlaufen (#1738). Ein Umzug ohne Schritt 7 erzeugt
einen Doppellauf mit möglicherweise auseinanderlaufenden Datenbanken.

## Rückweg

Bis Schritt 6 ist der Umzug folgenlos rückgängig zu machen: DNS zurückstellen,
Container auf `prod-b` stoppen. Ab Schritt 7 ist die alte Datenbank veraltet —
ein Rückweg bedeutet dann erneutes Dump/Restore in die Gegenrichtung.

## Reihenfolge

Eine App nach der anderen, kleinste zuerst. **Pilot: `apo-hub`** (203 MiB, drei
Container, kein Worker und kein Beat) — daran wird das Verfahren einmal
vollständig durchlaufen und dieses Runbook korrigiert, bevor größere Apps folgen.
Apps mit Hintergrundjobs (`*_beat`, `*_worker`) brauchen zusätzlich die Prüfung,
ob während der Umstellung Jobs doppelt oder gar nicht laufen.

## Offene Vorbedingung

`prod` und `prod-b` melden derzeit keine Metriken (#1734). Bis das behoben ist,
ist ein Umzug nicht messbar überwacht — ein Fehlschlag fällt erst auf, wenn
jemand die Anwendung aufruft. Der Pilot sollte danach stattfinden, nicht davor.
