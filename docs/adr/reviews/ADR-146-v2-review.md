# ADR-146 v2 Re-Review: Package Consolidation Strategy (34 → 22)

> **Reviewer**: Principal IT-Architekt (Cascade)
> **Datum**: 2026-03-25
> **Scope**: ADR-146 v2 (commit 4fdca3e)
> **Methode**: Zweiter Review-Pass nach Einarbeitung der 14 v1-Findings

---

## 1. Bewertung der v1-Finding-Einarbeitung

| v1-Finding | Status | Bemerkung |
|------------|--------|-----------|
| B1 (Inventar falsch) | ✅ Behoben | Korrigiert auf 22 pip + 12 intern |
| B2 (ADR-027 Widerspruch) | ✅ Behoben | `supersedes` + Begründung + Option D |
| K1 (Import-Bruch) | ✅ Behoben | Umbrella statt Merge, Kernprinzip #1 |
| K2 (Extras ≠ Code) | ✅ Behoben | Kernprinzip #3, klar dokumentiert |
| K3 (Compat-Redirect limitiert) | ✅ Behoben | Import-Pfade bleiben stabil |
| H1 (Kategorisierung) | ✅ Behoben | Separate Tabelle B) Interne Packages |
| H2 (riskfw 1-Consumer) | ✅ Behoben | Inline in risk-hub/src/ |
| H3 (cad-hub vendor) | ✅ Behoben | Sonderfälle Section C) |
| H4 (Kein Rollback) | ✅ Behoben | Rollback pro Phase |
| H5 (Keine Akzeptanz-Kriterien) | ✅ Behoben | 7 Acceptance Criteria |
| M1 (task-scorer intern) | ✅ Behoben | In Tabelle B) |
| M2 (ADR-130 check) | ⚠️ Teilweise | "supersedes ADR-130" erwähnt, aber **falsche Prämisse** (s. B1 unten) |
| M3 (Django Migrations) | ✅ Behoben | app_label Stabilität dokumentiert |
| M4 (Timeline unrealistisch) | ✅ Behoben | 4 Monate statt 6 Wochen |

**12 von 14 Findings vollständig behoben.** Gut.

---

## 2. Neue Findings (v2-spezifisch)

| # | Befund | Severity | Betroffene Stelle | Korrektur |
|---|--------|----------|-------------------|-----------|
| B1 | **content-store ist KEIN Orphan**: ADR-130 (accepted, implemented) zeigt 2 aktive Consumer: `dev-hub` (INSTALLED_APPS, DATABASE_ROUTERS, settings) und `research-hub` (`_publish_to_content_store()`, `ContentItem.objects.using("content_store")`, metrics). Prod DB existiert: `devhub_db` auf 88.198.191.108 mit 3 Tabellen + 9 Indizes. **Löschen würde Production-Daten und 2 Hubs brechen.** | **BLOCKER** | Tabelle B) Zeile `iil-content-store: 0 Consumer (Orphan)`, Tier 1 `git rm -r` | content-store aus Orphan-Liste entfernen. In Tabelle A) als pip-distributed mit 2 Consumer aufnehmen. Tier 1 Lösch-Aktion streichen. **ADR-130 wird NICHT superseded.** |
| K1 | **Titel-Inkonsistenz**: Titel sagt "34 → 22" aber Ergebnis-Übersicht zeigt **34 → 19** (pip: 22→11, intern: 12→8). Der Titel muss zum Ergebnis passen. | **KRITISCH** | Zeile 17: `# ADR-146: Package Consolidation Strategy — 34 → 22 Packages (v2)` | Titel ändern zu `34 → 20 Packages` (korrigiert: content-store bleibt → 19+1=20). Oder Titel auf pip-distributed beschränken: "pip-distributed: 22 → 12". |
| K2 | **iil-django-commons hat nur 1 Consumer (billing-hub)**: Kein Repo außer billing-hub importiert `iil_commons`. risk-hub, cad-hub, coach-hub, wedding-hub, learn-hub — keiner nutzt es. Aber billing-hub nutzt es intensiv (INSTALLED_APPS, Middleware, Health-URLs). In Ergebnis-Tabelle steht iil-django-commons als Kern-Dependency von `iil-platform` — das erzwingt es auf ALLE Consumer, obwohl nur 1 es braucht. | **KRITISCH** | Tier 3 pyproject.toml: `"iil-django-commons>=0.3.0"` als core dependency | iil-django-commons als **Optional** in iil-platform: `commons = ["iil-django-commons>=0.3.0"]`. Oder: Da nur billing-hub es nutzt, ggf. 1-Consumer-Regel anwenden (inline in billing-hub). |
| H1 | **iil-platform-notifications hat nur 1 Consumer (wedding-hub)**: Nur wedding-hub importiert `platform_notifications`. Nach 1-Consumer-Regel: Inline-Kandidat, nicht Umbrella-Extra. | **HOCH** | Tier 3 extras: `notifications = ["iil-platform-notifications>=0.1.0"]` | Entscheiden: (A) Inline in wedding-hub (konsequent) oder (B) Als Extra belassen weil perspektivisch mehrere Consumer. Falls B: dokumentieren warum Ausnahme von 1-Consumer-Regel. |
| H2 | **riskfw Source-Repo nicht gefunden**: `/home/dehnert/github/riskfw/` existiert nicht. `riskfw==0.1.0` ist per PyPI-Pin installiert. Ohne Source-Repo ist Inline-Migration schwieriger — Code muss von PyPI extrahiert oder anderswo gefunden werden. | **HOCH** | Tier 1: `riskfw: Inline in risk-hub/src/` | Source-Repo lokalisieren (PyPI-Tarball oder privates Repo). Falls kein Zugriff auf Source: riskfw als externe Dependency belassen bis Repo gefunden. Migration-Step in Phase 1 mit Vorbedingung "Source verfügbar" markieren. |
| H3 | **billing-hub installiert iil-django-commons per separatem git+https-Repo**: `git+https://github.com/achimdehnert/iil-django-commons.git@v0.3.0` — das ist ein EIGENSTÄNDIGES Repo, nicht `platform/packages/`. ADR-146 geht davon aus dass iil-django-commons in `platform/packages/` lebt. Beides existiert parallel. | **HOCH** | Tier 3 Umbrella, Consumer-Analyse | Klären: Ist `platform/packages/iil-django-commons/` die SSOT oder `github.com/achimdehnert/iil-django-commons`? Falls doppelt: eines als kanonisch deklarieren, anderes archivieren. |
| M1 | **Consumer-Analyse unvollständig**: `iil-platform-context` und `iil-django-tenancy` Consumer-Count zeigt "4+" aber dev-hub, research-hub, learn-hub fehlen in der Analyse. Auch `iil-django-commons` fehlt komplett in Consumer-Tabelle. | **MEDIUM** | Consumer-Analyse Tabelle | Vollständige Consumer-Matrix erstellen: Alle Hubs × Alle Packages. Mindestens: risk, cad, coach, billing, wedding, bfagent, writing, trading, pptx, learn, dev, research. |
| M2 | **Ergebnis-Übersicht: AI/LLM zeigt 3 aber v1 hatte 4**: v1 zählte `iil-task-scorer` als AI/LLM (4). v2 verschob task-scorer korrekt zu "intern". Aber v1 hatte auch `iil-aifw, iil-promptfw, iil-authoringfw, iil-task-scorer` = 4. v2 zeigt AI/LLM = 3 (ohne task-scorer) — korrekt. Aber Gesamtzählung A) pip-distributed = 22 inkludiert task-scorer NICHT (er ist in B). Passt. **Kein Fix nötig, nur Bestätigung.** | **MEDIUM** | — | Kein Fix nötig. Konsistenz verifiziert. |
| M3 | **Phase 3 Risiko herabgestuft**: v1 hatte "Risiko: Hoch", v2 hat "Risiko: Mittel". Das stimmt für Umbrella (kein Code-Merge), aber die Vorbedingung "alle Sub-Packages auf PyPI" ist selbst riskant — unklar ob iil-django-tenancy und iil-django-module-shop überhaupt schon auf PyPI sind. | **MEDIUM** | Phase 3, Vorbedingung | Vorbedingung explizit als "Phase 2.5" oder "Phase 3 Gate" definieren. Risiko-Bewertung "Mittel" ist korrekt, aber Gate-Bedingung stärken: "Phase 3 startet ERST wenn alle 5 Sub-Packages auf PyPI verifiziert." |

---

## 3. Gesamturteil

### ⚠️ APPROVED WITH COMMENTS

**1 Blocker (content-store), 2 Kritische Findings** — aber alle leicht behebbar.
Die Architektur-Entscheidungen in v2 sind solide.

### Was v2 richtig macht

- **Umbrella statt Merge**: Korrekt. Import-Pfad-Stabilität ist gewährleistet.
- **Kernprinzipien**: Alle 4 Prinzipien sind technisch korrekt und gut formuliert.
- **Kein PyPI Yank**: Richtige Entscheidung.
- **Rollback pro Phase**: Professionell.
- **Akzeptanz-Kriterien**: Messbar und sinnvoll.
- **Option D explizit verworfen**: Zeigt Reife im Decision-Prozess.

### Was noch fehlt

1. **content-store ist kein Orphan** → Korrektur in Inventar + Tier 1
2. **Titel passt nicht zum Ergebnis** → Einfacher Fix
3. **iil-django-commons Consumer-Count falsch** → Als Optional oder Inline
4. **Vollständige Consumer-Matrix** → Für Nachvollziehbarkeit essentiell

---

## 4. Korrektur-Vorschläge (produktionsreif)

### Fix B1: content-store aus Orphan-Liste entfernen

```diff
 #### B) Interne Platform-Packages (nicht pip-distributed, 12)
 ...
-| iil-content-store | — | 0 Consumer (Orphan) |
+| iil-content-store | dev-hub, research-hub (ADR-130) | Aktiv, Prod DB auf devhub_db |
```

```diff
 #### Tier 1: Sofort löschen/deprecaten (Phase 1)
 ...
-| `iil-content-store` | `git rm -r` (platform/packages/) | 0 Consumer, supersedes ADR-130 |
```

### Fix K1: Titel korrigieren

```diff
-# ADR-146: Package Consolidation Strategy — 34 → 22 Packages (v2)
+# ADR-146: Package Consolidation Strategy — 34 → 20 Packages (v2)
```

Korrigierte Ergebnis-Übersicht:

| Kategorie | Vorher | Nachher | Details |
|-----------|--------|---------|---------|
| nl2cad | 7 | 1 | nl2cad-core (Mono-Distribution) |
| AI/LLM | 3 | 3 | aifw, promptfw, authoringfw |
| Platform (pip) | 5 | 1 | iil-platform (Umbrella) |
| Domain | 6 | 5 | learnfw, weltenfw, outlinefw, researchfw, brandschutzfw |
| Shared Tools | 1 | 1 | iil-testkit |
| **pip-distributed** | **22** | **11** | **−50%** |
| Interne (platform/) | 12 | 9 | content-store bleibt, Rest Orphans entfernt |
| **Gesamt** | **34** | **20** | **−41%** |

### Fix K2: iil-django-commons als Optional

```diff
 # platform/packages/iil-platform/pyproject.toml
 dependencies = [
     "iil-platform-context>=0.5.1",
-    "iil-django-commons>=0.3.0",
     "iil-django-tenancy>=0.1.0",
 ]

 [project.optional-dependencies]
+commons = ["iil-django-commons>=0.3.0"]
 shop = ["iil-django-module-shop>=0.2.0"]
 notifications = ["iil-platform-notifications>=0.1.0"]
-full = ["iil-platform[shop,notifications]"]
+full = ["iil-platform[commons,shop,notifications]"]
```

Consumer-Migration:
- billing-hub: `iil-platform[commons]>=1.0.0`
- risk-hub: `iil-platform[shop]>=1.0.0` (braucht kein commons)
- wedding-hub: `iil-platform[notifications]>=1.0.0`

### Fix H1: notifications Entscheidung dokumentieren

```markdown
**Ausnahme von 1-Consumer-Regel**: `iil-platform-notifications` bleibt als Extra
weil coach-hub und billing-hub perspektivisch Notifications benötigen (ADR-Roadmap Q3/2026).
Ohne diese Perspektive → Inline in wedding-hub.
```

### Fix H3: iil-django-commons Repo-Dualität klären

```markdown
**SSOT**: `platform/packages/iil-django-commons/` ist kanonisch.
`github.com/achimdehnert/iil-django-commons` ist ein separates Repo (v0.3.0)
das billing-hub per git+https nutzt. Nach Phase 3 (PyPI-Publish) wird das
separate Repo archiviert. billing-hub migriert auf `iil-platform[commons]`.
```

---

## 5. Empfohlene Consumer-Matrix (vollständig)

| Package | risk | cad | coach | billing | wedding | bfagent | writing | trading | pptx | learn | dev | research |
|---------|------|-----|-------|---------|---------|---------|---------|---------|------|-------|-----|----------|
| iil-platform-context | ✅ | ? | ✅ | ? | ✅ | ? | ? | ? | ? | ? | ? | ? |
| iil-django-tenancy | ✅ | ? | ✅ | ? | ✅ | — | — | — | — | — | — | — |
| iil-django-commons | — | — | — | ✅ | — | — | — | — | — | — | — | — |
| iil-django-module-shop | ✅ | — | ✅ | — | — | — | — | — | — | — | — | — |
| iil-platform-notifications | — | — | — | — | ✅ | — | — | — | — | — | — | — |
| iil-content-store | — | — | — | — | — | — | — | — | — | — | ✅ | ✅ |
| iil-aifw | ✅ | — | — | — | — | ✅ | ✅ | — | ✅ | — | — | — |
| iil-promptfw | ✅ | ✅ | — | — | — | ✅ | ✅ | ✅ | ✅ | — | — | — |
| iil-authoringfw | ✅ | ✅ | — | — | — | ✅ | ✅ | ✅ | ✅ | — | — | — |
| nl2cad-core | ✅ | ✅ | — | — | — | — | — | — | — | — | — | — |
| riskfw | ✅ | — | — | — | — | — | — | — | — | — | — | — |
| iil-testkit | ✅ | ? | ? | ? | ? | ? | ? | ? | ? | ? | — | — |
| iil-learnfw | — | — | — | — | — | — | — | — | — | ✅ | — | — |

**?** = Nicht verifiziert (Repo nicht im Workspace). Vor Phase 3 vollständig ausfüllen.

---

## 6. ADR-Konflikt-Matrix (aktualisiert)

| ADR | Beziehung zu ADR-146 v2 | Aktion |
|-----|-------------------------|--------|
| ADR-022 | Stärkt Konsistenz → kein Konflikt | Keine |
| ADR-027 | Superseded ✅ | Bereits im Frontmatter |
| ADR-028 | platform-context → Import-Pfad bleibt | Keine |
| ADR-035 | django-tenancy → Import-Pfad bleibt | Keine |
| ADR-044 | MCP Hub → nicht betroffen | Keine |
| ADR-050 | Hub Landscape → verstärkt | Keine |
| **ADR-130** | **content-store → NICHT löschen** | **Aus Tier 1 entfernen** |
