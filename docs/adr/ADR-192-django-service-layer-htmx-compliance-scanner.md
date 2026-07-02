---
status: accepted
date: 2026-05-09
amended: 2026-05-10
decision-makers:
  - Achim Dehnert
reviewed-by:
  - Claude (Sparring Review, 2026-05-09)
depends-on:
  - ADR-191 (iil-codeguard Library-First Tooling)
  - ADR-048 (HTMX Playbook)
  - ADR-043 (Database-First Conventions)
  - ADR-057 (Four-Level Test Strategy)
repo: platform
consumers:
  - dev-hub
  - travel-beat
  - bfagent
  - risk-hub
  - weltenhub
  - wedding-hub
  - coach-hub
domains:
  - django/views
  - django/models
  - htmx
  - testing
implementation_status: verified
staleness_months: 6
last_reviewed: 2026-05-09
drift_check_paths:
  - "*/views.py"
  - "*/services.py"
  - "*/templates/**/*.html"
---

# ADR-192: Django Service-Layer and HTMX Template Compliance Scanner

> **Historie:** Frühere Abhängigkeit ADR-009 (Service Layer Architecture) ist archiviert (`docs/adr/archive/`) und wurde aus `depends_on` entfernt.

| Metadaten | |
|-----------|---|
| **Status** | Accepted (v1.1, amended 2026-05-10) — Implementation verified |
| **Datum** | 2026-05-09 (v1.0), 2026-05-10 (v1.1) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Claude (Sparring Review) |
| **Depends On** | ADR-191, ADR-009, ADR-048, ADR-043, ADR-057 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub |

---

## v1.0 → v1.1 — Empirisch validierte Änderungen

| Aspekt | v1.0 | v1.1 |
|--------|------|------|
| Service-Layer Check | View ruft `services.py`-Funktion auf? | **Inversion**: View enthält ORM-Zugriff? (beweisbar, CBV+async-kompatibel) |
| CBV-Support | Open Question | **Phase 1** (dev-hub 93%, weltenhub 88% CBV) |
| HTMX Pathological Case | nicht adressiert | **HX-009 Trip-Wire**: `{% %}` zwischen hx-Attributen detektieren |

## Context

ADR-009 mandates the three-tier pattern: `views.py` → `services.py` → `models.py`. ADR-048 mandates HTMX attributes: every element with `hx-*` must include `hx-target`, `hx-swap`, `hx-indicator`, and `data-testid`. These are the two most frequently violated platform rules — found in PR reviews across all 7 consumer repos.

**Current enforcement gap:**

| Rule | Enforcement | Gap |
|------|------------|-----|
| No ORM in views (ADR-009) | `platform-context` string-match on `.objects.`, `.filter(` | Misses: CBV-Methoden, async views, queryset chains via Variable |
| Service delegation (ADR-009) | Windsurf rules (agent instruction only) | Keine automatisierte Prüfung; in CBV strukturell nicht erfassbar |
| HTMX triple (ADR-048) | Windsurf rules | Templates werden nie systematisch gescannt |
| `data-testid` (ADR-048) | nicht geprüft | nirgends erfasst |

**Empirische Datenbasis (2026-05-10)**: Bei der Stakeholder-Validation wurden über 7 Consumer-Repos analysiert: 388 Views (davon 110 CBV, 6 async), 940 HTMX-Elemente (davon 399 mit Django-Tags im Attribut-Wert, 0 mit pathological case `{% %}` zwischen Attributen). Diese Zahlen begründen die konkreten Implementierungsentscheidungen unten.

## Decision

We implement two scanner modules in the `iil-codeguard` package (per ADR-191 v1.1):

### 1. Service-Layer Scanner (`SL-NNN` rules)

**Inversion (v1.1)**: Statt zu prüfen ob die View einen Service aufruft, wird strukturell erkannt, ob die View ORM-Zugriff enthält. Die Inversion ist robuster, weil:

- Abwesenheit von ORM ist beweisbar (AST-Suche findet Zugriffe deterministisch)
- Anwesenheit von Service-Calls ist nicht beweisbar (Aliase, Mixins, dynamische Dispatch verhindern Match)
- CBV-Methoden (`form_valid`, `dispatch`, `get_queryset`) und async views funktionieren nativ

**Implementation**:

```python
class ORMDetector(ast.NodeVisitor):
    def visit_Attribute(self, node):
        # Detect: SomeModel.objects.* (manager access)
        if isinstance(node.value, ast.Name) and node.attr == "objects":
            self.violations.append(...)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):  # async views supported nativ
        self.generic_visit(node)
```

Empirisch validiert: erkennt korrekt `World.objects.create(...)` in `WorldCreateView.form_valid` (CBV) UND `await Trip.objects.aget(...)` in async FBV.

**Violation types (Phase 1):**

| ID | Severity | Description |
|----|----------|-------------|
| `SL-001` | error | View enthält `Model.objects.*` (ORM access) |
| `SL-002` | error | View enthält `transaction.atomic()` (transaction handling gehört in services) |
| `SL-003` | warning | View enthält `select_related`/`prefetch_related` (queryset chains) |
| `SL-004` | warning | View importiert Model direkt (Bypass-Risiko) |
| `SL-005` | error | View enthält rohe SQL (`connection.cursor()`, `raw()`) |
| `SL-006` | info | App hat Views aber keine `services.py` |

### 2. HTMX Template Scanner (`HX-NNN` rules)

**Tooling-Wahl (v1.1)**: Empirischer Test mit 940 HTMX-Elementen aus 7 Repos zeigt: `html.parser` aus stdlib funktioniert korrekt mit Django-Tags innerhalb Attribut-Werten (`hx-get="{% url 'foo' %}"` — der häufige Fall, 399 Vorkommen). Der pathologische Fall (`{% if %}` zwischen Attributen) kommt **0 mal** vor. Wir bleiben bei `html.parser` für Phase 1, ergänzen aber **HX-009** als Trip-Wire um zu verhindern, dass das Pattern still einzieht.

**Analysis approach** (`html.parser` + Pre-Scan-Regex):

1. Pre-Scan per Regex: erkennt `\{%[^%]+%\}\s+hx-` zwischen Attributen → HX-009
2. Recursive find aller `.html` Files in `templates/`
3. Parse mit `html.parser`, find elements mit `hx-*` attribute
4. Per Element verify required attributes + banned patterns

**Violation types:**

| ID | Severity | Description |
|----|----------|-------------|
| `HX-001` | error | HTMX element missing `hx-target` |
| `HX-002` | error | HTMX element missing `hx-swap` |
| `HX-003` | warning | HTMX element missing `hx-indicator` |
| `HX-004` | warning | HTMX element missing `data-testid` |
| `HX-005` | error | `hx-boost` used (banned by ADR-048) |
| `HX-006` | error | `onclick=` mixed with `hx-*` |
| `HX-007` | info | `hx-post` form without `{% csrf_token %}` in parent |
| `HX-008` | error | Partial template contains `{% extends %}` (should be fragment) |
| `HX-009` | error | Django template tag (`{% %}`) between HTMX attributes — html.parser kann nicht zuverlässig parsen, Pattern muss in `{% if %}`-Block um das gesamte Element verschoben werden |

**HX-009 Rationale**: Bei 0 aktuellen Vorkommen ist die Rule eine reine Trip-Wire. Sollte das Pattern eingeführt werden, schlägt der Linter sofort an, bevor stille false-negatives entstehen können.

## Consequences

### Positive
- Catches the #1 and #2 most common PR review findings automatically
- Zero-dependency implementation (stdlib `ast` + `html.parser`)
- Violation IDs (`SL-001`, `HX-001`) create a shared vocabulary for team communication
- Directly usable in `/pr-review` workflow: "2 SL-001 violations found → [BLOCK]"
- Template scanner works on any HTML — not Django-template specific

### Negative
- AST analysis cannot follow dynamic dispatch (e.g., `getattr(model, 'objects')`)
- `html.parser` parsed `{% if %}` zwischen Attributen falsch — durch HX-009 Trip-Wire abgesichert
- Template inheritance (`{% include %}`, `{% block %}`) macht partial analysis incomplete — bewusst akzeptiert für Phase 1
- Mixins über mehrere Files können nicht vollständig erfasst werden (cross-file analysis Phase 2)

## Alternatives Considered

1. **pylint/flake8 custom plugin** — Tied to linter ecosystem, harder to integrate with MCP. AST approach is more flexible.
2. **Semgrep rules** — Powerful but adds a heavy dependency. Custom `ast` analysis is simpler for our specific patterns.
3. **Manual checklists in PR template** — Current approach. Does not scale, easily overlooked.
4. **Django system check framework** — Runs at startup, not at PR review time. Cannot check templates.

## Implementation Priorities

| Priority | Check | Expected findings (7 Consumer-Repos) |
|----------|-------|--------------------------------------|
| P0 | `SL-001` ORM in views (CBV+FBV+async) | 50-150 violations |
| P0 | `HX-001/002` Missing hx-target/hx-swap | 20-40 violations |
| P0 | `HX-009` Pathological {% %} between attrs | 0 expected (trip-wire) |
| P1 | `SL-002` `transaction.atomic` in views | 5-15 violations |
| P1 | `HX-003/004` Missing indicator/testid | 200-400 violations |
| P2 | `HX-005` hx-boost usage | 0-5 violations |
| P2 | `SL-003/004` queryset chains / model imports | 20-50 violations |

## Glossar

- **AST** — Abstract Syntax Tree (strukturelle Code-Repräsentation in Python's `ast` Modul)
- **CBV** — Class-Based View (Django, z.B. `CreateView`, `UpdateView`)
- **FBV** — Function-Based View (Django, `def my_view(request)`)
- **HTMX** — Frontend-Library für AJAX via HTML-Attribute
- **Inversion (Check-Logik)** — "View enthält ORM" prüfen (beweisbar) statt "View ruft Service" prüfen (nicht beweisbar)
- **Trip-Wire** — Linter-Rule mit erwarteter 0-Trefferzahl, die anschlägt wenn Pattern eingeführt wird
