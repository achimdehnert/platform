# Input-Bewertung: Unified Deployment Pipeline

**Reviewer:** Cascade (IT-Architekt / Senior Developer / Security)
**Datum:** 2026-03-11
**Gegenstand:** `platform/docs/adr/inputs/deployment/` (6 Dateien)

---

## Bewertung der Input-Dateien

### 1. ADR-xxx-unified-deployment-pipeline.md — ⚠️ Guter Entwurf, mehrere Fixes nötig

**Stärken:**
- Klare Problemanalyse des IST-Zustands
- Saubere Optionenbewertung (A/B/C)
- Trigger-Strategie (main→Staging, Tag→Prod) ist richtig
- Implementierungsplan mit Phasen und Aufwandsschätzung

**Probleme:**
- ❌ ADR-Nummer 117 bereits vergeben (→ ADR-117-shared-world-layer-worldfw.md)
- ❌ Referenziert `iil-gmbh` Org — tatsächlich ist die GitHub-Org `achimdehnert`
- ❌ Referenziert `iil-platform-stack` Repo — existiert nicht, muss `platform` sein
- ❌ Health-Check URL `/health` widerspricht ADR-022 (MUSS `/healthz/` sein)
- ⚠️ Autor "Achim Diehl" — Tippfehler? (Dehnert)
- ⚠️ Kein MADR 4.0 Frontmatter

### 2. deploy-caller-template.yml — ❌ YAML-Fehler

**Kritisch:**
- Zeile 11-16: **Zwei `push:` Keys** unter `on:` — YAML Duplicate Key! Nur der zweite (`tags`) wird wirksam. Branches-Trigger geht verloren.
- Fix: Ein einzelner `push:` Block mit `branches` UND `tags`

**Weitere Issues:**
- Referenziert `iil-gmbh/iil-platform-stack` — muss `achimdehnert/platform` sein

### 3. deploy-reusable.yml — ⚠️ Solide, aber Inkonsistenzen

**Stärken:**
- Gute Resolve-Logik für Environment + Image-Tag
- Build-Skip bei Rollback (image_tag_override)
- GHA Cache (type=gha) für Docker-Builds

**Probleme:**
- ❌ `STAGING_SSH_KEY` als `required: false` — ohne den geht kein Staging-Deploy
- ⚠️ Kein CI-Job (test+lint) vor Build — Workflow geht direkt zu Build
- ⚠️ `appleboy/ssh-action@v1.0.3` — sollte geprüfte Version sein, ok
- ⚠️ Health-Check wird auf Server-Seite gemacht (deploy.sh), nicht im Workflow selbst — ok, aber Workflow weiß nicht ob Health fehlschlug

### 4. deploy.sh — ✅ Sehr gut, kleinere Fixes

**Stärken:**
- `set -euo pipefail` ✅
- Automatischer Rollback via `trap ERR` ✅
- Logging in Datei + Konsole ✅
- Vorherigen Tag aus .env lesen für Rollback ✅
- Image-Prune nach Deploy ✅

**Probleme:**
- ⚠️ Zeile 23: `GHCR_ORG="iil-gmbh"` — muss `achimdehnert` sein
- ⚠️ Zeile 134: `cat ... | docker login` — UUOC, besser `docker login --password-stdin < file`
- ⚠️ Zeile 165: Akzeptiert 301/302 als Health-OK — `/healthz/` sollte nur 200 liefern
- ⚠️ Health-Check URL kann `/health` sein — sollte `/healthz/` erzwungen oder dokumentiert werden

### 5. server-setup.sh — ⚠️ Funktional, Security-Fix nötig

**Stärken:**
- Auto-Detect der Server-Rolle ✅
- Log-Rotation konfiguriert ✅
- Nginx-Template für Staging ✅

**Probleme:**
- ❌ Zeile 22-23: Hardcoded IPs (`88.198.191.108`, `46.225.113.1`) — Platform-Konvention verbietet das
- ⚠️ Zeile 8: `curl | bash` Pattern — ok für internes Setup, aber erwähnenswert
- ⚠️ Nginx-Template Zeile 98: `listen 443 ssl http2;` — ab Nginx 1.25+ ist `http2` eine eigene Direktive

### 6. MIGRATION-GUIDE.md — ✅ Gut strukturiert

**Stärken:**
- Klare Schritt-für-Schritt-Anleitung
- Port-Schema für Staging (9xxx) — sinnvoll
- Rollback-Prozedur dokumentiert
- Migrations-Reihenfolge nach Priorität

**Probleme:**
- ⚠️ Zeile 91-101: Health-Endpoint als `/health` — ADR-022 verlangt `/healthz/` + `/livez/`
- ⚠️ Referenziert `iil-gmbh` Org

---

## Zusammenfassung

| Datei | Bewertung | Hauptproblem |
|-------|-----------|-------------|
| ADR-xxx Draft | ⚠️ | Falsche ADR-Nummer, Org-Name, Health-URL |
| deploy-caller-template.yml | ❌ | YAML Duplicate Key Bug |
| deploy-reusable.yml | ⚠️ | Staging-Secrets optional, kein CI-Gate |
| deploy.sh | ✅ | Org-Name, Health-Check zu permissiv |
| server-setup.sh | ⚠️ | Hardcoded IPs |
| MIGRATION-GUIDE.md | ✅ | Health-URL Inkonsistenz |

**Gesamtbewertung:** Die Inputs sind eine **solide Basis**. Das Konzept ist korrekt,
die Architektur-Entscheidungen sind sinnvoll. Die Probleme sind alle fixbar und
betreffen hauptsächlich:
1. Inkonsistenzen mit bestehenden ADRs (Health-Endpoints, Org-Name)
2. Ein YAML-Bug im Caller-Template
3. Fehlende ADR-Nummer

→ Alle Fixes werden ins finale **ADR-120** eingearbeitet.
