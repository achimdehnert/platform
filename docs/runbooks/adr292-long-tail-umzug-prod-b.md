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
| apo-hub | 203 | 3 | **Pilot** — 2026-08-04 durchgeführt, siehe unten |
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

**Immer als Superuser dumpen — sonst entsteht stillschweigend Datenverlust.**
Steht auch nur eine Tabelle unter Row-Level-Security und hat der App-User kein
`BYPASSRLS`, bricht pg_dump mit `query would be affected by row-level security
policy` ab — **schreibt die Datei aber trotzdem**. Bei `pptx-hub` waren das
138K statt 139K; über die Dateigröße ist das nicht zu erkennen. Deshalb:

```bash
# Superuser-Rolle ermitteln (NICHT blind POSTGRES_USER nehmen)
docker exec <app>_db psql -U <app-user> -d <db> -tAc \
  "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolcanlogin"
# dumpen und Objektzahl pruefen — die ist der Beleg, nicht der Exit-Code allein
docker run --rm -v /tmp:/t <db-image> pg_restore --list /t/<app>.dump | grep -c '^[0-9]'
```

**Die Rollenlage muss auf dem Zielhost nachgebaut werden.** Der Bootstrap-User
eines Postgres-Containers (`POSTGRES_USER`) ist dort **immer** Superuser und
kann das nicht verlieren (`the bootstrap user must have the SUPERUSER
attribute`). Startet man den Zielcontainer mit dem *App*-Benutzernamen, hat die
App auf dem neuen Host `BYPASSRLS` — und eine RLS-gestützte Mandantentrennung
ist dort wirkungslos, ohne dass irgendetwas fehlschlägt. Richtig:

1. Zielcontainer einmalig mit `POSTGRES_USER=<superuser>` initialisieren
2. App-Rolle danach anlegen: `CREATE ROLE <app> LOGIN NOSUPERUSER NOBYPASSRLS`
3. Restore als Superuser
4. Rollenlage gegen die Quelle vergleichen (`rolsuper`/`rolbypassrls` je Rolle)

**Passwörter nicht aus `.env` ableiten, sondern den SCRAM-Verifier kopieren.**
Welche Rolle die App tatsächlich benutzt, steht nicht zuverlässig in
`POSTGRES_USER` — `pptx-hub` verbindet sich als `pptx_hub`, obwohl dort
`pptx_hub_app` steht. Statt zu raten, den Verifier je Rolle übertragen; das
umgeht Quoting- und Encoding-Fragen und lässt keinen Klartext entstehen:

```bash
ssh <quelle> "docker exec <app>_db psql -U <su> -tAc \
  \"SELECT rolpassword FROM pg_authid WHERE rolname='<rolle>'\"" \
  | ssh <ziel> 'read -r H; docker exec -i <app>_db psql -U <su> -v h="$H" \
      -c "ALTER ROLE <rolle> PASSWORD :'"'"'h'"'"'"'
```

Beim Zeilenvergleich unbedingt **als Superuser zählen** — als App-User filtert
RLS die Ergebnisse und beide Seiten sehen gleich falsch aus.

**PostGIS-Apps** (Image `postgis/postgis`) melden beim Restore zuverlässig drei
Fehler `schema "tiger" | "tiger_data" | "topology" already exists` und `exit=1` —
das Image legt diese Schemas beim Init selbst an, der Dump bringt sie mit.
Das ist folgenlos, **aber nur nachweislich**. Pflichtschritt, nicht optional:

```bash
# auf BEIDEN Hosts laufen lassen und die Ausgaben diffen
for t in $(docker exec <app>_db psql -U <user> -d <db> -tAc \
    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"); do
  echo "$t $(docker exec <app>_db psql -U <user> -d <db> -tAc \
    "SELECT count(*) FROM public.\"$t\"")"
done
```

Erst wenn Tabellenliste und alle Zeilenzahlen identisch sind, gilt der Restore
als geglückt — der Exit-Code allein sagt darüber nichts.

### 4. Container starten und prüfen

Zwei Fallen, beide im Pilot aufgetreten:

**Externe Netze existieren auf dem Zielhost nicht.** `apo-hub` verlangt
`bf_platform_prod` (`external: true`); ohne das bricht Compose ab:

```bash
ssh root@89.167.43.30 "docker network create <netzname>"   # falls external
```

**Nicht alle definierten Services laufen auch.** `apo-hub` definiert
`*-worker` und `*-beat`, die auf `prod` nicht laufen. Ein pauschales
`up -d` startet auf dem Zielhost mehr als vorher lief. Deshalb vorher
`docker ps` auf der Quelle vergleichen und nur die tatsächlich laufenden
Services benennen:

```bash
ssh root@89.167.43.30 "cd /opt/<app> && IMAGE_TAG=<tag> \
  docker compose -f docker-compose.prod.yml up -d <service-db> <service-redis> <service-web>"
```

`IMAGE_TAG` nicht vergessen: Compose interpoliert `${IMAGE_TAG:-latest}` aus
`.env`, **nicht** aus `.env.prod` — ohne Angabe wird `latest` gezogen statt des
Tags, der auf `prod` läuft.

Port aus `infra/ports.yaml` — er bleibt gleich, weil die Hosts getrennt sind
(ADR-164). Health-Endpunkt gegen `localhost:<port>` prüfen, noch ohne DNS.

### 5. Ingress anlegen

nginx-vhost auf `prod-b` nach dem Muster
`/etc/nginx/sites-enabled/illustration.iil.pet.conf`.

**Zuerst alle `server_name` des Quell-vhosts auslesen — das Register kennt sie
womöglich nicht.** Der `pptx-hub`-vhost auf `prod` bedient **fünf** Namen in
**drei** Cloudflare-Zonen (`pptx-hub.iil.pet`, `prezimo.de`, `www.prezimo.de`,
`prezimo.com`, `www.prezimo.com`); `ports.yaml` führte davon zwei. Wer nur den
Namen aus dem Register umschaltet, bricht die übrigen, sobald die Quelle
abgeschaltet wird.

```bash
grep -h server_name /etc/nginx/sites-enabled/<app>*.conf | sort -u
```

**Auf `prod-b` wird kein TLS terminiert.** Dort liegen 0 Zertifikatsdateien und
kein aktiver vhost hat eine `ssl_certificate`-Direktive (gemessen 2026-08-04;
auf `prod` findet derselbe Suchlauf 224 Dateien). Der vhost bekommt deshalb
`listen 127.0.0.1:<freier-port>;` statt `listen 443 ssl` — TLS macht der
Cloudflare-Edge, der Tunnel spricht HTTP zum Origin. Private Schlüssel wandern
nicht mit.

Dabei **`X-Forwarded-Proto https` fest setzen**, nicht `$scheme`: der Origin
spricht HTTP, Django würde sonst http-URLs bauen und in Redirect-Schleifen
laufen.

### 6. Ingress umschalten und beweisen

Der Ingress läuft über **Cloudflare-Tunnel**, nicht über A-Records: der
öffentliche Name ist ein CNAME auf `<tunnel-id>.cfargotunnel.com`. Umschalten
heißt deshalb zweistufig, **in dieser Reihenfolge** — umgekehrt entsteht eine
404-Lücke:

1. Route im Ziel-Tunnel eintragen (`/etc/cloudflared/config.yml`, vor der
   Catch-all-Zeile `- service: http_status:404`), dann
   `cloudflared tunnel ingress validate`.
   ⚠ **`cloudflared` kennt kein `reload`** (`Job type reload is not applicable`)
   — es braucht `systemctl restart`, und der trennt **alle** Routen dieses
   Tunnels für einige Sekunden. Auf `prod-b` mit einer Handvoll Routen
   unkritisch; auf `prod` trifft es die gesamte Plattform und gehört in ein
   Wartungsfenster.
2. CNAME auf die Tunnel-ID des Zielhosts umhängen (`proxied` beibehalten).

**Nachweis — der externe `curl` taugt dafür nicht.** Vor den Hubs steht
Cloudflare Access: jede unauthentifizierte Anfrage endet mit 302 auf
`iil-team.cloudflareaccess.com`, auch eine auf einen frei erfundenen Pfad. Ein
302 unterscheidet also weder „Anwendung antwortet" noch „welcher Host bedient".

Belastbarer Nachweis:

```bash
# 1) Anfrage mit Access-Service-Token und eindeutigem Marker (erwartet: 200)
curl -s -o /dev/null -w "%{http_code}\n" -A "iil-marker-<datum>-<app>" \
  -H "CF-Access-Client-Id: $(tr -d '\n' < ~/.secrets/cf_access_client_id)" \
  -H "CF-Access-Client-Secret: $(tr -d '\n' < ~/.secrets/cf_access_client_secret)" \
  https://<host>/

# 2) Marker in den Zugriffsprotokollen BEIDER Hosts suchen
ssh root@<host> "grep -rl 'iil-marker-<datum>-<app>' /var/log/nginx/; \
                 wc -l < /var/log/nginx/access.log"
```

Die zweite Ausgabe (`wc -l`) ist die **Kalibrierung**: ein „kein Treffer" auf
dem alten Host beweist nur dann etwas, wenn dessen Log nachweislich lebt. Ohne
diese Gegenprobe ist die Null womöglich der eigene Filter und nicht die Welt.

**Je Hostname einen eigenen Marker verwenden.** Das nginx-Log führt den
`Host`-Header nicht mit; bei mehreren Domains lässt sich sonst nicht sagen,
*welche* noch am alten Host hängt. Beim pptx-hub-Umzug ergaben drei Anfragen
mit **einem** Marker „prod 1 / prod-b 2" — welche der drei Domains die
Nachzüglerin war, war daraus nicht ableitbar. Mit fünf Einzelmarkern war die
Zuordnung eindeutig (prod 0, prod-b 5).

**Direkt nach dem CNAME-Schwenk mit Nachzüglern rechnen.** Der Cloudflare-Edge
liefert für kurze Zeit noch an den alten Tunnel. Ein einzelner Treffer auf dem
alten Host unmittelbar nach der Umstellung ist deshalb kein Fehler, sondern ein
Grund, die Messung eine Minute später zu wiederholen — und **erst bei 0 auf der
alten Seite** darf Schritt 7 folgen.

### 7. Alte Instanz stoppen und Register nachziehen

```bash
ssh root@88.198.191.108 "cd /opt/<app> && docker compose -f docker-compose.prod.yml down"
```

Im selben Zug in `infra/ports.yaml` `prod_host: prod-b` setzen und den
`hosts.yaml`-Eintrag ergänzen. **Genau dieser Schritt ist bei `illustration-hub`
unterblieben**: das Register meldet seit dem 2026-08-02 „prod-Kopie gestoppt",
während beide Instanzen weiterlaufen (#1738). Ein Umzug ohne Schritt 7 erzeugt
einen Doppellauf mit möglicherweise auseinanderlaufenden Datenbanken.

**Den Stop messen, nicht übernehmen.** „Ist gestoppt" ist eine prüfbare
Behauptung — auch wenn sie von einem Menschen kommt. Der Eintrag ins Register
darf erst danach erfolgen:

```bash
ssh root@<alter-host> 'docker ps --filter name=<app>_ --format "{{.Names}}" | wc -l
docker inspect <app>_web --format "{{.State.StartedAt}} {{.State.Running}}"'
```

`0` laufende Container ist der Beleg. Ein unveränderter `StartedAt` beweist,
dass nichts passiert ist — genau daran ist der apo-hub-Pilot am 2026-08-04
hängen geblieben: der Stop galt als erledigt, die drei Container liefen mit
bit-identischem Zeitstempel weiter. Wäre der Wert ungeprüft ins Register
gewandert, hätte der Pilot exakt den Fehler reproduziert, den er beheben sollte.

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
