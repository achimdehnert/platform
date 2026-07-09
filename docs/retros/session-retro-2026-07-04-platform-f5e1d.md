---
retro_schema: 1
date: 2026-07-04
repo_scope: [platform, odoo-hub, nl2cad, cad-hub, risk-hub, ttz-hub, aifw, bfagent]
session_id: f5e1d
footprint: deep
findings_total: 15
findings_survived: 12
refuted_rate: 0.20
phase3_refuted: 3
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [handover-stale-vor-merge, worktree-midsession-accumulation, claim-before-cheapest-check]
recurring_findings: [handover-stale-vor-merge, worktree-midsession-accumulation, claim-before-cheapest-check, prod-as-test-environment, pii-in-public-fixtures, pr-body-stale-after-scope-change, changelog-skipped-for-ci-files, v18-v19-addon-duplication, tracking-misses-pr-body-risks, dispatch-wrong-ref-under-pressure]
---

# Session-Retro 2026-07-04 — NL2X-Fleet-Session (Audit → WPs → odoo-Incident)

Session-Umfang laut Artefakten: NL2X-Fleet-Audit (platform#917), 7 Umsetzungs-PRs über 6 Repos
(nl2cad#38/#39, cad-hub#31 offen, risk-hub#377, ttz-hub#24, aifw#31, odoo-hub#11/#12),
Tracking-Issue platform#913, ein Prod-Incident odoo.iil.pet (17:24–17:46 UTC) mit Recovery.
Methode: deep — 1 Collector (haiku) + 3 Finder + 3 gebündelte Skeptiker + Meta-Reviewer (sonnet),
Richter≠Angeklagter durchgehend eingehalten.

## 1. Executive Summary

- **Kernziel erreicht:** Alle gate-freien Arbeitspakete des Audits umgesetzt, gemergt und
  verifiziert; der schwerste Sicherheitsbefund (WP1, LLM-SQL auf RW-Cursor) ist in Prod; das
  seit ≥2026-04-29 nie funktionsfähige odoo-Auto-Deploy läuft erstmals grün.
- **Teuerster Fehler:** Der „Wiring-Beweis" für den Deploy-Workflow-Fix lief mangels
  parametrisierbarem Ziel zwangsläufig **gegen Prod** und löste einen 22-Minuten-Ausfall aus —
  obwohl eine vollwertige Staging-Compose im Repo existiert (F-E1/F-E2, beide SURVIVES).
- **Gefährlichste Unterlassung:** Der PII-Fund in den öffentlichen nl2cad-Fixtures (G5) blieb
  den ganzen Tag ohne Interims-Schadensbegrenzung, während niedriger priorisierte Pakete
  gemergt wurden (F-S2, kritisch, SURVIVES).
- **Doku-Drift am selben Tag:** Handoff-Dokument und CC-Memory froren um ~13:00 ein; Issue #913
  lief bis 17:49 weiter — eine Folge-Session sähe einen falschen Gate-Stand (F-S3/F-P3).
- **Falsifikation wirkte:** 3 von 15 Befunden fielen (Erkennung des Pipeline-Fails WAR 2h54m vor
  dem Dispatch dokumentiert; actionlint+shellcheck finden den Heredoc-Bug empirisch NICHT;
  Alt-PR cad-hub#24 war nie Audit-Scope) — refuted_rate 0,20, Band gesund.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F-S1 | Deploy-Fails 5×/4,5h „nicht erkannt/eskaliert" vor Dispatch | Prozesslücke | kritisch | **REFUTED** | GraphQL userContentEdits #913: G7 dokumentiert 14:17:32Z = 2h54m VOR Dispatch 17:22:00Z; Run-Serie 12:56–17:22 bestätigt, aber Erkennung lag vor | — |
| F-S2 | PII in Fixtures eines PUBLIC-Repos ohne Interims-Mitigation, während 🟡-WPs gemergt wurden | Prozesslücke | kritisch | SURVIVES | `gh api repos/achimdehnert/nl2cad` → public; `packages/nl2cad-core/tests/fixtures/minimal.ifc` 37.981.923 B, E-Mail-/Telefon-Muster im Header (2×/3×); #913+Handoff: nur „Entscheidung Achim", kein Interims-Schritt | pii-in-public-fixtures ×1 |
| F-S3 | CC-Memory führt WP1 als „schwersten offenen Punkt", obwohl gemergt+deployt; G7/Incident fehlen | Prozesslücke | hoch | SURVIVES | memory/nl2x-fleet-audit-handoff.md Z.16 vs. #913 `[x] G2→WP1` + G7-Resolution 17:49:36Z | handover-stale-vor-merge (Familie) |
| F-S4 | Retro-Collector erzeugte Falsch-Negativ „nl2cad ohne CI" durch unverifizierte Org-Annahme (iilgmbh statt achimdehnert) | Werkzeug / fehlende Validierung | mittel | SURVIVES | `gh api repos/iilgmbh/nl2cad` → 404; `gh run list -R achimdehnert/nl2cad` → grüne Runs 2026-07-04; Ursache: mehrdeutige Repo-Liste im Collector-Prompt | claim-before-cheapest-check ×12, bereits Gate-pflichtig |
| F-E1 | „Wiring-Beweis"-Dispatch = voller Prod-Deploy → Incident selbst ausgelöst; billigere Prüfung existierte (actionlint fand Bug 1 kostenlos; Staging existierte) | verfrühte Festlegung / Prozesslücke | kritisch | SURVIVES | Run 28713878976: SOPS→SSH→rsync→compose→`odoo -u` gegen root@46.225.127.211, Health-Fail 17:24:39Z; actionlint gegen `bc17583~1` → `context "secrets" is not allowed here`; PR#12 0 Reviews (Solo) | prod-as-test-environment ×1 |
| F-E2 | Staging existiert vollwertig (docker-compose.staging.yml, ports.yaml `domain_staging`), war aber im Workflow nicht anwählbar (DEPLOY_HOST hart, dispatch ohne inputs) | Prozesslücke / fehlende Validierung | hoch | SURVIVES | compose-Datei mit v18/v19-Profilen+Healthchecks; `_deploy-odoo-hub.yml` env-Hardcode, `workflow_dispatch:` ohne `inputs:`; kein Staging-Workflow-File | prod-as-test-environment |
| F-E3 | Zweiter Workflow-Bug (Heredoc) war „mit Standard-Tooling findbar", Voll-Audit unterlassen | fehlende Validierung | hoch | **REFUTED** | Empirisch: actionlint v1.7.12 + shellcheck v0.9.0 gegen `bc17583`-Stand → exit 0 / keine relevante Meldung (Bug liegt 3 Ebenen tief: YAML→SSH-String→Heredoc); Prämisse „findbar" falsch | — |
| F-E4 | PR#12 (incident-auslösend, Semantik-Änderung skip→fail) ohne CHANGELOG — obwohl Repo-Historie Workflow-Änderungen dort führt | Konventionsverstoß | mittel | SURVIVES | `git show 2272eae --stat` (Workflow-Anlage MIT Changelog), PR#11 mit Changelog; `bc17583`/`8260831` ohne | changelog-skipped-for-ci-files ×1 |
| F-E5 | Security-Fix doppelt in v18/v19 gepatcht; realer API-Diff nur 6 Zeilen (`json`↔`jsonrpc`) → Duplikat-Debt vermeidbar | verfrühte Festlegung | mittel | SURVIVES | `diff addons/... addons_v19/...` → 6 Zeilen von ~800; PR#11 438-LOC-Doppel-Diff | v18-v19-addon-duplication ×1 |
| F-E6 | risk-hub `iil-ingest @ git+…` unpinned; Risiko nur im PR#377-Body, nicht im Tracking #913 | Prozesslücke | niedrig | SURVIVES | pyproject.toml:57; #913 Body+4 Kommentare: 0 Treffer „ingest" | tracking-misses-pr-body-risks ×1 |
| F-P1 | Erster Recovery-Dispatch unter Incident-Druck gegen falschen Ref (main statt Fix-Branch), obwohl korrektes Kommando seit 3h im PR-Body stand | fehlende Validierung | mittel* | SURVIVES | Run 28714416549 (17:42:26Z, main, startup_failure) vs. 28714450993 (17:43:49Z, Fix-Branch, success); *Skeptiker: Schaden nur ~83s, Schwere reduziert | dispatch-wrong-ref-under-pressure ×1 |
| F-P2 | PR#12 bekam 3h nach Eröffnung den incident-auslösenden zweiten Fix — Titel/Body/Kommentare nie nachgezogen; gemergter PR dokumentiert nur den halben Inhalt | Kommunikation | mittel-hoch | SURVIVES | `gh pr view 12 --json commits,body` + Timeline: 2 Commits (14:27/17:29), Body unverändert seit 14:29, 0 Kommentare | pr-body-stale-after-scope-change ×1 |
| F-P3 | Handoff-Doc (§2 „alle Gates OFFEN") eingefroren 12:58, Issue #913 lief bis 17:49 — zwei divergierende Wahrheitsquellen am selben Tag; gemergter Stand = das, was Folge-Sessions sehen | Prozesslücke | hoch | SURVIVES | `git log --follow` → 1 Commit e3a8649 12:58:08Z; kein Working-Tree-Diff; #913 updatedAt 17:49:36Z mit `[x]` G2/G4/G7 | handover-stale-vor-merge ×2 ⇒ **GATE-PFLICHT** |
| F-P4 | 6 Session-Worktrees+Leases zu gemergten PRs offen (nl2cad×2, aifw, risk-hub, platform×2) — trotz Pflicht-Reaper-Schritt (session-ende 3.1c, ADR-233) | Werkzeug / Prozesslücke | mittel | SURVIVES | `git worktree list` je Repo + Leases ohne `.closed`; alle 6 clean+merged; session-ende.md:382 deklariert Reaper als PFLICHT | worktree-midsession-accumulation ×2 ⇒ **GATE-PFLICHT** |
| F-P5 | cad-hub#24 (26 Tage alt, blockiert, ohne Owner) fehlt im Fleet-Tracking | Prozesslücke | niedrig | **REFUTED** | #913 ist findungs-getrieben (NL2X-Audit-Anker), PR#24 war nie Audit-Fund; Abwesenheit = erwartetes Scope-Verhalten | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle deklarierten gate-freien WPs + WP1 + G7 erledigt und unabhängig verifiziert (#913-Checkboxen, grüne Runs); Abzug: höchst-severes Item G5 blieb ohne jeden Fortschritt (F-S2) |
| architektur_design | 4 | Fix-Designs überlebten Falsifikation (frischer RO-Cursor #11; Echo-Block+Sanity-Gate #12); Abzug: Duplikat-Debt verstärkt (F-E5), Staging-Lücke belassen (F-E2) |
| code_konventionstreue | 3 | Commit-Format/Branch-Disziplin eingehalten (ADR-233-Worktrees durchgehend); Abzug: CHANGELOG-Verstoß trotz Repo-Präzedenz (F-E4), PR-Body-Pflege verletzt (F-P2) |
| risiko_debt | 2 | Realer Prod-Ausfall 22 min (F-E1) + unbehandelte öffentliche PII-Exposition (F-S2) = „verfehlt mit Rework" trotz netto reduzierter Fleet-Debt |
| prozess_effizienz | 3 | 7 PRs/6 Repos parallel via Agenten, Incident-Recovery <25 min; Abzug: Fehlzyklus F-P1, Orphan-Worktrees F-P4, Collector-Falschbefund F-S4 kostete Verifikationsaufwand |
| entscheidungsqualitaet | 3 | Gate-Disziplin respektiert (kein Merge vor Freigabe, Classifier-Denials nicht umgangen); Abzug: Prod-als-Testziel akzeptiert statt erst Staging-Input nachzurüsten (F-E1/E2) — mildernd: F-E3/F-S1 REFUTED |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| PII-Fund in public Repo als reines Entscheidungs-Gate geparkt (#913 G5) | Bei PII in öffentlichem Repo im SELBEN Turn eine reversible Interims-Mitigation anbieten/ausführen (Repo temporär privat = 1 API-Call, reversibel) und erst dann die irreversible Lösung (History-Rewrite) zur Entscheidung stellen | F-S2 |
| CC-Memory nach 13:00 nie aktualisiert (Z.16 „WP1 offen") | Memory-Einträge zu laufender Arbeit beim Session-Wrap gegen den Issue-Stand diffen und nachziehen (fester /session-ende-Schritt) | F-S3 |
| Collector-Prompt listete Repos ohne Owner-Qualifikation → iilgmbh-Annahme | Repo-Listen in Agent-Prompts IMMER als `owner/repo` qualifizieren; Collector-Regel: vor jedem `gh -R` einmal `git -C ~/github/<repo> remote get-url origin` | F-S4 |
| Wiring-Beweis = voller Prod-Deploy (Run 28713878976) | Für Deploy-Workflow-Fixes zuerst statische Prüfung (actionlint lokal — fand Bug 1 kostenlos), dann Beweis-Lauf gegen NICHT-Prod-Ziel; fehlt das Ziel, ist der Ziel-Parameter Teil des Fixes | F-E1 |
| `_deploy-odoo-hub.yml`: DEPLOY_HOST hardcoded, dispatch ohne inputs | `workflow_dispatch`-Input `target: staging\|prod` + Staging-Host verdrahten (Staging-Compose existiert bereits) | F-E2 |
| Workflow-Fix-Commits ohne CHANGELOG (Repo führt CI-Änderungen historisch im CHANGELOG) | CHANGELOG-Eintrag als DoD JEDES Fix-Commits in Repos mit CHANGELOG-Präzedenz für den Dateityp | F-E4 |
| Identischer Fix 2× gepatcht (438 LOC Diff für 6 Zeilen echte Divergenz) | mfg_nl2sql auf gemeinsame Quelle + versioniertes Route-Typ-Symbol refactoren (einmalig), danach Single-Patch | F-E5 |
| „Offenes"-Abschnitt aus PR#377-Body nicht ins Tracking gespiegelt | Beim Session-Wrap alle „Offenes"-Abschnitte der eigenen PR-Bodies in das Tracking-Issue übertragen (1 Kommentar genügt) | F-E6 |
| Recovery-Dispatch gegen Default-Ref main (Run 28714416549) | Recovery-Kommandos ausschließlich per Copy-Paste aus dem dokumentierten Rezept; bei UI-Dispatch Branch-Feld als expliziten Checkpunkt nennen | F-P1 |
| Zweiter (incident-auslösender) Commit ohne PR-Body-Update | Nach jedem scope-erweiternden Commit auf offenem PR im selben Turn Body/Kommentar nachziehen | F-P2 |
| Handoff sagt „alle Gates OFFEN", Issue #913 sagt `[x]` — same day | EINE lebende Wahrheitsquelle deklarieren: Handoff bekommt beim Commit ein Banner „Live-Status: #913"; statische Kopien führen keinen Gate-Stand | F-P3 |
| 6 Worktrees/Leases gemergter PRs offen trotz Pflicht-Reaper | Worktree-Reaper nach jedem Merge-Batch (nicht nur bei /session-ende) laufen lassen; Umsetzungs-Agenten beenden ihre eigene Session per `repo-session.sh end` nach PR-Erstellung NICHT (Merge steht aus) → Reaper-Lauf gehört dem Merger | F-P4 |

## 5. Längsschnitt (retro_kpis.py, Pflichtlauf 2026-07-04)

- **Gate-pflichtig durch diesen Report (Zähler ≥2):** `handover-stale-vor-merge` (44240f + hier),
  `worktree-midsession-accumulation` (35c665 + hier). Bereits zuvor Gate-pflichtig und hier erneut
  aufgetreten: `claim-before-cheapest-check` (F-S4).
- Neu beobachtet (×1, beobachten): `prod-as-test-environment`, `pii-in-public-fixtures`,
  `pr-body-stale-after-scope-change`, `changelog-skipped-for-ci-files`,
  `v18-v19-addon-duplication`, `tracking-misses-pr-body-risks`,
  `dispatch-wrong-ref-under-pressure`.
- refuted_rate 0,20 liegt im gesunden Band (Historie: 0,00–0,57), aber exakt auf der unteren
  Bandgrenze — kein Puffer; bei zwei weiteren Retros <0,2 wären die Finder zu lasch kalibriert.
- Score-Vergleich zum Mittel (n=12): risiko_debt 2 vs. Ø2,75 (schlechter — Incident),
  zielerreichung 4 vs. Ø3,92 (gleichauf), Rest im Band.

### 5b. Autonomie-Kalibrierung
- `over_ask = 0` bestätigt; 1 schwacher Kandidat (WP5d „obsolet"-Entscheid bei archiviertem
  read-only Repo — deterministisch entscheidbar, aber Belegstärke gering, nur 1 Datenpunkt).
- `over_act = 0` bestätigt; F-P1 (main-Dispatch) ist aus Artefakten nicht Mensch/Agent
  attribuierbar (GH-API zeigt nur den Account) → Kandidat, nicht Fall (§8).
- Kein ≥2-Muster über Retros → keine Charter-Schärfung aus dieser Session.

## 6. Verankerung (kopierfertig — Entscheidung beim Menschen)

**memory_candidates:**
```markdown
---
name: prod-as-test-environment
description: Deploy-Workflow-Fixes nie per Dispatch gegen Prod „beweisen" — erst actionlint, dann Staging-Ziel; fehlt das Ziel, ist der Ziel-Parameter Teil des Fixes
metadata: {type: feedback, drift: true, drift_episode: 2026-07-04-odoo-heredoc-incident}
---
Der „Wiring-Beweis" für odoo-hub#12 lief als workflow_dispatch gegen Prod (einzige verdrahtete
Option) und löste einen 22-min-Ausfall aus — der zweite Bug (Heredoc→literale .env) war
NICHT tool-erkennbar (actionlint+shellcheck exit 0, empirisch verifiziert), der erste schon.
**Why:** Ein Beweis-Lauf beweist die Verdrahtung nur im getroffenen Ziel; gegen Prod ist er
selbst das Risiko. **How to apply:** Vor Deploy-Workflow-Tests: (1) actionlint lokal,
(2) `workflow_dispatch`-Ziel-Input prüfen — fehlt Staging als Ziel, zuerst Input nachrüsten,
(3) erst nach grünem Staging-Lauf gegen Prod. Verwandt: [[nl2x-fleet-audit-handoff]].
```
```markdown
---
name: pii-fund-interim-mitigation-first
description: PII-Fund in public Repo → im selben Turn reversible Interims-Mitigation (Repo privat) anbieten, nicht nur irreversible Lösung zur Entscheidung parken
metadata: {type: feedback}
---
G5 (Kundendaten in nl2cad-Fixtures, Repo public) stand einen ganzen Arbeitstag ohne
Schadensbegrenzung, während niedriger priorisierte WPs liefen. **Why:** „Entscheidung nötig
(irreversibel)" blockiert nicht die reversible Sofortmaßnahme. **How to apply:** Bei
PII/Secret-Exposition: zuerst reversible Mitigation (privat schalten, Secret rotieren)
im selben Turn vorschlagen/ausführen, dann die dauerhafte Lösung gaten.
```

**adr_candidates:** keine — F-E2 (Staging-Input) ist repo-lokal ohne Trade-off (adr-threshold:
CHANGELOG+PR genügt); die Gate-Kandidaten sind Hook-/Skill-Edits, keine Architektur-Entscheide.

## 7. Maßnahmen (Action Board, aus §4 abgeleitet)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| R1 | 🟢 G5-Interim: nl2cad temporär privat schalten (reversibel) + danach History-Rewrite-Entscheid | nl2cad | #913 G5 | 🟢 offen | Entscheiden + 1 Klick (du) |
| R2 | 🟢 Gate-PR `handover-stale-vor-merge` (×2): Hook/Skill-Edit — Handoff-Commits erzwingen Live-Status-Banner | platform | neu | 🟢 offen | Freigabe, dann baue ich (du→ich) |
| R3 | 🟢 Gate-PR `worktree-midsession-accumulation` (×2): Reaper-Lauf in Merge-Flow verankern | platform | neu | 🟢 offen | Freigabe, dann baue ich (du→ich) |
| R4 | 🔵 Staging-Input für `_deploy-odoo-hub.yml` (`target: staging\|prod`) | odoo-hub | neu | 🔵 ready | PR bauen (ich) |
| R5 | 🔵 Worktree-Reaper JETZT laufen lassen (6 Orphans) | 4 Repos | — | 🔵 ready | ausführen (ich) |
| R6 | 🔵 PR#12-Nachtrag-Kommentar (Heredoc-Fix dokumentieren) + CHANGELOG-Nachtrag | odoo-hub | #12 | 🔵 ready | Kommentar+PR (ich) |
| R7 | 🔵 `iil-ingest`-Risiko in #913 spiegeln; CC-Memory nl2x aktualisieren; Handoff-Banner | platform | #913 | 🔵 ready | ausführen (ich) |
| R8 | 🔵 mfg_nl2sql-Konsolidierung v18/v19 (gemeinsame Quelle, 6-Zeilen-Delta) | odoo-hub | neu | 🔵 ready | PR bauen (ich, nach R4) |

## 8. Nicht verifiziert (Restlücken)

- **F-P6 (Hypothese):** ob der aifw#31-Nachbesserungs-Commit (12:45) Reaktion auf einen roten
  Lauf oder proaktiv war — Artefakte zeigen nur 1 CI-Lauf. Billigster Check: Session-Transkript.
- **F-P1-Attribution:** ob der main-Dispatch (17:42) Mensch (UI-Default) oder Agent war —
  GH-API zeigt nur den Account. Session-Gedächtnis der reviewten Session legt UI-Dispatch des
  Menschen nahe (Option A wurde als UI-Weg kommuniziert); als Hypothese geführt, NICHT als Befund.
- **F-P4-Attribution:** 2 der 6 Orphan-Worktrees (platform `syncreg-*`) stammen laut Task-Slugs
  mutmaßlich aus einer PARALLELEN Session desselben Tages — der Zustandsbefund gilt unabhängig,
  die Zurechnung zur reviewten Session ist für diese 2 unverifiziert. Check: Transkript der
  Parallel-Session.
- **PII-Umfang G5:** nur `minimal.ifc`-Header geprüft (Muster-Treffer); ob `minimal.dxf` und
  weitere Fixtures ebenfalls PII tragen ist offen. Billigster Check: `strings`-Scan über
  `packages/*/tests/fixtures/`.
- **ttz-Sovereignty (G1), NL2X-ADR (G3), Realdata-Secret (G6):** unverändert offene
  Entscheidungen aus #913 — kein Retro-Gegenstand, aber der Vollständigkeit halber.

## Self-Review (Meta-Agent, Phase 5)

Struktur-Prüfung gegen die Skill-Regeln (kein Inhalts-Urteil): Invariante |Soll|==|Survivors|
= 12==12 PASS · Frontmatter-Arithmetik PASS · Belegpflicht aller SURVIVES PASS · Scores
ganzzahlig+verankert PASS · Pfad kollisionsfrei PASS (3. Retro dieses Datums, eigene session_id)
· §8 substanziell PASS. Ein FAIL (recurring_findings-Frontmatter unvollständig, 3 Slugs) wurde
vor Commit korrigiert; refuted_rate 0,20 als Grenzwert ohne Puffer explizit vermerkt.
Längsschnitt-Zähler unabhängig re-verifiziert: `handover-stale-vor-merge` ×1→×2,
`worktree-midsession-accumulation` ×1→×2 (beide jetzt GATE-PFLICHT), `claim-before-cheapest-check` ×12.

---
*Methode: /session-retro (deep) · Collector haiku, 3 Finder + 3 Skeptiker + Meta sonnet ·
alle Belege unabhängig gezogen · refuted_rate 0,20 · Report committed nach KONZ-010.*
