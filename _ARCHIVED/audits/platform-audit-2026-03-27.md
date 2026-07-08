# Platform Audit Report — 2026-03-27

## Executive Summary

- **Repos audited:** 39 (21 Django-Apps, 12 Python-Packages, 6 Meta/Infra)
- **Findings total:** 47 (Critical: 4, High: 12, Medium: 18, Low: 13)
- **Health Score:** 52/100
- **Trend:** Erster Audit — Baseline

---

## Critical Findings

| # | Repo | Finding | Impact | Fix |
|---|------|---------|--------|-----|
| C1 | **Server** | Disk 93% voll (133G/150G), Swap 100% | Server-Crash, OOM-Kills | Docker prune, Log-Rotation, ggf. Disk erweitern |
| C2 | **pptx-hub** | `pptx_hub_web` in Restart-Loop | Prezimo komplett offline | Container-Logs prüfen, Debug, Redeploy |
| C3 | **Server** | 3 orphan Container (`wonderful_dewdney`, `confident_meitner`, `heuristic_mclean`) unhealthy | Ressourcen-Verschwendung, Verwirrung | `docker rm -f` diese Container |
| C4 | **Server** | 9 Container unhealthy (inkl. Celery-Worker für risk-hub, recruiting-hub, learn-hub) | Background-Jobs laufen nicht | Healthcheck-Config oder Worker-Restart |

---

## High Findings

| # | Repo | Finding | ADR-Ref | Fix |
|---|------|---------|---------|-----|
| H1 | **bfagent** | 187 Dateien mit `os.environ` | ADR-045 | Migration zu `decouple.config()` |
| H2 | **bfagent** | 5994 `print()` Statements (!) | Reviewer | Migration zu `logging.getLogger()` |
| H3 | **mcp-hub** | 42 Dateien `os.environ`, 215 `print()` | ADR-045 | Schrittweise Migration |
| H4 | **bfagent** | 4 Direct LLM imports (anthropic/openai) | aifw-Pflicht | Zu `aifw.service.sync_completion()` |
| H5 | **cad-hub** | 3 Direct LLM imports, 75 `print()`, 12 `os.environ` | ADR-045 | Schrittweise Migration |
| H6 | **billing-hub** | 0 Health-Refs (`/livez/` fehlt) | Platform | Health-Endpoint hinzufügen |
| H7 | **odoo-hub** | 0 Health-Refs (`/livez/` fehlt) | Platform | Health-Endpoint hinzufügen |
| H8 | **research-hub** | 0 Health-Refs (`/livez/` fehlt) | Platform | Health-Endpoint hinzufügen |
| H9 | **recruiting-hub** | 1 Direct LLM import | aifw-Pflicht | Zu `aifw.service` migrieren |
| H10 | **mcp-hub** | 1 Direct LLM import | aifw-Pflicht | Zu `aifw.service` migrieren |
| H11 | **travel-beat/weltenhub** | Kein `pyproject.toml` | Platform | `pyproject.toml` anlegen |
| H12 | **dms-hub** | Keine CI/CD Workflows (`.github/workflows/` fehlt) | Platform | CI/CD einrichten |

---

## Medium Findings

| # | Repo | Finding | Fix |
|---|------|---------|-----|
| M1 | 15 Django-Apps | Kein `Makefile` | Template von bfagent/risk-hub kopieren |
| M2 | 14 Repos | Kein `CHANGELOG.md` | CHANGELOG anlegen |
| M3 | **illustration-hub** | Keine `.gitignore`, kein `.env.example`, 0 Test-Dateien | Grundlagen anlegen |
| M4 | **lastwar-bot** | 0 Test-Dateien, keine CI/CD | Mindestens Smoke-Tests |
| M5 | **infra-deploy** | 0 Test-Dateien | Tests für Reusable Workflows |
| M6 | **dev-hub** | Kein `.env.example` | Anlegen |
| M7 | **illustration-hub** | Kein `.env.example` | Anlegen |
| M8 | **odoo-hub** | 43 uncommitted Dateien | Aufräumen, committen oder .gitignore |
| M9 | **writing-hub** | 28 uncommitted Dateien | Aufräumen |
| M10 | **bfagent** | 26 uncommitted Dateien | Aufräumen |
| M11 | 12 Repos | Exakt 25 uncommitted Dateien (= .windsurf symlinks?) | .gitignore für .windsurf/ |
| M12 | **risk-hub-tmp** | Duplikat von risk-hub, 16 dirty files | Archivieren oder löschen |
| M13 | **coach-hub** | Settings in `build.py` statt `base.py` | Konsistente Namensgebung |
| M14 | **wedding-hub** | Settings in `build.py` statt `base.py` | Konsistente Namensgebung |
| M15 | **pptx-hub** | Settings in `settings.py` (nicht split) | Optional: Split in base/dev/prod |
| M16 | **odoo-hub** | Settings in `settings.py` (nicht split) | Optional: Split |
| M17 | **risk-hub** | Settings in `settings.py` (nicht split) | Bereits so gewachsen, OK |
| M18 | **trading-hub** | Settings in `settings.py` (nicht split) | Optional: Split |

---

## Low Findings

| # | Repo | Finding | Fix |
|---|------|---------|-----|
| L1 | **awesome-openclaw-skills** | Keine CI/CD | Optional für Docs-Repos |
| L2 | **platform** | Kein `pyproject.toml` | Optional für Meta-Repo |
| L3 | **mcp-hub** | Kein `pyproject.toml` | Eigenes Build-System |
| L4 | **infra-deploy** | Kein `pyproject.toml` | Reine GitHub Actions |
| L5 | **iil-relaunch** | Kein `pyproject.toml` | Website-Repo |
| L6 | 6 Python-Packages | Kein `Makefile` | Template kopieren |
| L7 | **openclaw** | 88 `print()` Statements | Schrittweise migrieren |
| L8 | **dev-hub** | 47 `print()` Statements | Migration zu logging |
| L9 | **odoo-hub** | 51 `print()` Statements | Migration zu logging |
| L10 | **weltenhub** | 73 `print()` Statements | Migration zu logging |
| L11 | **travel-beat** | 48 `print()` Statements | Migration zu logging |
| L12 | **pptx-hub** | 68 `print()` Statements | Migration zu logging |
| L13 | **research-hub** | 12 `os.environ` Dateien | Zu decouple migrieren |

---

## Cross-Repo Patterns

| Pattern | Betroffene Repos | Root Cause | Vorgeschlagene Lösung |
|---------|-----------------|------------|----------------------|
| **`os.environ` statt `decouple.config()`** | 25 von 32 Repos (bfagent: 187!) | Historisch gewachsen, kein Enforcement | Ruff-Rule oder pre-commit Hook |
| **`print()` statt `logging`** | 20+ Repos (bfagent: 5994!) | Schnelles Prototyping ohne Cleanup | Automatisierte Migration, Ruff-Rule |
| **Fehlende Makefiles** | 21 von 39 Repos | Kein Standard-Template beim Onboarding | `/onboard-repo` Workflow erweitern |
| **Fehlende CHANGELOG.md** | 14 Repos | Kein Release-Prozess etabliert | Template bereitstellen |
| **25 dirty files überall** | 14+ Repos identisch | `.windsurf/workflows/` Symlinks | `.gitignore` Pattern `.windsurf/` |
| **Inkonsistente Settings-Struktur** | coach-hub (build.py), wedding-hub (build.py), 4× settings.py statt split | Verschiedene Generationen von Repos | Standard-Template dokumentieren |
| **Direct LLM imports** | bfagent(4), cad-hub(3), recruiting-hub(1), mcp-hub(1) | Vor aifw-Migration | Migration zu aifw.service |
| **Fehlende Health-Endpoints** | billing-hub, odoo-hub, research-hub | Beim Onboarding vergessen | Health-View Template |
| **Celery-Worker unhealthy** | risk-hub, recruiting-hub, learn-hub | Healthcheck prüft HTTP, Celery hat keinen | Celery-spezifischen Healthcheck |

---

## Infrastruktur-Status

| Service | Container | Health | Uptime |
|---------|-----------|--------|--------|
| bfagent | bfagent_web | ✅ healthy | 12d |
| billing-hub | billing-hub-web | ✅ healthy | 2d |
| cad-hub | cad_hub_web | ✅ healthy | 4w |
| coach-hub | coach_hub_web | ✅ healthy | 50m |
| dev-hub | iil_dochub_web | ✅ healthy | 12d |
| dms-hub | dms_hub_web | ✅ healthy | 26h |
| illustration-hub | illustration_web | ⚠️ no healthcheck | 12d |
| knowledge | iil_knowledge_outline | ✅ healthy | 3d |
| pptx-hub | pptx_hub_web | ❌ **RESTART LOOP** | — |
| recruiting-hub | recruiting_hub_web | ✅ healthy | 30h |
| research-hub | research_hub_web | ✅ healthy | 12d |
| risk-hub | risk_hub_web | ✅ healthy | 2h |
| trading-hub | trading_hub_web | ✅ healthy | 12d |
| travel-beat | travel_beat_web | ✅ healthy | 12d |
| wedding-hub | wedding_hub_web | ✅ healthy | 12d |
| weltenhub | weltenhub_web | ✅ healthy | 12d |
| writing-hub | writing_hub_web | ⚠️ no healthcheck | 12d |
| ausschreibungs-hub | ausschreibungs_hub_web | ⚠️ no healthcheck | 12d |

### Server-Ressourcen

| Metrik | Wert | Status |
|--------|------|--------|
| **Disk** | 133G / 150G (93%) | ❌ CRITICAL |
| **RAM** | 14G / 22G (64%) | ⚠️ |
| **Swap** | 4.0G / 4.0G (100%) | ❌ CRITICAL |
| **Container total** | ~70 | ⚠️ Viele |
| **Unhealthy** | 9 | ❌ |
| **Orphaned** | 3 (random names) | ⚠️ |

---

## Verbesserungspotenziale (priorisiert)

### Sofort (heute)

1. **Disk-Space freigeben** — `docker system prune -a --volumes` (vorsichtig), alte Images, Logs
2. **pptx_hub_web debuggen** — Restart-Loop beheben
3. **Orphan-Container entfernen** — `wonderful_dewdney`, `confident_meitner`, `heuristic_mclean`

### Kurzfristig (diese Woche)

4. **`.gitignore` für `.windsurf/`** — Behebt 25-dirty-files Pattern in 14+ Repos
5. **Health-Endpoints für billing-hub, odoo-hub, research-hub** — Copy/Paste Template
6. **Celery-Healthcheck-Pattern** — ADR oder Runbook für Worker-Healthchecks
7. **bfagent Direct LLM imports** → aifw migrieren (4 Dateien)

### Mittelfristig (nächste 2 Wochen)

8. **Ruff-Rule für `os.environ`** — Automatisches Enforcement über alle Repos
9. **`print()` → `logging` Migration** — Start mit bfagent (5994 Stellen, ggf. automatisiert)
10. **Makefile-Template** — Standard-Makefile in `/onboard-repo` Workflow
11. **CHANGELOG-Template** — Standard-Format, bei jedem Release pflegen
12. **Settings-Struktur standardisieren** — coach-hub/wedding-hub `build.py` → `base.py`

### Langfristig (Backlog)

13. **risk-hub-tmp archivieren** — Duplikat bereinigen
14. **illustration-hub Tests** — Von 0 auf mindestens Smoke-Tests
15. **cad-hub/mcp-hub os.environ Migration** — Größere Refactoring-Tasks
16. **Server-Kapazität** — Disk-Upgrade oder zweiten Server evaluieren

---

## Metriken-Trend

| Metrik | Baseline (heute) | Ziel |
|--------|-------------------|------|
| Repos mit UUIDField PK-Verstoß | **0** ✅ | 0 |
| Repos mit `os.environ` | **25/32** ❌ | 0 |
| Repos mit `print()` statt logging | **20+** ❌ | 0 |
| Repos mit Direct LLM imports | **4** (9 Dateien) | 0 |
| Repos mit CI/CD | **36/39** ⚠️ | 39/39 |
| Django-Apps mit `/livez/` | **17/21** ⚠️ | 21/21 |
| Django-Apps mit Makefile | **6/21** ❌ | 21/21 |
| Repos mit CHANGELOG | **12/39** ⚠️ | 39/39 |
| Container healthy | **~50/70** ⚠️ | 70/70 |
| Disk usage | **93%** ❌ | <80% |
| Swap usage | **100%** ❌ | <50% |

---

*Generated by /platform-audit v2.0 — 2026-03-27T19:45+01:00*
