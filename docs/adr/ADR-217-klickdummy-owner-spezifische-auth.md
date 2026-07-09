---
id: ADR-217
title: "Klickdummy Owner-spezifische Auth (Phase 2 nach ADR-216)"
status: proposed
decision_date: 2026-05-21
deciders: [Achim Dehnert]
consulted: [self-advocatus-diabolus]
informed: [meiki-lra, bahn-sqf, ttz-lif, iilgmbh]
domains: [auth, klickdummy, infrastructure, security]
supersedes: []
amends: [ADR-216]
depends_on: [ADR-142, ADR-216]
related: [ADR-211, ADR-215]
tags: [klickdummy, auth, authentik, sso, owner-routing, traefik]
---

# ADR-217 — Klickdummy Owner-spezifische Auth (Phase 2)

## Status

**proposed** — mit pre-integriertem advocatus-diabolus-Review (gelernt aus
ADR-216-Erfahrung). Tritt in Kraft nach Pilot-Feedback Phase 1 (ADR-216
SSO-Initial). Empfohlene Aktivierung wenn der erste Stakeholder fragt:
„Ich will nur meine Klickdummies sehen."

## Kontext

`platform:ADR-216` etabliert Klickdummy-Hosting auf
`staging-klickdummy.iil.pet` mit Authentik-SSO (ADR-142) und einer
gemeinsamen Gruppe `klickdummy-viewers`. **Alle Stakeholder sehen alle
Klickdummies** — fachlich heute akzeptabel (DSFA 2026-05-21 nicht
kritisch), aber:

- Raphael Bayer (DB Regio) hat operativ nichts mit `meiki-lra`-Klickdummies zu tun
- Ilja Lerch + Grinninger (pg-hub Stab) hat keinen Bezug zu `ttz-lif`
- LRA-Stakeholder sehen Bahn-Lost-Units, die fachlich verwirren

Wenn künftige Klickdummies **echte Pilot-Daten** in Phase B/C
enthalten (siehe ADR-211 I3 Off-Ramp-Phasen), wird Owner-Trennung
zwingend.

### Trigger für diese ADR

User-Skizze aus ADR-216 §Authentifizierung Phase 2:

> „später owner-login..?"

## Entscheidungs-Vorschlag

**Path-Prefix-basierte Owner-Auth via Authentik-Groups + Traefik+nginx
Header-Map.** Konkret:

1. **Pro Org eine Authentik-Gruppe** (statt einer gemeinsamen
   `klickdummy-viewers`):
   - `klickdummy-sqf-viewers` — Zugriff auf `/bahn-sqf/sqf-hub/*`
   - `klickdummy-pg-viewers` — Zugriff auf `/bahn-sqf/pg-hub/*`
   - `klickdummy-ttz-viewers` — Zugriff auf `/ttz-lif/*`
   - `klickdummy-meiki-viewers` — Zugriff auf `/meiki-lra/*`
   - `klickdummy-admin` — Zugriff auf alle Pfade

2. **Eine Authentik-App** (`klickdummy`) bleibt — keine Splitting in
   4 Apps. Bindings sind Group-skopiert; Authentik liefert die Gruppen
   im `X-authentik-groups`-Header zurück.

3. **nginx-Map als Auth-Filter** (statt zusätzlicher Traefik-Middleware):

```nginx
# /etc/nginx/conf.d/owner-auth.conf
map "$request_uri $http_x_authentik_groups" $owner_authorized {
  default                                          0;
  "~^/bahn-sqf/sqf-hub/.* .*klickdummy-sqf-viewers"   1;
  "~^/bahn-sqf/pg-hub/.* .*klickdummy-pg-viewers"     1;
  "~^/ttz-lif/.* .*klickdummy-ttz-viewers"            1;
  "~^/meiki-lra/.* .*klickdummy-meiki-viewers"        1;
  "~ .*klickdummy-admin"                              1;
  # Discovery + Landing immer erlaubt
  "~^/api/list"                                        1;
  "~^/$"                                               1;
  "~^/robots.txt$"                                     1;
  "~^/healthz$"                                        1;
}

server {
  # … (aus ADR-216)

  location / {
    if ($owner_authorized = 0) {
      return 403 "Forbidden: kein Zugriff auf diesen Klickdummy-Pfad. Falls fehlerhaft, an Achim Dehnert melden.\n";
    }
    # bestehender autoindex + try_files
  }
}
```

4. **Landing-Page (`/`) gefiltert**: `generate_landing.py` rendert nur
   die für den User sichtbaren Klickdummies — basierend auf
   `X-authentik-groups`-Header. Klickdummies anderer Orgs erscheinen
   nicht in der Liste (kein Discovery-Leak).

## I1–I4 Auswirkung

- **I1 Spec-First**: keine Auswirkung (Auth-Layer ist orthogonal zur Spec)
- **I2 Prod-Sicherheit**: keine Auswirkung (Klickdummies bleiben `class: mock`)
- **I3 Off-Ramp**: kein Eingriff — Phase A bleibt
- **I4 Namensraum**: keine Auswirkung (ADR-Refs unverändert)

## DSGVO

- User-Identifikation via Authentik (E-Mail + Username): bereits unter ADR-142 abgedeckt
- Group-Membership ist nicht personenbezogen-sensibel (Funktionsrolle)
- Audit-Log via Authentik bleibt vollständig (welcher User wann auf welche Klickdummies)
- **Klassifikation**: nicht kritisch, identisch zu ADR-216 §DSGVO

## Advocatus-Diabolus-Review (pre-integriert)

### Pass 1: Architektur-Smells

| Smell | Ausgangs-Vorschlag | Behoben |
|---|---|---|
| nginx-Map mit Regex-Pattern ist Performance-anfällig | Komplexe `map`-Ausdrücke pro Request | OK: nginx-Map ist O(1) für Lookups, Regex nur 5-10 Patterns — vernachlässigbar |
| Authentik-Group-Header trauen → Spoof-Risiko | nginx vertraut auf `X-authentik-groups`-Header | **Mitigation**: nginx setzt diesen Header **nur** via Traefik-forwardAuth, nicht aus Client-Request. `proxy_set_header X-authentik-groups ""` als Initial-Cleanup vor forwardAuth. |
| Discovery-Endpoint `/api/list` ist unfiltered | alle User sehen alle Klickdummies in der Liste | **Fix**: `_index.json`-Generierung sieht User-Header **nicht** (statisch generiert). Alternative: serverseitige Render-Logik pro Request → server-side template (nginx kann das nicht ohne Modul) |
| Landing-Filter ist Cosmetic, nicht Security | wer URL kennt, kommt durch | **Phase-2-Trade-off**: explizit dokumentiert. Owner-Trennung ist UX-Komfort + Compliance-Audit-Trail, nicht harte Security gegen URL-Erraten |

### Pass 2: Out-of-the-box-Ideen

| Idee | Bewertung |
|---|---|
| **Sub-Domains pro Org** (`sqf.staging-klickdummy.iil.pet`, …) | ✅ Trade-off: 4× DNS+TLS-Cert, aber saubere Cookie-Domain-Trennung. Verworfen für Phase 2 (Komplexität), Kandidat für Phase 3 wenn Org-Branding gewünscht |
| **GitHub Org Membership als Auth-Quelle** | Stakeholder müssen GitHub-Konten haben (Raphael/LRA-Pilot evtl. nicht). Verworfen |
| **Magic-Link statt SSO** | Schöner UX für Externe (kein Passwort-Management), aber wir haben Authentik schon. Verworfen für Phase 2, ggf. als Add-on |
| **JWT mit Owner-Claim im Cookie** | Authentik liefert das Subset schon via `X-authentik-groups`. Kein Wert in eigener JWT-Schicht |
| **OPA (Open Policy Agent) als Auth-Decision** | Overkill für 4 Org-Gruppen mit Pfad-Mapping. Wertvoll bei >20 Policies |
| **Discovery-Endpoint pro User mit Auth-aware Templating** | nginx kann das nicht ohne Lua/njs. Alternative: ein kleiner FastAPI-Sidecar — Komplexitäts-Trade-off zu groß. Verworfen |
| **Authentik-Application-Bindings statt nginx-Map** | Authentik kann nativ Path-Pattern → Group filtern. **Saubererer Pfad als nginx-Map**, aber: Auth-Decision liegt dann komplett in Authentik (nginx muss nur trustForward) → mehr Authentik-Kompetenz nötig. Trade-off: nginx-Map ist transparent + low-trust; Authentik-Bindings sind „magical" + zentralisiert |

**Out-of-the-box-Empfehlung:** **Authentik-Application-Bindings als
primäre Entscheidung**, nginx-Map als Backup für Defense-in-Depth.

### Pass 3: Was-passiert-wenn

| Szenario | Verhalten |
|---|---|
| User in keiner `klickdummy-*-viewers`-Gruppe | Authentik blockiert vor nginx — Authentik-Outpost returned 403 |
| User in `sqf-viewers` ruft `/meiki-lra/...` auf | nginx-Map liefert 0, return 403. Audit-Log: failed access attempt. |
| User-Group-Change in Authentik | Session-Cookie cached alte Groups bis Session-Refresh (Standard: 24h) — User muss neu einloggen für sofortigen Effekt. **Trade-off-Doku in Phase-2-Operations-Anleitung** |
| Admin überschneidet Owner | `klickdummy-admin` matched alle Patterns → Admin sieht alles. Korrekt. |
| Klickdummy von neuer Org dazu (z.B. `iilgmbh/iil-klickdummy` als Klickdummy?) | Neue Gruppe + Map-Erweiterung nötig — manueller Schritt. Acceptable, geschieht selten |
| Group-Spoofing (Client setzt eigenen Header) | Initial-Cleanup `X-authentik-groups ""` vor forwardAuth verhindert |

### Pass 4: ADR-Konformität

- **ADR-142** (Authentik IdP): vollumfänglich genutzt, keine Erweiterung nötig
- **ADR-216** (Klickdummy-Hosting): erweitert um Group-Mapping, kein Bruch
- **ADR-212** (Traefik): nutzt bestehende Middleware-Chain, keine neue Klausel
- **ADR-211** (Klickdummy-Rahmen): I1–I4 unverändert
- **ADR-Threshold**: ADR-217 ist legitim (neuer Berechtigungsmodell-Entscheid, nicht reine Pattern-Folge)

## Bauauftrag

### Phase 1 (heute, ADR-217)

1. ✅ Diese ADR
2. ⏳ Authentik-Gruppen anlegen (4× `klickdummy-<org>-viewers` + 1× `klickdummy-admin`)
3. ⏳ Authentik-Application-Bindings mit Path-Patterns (Authentik-UI oder via Skript)
4. ⏳ User aus existierender `klickdummy-viewers`-Gruppe in Org-spezifische Gruppen migrieren
5. ⏳ `infra/klickdummy-host/nginx.conf` erweitern um Owner-Auth-Map
6. ⏳ `infra/klickdummy-host/generate_landing.py` erweitern um Owner-Filter (Phase 2 Cosmetic)
7. ⏳ Operations-Doc: „User in neue Gruppe schieben → 24h Session-TTL beachten"

### Phase 3 (Backlog, nicht in dieser ADR)

- **Sub-Domains pro Org** wenn Org-Branding wichtig wird
- **OPA-Integration** wenn Policy-Komplexität wächst (>20 Pattern)
- **Magic-Link für Externe** wenn Authentik-User-Mgmt zu schwer wird

## Konsequenzen

### Positiv

- **Saubere Owner-Trennung** ohne neue Service-Boundary
- **Cosmetic + Hard Security** kombiniert (Landing-Filter + nginx-Map)
- **Skaliert** mit neuen Orgs (eine Gruppe + Map-Zeile)
- **ADR-Stack konform**: nutzt 142+216+212 ohne Bruch

### Negativ

- **Authentik-Group-Management** wird pro Stakeholder manueller (statt 1 Gruppe → 4-5 Gruppen)
- **Session-TTL-Caveat** für Group-Changes (Standard 24h, in Authentik tunbar)
- **Map-Patterns** werden in einem File gepflegt — bei vielen Orgs einseitig
- **kein hartes Schutz gegen URL-Erraten** für Inhaber des gemeinsamen Authentik-Logins; aber: Discovery-Endpoint zeigt nichts, was nicht autorisiert ist

### Neutral

- **Discovery-Endpoint** kann optional Owner-aware werden (sieht User-Header). Initial bleibt er statisch (von Sync-Job generiert) — alle Klickdummies in `_index.json`, Landing-Render filtert client-side. Trade-off: Discovery-Leak vs. Server-Komplexität.

## Alternativen

1. **Sub-Domains pro Org** — saubere Trennung, aber 4× DNS+TLS+Authentik-App. Phase-3-Kandidat.
2. **Multiple Authentik-Apps** (statt 1 mit Bindings) — Mehraufwand für gleichen Effekt. Verworfen.
3. **Keine Owner-Trennung** (Status quo ADR-216) — OK für Phase 1, nicht skalierbar mit Pilot-Daten.
4. **External Auth-Proxy** (z. B. Caddy + caddy-security oder oauth2-proxy) — eigenes Service-Set neben Authentik. Komplexitäts-Trade-off zu groß.

## Provenance

- ADR-216 §Authentifizierung Phase 2 hat den Bedarf skizziert
- User-Auftrag 2026-05-21 Iter. 27: ADR-217 entwerfen + tief reviewen
- Pre-integrierter advocatus-diabolus-Review (Erfahrung aus ADR-216-Initial-Drift)
- ADR-Threshold-Policy: ADR-217 ist legitim (neuer Auth-Entscheid + Service-Boundary-Verschiebung, kein reine Pattern-Folge)

## Open Loops

1. **Wann aktivieren?** — nicht in dieser ADR. Trigger: erster Stakeholder fragt nach Owner-Trennung, oder erste Klickdummy mit Pilot-Daten geht auf staging.
2. **Authentik-Bindings vs. nginx-Map Default**: heute defensiv beide (Defense-in-Depth). Entscheidung welcher der Primary-Path ist, fällt nach erstem Pilot.
3. **Session-TTL für Group-Changes**: 24h Standard ist akzeptabel; falls nicht, in Authentik-Application-Settings auf 1h tunbar.
