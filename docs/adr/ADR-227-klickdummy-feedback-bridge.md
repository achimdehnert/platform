---
id: ADR-227
title: "Klickdummy-Feedback-Bridge (Pfad B): CF-Worker statt User-PAT"
status: draft
decision_date: 2026-05-29
deciders: [Achim Dehnert]
consulted: []
informed: [iilgmbh, meiki-lra, bahn-sqf, ttz-lif]
domains: [klickdummy, feedback, cloudflare, security, ci]
supersedes: []
amends: [ADR-211]
depends_on: [ADR-216]
related: [ADR-211, ADR-216, ADR-225]
tags: [klickdummy, feedback, bridge, cloudflare-worker, cf-access, co-creation]
scope:
  include_paths:
    - "docs/adr/ADR-227-*"
---

# ADR-227 — Klickdummy-Feedback-Bridge (Pfad B): CF-Worker statt User-PAT

> WARNUNG **Korrektur erforderlich (Auth-Substrat falsch, 2026-06-06):** Diese ADR baut auf der Annahme, iil.pet liege hinter **Cloudflare Access** (ADR-216) — das ist **faktisch falsch**. ADR-216 etabliert **Authentik forwardAuth** (verifiziert: `platform/infra/klickdummy-host/` nutzt `klickdummy-sso`-Middleware + `outpost.goauthentik.io`; die Cloudflare-Praesenz ist ein *Tunnel* fuer Ingress, **nicht** *Access* fuer Auth). Zudem **architektonisch inkompatibel**: ein CF-Worker am Edge sieht die origin-seitige Authentik-Identitaet nicht (Cf-Access-Jwt-Assertion existiert nicht). **Redesign noetig** (Bridge-Auth auf Authentik-Identitaet neu aufsetzen) — daher Status `draft`. Loest den Full-Scan-Konflikt 227<->216.

| Attribut       | Wert                                             |
|----------------|--------------------------------------------------|
| **Status**     | Proposed                                         |
| **Scope**      | platform (cross-cutting: alle KD-Repos + iil.pet)|
| **Repo**       | platform                                         |
| **Erstellt**   | 2026-05-29                                       |
| **Autor**      | Achim Dehnert                                    |
| **Reviewer**   | –                                                |
| **Amends**     | ADR-211 (hebt die Pfad-B-Sperre unter Bedingungen auf) |
| **Relates to** | ADR-211 (Co-Creation), ADR-216 (Hosting iil.pet), ADR-225 (genesor-Ingest) |

## 1. Kontext

### 1.1 Ausgangslage

Klickdummies tragen ein Feedback-Widget (ADR-211 §Co-Creation). Heute aktiv ist
**Pfad A-User-Direct**: der Browser postet ein GitHub-Issue **direkt** an
`api.github.com` mit dem **persönlichen PAT des Nutzers** aus `localStorage`
(`klickdummy_github_token`). Alternativ: Download/Clipboard (offline).

### 1.2 Problem / Lücken

Der „🚀 GitHub Issue"-Button verlangt einen PAT. `localStorage` ist **pro Browser +
Gerät + Domain** — bei jedem Rechner-/Browserwechsel (oder nach „Site-Daten löschen",
Inkognito) ist der Token weg → erneute PAT-Einrichtung. Das skaliert nicht für
**mehrere Stakeholder/Geräte**: jeder bräuchte einen eigenen PAT, was die meisten
Reviewer abschreckt → Feedback-Loop bleibt ungenutzt (empirisch wiederholt 2026-05-29).

### 1.3 Constraints

- `iil.pet` liegt bereits **hinter Cloudflare Access** (ADR-216) — alle Zugriffe sind
  authentifiziert.
- ADR-211 Rev 13 sperrt **Pfad B (Browser→Backend→GitHub)** ausdrücklich „ohne eigenen
  ADR" — wegen Service-Grenze, Threat-Model, Cost-Cap. **Dieser ADR ist dieser Beschluss.**
- Kein neues User-Login, keine zusätzliche Secret-Verteilung an Endnutzer.

## 2. Entscheidung

Wir führen eine **Feedback-Bridge** ein, die GitHub-Issues **serverseitig** anlegt — die
Nutzer brauchen **keinen PAT** mehr.

1. **Bridge = Cloudflare Worker** (iil.pet ist auf Cloudflare): gleiche Edge, liest die
   CF-Access-Identität, günstig, kein eigener Server zu betreiben.
2. **Auth über CF-Access (ADR-216), nicht neu erfunden:** Der Worker **validiert das
   CF-Access-JWT** (`Cf-Access-Jwt-Assertion` gegen die Team-Public-Keys). Nur
   CF-Access-authentifizierte Stakeholder erreichen die Bridge — **kein offener Endpoint**.
3. **Attribution:** Der Worker liest `Cf-Access-Authenticated-User-Email` und schreibt
   den **echten Einreicher** in Issue-Body + Label. GitHub-Author ist der Service-Account,
   die Person ist aber **verifiziert** zugeordnet (löst das Pfad-B-Audit-Bedenken).
4. **Token serverseitig:** *Ein* fine-grained GitHub-Token (oder GitHub-App) mit
   **`Issues: write`** auf einer **Repo-Allowlist**, als **Worker-Secret** — nie im Browser.
5. **Schutz:** Repo-Allowlist (nur KD-Repos), Payload-Größen-Cap, **Rate-Limit pro
   CF-Identität**, Input-Sanitizing. Kein LLM in der Schleife (→ kein Kosten-Risiko;
   falls je ergänzt: harter Cost-Cap, separater Beschluss).
6. **Widget:** neuer Submit-Mode `bridge` im geteilten `iil-klickdummy`-Widget — postet
   das Feedback-JSON an die Bridge statt an api.github.com. Pfad A (PAT) **bleibt** als
   Fallback für lokale/Nicht-iil.pet-Nutzung; Download/Clipboard bleiben.

## 3. Betrachtete Alternativen

| Option | Bewertung |
|---|---|
| **Pfad A beibehalten** (User-PAT, Status quo) | ❌ skaliert nicht über Geräte/Stakeholder; Reibung verhindert Nutzung. Bleibt als Fallback. |
| **PAT-UX verbessern** (Bookmarklet etc.) | ⚠️ lindert, löst aber Multi-Device/Multi-User nicht. |
| **Eigener Server/Service (Django-Route)** | ❌ überdimensioniert; eigener Betrieb, Auth-Schicht neu — CF-Worker nutzt die vorhandene CF-Access-Schicht. |
| **CF-Worker-Bridge hinter CF-Access (gewählt)** | ✅ null User-Setup, Auth+Attribution aus CF-Access, minimale Service-Fläche, edge-nah. |

## 4. Begründung im Detail

Der entscheidende Hebel: **CF-Access ist bereits die Auth-Schicht von iil.pet**. Eine
Bridge dort kann (a) Zugriff auf authentifizierte Nutzer beschränken und (b) deren
Identität für die Attribution nutzen — **beide** Pfad-B-Hauptsorgen (offener Endpoint,
verlorene Pro-Nutzer-Zuordnung) sind damit konstruktiv adressiert, ohne neue Login-/
Identitäts-Infrastruktur. Der Worker ist klein (~100 Zeilen), zustandslos (Rate-Limit via
CF KV/Durable Object), und der einzige Secret liegt edge-seitig, nie im Client.

## 5. Implementation Plan

1. **GitHub-App/Token** anlegen (`Issues: write`, Repo-Allowlist), als Worker-Secret hinterlegen.
2. **CF-Worker** `klickdummy-feedback-bridge`: CF-Access-JWT validieren → Payload validieren
   (Repo-Allowlist, Größe) → Rate-Limit (KV/Durable Object pro `sub`/Email) → Issue erstellen
   (Einreicher-Email + KD-Metadaten in Body/Labels) → 201 zurück.
3. **Widget** (`iil-klickdummy`): Submit-Mode `bridge` + Config `KLICKDUMMY_FEEDBACK_BRIDGE_URL`;
   wenn gesetzt, primärer Button → Bridge; PAT-Pfad bleibt Fallback. (Platform-PR + Vendoring-Refresh.)
4. **Rollout:** zuerst eine KD-Domain (z. B. design-hub) als Pilot, dann genesor-weit.

## 6. Risiken / Threat-Model

- **Token-Leak (Worker-Secret):** fine-grained, nur `Issues: write`, nur Allowlist-Repos →
  begrenzter Schaden; Rotation via Secret-Tausch.
- **Spam/Abuse:** nur via CF-Access erreichbar (authentifizierte Stakeholder) + Rate-Limit +
  Payload-Cap. Missbrauch ist einer realen Identität zuordenbar.
- **JWT-Validierung falsch:** gegen CF-Access-Team-Keys verifizieren (Issuer/Audience prüfen),
  nicht nur Header-Trust.
- **Issue-Flut:** Rate-Limit + optional Dedup (gleicher Screen+Hash innerhalb N min).

## 7. Konsequenzen

### 7.1 Positiv
- **Null Setup** für alle CF-Access-Stakeholder; Rechnerwechsel irrelevant.
- Feedback einer **verifizierten Person** zugeordnet; nativer Audit via CF + Issue-Label.
- Eine zentrale, kleine Service-Fläche statt PAT-Verteilung.

### 7.2 Trade-offs
- Neue (kleine) Betriebskomponente (CF-Worker + Secret).
- GitHub-Author = Service-Account (Einreicher im Body, nicht als nativer Author).
- Widget-Änderung am geteilten Paket → koordiniertes Vendoring-Refresh.

### 7.3 Nicht in Scope
- LLM-gestütztes Feedback-Processing (Pfad C bleibt verboten, eigener ADR).
- Nicht-iil.pet-Hosting der KDs (dort Pfad A/Download).

## 8. Validation Criteria

- Auf iil.pet: 🚀-Submit ohne PAT erzeugt ein GitHub-Issue im korrekten Repo mit
  Einreicher-Attribution; nicht-authentifizierter Direktaufruf der Bridge → 401/403.
- Rate-Limit greift; Payload jenseits Cap → 413; Repo außerhalb Allowlist → 403.
- Pfad A (PAT) + Download/Clipboard funktionieren unverändert weiter.

## 9. Glossar

| Abkürzung | Bedeutung |
|-----------|-----------|
| **PAT** | Personal Access Token — persönliches GitHub-Zugriffstoken |
| **CF-Access** | Cloudflare Access — Zugriffs-Gate vor iil.pet (Auth-Schicht) |
| **CF-Worker** | Cloudflare Worker — serverlose Funktion an der Cloudflare-Edge |
| **JWT** | JSON Web Token — von CF-Access signiertes Identitäts-Token |
| **Bridge** | Server-Vermittler Browser→GitHub (Pfad B), hält den Service-Token |
| **KV / Durable Object** | Cloudflare-Speicher für Zustand (hier: Rate-Limit) |
| **Pfad A/B/C** | Co-Creation-Pfade aus ADR-211 (A=User-Direct, B=Backend-Bridge, C=Browser-LLM verboten) |

## 10. Referenzen

- platform:ADR-211 — Klickdummy-Prozess, §Co-Creation (Pfade A/B/C)
- platform:ADR-216 — Klickdummy-Hosting iil.pet (CF-Access)
- platform:ADR-225 — genesor-Ingest-Architektur
- Cloudflare Access: JWT-Validierung (`Cf-Access-Jwt-Assertion`, Team-Public-Keys)

## 11. Changelog

- 2026-05-29: Initial (Proposed). Aus wiederholter PAT-Reibung beim Klickdummy-Feedback abgeleitet; aktiviert ADR-211 Pfad B unter CF-Access-Bedingungen.
