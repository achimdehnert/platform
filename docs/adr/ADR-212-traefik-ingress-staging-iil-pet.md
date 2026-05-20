---
id: ADR-212
title: Zentraler Traefik-Ingress für staging-*.iil.pet (Klausel-3-Routing)
status: accepted
date: 2026-05-20
deciders: [Achim Dehnert]
consulted: [cascade-advocatus-diabolus]
informed: [all-repos]
domains: [infrastructure, deployment, ingress, tls]
supersedes: []
amends: [ADR-198, ADR-210]
depends_on: [ADR-045, ADR-102, ADR-198, ADR-205, ADR-210]
tags: [traefik, staging, ingress, wildcard-cert, dns-01, docker-labels, letsencrypt]
scope:
  include_paths:
    - "infra/traefik/"
    - "infra/cloudflared-tunnels.yaml"
    - "docs/staging-ingress-migration.md"
drift_check_paths:
  - "infra/traefik/docker-compose.yml"
  - "docs/staging-ingress-migration.md"
---

# ADR-212 — Zentraler Traefik-Ingress für `staging-*.iil.pet`

## Kontext

ADR-198 etablierte den zweiten Cloudflare-Tunnel `bf-staging` (2a517762-…) auf
`178.104.184.168` als Edge-Routing-Schicht für alle `staging-<slug>.iil.pet`-
Hostnames. ADR-210 kodifizierte das dreistufige Hosting-Modell (local / staging / prod)
mit `staging-platform` (178.104.184.168) als dediziertem Staging-Host.

### Problem

Die aus ADR-198/210 resultierende **per-Repo-nginx-Architektur** erzeugt bei 22+
Staging-Hubs erheblichen Wartungsaufwand:

- Jeder Hub braucht eine eigene nginx-vhost-Config auf `staging-platform`.
- TLS wird über Cloudflare Universal SSL an der Edge erledigt — origin-seitig kein
  Cert benötigt. Das Modell funktioniert, ist aber opak: kein Gesamt-Überblick,
  kein zentrales Routing-Dashboard, keine einheitliche Health-Signal-Quelle.
- Das Hinzufügen eines neuen Staging-Hubs erfordert manuelle SSH-Schritte auf
  `staging-platform` (nginx-Config anlegen, reload), was Automatisierung behindert.
- Per-Repo-nginx-Configs driften vom SSoT `registry/repos.yaml` ab — genau das
  Muster, das ADR-210 durch Generated-Artifacts lösen wollte, aber für nginx-Configs
  bisher nur auf der Renderer-Ebene abgefangen wird.

### Lösungsalternative: Traefik als zentraler Ingress

Traefik liest Docker-Labels direkt aus laufenden Containern und generiert seine
Routing-Regeln dynamisch. Kein nginx-Config-Management pro Hub — ein neuer
Staging-Container mit den richtigen Labels routet automatisch.

---

## Drei Routing-Klauseln (Terminologie für dieses ADR)

Um Routing-Entscheidungen klarer zu referenzieren, benennt dieses ADR drei
**Klauseln** für die `iil.pet`-Staging-Hostnamen:

| Klausel | Pattern | Edge-Tunnel | Origin-Ingress | Status |
|---------|---------|-------------|----------------|--------|
| **1** | `<slug>.iil.pet` (Prod) | `bf-platform` | nginx auf 88.198.191.108 | Bestehend, unverändert |
| **2** | `staging-<slug>.iil.pet` → per-Repo-nginx | `bf-staging` | nginx-vhost auf 178.104.184.168 | **Grandfathered** — bleibt bis Cutover |
| **3** | `staging-<slug>.iil.pet` → Traefik-Labels | `bf-staging` | Traefik auf 178.104.184.168 | **Ziel dieser ADR** |

**Klausel 3 ist das Routing-Ziel.** Per-Repo-Klausel-2-Configs bleiben erlaubt,
bis der jeweilige Hub auf Klausel 3 migriert ist. Migration wird pro Hub in
`docs/staging-ingress-migration.md` getrackt.

---

## Entscheidung

**Traefik v3 als zentraler Ingress-Controller auf `178.104.184.168`**, der über
das Docker-Network `traefik_public` alle Klausel-3-Staging-Container via
Compose-Labels routet.

```
                 Cloudflare Edge
                      │
          CNAME staging-<slug>.iil.pet
                      │
              bf-staging Tunnel
                      │
           178.104.184.168:80 (HTTP, Loopback)
                      │
              ┌───────────────┐
              │   Traefik v3  │  ← docker-compose.yml
              │  (Port 80+443)│    infra/traefik/
              └──────┬────────┘
                     │  traefik_public network
              ┌──────┴────────┐
              │               │
     dev-hub_staging_*  writing-hub_staging_*  …
     (labels: traefik.*)
```

### Kernkomponenten

1. **Traefik v3** — Docker-Provider, liest Labels aus laufenden Containern.
2. **ACME DNS-01 via Cloudflare** — Wildcard-Cert `*-staging.iil.pet` wird
   von Traefik selbst geholt und erneuert (`CF_DNS_API_TOKEN` als Secret).
3. **Docker-Network `traefik_public`** — alle Klausel-3-Apps hängen daran,
   Traefik routet per `Host()` Rule.
4. **BasicAuth-Dashboard** — intern zugänglich (`traefik.iil.pet` oder per
   SSH-Tunnel), nicht öffentlich exponiert.
5. **restart: always + Healthcheck** — SPOF-Mitigation; wenn Traefik fällt,
   sind alle Klausel-3-Staging-Apps weg.

### TLS-Strategie

**Klausel 3 verwendet Traefik ACME (Let's Encrypt DNS-01)**, nicht Cloudflare
Universal SSL als primäres Cert:

| Schicht | Cert | Begründung |
|---------|------|------------|
| CF Edge → cf_client | CF Universal SSL | Unverändert — CF terminiert TLS für externe Clients |
| bf-staging Tunnel → 178.104.184.168 | **kein** Origin-Cert (HTTP Loopback) | ADR-198 §4.2 — origin-seitiges TLS auf Loopback ohne Mehrwert |
| Traefik intern | LE Wildcard `*-staging.iil.pet` via DNS-01 | Für HTTPS-Health-Checks und Dashboard; optional aber bereit |

Das LE-Wildcard-Cert dient primär dem Traefik-Dashboard (HTTPS) und als
Fallback, falls ein Hub Traefik direkt via HTTPS answorten muss. Das Staging-
Traffic-Hauptpfad bleibt CF-Edge-terminated + HTTP-Loopback.

### Warum Traefik statt Nginx?

| Kriterium | Nginx (Klausel 2) | Traefik (Klausel 3) |
|-----------|-------------------|---------------------|
| Neue Route hinzufügen | SSH + vhost-Config + reload | Nur `traefik.*`-Labels im compose.yml |
| Routing-Übersicht | `nginx -T` auf Server | Traefik Dashboard |
| Drift-Risiko | hoch (Config-Datei ↔ Registry) | niedrig (Labels im SSoT compose.yml) |
| LE-Wildcard einmalig | manuelle certbot-Integration | eingebaut (ACME-Provider) |
| Hot-Reload | `nginx reload` (Downtime < 1s) | automatisch (Label-Watcher) |

### Warum kein Caddy?

Caddy wäre ebenfalls eine valide Wahl. Traefik bevorzugt wegen:
- Docker-Provider ist in der Org bereits bekannt.
- Dashboard für sofortigen Routing-Überblick ohne Extra-Tool.
- Label-Syntax ist established in der Community.

---

## Akzeptanz-Kriterien (Klausel 3 "live")

- [ ] `infra/traefik/docker-compose.yml` auf `178.104.184.168` deployed
- [ ] Traefik-Container läuft mit `restart: always`
- [ ] Wildcard-Cert `*-staging.iil.pet` via DNS-01 ausgestellt (ACME-Storage)
- [ ] Smoke-Test: `staging-traefiktest.iil.pet` → Traefik whoami-Container → HTTP 200
- [ ] Traefik-Dashboard intern erreichbar (BasicAuth), nicht öffentlich
- [ ] Pilot-Migration `dev-hub` dokumentiert in `docs/staging-ingress-migration.md`
- [ ] Runbook `docs/runbooks/traefik.md` vorhanden

---

## Migration (Klausel 2 → Klausel 3 pro Hub)

Jeder Hub migriert einzeln; beide Klauseln koexistieren während der Übergangszeit.

```
Klausel-2-Hub (nginx-Config auf staging-platform):
1. traefik_public network in compose.staging.yml einhängen
2. Traefik-Labels hinzufügen (Host-Rule, Port, TLS)
3. nginx-vhost für diesen Hub aus /etc/nginx/sites-available/ entfernen
4. nginx reload
5. Smoke-Test: curl -sI https://staging-<slug>.iil.pet/livez/ → 200
6. staging-ingress-migration.md: status auf ✅ setzen
```

Pilot: **dev-hub** (erstes Repo ohne produktiven Staging-Traffic).

---

## Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| R-1: Traefik fällt = alle Klausel-3-Hubs down | Niedrig | Hoch | restart: always; Runbook; Uptime-Kuma-Monitor auf Traefik-Health |
| R-2: ACME-Rate-Limit bei Wildcard-Cert | Sehr niedrig | Mittel | Wildcard = eine Anfrage deckt alle Klausel-3-Hubs; Staging-Wildcard < 5 Certs/Woche |
| R-3: CF-Token-Scope zu weit | Niedrig | Hoch | Token auf Zone:DNS:Edit für `iil.pet` beschränken; Token-Scope verifizieren (ADR-205 TODO) |
| R-4: Label-Drift wenn compose.staging.yml hand-edited | Mittel | Niedrig | ADR-210 Renderer prüft drift; render-staging pre-commit hook fängt es |
| R-5: Dashboard unbeabsichtigt öffentlich | Niedrig | Mittel | Entrypoint `dashboard` ohne Port-Binding nach außen; nur über SSH-Tunnel oder private IP |

---

## Alternativen verworfen

### Per-Hub-nginx (Klausel 2 als Dauerlösung)
Verworfen wegen Wartungsaufwand bei >10 Hubs und fehlendem zentralen Überblick.

### Nginx Ingress (ohne Docker-Labels)
Würde dasselbe Config-Management-Problem wie Klausel 2 reproduzieren.

### Istio / Kubernetes-Ingress
Over-Engineering für Single-Node-Staging; kein K8s auf staging-platform.

---

## Consequences

### Positiv
- Neue Klausel-3-Hubs werden durch Compose-Labels konfiguriert — kein SSH.
- Zentrales Dashboard für alle Staging-Routes.
- LE-Wildcard einmalig, auto-erneuert — kein certbot-Monitoring nötig.
- Drift zwischen Routes und Registry strukturell minimiert.

### Negativ
- SPOF: Traefik-Ausfall trifft alle Klausel-3-Hubs gleichzeitig.
- Migrations-Aufwand pro Hub: ~20 min (Labels + nginx-Config entfernen).
- Zusätzliches Tooling zu verstehen (Traefik-Labels, ACME-Config).

---

## Implementation

Tracks: `achimdehnert/platform#246`

Runbook: `docs/runbooks/traefik.md`
Tracker: `docs/staging-ingress-migration.md`

---

## References

- ADR-045 — Secrets Management
- ADR-102 — Cloudflare DNS + CDN + Tunnel
- ADR-198 — Zweiter Cloudflare-Tunnel (`bf-staging`)
- ADR-205 — TLS-Termination & Cert-Strategie auf prod
- ADR-210 — Local/Staging/Prod Architecture

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-05-20 | Achim Dehnert + Cascade | Initial — accepted |
