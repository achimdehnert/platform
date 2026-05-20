# Staging-Ingress-Migration — Klausel 2 → Klausel 3

**ADR-212** legt Traefik als zentralen Ingress (Klausel 3) für alle
`staging-<slug>.iil.pet`-Hostnames fest. Diese Tabelle trackt den Cutover-Status
pro Repo.

- **Klausel 2** = per-Repo-nginx-Config auf `staging-platform` (178.104.184.168)
- **Klausel 3** = Traefik-Labels in `docker-compose.staging.yml`

Infrastruktur-Voraussetzung: Traefik-Stack läuft auf `staging-platform` ✅
(Issue #246)

---

## Status-Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 todo | Noch keine Klausel-3-Migration begonnen |
| 🟡 in-progress | Labels vorbereitet / PR offen |
| ✅ done | Klausel-3-aktiv, nginx-Config entfernt |
| ⏭ skip | Kein Staging-Traffic, Migration nicht geplant |

---

## Repo-Status

| Repo | Staging-Hostname | Ingress-Migration | Ingress-Issue |
|------|-----------------|-------------------|---------------|
| **dev-hub** | `staging-devhub.iil.pet` | 🟡 Pilot (nächstes Issue) | — |
| writing-hub | `staging-writing.iil.pet` | 🔴 todo | — |
| bfagent | `staging-bfagent.iil.pet` | 🔴 todo | — |
| billing-hub | `staging-billing.iil.pet` | 🔴 todo | — |
| coach-hub | `staging-coachhub.iil.pet` | 🔴 todo | — |
| cad-hub | `staging-cadhub.iil.pet` | 🔴 todo | — |
| risk-hub | `staging.schutztat.de` | 🔴 todo | — |
| travel-beat | `staging-travelbeat.iil.pet` | 🔴 todo | — |
| pptx-hub | `staging-pptxhub.iil.pet` | 🔴 todo | — |
| research-hub | `staging-researchhub.iil.pet` | 🔴 todo | — |
| sqf-hub | `staging-sqfhub.iil.pet` | 🔴 todo | — |
| tax-hub | `staging-taxhub.iil.pet` | 🔴 todo | — |
| trading-hub | `staging-tradinghub.iil.pet` | 🔴 todo | — |
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

**Pilot-Migration dev-hub** → eigenes Issue öffnen mit:
1. Traefik-Labels in `dev-hub/docker-compose.staging.yml` hinzufügen
2. `traefik_public` network einhängen
3. Staging deployen + Smoke-Test
4. Nginx-vhost entfernen
5. Dieses Dokument auf ✅ aktualisieren
