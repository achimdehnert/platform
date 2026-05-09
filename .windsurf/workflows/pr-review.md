---
description: Review and address PR comments using GitHub MCP
---

# PR Review Workflow

**Trigger:** User sagt eines von:
- "Review PR #XX"
- "PR-Kommentare adressieren für #XX"
- "Code Review machen für [branch]"

---

## Step 1: PR-Kontext laden

```
1. docs/CORE_CONTEXT.md — Architektur-Constraints prüfen
2. PR-Beschreibung + Diff lesen
3. Verknüpfte Issues + ADRs lesen
```

GitHub MCP: `mcp_github_get_pull_request` mit owner/repo/pull_number.

---

## Step 1.5: ADR Impact + Compliance Check (automatisch)

> Nutzt `iil-adrfw` MCP Tools (Prefix aus project-facts.md, aktuell `mcp2_`).

Für **jede geänderte Datei** im PR:

```
MCP: mcp2_adr_impact(file_path="<datei>", repo="<repo>")
→ Zeigt welche ADRs für diese Datei gelten
```

Bei Dateien mit ADR-Treffern → Code gegen Rules prüfen:

```
MCP: mcp2_adr_check(paths=["<datei1>", "<datei2>"], severity_threshold="warning")
→ Liefert: Violations mit rule_id, severity, expected vs. actual
```

Jede Violation mit severity ≥ error → `[BLOCK]` im Review.

### Step 1.6: Cross-Repo Validation (nur bei ADR-Änderungen)

Wenn der PR **ADR-Dateien** (`docs/adr/ADR-*.md`) enthält:

```
MCP: mcp2_adr_validate_cross_repo(
  adr_id="<geändertes_ADR>",
  consumer_repos=[
    {name: "<repo1>", root: "${GITHUB_DIR}/<repo1>"},
    {name: "<repo2>", root: "${GITHUB_DIR}/<repo2>"}
  ]
)
→ Prüft ob der ADR-Inhalt mit dem tatsächlichen Code in Consumer-Repos übereinstimmt
→ blocks_publish=true bei HIGH-Confidence Konflikten → [BLOCK] im Review
```

Wenn der PR **docker-compose/requirements** ändert:
```
MCP: mcp2_adr_freshness(repo_path="${GITHUB_DIR}/<repo>")
→ Prüft ob sich durch die Änderung neue ADR-Drifts ergeben
→ z.B. PostgreSQL-Upgrade in compose → ADR-022 sagt noch "PostgreSQL 15"
→ Findings als [SUGGEST] im Review: "ADR-022 aktualisieren"
```

---

## Step 2: Review-Kriterien (Checkliste)

### Architektur & Patterns

- [ ] Service Layer korrekt? (`views.py` → `services.py` → `models.py`)
- [ ] Keine Businesslogik in `views.py`?
- [ ] `DEFAULT_AUTO_FIELD = BigAutoField` — keine UUIDs als PK?
- [ ] Templates in `templates/<app>/` (nicht per-app)?
- [ ] HTMX: `request.htmx` (nicht raw header check)?
- [ ] ADR-Compliance: `mcp2_adr_check` zeigt keine Violations?

### Code-Qualität

- [ ] Imports an oberster Stelle?
- [ ] Keine hard-codierten Secrets / Credentials?
- [ ] Error Handling vorhanden wo nötig?
- [ ] Keine SQL-Injection-Vektoren (ORM oder parameterisiert)?

### Tests

- [ ] Tests vorhanden? (`test_should_*` Naming)
- [ ] Happy Path + mindestens 1 Edge Case?
- [ ] Bei Bug Fix: Regression Test (`test_should_not_*`)?
- [ ] Coverage nicht gesunken?

### Deployment

- [ ] Migrations vorhanden wenn Model geändert?
- [ ] Neue Env-Variablen in `.env.example` dokumentiert?
- [ ] `docker-compose.prod.yml` aktuell wenn Services geändert?
- [ ] Breaking Changes? (→ erst deprecaten per Platform-Convention)

---

## Step 3: Review-Kommentare schreiben

Format für konstruktives Feedback:

```
[BLOCK] — Muss geändert werden vor Merge
[SUGGEST] — Empfehlung, nicht zwingend
[QUESTION] — Klärungsbedarf
[NITS] — Kleinigkeit, optional
```

Beispiel:
```
[BLOCK] Businesslogik in views.py — bitte in services.py auslagern (ADR-041)
[SUGGEST] test_should_return_404_when_book_not_found wäre hier sinnvoll
[NITS] Leerzeile nach Imports fehlt
```

GitHub MCP: `mcp_github_create_review` mit dem Review-Body.

---

## Step 4: Kommentare adressieren (als Autor)

Wenn eigene PR-Kommentare zu adressieren sind:

1. Jeden `[BLOCK]` sofort fixen — kein Merge ohne
2. Jeden `[SUGGEST]` bewerten: übernehmen oder begründet ablehnen
3. Nach Fix: Kommentar mit "Fixed in [commit-sha]" beantworten
4. Re-Review anfordern: `mcp_github_request_review`

---

## Step 5: Merge-Entscheidung

**Merge wenn:**
- [ ] Alle `[BLOCK]`-Kommentare resolved
- [ ] CI-Checks grün
- [ ] Mind. 1 Approval
- [ ] Keine unresolvten Kommentare

**Merge-Strategie:**
- Features → Squash & Merge
- Releases / Hotfixes → Merge Commit
- Kein Rebase auf main

---

## Referenz: Häufige Review-Patterns

| Anti-Pattern | Korrekt | ADR |
|---|---|---|
| Logic in views | services.py | Platform Convention |
| UUID PK | BigAutoField | Platform Convention |
| `import anthropic` | llm_mcp tools | ADR-082 |
| HEALTHCHECK im Dockerfile | docker-compose.prod.yml | ADR-022 |
| `${VAR}` in compose env | env_file: .env.prod | Platform Convention |
| Hardcoded secrets | decouple.config() | Security |
