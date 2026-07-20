---
retro_schema: 1
date: 2026-07-02
repo_scope: [platform, tax-hub]
session_id: 54a76c
footprint: full
findings_total: 12
findings_survived: 6
refuted_rate: 0.17
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, closes-issue-requires-all-acceptance-checked]
gate_candidate_basis:
  claim-before-cheapest-check: "recurring ×4 (kpis-Live über 4 Retros inkl. diesem; EF-1 = zirkuläre-Selbst-Verifikations-Variante, die das vorhandene Gate nicht greift)"
  closes-issue-requires-all-acceptance-checked: "SI-1 mittel-hoher Survivor mit direkter main-Regression (toter Doc-Ref)"
recurring_findings: [claim-before-cheapest-check]
# Auswertungs-Transparenz (zusätzlich zum schema-Pflicht-refuted_rate oben):
phase3_examined: 8          # SI-1,SI-2,EF-1,EF-4,EF-2,PK-3,PK-4,PK-5 (skeptiker-adjudiziert)
grounded_unchecked: 4       # SI-3,EF-3,EF-6,PK-6 (geerdet, nicht skeptiker-geprüft)
phase3_refuted_rate: 0.25   # 2/8 — Falsifikations-Quote NUR auf dem adjudizierten Subset
# refuted_rate: 0.17 oben = schema-Definition (phase3_refuted+pre_refuted)/findings_total = 2/12
---

# Session-Retro 2026-07-02 — platform + tax-hub-Folgefix (Strang: repo-optimize → Secret-Rotation → Skill-Optimierung → MCP-Sweep)

> Methode: 1 Collector (haiku) + 3 Finder (sonnet, je Dimension) + 3 Skeptiker (sonnet, binäre
> Falsifikation) + Meta (Phase 5). Richter≠Angeklagter: alle Befunde aus frischem Artefakt-Kontext.
> Attribution: Session geerdet an der Turn-Historie = der repo-optimize-Strang; Parallel-Session-
> Artefakte (ADR-259-Kollision, repo-ux-opt-Löschung) sind NICHT gewertet.

## 1. Executive Summary

- Großer, **überwiegend PR-basiert reversibler + explizit freigegebener** Strang: **14 von mir authorte
  gemergte PRs** (das Prozess-Auswertungsset umfasst 17 — die 3 zusätzlichen #822/#812/#834 habe ich nur
  gemergt, nicht authort, Parallel-Sessions); 26/26 geleakte Secrets rotiert (P0 geschlossen — **operativ
  abgeschlossen, nicht trivial reversibel**), 3 Skills optimiert, 82 MCP-Prefix-Call-Sites migriert.
- **6 Befunde überleben die Falsifikation; keiner kritisch, höchster Schweregrad mittel-hoch (SI-1)** —
  konsistent mit der Dichte-Regel (reversibel+transparent+freigegeben → harte Survivors selten).
- **Wichtigster Längsschnitt-Hebel:** EF-1 (Validierungsquery == Implementierungsquery) ist eine weitere
  Instanz von `claim-before-cheapest-check` — laut `retro_kpis.py` (Live) jetzt **×4 über 4 Retros**
  (`0181a7-incr, 73003f, a50bc6, 54a76c`), längst gate-pflichtig, aber das vorhandene Gate greift die
  zirkuläre-Selbst-Verifikations-Variante nicht. Kein N-tes Memo, sondern strukturelle Verankerung nötig.
- Zwei ehrliche Zielverfehlungen: SI-1 (#817 mit unerfülltem Akzeptanzkriterium geschlossen → toter
  api.md-Verweis auf main) und SI-2 (tax-hub#20 mergebar + admin-Recht, aber nicht gemergt → tax-hub-CI
  bleibt rot).
- 2 REFUTED (EF-2 „Lücke ungetrackt" — ist via #819 getrackt; PK-5 „Worktree-Orphans" — Reaper
  funktioniert korrekt, alle 4 „Orphans" sind lease-/PR-geschützt und stammen aus Fremd-Sessions).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| SI-1 | #829 schloss #817 („Closes"), obwohl Akzeptanzkriterium 2 offen: toter `concepts/pptx-hub/...`-Verweis in `docs/reference/api.md` bleibt auf main; kein Folge-Issue | fehlende-Validierung | mittel-hoch | **SURVIVES** | api.md:9,13 (ref=main) + gh pr diff 829 (Pfad gelöscht) + #829-Body Kriterium unabgehakt | neu |
| SI-2 | tax-hub#20 mergeable + Autor hat admin/push, aber nicht gemergt → Issue-Triage-Workflow bleibt rot (Run 12:39 failure) | fehlende-Validierung | mittel | **SURVIVES** | gh pr view 20 (OPEN, mergedAt null) + gh run list (failure post-PR) + repo-perms admin:true | neu |
| EF-1 | mcp-Sweep #842 nutzte Regex `mcp[0-9]_` (einstellig), behauptete Vollständigkeit, übersah 2 zweistellige `mcp14_` → Nachzug #843; Verifikationsquery == Implementierungsquery (zirkulär) | fehlende-Validierung | niedrig-mittel | **SURVIVES** | #843-Body-Geständnis + #842-Body Vollständigkeitsclaim + Diff | **×4** (kpis-Live über 4 Retros) |
| EF-4 | 5 Workflow-PRs (#822/#828/#839/#842/#843) ohne dokumentierten `/workflow-review`-Beleg — nur #828 nennt die Konvention (als Reminder, kein Nachweis), 4 gar nicht; CORE_CONTEXT:98 verlangt ihn unqualifiziert | Konventionsverstoß | niedrig | **SURVIVES** (Schwere ↓) | CORE_CONTEXT.md:98 + `gh pr view` je PR (workflow-review-Erwähnung: #828=1, andere=0); nur Signatur-CI-Gates liefen (anderes Gate) | neu |
| PK-3 | 2 PRs mit manuell aufgelösten Textkonflikten gegen zwischenzeitlich gemergte main (#829 CORE_CONTEXT.md, #832 tools-tests.yml) | Prozesslücke | mittel | **SURVIVES** | Merge-Commits ca22340/de90639 mit `# Conflicts:`-Blöcken | neu |
| PK-4 | 11/17 PRs mit Catch-up-Merge-Commit → Rebase-Tax durch sequenzielles Kleinst-PR-Selbstmergen (nicht Fremd-Session-induziert) | Prozesslücke | niedrig-mittel | **SURVIVES** (11/17 korr.) | gh pr view --json commits über 17 PRs, alle self-merged 09:27–12:45 | neu |
| EF-2 | guardian-Fix #833 ließ TestG003 rot + agents/tests CI-blind, angeblich ungetrackt | Tech-Debt | — | **REFUTED** | #833-Body verweist wörtlich auf #819 (Lücke IST getrackt) | — |
| PK-5 | 4 alte Worktrees = Orphan-Akkumulation, Reaper lief nicht | Werkzeug | — | **REFUTED** | worktree-reaper --dry-run: 0 entfernbar, alle 4 lease-/PR-geschützt, keiner aus 2026-07-02 | — |
| SI-3 | 2/5 O-Issues geschlossen, Rest offen mit dokumentiertem Scope + neues Deferred #841 | Kommunikation | niedrig | geerdet (nicht skeptiker-geprüft) | gh issue-States + git grep origin/main (23 Rest-Token = exakt #841-Scope) | neu |
| EF-3 | permissions-Flip write→read live, aber kein dokumentierter grüner Voll-Lauf aller 27 WF post-Flip | Prozesslücke | niedrig | geerdet | gh api actions/permissions = read; #831-Testplan-Checkbox offen | neu |
| EF-6 | guardian `non_live_prefixes` als hartes Tupel ohne SSoT-Verweis (Hardcoding-Muster) | verfrühte-Festlegung | niedrig | geerdet | agents/guardian.py Diff #833 | neu |
| PK-6 | Self-Approval-Pattern (author==mergedBy==achimdehnert bei allen 17 PRs) | Kommunikation | info | geerdet (Finder-selbst-schwach) | gh pr list --json mergedBy | wiederkehrend |

**Nicht gewertet (Parallel-Session, nicht dieser Strang):** ADR-259↔261-Nummernkollision (#708/#812);
uncommittete `repo-ux-opt.md`-Löschung im geteilten Tree (Fremd-Session — Risiko-Notiz: nie `git add -A`).

## 3. Scorecard (1–5, ganzzahlig, an Befunde verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | P0 (26 Secrets), Skills, MCP-Sweep, DX geliefert; kleine Mängel SI-1 (toter Doc-Ref) + SI-2 (tax-hub-CI rot) |
| architektur_design | **4** | guardian-Fix sauber (Regressionstest schützt Live-Code), suffix-getriebener Sweep gut begründet, adr_* ehrlich deferred; minus EF-6 Hardcoding |
| code_konventionstreue | **3** | EF-4 SURVIVES (workflow-review über mehrere PRs übergangen); sonst Commits sauber (kein add -A, keine Backticks) |
| risiko_debt | **4** | Session **reduzierte** Risiko massiv (Secret-Rotation, gitleaks-Gate, permissions read); neue Debt minimal + getrackt |
| prozess_effizienz | **3** | PK-3 (2 Konflikte) + PK-4 (11/17 Rebase-Tax) + EF-1 (Rework-PR #843) = reale Reibung; platform-Strang gelandet, **tax-hub#20 blieb offen** (SI-2) |
| entscheidungsqualitaet | **3** | stark: adr_* nicht geraten, #841 ehrlich, Secret-Rotation methodisch; minus SI-1/SI-2 (Judgment-Lücken) + EF-1 (zirkuläre Selbst-Verifikation) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #) — Invariante |Soll| == 6 Survivors

> Alle 6 Survivors sind hier gemappt UND haben ein Action-Board-Item (§7): SI-1→R-0/R-2, SI-2→R-3,
> EF-1→R-1, EF-4→R-5, PK-3→R-6, PK-4→R-7. Keine Survivor-Lücke im Board (Review-Fix).

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| „Closes #817" bei unabgehaktem Akzeptanzkriterium → toter api.md-Verweis landet auf main (#829-Body) | Issue nur mit „Closes" schließen, wenn ALLE Akzeptanz-Checkboxen ✅; ein offener Punkt → Issue offen lassen ODER vor dem Close ein Folge-Issue anlegen und referenzieren | #SI-1 |
| tax-hub#20 grün + admin-Recht, aber als „Owner-Entscheid" geparkt → tax-hub-CI bleibt 7h+ rot (gh run failure) | Wenn Merge-Recht vorhanden UND Fix grün+secret-frei: in derselben Session mergen; nur die echte Owner-Alternative (PROJECT_PAT-Secret) parken, nicht den secret-freien Fix | #SI-2 |
| Vollständigkeits-Check des Sweeps nutzte denselben `mcp[0-9]_`-Regex wie die Implementierung (zirkulär) → 2 `mcp14_` still übersehen | Der Verifikations-Query muss vom Implementierungs-Muster **unabhängig** sein: breiter greppen (`mcp[0-9]+_`) als der Bau-Regex, bevor „vollständig/Rest = X" behauptet wird (claim-before-cheapest-check) | #EF-1 |
| 4/5 Skill-PRs ohne `/workflow-review`-Beleg, obwohl CORE_CONTEXT:98 ihn unqualifiziert verlangt | Bei `.windsurf/workflows/`-Änderung entweder `/workflow-review` laufen lassen + Output im PR-Body zitieren, ODER die Ausnahme (rein mechanischer Sweep) explizit im PR-Body begründen — nie stillschweigend überspringen | #EF-4 |
| #829/#832 liefen während Bearbeitung aus main heraus → manuelle Textkonflikte | `gh pr update-branch` unmittelbar vor dem finalen Push/Merge (rebase-on-ready), nicht früh — verkürzt das Konflikt-Fenster | #PK-3 |
| 11/17 PRs mit Catch-up-Merge durch sequenzielles Kleinst-PR-Selbstmergen gegen wandernden main | Thematisch verwandte kleine Änderungen (z.B. DX + Doku-Karte + Kleinfixes) in weniger, breitere PRs bündeln, wo sie nicht kollidieren; sonst in Abhängigkeits-Reihenfolge mergen ohne jeden Branch einzeln zu update-branchen | #PK-4 |

## 5. Längsschnitt (retro_kpis.py — Pflicht)

`python3 tools/retro_kpis.py` (2026-07-02) über die Vor-Reports:

- 🚨 **`claim-before-cheapest-check` ×4 → GATE-PFLICHT** (Live-Lauf: Slugs `0181a7-incr, 73003f, a50bc6,
  54a76c` — inkl. dieser Retro; zusätzlich neu ×2: `lint-failure-no-local-gate`, `planned-phase-no-issue`
  aus Parallel-Session a50bc6). **EF-1 ist die aktuelle Instanz.** Das Muster ist längst als gate-pflichtig
  markiert, aber die vorhandenen Gates (`evidence_claim_scanner.py`-Hook, CLAUDE.md-Regel) fangen die
  **zirkuläre-Selbst-Verifikation-Variante** nicht: „ich habe geprüft" mit demselben Werkzeug, das den Fehler
  baute. Das ist der eigentliche Skill-Hebel dieser Retro → siehe gate_candidates.
- `refuted_rate`-Band: bisher nur 2 Reports (0.09, 0.00); dieser Report 0.17 — erst ab 3 als Band wertbar.
- **Zwei Quoten, sauber getrennt (Review-Fix):** (a) schema-`refuted_rate` = `(phase3_refuted+pre_refuted)/
  findings_total` = 2/12 = **0.17** (Report-Gesamtquote über ALLE 12 In-Scope-Befunde, inkl. der 4 geerdet-
  ungeprüften). (b) **Adjudizierte Falsifikations-Quote** = `phase3_refuted/phase3_examined` = 2/8 = **0.25**
  (nur die 8 skeptiker-adjudizierten). Die 0.25 ist die aussagekräftigere Skeptiker-Schärfe; beide gesund —
  die 2 REFUTED sind echte Skeptiker-Fänge (EF-2 getrackt, PK-5 Reaper-korrekt), keine vorgewiderlegten
  Strohmänner (pre_refuted=0).

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates:**
1. `feedback_verification_query_must_be_independent_of_impl` (drift): Bei „vollständig/Rest = X"-Claims
   nach einem Sweep/Refactor den Verifikations-Query **breiter/anders** als das Implementierungs-Muster
   ziehen — sonst wandert der Bau-Blindfleck ungeprüft durch (Realfall 2026-07-02: Sweep-Regex `mcp[0-9]_`
   einstellig, Verifikation mit demselben Regex → 2 `mcp14_` still übersehen, #842→#843). Instanz von
   [[claim-before-cheapest-check]], Variante „zirkuläre Selbst-Verifikation".
2. `feedback_closes_issue_requires_all_acceptance_checked`: „Closes #N" nur, wenn ALLE Akzeptanz-Checkboxen
   erfüllt; ein offener Punkt → Issue offen lassen oder Folge-Issue vor dem Close anlegen. Realfall
   2026-07-02: #829 schloss #817 mit unabgehaktem Kriterium → toter Doc-Verweis auf main, kein Tracking.
3. `feedback_merge_own_green_fix_when_permitted`: Wenn Merge-Recht vorhanden UND Fix grün+secret-frei, in
   derselben Session mergen statt als „Owner-Entscheid" parken (nur echte Owner-Sachen — PAT/Secret — parken).
   Realfall 2026-07-02: tax-hub#20 grün + admin, nicht gemergt → tax-hub-CI blieb rot.

**adr_candidates:** keine — alle Befunde sind Prozess/Konvention, keine Architektur-Entscheidung (adr-threshold).

## 7. Maßnahmen (Action Board, aus Soll-Ablauf abgeleitet)

🟢 dein Zug · 🔵 ich sofort · 🟡 wip · ✅ done

Jede Zeile trägt eine **DoD** (Definition of Done, prüfbar). Owner-Kürzel: User=Mensch · Agent=ich.

| # | Item (Survivor) | Repo | Ref | DoD | Status | Next Step |
|---|---|---|---|---|---|---|
| R-0 | ✅ **PR #848** — .github/pull_request_template.md (Issue-Bezug-Checkbox). Gate/Template `closes-issue-requires-all-acceptance-checked` (SI-1, gate_candidate #2): „Closes #N" nur, wenn alle Akzeptanz-Checkboxen ✅ ODER Folge-Issue verlinkt | platform | Gate/Template-PR | PR-Body-Check oder Review-Checkliste erzwingt es; ein Testfall dokumentiert | ✅ done | #848 gemergt |
| R-1 | ✅ **PR #848** — evidence-discipline.md §How-to-apply Punkt 5. GATE `claim-before-cheapest-check` / Variante zirkuläre Selbst-Verifikation (EF-1, ×4): „Verifikations-Query ≠ Implementierungs-Query" | platform | Gate-PR (kpis ×4) | `evidence_claim_scanner.py` ODER CLAUDE.md fordert bei „vollständig/Rest"-Claims einen unabhängig-breiteren Query; `mcp[0-9]_` vs `mcp[0-9]+_`-Testfall existiert | ✅ done | #848 gemergt; claude-policy-sync = Owner |
| R-2 | ✅ **PR #850** — 3 stale Sektionen (pptx_hub + 2× governance-deploy) aus api.md entfernt (R-2 deckte 2 zusätzliche auf) | platform | #850, Folge #817 | `grep pptx` = 0 ✓ | ✅ done (Merge läuft) | — |
| R-3 | ✅ SI-2 geschlossen: tax-hub#20 **gemergt** (14:32Z); Triage-Fallback jetzt auf main. Rest: Triage-WF läuft erst bei nächstem `issues:opened` (kein workflow_dispatch) | tax-hub | #20 | #20 gemergt ✓ | ✅ done | — |
| R-4 | 3 memory_candidates verankern (§6) | — | CC-Memory | 3 Memory-Dateien + MEMORY.md-Index-Zeilen existieren | ✅ done | — |
| R-5 | ✅ **PR #851** — CORE_CONTEXT:98 präzisiert: enge Ausnahme für mechanische Sweeps (gate-gedeckt), substanzielle Änderungen weiter review-pflichtig | platform | #851 | Ausnahme dokumentiert ✓ | ✅ done (Merge läuft) | — |
| R-6 | ✅ **PR #848** — session-ende Phase 3.1. PK-3: Rebase-on-ready-Regel — `gh pr update-branch` erst unmittelbar vor finalem Push/Merge | platform | Prozessregel/Skill | Regel in session-ende/CLAUDE.md; nächste Retro misst Konflikt-Rate | ✅ done | #848 gemergt |
| R-7 | ✅ **PR #848** (bündelt sich selbst). PK-4: Bundling-Heuristik für Kleinst-PRs (thematisch gekoppelte Kleinfixes bündeln) senkt Catch-up-Merge-Tax | platform | Prozessregel | Schwelle definiert; ODER bewusst als akzeptierte Prozesskost markiert | ✅ done | #848 gemergt |
| ✅ | Secret-Rotation P0, Skills v2.1, MCP-Sweep, DX, guardian-Fix | platform | #823-843 | — | ✅ done | — |

## 8. Nicht verifiziert (Restlücken)

- **Testqualität** der 56 neuen Tests aus #832 (nur Struktur/Zählung geprüft, nicht ob sie echtes Verhalten
  prüfen). Billigster Check: 1 Test gezielt brechen und `pytest` rot sehen.
- **guardian G-002-Nebenwirkungen** auf *andere* Live-Code-Löschungen (#833 nur „entblockt #829" bestätigt,
  Regressionstest deckt 1 Positivfall). Billigster Check: einen echten `apps/.../views.py`-Serializer-Delete
  durch guardian jagen → muss weiter Gate-2 feuern.
- **PK-6 Self-Approval-Reibung** nur strukturell belegt (author==mergedBy), nicht die Classifier-Block-Häufigkeit
  selbst. Billigster Check: Transkript-Grep nach „Permission … denied by the Claude Code auto mode classifier".
- **EF-3 Permissions-Flip:** `actions/permissions = read` ist live, aber es gibt **keinen dokumentierten grünen
  Voll-Lauf aller 27 Workflows nach dem Flip** — die Scorecard `risiko_debt=4` verbucht die Reduktion positiv,
  ohne diesen Beweis. Billigster Check: gezielter Full-Workflow-Lauf bzw. `gh run list` nach dem Flip-Zeitpunkt,
  Run-ID im Report nachtragen.

## Repro-Appendix (Auditierbarkeit)

```
gh issue view 817 --repo achimdehnert/platform --json state,closedAt
gh api repos/achimdehnert/platform/contents/docs/reference/api.md?ref=main --jq .content | base64 -d | grep -n pptx
gh pr diff 829 | grep concepts/pptx-hub
gh pr view 20 --repo iilgmbh/tax-hub --json state,mergedAt,mergeable
gh run list --repo iilgmbh/tax-hub --workflow "Issue Triage" --limit 5
gh pr view 842 --json body      # Vollständigkeits-Claim
gh pr diff 843                   # 2× mcp14_ (zweistellig)
git show -s --format=%B ca22340  # #829 Conflict CORE_CONTEXT.md
git show -s --format=%B de90639  # #832 Conflict tools-tests.yml
python3 tools/worktree-reaper.py  # PK-5: 0 entfernbar (lease/PR-geschützt)
python3 tools/retro_kpis.py       # claim-before-cheapest-check ×2 → GATE
```

---
Fußzeile: HEAD-SHA bei Retro 28c8861 · Footprint full · 1 Collector(haiku)+3 Finder+3 Skeptiker(sonnet) ·
Bilanz **6 SURVIVES · 2 REFUTED · 4 geerdet-ungeprüft** (von 12 in-scope; 2 Parallel-Session-Artefakte nicht gewertet) ·
refuted_rate 0.17 · Coverage-Disclaimer: Einzel-Lauf, nicht erschöpfend.
