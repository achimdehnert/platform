# Staging-Ingress-Migration — nginx → Traefik

**ADR-212** legt Traefik als Routing-**Zielarchitektur** für Klausel-3-Hostnames
(`staging-<system-slug>.iil.pet`) fest. Diese Tabelle trackt den Cutover-Status
pro Repo von Per-Repo-nginx auf zentralen Ingress.

- **Routing aktuell (nginx)** = Per-Repo-nginx-Config auf `staging-platform` (178.104.184.168)
- **Routing-Ziel (Traefik)** = Traefik-Labels in `docker-compose.staging.yml`

**Hinweis zu Begriffen:** Die Klauseln 1/2/3 aus ADR-212 beschreiben die
*Hostname-Form* (Domain mit/ohne Subdomain-Tenancy bzw. `*.iil.pet`), **nicht**
die Routing-Mechanik. Dieser Tracker betrifft nur die Routing-Mechanik der
Klausel-3-Hostnames. Klausel-1-Repos mit eigener Domain (z. B. risk-hub
`staging-demo.schutztat.de`) bleiben außerhalb des Traefik-Wildcards und
behalten Per-Repo-nginx.

Infrastruktur-Voraussetzung: Traefik-Stack läuft auf `staging-platform` ✅
(Issue #246)

---

## Status-Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 todo | Cutover auf Traefik nicht begonnen |
| 🟡 in-progress | Labels vorbereitet / PR offen |
| ✅ done | Traefik-aktiv, nginx-Config entfernt |
| ⏭ skip | Kein Staging-Traffic, Cutover nicht geplant |
| n/a | Klausel 1 (eigene Domain) — bleibt nginx, kein Traefik |

---

## Repo-Status

| Repo | Staging-Hostname | Ingress-Migration | Ingress-Issue |
|------|-----------------|-------------------|---------------|
| **dev-hub** | `staging-devhub.iil.pet` | 🟡 in-progress | [PR#56](https://github.com/achimdehnert/dev-hub/pull/56) |
| writing-hub | `staging-writing.iil.pet` | ✅ done (pilot) | — |
| bfagent | `staging-bfagent.iil.pet` | 🔴 todo | — |
| billing-hub | `staging-billing.iil.pet` | 🟡 in-progress | [PR#3](https://github.com/achimdehnert/billing-hub/pull/3) |
| coach-hub | `staging-coachhub.iil.pet` | 🟡 in-progress ⚠️ DNS | [PR#23](https://github.com/achimdehnert/coach-hub/pull/23) |
| cad-hub | `staging-cadhub.iil.pet` | ✅ done (pilot) | — |
| risk-hub | `staging-demo.schutztat.de` | n/a (Klausel 1, eigene Domain) | — |
| travel-beat | `staging-travelbeat.iil.pet` | 🔴 todo | — |
| pptx-hub | `staging-pptxhub.iil.pet` | 🟡 in-progress ⚠️ DNS | [PR#22](https://github.com/achimdehnert/pptx-hub/pull/22) |
| research-hub | `staging-researchhub.iil.pet` | 🔴 todo | — |
| sqf-hub | `staging-sqfhub.iil.pet` | 🔴 todo | — |
| tax-hub | `staging-taxhub.iil.pet` | 🔴 todo | — |
| trading-hub | `staging-tradinghub.iil.pet` | 🟡 in-progress ⚠️ DNS | [PR#4](https://github.com/achimdehnert/trading-hub/pull/4) |
| 137-hub | `staging-137hub.iil.pet` | 🔴 todo | — |
| wedding-hub | `staging-weddinghub.iil.pet` | 🔴 todo | — |
| recruiting-hub | `staging-recruitinghub.iil.pet` | 🔴 todo | — |
| dms-hub | `staging-dmshub.iil.pet` | 🔴 todo | — |
| bahn-hub | `staging-bahnhub.iil.pet` | 🔴 todo | — |

---

## Traefik-Stack Akzeptanz-Kriterien (Issue #246)

- [ ] `docker-compose.yml` deployt auf `staging-platform`
- [ ] Cloudflare DNS-Record `*-staging.iil.pet` → `178.104.184.168` (via bf-staging)
- [ ] Wildcard-Cert via DNS-01 ausgestellt (sichtbar in ACME-Storage)
- [ ] Smoke-Test: `staging-traefiktest.iil.pet` → HTTP 200
- [ ] Traefik-Dashboard intern erreichbar (BasicAuth)
- [ ] Pilot-Repo dev-hub dokumentiert (dieses Dokument)
- [ ] Runbook `docs/runbooks/traefik.md` vorhanden

---

## Nächster Schritt

**Phase Sonnet-1 abgeschlossen (2026-05-21)** — 5 PRs gepusht:
dev-hub, billing-hub, coach-hub, pptx-hub, trading-hub.

⚠️ DNS-CNAMEs für coach-hub, pptx-hub, trading-hub fehlen noch (Cloudflare-Token
abgelaufen — manuelle Erstellung nötig). Vor Merge der jeweiligen PRs anlegen:
- `staging-coachhub.iil.pet`
- `staging-pptxhub.iil.pet`
- `staging-tradinghub.iil.pet`

**Nach Merge der PRs:** Auf `staging-platform` jeweils `docker compose up -d` neu
starten + Nginx-vhost entfernen → Status auf ✅ setzen.
