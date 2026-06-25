# Prozess-Convention: MMD → KD → Code → Testen (E2E)

> **Scope:** ORG-WEIT (platform = kanonische Quelle) · gilt für alle Klickdummy-gestützten
> Feature-Stränge in allen Hubs (risk-hub, illustration-hub, …).
> **Status:** freigegeben 2026-06-24 (risk-hub) · org-weit gehoben 2026-06-25 ·
> Ableitungsquelle: Ex-Schutz-Konzept-Brownfield-Session (risk-hub).
> **Voraussetzungen im Ziel-Repo:** `klickdummy/<modul>/` (`_flow.view.md` + `screens-spec.yaml` +
> `index.html`), `iil-klickdummy`-Schema, Makefile-Target `klickdummy-parity-drift` (auto-discovering).

---

## 1 — Zwei Varianten

> **Evidenz-Pflicht vor Varianten-Wahl:** Auch wenn der Trigger "Greenfield" lautet,  
> erst `grep -rn <modul> src/` + `git log -- src/` laufen lassen.  
> Code gefunden → **automatisch Brownfield**. Befund explizit benennen.  
> Kein Modul ist "neu" bevor die Codebase das bestätigt hat.

### Greenfield (kein Code gefunden — nach Evidenz-Check bestätigt)

```
[Evidenz-Check: grep src/ + git log → kein Treffer]
MMD (_flow.view.md)
  → Freigabe ("freigeben")
  → SoR (screens-spec.yaml)
  → KD (index.html)
  → Playwright-Test am KD
  → Code (Django-Views/-Templates/-Models)
  → Playwright-Test am echten Stack
  → Befund? → zurück zu MMD
```

### Brownfield (Code existiert — durch Evidenz-Check oder Trigger bestätigt)

```
Code-Ist-Stand analysieren
  → MMD (_flow.view.md) — Ist-Stand + Korrekturen dokumentieren
  → Freigabe ("freigeben")
  → SoR (screens-spec.yaml)
  → KD (index.html)
  → Playwright-Test am KD
  → Code — nur abweichende Stellen korrigieren (kein Rewrite)
  → Playwright-Test am echten Stack
  → Befund? → zurück zu MMD
```

---

## 2 — Artefakte & ihre Rollen

| Artefakt | Datei | Zweck | Schreibrecht |
|---|---|---|---|
| **MMD** | `klickdummy/<modul>/_flow.view.md` | Screen-Flow als Mermaid-Flowchart; freigabepflichtiger UX-Vertrag | User (Stift-Icon auf GitHub) |
| **SoR** | `klickdummy/<modul>/screens-spec.yaml` | Maschinenlesbare Spec; Nodes, Gates, ext. Module, parity_acceptance | AI nach Freigabe |
| **KD** | `klickdummy/<modul>/index.html` | HTML-Prototyp; folgt SoR; wird per Playwright getestet | AI nach Freigabe |
| **Code** | `src/` (Views/Templates/Models) | Produktionscode; folgt freigegebenem KD, nie umgekehrt | AI nach KD-Freigabe |
| **Master-Flow** | `klickdummy/<modul>/_master-flow.view.md` | Übersicht aller WFs im Modul; verweist auf WF-spezifische `_flow.view.md` | AI / User |

---

## 3 — Branch-Convention

```
mmds/<modul>-master      ← kanonischer MMD-Branch (SoR + KD + _flow.view.md)
feat/<nr>-<slug>         ← Code-PRs; basieren auf main
```

MMD-Änderungen landen **immer** auf `mmds/<modul>-master`, Code-PRs auf Feature-Branches von `main`.

---

## 4 — Freigabe-Gate (Pflicht-Checkpoint)

Der User muss explizit **"freigeben"** sagen, bevor AI:
- `screens-spec.yaml` schreibt/ändert
- `index.html` ändert
- Produktionscode anfasst

Ein "sieht gut aus" oder Schweigen ist **keine Freigabe**. Der User reviewt das MMD auf GitHub (Mermaid-Rendering) oder lokal.

---

## 5 — SoR-Pflichtfelder je Screen

```yaml
screens:
  - id: <step-id>
    title: "…"
    personas: [fachplaner]
    next_screens: [<id>]
    back_screen: <id>
    parity_acceptance:
      - { id: <step>.<check-slug>, check: "Sichtbar prüfbare Bedingung im Browser." }
    off_ramp_status: static
```

Für **externe Module** (kein KD-Screen):

```yaml
flow:
  nodes:
    - id: <step>
      external_links:
        - id: ext_<slug>
          label: "…"
          route: /ex/concept/{concept_id}/
          note: "Reales Modul :8090 — …; Rücksprung nach <step>"

external_modules:
  - id: ext_<slug>
    route: /ex/concept/{concept_id}/
    port: 8090
    status: "fast fertig | live"
    note: "…"
```

---

## 6 — Playwright-Test am KD (Pflicht vor Code-Schritt)

Jeder Screen bekommt `testid`-Attribute im HTML. Playwright prüft je `parity_acceptance`-Eintrag:

```python
# Beispiel: Schritt E — bearbeiten-Link öffnet ext. Overlay
page.click("[data-testid='e-bearbeiten-0']")
assert page.locator("#ext-module-overlay").is_visible()
assert "/ex/concept/" in page.locator("#ext-module-overlay a").get_attribute("href")
```

Kein Code-Schritt ohne grünen KD-Playwright-Lauf. **Browser-Verifikation ist Pflicht** — `make test` allein reicht nicht.

---

## 7 — Brownfield-Besonderheiten

1. **Code analysieren zuerst** — Ist-Verhalten per Playwright/grep, nicht durch Lesen erraten.
2. **Befunde im MMD dokumentieren** — Abweichungen zwischen Ist und Soll werden als Korrekturnotiz in `_flow.view.md` festgehalten (z. B. `Korrektur 2026-06-24: E→ext statt interne A3-Navigation`).
3. **Externe Module früh identifizieren** — Wenn ein Flow-Schritt auf ein fast-fertiges echtes Modul verweist (statt KD-intern), gehört das als `external_links` in den MMD-Knoten, **nicht** als KD-Navigation.
4. **Minimale Code-Änderungen** — Brownfield korrigiert nur die Abweichung. Kein Rewrite, kein Refactor-Scope.

---

## 8 — Takt-Regel

**Ein Schritt, ein Artefakt, ein Commit. Kein Bulk.**

- MMD freigegeben → erst dann SoR — nicht schon KD vorbereiten
- SoR fertig → erst dann KD — nicht schon Code skizzieren
- KD-Korrektur → nur die eine Abweichung, nicht "während wir hier sind noch ..."
- Jede Phase wartet auf Freigabe der vorherigen ("freigeben" oder explizite Bestätigung)
- Convention wächst Schritt für Schritt beim echten Arbeiten — kein Bulk-Update auf Vorrat

---

## 9 — Vollständiger Checklisten-Ablauf

### A — MMD-Phase

- [ ] `_flow.view.md` auf `mmds/<modul>-master` erstellt/aktualisiert
- [ ] Alle Screens als Mermaid-Knoten, externe Module als `⬡`-Knoten mit Route
- [ ] Gates als Kantenbeschriftungen (`|"alle Punkte grün"|`)
- [ ] Rücksprünge als `-.zurück.->` (gestrichelt)
- [ ] GitHub-Rendering geprüft
- [ ] User hat **"freigeben"** gesagt

### B — SoR-Phase (`screens-spec.yaml`)

- [ ] `spec_version` erhöht, `spec_date` aktualisiert
- [ ] `flow:` Block vollständig (alle Nodes + `external_links` wo nötig)
- [ ] `external_modules:` Block ergänzt
- [ ] Je Screen: `parity_acceptance` mit testbaren Browser-Checks
- [ ] Kommentar-Header `flow_sor:` zeigt auf `_flow.view.md`

### C — KD-Phase (`index.html`)

- [ ] Alle `parity_acceptance`-Checks als `data-testid` im HTML
- [ ] Externe Module als Overlay/Modal (kein interner `go()`-Aufruf)
- [ ] `(ext.)`-Marker bei externen Links sichtbar
- [ ] Banned-Patterns-Check: kein `onclick=` in src/templates (→ `data-act`)

### D — Test-Phase KD

- [ ] Playwright öffnet KD im Browser (kein `file://` — via Serve oder GitHub Pages)
- [ ] Golden Path durchgeklickt: A1 → … → G
- [ ] Externe Links öffnen Overlay, URL zeigt auf reales Modul
- [ ] Gates blockieren korrekt (F gesperrt wenn E offen)
- [ ] User bestätigt oder meldet Befund

### E — Code-Phase

- [ ] Nur abweichende Stellen gegenüber KD korrigieren
- [ ] URL-Pattern spiegelt `route` aus SoR (`/ex/concept/{id}/` o. ä.)
- [ ] Kein Feature-Scope-Creep

### F — Test-Phase Code

- [ ] Playwright auf echtem Stack (Container + Browser, kein Reload-Gunicorn)
- [ ] Selbe `parity_acceptance`-Checks wie beim KD-Test
- [ ] Befund → Schritt A (neues MMD-Delta)

---

## 9 — Anti-Patterns (aus Post-Mortems)

| Anti-Pattern | Korrekte Alternative |
|---|---|
| Code direkt ohne MMD-Freigabe ändern | Immer MMD → Freigabe → Code |
| `onclick=` in KD-HTML | `data-act`-Delegation (Banned-Patterns-Gate) |
| KD-internen `go()`-Aufruf für ext. Modul | `extModuleOpen()` / Overlay mit externem Link |
| `make test` als Verifikation für UI-Flow | Playwright im Browser auf laufendem Stack |
| `screens-spec.yaml` ohne `parity_acceptance` | Jeder Screen braucht ≥1 testbaren Check |
| Brownfield = Rewrite | Brownfield = minimale Delta-Korrektur |
| "freigegeben" ohne explizites Wort | Warten auf "freigeben" vom User |

---

## 10 — MMD/Mermaid verifizieren (Lehre 2026-06-25)

Das MMD ist Mermaid → **vor dem Ausgeben/Pushen zweistufig prüfen**, weil Syntax-OK ≠ GitHub-OK:

1. **Syntax:** `npx @mermaid-js/mermaid-cli -p pptr.json -i x.mmd -o x.svg`
   (`pptr.json` = `{"args":["--no-sandbox"]}`; SVG > 0 Bytes = OK). Fängt Syntaxfehler
   wie gemischte Link-Form `-.|"txt"|.->` (korrekt: `-. "txt" .->`).
2. **GitHub-Verhalten:** `gh api --method POST /markdown` + ggf. Playwright.
   GitHub rendert Mermaid in einer **iframe-Sandbox** → In-Diagramm-`click "#anker"` bricht
   (schwarzer Bildschirm); `<a id="x">` wird zu `user-content-x` umgeschrieben. **Für TOC**
   daher **Heading-Auto-Anker** mit simplen ASCII-Headings nutzen (`### Schritt A` → `#schritt-a`),
   keine Custom-Anker, kein Mermaid-`click`.

**Diagramm-Typen je Zweck (eine Quelle je Detailgrad, gegen Drift):**
- `flowchart` = Workflow (Schritt-Reihenfolge, Gates) · `erDiagram` = Daten-Modell (spiegelt die Models) ·
  `classDiagram` = Attribute/Aktionen je Screen. **Per-Screen-Felder gehören in die SoR (`screens-spec.yaml`),
  nicht zusätzlich hand-gepflegt** — sonst drei Quellen = Drift.

**Regel:** Privates Ziel (Repo) in Playwright nicht ohne Login ladbar → dann **„unverifiziert" sagen**,
nicht „funktioniert" behaupten (ein lokaler Nachbau ist kein Beweis fürs echte Ziel).
