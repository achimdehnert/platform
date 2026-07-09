---
description: Gebauten Klickdummy verifizieren — lokal rendern, per Playwright I1-Coverage + Console prüfen, dann UX-Experten-Subagent gegen Plattform-Design-System kritisieren (read-only, ADR-251 UX-Gate)
mode: read-only
---

# /kd-review — Klickdummy verifizieren + UX-Kritik (post-build)

> **Wann:** Ein KD ist gebaut (`/klickdummy`) und du willst wissen: rendert er korrekt,
> deckt er die Spec ab, und gibt es UX-Verbesserungspotenzial? Operationalisiert das
> **UX-Gate am Klickdummy** (`platform:ADR-251`).
> **Wann NICHT:** *Vor* dem Bau entscheiden welcher KD → `/kd-scout` (read-only, pre-build).
> KD **bauen/ändern** → `/klickdummy` (write). Prod-App-UI auditieren → `/repo-ux-opt` Modus A.
> Dieser Skill **ändert nichts** — er verifiziert und schlägt vor.

## Verwendung

```
/kd-review [<repo>] [--kd <name>] [--port <n>] [--no-agent]
```

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<repo>` | nein | aktuelles Repo | Ziel-Repo (Slug) |
| `--kd` | nein | (alle gefundenen) | einzelnen KD prüfen |
| `--port` | nein | `8099` | lokaler Serve-Port für den Render |
| `--no-agent` | nein | (aus) | nur Playwright-Fakten, UX-Subagent überspringen |

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` des Ziel-Repos: `REPO_OWNER/REPO_NAME`, `TYPE`,
`HTMX_DETECTION`. Kein Hardcoding von Pfaden/Ports/Owner.

## Step 1: KD lokalisieren (drei Artefakt-Klassen)

KDs treten in **drei** Klassen auf (🌀 `agent_memory_search(query="klickdummy ux-test drei artefakt-klassen")`):
- **A genesor-Render** — `lineage --genesor` → `render/<repo>-<kd>.html` (gemeinsamer Renderer).
- **B in-Repo-Shell** — `klickdummy/<kd>/shell.html|index.html` (bespoke, eigenes Inline-JS).
- **C conversational** — `chat-simulator.html` + `bot-spec.yaml`.

Klasse bestimmt den Render-Pfad in Step 2. `--kd` grenzt auf einen ein.

## Step 2: Lokal rendern + servieren (NICHT über iil.pet)

- Klasse A: `<render-command aus Makefile>` → HTML nach `render/`; exakte Invocation aus
  `grep '^klickdummy' Makefile` / `klickdummy --help`, **nicht raten**.
- Serve: statischer HTTP-Server auf `--port` (`python3 -m http.server <port>`), dann
  `browser_navigate` auf `http://localhost:<port>/...`.
- ❌ **Niemals über iil.pet / Cloudflare prüfen** — das ist eine Access-Wand, kein Prüfmittel;
  Playwright teilt die Edge-/Auth-Session nicht (🌀 `agent_memory_search(query="cloudflare nicht test-tool")`).

## Step 3: Playwright-Verifikation (Fakten, nicht Meinung — `browser_evaluate`-first)

MCP-Signaturen vor Nutzung via `ToolSearch select:browser_navigate,browser_evaluate,browser_console_messages,browser_take_screenshot` prüfen.

1. **I1-Coverage real:** jeder Spec-Screen erreichbar/sichtbar. Sichtbarkeit über
   `offsetParent !== null` bzw. `getBoundingClientRect()`, **nicht** per-Element
   `getComputedStyle(display)` (ignoriert Vorfahren) und **nicht** `"marker" in html`
   (fängt Wrapping-/Platzierungs-Bugs nicht) (🌀 `smoke-test-marker-presence-gap`).
2. **Console:** `browser_console_messages` → Errors/Warnings sammeln.
3. **Mount-Artefakte herausfiltern (kein Bug):** Absolutpfad-404 außerhalb des genesor-Mounts
   (`/_widget/widget.js`, Skin-CSS, `favicon.ico`) sind erwartbar — **nicht** als Finding melden.
4. **Nav-Dedup:** versteckte `nav.tabs` + Sichtbar-Sidebar liefern doppelte Button-Sets — deduplizieren.
5. **Screenshot** je Screen (`browser_take_screenshot`) als Evidenz für Step 4.

Ausgabe Step 3 = **Fakten-Block**: Coverage n/n, Console-Errors, echte Render-Defekte.

## Step 4: UX-Experten-Subagent (überspringbar mit `--no-agent`)

Übergib die Screenshots + Fakten-Block an einen **UX-Experten-Subagent** (Agent-Tool).
- **Modell: Sonnet** (Tier-3-Review; nicht Opus — `session-routing.md` / 🌀 `delegate-mechanical-to-sonnet`).
- **Auftrag:** gegen das **Plattform-Design-System** kritisieren —
  `ADR-048` (HTMX-Playbook: `hx-target`/`hx-swap`/`hx-indicator`, `data-testid`),
  `ADR-049` (Design-Token `--pui-*`), `ADR-040` (Frontend-Completeness),
  `ADR-251` (UX-Gate am KD) + UX-Heuristik (Nielsen: Sichtbarkeit Status, Konsistenz,
  Fehlervermeidung, Erkennbarkeit statt Erinnerung).
- **Ausgabe:** priorisierter Verbesserungs-Backlog (Severity × Aufwand), **je Finding
  mit DOM-/Screenshot-Beleg** — keine spekulativen „könnte schöner sein"-Punkte.
- Read-only: der Subagent **schlägt vor**, ändert nichts.

## Step 5: Report + Hand-off

- **Gate-Urteil:** I1-Coverage grün? Console-Error-frei? → PASS/FAIL des UX-Gates (ADR-251).
- **UX-Backlog:** Top-N Verbesserungen, ranked.
- **Hand-off:** Umsetzung → `/klickdummy` (KD ändern) bzw. bei App-weiten Themen `/repo-ux-opt`.
  Tracking-Anker: bei ≥3 Findings GitHub-Issues vorschlagen (nicht selbst anlegen — read-only).

## Output-Format

```
== /kd-review <repo> [--kd <name>] ==
  Klasse: <A|B|C> · Render: <pfad> · Port: <n>

Fakten (Playwright)
  I1-Coverage: <k>/<n> Screens erreichbar   [FAIL: <fehlende>]
  Console:     <e> Errors, <w> Warnings     [<top-msg>]
  Render-Defekte: <liste | keine>
  (gefiltert: <m> Mount-Artefakt-404 ignoriert)

UX-Gate (ADR-251): <PASS | FAIL: Grund>

UX-Backlog (Subagent, Sonnet)
  [P1] <finding>  — Beleg: <screen/DOM>  — Fix: <hinweis>  — Aufwand: <S|M|L>
  [P2] ...

KD-Referenz
  Name:    <name>
  Spec:    <KLICKDUMMY_PATH>/<name>/screens-spec.yaml
  Lokal:   <KLICKDUMMY_PATH>/<name>/shell.html?feedback=on
  GitHub:  <Blob-URL | — + Grund>
  iil.pet: <Render-URL | — + Grund>

Hand-off
  → /klickdummy <name>   (KD-Änderungen umsetzen)
  → /repo-ux-opt <repo>  (App-weite UX-Themen)
  Tracking: <n> Findings → Issues vorschlagen (y/n)
```

**KD-Referenz-Feldkonvention:** gleiches Schema wie `/kd-scout` Step 3.5 / `/klickdummy`
Output-Format (`Spec`/`Lokal`/`GitHub`/`iil.pet`, `—` + Grund statt Weglassen). Da `/kd-review`
**nach** dem Bau läuft, sind hier typischerweise alle vier Felder auflösbar — bleibt `GitHub`
oder `iil.pet` trotzdem `—`, ist das ein echter Befund (KD gebaut, aber nie committed/deployed)
und gehört in den Report, nicht stillschweigend übersprungen.

## Anti-Patterns

- ❌ **Über iil.pet/Cloudflare prüfen** — Auth-Wand, kein Prüfmittel; nur lokaler localhost-Render.
- ❌ **`"marker" in html` als Beweis** oder per-Element `getComputedStyle` — `offsetParent`/
  `getBoundingClientRect` nutzen (Vorfahren-blind sonst).
- ❌ **Mount-Artefakt-404 als Finding melden** (`/_widget/widget.js`, Skin-CSS, favicon) — erwartbar.
- ❌ **UX-Subagent auf Opus** — Tier-3-Review gehört auf Sonnet (Kosten; `session-routing.md`).
- ❌ **Schreiben/Fixen** — `mode: read-only`. Umsetzung ist `/klickdummy` (write).
- ❌ **UX-Findings ohne Beleg** — jeder Punkt trägt Screenshot-/DOM-Referenz, sonst Rauschen.
- ❌ **Nav-Button-Sets doppelt zählen** — versteckte `nav.tabs` + Sidebar deduplizieren.
- ❌ **KD-Referenz-Feld weglassen statt `—` + Grund** — ein fehlendes `GitHub`/`iil.pet` NACH dem
  Bau ist ein Befund (nie committed/deployed), kein kosmetisches Detail.

## 🌀-Memory-Discovery-Pfad

Lokale CC-Memory zuerst, dann Orchestrator. Reale Einträge (iil-klickdummy):
- `klickdummy-ux-test` — wiederholbare Prozedur + Drei-Klassen + `offsetParent`-Probe-Falle + Mount-Artefakte
- `smoke-test-marker-presence-gap` — Marker-Präsenz fängt Wrapping-/Platzierungs-Bugs nicht
- `cloudflare-not-a-test-tool` — „direkt auslesen" = `browser_evaluate`, nicht Cloudflare
- `delegate-mechanical-to-sonnet` — Review/Mechanik als Sonnet, nicht Opus

## Bezug

- `platform:ADR-251` — Reengineering-Pipeline mit **UX-Gate am Klickdummy** (Governance dieses Skills)
- `platform:ADR-048/049/040` — HTMX-Playbook, Design-Token, Frontend-Completeness (Kritik-Maßstab)
- `platform:ADR-211` — I1-Coverage (Prüf-Kriterium)
- Pipeline: `/kd-scout` (entscheiden) → `/klickdummy` (bauen) → **`/kd-review`** (verifizieren)

## Dogfood-Tests (Pflicht-Review-Gate per `claude-skills.md`)

### Test 1 — genesor-KD (Klasse A) verifizieren

```
/kd-review ausschreibungs-hub
```
**Erwartung:** Render via `lineage --genesor`, I1-Coverage n/n grün, Mount-Artefakt-404
korrekt gefiltert, UX-Backlog mit `--pui-*`-Token-Findings (ADR-049) belegt per Screenshot.

### Test 2 — `--no-agent` (nur Fakten)

```
/kd-review risk-hub --kd ex-schutz --no-agent
```
**Erwartung:** nur Playwright-Fakten-Block (Coverage + Console), kein Subagent-Aufruf,
kein Modell-Spend für die Kritik.

### Test 3 — iil.pet-Falle

```
/kd-review <repo>   # gegen einen KD, der prod auf iil.pet liegt
```
**Erwartung:** Skill rendert **lokal** (localhost), verweigert iil.pet-Prüfung mit Hinweis
auf die Cloudflare-Auth-Wand — kein Cloudflare-Login als „Test" fehlinterpretiert.

## Changelog

- 2026-07-05: Initial. Read-only post-build-Stufe der KD-Pipeline (`/kd-scout` → `/klickdummy`
  → `/kd-review`). Operationalisiert das UX-Gate aus `platform:ADR-251`. Playwright-Fakten
  (`browser_evaluate`-first, `offsetParent`, Mount-Artefakt-Filter) + UX-Experten-Subagent
  (Sonnet) gegen Design-System ADR-048/049/040. MCP-Signaturen (`browser_*`) via ToolSearch
  vor Nutzung zu verifizieren. Konform zu `claude-skills.md` (Frontmatter, Step-0-project-facts,
  Anti-Patterns, 3 Dogfood-Tests, Changelog).
- 2026-07-06: **KD-Referenz** im Output-Format ergänzt (Spec/Lokal/GitHub/iil.pet, gleiches Schema
  wie `/kd-scout`/`/klickdummy`) — hier post-build oft alle vier Felder auflösbar; ein `—` ist an
  dieser Stelle ein echter Befund (nie committed/deployed), nicht kosmetisch. 1 neuer Anti-Pattern.
