# ADR-146 Review: Package Consolidation Strategy (36 → 18)

> **Reviewer**: Principal IT-Architekt (Cascade)
> **Datum**: 2026-03-25
> **Scope**: ADR-146-package-consolidation-strategy.md
> **Methode**: Vollständiger Architektur-Review gegen Platform-Standards + ADR-Landschaft

---

## 1. Review-Tabelle

| # | Befund | Severity | Betroffene Stelle | Korrektur |
|---|--------|----------|-------------------|-----------|
| B1 | **Zählung falsch: 36 stimmt nicht** — bfagent-Packages (bfagent-core, bfagent-llm, chat-logging, chat-agent, creative-services) werden NICHT per pip installiert. Sie existieren in `platform/packages/` aber sind **nicht in bfagent requirements.txt**. `chat_agent` wird nur von bfagent (1 Import) und cad-hub (vendored) genutzt. `creative_services` wird nur von cad-hub/vendor/ genutzt. Tatsächliche Zählung ~31 aktive Packages. | **BLOCKER** | Section "Bestandsaufnahme", Tier 3 | Inventar korrigieren. bfagent-Packages separat kategorisieren als "platform/packages/ — nicht pip-installiert, intern genutzt". Ziel-Zahl anpassen (31 → ~16). |
| B2 | **ADR-027 Widerspruch**: ADR-027 entschied explizit "Option A — Modulare Packages in `platform/packages/`" und LEHNTE "Option B — Standalone PyPI / Ein Package mit Extras" AB (Zitat: "Monolith-Library mit shared Versionierung"). ADR-146 Tier 3 schlägt genau das Abgelehnte vor (`iil-platform` mit Extras). | **BLOCKER** | Tier 3, Section "Decision Outcome" | Entweder ADR-027 superseden (mit Begründung warum die Bewertung von damals nicht mehr gilt) oder Tier 3 anders lösen (z.B. namespace-packages statt Extras-Monolith). Frontmatter `supersedes: ["ADR-027"]` ergänzen. |
| K1 | **Import-Bruch platform_context → iil_platform**: risk-hub hat 20+ Imports `from platform_context.*` und `from django_tenancy.*`. Ein Rename zu `iil_platform` erzwingt **hunderte Import-Änderungen** in allen Consumer-Repos. Das ist kein "Compat-Redirect" — Python-Package-Imports können nicht per pip umgeleitet werden. | **KRITISCH** | Tier 3 "iil-platform" | Python-Import-Pfad MUSS `platform_context` bleiben (backward-compatible). Nur der pip-Name darf sich ändern. Oder: `iil-platform` installiert `platform_context` + `iil_commons` + `django_tenancy` als separate Namespace-Packages innerhalb eines Distributions-Package. |
| K2 | **nl2cad-core Extras funktionieren nicht mit Subpackages**: `pip install nl2cad-core[areas]` installiert nur Extra-Dependencies, aber NICHT den Code von `nl2cad.areas`. Extras steuern nur pip-Dependencies, nicht welche Python-Module mitgeliefert werden. Alle Subpackages werden IMMER mitinstalliert. | **KRITISCH** | Tier 2 "nl2cad → nl2cad-core[extras]" | Zwei Optionen: (A) Alles in nl2cad-core packen — Extras steuern nur Drittanbieter-Deps (lxml, spacy). Dann ist `[areas]` redundant (keine Extra-Deps). (B) Code in nl2cad-core belassen aber Subpackages per Lazy-Import mit ImportError → "install nl2cad-core[nlp]". Option A ist ehrlicher. |
| K3 | **Compat-Redirect für Python-Packages ist limitiert**: ADR behauptet "Zero Breaking Changes" durch Compat-Redirects. Aber: `nl2cad-areas 0.2.0` mit `requires = ["nl2cad-core[areas]"]` funktioniert nur für pip-Installation, nicht für Imports. Code der `from nl2cad.areas` importiert muss weiter funktionieren. Das geht NUR wenn der Code weiterhin unter `nl2cad.areas` installiert wird. | **KRITISCH** | Migration Plan, Compliance Notes | Compat-Redirect kann nicht Imports umleiten. Zwei Strategien: (1) Code bleibt unter gleichen Import-Pfaden, nur pip-Verteilung ändert sich. (2) Deprecation-Periode mit `import nl2cad.areas; warnings.warn("use nl2cad.core.areas")`. Strategie explizit dokumentieren. |
| H1 | **docs-agent, mcp-governance, inception-mcp als "Tooling" gezählt aber 0 Consumer-Repos**: Diese 3 sind interne Tools ohne Consumer in Hub-Repos. Sie sollten unter "Interne Tools" statt "Tooling Packages" laufen. `iil-mcp-governance` hat 0 pip-Installs außerhalb mcp-hub. | **HOCH** | Tooling-Kategorie | Separate Kategorie "Interne Platform-Tools (nicht pip-verteilt)" einführen. Nicht in Konsolidierungs-Zählung aufnehmen, da sie keine Consumer-Last erzeugen. |
| H2 | **riskfw hat ebenfalls nur 1 Consumer**: `riskfw==0.1.0` wird nur von risk-hub genutzt. Nach der eigenen Regel "1-Consumer-Packages gehören ins Consumer-Repo" müsste riskfw in risk-hub/ integriert werden (analog brandschutz-Migration). Rename zu `iil-riskfw` verschlimmert das Problem. | **HOCH** | Tier 4, Decision Drivers | Entscheiden: Entweder riskfw in risk-hub/src/ integrieren (konsequent) ODER die "1-Consumer"-Regel lockern auf "1-Consumer UND keine Wiederverwendungs-Absicht". Wenn riskfw perspektivisch für andere Hubs ist → dokumentieren. |
| H3 | **cad-hub vendored creative_services**: cad-hub hat `vendor/creative_services/` mit ~20 Files die `from creative_services.*` importieren. Das ist KEINE pip-Dependency sondern Copy-Paste. Wird durch ADR-146 nicht adressiert. | **HOCH** | Bestandsaufnahme fehlt | cad-hub vendor/ in Inventar aufnehmen. Entscheidung treffen: vendor-Copy löschen und auf iil-aifw migrieren, oder als cad-hub-intern akzeptieren. |
| H4 | **Keine Rollback-Strategie**: Was passiert wenn Phase 2 (nl2cad-Merge) fehlschlägt? Consumer haben bereits auf `nl2cad-core[areas]` umgestellt, alte Packages sind deprecated. | **HOCH** | Migration Plan | Pro Phase: Rollback-Bedingungen definieren. Alte Packages nicht deprecaten bevor ALLE Consumer erfolgreich migriert UND 1 Woche ohne Fehler. |
| H5 | **Fehlender Erfolgs-Metrik / Akzeptanz-Kriterien**: Wann ist die Konsolidierung "fertig"? Keine KPIs definiert. | **HOCH** | Fehlt komplett | Acceptance Criteria ergänzen: (1) 0 git+https in requirements.txt, (2) 0 Orphan-Packages auf PyPI, (3) Alle Hubs bauen mit pip install aus PyPI, (4) CI green auf allen Repos. |
| M1 | **iil-task-scorer nur in mcp-hub**: Hat exakt 1 Consumer (orchestrator_mcp). Sollte wie bfagent-Packages intern bleiben. | **MEDIUM** | Tooling-Kategorie | In "Interne Tools" verschieben. |
| M2 | **iil-content-store hat ADR-130 Referenz**: Bevor gelöscht, ADR-130 prüfen ob content-store dort als geplant/accepted gilt. Sonst ADR-130 ebenfalls superseden. | **MEDIUM** | Tier 1 Löschung | ADR-130 prüfen und ggf. Status auf "superseded" setzen. |
| M3 | **django-module-shop hat Migrations**: `django_module_shop` hat Django Migrations. Ein Merge in `iil-platform[shop]` muss sicherstellen dass bestehende Migrations-History nicht bricht (`MIGRATION_MODULES` oder SeparateDatabaseAndState). | **MEDIUM** | Tier 3 Platform-Merge | Explizit dokumentieren: Django-Apps mit Migrations behalten ihren `app_label`. Import-Pfad bleibt `django_module_shop`, nur pip-Verteilung ändert sich. |
| M4 | **Timeline unrealistisch**: 6 Wochen für 4 Phasen mit Cross-Repo Breaking Changes. Phase 3 allein (iil-platform) betrifft risk-hub (20+ Imports), coach-hub, billing-hub, wedding-hub. Realistischer: 3–4 Monate mit Puffer. | **MEDIUM** | Migration Plan Timeline | Timeline auf Quartals-Basis anpassen: Q2/2026 Phase 1+2, Q3/2026 Phase 3+4. |

---

## 2. Gesamturteil

### ❌ CHANGES REQUESTED

**2 Blocker, 3 Kritische Findings** müssen adressiert werden bevor ADR-146 akzeptiert werden kann.

### Kernprobleme

1. **Das Inventar ist ungenau** (B1) — Die Zählung "36" enthält Packages die nicht per pip installiert werden. Das untergräbt die Argumentation "50% Reduktion".

2. **ADR-027 Widerspruch** (B2) — Tier 3 schlägt genau das vor, was ADR-027 explizit ablehnte. Ohne Supersede-Erklärung ist das ein Governance-Bruch.

3. **Python-Imports ≠ pip-Names** (K1, K2, K3) — Die "Compat-Redirect"-Strategie funktioniert auf pip-Ebene, aber NICHT für Python-Imports. Das ist der kritischste technische Fehler im ADR.

### Was gut ist

- **Problem korrekt erkannt**: Zu viele Packages, Orphans, Naming-Chaos — das stimmt alles.
- **Phased Approach**: Tier 1 (Orphans) ist risikoarm und sofort machbar.
- **Consumer-Analyse**: Die Tabelle wer was nutzt ist wertvoll.

---

## 3. Empfohlene Alternativen

### Alternative für Tier 2 (nl2cad): Mono-Distribution, Multi-Namespace

Statt "Extras" → **ein Distribution-Package, alle Subpackages immer dabei**:

```toml
[project]
name = "nl2cad-core"
version = "0.2.0"
description = "NL2CAD — IFC/DXF, DIN 277, GAEB, NLP"

dependencies = []

[project.optional-dependencies]
gaeb = ["lxml>=5.0"]
nlp = ["spacy>=3.7"]
ifc = ["ifcopenshell>=0.8"]
```

- `pip install nl2cad-core` → installiert Core + Areas (keine Extra-Deps)
- `pip install nl2cad-core[gaeb]` → + lxml
- Import-Pfade bleiben: `from nl2cad.core import ...`, `from nl2cad.areas import ...`
- Kein Redirect nötig — alter Import funktioniert weiter

**Trade-off**: Package ist größer (enthält NLP-Code auch wenn nicht genutzt), aber:
- NLP-Code ohne spacy importiert → `ImportError` bei Nutzung
- Kein Import-Bruch
- Kein Redirect-Package nötig

### Alternative für Tier 3 (Platform): Umbrella-Package, Import-Pfade bleiben

```toml
[project]
name = "iil-platform"
version = "1.0.0"

dependencies = [
    "iil-platform-context>=0.5.1",
    "iil-django-commons>=0.3.0",
    "iil-django-tenancy>=0.1.0",
]

[project.optional-dependencies]
shop = ["iil-django-module-shop>=0.2.0"]
notifications = ["iil-platform-notifications>=0.1.0"]
```

- `iil-platform` ist ein **Umbrella-Package** (Meta-Package), KEIN Merge
- Import-Pfade bleiben: `from platform_context import ...`, `from iil_commons import ...`, `from django_tenancy import ...`
- Consumer installieren `iil-platform[shop]` statt 4 einzelne Packages
- Interne Packages werden weiter einzeln entwickelt + versioniert
- **Kein Breaking Change**, kein Import-Rewrite

**Trade-off**: Weniger Konsolidierung (Packages existieren weiter), aber:
- Zero Breaking Changes — wirklich, nicht nur behauptet
- Incremental adoption möglich
- Bei Bedarf später echter Merge machbar

---

## 4. Korrigiertes Inventar

### Aktive PyPI/pip-installierte Packages (tatsächlich ~28)

| # | Kategorie | Packages | Count |
|---|-----------|----------|-------|
| 1 | nl2cad | nl2cad, iil-nl2cadfw, nl2cad-core, nl2cad-areas, nl2cad-brandschutz, nl2cad-gaeb, nl2cad-nlp | 7 |
| 2 | AI/LLM | iil-aifw, iil-promptfw, iil-authoringfw | 3 |
| 3 | Platform (pip) | iil-platform-context, iil-django-commons, iil-django-tenancy, iil-django-module-shop, iil-platform-notifications | 5 |
| 4 | Domain FW | iil-learnfw, iil-weltenfw, iil-outlinefw, iil-researchfw, iil-illustrationfw, riskfw | 6 |
| 5 | Shared Tools | iil-testkit | 1 |
| | **Subtotal pip-distributed** | | **22** |

### Platform/packages/ — intern, nicht pip-distributed (6)

| Package | Genutzt von | Status |
|---------|-------------|--------|
| iil-bfagent-core | bfagent (intern) | Nicht per pip installiert |
| iil-bfagent-llm | bfagent (intern) | Nicht per pip installiert |
| iil-chat-agent | bfagent (1 import), cad-hub (vendored) | Nicht per pip installiert |
| iil-chat-logging | — | 0 Consumer |
| iil-creative-services | cad-hub (vendored) | Nicht per pip installiert |
| iil-content-store | — | 0 Consumer (ADR-130) |
| iil-platform-search | — | 0 Consumer |
| iil-cad-services | — | 0 Consumer |
| iil-task-scorer | orchestrator_mcp | Intern |
| iil-docs-agent | CLI-Tool | Intern |
| iil-mcp-governance | mcp-hub intern | Intern |
| iil-inception-mcp | mcp-hub intern | Intern |
| | **Subtotal intern** | **12** |

### Korrigierte Zählung

| | Vorher | Nachher (korrigiert) |
|---|--------|---------------------|
| pip-distributed | 22 | 14 |
| Intern/platform | 12 | 8 (Orphans weg) |
| **Gesamt** | **34** | **22** |
| **Reduktion** | | **−35%** |

---

## 5. Anhang: ADR-Konflikt-Matrix

| ADR | Beziehung zu ADR-146 | Aktion erforderlich |
|-----|----------------------|---------------------|
| ADR-022 | Stärkt Konsistenz → kein Konflikt | Keine |
| ADR-027 | **KONFLIKT** — lehnt Monolith-Package ab | **Supersede oder Tier 3 ändern** |
| ADR-028 | platform-context Architektur → betroffen | Prüfen ob Import-Pfade sich ändern |
| ADR-035 | django-tenancy Architektur → betroffen | Sicherstellen `django_tenancy` Import bleibt |
| ADR-044 | MCP Hub → nicht betroffen | Keine |
| ADR-050 | Hub Landscape → verstärkt | related hinzufügen |
| ADR-130 | content-store → wird gelöscht | **Supersede ADR-130** |
