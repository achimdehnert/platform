---
parent: Decisions
nav_order: 198
title: "ADR-198: Staging Edge — Zweiter Cloudflare Tunnel + Single-Level Subdomain-Konvention"
status: accepted
decision_date: 2026-05-13
deciders: Achim Dehnert
consulted: Cascade AI
informed: []
amends:
  - ADR-102-cloudflare-dns-cdn-migration.md
  - ADR-157-staging-production-split-and-port-governance.md  # 2. Amendment nach Inline-Amendment 2026-04-16
related:
  - ADR-106-port-audit.md
  - ADR-021-unified-deployment-pattern.md
  - ADR-156-reliable-deployment-pipeline.md
  - ADR-164-port-strategy-conflict-free-dev-staging-prod.md
implementation_status: none
staleness_months: 6
last_reviewed: 2026-05-13
drift_check_paths:
  - infra/ports.yaml
  - infra/cloudflared-tunnels.yaml
---

# Staging Edge — Zweiter Cloudflare Tunnel + Single-Level Subdomain-Konvention

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - infra/ports.yaml
  - infra/cloudflared-tunnels.yaml
amends_check: ADR-102, ADR-157
-->

---

## 1. Context and Problem Statement

ADR-102 (Cloudflare DNS + CDN + Tunnel, 2026-03-06) etablierte einen **einzigen
Cloudflare Tunnel `bf-platform`** als Catch-all-Origin auf
`https://localhost:443` des Produktionsservers (88.198.191.108). Alle DNS-Records
sind CNAMEs auf `f758021c-…-1c14599a38e2.cfargotunnel.com`.

ADR-157 (3-Server Architecture, 2026-04-02 / Amendment 2026-04-16) etablierte
einen **dedizierten Staging-Server** (178.104.184.168, Hetzner CPX42) mit dem
Prinzip *gleiche Ports, verschiedene Server* und schrieb in §4.1 die
Staging-Domain-Konvention `staging.<app>.iil.pet` vor.

Beim Versuch, diese beiden ADRs zusammen umzusetzen, kollidieren zwei Constraints:

### 1.1 Constraint A — Cloudflare Universal SSL deckt nur 1 Subdomain-Level

Das in ADR-102 §5.9 verwendete kostenlose Edge-Cert (Cloudflare Universal SSL)
ist ein **2-SAN-Cert** pro Zone:

- `<zone>` (z.B. `iil.pet`) und
- `*.<zone>` (z.B. `*.iil.pet`)

Damit gilt: **Single-Label-Subdomains** (`writing.iil.pet`, `staging-writing.iil.pet`)
matchen den Wildcard. **Zwei-Label-Subdomains** (`a.b.iil.pet`, also auch
`staging.writing.iil.pet`) **matchen nicht**.

Daher schlägt jedes Cert für `staging.writing.iil.pet`, `staging.billing.iil.pet`,
`staging.research.iil.pet` fehl (alle drei wären 2-Label-Subdomains). Nur
Cloudflare Advanced Certificate Manager ($10/Monat pro Zone = $120/Jahr) oder
Cloudflare for SaaS könnten verschachtelte Wildcards (`*.*.iil.pet` oder
per-Hostname-Certs für 2-Label-Subdomains) ausstellen.

Die in ADR-157 §4.1 vorgeschriebene Konvention `staging.<app>.iil.pet` ist
damit auf dem Free-Tier **nicht umsetzbar**.

Für eigene TLDs (z.B. `schutztat.de`, `drifttales.com`) bleibt `staging.<domain>`
korrekt — dort ist `staging` selbst die erste Subdomain-Ebene und vom
Zone-Wildcard `*.schutztat.de` abgedeckt.

### 1.2 Constraint B — Der bestehende Tunnel zeigt ausschließlich auf Prod

Egal welcher Hostname auf den Tunnel `bf-platform` zeigt, der Traffic endet auf
`88.198.191.108`. Ein DNS-Eintrag `staging-writing.iil.pet` als CNAME auf
denselben Tunnel-Hostname würde Staging-Traffic an Prod-Nginx liefern.
ADR-157 §4.4 erwähnte zwar A-Records auf `88.99.38.75` (alter Dev Desktop),
liefert aber **kein Routing-Konzept für den realen Staging-Server hinter
Cloudflare**.

Mögliche Pfade ohne zweiten Tunnel — keiner davon sauber:
- A-Records ohne CF-Proxy würden die Origin-IP exponieren (verstößt gegen
  ADR-102 §6.1 — "Server-IP komplett versteckt").
- A-Records mit CF-Proxy umgehen den Tunnel, exponieren die IP im
  CF-Account und brauchen Origin-Cert-Pflege auf Staging.
- CNAME auf `bf-platform`-Tunnel liefert an die falsche Maschine.

### 1.3 Ist-Zustand vs. Soll-Zustand

| Aspekt | Ist (verifiziert 2026-05-13) | Soll (laut ADR-157) |
|--------|------------------------------|---------------------|
| Staging-Server | Existiert (178.104.184.168, CPX42) | Existiert |
| Staging-Container | **Teilweise auf Prod colocated** (siehe §1.4) | Auf 178.104.184.168 |
| Edge-Pfad zum dedizierten Staging-Server | **Fehlt komplett** — kein zweiter Tunnel, keine A-Records dokumentiert | Cloudflare → Staging |
| `staging.*` DNS-Konfiguration | Heterogen (Single-Tunnel via Prod) | Edge → Staging-Server |
| `infra/ports.yaml` Single-Level-Regel | Im Kommentar Z. 39-42 dokumentiert | — |
| ADR-157 §4.1 Konvention | Veraltet (`staging.<app>.iil.pet`) | Soll mit Cert-Realität in Einklang |

### 1.4 Verifizierter Pilot — risk-hub (Drift-Inventar)

ADR-157 §8 nennt `staging.schutztat.de` als deployten Pilot. Faktencheck am 2026-05-13:

| Quelle | Behauptung | Widerspruch zu `ports.yaml` (risk-hub = 8090)? |
|--------|-----------|-----------------------------------------------|
| `risk-hub/docker-compose.prod.yml:96` | Port 8090 | ✅ stimmt überein |
| `risk-hub/docker-compose.local.yml:71` | Port 8090 | ✅ stimmt überein |
| `risk-hub/docker-compose.staging.yml:95` | Port **8099** | ❌ Drift (8099 = tax-hub Prod-Port laut ports.yaml) |
| `risk-hub/docker/nginx/nginx-staging.conf:26,61` | `proxy_pass :8091` | ❌ Drift (8091 = **bfagent** Prod-Port laut ports.yaml) |
| `risk-hub/scripts/setup-server.sh:116` | `DNS: staging.schutztat.de → 88.198.191.108` (Prod-IP!) | ⚠️ widerspricht ADR-157 §8 |
| ADR-157 §8 Validation | `Alle staging.* DNS → 178.104.184.168` | ⚠️ widerspricht setup-server.sh |
| `infra/scripts/dns_staging_sync.py:2` | "DNS-Records auf **Dev Desktop** zeigen lassen" | ⚠️ veralteter Staging-Plan (vor 2026-04-16) |

Commit-History `46be407 feat(staging): … port 8099` zeigt: 8099 wurde absichtlich
gesetzt, später als Konflikt geflagt (ADR-157 §1.2), aber nie zurückkorrigiert.
Der Pilot-Eintrag in ADR-157 §8 ("erreichbar") ist mit hoher Wahrscheinlichkeit
ein **veralteter Status-Eintrag**.

**Implikation für dieses ADR:**

- Ohne SSH-Live-Check ist **nicht** beweisbar, welche App heute hinter
  `staging.schutztat.de` antwortet. Falls `nginx-staging.conf` aus diesem Repo
  auf Prod-Nginx deployt wurde, proxiert sie auf bfagent's Port — **latentes
  Wrong-Service-Risiko**, vor Phase-1-Pilot zu prüfen.
- Die DNS-Aussage in `setup-server.sh:116` (Prod-IP) deutet auf
  **Colocation auf Prod-Server**. Physische Trennung aus ADR-157 ist nicht
  umgesetzt.
- Der Migrationsschritt *"Staging-Container von Prod auf 178.104.184.168
  umziehen + Drift in compose/nginx/setup-server.sh bereinigen"* ist
  Voraussetzung und wird in §7 Phase 0 als Pflichtschritt geführt.

### 1.4.1 Multi-Tenant-Wildcard auf Custom-Domain (Pilot-spezifisch)

Pilot-Faktencheck zeigt zusätzlich, dass risk-hub **Multi-Tenancy per
Subdomain-Wildcard** betreibt:

- `risk-hub/docker/nginx/nginx-staging.conf:38` → `server_name *.staging.schutztat.de`
- `risk-hub/scripts/setup-server.sh:67` → `CSRF_TRUSTED_ORIGINS=https://*.staging.schutztat.de`
- `risk-hub/scripts/setup-server.sh:60` → `DJANGO_ALLOWED_HOSTS=staging.schutztat.de,.staging.schutztat.de`

`*.staging.schutztat.de` ist ein **2-Level-Wildcard auf eigener Domain**. CF
Universal SSL liefert für die Zone `schutztat.de` eine 2-SAN-Cert
(`schutztat.de` + `*.schutztat.de`) — der zweite Wildcard-Level wird **nicht**
abgedeckt. Tenant-URLs unter `<tenant>.staging.schutztat.de` würden mit dem
Free-Plan Cert-Errors produzieren. Lösungs­optionen siehe §4.1.1.

### 1.5 Ist-Zustand in `infra/ports.yaml`

Die Datei dokumentiert die Single-Level-Regel bereits in den Kommentar­zeilen
(Z. 39-42) und führt für `*.iil.pet`-Hubs konsistent `staging-<app>.iil.pet`
(z.B. `staging-writing.iil.pet`, `staging-billing.iil.pet`).
ADR-157 §4.1 dagegen schreibt noch `staging.<app>.iil.pet` vor — **ADR-Drift**.

---

## 2. Decision Drivers

- **D-01**: Staging-Edge MUSS auf Cloudflare Free Tier funktionieren (keine
  $10/Monat-Ausgabe pro Zone für Advanced Cert Manager).
- **D-02**: Staging-Origin-IP MUSS — analog zu Prod — versteckt bleiben.
- **D-03**: Die Konvention MUSS für `*.iil.pet`-Hubs UND eigene TLDs einheitlich
  beschreibbar sein.
- **D-04**: Onboarding eines neuen Hubs darf weiterhin in einem Schritt
  automatisierbar bleiben (ADR-157 §4.5).
- **D-05**: Staging-Edge-Komponenten teilen keine Failure-Domain mit Prod
  (Option A erfüllt dies vollständig, Option B teilweise — beide isolieren
  Traffic, aber Option B teilt das CF-Edge-Konfigurations-Surface)
- **D-06**: Eine einzige Quelle der Wahrheit (`ports.yaml`) bleibt verbindlich.

---

## 3. Considered Options

### Option A — Zweiter Cloudflare Tunnel `bf-staging` auf 178.104.184.168

`cloudflared` läuft als systemd-Service auch auf dem Staging-Server.
Eigene Tunnel-ID, eigene Credentials, eigene CNAMEs für `staging-*` / `staging.<domain>`.

- **Pro**: Symmetrisch zu Prod (gleiches Sicherheits- und Cert-Modell)
- **Pro**: Origin-IP weiterhin versteckt, WAF/DDoS/HSTS identisch zu Prod
- **Pro**: Free Tier reicht (Tunnel sind unlimited free)
- **Pro**: Tunnel-Ausfälle isoliert (Prod ↔ Staging entkoppelt)
- **Contra**: **Operationaler Doppelaufwand** — jedes `cloudflared`-CVE/Upgrade
  muss auf 2 Servern ausgerollt werden, 2 systemd-Units zu überwachen,
  Version-Drift zwischen Prod und Staging möglich
- **Contra**: Onboarding-Script kennt 2 Tunnel-IDs
- **Track-Record-Risiko**: ADR-102 §5.4 Task #25 ("Port 80/443 extern schliessen")
  ist seit 2+ Monaten als P2 offen — die Org-Historie zeigt, dass tunnel-bezogene
  Folgearbeit nicht zuverlässig geschlossen wird

### Option B — CF-Proxy mit A-Records auf Staging-Server

`staging-*.iil.pet` → A-Record `178.104.184.168` mit aktiviertem CF-Proxy (orange cloud).

- **Pro**: **Nur ein cloudflared-Daemon insgesamt zu monitoren** — keine
  Doppel-Ops bei Upgrades/CVE-Patches
- **Pro**: Etabliertes, gut dokumentiertes CF-Standardmuster
- **Pro**: Migration einfacher als Tunnel-Setup
- **Contra**: Origin-Cert-Pflege auf Staging-Nginx nötig (CF Origin Cert mit
  15 Jahren oder LE per certbot) — zusätzlicher Wartungspfad
- **Contra**: Versehentliches Toggeln auf "DNS only" (grey cloud) im CF-UI
  exponiert die Origin-IP sofort — schwer durch Policy verhinderbar
- **Contra**: Nginx auf Staging braucht IP-Allowlist für CF-Ranges (regelmäßiges
  Range-Update via cron oder ADR-102 §5.1 Pfad #7-Mechanismus)
- **Contra**: Origin-IP im CF-Dashboard / Audit-Log direkt sichtbar (bei Option A
  sieht CF nur die Tunnel-Origin, was den Leak-Vektor reduziert)

### Option C — Advanced Certificate Manager + nested Wildcards

CF ACM ($10/Monat pro Zone) erlaubt Certs für `*.*.iil.pet`, behält
`staging.<app>.iil.pet`-Konvention.

- **Pro**: Konvention aus ADR-157 §4.1 unverändert
- **Contra**: $10/Monat pro Zone × 9 Zones = **$90/Monat = ~$1080/Jahr** —
  verstößt gegen D-01
- **Contra**: Löst Routing-Problem (1.2) nicht

### Option D — Cloudflare for SaaS

Custom-Hostnames pro Tenant. Nicht passend für Plattform-internes Staging.

- **Contra**: Zweckentfremdet, hoher Setup-Aufwand, Kosten

---

## 4. Decision

**Option A — Zweiter Cloudflare Tunnel `bf-staging` auf dem Staging-Server,
kombiniert mit einer harmonisierten Single-Level-Subdomain-Konvention.**

Option B (CF-Proxy + A-Record) wurde verworfen, weil D-05 vollständige
Failure-Domain-Trennung verlangt und das DNS-Only-Toggle-Risiko (B Contra 2)
in Verbindung mit dem direkt sichtbaren Origin-IP-Leak im CF-Dashboard
(B Contra 4) Free-Tier-Konformität unter Realbedingungen nicht garantiert.
Der Single-Daemon-Pro von B (R-5) wiegt diese Kontras nicht auf.

```
                          ┌─────────────────────────────────┐
                          │  Cloudflare Edge (CDN, WAF, SSL)│
                          └────────┬───────────────┬────────┘
                                   │               │
   DNS:                            │               │
   <app>.iil.pet ──CNAME──► bf-platform        bf-staging ◄──CNAME── staging-<app>.iil.pet
   <domain>      ──CNAME──► bf-platform        bf-staging ◄──CNAME── staging.<domain>
                                   │               │
                                   ▼               ▼
                         ┌────────────────┐  ┌────────────────┐
                         │ Prod           │  │ Staging        │
                         │ 88.198.191.108 │  │ 178.104.184.168│
                         │ cloudflared +  │  │ cloudflared +  │
                         │ Nginx + Hubs   │  │ Nginx + Hubs   │
                         └────────────────┘  └────────────────┘
```

### 4.1 Staging-Domain-Konvention (überschreibt ADR-157 §4.1)

| Prod-Domain-Typ | Staging-Pattern | Beispiel | Cert |
|-----------------|-----------------|----------|------|
| `<app>.iil.pet` (Subdomain) | **`staging-<app>.iil.pet`** | `staging-writing.iil.pet` | CF Universal SSL (1 Level) |
| `iil.pet` (Apex, bfagent) | `staging.iil.pet` | `staging.iil.pet` | CF Universal SSL (1 Level) |
| Eigene Domain (Primary) | `staging.<domain>` | `staging.schutztat.de` | CF Universal SSL (Apex+1) |
| Alias-Domain | **kein Staging** | `schutztat.com` — nur Prod-Redirect | — |

**Begründung des Mustertyps `staging-<app>` mit Bindestrich für `*.iil.pet`:**
Der Bindestrich macht es zu einer Single-Level-Subdomain, was Cloudflare Universal
SSL abdeckt. `staging.<app>.iil.pet` wäre zweistufig und scheitert am Free-Tier-Cert.

**Apex-Sonderfall `iil.pet` (bfagent):** `staging.iil.pet` ist *ein* Subdomain-Level
unter dem Apex und damit von `*.iil.pet` Universal-SSL abgedeckt. Beim Tunnel-CNAME
gilt CF-eigenes CNAME-Flattening (Cloudflare verarbeitet CNAMEs auf Apex- *und*
Subdomain-Ebene transparent, keine RFC-1034-Verletzung). Beim Onboarding daher
einfach CNAME `staging.iil.pet` → bf-staging-Tunnel anlegen — kein Sondercode nötig.

### 4.1.1 Multi-Tenant-Wildcard im Staging

Hubs mit Subdomain-basierter Multi-Tenancy (heute: risk-hub, künftig: alle
Tenant-fähigen Hubs gemäß ADR-072/ADR-137) brauchen Wildcard-Certs
`*.staging.<domain>` bzw. `*.staging-<app>.iil.pet`. **Beide sind zweistufige
Wildcards**, die Universal SSL **nicht** abdeckt.

Lösungsstrategie:

| Domain-Typ | Wildcard-Bedarf | Empfehlung |
|------------|-----------------|------------|
| `*.staging.<custom-domain>` (z.B. risk-hub) | `*.staging.schutztat.de` | **CF Advanced Certificate Manager pro Zone, $10/Monat** — nur für tatsächlich tenant-fähige Hubs einschalten. Kosten je betroffenem Hub kalkulierbar. |
| `*.staging-<app>.iil.pet` | 2-Label-Wildcard | **Nicht erlaubt** (Konvention §4.1 unterstützt das nicht) — Tenant-Subdomains für `*.iil.pet`-Hubs MÜSSEN auf eine eigene Custom-Domain ausweichen, falls Tenant-DNS benötigt wird. |
| `<tenant>.staging-<app>.iil.pet` per-Hostname | sehr viele Certs | **Nicht praktikabel** — siehe Universal-SSL-Rate-Limits ADR-157 Q-02 |

Konsequenz für risk-hub-Pilot: `staging.schutztat.de` ist als App-Domain frei
erreichbar (Universal SSL deckt das). Für Tenant-URLs `<tenant>.staging.schutztat.de`
muss vor Phase-1-Pilot entschieden werden:

- **Option α**: ACM für Zone `schutztat.de` aktivieren ($10/Monat, deckt
  `*.staging.schutztat.de` per nested-Wildcard ab) → kleinste Änderung, läuft sofort.
- **Option β**: Path-basierte Tenancy im Staging (`staging.schutztat.de/<tenant>/`)
  → keine Cert-Kosten, aber bricht mit Prod-URL-Schema.
- **Option γ**: Tenant-Tests nur in Prod (Staging single-tenant) → günstig,
  reduziert Staging-Wert für Multi-Tenant-Features.

**Vorläufige Entscheidung**: Option α für Zonen mit Multi-Tenant-Staging-Bedarf.
Hub-spezifisch zu beschließen, Budget jährlich ≤ $240 (max 2 Zonen × $120/J).
Eintrag in `infra/cloudflared-tunnels.yaml` pro Zone: `acm_required: true`.

### 4.2 Routing-Architektur

| Element | Prod | Staging |
|---------|------|---------|
| Tunnel-Name | `bf-platform` | `bf-staging` |
| Tunnel-Origin | `https://localhost:443` (Nginx terminiert TLS lokal) | `http://localhost:80` (Nginx ohne TLS — passt zu Pilot-Realität, siehe Note) |
| Tunnel-Host | 88.198.191.108 | 178.104.184.168 |
| CF-Hostname-Pattern | `<app>.iil.pet`, `<domain>` | `staging-<app>.iil.pet`, `staging.<domain>` |
| Nginx-Routing | `server_name` | `server_name` (identisch) |
| Edge-Cert (Client ↔ CF) | CF Universal SSL | CF Universal SSL |
| Origin-TLS (CF ↔ cloudflared) | TLS mit `noTLSVerify: true` (Origin-Cert irrelevant) | **kein Origin-TLS** — Loopback HTTP, da Nginx auf :80 lauscht (siehe `risk-hub/docker/nginx/nginx-staging.conf:1 listen 80;`) |

**Note zur Tunnel-Origin-Wahl**: Der Pilot-Nginx (`nginx-staging.conf:1`) hört
auf Port 80 ohne TLS. Tunnel-Traffic zwischen cloudflared und Nginx auf
Loopback `127.0.0.1` ist unverschlüsselt unkritisch (kein Netzwerk-Sniffing).
Empfehlung: Staging bleibt auf `http://localhost:80`. Wer die Prod-Symmetrie
streng will, kann Staging-Nginx zusätzlich auf 443 mit Self-Signed-Cert
konfigurieren und `https://localhost:443 + noTLSVerify` nutzen — aber das
ist Overhead ohne Sicherheitsgewinn.

### 4.3 `cloudflared` auf Staging — Soll-Konfiguration

```yaml
# /root/.cloudflared/config.yml auf 178.104.184.168
tunnel: <bf-staging-id>
credentials-file: /root/.cloudflared/<bf-staging-id>.json
ingress:
  - service: http://localhost:80   # Nginx ohne TLS, routet per server_name
```

```
[Unit] cloudflared.service — systemd-Unit identisch zu ADR-102 §5.8
[Service] User=root, ExecStart=/usr/local/bin/cloudflared tunnel run
[Install] WantedBy=multi-user.target
```

### 4.4 `infra/ports.yaml` — keine Schema-Ergänzung nötig

Bewusste Entscheidung: **keine neuen Felder** `tunnel_prod` / `tunnel_staging`.
Das vorhandene `server`-Feld (prod | staging | dev) leitet den zuständigen Tunnel
eindeutig ab — ein Mapping `server → tunnel` gehört in `infra/cloudflared-tunnels.yaml`
(§4.5) und nicht in `ports.yaml`. Damit bleibt `ports.yaml` Single Source of Truth
für *Ports und Domains*, getrennt von Edge-Routing-Details.

### 4.5 Onboarding-Checkliste (ersetzt ADR-157 §4.5 Schritte 3-9)

Voraussetzung: `infra/cloudflared-tunnels.yaml` (neue Datei) hält die Tunnel-IDs
und Tunnel-Hostnames als Konstanten:

```yaml
# infra/cloudflared-tunnels.yaml
tunnels:
  bf-platform:
    id: f758021c-a475-4ab7-9c02-1c14599a38e2
    hostname: f758021c-a475-4ab7-9c02-1c14599a38e2.cfargotunnel.com
    server: prod   # 88.198.191.108
  bf-staging:
    id: <neu, nach `cloudflared tunnel create bf-staging`>
    hostname: <id>.cfargotunnel.com
    server: staging  # 178.104.184.168
```

Damit alle Onboarding-Scripts denselben Tunnel-Hostname referenzieren.

| # | Schritt | Detail |
|---|---------|--------|
| 1 | Port reservieren | `port_audit.py --next-free` → ports.yaml |
| 2 | `domain_prod` / `domain_staging` in ports.yaml | Konvention §4.1 dieses ADRs |
| 3 | DNS Prod | CNAME `<prod-host>` → `tunnels.bf-platform.hostname` |
| 4 | DNS Staging | CNAME `<staging-host>` → `tunnels.bf-staging.hostname` |
| 5 | DNS Alias-Domains | CNAME auf `bf-platform` (Prod) — kein Staging |
| 6 | SSL Prod | Universal SSL (automatisch durch CF, sofern Single-Level) |
| 7 | SSL Staging | Universal SSL (automatisch durch CF, sofern Single-Level) |
| 8 | Nginx Prod | `server_name <prod-host>` → Hub-Port |
| 9 | Nginx Staging | `server_name <staging-host>` → Hub-Port (gleiche Port-Nummer) |
| 10 | docker-compose.prod.yml | Port aus ports.yaml |
| 11 | Health | `/livez/` + `/healthz/` auf beiden Servern |
| 12 | Outline-Steckbrief | ADR-157 §4.5 Schritt 13 bleibt aktiv — Repo-Steckbrief mit allen Domains + Ports + Tunnel-Zuordnung pflegen |

DNS-Mutationen erfolgen über den Cloudflare-MCP-Server mit Write-Token
(ADR-102 §5.7), nicht über die CF-UI — damit reproduzierbar und auditbar.

### 4.6 Migration — Bestand korrigieren

| Aufgabe | Wo |
|---------|-----|
| Tunnel `bf-staging` einmalig erstellen (cloudflared tunnel create) | Staging-Server |
| systemd-Unit deployen | Staging-Server |
| Bestehende `staging.<app>.iil.pet`-DNS-Einträge entfernen / migrieren auf `staging-<app>.iil.pet` | Cloudflare |
| Alle `staging-*.iil.pet`-CNAMEs auf bf-staging-Tunnel umbiegen | Cloudflare |
| `staging.<custom-domain>` analog umbiegen | Cloudflare |
| Nginx-Configs auf Staging-Server für jeden Hub anlegen | 178.104.184.168 |
| ADR-157 §4.1 als überschrieben markieren | docs/adr |
| ADR-102 §5.6 um zweiten Tunnel ergänzen | docs/adr |

### 4.7 Secrets & Tunnel-Credential-Rotation

Unverändert gegenüber ADR-157 §4.7 — Staging-Secrets bleiben separate Werte.
Zusätzlich:

- `cloudflared`-Credentials für `bf-staging` liegen ausschließlich auf
  178.104.184.168 (`/root/.cloudflared/<id>.json`, root-only, chmod 600).
- **Rotation**: Credentials sind nicht zeitlich begrenzt, sind aber bei
  Server-Kompromittierung sofort zu rotieren. Verfahren:
  `cloudflared tunnel token <name>` erzeugt neue Credentials, `tunnel delete`
  alte ID, `tunnel route dns` neue CNAMEs. **CNAME-Hostname ändert sich
  bei Rotation** — entsprechend `infra/cloudflared-tunnels.yaml` updaten und
  DNS-Sync laufen lassen.
- **Cookie-Domain-Scope-Risiko**: Cookies mit `Domain=.iil.pet` würden zwischen
  `<app>.iil.pet` (Prod) und `staging-<app>.iil.pet` (Staging) leaken. Mitigation:
  Django `SESSION_COOKIE_DOMAIN` darf nicht auf `.iil.pet` gesetzt sein (Default
  = exakter Hostname ist sicher). **Confirmation in §7 Phase 2** (nicht
  Behauptung): `grep -r "SESSION_COOKIE_DOMAIN" ~/github/*/src/config/settings*.py
  ~/github/*/.env.staging` muss für alle Hubs leer bleiben oder einen exakten
  Hostnamen liefern — keine `.iil.pet`- oder andere zone-weite Werte.

---

## 5. Consequences

### 5.1 Positive

- **Symmetrisches Sicherheitsmodell** Prod ↔ Staging — Origin-IPs in beiden Fällen
  versteckt; WAF, DDoS, HSTS, TLS 1.2+ identisch.
- **Free Tier reicht** — keine Cert-Manager-Kosten.
- **Single Source of Truth bleibt** `infra/ports.yaml` (kein Schema-Bruch).
- **Entkoppelte Ausfälle** — Staging-Tunnel-Outage hat keinerlei Einfluss auf Prod.
- **Onboarding bleibt 1-Step** — nur ein zweiter CNAME pro neuem Hub.
- **ADR-Drift beseitigt** — ADR-157 §4.1 wird durch dieses ADR explizit korrigiert.

### 5.2 Negative

- **Zweiter cloudflared-Service** muss überwacht werden (systemd, Monitoring).
- **Onboarding-Skripte/Docs** müssen den zweiten Tunnel-Hostname kennen.
- **Namens-Bruch** für `*.iil.pet`-Staging-URLs, die intern noch unter
  `staging.<app>.iil.pet` referenziert sein könnten — siehe Migration §4.6.
- **Phase-0-Aufwand** für Container-Migration und Drift-Cleanup ist nicht trivial
  (geschätzt 2-3 Tage für alle aktuell colocated Staging-Hubs).
- **Optionale Recurring-Cost**: CF Advanced Certificate Manager wird pro
  Multi-Tenant-Zone benötigt (§4.1.1) — Budget ~$120-240/Jahr (max 2 Zonen,
  heute nur risk-hub). Komplett-Free-Tier ist nur möglich, wenn alle Hubs auf
  single-tenant Staging beschränkt bleiben.

### 5.2.1 Kostenvergleich über 12 Monate

| Option | Setup | Laufende Kosten | Op-Aufwand 12 Mo |
|--------|-------|-----------------|------------------|
| A (zweiter Tunnel) — **Empfohlen** | 1 Tag | $0 | ~2× Upgrades × 30 min = 1 h, plus Monitoring |
| B (CF-Proxy + A-Record) | 0.5 Tag | $0 | 1× Upgrade × 30 min, Cert-Renewal automatisiert |
| C (ACM für alle Zonen) | 0.5 Tag | ~$1080 (9 Zonen × $120) | minimal |
| A + ACM (Option α aus §4.1.1, nur Multi-Tenant-Zonen) | 1 Tag | ~$120-240 (max 2 Zonen) | wie A plus 0 |

**Begründung der Wahl A + ACM-Selective**: Cost-Sweet-Spot bei <$240/Jahr,
voll versteckter Origin, gleicher Operational-Footprint wie Option B + Multi-Tenant
funktionsfähig.

### 5.2.2 Operational Concerns (Coverage)

- **Observability**: Phase 1 enthält Uptime-Kuma-Monitor für `staging-writing.iil.pet`
  und einen Tunnel-Health-Check (`cloudflared tunnel info bf-staging | grep
  Connections`). Ohne dies sind Tunnel-Ausfälle nur durch Developer-Beschwerden
  sichtbar.
- **Failure-Mode bei `bf-staging`-Outage**: Cloudflare liefert "Web server is
  returning an unknown error" (Error 520/525) — kein Failover auf Prod (Q-02).
  Bewusste Entscheidung: keine cross-environment-Fallbacks, da das Prod-Daten-
  Leak-Risiko bei versehentlichem Failover zu hoch wäre. Stattdessen
  Maintenance-Page-Worker auf CF-Edge (Backlog §6 Q-02).
- **Rollback-Pfad**: Siehe §7 Phase 5 — bei Pilot-Tag-1-Fehlschlag müssen alte
  CNAMEs und nginx-Configs revertbar bleiben (kein hard-delete in Phase 1/2).

### 5.3 Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| R-01 cloudflared auf Staging crasht | Niedrig | Mittel (nur Staging down) | systemd Restart=always, 4 Connections Redundanz wie Prod |
| R-02 Tunnel-Credentials werden ausgecheckt | Niedrig | Hoch | `/root/.cloudflared/` chmod 600, nicht im Repo, ADR-045 |
| R-03 Universal SSL gibt Cert nicht aus (Edge-Case) | Sehr niedrig | Niedrig | Fallback auf CF Origin Cert; AlertManager auf Cert-Errors |
| R-04 Alte 2-Level-DNS-Einträge bleiben hängen (`staging.<app>.iil.pet`) | Mittel | Mittel — User sehen `NET::ERR_CERT_COMMON_NAME_INVALID` (Universal SSL liefert kein Cert für `*.*.iil.pet`), nicht 404 | Cert-SAN-Check als Pflicht-Schritt VOR Phase-2-DNS-Migration: `openssl s_client -servername <host>` für jeden Eintrag — IP-Audit allein (ADR-157 §5.4) reicht nicht, da es Cert-Validität nicht prüft |
| R-05 Multi-Tenant-Cert-Lücke (`*.staging.<custom>`) übersehen | Mittel | Hoch — Tenant-URLs für risk-hub-Staging unbenutzbar | §4.1.1 Entscheidung pro Hub VOR Phase-1-Pilot dokumentieren; ACM-Aktivierung als sichtbarer Schritt in Phase 1 für Multi-Tenant-Hubs |
| R-06 Wrong-Service-Routing aus §1.4 nicht aufgelöst | Mittel | Hoch — Staging zeigt fremde App | Phase 0 enthält SSH-Live-Check: `ssh hetzner-prod 'nginx -T 2>/dev/null \| grep -A5 staging.schutztat'` und `docker ps \| grep staging` — Klarheit BEVOR Tunnel-Setup |

### 5.4 Confirmation

Compliance dieses ADRs ist erreicht, wenn alle folgenden Checks grün sind:

1. `curl -sI https://staging-writing.iil.pet/livez | head -1` → 200 (über bf-staging-Tunnel)
2. `dig +short staging-writing.iil.pet` → nur Cloudflare-Anycast-IPs
3. `ssh hetzner-staging systemctl is-active cloudflared` → active
4. `cloudflared tunnel list` auf Staging → `bf-staging` mit ≥1 Connection
5. `grep -E "domain_staging:.*staging\.[^.]+\.[^.]+\.iil\.pet" infra/ports.yaml` → leer
   (Regex verlangt genau 2 Labels zwischen `staging.` und `.iil.pet`. Damit
   matched `staging.writing.iil.pet` als Verstoß, aber `staging.iil.pet`
   bei bfagent — 1-Label am Apex — NICHT, und ist damit erlaubt)
6. DNS-Audit-Script (analog ADR-157 §5.4): kein CNAME von `staging-*.iil.pet`
   zeigt auf `bf-platform`-Tunnel; **zusätzlich Cert-SAN-Check**:
   `for h in <staging-hosts>; do echo | openssl s_client -connect $h:443 \
    -servername $h 2>/dev/null | openssl x509 -noout -subject -ext subjectAltName; done`
   → jeder Hostname muss in einer ausgestellten SAN matchen
7. **`port_audit.py --inventory staging`** (NEU — Implementation in §7 Phase 3)
   muss grün sein: vergleicht `infra/ports.yaml` gegen
   `ssh hetzner-staging docker ps --format '{{.Names}} {{.Ports}}'`,
   identische Port-Nummern Prod/Staging, kein Drift in
   `*/docker-compose.staging.yml` und `*/nginx-staging.conf`
8. **Pro Hub** auf 178.104.184.168 existiert `docker ps`-Eintrag mit dem Port aus
   `ports.yaml` (kein Hub läuft mehr colocated auf Prod als Staging-Container)

---

## 6. Open Questions

| # | Frage | Status |
|---|-------|--------|
| Q-01 | `tunnel_prod` / `tunnel_staging` Felder in ports.yaml? | **Entschieden: Nein** — `server`-Feld reicht, Mapping `server → tunnel` lebt in `infra/cloudflared-tunnels.yaml` (§4.5) |
| Q-02 | Wartungsmodus bei Tunnel-Outage — eigene Cloudflare-Worker-Page nötig? | **Pre-Acceptance-Entscheidung getroffen**: Vorerst Default CF-Error-Seite (520/525); Worker-Page als Backlog für Q3 2026 |
| Q-03 | Monitoring von `cloudflared` (Uptime-Kuma vs CF Notifications)? | **Entschieden**: Uptime-Kuma als Single-Source — überwacht Tunnel-Health über `staging-<pilot>.iil.pet/livez/`. CF Notifications nur als Backup. Setup in §7 Phase 1. |
| Q-04 | Sollen Alias-Domains zukünftig auch Staging bekommen? | Nein — Aliase sind reine Prod-Redirects, kein eigener App-Code, daher kein Testbedarf in Staging |
| Q-05 | Welche Hubs laufen heute als Staging-Container colocated auf Prod (statt 178.104.184.168)? | Offen — Bestandsaufnahme in Phase 0 §7 |
| Q-06 | Wie weit verbreitet ist Multi-Tenant-Wildcard-Bedarf außerhalb risk-hub? | Offen — Audit in Phase 0 (`grep -r "TENANT_BASE_DOMAIN\|\\*\\.staging" ~/github/`) |

---

## 7. Implementation Plan

| Phase | Task | Status | Target |
|-------|------|--------|--------|
| **0** | **Bestandsaufnahme** — auf Prod-Server (88.198.191.108) alle Container mit `staging`-Suffix auflisten: `ssh hetzner-prod docker ps --format '{{.Names}}' \| grep -i staging` | ☐ | Sofort |
| **0** | **DNS-Inventar** — alle `staging.*` und `staging-*` CF-Records dokumentieren (Ziel-Tunnel, Cert-Status), inkl. eventuell vorhandener 2-Level-Records `staging.<app>.iil.pet` (Cert-Risiko) | ☐ | Sofort |
| **0** | **Port-Drift-Cleanup** in risk-hub (nginx-staging.conf=8091, compose.staging.yml=8099, ports.yaml=8090 angleichen auf 8090) | ☐ | Sofort |
| **0** | **Container-Migration** — alle bisher colocated auf Prod laufenden Staging-Container auf 178.104.184.168 umziehen (compose pull + up dort, dann auf Prod down) | ☐ | Woche 1 |
| **0** | **Multi-Tenant-Audit** (Q-06): `grep -r "TENANT_BASE_DOMAIN\\\|\\*\\.staging" ~/github/` über alle Hubs — ACM-Bedarf pro Zone ermitteln, in `infra/cloudflared-tunnels.yaml` als `acm_required: true` pro Zone hinterlegen | ☐ | Sofort |
| 1 | Tunnel `bf-staging` auf 178.104.184.168 erstellen, systemd-Unit deployen | ☐ | Woche 1 |
| 1 | cloudflared-Config + Credentials nach `/root/.cloudflared/` | ☐ | Woche 1 |
| 1 | `infra/cloudflared-tunnels.yaml` mit beiden Tunnel-IDs anlegen (§4.5) | ☐ | Woche 1 |
| 1 | Pilot: `staging-writing.iil.pet` CNAME → bf-staging-Tunnel, Nginx, Smoke-Test | ☐ | Woche 2 |
| 2 | DNS-Migration aller bestehenden `staging-*.iil.pet` auf bf-staging | ☐ | Woche 2 |
| 2 | `staging.<custom-domain>` CNAMEs auf bf-staging umbiegen | ☐ | Woche 2 |
| 3 | Onboarding-Workflow (ADR-157 §4.5) aktualisieren — Schritte 3/4 | ☐ | Woche 3 |
| 3 | DNS-Audit-Script erweitern: Staging-Records müssen auf bf-staging zeigen | ☐ | Woche 3 |
| 3 | `port_audit.py --inventory staging` Subkommando (Confirmation #7) | ☐ | Woche 3 |
| 4 | ADR-157 §4.1 mit Verweis auf ADR-198 markieren | ☐ | Mit Acceptance |
| 4 | ADR-102 §5.6 um zweiten Tunnel ergänzen | ☐ | Mit Acceptance |
| **5** | **Rollback-Plan dokumentiert** — bei Pilot-Tag-1-Fehlschlag (Phase 1 Smoke-Test schlägt fehl): alte `staging.*` CNAMEs nicht löschen (Soft-Switch mit niedrigem TTL=60s, Revert binnen 5 Min), Phase-0-Drift-Cleanup-Commits revertbar | ☐ | Phase 1 |
| 5 | **Cookie-Scope-Check** — `.env.staging` jedes Hubs: `SESSION_COOKIE_DOMAIN` darf nicht `.iil.pet` sein (siehe §4.7) | ☐ | Phase 2 |
| 5 | **Uptime-Kuma-Monitor** für `bf-staging`-Tunnel über Pilot-Host `staging-writing.iil.pet/livez/` | ☐ | Phase 1 |

---

## 8. Validation

- [ ] Phase-0-Inventar erstellt: bekannt, welche Staging-Container heute auf Prod colocated sind
- [ ] Port-Drift in risk-hub bereinigt (8091/8099 → 8090 in nginx-staging.conf + compose.staging.yml)
- [ ] Alle bisher colocated Staging-Container auf 178.104.184.168 umgezogen
- [ ] `bf-staging`-Tunnel läuft mit ≥1 Connection
- [ ] `infra/cloudflared-tunnels.yaml` existiert mit beiden IDs
- [ ] Mindestens 1 Hub (writing-hub als Pilot) über `staging-writing.iil.pet` erreichbar
- [ ] Origin-IP 178.104.184.168 in keiner DNS-Antwort sichtbar
- [ ] Alle `staging-*.iil.pet` CNAMEs zeigen auf `bf-staging`
- [ ] `port_audit.py --inventory staging` grün
- [ ] Onboarding-Workflow erfolgreich für 1 neuen Hub angewendet
- [ ] DNS-Audit grün (keine 2-Level-`staging.<app>.iil.pet` mehr im Bestand)

---

## 9. More Information

- **ADR-102**: Cloudflare DNS + CDN + Tunnel — Single-Tunnel-Architektur (wird durch dieses ADR ergänzt)
- **ADR-157**: 3-Server Architecture — §4.1 Staging-Domain-Konvention wird durch §4.1 dieses ADRs ersetzt
- **ADR-164**: Unified Port Strategy — `dev = staging = prod` Port (unverändert)
- **ADR-045**: Secrets Management — Tunnel-Credentials als Server-lokale Datei
- **infra/ports.yaml** — Kommentar-Regel Z. 39-42 bestätigt diese Entscheidung
- **Cloudflare Universal SSL Scope**: https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/
- **Cloudflare Tunnel Multi-Origin Limit**: Ein cloudflared-Daemon pro Origin-Server

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-05-13 | Achim Dehnert + Cascade | Initial — Proposed |
| 2026-05-13 | Achim Dehnert + Cascade | Review-Findings F-1 … F-9 eingearbeitet: Ist/Soll-Trennung in §1.3-1.5 (Pilot risk-hub verifiziert, Port-Drift dokumentiert), Option B Contras ehrlich, Edge-Cert/Origin-TLS-Spalten präzisiert, Apex-CNAME-Flattening, ports.yaml-Schema bewusst nicht erweitert, `infra/cloudflared-tunnels.yaml` als Konstanten-Datei, R-04 Cert-Error-Realität, Phase-0 mit Bestandsaufnahme + Container-Migration |
| 2026-05-13 | Achim Dehnert + Cascade | Out-of-the-Box Review Findings R-1 … R-10 + Coverage-Lücken eingearbeitet: §1.1 SSL-Cert-Scope präzise (2-SAN-Cert-Erklärung), §1.4 als Drift-Inventar mit Quell-Belegen, neuer §1.4.1 Multi-Tenant-Wildcard, neuer §4.1.1 mit ACM-Selective-Strategie, §4.2 Origin-TLS spiegelt Pilot-Realität (HTTP statt HTTPS), Option A Contras um Doppel-Ops + Track-Record erweitert, Option B Pro "single daemon" ergänzt, neue Risiken R-05/R-06, §4.7 Tunnel-Credential-Rotation + Cookie-Scope, §5.2.1 12-Mo-Kostenvergleich, §5.2.2 Operational Concerns (Observability/Failure-Mode/Rollback), Q-02/Q-03 entschieden, Q-06 Multi-Tenant-Audit, §7 Phase 5 mit Rollback + Cookie-Scope-Check + Uptime-Kuma |
| 2026-05-13 | Achim Dehnert + Cascade | Out-of-the-Box Review v2 Findings (3 Substantial + 5 Nits) eingearbeitet: §4 rebutiert Option B explizit, §1.1 Beispiele auf real failing Domains (writing/billing/research), §3 Option C Kosten als Jahres-Summe ($1080/J), §5.4 Confirmation #5 Regex auf 2-Label-Match verschärft, §5.2 ACM-Recurring-Cost-Bullet, drift_check_paths auf `infra/cloudflared-tunnels.yaml`, §4.7 Cookie-Scope als Phase-2-Confirmation reframet, §7 Multi-Tenant-Audit nach Phase 0 verschoben (war Phase/Target-Mismatch). **Status: accepted** |
