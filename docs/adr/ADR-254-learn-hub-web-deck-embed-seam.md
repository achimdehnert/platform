---
id: ADR-254
title: "learn-hub Web-Deck-Embed-Naht: Artefakt-URL, Auth/Tenant-Isolation, CSP/iframe, Staleness-Lifecycle"
status: proposed
date: 2026-06-19
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, achimdehnert]
domains: [teaching, learn-hub, security, architecture, governance]
supersedes: []
amends: []
depends_on: [ADR-253, ADR-140]
related: [ADR-137, ADR-139]
tags: [learn-hub, web-deck, embed, iframe, csp, auth, tenant-isolation, staleness, security]
scope:
  include_paths:
    - "docs/adr/ADR-254-*"
---

# ADR-254 — learn-hub Web-Deck-Embed-Naht

> **Folge-ADR zu ADR-253.** ADR-253 hat die learn-hub-Einbettung bewusst nur **benannt** und die
> Ausspezifikation hierher ausgelagert (Cross-Repo-Scope). Dieses ADR ist **renderer-agnostisch**:
> Es definiert die Naht zwischen einem **fertig gebauten, statischen Web-Deck-Artefakt** und
> learn-hub — **unabhängig davon, welcher Renderer den Gate-1-Bake-off (ADR-253 §3) gewinnt**
> (Slidev oder reveal.js-aus-Python).

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage
ADR-253 produziert ein **statisches** Web-Deck (einmal gebaut, zur Vortragszeit ohne Node/Chromium).
ADR-140 etabliert learn-hub als LMS mit Multi-Tenancy (ADR-137). Offen ist die **Naht**: Wie kommt
das Deck-Artefakt sicher und aktuell in einen learn-hub-Kurs.

### 1.2 Problem / Lücken
| Lücke | Konsequenz |
|---|---|
| Artefakt-Ablage & URL-Schema undefiniert | Renderer und LMS koppeln sich später über implizite Pfad-/URL-Konventionen |
| Auth/Zugriffsschutz offen | Nicht-öffentliche Vorlesungs-Decks wären ohne Schutz per URL abrufbar |
| Tenant-Isolation offen | Deck von Tenant A in Kurs von Tenant B abrufbar (ADR-137-Verletzung) |
| iframe/CSP offen | Einbettung bricht an Browser-Security-Headern oder öffnet XSS-Fläche |
| **Staleness** offen (ADR-253 Render-Job) | Dozent ändert Outline → eingebettetes Deck zeigt alten Stand bis manuellem Re-Run |

## 2. Entscheidung

1. **Artefakt-Adresse:** Web-Decks liegen unter einem **versionierten, tenant-gescopten Pfad**
   `/<tenant>/decks/<deck-id>/<build-hash>/index.html`; learn-hub speichert pro Kurs-Element die
   **`deck-id` + gewünschten Pin** (`latest` oder fixer `build-hash`), **nie** eine rohe URL.
2. **Auth:** Deck-Auslieferung ist **nicht öffentlich**; Zugriff über eine **signierte, kurzlebige
   URL** (oder Reverse-Proxy-Auth gegen die learn-hub-Session) — kein „security by obscurity".
3. **Tenant-Isolation:** Auslieferung prüft Tenant-Zugehörigkeit (ADR-137) **serverseitig**;
   `build-hash` im Pfad verhindert Cross-Tenant-Erraten.
4. **Einbettung:** `<iframe>` mit **restriktiver CSP** (`frame-ancestors` nur learn-hub-Origin;
   `sandbox` ohne `allow-same-origin` wo möglich); Deck-Build darf **kein raw-`<script>` aus
   LLM-/Nutzer-Inhalt** enthalten (erbt die Sanitization-Regel aus ADR-253 §5 Security).
5. **Staleness-Lifecycle:** Pin-Default `latest` zeigt **immer den letzten erfolgreichen Build**;
   bei Outline-Änderung triggert der ADR-253-Render-Job einen neuen `build-hash` und aktualisiert
   `latest` **atomar nach** erfolgreichem Build. Optionaler **fixer Pin** für „eingefrorene"
   Vorlesungsstände. Alte `build-hash`-Artefakte werden per Retention-Policy aufgeräumt.

## 3. Betrachtete Alternativen
| Option | Bewertung |
|---|---|
| Rohe öffentliche URL pro Deck | ❌ kein Schutz, keine Tenant-Isolation |
| Deck-HTML direkt in learn-hub-DOM inlinen (kein iframe) | ❌ XSS-Fläche, CSS/JS-Kollision mit LMS |
| `latest`-only ohne fixe Pins | ➖ einfacher, aber keine eingefrorenen Prüfungsstände |
| **iframe + signierte URL + Tenant-Check + Pin (gewählt)** | ✅ Schutz, Isolation, Staleness-Kontrolle, renderer-agnostisch |

## 4. Konsequenzen
- **Positiv:** klare, renderer-unabhängige Naht; Tenant-sicher; Stale-Deck-Bugklasse adressiert;
  eingefrorene Stände möglich.
- **Trade-offs:** signierte URLs + Retention-Job sind zusätzlicher Betrieb; CSP/sandbox kann
  Renderer-Features (z. B. externe Fonts/CDN-Plugins) einschränken → im Gate-1-Bake-off mitprüfen.
- **Nicht in Scope:** Kurs-/Enrollment-Logik (learn-hub-intern), Wahl des Renderers (ADR-253 Gate 1),
  PDF-Handout (ADR-253 Gate 2).

## 5. Validation Criteria
- Deck nur mit gültiger Session/Signatur + korrektem Tenant abrufbar (Negativtest: fremder Tenant → 403).
- CSP `frame-ancestors` lässt nur learn-hub-Origin zu; raw-Script aus Deck-Inhalt blockiert.
- Outline-Änderung → neuer `build-hash`, `latest` erst nach erfolgreichem Build umgeschaltet (kein Stale-Zustand sichtbar).

## 6. Glossar
| Begriff | Bedeutung |
|---|---|
| **Embed-Naht** | definierte Schnittstelle, über die learn-hub ein extern erzeugtes Artefakt einbettet |
| **CSP** | Content Security Policy — Browser-Header, der Einbettung/Skripte einschränkt |
| **`frame-ancestors`** | CSP-Direktive: welche Origins dürfen die Seite im iframe einbetten |
| **build-hash** | eindeutige Kennung eines konkreten Deck-Builds (Versionierung/Cache-Busting) |
| **Pin** | Festlegung, welchen Build ein Kurs-Element zeigt (`latest` oder fixer `build-hash`) |
| **Staleness** | Zustand, in dem das eingebettete Deck einen veralteten Outline-Stand zeigt |

## 7. Referenzen
- platform **ADR-253** — render-neutraler Lehr-Outline-Vertrag + Web-Deck-Renderer (Bake-off)
- platform **ADR-140** — learn-hub (LMS)
- platform **ADR-137** — Tenant-Lifecycle / RLS (Multi-Tenancy)
- platform **ADR-139** — iil-learnfw

## 8. Changelog
- **2026-06-19** — Entwurf erstellt (proposed); ausgelagert aus ADR-253 §5 (learn-hub-Naht).
