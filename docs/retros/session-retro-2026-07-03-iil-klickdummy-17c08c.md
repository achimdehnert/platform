---
retro_schema: 1
date: 2026-07-03
repo_scope: [iil-klickdummy, risk-hub]
session_id: 17c08c
footprint: deep
findings_total: 16
findings_survived: 12
refuted_rate: 0.25
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [parallel-session-pr-collision, claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
recurring_findings: [parallel-session-pr-collision, claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
---

# Session-Retro — iil-klickdummy (+ risk-hub) · 2026-07-02/03

_Deep-Footprint (2 Repos, 2 nicht-rückrollbare PyPI-Publishes). 1 Collector (haiku) + 3 Finder + 3 Skeptiker (sonnet), Richter≠Angeklagter. 16 Befunde, 12 SURVIVES, 4 REFUTED._

## 1. Executive Summary

- **Auslieferung stark, Fundament mit Rissen:** Der komplette Bogen (Repo-Optimize → S-01-Browser-Fix → RCE-Härtung → KONZ-008-Loop → 2 Releases → Phase-C-Beweis gegen echte App) wurde geliefert und auf PyPI verifiziert. Aber die Falsifikation legt **6 echte technische Schwächen** frei, die im Selbst-Bericht als „erledigt" durchgingen.
- **Der lauteste Finder-Befund (EF-1 „Kritisch-RCE") ist REFUTED** — die fatale Schema-Validierung (spec_id-Pattern) blockt den Vektor im realen Pfad (PoC exit 1). Genau dafür existiert Richter≠Angeklagter: ein Self-Review hätte den PoC ungefiltert als „kritisch" durchgelassen.
- **Der genesor-Security-Pfad (SI-3, HOCH) bleibt ungefixt** — S-02 (raw-HTML) + S-03 (Path-Traversal) wurden nur als Issues (#105/#106) geparkt; `scan.py`/`ucs.py`/`lineage.py` laufen nie durch die jsonschema-Validierung. Die RCE-Härtung (#102) deckte punktuell nur `gen_e2e.load_spec`.
- **Zwei wiederkehrende Muster mit Gate-Pflicht:** (a) `parallel-session-pr-collision` — die Memory dazu existierte seit letzter Session, die Kollision (#95/#96↔#97/#98, 131 Zeilen doppelt) kam trotzdem → Memo wirkungslos. (b) `claim-before-cheapest-check` ×5 über Retros (EF-4: infer-asserts released, bevor sein Kill-Gate gemessen wurde).
- **13 Audit-Issues (inkl. HOCH-Security) alle offen** — der /repo-optimize-Report nannte „anlegen + abarbeiten diese Woche"; abgearbeitet wurde nichts, die Session priorisierte Neuentwicklung.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| SI-3 | genesor-Pfad (`scan.py`/`ucs.py`/`lineage.py`/`render_uc.py`) ungefixt: S-02 raw-HTML-Passthrough + S-03 Path-Traversal via `id`; keine jsonschema-Validierung, obwohl Schema-Pattern existiert | fehlende Validierung | **hoch** | SURVIVES | `render_uc.py:739-742/782` (markdown ohne Escape), `lineage.py:459-472` (`sid` roh in Dateiname), scan/ucs nur `yaml.safe_load`; Issues #103/#105/#106 offen | — |
| EF-2 | Flow-Knoten-`anyOf` (#122) verliert Sicherheitsnetz: Screen mit `off_ramp_status`+`next_screens` aber ohne `purpose`/`parity_acceptance` validiert + passiert check_i3 | Schema-Design | **hoch** | SURVIVES | `screens-spec.schema.json:156-186` anyOf 3 Branches + `additionalProperties:true`; `check_i3.py:64-70` Exemption prüft nur `off_ramp_status`; PoC: solcher Screen → I1 PASS, I3 PASS (PR #122) | — |
| EF-3 | `infer_asserts` emittiert für templated testid (`step-${…}`) einen funktional toten `count`-Assert (`get_by_test_id("step")` matcht `step-1..10` nie) und markiert ihn `kind:executable`; `is_fragile_selector` nennt ihn stabil | Heuristik-Korrektheit | **hoch** | SURVIVES | `infer_asserts.py:_match_testid/infer_one`; `is_fragile_selector("testid=step")→False`; interner Widerspruch: `note` warnt, `kind` bleibt executable | — |
| EF-4 | `infer_asserts` in 1.30.0 released, obwohl sein eigenes Kill-Kriterium (Bestätigungsquote <50%) nie gemessen wurde; Ledger-L3 explizit „⚠️ offen" | Prozess/Gate-Timing | mittel-hoch | SURVIVES | `KONZ-iil-klickdummy-008.md:10` (kill_criteria) + `:50` (L3 „⚠️ offen"); `pyproject.toml:35` + CHANGELOG-[1.30.0] listet `klickdummy-infer-asserts` (PR #121) | claim-before-cheapest-check ×5 |
| SI-2 | 13 Audit-Issues (#103,#105–#116, inkl. HOCH-Security) 0/13 adressiert, obwohl /repo-optimize-Report „anlegen + abarbeiten diese Woche" nennt | Prozesslücke | mittel | SURVIVES | `gh issue list --state open` alle 13 OPEN; Report Z.99 „Quick Wins (diese Woche): … + abarbeiten" | planned-phase-no-issue ×2 |
| PK-1 | Parallel-Session-Kollision: #95/#96 (131 Zeilen) verworfen zugunsten #97/#98 — zwei unabhängige Sessions am selben Issue, kein Issue-Lock | Prozesslücke | mittel | SURVIVES | Autor-Kommentar „Duplikat aus paralleler Session"; #95(+61)/#96(+70) CLOSED, #97/#98 MERGED; getrennte Branches | **Memory existierte, Kollision recurred ⇒ ×2** |
| PK-4 | risk-hub #368: Spec editiert, Suite nicht regeneriert → Parity-Drift-Gate rot → 2. Commit „Behebt Parity-Drift" nötig | fehlende Validierung | mittel | SURVIVES | check-runs Commit1 (2d2b0f9) failure → Commit2 (4b52f63) success | — |
| PK-5 | Release-PR #117 15,5h offen; 1.30-Breaking-Change (Flow-Knoten) erst durch echten risk-hub-Lauf entdeckt (#122), nicht vorab — reaktiv, aber vor Publish gefangen | fehlende Validierung | mittel | SURVIVES | #122-Body „Release-Blocker … beim echten Lauf gegen risk-hub"; #117 created 07-02 15:52 → merged 07-03 07:19 | — |
| EF-5 | `kind`-Default `executable` bricht bestehende Adopter-Specs ohne `kind`, sobald sie `parity-gate` nutzen; kein CHANGELOG-Migrationshinweis (bedingt: nur bei aktiver Gate-Nutzung) | Release-Migration | mittel | SURVIVES | `screens-spec.schema.json:156-160` `default:executable`; `parity_gate.py:33-39` `_kind_map`-Default; PoC Gate exit 1; CHANGELOG ohne Migrationsabschnitt (PR #121) | — |
| SI-1 | Scope-Checkpoint (Hausregel „3. Repo/Prod → spiegeln") in keinem Artefakt dokumentiert (schwache Version; starke „fand nicht statt" REFUTED — Chat-Ebene) | Prozesslücke | niedrig | SURVIVES (schwach) | PR-Bodies ohne Scope-Spiegel-Sprache; PR#117 nur punktuelles Publish-Gate „dein Zug" | scope-checkpoint-not-durably-recorded ×2 |
| SI-5 | v1.29.0 im CHANGELOG, nie getaggt/released (transparent dokumentiert) — SemVer-Phantom (== EF-6) | SemVer | niedrig | SURVIVES | `git tag -l v1.29*` leer; CHANGELOG erklärt es | — |
| EF-7 | `__REPO_LABEL__` (= `repo_root.name`) roh in HTML `<title>`/`<code>`, kein Escape — gleiche Fehlerklasse wie S-01, aber nur Self-XSS via Verzeichnisname | Security (Rest) | niedrig | SURVIVES | `registry.py:392` `html.replace` ohne Escape; PoC Break-out reproduziert | — |
| EF-1 | „Kritisch-RCE" via ungeescaptem HEADER (`spec_id`/`spec_version`) | Security | (kritisch→) niedrig | **REFUTED** | spec_id-Pattern verbietet `\n`; `main→load_spec→validate_spec` fatal VOR `gen_suite`; PoC exit 1. Rest: HEADER inkonsistent ungehärtet (Defense-in-Depth, niedrig) | — |
| SI-4 | „KONZ-008-Abnahme-Gate unterlaufen" (Impl vor Doc-Merge) | Prozess | — | **REFUTED** | PR #120 merged 06:57:32Z, #121 06:57:46Z, Doc-PR #119 07:18:49Z (Code vor Doc); `KONZ-008.md:144` Roadmap „M1-Prototyp … Kill-Gate-Entscheid" = Pilot-vor-Entscheid by design; keine Abnahme-Verletzung im Artefakt | — |
| SI-6 | „v1.3.0 vs v1.30.0 Tag-Verwechslung" | Werkzeug | — | **REFUTED** | pip/PEP-440 löst korrekt auf (`Version('1.30.0')>Version('1.3.0')`); rein kosmetisch, kein Bug | — |
| PK-2 | „Zwei Releases = Prozessfehler" | Prozess | — | **REFUTED** | M3 war zum 1.30.0-Publish nur Roadmap-Punkt; PR#117 „dein Zug"-Freigabe + Adopter-Dringlichkeit = legitime iterative Auslieferung | — |

## 3. Scorecard (1–5, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Alle Kern-Ziele geliefert + released + Phase-C-bewiesen; Abzug: 13 Audit-Issues + genesor-Security offen (SI-2/SI-3), aber bewusst deferred |
| architektur_design | **3** | Loop-Design stark (Spec-SoR, Manifest-Gate, kind-Klassifikation, B evidenzbasiert verworfen); signifikante Abweichungen: anyOf-Regression (EF-2) + infer-asserts-Selbstwiderspruch (EF-3) |
| code_konventionstreue | **4** | ruff clean, `test_should_*`, `main_cli`, 192 Tests; neue Module konsistent; kleine Mängel (F841 im Prozess gefangen) |
| risiko_debt | **2** | genesor-Security ungefixt (SI-3, HOCH) + anyOf-Netz-Verlust (EF-2) + toter Inferenz-Kandidat (EF-3) + ungemessenes Kill-Gate released (EF-4) — mehrfache neue Debt, Rework nötig |
| prozess_effizienz | **3** | Hoher Durchsatz (20 Merges/26h), aber Rework: Parallel-Kollision 131 Zeilen (PK-1), Suite-Drift-Nachbesserung (PK-4), reaktiver Breaking-Change (PK-5) |
| entscheidungsqualitaet | **4** | B evidenzbasiert verworfen (3%), externe Zweitmeinung eingeholt, Phase-C bewiesen, Flow-Knoten VOR Publish gefangen; Abzug: EF-4 (Release vor Kill-Gate-Messung) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| RCE-Härtung #102 fixte nur `gen_e2e.load_spec`; genesor-Pfad blieb roh (`grep` scan/ucs = nur safe_load) | Security-Fix **sink-getrieben statt aufrufstellen-getrieben**: bei einem Injection/XSS-Fund eine `grep`-Inventur ALLER Einspeise-Pfade (hier: alle `yaml.safe_load`+Render-Sinks) machen, dann als geteilte Validierungsschicht fixen | #SI-3 |
| `screens.items` von uniform-required auf `anyOf` gelockert (#122), ohne Test für „Assertions-Screen ohne parity_acceptance aber mit next_screens" | Bei Schema-**Lockerung** einen expliziten Negativ-Test für die neu-erlaubte Grauzone + einen Diskriminanz-Marker (`screen_kind`) statt struktureller anyOf-Heuristik | #EF-2 |
| `infer_one` markiert templated-testid-Kandidat als `kind:executable` obwohl `note` „nicht exakt zählbar" warnt | Wenn die Heuristik selbst einen ⚠-Vorbehalt setzt, **downgrade `kind→behavioral-manual`** statt executable — Selbstwiderspruch im Code eliminieren + Test „templated → nicht executable" | #EF-3 |
| `infer_asserts` in 1.30.0 released, Kill-Gate-Ledger-L3 „⚠️ offen" | **Release-Freigabe an offene `kill_criteria`-Ledger-Zeilen koppeln**: eine Komponente mit ungemessenem Kill-Gate wird `experimental`-markiert oder nicht in den stable-Release aufgenommen | #EF-4 |
| 13 Audit-Issues angelegt, 0 abgearbeitet, obwohl Report „diese Woche abarbeiten" sagte | Bei Audit-Läufen die **HOCH-Severity-Befunde in derselben Session anfassen** (oder explizit im Handover als „nicht angefasst, Grund X" markieren) statt still zu parken | #SI-2 |
| Zwei Sessions bauten #95/#96 vs #97/#98 zum selben Issue (Memory existierte, griff nicht) | **Gate statt Memo:** `repo-session.sh start` prüft vor Branch-Anlage `gh pr list --search "<issue>"` + warnt bei offenem PR/Branch zum selben Issue (Recurrence ≥2 → Enforcement) | #PK-1 |
| risk-hub #368: Spec editiert, Suite nicht re-generiert → Gate rot → Nachbesserung | Nach jeder Spec-Änderung in einem KD-Repo **im selben Commit `klickdummy-gen-e2e` re-run** (Pre-Commit-Hook/Makefile-Target), damit Suite nie driftet | #PK-4 |
| 1.30-Breaking-Change erst durch echten risk-hub-Lauf entdeckt, nach Release-PR-Öffnung | **Adopter-Smoke-Test VOR dem Release-PR**: das neue Paket gegen den realen Haupt-Adopter (risk-hub ex-schutz) laufen lassen, bevor `#117` geöffnet wird — „fixen, dann Release-PR" | #PK-5 |
| `kind`-Default `executable` ohne CHANGELOG-Migrationshinweis | Bei defaultet-brechenden Feldern **einen expliziten Adopter-Migrationsabschnitt** im CHANGELOG (wie beim `ruff format`-Blocker schon vorbildlich getan) | #EF-5 |
| Scope-Checkpoint (3. Repo/Publish) nur im Chat, kein Artefakt | Scope-Übergang **einmal im PR-Body spiegeln** („dieser PR ist Repo #N / Prod-Schritt — Freigabe: <Zitat>") — macht die Hausregel artefakt-prüfbar | #SI-1 |
| v1.29.0 im CHANGELOG ohne Tag | **Tag-vor-CHANGELOG-Heading-Regel**: ein `## [X.Y.Z]`-Heading nur committen, wenn `git tag vX.Y.Z` gesetzt wird (oder als `[Unreleased]` führen) | #SI-5 |
| `__REPO_LABEL__` roh in HTML (gleiche Klasse wie S-01) | Beim S-01-Fix **alle Template-Platzhalter** (nicht nur die JSON-Insel) durch denselben Escape-Pfad — sink-vollständig statt sink-einzeln | #EF-7 |

## 5. Längsschnitt (retro_kpis.py über bestehende Retros)

`python3 platform/tools/retro_kpis.py` (4 Reports in `platform/docs/retros`):
- 🚨 **`claim-before-cheapest-check` ×4 → GATE-PFLICHT** — **EF-4 ist Vorkommen 5** (Komponente released vor Kill-Gate-Messung = „gebaut ≠ validiert").
- 🚨 **`scope-checkpoint-not-durably-recorded` ×1 → mit SI-1 jetzt ×2 → GATE-PFLICHT.**
- 🚨 **`parallel-session-pr-collision`** — die Auto-Memory dazu existiert seit letzter Session (`~/.claude/projects/…/memory/parallel-session-pr-collision.md`, per `ls` verifiziert); die Kollision recurred diese Session (PK-1) → **Memo wirkungslos, Gate nötig.**
- refuted_rate diese Session **0,25** (>0,2) — gegen den jüngsten Trend (letzte 3 <0,2 „Falsifikation Theater") ein **gesunder** Wert: EF-1-Kritisch→REFUTED ist eine echte Falsifikation.

## 6. Verankerung (Vorschläge — Mensch entscheidet)

**memory_candidates:**
1. `feedback`/drift `genesor-security-unvalidated-path` — „Security-Fix an EINER Aufrufstelle (gen_e2e.load_spec) deckt den Parallel-Pfad (genesor/scan→ucs→render_uc/lineage) NICHT. Bei Injection/XSS-Fund immer sink-getriebene grep-Inventur, dann geteilte Validierungsschicht. Beleg: SI-3, Issues #103/#105/#106." **Why:** RCE-Härtung wirkte vollständig, war aber halb. **How:** grep alle `yaml.safe_load`+Render-Sinks vor „gefixt".
2. `feedback` `infer-heuristic-self-contradiction` — „Wenn eine Heuristik selbst einen ⚠-Vorbehalt in den Kandidaten schreibt, darf sie ihn nicht gleichzeitig als `executable`/stabil klassifizieren (EF-3). Der note-vs-kind-Widerspruch ist das Bug-Signal."

**adr_candidates:** keiner (alle Befunde sind Repo-lokal / Prozess — kein Architektur-Reversal; ADR-Schwelle nicht erreicht).

**Gate-Verankerung (Recurrence ≥2, PFLICHT — kein Memo):**
- `parallel-session-pr-collision` → `repo-session.sh start` um einen `gh pr list --search "<issue>"`-Vorcheck erweitern (Warnung bei offenem PR/Branch zum selben Issue).
- `claim-before-cheapest-check` → Release-/„fertig"-Gate: eine Komponente mit offener `kill_criteria`-Ledger-Zeile bekommt `experimental`-Marker, nicht stable-Release.
- `scope-checkpoint-not-durably-recorded` → PR-Template-Zeile „Scope/Freigabe" bei 3.-Repo/Publish.

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)

🟢 **Dein Zug**

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | genesor-Security fixen (S-02 render_uc-Sanitize + S-03 lineage `.name`/Pattern-Check + AD-6 scan-Validierung) | iil-klickdummy | #103/#105/#106 | 🟢 offen | HOCH — priorisieren; Fix als geteilte Validierungsschicht (du/Queue) |
| 2 | EF-2 anyOf-Netz + EF-3 infer-`kind`-Downgrade + EF-4 experimental-Marker | iil-klickdummy | — | 🟢 offen | 1 Sammel-PR (Schema-Negativtest + kind-Fix + Ledger-Status) (ich, auf dein Wort) |
| 3 | Gate: `repo-session.sh` Pre-Start `gh pr list`-Check (Recurrence-Pflicht) | platform | — | 🟢 offen | platform-PR (Governance-Scope, deine Freigabe) |

🔵 **Ich sofort (gate-frei, auf dein Wort)**

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 4 | EF-5/EF-7/SI-5 Kleinfixes (CHANGELOG-Migrationshinweis · `__REPO_LABEL__`-Escape · Tag-vor-Heading-Regel) | iil-klickdummy | 🔵 ready | 1 PR |
| 5 | 2 memory_candidates schreiben (nach deiner Freigabe) | — | 🔵 ready | Memory-Dateien |

## 8. Nicht verifiziert (Restlücken)

- **`retro_kpis.py` liest `platform/docs/retros`, nicht `~/shared/`** — dieser Report landet in `~/shared/` (Skill-Vorgabe) und wird vom Längsschnitt-Tool **nicht automatisch gezählt**, bis er auch nach `platform/docs/retros` gespiegelt wird (platform-Governance-Schritt, nicht in dieser Runde gemacht). Billigster Check: `ls platform/docs/retros/`. Zusätzlich hat `retro_kpis.py` einen Slug-Parse-Glitch (Kommentar-Zeilen als Slugs gezählt) — eigener Tool-Fix, out-of-scope.
- **SI-1 / SI-4 Chat-Ebene:** die starke Form beider (Checkpoint fand nicht statt / Gate unterlaufen) ist aus Artefakten **nicht** beweisbar und wurde REFUTED; ob die Chat-Freigaben ausreichend explizit waren, kann dieser artefakt-basierte Retro nicht entscheiden — bewusst offen gelassen.
- **EF-3 Real-Impact:** der tote count-Assert wurde in ex-schutz vom Menschen zu `[data-testid^=step-]` korrigiert (funktioniert); ob andere Adopter den rohen Tool-Kandidaten ungeprüft übernehmen, ist nicht gemessen — billigster Check: infer-asserts-Ausgabe über das KD-Portfolio.
