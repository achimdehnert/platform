---
description: Repo-UX optimieren — Modus A (Audit + Refactor bestehender App) oder Modus B (Spec-first für Neues) nach Plattform-Design-System (ADR-048/049/040/211/251)
---

# /repo-ux-opt — Repo-UX optimieren

**Usage:** `/repo-ux-opt <reponame> [A|B] [--scan-only]`

- **Modus A** — bestehende App: UX-Audit + priorisierter Refactor
- **Modus B** — neue App / neues Feature: Spec-first via Klickdummy (ADR-211/251)
- Ohne Modus-Angabe: Templates vorhanden (`git ls-files '*.html'` > 0) → A, sonst B
- `--scan-only`: nur Schritt 1–2 (Inventar + Findings-Tabelle), **keine Edits** —
  empfohlener erster Lauf, bevor Schreibrechte sinnvoll sind

## Wann `/repo-ux-opt` — und wann nicht?

- **Wann:** gezielte **UI/UX**-Arbeit an einem Repo — Frontend-Audit + Refactor (Modus A)
  oder Spec-first für neue Views via Klickdummy (Modus B), nach Plattform-Design-System.
- **Wann NICHT / stattdessen:**
  - Repo **breit** optimieren (Tech-Debt, Tests, Robustheit, LLM-Readiness) → `/repo-optimize`.
  - Fleet/Cross-Repo-Audit → `/platform-audit`.
  - Reines Quality-Gate vor Publish/Deploy → `/repo-health-check`.

---

## Schritt 0 — Repo-Fakten laden (Pflicht, nichts raten)

`${GITHUB_DIR:-$HOME/github}/[REPO]/.windsurf/rules/project-facts.md` lesen und übernehmen:
`DJANGO_VERSION`, `SETTINGS_MODULE`, `TEST_SETTINGS_MODULE`, `HTMX_DETECTION`,
`LOCAL_APPS`, `AUTH_USER_MODEL`. Fehlt die Datei → Fallbacks aus `/prompt` Schritt 2
(lokal generieren via `platform/scripts/gen_project_facts.py`).

**Design-System-Kontext (plattformweit, verifiziert):**
- ADR-049: Zwei-Layer-Token-System — `--pui-*` Custom Properties + semantische
  Tailwind-Bridge (`--pui-primary`, `--pui-success`, `--pui-danger`, `--pui-warning`,
  `--pui-surface`, `--pui-border`, `--pui-muted`, `--pui-space-*`).
  Quelle: `platform/static/css/tokens.css`.
- ADR-048: HTMX-Playbook — HP-001..007 kanonisch, AP-001..007 verboten.
- ADR-040: Frontend-Completeness-Gate — „Fertig" nur mit Element-Inventar Spec↔Template.
- ADR-200 (iil-ui) ist **paused** — KEINE shared UI-Library verwenden/erfinden;
  Patterns als Template-Partials im Repo.

---

## Schritt 1 — Template-Discovery (robust, NIE Pfade hardcoden)

Templates liegen je Repo unterschiedlich (`templates/`, `src/templates/`,
`src/<app>/templates/`). Discovery immer über git, Archiv/Vendor ausschließen:

```bash
cd ${GITHUB_DIR:-$HOME/github}/[REPO]
git ls-files '*.html' | grep -vE '(^|/)(_archive|node_modules|\.venv|staticfiles)/' > /tmp/ux_tpl_[REPO].txt
wc -l /tmp/ux_tpl_[REPO].txt
```

0 Treffer → Modus B. Sonst Modus A (außer explizit B verlangt).

---

## Schritt 2 — AP-Scan (Modus A; alle Greps über die Discovery-Liste)

```bash
cd ${GITHUB_DIR:-$HOME/github}/[REPO]
TPL=/tmp/ux_tpl_[REPO].txt

echo "== AP-002 hx-boost auf Forms ==";        xargs -a $TPL -r grep -n 'hx-boost' | wc -l
echo "== AP-003 onclick + hx-* gemischt ==";   xargs -a $TPL -r grep -l 'onclick=' | xargs -r grep -l 'hx-' | wc -l
echo "== AP-004 inline style= ==";             xargs -a $TPL -r grep -n 'style=' | wc -l
echo "== AP-007 Hex-Farben ==";                xargs -a $TPL -r grep -nE '#[0-9a-fA-F]{6}\b' | grep -vE '\{#' | wc -l
echo "== direkte Tailwind-Farbklassen ==";     xargs -a $TPL -r grep -nE '(bg|text|border)-(blue|red|green|amber|gray)-[0-9]{3}' | wc -l
echo "== hx-get/post ohne hx-indicator (zeilenweise, manuell verifizieren) ==";
xargs -a $TPL -r grep -nE 'hx-(get|post)' | grep -v 'hx-indicator' | wc -l
echo "== data-testid vorhanden ==";            xargs -a $TPL -r grep -n 'data-testid' | wc -l
```

**Findings-Tabelle ausgeben:** `Datei | Verstoß (AP-Nr./Token) | Fix`.
`hx-indicator`-Treffer als 🟡 „manuell prüfen" ausweisen (Indicator kann am
Parent liegen), NICHT pauschal als Verstoß zählen.
Bei `--scan-only`: **hier stoppen** und Tabelle + Priorisierung liefern.

---

## Schritt 3A — Refactor (Modus A, Prioritätsreihenfolge)

1. Fehlende Loading-/Error-Feedbacks (`hx-indicator` + Error-Partial, kein stilles Scheitern)
2. Hardcoded Farben / Inline-Styles → `--pui-*`-Tokens
3. Fehlende `data-testid` auf interaktiven Elementen
4. Inkonsistentes Spacing/Radii → `--pui-space-*`

Pro geändertem Flow einen Playwright-/View-Test ergänzen.
Großposten (z. B. tausende direkte Tailwind-Farbklassen) NICHT nebenbei fixen —
als eigenes Vorhaben via `/konzept` vorschlagen.

## Schritt 3B — Spec-first (Modus B)

1. NICHT direkt App-Code schreiben. Erst Use-Cases als `docs/use-cases/UC-*.md`,
   dann Klickdummy via `/klickdummy` (maschinenlesbare Spec + Renderer, ADR-211).
2. **UX-Gate (ADR-251):** Klickdummy vom User abnehmen lassen, BEVOR Views/Templates
   entstehen. Danach strikt gegen die KD-Spec implementieren; jede Abweichung zurück
   in Spec + KD pflegen (KD↔App-Drift war Root-Cause der apo-hub-Findings F1–F13).

---

## Constraints (NICHT verhandelbar)

- Jede HTMX-Interaktion: `hx-target` + `hx-swap` + `hx-indicator` (alle drei)
- HTMX-Detection portabel: `request.headers.get("HX-Request")` in shared Code;
  `request.htmx` nur wenn project-facts django-htmx ausweist
- Partials: kein `{% extends %}`, kein `<html>`
- Service-Layer (ADR-009): kein `Model.objects.*` / `.save()` in views.py
- Verboten: AP-001..007 (ADR-048) · UUIDField-PK · JSONField für strukturierte
  Daten · Secrets/IPs hardcoded · `print()` statt logging

## Akzeptanzkriterien

- [ ] Jede Interaktion hat Loading-Feedback + definierten Fehlerzustand
- [ ] 0 Treffer bei AP-002/003/004/007-Greps in geänderten Dateien
- [ ] Alle interaktiven Elemente via `data-testid` adressierbar
- [ ] [A] Findings-Tabelle + Element-Inventar Spec↔Template vollständig
- [ ] [B] Klickdummy abgenommen VOR Implementierung
- [ ] Ruff grün (`ruff check .` ohne `--exit-zero`) · Tests grün
- [ ] Alle `ASSUMPTION[unverified]` aufgelöst (ADR-174)

## Abschluss

```bash
git add -A && git commit -m "feat(ux): [kurze Beschreibung]"
```

Bei `moderate+` Komplexität: vorher `/pre-code`, danach `/agentic-coding`-Gates.
