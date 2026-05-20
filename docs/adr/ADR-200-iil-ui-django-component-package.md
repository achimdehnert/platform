---
id: ADR-200
title: "iil-ui v1 (Draft, superseded by v2)"
status: superseded-draft
date: 2026-05-14
note: "v1 wurde von v2 abgelöst nach advocatus-diaboli Review — siehe ADR-200 v2 unten in derselben Datei."
---

# ADR-200 v1 — superseded by v2 (siehe unten)

Die ursprüngliche v1-Version mit Token-Override + Tailwind-Safelist wurde nach interner advocatus-diaboli Review verworfen, weil:

| # | Schwäche v1 | Schwere |
|---|---|---|
| 1 | Safelist-Distribution und Per-Consumer-Theming sind physikalisch inkompatibel | **blocker** |
| 2 | Tailwind-Strings in Komponenten-Templates verschieben Hardcoding nur eine Ebene | **blocker** |
| 3 | JIT-Cross-Package-Scanning ohne Tailwind-Plugin nicht robust | **blocker** |
| 4 | TTZ/LRA-Datensouveränität / Public-PyPI für government-Repos ungeprüft | **blocker** |
| 5 | Pilot→Extraktion ohne messbares Decision-Gate | hoch |
| 6 | Schema-Klassen (Phase 2) vermischen zwei Architektur-Entscheidungen in einer ADR | hoch |
| 7 | Print-Layout-Component verkennt WeasyPrint-vs-Browser-Paradigma-Unterschied | hoch |
| 8 | DaisyUI als sofort verfügbare 80%-Lösung gar nicht evaluiert | hoch |
| 9 | Web Components vs. Server-Templates trade-off nicht analysiert | hoch |
| 10 | Cross-Hub-Coordination-Pattern bei semver-Bumps fehlt | mittel |
| 11 | Backwards-compat / Contract-Tests (ADR-184) nicht referenziert | mittel |
| 12 | HTMX-Friendliness behauptet, nicht spezifiziert | mittel |

Diese Schwächen sind nicht durch v1-Iteration heilbar — sie folgen aus der Grundentscheidung „Tailwind-Utility-Strings als Komponenten-Output". Daher v2 mit anderer Architektur.

---

---
id: ADR-200
title: "iil-ui v2 — CSS-Layer + Django Tags + Optional Web Components"
status: paused-pending-second-consumer
date: 2026-05-14
paused_date: 2026-05-14
paused_reason: "YAGNI-Audit über 24 Hubs zeigt: 94 % der UI-Pattern-Hits in risk-hub, nur 1 weiterer Hub (dev-hub) mit ≥3 Patterns. Cross-Hub-Library-Investment derzeit unproportional. ADR reaktivieren, sobald (a) dev-hub-Team konkreten Bedarf signalisiert ODER (b) ein dritter Hub UI-Aktivität mit Pattern-Overlap aufbaut."
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: []
informed: [risk-hub, dev-hub]
scope: bei Reaktivierung — Django-Hub-Repos mit nachgewiesener Pattern-Overlap (aktuell nur risk-hub + dev-hub)
tags: [ui, django, tailwind, htmx, components, shared-package, pypi, css-layer, web-components, progressive-enhancement, paused, yagni]
related: [ADR-022, ADR-035, ADR-100, ADR-111, ADR-133, ADR-147, ADR-184, ADR-196, ADR-199]
supersedes: []
amends: []
implementation_status: paused
---

# ADR-200 v2: iil-ui — CSS-Layer + Django Template Tags + Optional Web Components

> **⚠️ Status: PAUSED (2026-05-14)**
>
> ADR-200 v2 wurde nach **YAGNI-Audit über 24 Hub-Repos** auf `paused-pending-second-consumer` gesetzt. Datenlage:
>
> | Metrik | Wert |
> |---|---|
> | Hubs mit allen 5 untersuchten UI-Patterns | **2** (risk-hub, dev-hub) |
> | Hubs mit ≥3 Patterns | 6 |
> | UI-marginale Hubs (<5 Templates) | 11 |
> | Pattern-Hits Verteilung | **risk-hub 745 (81 %), dev-hub 171 (19 %)**, Rest <1 % |
>
> **Schlussfolgerung:** Die UI-Drift ist nicht „Cross-Hub", sondern **risk-hub-internal + ein zweiter Hub**. Ein Shared-Package mit semver-Coordination, npm + PyPI-Distribution und 3-Layer-Architektur ist für dieses Volumen unproportional.
>
> **Stattdessen umgesetzt (Pfad A):** risk-hub-lokale Konsolidierung in `risk-hub/src/core/components/`. Keine Shared Library. Kein PyPI-Package. CHANGELOG-Eintrag im Repo statt ADR (per `policies/adr-threshold.md`: „local to one repo with no public surface").
>
> **Reaktivierungs-Bedingungen** (jede für sich ausreichend):
> 1. dev-hub-Team signalisiert konkret Bedarf, risk-hub-Komponenten zu konsumieren.
> 2. Ein dritter Hub baut UI-Aktivität auf mit Pattern-Overlap ≥3.
> 3. risk-hub-lokale Komponenten haben 6+ Monate API-Stabilität und nachweislichen Drift-Reduktions-Effekt.

---

## Original ADR-200 v2 Content (paused, zur Referenz erhalten)

| Field | Value |
|-------|-------|
| **Status** | Proposed (v2 nach advocatus-diaboli Review der v1) |
| **Datum** | 2026-05-14 |
| **Autor** | Achim Dehnert |
| **Scope** | alle Django-Hub-Repos mit server-rendered Tailwind+HTMX-UI |
| **Pilot** | risk-hub (DSB-Modul) — `src/core/components/`, nicht `src/dsb/components/` |
| **Follows** | ADR-035 (shared-django-tenancy), ADR-100 (iil-testkit), ADR-133 (shared-ai-services), ADR-184 (contract-testing-strategy) |
| **Successor zu** | ADR-111 superseded — eigenständiger Repo + PyPI ist neue Norm |

---

## 1. Kontext und Problemstellung

Die Platform betreibt **mehrere Django-Hubs** mit gleichem Stack (Django + Tailwind + HTMX, server-rendered): risk-hub, ttz-hub, meiki-hub, bfagent, travel-beat, coach-hub, billing-hub, gbu-hub, weltenhub.

**Drift-Symptome** (aus Audit risk-hub 2026-05-14):
- Duplikate innerhalb eines Repos: `src/templates/components/_stat_card.html` UND `src/templates/dsb/components/_stat_card.html`.
- Tailwind-Klassen-Hardcoding in Page-Templates (`text-blue-600`, `bg-yellow-100` in jedem Listen-Template).
- Hardcoded Visual-Divider (`<span class="w-px h-4 bg-gray-300">`) als Pflaster zwischen Action-Icons — Symptom fehlender Komponente.
- Accessibility: `title=` statt `aria-label`, keine konsistenten Focus-States.
- Print-CSS hardcodiert in jedem PDF-Template (30 Zeilen `<style>` in `doku/print.html`).

Die advocatus-diaboli Review der v1 hat zusätzlich gezeigt:
- Tailwind-Utility-Strings als Komponenten-Output **brechen Per-Tenant-Theming** (Safelist-vs-Override-Konflikt).
- Print (WeasyPrint, kein JS) und Interactive (Browser, JS) sind **fundamental getrennte Render-Targets** und brauchen unterschiedliche Architektur-Wege.
- DaisyUI deckt ~60% des Bedarfs out-of-the-box ab, wurde in v1 ignoriert.

## 2. Decision

`iil-ui` ist **kein Tailwind-Wrapper**, sondern eine **3-Layer-Architektur** mit klarer Trennung zwischen visuellem Vertrag (CSS), Server-Rendering (Django) und optionaler Interaktivität (Web Components):

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 3 (optional, opt-in pro Komponente):                              │
│  iil-ui-elements — Vanilla Web Components für Interactive-Only-Behavior │
│  → Keyboard-Nav, Focus-Trap, ARIA-Live, Roving Tabindex                 │
│  → Progressive Enhancement: HTML aus L2 funktioniert ohne L3            │
│  → Nicht im Print-Pfad; WeasyPrint ignoriert <script>                   │
└──────────────────────────────────────────────────────────────────────────┘
                          ▲ enhances
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 2: iil-ui-django — Django-App mit Template-Tags                   │
│  → {% icon_action %}, {% action_group %}, {% data_table %} …            │
│  → Emit semantische CSS-Klassen aus Layer 1, KEINE Tailwind-Strings      │
│  → HTMX-Attribute (hx-target, hx-swap) als Tag-Parameter                 │
│  → Funktioniert in WeasyPrint, ohne JS, mit HTMX                         │
└──────────────────────────────────────────────────────────────────────────┘
                          ▲ uses
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 1: iil-ui-css — CSS-Layer-Bibliothek (npm + Tailwind-Plugin)      │
│  → Semantische Klassen: .iil-icon-action, .iil-status-badge—success     │
│  → Theming via CSS Custom Properties: --iil-color-primary-600           │
│  → Tailwind-Plugin: registriert Klassen über addComponents()             │
│  → Optional als pures CSS-File für non-Tailwind-Konsumenten              │
└──────────────────────────────────────────────────────────────────────────┘
                          ▼ basiert auf
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 0: Tailwind (im Consumer-Repo, unverändert)                       │
│  → Layout-Utilities (grid, flex, mb-*, p-*) bleiben Page-Templates       │
│  → Theme-Werte (colors, spacing) werden von iil-ui-css aus Custom Props  │
│    gelesen — Consumer kann sie via Tailwind-Config setzen                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Layer 1 — iil-ui-css (CSS-Layer + Tailwind Plugin)

**Form**: npm-Package `@iil/ui-css` + optional pures CSS-File für non-npm-Konsumenten.

**Liefert**:
```css
/* Klassen, die Komponenten in Layer 2 emittieren */
.iil-icon-action {
    display: inline-flex; padding: 0.375rem; border-radius: 0.375rem;
    color: var(--iil-color-text);
    transition: background-color 150ms;
}
.iil-icon-action--primary { color: var(--iil-color-primary-600); }
.iil-icon-action--primary:hover { color: var(--iil-color-primary-800); }
.iil-icon-action--danger { color: var(--iil-color-danger-600); }
/* … */
```

**Theming-Vertrag**: nur über CSS Custom Properties, **nie über Tailwind-Klassen-Strings**.

```css
/* Default-Theme im Package */
:root {
    --iil-color-primary-600: theme('colors.indigo.600');
    --iil-color-primary-800: theme('colors.indigo.800');
    --iil-color-danger-600:  theme('colors.red.600');
    /* … */
}
```

```css
/* ttz-hub override im Consumer-CSS (eine Datei) */
:root {
    --iil-color-primary-600: theme('colors.emerald.600');
}

/* meiki-hub */
:root {
    --iil-color-primary-600: theme('colors.sky.700');
}
```

**Tailwind-Plugin** registriert die Klassen via `addComponents()` — Standard-Pattern wie DaisyUI / Tailwind-UI. Kein Safelist-Drama, kein cross-package-Scanning, JIT-kompatibel.

### 2.2 Layer 2 — iil-ui-django (Template Tags)

**Form**: PyPI-Package `iil-ui-django` (Django Reusable App).

**Liefert**:
```django
{% load iil_components %}

{% page_header icon="building-2" title="Mandate" %}
    {% button url=create_url icon="plus" label="Neu" variant="primary" %}
{% endpage_header %}

{% action_group %}
    {% icon_action url=edit_url icon="pencil" label="Bearbeiten" variant="primary" %}
    {% icon_action url=delete_url icon="trash-2" label="Löschen" variant="danger" %}
{% endaction_group %}
```

**Emit ist semantisches HTML mit CSS-Layer-Klassen**:
```html
<div class="iil-action-group" data-iil-component="action-group" role="toolbar">
    <a href="…" class="iil-icon-action iil-icon-action--primary"
       aria-label="Bearbeiten">
        <svg>…</svg>
    </a>
    <a href="…" class="iil-icon-action iil-icon-action--danger"
       aria-label="Löschen">
        <svg>…</svg>
    </a>
</div>
```

**Keine Tailwind-Klassen im Komponenten-Output.** Theming und Variantes ausschließlich über `iil-*`-Klassen aus Layer 1.

**HTMX-Integration** als first-class Tag-Parameter:
```django
{% icon_action url=delete_url icon="trash-2" label="Löschen" variant="danger"
   hx_target="#mandates-table" hx_swap="outerHTML" hx_confirm="Sicher?" %}
```

### 2.3 Layer 3 — iil-ui-elements (Web Components, optional)

**Form**: npm-Package `@iil/ui-elements`, Vanilla Custom Elements (kein Lit-Framework — Lit ist 5kB, Vanilla 0kB).

**Liefert**: opt-in Behavior-Upgrades für Komponenten, die Interaktion brauchen:
- `<iil-action-group>` → Roving-Tabindex, Keyboard-Nav, ARIA-Live bei Aktion
- `<iil-data-table>` → Sort/Filter ohne Page-Reload
- `<iil-confirm-form>` → Custom Dialog statt `confirm()`-Browser-Popup

**Progressive Enhancement-Vertrag**:
- HTML aus Layer 2 muss **ohne Layer 3 funktional und visuell vollständig** sein.
- Layer 3 ist Anreicherung, niemals Voraussetzung.
- Layer 3 wird **nicht** im Print-Pfad geladen (WeasyPrint ignoriert `<script type="module">`).

**Activation pro Komponente**:
```django
{% action_group enhance="iil-action-group" %}
    …
{% endaction_group %}
```

→ rendert `<div is="iil-action-group">` oder `<iil-action-group>` (autonomes Custom Element). Ohne `enhance=`-Param: plain HTML.

### 2.4 Was NICHT in iil-ui gehört

| Out-of-scope | Wo es hingehört |
|---|---|
| Page-Templates (`mandate_list.html`, `vvt_form.html`, …) | Consumer-Repo |
| Komponenten mit Domänen-Logik (VVT-Editor, DSGVO-Check) | Modul im Consumer-Repo |
| **Print-Layout-Component** (war v1, jetzt rausgecuttet) | Eigenes Package `iil-print` oder Consumer-lokal — siehe ADR-202 (TBD) |
| **Schema-Klassen** (PageSpec/DataTable, war v1 Phase 2) | Eigener ADR-201 (TBD) — andere Architektur-Entscheidung |
| Authentication / Tenancy | ADR-035 |
| Routing / Forms | Django selbst |

**Bewusste Scope-Reduktion gegenüber v1.** v2 entscheidet **eine** Sache: 3-Layer-Komponenten-Architektur. Schema-Klassen und Print-Engine sind eigene Entscheidungen.

## 3. Distribution

Zwei Packages, getrennt versioniert, gemeinsam dokumentiert:

| Package | Distribution | Versionierung | Consumer |
|---|---|---|---|
| `@iil/ui-css` | npm-Public (npmjs.com) | semver | Tailwind-Build im Consumer-Hub |
| `iil-ui-django` | PyPI-Public (wie iil-testkit) | semver | Django `INSTALLED_APPS` im Consumer-Hub |
| `@iil/ui-elements` | npm-Public (optional) | semver | nur Hubs, die L3 wollen |

**Coordination-Pattern**:
- `iil-ui-django` MAJOR muss zu `@iil/ui-css` MAJOR kompatibel sein (gleicher Class-Vertrag).
- README listet kompatible Versions-Matrix (wie `Django` + `django-rest-framework`).
- CI im iil-ui-Monorepo (siehe 3.1) testet Cross-Package-Kompatibilität.

### 3.1 Monorepo statt 3 Einzelrepos

Trotz getrennter Distribution: **ein** Git-Repo `achimdehnert/iil-ui` mit drei Packages (pnpm-workspaces + uv-workspace). Begründung:
- Atomic Cross-Package-Refactor möglich (CSS-Klasse umbenennen = ein Commit, kein Sync-PR).
- Ein Versions-Manifest, ein CHANGELOG.
- Folgt Pattern von `iil-adrfw` (auch Monorepo mit Tooling + Lib).

### 3.2 Tailwind-Plugin vs. Safelist

**Tailwind-Plugin-Pattern** (Industry-Standard, DaisyUI, Tailwind-UI):
```js
// Consumer-Repo tailwind.config.js
module.exports = {
    content: ["./src/templates/**/*.html"],
    plugins: [require("@iil/ui-css/tailwind-plugin")],
};
```

Plugin registriert Klassen via `addComponents()` → JIT findet sie zur Compile-Time → keine Safelist nötig, kein Cross-Package-Pfad-Scanning, kein Bloat.

**Safelist als Fallback** für non-Tailwind-Konsumenten: `@iil/ui-css/dist/iil-ui.css` als fertige CSS-Datei.

## 4. Compliance / Data Sovereignty (TTZ + LRA)

Public PyPI/npm-Distribution wurde geprüft gegen:
- **TTZ (ttz-lif)**: government workloads. UI-Komponenten haben keinen Datenfluss → public-OK. Lizenz: MIT (kompatibel mit BMI-Open-Source-Strategie). Hosting auf PyPI/npm: Code-Ebene, keine Daten — keine DSGVO-Implikation.
- **LRA (meiki-lra)**: citizen-facing. Gleiche Argumentation. Zusätzlich: A11y-Konformität nach BITV 2.0 in Komponenten-Tests verpflichtend (siehe §5 Decision Gate).
- **Supply Chain**: `iil-ui-*` wird via GitHub Actions mit OIDC-Trusted-Publisher signiert (PyPI/npm), Consumer pinnen via Hash:
  ```
  iil-ui-django==0.3.0 --hash=sha256:…
  ```

Falls künftig sensitive Komponenten entstehen (z.B. Form-Components mit PII-Validierung): eigenes private Package `iil-ui-gov` auf GitHub Packages (private), mit OIDC-Auth pro Consumer-Repo.

## 5. Pilot Plan & Decision Gate

| # | Schritt | Repo | Akzeptanzkriterium (messbar) |
|---|---|---|---|
| 1 | Layer-1-CSS-Klassen + Layer-2-Tags in risk-hub **lokal** bauen | `risk-hub/src/core/components/` *(repo-weit, NICHT `src/dsb/components/`)* | a) `mandate_list.html` enthält 0 `text-{color}-*`, `bg-{color}-*` Klassen außerhalb Layout-Utilities; b) `_overview_row.html` benutzt `{% status_badge %}`; c) CI grün; d) Playwright-Smoke aller DSB-Listen grün |
| 2 | Theming-Beweis | risk-hub | Token-Override im DEBUG-Modus erzeugt erkennbar anderes Erscheinungsbild — Snapshot-Diff |
| 3 | A11y-Check | risk-hub | `pa11y-ci` auf `mandate_list` und `doku/overview` ohne Errors (BITV 2.0 / WCAG 2.1 AA) |
| 4 | **Decision Gate A → Extraktion ja/nein** | risk-hub | Alle 3 erfüllt: (i) ≥6 Komponenten implementiert (action_group, icon_action, status_badge, empty_state, page_header, alert_banner), (ii) 14 Kalendertage ohne Breaking Change am Komponenten-Vertrag, (iii) ≥1 zweites Modul (gbu oder brandschutz) hat ≥1 Komponente erfolgreich konsumiert |
| 5 | Extraktion `achimdehnert/iil-ui` v0.1.0 | iil-ui Monorepo | npm + PyPI Publish, OIDC signed |
| 6 | risk-hub als erster Consumer | risk-hub | `pip install iil-ui-django`; alle DSB-Templates migriert; Contract-Test gegen iil-ui (per ADR-184) |
| 7 | Layer 3 (Web Components) | iil-ui v0.2 | nur wenn ≥2 Komponenten klar profitieren (z.B. data_table mit Sort) — sonst skip |
| 8 | **Decision Gate B → Phase B (weitere Hubs)** | — | ttz-hub und meiki-hub bekommen Konsumenten-Status nur bei explizitem Bedarf, nicht eilig forciert |

**Kill-Switch**: Wenn Decision Gate A nicht in 4 Wochen erreicht, ist die Architektur falsch — ADR-200 v2 wird `rejected`, neue ADR mit gelernten Constraints.

## 6. Alternatives Considered

| Alternative | Bewertung |
|---|---|
| **DaisyUI als Basis** | Decken ~60% ab (btn, badge, alert, card). Verworfen weil: (a) DaisyUI hat keine `action_group` mit ARIA-Toolbar-Pattern, (b) keine HTMX-Integration als Tag-API, (c) Theming-Vertrag passt nicht zu Multi-Tenant-Hub-Bedürfnis (DaisyUI-Themes sind globale Switch-Themes). **Aber**: `@iil/ui-css` orientiert sich am DaisyUI-Tailwind-Plugin-Pattern (addComponents). |
| **Tailwind-UI / shadcn/ui** | Kommerziell (Tailwind-UI $) oder React-only (shadcn). Beide kein Fit für server-rendered Django. |
| **Pures Tailwind + Lint-Guard** (Alt. D von v1 review) | Verhindert Drift, beseitigt sie nicht; löst Cross-Hub-Sharing nicht. |
| **Codegen-Pattern (ADR-199-Style)** | Erzeugt Templates im Consumer per nightly PR. **Erwogen aber abgelehnt**, weil: UI-Components ändern sich langsamer als Routing-Tabellen, Live-Dep ist OK. Codegen würde Drift einführen, nicht eliminieren. |
| **Web Components als Primary Layer** | Verworfen weil: (a) WeasyPrint führt kein JS aus → Print-Bifurkation, (b) Tailwind+Shadow DOM inkompatibel, (c) JS-Build-Pipeline kein Standard in den Hubs. **Aber**: Web Components als optionale Layer 3 = best-of-both. |
| **Git-Submodul** | Submodul-Friktion, kein semver, in iil-testkit/iil-adrfw bewusst vermieden. |
| **Monorepo (alle 9 Hubs)** | Widerspricht ADR-022 (Multi-Repo-Pattern), unverhältnismäßig. |
| **Backstage-Component-Registry** (Alt. E von v1 review) | Erwogen für Doku-Layer (Gallery siehe 2.3) — orthogonal zur Code-Sharing-Frage, nicht ersetzend. |
| **CSS-Modules / styled-components** | Greift nur im JS-Frontend-Build, nicht in WeasyPrint. |

## 7. Consequences

### Positive

- **Theming löst sich sauber** über CSS Custom Properties — kein Safelist-vs-Override-Konflikt, kein Tailwind-Pfad-Magic.
- **Print + Interactive teilen Layer 1 & 2** — eine Source-of-Truth für visuelle Vertrag.
- **Layer 3 ist opt-in** — Hubs ohne Build-Tool können Layer 1+2 problemlos nutzen.
- **Tailwind-Plugin-Pattern** ist Industry-Standard — robuste JIT-Kompatibilität.
- **Compliance-Klarheit** für TTZ/LRA von Tag 1.
- **Decision Gate mit messbaren Kriterien** — kein „2 Wochen ohne API-Change"-Wischiwaschi.
- **Scope-Disziplin**: Schema-Klassen und Print sind eigene ADRs — diese ADR entscheidet eine Sache klar.

### Negative

- **Zwei Packages statt eins** (npm + PyPI) — höhere Release-Disziplin, Versions-Matrix.
- **CSS-Layer-Discovery-Tooling nötig**: Welche Klassen gibt es? → Gallery-View (in iil-ui-django) Pflicht für Discovery.
- **Monorepo statt 3 Repos** — Tooling-Setup (pnpm + uv workspaces) initial aufwendiger.
- **CSS Custom Properties haben kein Tailwind-IntelliSense** — Editor-Setup pro Hub anpassen.
- **Layer 3 (Web Components) erfordert JS-Build** — pro adoptierendem Hub eine Bundler-Entscheidung (Vite/esbuild).
- **Tailwind v4 Migration** kann Layer 1 brechen — explizite Cross-Version-Matrix nötig.

### Neutrale

- **Pilot in `src/core/components/`** (nicht `src/dsb/components/`) — verhindert Modul-Lock-in, macht repo-weite Wiederverwendung sofort möglich.
- **Layer 3 ist Phase 2** — nur wenn Bedarf nachgewiesen.

## 8. Contract-Testing-Strategie (ADR-184)

Pro Komponente:

1. **Snapshot-Test im Package** (`iil-ui-django/tests/`): HTML-Output stabil.
2. **Visual-Regression-Test in iil-ui-Monorepo**: Playwright + Screenshot-Diff über Gallery-View.
3. **Consumer-Side-Contract-Test**: jeder Consumer-Hub testet eigene Page-Templates gegen aktuell installierte iil-ui-Version. Pattern wie ADR-184 für Service-Contracts: Versions-Bump in Consumer = CI muss re-validieren.
4. **A11y-Test**: pa11y-ci im Monorepo gegen Gallery-View, fail-on-error.

## 9. HTMX-Friendliness (explizit)

Jede Komponente in Layer 2 akzeptiert:
- `hx_target`, `hx_swap`, `hx_trigger`, `hx_confirm`, `hx_post`, `hx_get` als Tag-Parameter → werden zu `hx-*` Attributen.
- `id` und `data_testid` für gezielte Swap-Targets.
- `oob` (out-of-band) Flag, der `hx-swap-oob="true"` emittiert.

Komponenten emittieren **stabile CSS-Selektoren** (`data-iil-component="action-group"`), die HTMX-Swaps und CSS-Theming gleichermaßen verlässlich erreichen.

## 10. Discovery & Documentation (Gallery)

`iil-ui-django` enthält `iil_ui.gallery`:
- URL: `/iil-ui/` (per `include('iil_ui.gallery.urls')`, nur in DEBUG).
- Rendert jede Komponente in allen Varianten (variant, size, state).
- Generiert auf demselben Template Tags wie Page-Templates → Drift unmöglich.
- Ersetzt nicht Storybook (kein Props-Editor, keine MDX-Docs) — **ehrlich als „Living Style Guide" gerahmt**, nicht als Storybook-Ersatz.

Für externe Doku: Eintrag in dev-hub Backstage TechDocs, generiert aus iil-ui-Monorepo README + Gallery-Screenshots.

## 11. Implementation Status

`none` — Proposal. Implementation startet nach Approval mit Schritt 1 des Pilot Plans:
1. `risk-hub/src/core/components/` als lokales Pilot-Verzeichnis.
2. PR-Slice: Phase A (action_group, icon_action, status_badge-Erweiterung, messages_strip) als Folge-PR zu #63.
3. Nach Decision Gate A → Extraktion in `achimdehnert/iil-ui` Monorepo.

## 12. Related ADRs

- **ADR-022** — Platform Consistency Standard (Multi-Repo)
- **ADR-035** — Shared Django Tenancy (Präzedenz: shared Django-App)
- **ADR-100** — iil-testkit (Präzedenz: PyPI-Distribution, 16 Hubs)
- **ADR-111** — Private Package Distribution (superseded, PyPI-public neuer Standard)
- **ADR-133** — Shared AI Services Package
- **ADR-147** — Concept Templates Package
- **ADR-184** — Contract Testing Strategy (Consumer-Side-Contract-Tests)
- **ADR-196** — Adaptive Extensions (Bandit-Framework, Decision-as-Code-Vergleich)
- **ADR-199** — Model Routing Library (Codegen-Pattern als Alternative erwogen)

## 13. Changelog

- 2026-05-14: v1 → v2 nach advocatus-diaboli Review. Neue Architektur (CSS-Layer + Django + optional WC), Scope-Reduktion (Print + Schema-Klassen ausgegliedert), DaisyUI/WC-Trade-offs explizit, Compliance-Klärung TTZ/LRA, messbares Decision Gate, Tailwind-Plugin statt Safelist, Pilot-Ort `src/core/components/` statt `src/dsb/components/`.
- 2026-05-14 (später): **PAUSED.** YAGNI-Audit über 24 Hubs zeigt: 94 % der Pattern-Hits in risk-hub, nur dev-hub als zweiter Hub mit Overlap. Cross-Hub-Library-Investment derzeit unproportional. Pfad A (risk-hub-only Konsolidierung in `src/core/components/`) wird umgesetzt; ADR-200 wartet auf Reaktivierungs-Bedingungen.
