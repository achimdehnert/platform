---
description: Cross-Repo Platform Audit — Schwachstellen, Inkonsistenzen und Verbesserungspotenziale über ALLE Repos ermitteln und als Report sichern
---

# /platform-audit

> **Ziel:** Alle Repos + Infrastruktur systematisch auditieren, Schwachstellen finden,
> priorisierte Optimierungsvorschläge generieren und als actionable Report sichern.
> Gegenstück: `/repo-health-check` (einzelnes Repo), `/deploy-check` (einzelner Deploy).

**Trigger:** Manuell (`/platform-audit`), empfohlen: 1× pro Woche oder nach größeren Changes.

---

## Bekannte Repos (alle auditieren)

### Django-Apps (21)

| Repo | Prod-URL | Port |
|------|----------|------|
| **137-hub** | — | — |
| **ausschreibungs-hub** | — | — |
| **bfagent** | bfagent.iil.pet | 8000 |
| **billing-hub** | — | — |
| **cad-hub** | — | — |
| **coach-hub** | coach-hub.iil.pet | — |
| **dev-hub** | devhub.iil.pet | — |
| **dms-hub** | — | — |
| **illustration-hub** | illustration.iil.pet | — |
| **learn-hub** | — | — |
| **odoo-hub** | odoo.iil.pet | — |
| **pptx-hub** | prezimo.com | 8020 |
| **recruiting-hub** | — | — |
| **research-hub** | — | — |
| **risk-hub** | schutztat.de | 8090 |
| **risk-hub-tmp** | — | — |
| **trading-hub** | — | — |
| **travel-beat** | drifttales.app | 8010 |
| **wedding-hub** | — | — |
| **weltenhub** | weltenforger.com | 8030 |
| **writing-hub** | — | — |

### Python-Packages (12)

| Package | PyPI | Import |
|---------|------|--------|
| **aifw** | iil-aifw | `aifw` |
| **authoringfw** | iil-authoringfw | `authoringfw` |
| **illustration-fw** | — | `illustration_fw` |
| **lastwar-bot** | — | — |
| **learnfw** | iil-learnfw | `learnfw` |
| **nl2cad** | iil-nl2cad | `nl2cad` |
| **openclaw** | — | `openclaw` |
| **outlinefw** | iil-outlinefw | `outlinefw` |
| **promptfw** | iil-promptfw | `promptfw` |
| **researchfw** | — | `researchfw` |
| **testkit** | iil-testkit | `testkit` |
| **weltenfw** | — | `weltenfw` |

### Meta / Infra (6)

| Repo | Zweck |
|------|-------|
| **platform** | ADRs, Workflows, Packages, Infra-Scripts |
| **mcp-hub** | MCP-Server (deployment, orchestrator, llm) |
| **infra-deploy** | GitHub Actions Reusable Workflows |
| **iil-relaunch** | Website |
| **awesome-openclaw-skills** | OpenClaw Docs |
| **awesome-openclaw-usecases** | OpenClaw Docs |

### Ohne Git (ignoriert)

`iil-dms-hub-client`, `iil-dvelop-client`, `iil-sevdesk-client`

**Gesamt: 39 Git-Repos** (3 ohne Git = ignoriert)

---

## Phase 1: Repo-Scan (autonom, pro Repo)

Für **jedes** Repo aus der Liste oben:

### 1.1 Git-Status + Branch-Hygiene

// turbo
```bash
ALL_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub risk-hub-tmp trading-hub travel-beat wedding-hub weltenhub writing-hub aifw authoringfw illustration-fw lastwar-bot learnfw nl2cad openclaw outlinefw promptfw researchfw testkit weltenfw platform mcp-hub infra-deploy iil-relaunch awesome-openclaw-skills awesome-openclaw-usecases"
for repo in $ALL_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  git -C ${GITHUB_DIR:-$HOME/github}/$repo branch --show-current
  git -C ${GITHUB_DIR:-$HOME/github}/$repo status --porcelain | head -5
  git -C ${GITHUB_DIR:-$HOME/github}/$repo log --oneline -3
  echo ""
done
```

Erfasse pro Repo:
- **Branch**: auf `main`? Stale Feature-Branches?
- **Uncommitted**: Dirty working tree?
- **Last commit**: Wie alt ist der letzte Commit?

### 1.2 Pflicht-Dateien Check

// turbo
```bash
ALL_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub risk-hub-tmp trading-hub travel-beat wedding-hub weltenhub writing-hub aifw authoringfw illustration-fw lastwar-bot learnfw nl2cad openclaw outlinefw promptfw researchfw testkit weltenfw platform mcp-hub infra-deploy iil-relaunch awesome-openclaw-skills awesome-openclaw-usecases"
for repo in $ALL_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  for f in README.md .gitignore Makefile pyproject.toml CHANGELOG.md; do
    [ -e ${GITHUB_DIR:-$HOME/github}/$repo/$f ] && echo "  OK: $f" || echo "  MISSING: $f"
  done
  # Django-spezifisch (nur wenn docker-compose vorhanden)
  if [ -f ${GITHUB_DIR:-$HOME/github}/$repo/docker-compose.prod.yml ] || [ -d ${GITHUB_DIR:-$HOME/github}/$repo/docker ]; then
    for f in docker-compose.prod.yml Dockerfile .env.example; do
      [ -e ${GITHUB_DIR:-$HOME/github}/$repo/$f ] || [ -e ${GITHUB_DIR:-$HOME/github}/$repo/docker/$f ] || [ -e ${GITHUB_DIR:-$HOME/github}/$repo/docker/app/$f ] && echo "  OK: $f" || echo "  MISSING: $f"
    done
  fi
  echo ""
done
```

### 1.3 CI/CD Workflows Check

// turbo
```bash
ALL_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub risk-hub-tmp trading-hub travel-beat wedding-hub weltenhub writing-hub aifw authoringfw illustration-fw lastwar-bot learnfw nl2cad openclaw outlinefw promptfw researchfw testkit weltenfw platform mcp-hub infra-deploy iil-relaunch awesome-openclaw-skills awesome-openclaw-usecases"
for repo in $ALL_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  ls ${GITHUB_DIR:-$HOME/github}/$repo/.github/workflows/ 2>/dev/null || echo "  MISSING: .github/workflows/"
  echo ""
done
```

### 1.4 Test-Suite Status

// turbo
```bash
ALL_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub risk-hub-tmp trading-hub travel-beat wedding-hub weltenhub writing-hub aifw authoringfw illustration-fw lastwar-bot learnfw nl2cad openclaw outlinefw promptfw researchfw testkit weltenfw platform mcp-hub infra-deploy"
for repo in $ALL_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  find ${GITHUB_DIR:-$HOME/github}/$repo -path '*/tests/*.py' -o -path '*/test_*.py' | grep -v '.venv' | grep -v node_modules | wc -l | xargs echo "  Test files:"
  find ${GITHUB_DIR:-$HOME/github}/$repo -name 'conftest.py' | grep -v '.venv' | wc -l | xargs echo "  conftest.py:"
  echo ""
done
```

---

## Phase 2: Architektur-Konsistenz (Cross-Repo)

### 2.1 Platform-Context Violations

Für jedes Django-Repo: `mcp14_get_context_for_task` aufrufen und bekannte Violations prüfen.

Prüfe insbesondere:
- **BigAutoField vs. UUIDField** — `grep -r 'UUIDField(primary_key=True)' src/ apps/ --include='*.py' -l`
- **os.environ statt decouple** — `grep -r 'os\.environ' src/ apps/ --include='*.py' -l`
- **print() statt logging** — `grep -rn 'print(' src/ apps/ --include='*.py' | grep -v test | grep -v '#'`
- **Hardcoded secrets** — `grep -rni 'password\|secret_key\|api_key' src/ apps/ --include='*.py' | grep -v test | grep -v config`
- **Direct LLM imports** — `grep -r 'import anthropic\|import openai\|from groq' src/ apps/ --include='*.py' -l`

// turbo
```bash
DJANGO_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub trading-hub travel-beat wedding-hub weltenhub writing-hub"
PKG_REPOS="aifw authoringfw illustration-fw learnfw nl2cad openclaw outlinefw promptfw researchfw testkit weltenfw mcp-hub"
for repo in $DJANGO_REPOS $PKG_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  echo "  UUIDField PKs: $(grep -r 'UUIDField(primary_key=True)' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' -l 2>/dev/null | grep -v '.venv' | wc -l)"
  echo "  os.environ: $(grep -r 'os\.environ' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' -l 2>/dev/null | grep -v test | grep -v '.venv' | grep -v node_modules | wc -l)"
  echo "  print(): $(grep -rn 'print(' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' 2>/dev/null | grep -v test | grep -v '.venv' | grep -v node_modules | grep -v '#' | wc -l)"
  echo "  Direct LLM: $(grep -r 'import anthropic\|import openai\|from groq' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' -l 2>/dev/null | grep -v '.venv' | wc -l)"
  echo ""
done
```

### 2.2 Settings-Struktur Konsistenz

// turbo
```bash
DJANGO_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub trading-hub travel-beat wedding-hub weltenhub writing-hub"
for repo in $DJANGO_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  echo "  DEFAULT_AUTO_FIELD:"
  grep -r 'DEFAULT_AUTO_FIELD' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' 2>/dev/null | grep -v '.venv' | head -1
  echo "  Settings file:"
  find ${GITHUB_DIR:-$HOME/github}/$repo -path '*/config/settings*' -name '*.py' 2>/dev/null | grep -v '.venv' | head -3
  echo ""
done
```

### 2.3 Health-Endpoints Konsistenz

// turbo
```bash
DJANGO_REPOS="137-hub ausschreibungs-hub bfagent billing-hub cad-hub coach-hub dev-hub dms-hub illustration-hub learn-hub odoo-hub pptx-hub recruiting-hub research-hub risk-hub trading-hub travel-beat wedding-hub weltenhub writing-hub"
for repo in $DJANGO_REPOS; do
  [ -d ${GITHUB_DIR:-$HOME/github}/$repo/.git ] || continue
  echo "=== $repo ==="
  grep -rn 'livez\|healthz\|health/' ${GITHUB_DIR:-$HOME/github}/$repo --include='*.py' 2>/dev/null | grep -v test | grep -v '.venv' | head -3
  echo ""
done
```

---

## Phase 3: Infrastruktur Health (Production)

### 3.1 Container-Status aller Apps

Via deployment-mcp:

```
mcp6_docker_manage(action="container_list", host="88.198.191.108")
```

Erfasse:
- Welche Container laufen / gestoppt / unhealthy?
- Memory/CPU pro Container
- Uptime (Restart-Loops erkennen)

### 3.2 Health-Endpoints aller Prod-URLs

```
mcp6_system_manage(action="health_dashboard", host="88.198.191.108")
```

Oder manuell:
```
mcp6_ssh_manage(action="http_check", url="https://bfagent.iil.pet/livez/", host="88.198.191.108")
mcp6_ssh_manage(action="http_check", url="https://drifttales.app/livez/", host="88.198.191.108")
mcp6_ssh_manage(action="http_check", url="https://weltenforger.com/livez/", host="88.198.191.108")
mcp6_ssh_manage(action="http_check", url="https://schutztat.de/livez/", host="88.198.191.108")
mcp6_ssh_manage(action="http_check", url="https://prezimo.com/livez/", host="88.198.191.108")
```

### 3.3 SSL-Zertifikate

```
mcp6_network_manage(action="ssl_expiring", days=30, host="88.198.191.108")
```

### 3.4 Disk + Memory

```
mcp6_system_manage(action="info", host="88.198.191.108")
```

---

## Phase 4: Analyse + Report

### 4.1 Findings klassifizieren

Ordne jedes Finding in eine Kategorie ein:

| Severity | Bedeutung | Beispiel |
|----------|-----------|---------|
| **CRITICAL** | Prod-Risiko, sofort beheben | Container down, SSL ablaufend, Secrets im Code |
| **HIGH** | Architektur-Verstoß, nächster Sprint | UUIDField PK, os.environ, Direct LLM |
| **MEDIUM** | Inkonsistenz, zeitnah | Fehlende Tests, Missing CHANGELOG, Stale Branches |
| **LOW** | Nice-to-have, Backlog | Fehlende Keywords, Missing Makefile |

### 4.2 Cross-Repo Patterns erkennen

Suche nach **systematischen** Problemen:
- Gleicher Fehler in >2 Repos → Pattern → Platform-weite Lösung
- Fehlende Standardisierung → neuer ADR nötig?
- Drift zwischen Repos → Tooling oder Template aktualisieren

### 4.3 Report generieren

Generiere den Report als Markdown mit folgendem Template:

```markdown
# Platform Audit Report — {DATUM}

## Executive Summary

- **Repos audited:** {N}
- **Findings total:** {N} (Critical: {N}, High: {N}, Medium: {N}, Low: {N})
- **Health Score:** {N}/100
- **Trend:** ↑/↓/→ vs. letzter Audit

## Critical Findings

| # | Repo | Finding | Impact | Fix |
|---|------|---------|--------|-----|

## High Findings

| # | Repo | Finding | ADR-Ref | Fix |
|---|------|---------|---------|-----|

## Medium Findings

| # | Repo | Finding | Fix |
|---|------|---------|-----|

## Low Findings

| # | Repo | Finding | Fix |
|---|------|---------|-----|

## Cross-Repo Patterns

| Pattern | Betroffene Repos | Root Cause | Vorgeschlagene Lösung |
|---------|-----------------|------------|----------------------|

## Infrastruktur-Status

| Service | Container | Health | SSL | Memory |
|---------|-----------|--------|-----|--------|

## Verbesserungspotenziale (priorisiert)

### Kurzfristig (diese Woche)
1. ...

### Mittelfristig (nächste 2 Wochen)
1. ...

### Langfristig (Backlog)
1. ...

## Metriken-Trend

| Metrik | Vorher | Jetzt | Ziel |
|--------|--------|-------|------|
| Repos mit BigAutoField-Verstoß | — | {N} | 0 |
| Repos mit os.environ | — | {N} | 0 |
| Repos mit CI/CD | — | {N}/39 | 39/39 |
| Health-Endpoints grün | — | {N}/21 | 21/21 |
| Test-Coverage (Dateien) | — | {N} | >50 pro Django-App |

---

*Generated by /platform-audit — {TIMESTAMP}*
```

---

## Phase 5: Report sichern

### 5.1 Lokal speichern

Speichere den Report als:
```
${GITHUB_DIR:-$HOME/github}/platform/audits/platform-audit-{YYYY-MM-DD}.md
```

### 5.2 In Outline sichern

```
<outline-mcp>_search_knowledge(query="Platform Audit Report")
```

- **Erster Audit**: `<outline-mcp>_create_concept(title="Platform Audit Report — {DATUM}", content=report)`
- **Folge-Audits**: `<outline-mcp>_update_document(document_id=..., content=report)` — Trend-Abschnitt aktualisieren

### 5.3 GitHub Issues erstellen (optional)

Für jedes CRITICAL oder HIGH Finding:
```
mcp8_create_issue(
    owner="achimdehnert",
    repo="{betroffenes-repo}",
    title="[Platform Audit] {Finding}",
    labels=["platform-audit", "tech-debt"],
    body="..."
)
```

### 5.4 Cascade Memory updaten

```
Memory: "Platform Audit {DATUM} — {N} Findings, Score {N}/100 — Report in Outline"
```

---

## Schnell-Referenz

```
/platform-audit              ← Vollständiger Audit (alle Phasen)
/platform-audit --quick      ← Nur Phase 1+3 (Git + Health, ~2 Min)
/platform-audit --repo X     ← Einzelnes Repo (wie /repo-health-check, aber mit Infra)
```

**Zeitaufwand:**
- Quick: ~2 Minuten
- Vollständig: ~10 Minuten
- Mit GitHub Issues: ~15 Minuten

---

## Audit-zu-Action Pipeline

```
/platform-audit
    │
    ├─ CRITICAL → /hotfix (sofort)
    │
    ├─ HIGH → GitHub Issue + nächster Sprint
    │   └─ Architektur-Verstoß? → /adr prüfen
    │
    ├─ MEDIUM → GitHub Issue (Backlog)
    │   └─ Cross-Repo Pattern? → Platform-Template updaten
    │
    └─ LOW → Sammeln, bei Gelegenheit
```

---

*platform-audit v2.0 — Platform Coding Agent System | 2026-03-27*
