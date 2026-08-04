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

**Geteilte Dateien außerhalb des App-Verzeichnisses werden von diesem `rsync`
nicht erfasst.** `cad-hub` bindet `/opt/shared-secrets/api-keys.env` ein — eine
Datei, die sich vier Apps teilen (cad-hub, writing-hub, onboarding-hub,
travel-beat). Fehlt sie, startet der Container gar nicht:
`env file /opt/shared-secrets/api-keys.env not found`. Vor dem Start prüfen:

```bash
grep -hoE '(env_file|source):[[:space:]]*/[^ ]+' /opt/<app>/docker-compose*.yml
grep -hoE '^[[:space:]]*-[[:space:]]*/[^:]+:' /opt/<app>/docker-compose*.yml  # bind mounts
```

Übertragung mit denselben Rechten (hier `0600 root:root`) und Prüfung per
Hash-Vergleich statt Sichtkontrolle — der Inhalt gehört nicht auf den Bildschirm.

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

**Und nicht alle laufenden Services stehen in der Datei, die man erwartet.**
Bei `weltenhub` sind `db` und `redis` **ausschließlich** in
`docker-compose.override.yml` definiert (inklusive des Volumes, das dort per
`name:` einen festen Namen bekommt). Ein Aufruf mit nur
`-f docker-compose.prod.yml` kennt sie nicht — auf dem Ziel fehlen sie dann,
und auf der Quelle würde ein solcher Aufruf sie sogar entfernen. Vor dem ersten
compose-Befehl prüfen, aus welcher Datei die laufenden Container stammen:

```bash
ls /opt/<app>/docker-compose*
docker inspect <app>_db --format '{{index .Config.Labels "com.docker.compose.config_files"}}'
# und dann konsequent BEIDE Dateien angeben:
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml up -d <services>
```

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

**Portbasiert suchen, nicht nach dem App-Namen.** vhosts heißen nicht zwingend
nach der Anwendung. `kiohnerisiko.de` wird von einem vhost namens
`kiohnerisiko.de.conf` bedient, der auf Port 8007 zeigt — also auf `coach-hub`.
Ein `grep` nach „coach" findet ihn nicht; ohne diesen Fund wäre die Domain beim
Abschalten von `prod` ausgefallen. Maßgeblich ist der Ziel-Port:

```bash
# -R (nicht -r): sites-enabled enthaelt Symlinks, denen -r NICHT folgt.
# Regex statt Fixstring: die Einrueckung nach proxy_pass variiert.
for f in $(grep -RlE "proxy_pass[[:space:]]+http://127\.0\.0\.1:<app-port>" \
             /etc/nginx/sites-enabled/); do
  echo "$f"; grep -hE "^[[:space:]]*server_name" "$f" | sort -u
done
```

Beide Abweichungen haben beim coach-hub-Umzug echte Treffer verschluckt: mit
`-r` fehlte `weltenhub` (Symlink), mit einfachem Leerzeichen fehlte `apo`
(mehrfache Einrückung). Der Suchlauf fand in drei von fünf Fällen etwas und
sah dadurch funktionsfähig aus — die beiden Nullen waren der Filter, nicht die
Welt.

**Die DNS-Records vollständig abfragen — `per_page` beachten.** Die Zone
`iil.pet` hat mehr als 50 Einträge. Eine Abfrage mit `?per_page=50` lieferte
beim weltenhub-Umzug `weltenhub.iil.pet` **nicht** zurück, obwohl der Record
existiert; die gezielte Abfrage nach dem Namen fand ihn sofort. Wer aus der
Listenansicht auf „gibt es nicht" schließt, schwenkt einen Namen zu wenig.
Deshalb je Hostname gezielt abfragen (`?name=<host>`), nicht aus einer
paginierten Liste heraus arbeiten.

**Auf `prod-b` wird kein TLS terminiert.** Dort liegen 0 Zertifikatsdateien und
kein aktiver vhost hat eine `ssl_certificate`-Direktive (gemessen 2026-08-04;
auf `prod` findet derselbe Suchlauf 224 Dateien). Der vhost bekommt deshalb
`listen 127.0.0.1:<freier-port>;` statt `listen 443 ssl` — TLS macht der
Cloudflare-Edge, der Tunnel spricht HTTP zum Origin. Private Schlüssel wandern
nicht mit.

**Hilfsport aus 9500–9599 wählen, nicht aus dem App-Bereich.** `infra/ports.yaml`
vergibt 8000–8199 an Anwendungen. Ein dort gewählter nginx-Port kollidiert
früher oder später mit der nächsten App, die auf `prod-b` zieht: Port 8094 war
zunächst der wedding-nginx und gehört laut Register `cad-hub` — beim
cad-hub-Umzug musste er erst umgezogen werden. Unterbrechungsfrei geht das, indem
der vhost übergangsweise auf **beiden** Ports lauscht, dann die Tunnel-Route
umgestellt und erst danach der alte `listen` entfernt wird.

Bereits vergeben auf `prod-b` (nicht neu belegen): 8008 coach-hub, 8021 pptx-hub,
8043 apo-hub, 8082 weltenhub, 9501 wedding-hub, 9502 research-hub, 9503 cad-hub.

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

   **Sonderfall A-Record:** `wedding-hub.iil.pet` war kein CNAME, sondern ein
   A-Record auf die prod-IP. Er muss durch einen **CNAME auf den Tunnel**
   ersetzt werden (Typ-Wechsel per `PUT` auf dieselbe Record-ID) — ein A-Record
   auf die prod-b-IP funktioniert nicht, weil dort kein TLS terminiert wird.
   Ein Skript, das nur `type == "CNAME"` behandelt, überspringt solche Records
   stillschweigend.

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

## Apps mit Worker und Beat

Die ersten beiden Umzüge (`apo-hub`, `pptx-hub`) waren Sonderfälle: `apo-hub`
hatte gar keine Hintergrundjobs, `pptx-hub`s Worker war defekt. **Alle acht
verbleibenden Kandidaten haben einen Worker, fünf zusätzlich einen Beat.**
Damit kommt eine Gefahr dazu, die das Verfahren oben nicht abdeckt.

### Warum das gefährlich ist

Zwischen Schritt 4 und Schritt 7 laufen zwei vollständige Instanzen — die alte
mit Traffic, die neue ohne. Bei einer reinen Web-App ist das harmlos. Laufen
dort aber Worker und Beat mit, verarbeiten **beide** Seiten periodische
Aufgaben, jede gegen ihre eigene Datenbank. Ergebnis: doppelte Mails, doppelte
Zustandswechsel, zwei auseinanderlaufende Wahrheiten. Der Doppellauf ist hier
nicht nur ein Registerfehler, sondern verändert Daten.

Zweiter Punkt, leicht zu übersehen: **Redis wird nicht mitmigriert.** Auf dem
Ziel entsteht eine leere Instanz. Alles, was in der alten Queue wartet, ist
nach dem Umschalten verloren.

### Erst erheben, dann entscheiden

Nicht raten, was der Beat tut — nachsehen. Read-only auf der Quelle:

```bash
# 1) Was sendet der Beat wirklich?
docker logs --tail 200 <app>_beat 2>&1 | grep -oE 'Sending due task [^ ]+ \([^)]+\)' | sort -u

# 2) Was hat der Worker zuletzt ausgefuehrt?
docker logs --tail 120 <app>_worker 2>&1 | grep -oE 'Task [a-zA-Z0-9_.]+\[' | sort | uniq -c

# 3) Liegt der Schedule in der DB (abschaltbar) oder im Code (nur Container-Stop)?
docker exec <app>_db psql -U <su> -d <db> -tAc \
  "SELECT count(*) FROM django_celery_beat_periodictask WHERE enabled"

# 4) Wartet etwas in der Queue? MUSS 0 sein, sonst gehen Jobs verloren
docker exec <app>_redis redis-cli eval "local n=0 for _,k in ipairs(redis.call('keys','*')) do if redis.call('type',k)['ok']=='list' then n=n+redis.call('llen',k) end end return n" 0
```

Danach die Tasks in drei Klassen einsortieren:

| Klasse | Beispiel (gemessen 2026-08-04) | Umgang |
|---|---|---|
| **Housekeeping** | `celery.backend_cleanup` (weltenhub, wedding-hub) | unkritisch, idempotent |
| **lesend/prüfend** | `apps.governance.tasks.check_overdue_actions` (coach-hub, täglich) | unkritisch, solange nicht im Umzugsfenster |
| **handelnd** | `trading.monitor_trades` (trading-hub, **minütlich**, schließt Positionen) | Wartungsfenster, kein Parallelbetrieb |

Für die drei anstehenden Beat-Apps ergab die Erhebung ausschließlich Klasse 1
und 2, alle **täglich**, und in allen drei Queues null wartende Jobs. Ein
Umzugsfenster von Minuten trifft einen Tagesjob mit hoher Wahrscheinlichkeit
gar nicht — und wenn doch, ist er idempotent oder nur prüfend.

### Ablauf für Klasse 1 und 2

Gegenüber dem Verfahren oben ändert sich nur, **wann** Worker und Beat laufen:

1. Auf der Quelle **zuerst Beat und Worker stoppen**, Web weiterlaufen lassen:
   `docker compose -f docker-compose.prod.yml stop <beat> <worker>`
2. Queue erneut prüfen — jetzt muss sie 0 sein (siehe Abfrage 4 oben)
3. Dump, Übertragung, Restore wie in Schritt 0–3
4. Auf dem Ziel **nur `db`, `redis`, `web`** starten — Worker und Beat bleiben aus
5. Ingress umschalten und den Marker-Nachweis führen (Schritt 6)
6. Quelle vollständig stoppen (Schritt 7)
7. **Erst jetzt** auf dem Ziel Worker und Beat starten

Zwischen 1 und 7 verarbeitet niemand Hintergrundaufgaben. Genau deshalb steht
Schritt 1 nicht früher: das Fenster soll so kurz wie möglich sein, und der
Web-Betrieb läuft dabei ununterbrochen weiter. Bei den gemessenen Tagesjobs
kostet dieses Fenster praktisch nichts; bei minütlichen Aufgaben wäre es ein
Ausfall und damit ein Fall für Klasse 3.

**Schritt 7 darf vor Schritt 6 gezogen werden** — sobald der Ingress geschwenkt
und nachgewiesen ist. Der Grund für die Reihenfolge ist allein, doppelte
Verarbeitung zu verhindern; die ist ab Schritt 1 ausgeschlossen, weil die
Quelle ihre Worker nicht mehr fährt. Das verkürzt das Fenster spürbar. Beim
weltenhub-Umzug so gemacht; der Beleg steht im Celery-Log des Ziels:

```
mingle: all alone
```

Meldet Celery dort stattdessen Nachbarn, läuft doch noch ein zweiter Worker am
selben Broker — dann sofort anhalten und die Quelle prüfen.

**Frische Named Volumes gehören root — der Beat scheitert daran.** `coach-hub`
legt seinen Schedule in `/celerybeat` ab; auf `prod` gehört das Verzeichnis
`1000:1000`, auf dem Ziel entsteht es neu als `0:0`. Der Container läuft als
`coachuser` (UID 1000) und bricht ab mit
`[Errno 13] Permission denied: '/celerybeat/celerybeat-schedule'` — dabei
meldet der Health-Status kurzzeitig `healthy`, bevor der Restart-Zyklus greift.
Besitzer aus dem Quell-Volume ablesen und auf dem Ziel setzen:

```bash
# Quelle
docker run --rm -v <app>_<vol>:/c alpine ls -lan /c | head -3
# Ziel
docker run --rm -v <app>_<vol>:/c alpine chown -R <uid>:<gid> /c
```

Gilt für jedes Volume, in das die Anwendung schreibt (Beat-Schedule, Medien,
Uploads) — nicht für reine Datenbank-Volumes, die der DB-Container selbst
initialisiert.

### Klasse 3 — nicht nebenbei

`trading-hub` ist der einzige gemessene Fall: `monitor_trades`,
`update_portfolio_pnl` und `ib_health_check` laufen **minütlich**, der Worker
meldet „checked 0 trades, closed 0" — die Aufgabe kann Positionen schließen. Im
Environment liegen Schlüssel für Alpaca, Binance, OANDA und Finnhub. Dazu
TimescaleDB mit 77 Chunks (eigenes Restore-Verfahren mit
`timescaledb_pre_restore()` / `post_restore()`) und ein beweglicher Image-Tag
`latest-pg16`, der auf dem Ziel eine andere Version ziehen kann.

Bedingungen, bevor diese App angefasst wird:

- **Wartungsfenster mit vollständigem Stillstand** — kein paralleles Hochfahren
- Vorher klären, ob die Broker-Schlüssel **IP-gebunden** sind; der Standortwechsel
  nach Helsinki ändert die ausgehende Adresse (Owner-Einschätzung 2026-08-04:
  vermutlich kein Whitelisting — **ungeprüfte Annahme**, vor dem Umzug in den
  Broker-Einstellungen verifizieren)
- Image per Digest pinnen statt per `latest`-Tag

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
