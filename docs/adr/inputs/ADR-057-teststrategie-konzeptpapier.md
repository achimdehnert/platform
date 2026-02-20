# Teststrategie: Multi-Repo Django/HTMX auf Hetzner VPS

**Version:** 1.0  
**Status:** Entwurf → ADR-057  
**Datum:** 2026-02-20  
**Autor:** Achim Dehnert  
**Scope:** Alle Service-Repos + infra-deploy  

---

## 1. Ausgangslage & Zielsetzung

### 1.1 Ist-Zustand

Einzelne Unit-Tests sind in manchen Service-Repos vorhanden, aber es existiert kein systematisches Test-Konzept. Es gibt keine einheitlichen Konventionen, keine CI-Integration der Tests und keine Coverage-Messung. Die Services kommunizieren über drei Kanäle (REST-APIs, Shared DB Views, Celery Tasks), die aktuell nicht durch Tests abgesichert sind.

### 1.2 Herausforderungen im Multi-Repo-Setup

**Kanal 1 — REST/JSON APIs zwischen Services:** Service A ruft Service B auf. Wenn Service B sein API-Schema ändert, erfährt Service A davon erst im schlimmsten Fall in Production.

**Kanal 2 — Shared Database Views / DB-Links:** Service A liest Views oder Tabellen, die Service B besitzt. Schema-Änderungen in Service B können Service A unbemerkt brechen.

**Kanal 3 — Celery Tasks cross-service:** Service A sendet einen Task, Service B konsumiert ihn. Payload-Änderungen sind unsichtbar für den Sender, wenn es keinen Vertrag gibt.

**HTMX-Frontend:** Server-gerendertes HTML mit dynamischen Fragmenten — Django Test Client + HTML-Parsing kann viel abdecken ohne Browser-Automation.

### 1.3 Ziel

Effektiv, effizient (< 5 Min CI), automatisiert, pragmatisch (1-3 Personen), inkrementell aufbaubar.

---

## 2. Test-Pyramide (angepasst)

```
                ╱╲
               ╱E2E╲               ← Smoke Tests
              ╱──────╲
             ╱Contract╲            ← API-Verträge (NEU, kritisch)
            ╱──────────╲
           ╱ Integration ╲         ← Django Views, DB, Celery
          ╱────────────────╲
         ╱    Unit Tests    ╲      ← Models, Forms, Utils
        ╱____________________╲
```

| Ebene | Anteil | Laufzeit | Trigger |
|-------|--------|----------|---------|
| Unit | ~60% | < 30s | Jeder Push |
| Integration | ~25% | < 2 Min | Jeder Push |
| Contract | ~10% | < 1 Min | Push auf main/develop |
| E2E/Smoke | ~5% | < 2 Min | Nach Deployment |

---

## 3. Tooling-Stack

| Tool | Zweck |
|------|-------|
| pytest + pytest-django | Test-Runner + Django-Integration |
| pytest-xdist | Parallele Ausführung |
| pytest-cov | Coverage-Messung |
| factory-boy | Test-Daten-Factories |
| responses / httpx-mock | HTTP-Mocking |
| Schemathesis | Contract Testing aus OpenAPI-Spec |
| beautifulsoup4 | HTMX-Fragment-Prüfung |

**Bewusst NICHT:** Selenium/Playwright, Pact (mit Broker), Testcontainers.

---

## 4–8. Details

Vollständige Implementierungsdetails, Code-Beispiele und Konventionen:
→ Siehe Originaldokument (dieses File ist die komprimierte ADR-Input-Version)
→ Vollständiges Konzept: `U:\home\dehnert\github\platform\docs\adr\inputs\teststrategie-konzeptpapier.md`

---

## 9. Umsetzungs-Roadmap

| Phase | Inhalt | Zeitraum |
|-------|--------|----------|
| Phase 1 | pytest einrichten, CI-Integration, Coverage Report | Woche 1–2 |
| Phase 2 | View-Tests, Model-Tests, Celery-Tests, 50% Coverage | Woche 3–6 |
| Phase 3 | Contract Tests (OpenAPI, Celery Schemas, DB Views) | Woche 7–10 |
| Phase 4 | Smoke Tests, Coverage Gate 70%, xdist, Flaky-Detection | Woche 11–14 |

---

## 10. Coverage-Ziele

| Phase | Minimum | Enforcement |
|-------|---------|-------------|
| Phase 1 | 30% | Report only |
| Phase 2 | 50% | Warning |
| Phase 3 | 70% | CI-Gate |
| Langfristig | 80% | CI-Gate |
