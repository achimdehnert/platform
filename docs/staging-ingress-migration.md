# Staging-Ingress-Migration — Tracker

Lebendes Dokument zum inkrementellen Übergang von Per-Repo-nginx auf einen
zentralen Ingress (Traefik) für Klausel-3-Hostnames `*-staging.iil.pet`.

**Architektur-Entscheidung:** [ADR-212](adr/ADR-212-staging-hostname-konvention.md)
(Klausel 3, „Routing-Zielarchitektur" + Advocatus-Diaboli Kritik 6).

**Scope:** Nur Klausel-3-Repos (iil.pet-Subdomains). Klauseln 1/2
(Domain-Repos wie `staging-demo.schutztat.de`) bleiben **außerhalb** des
Wildcards und behalten Per-Repo-nginx-Vhost.

## Vorgehen

1. **Hostname-Migration zuerst** — Suffix → Präfix gemäß Klausel 3
   (z. B. `billing-staging.iil.pet` → `staging-billing.iil.pet`).
   Per-Repo-nginx, 90-Tage-301-Redirect von alt nach neu, Cert-SAN,
   Authentik-Redirect-URI.
2. **Ingress-Migration danach** — pro Repo separat:
   1. Repo bekommt Traefik-Labels in `docker-compose.prod.yml`.
   2. Cert-Cutover auf das Wildcard `*-staging.iil.pet` (DNS-01).
   3. nginx-Vhost für den Hostname wird entfernt.
   4. Smoke-Test auf den Staging-Hostname (HTTP 200 + OIDC-Roundtrip).

**Reihenfolge-Empfehlung:** `dev-hub` als Pilot (bereits Klausel-3-konform,
kein Hostname-Bruch). Danach die 4 Suffix-Apps in Reihenfolge des
Schmerzlevels.

## Voraussetzungen (Ingress-Stack, einmalig)

- Traefik-Container auf `88.198.191.108`, Port 443 + 80.
- Wildcard-Cert `*-staging.iil.pet` via Let's Encrypt DNS-01
  (Cloudflare-Token vorhanden).
- Cloudflare-Origin-Rule, die `*-staging.iil.pet` auf Traefik leitet.
- Docker-Network `traefik_public`, in das jede ingress-migrierte App
  joint.
- Health-Check + Restart-Policy für Traefik (SPOF-Mitigation).

Ein separates Implementierungs-Ticket trackt diesen Stack-Aufsatz; bis
dahin ist die Spalte „Ingress-Migration" für alle Repos `🔴 todo`.

## Status

**Legende:** 🔴 todo · 🟡 in-progress · ✅ done · n/a (nicht anwendbar)

| Repo | Heutiger Hostname | Ziel-Hostname (Klausel 3) | Hostname-Migration | Ingress-Migration | Notizen |
|---|---|---|---|---|---|
| dev-hub | `staging-devhub.iil.pet` | unverändert | ✅ done | 🔴 todo | Pilot-Kandidat — kein Hostname-Bruch, ideal zum Lernen |
| billing-hub | `billing-staging.iil.pet` | `staging-billing.iil.pet` | 🔴 todo | 🔴 todo | Reihenfolge: erst Hostname, dann Ingress |
| coach-hub | `learn-staging.iil.pet` | `staging-learn.iil.pet` | 🔴 todo | 🔴 todo | system-slug `learn`, nicht `coach-hub` |
| wedding-hub | `wedding-staging.iil.pet` | `staging-wedding.iil.pet` | 🔴 todo | 🔴 todo | |
| weltenhub | `welten-staging.iil.pet` | `staging-welten.iil.pet` | 🔴 todo | 🔴 todo | |
| risk-hub | `staging.schutztat.de` (+ `staging-riskhub.iil.pet`) | `staging-demo.schutztat.de` | 🔴 todo | n/a | Klausel 1 — bleibt Per-Repo-nginx (eigene Domain) |

## Pflege

- Status-Wechsel: PR gegen `main`, der diese Tabelle aktualisiert
  **gleichzeitig** mit dem ausführenden Repo-PR (oder direkt danach).
- Bei „Ingress-Migration done": nginx-Vhost im
  `infrastructure/nginx/`-Repo (sofern existent) gleichzeitig entfernen,
  damit kein Schatten-Vhost stehenbleibt.
- Wenn ein neuer Klausel-3-Hostname entsteht (neues Repo): hier eintragen
  mit `Hostname-Migration: ✅ done` (greenfield-Klausel-3) und
  `Ingress-Migration: 🔴 todo` oder direkt `✅ done`, falls Ingress-Stack
  steht.
