---
retro_schema: 1
date: 2026-06-30
repo_scope: [writing-hub, platform]
session_id: 73003f
footprint: deep
findings_total: 16
findings_survived: 16
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [adr-number-collision-open-pr-queue, claim-before-cheapest-check, lint-failure-no-local-gate, planned-phase-no-issue, deprecation-grace-untracked-coupling]
recurring_findings: [claim-before-cheapest-check, lint-failure-no-local-gate, planned-phase-no-issue]
footprint_reduction_reason: "keine Reduktion — deep beibehalten: 2 Prod-DB-Migrationen (0011, 0012) verletzen Downscale-Bedingung (b) 'keine Migration'."
---

# Session-Retro 2026-06-30 — writing-hub Epic-#11-Finale + platform ADR-259 (F22)

> Methode: Richter≠Angeklagter. 1 Collector (haiku) + 3 Finder + 3 Skeptiker (sonnet), je frischer Kontext, nur Artefakte. Alle 16 Befunde unabhängig per gh/git re-verifiziert; **0 refuted**.

## 1. Executive Summary
- **Zielerreichung hoch, aber zwei Governance-Patzer:** Epic #11 (F13–F22) faktisch abgeschlossen, F16/F18 implementiert+deployt (164/174 Tests grün), ADR-182/183/259 akzeptiert — **aber** ADR-259 (die *Anti-Kollisions*-ADR) kollidiert mit offenem platform-PR #708 auf derselben Nummer (A-F1), und ADR-182 (erstes Authz-Modell, sicherheitsrelevant) wurde **ohne** externen Review akzeptiert+deployt (A-F2).
- **Über-Behauptung:** „each ADR went through 2 external reviews" ist falsch — ADR-182: 0 Reviews, ADR-183: 1 Runde, nur ADR-259: 2. Evidence-Discipline-Bruch (`claim-before-cheapest-check`, bereits gate-pflichtig ×≥2).
- **Migrations-Debt:** 0011 reaktiviert `session_replication_role=replica`, das `db.py:9` (§B15) explizit als SUPERUSER-pflichtig **verworfen** hatte — läuft nur, weil der Docker-User Superuser ist; bricht auf Managed-PG (B-F1).
- **Deprecation-Kopplung ohne Trail:** Sole-Owner-Signal (tot während Karenz, B-F3) + GDPR-Purge filtert auf deprecated `owner`-Spalte (B-F4) + owner-Drop/F14 ohne Tracking-Issue (A-F5) → tickende Uhr.
- **Prozess-Churn:** PR #114 brauchte 4 Pushes / 3 CI-Fails (kein lokales Pre-Push-Gate, C-F1, `lint-failure-no-local-gate` ×≥2); #108/#109 in rote Gate gemergt (C-F2). **Sauber bestätigt:** Authz-Coverage (12 Views Default-Deny), Integritäts-Trigger, CASCADE-Begründung, SSE-Drei-Phasen-Commit, Worktree-Hygiene, Canary-Issues unrelated (travel-beat).

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| A-F1 | ADR-259 (Anti-Kollisions-ADR) kollidiert mit offenem PR #708 (`ADR-259-cmis-first-dms-*`) auf derselben Nummer | fehlende Validierung | hoch | SURVIVES | platform PR #708 OPEN + #757 MERGED, 2 Dateien `ADR-259-*` | neu |
| A-F2 | ADR-182 (erstes Authz-Modell) akzeptiert+deployt **ohne** externen Review; „2 Reviews"-Claim falsch | fehlende Validierung | hoch | SURVIVES | kein `~/shared/adr-handoff-ADR-182-*`; PR #113 reviews:[] | `claim-before-cheapest-check` ×≥2 |
| A-F3 | ADR-183 Proposed→Accepted→Prod in 3h10min, nur 1 Review-Runde (nicht 2) | Prozesslücke | hoch | SURVIVES | PR #111/#115/#117/#118 Timestamps; 1 handoff-Paar | `claim-before-cheapest-check` ×≥2 |
| A-F4 | ADR-183 `on_delete=PROTECT`→CASCADE 47min NACH Acceptance (Impl-Test fing es) | fehlende Validierung | mittel | SURVIVES | ADR-183 Amendment-Block Z.75-80; #117→#118 | neu (mitigiert: dokumentiert) |
| A-F5 | Kein Tracking-Issue für owner-Spalten-Drop noch F14/CAS-Defer | Prozesslücke | mittel | SURVIVES | `gh issue list` → nur #11/#45/#51/#88 | `planned-phase-no-issue` ×≥2 |
| A-F6 | Epic #11 OPEN trotz erfüllter Schlussbedingungen (#112/#116 closed, ADRs accepted) | Kommunikation | niedrig | SURVIVES | #11 OPEN; #112/#116 CLOSED | neu |
| B-F1 | Migration 0011 nutzt `session_replication_role=replica`, das `db.py:9` (§B15) als SUPERUSER-pflichtig verworfen hatte; GUC war verfügbar | verfrühte Festlegung | mittel | SURVIVES | `0011_revision_dag.py:74` vs `db.py:9`; GUC seit `0004` | neu |
| B-F2 | `permissions.require()` ist toter Code (0 Call-Sites; Views nutzen `_project_for`→Http404) | Werkzeug | niedrig | SURVIVES | `grep require` apps/lectures/ → nur Definition | neu |
| B-F3 | `SoleOwnerDeletionError`-pre_delete-Signal unerreichbar während Karenz (PROTECT/Collector wirft zuerst); Test akzeptiert beide | verfrühte Festlegung | mittel | SURVIVES | `signals.py:23`; `models.py:163` PROTECT; Test Z.94 | neu |
| B-F4 | GDPR `purge_lecture_project --user` filtert auf deprecated `owner`-Spalte → 0 Treffer nach Spalten-Drop | fehlende Validierung | mittel | SURVIVES | `purge_lecture_project.py:68 filter(owner=user)` | `deprecation-grace-untracked-coupling` (neu) |
| B-F5 | 20 neue Test-Funktionen (authz/revision_dag/sse) verletzen `test_should_`-Konvention (0 Treffer) | Wissenslücke | niedrig | SURVIVES | `grep -c "def test_should_"` = 0 in 3 Files | neu (systematisch) |
| B-F6 | `enrich_section` fehlt in Nicht-Mitglied-404-Authz-Matrix (View IST geschützt) | fehlende Validierung | niedrig | SURVIVES | `_POST/_GET_PATHS` ohne enrich_section; View Z.254 | neu |
| C-F1 | PR #114 (F20): 4 Pushes / 3 CI-Fails (Ruff+a11y+Flow), kein lokales Pre-Push-Gate | Prozesslücke | mittel | SURVIVES | Runs 28438171401/244895/575069/869924 | `lint-failure-no-local-gate` ×≥2 |
| C-F2 | #108/#109 in rote `Integration Tests`-Gate gemergt (pre-existing a11y, vor Branch-Protection) | Prozesslücke | niedrig | SURVIVES | #108/#109 statusCheckRollup FAILURE @ merge | neu |
| C-F3 | #110-Deploy-Run „cancelled" deployte trotzdem Production (Audit-Ambiguität) | Werkzeug | niedrig | SURVIVES | Run 28434462704 Production-Job=success, run=cancelled | neu |
| C-F4 | ADR-259 Proposed→Accepted same-session, „Review" nur LLM (adr-handoff-extern), kein Mensch | Prozesslücke | niedrig(info) | SURVIVES | PR #757 2h17m, reviews:[], LLM-Artefakte | neu |

*(C-F5 war Clean-Bestätigung: 16 Canary-Issues #747–#771 = `travel-beat.iil.pet 502`, writing-hub nicht genannt → keine Aktion. Kein Defekt-Befund.)*

## 3. Scorecard (1–5, je befund-verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Alles Angekündigte geliefert (F16/F18 impl, 3 ADRs accepted, F22 geroutet); kleine Mängel: A-F2 (Review-Lücke), A-F6 (#11 nicht geschlossen) |
| architektur_design | **3** | Authz sauber (12 Views Default-Deny verifiziert), DAG additiv, SSE korrekt; aber B-F1 (verworfenes SUPERUSER-Muster reaktiviert), B-F3 (totes Signal), B-F4 (deprecated-Kopplung) = signifikante Abweichungen |
| code_konventionstreue | **3** | Commit-Format sauber; aber B-F5 (20× `test_should_`-Verstoß, systematisch) + B-F2 (toter Code) |
| risiko_debt | **2** | A-F1 (ADR-Kollision), B-F1 (bricht auf Managed-PG), B-F4 (GDPR-Purge tickt), A-F2 (Security-ADR ohne Review) → mehrere Fixes nötig |
| prozess_effizienz | **3** | C-F1 (4 Pushes/3 Fails), C-F2 (rote Gate), C-F3 (Deploy-Supersession), A-F3 (3h-ADR-Lifecycle) = Rework/Churn |
| entscheidungsqualitaet | **3** | Gute Calls (CASCADE-Fix gefangen, base_revision_id via Review verworfen); aber A-F1 (PR-Queue nicht geprüft), A-F2 (Review übersprungen), B-F1 (db.py nicht geprüft vor Muster-Reuse) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert; |Soll| = 16 = Survivors)
| Ist (Beleg) | Soll | eliminiert |
|---|---|---|
| ADR-259-Nummer vergeben ohne offenen PR-Queue zu prüfen; #708 hatte 259 bereits in OPEN-PR | Vor ADR-Nummern-Vergabe `gh pr list --search "ADR-NNN"` über offene PRs (nicht nur `ls docs/adr/`) — genau das, was ADR-259 selbst tooling-seitig fordert | A-F1 |
| „each ADR went through 2 external reviews" geschrieben ohne `ls ~/shared/adr-handoff-*` zu prüfen | Review-Behauptung erst nach `ls ~/shared/adr-handoff-ADR-NNN-*`; 0 Dateien → „kein externer Review" sagen | A-F2 |
| Security-ADR-182 same-session accepted, Review-Budget auf 183/259 konzentriert | Erst-Authz-/Security-ADR bekommt **erzwungenen** externen Review vor Accept (Gate), kein Same-Session-Accept ohne handoff-File | A-F3 |
| PROTECT erst beim Impl-Test als Purge-brechend erkannt, 47min nach Accept | Migrations-/on_delete-Entscheidungen gegen den DSGVO-Purge-Test prüfen **vor** ADR-Accept, nicht erst bei Impl | A-F4 |
| owner-Drop + F14 auf „spätere Migration" verschoben ohne Issue | Jeden Defer beim Schreiben in ein GitHub-Issue gießen (Slug `planned-phase-no-issue`); Epic-Close blockt sonst stillen Verlust | A-F5 |
| Epic #11 trotz erfüllter Bedingungen offen gelassen | Beim letzten Schlusskommentar die Schlussbedingung **selbst prüfen** und schließen, nicht nur empfehlen | A-F6 |
| 0011 reaktiviert `session_replication_role` trotz §B15-Verbot in db.py | Vor Trigger-Bypass in Migration `grep session_replication_role db.py` → bestehenden GUC-Pfad (`append_only_trigger_suspended`) nutzen | B-F1 |
| `permissions.require()` als Parallel-API ohne Call-Site | Keine API definieren, die kein View nutzt; `_project_for` ist die einzige Naht → `require()` entfernen oder verdrahten | B-F2 |
| Sole-Owner-Signal als „Guard" deklariert, feuert aber nie während Karenz | Signal-Guard mit einem Test absichern, der **beweist welche** Exception feuerte (nicht `raises((A,B))`); oder Signal erst beim Spalten-Drop hinzufügen | B-F3 |
| GDPR-Purge filtert `owner=user` (deprecated) | Purge-Command sofort auf Membership-Query umstellen (`memberships__role=owner`), nicht auf den zu droppenden Spalten-Pfad koppeln | B-F4 |
| 20 neue Tests als `test_<noun>_<verb>` statt `test_should_` | Test-Naming-Konvention (CLAUDE.md) beim ersten neuen Test-File prüfen; CI-Naming-Gate war vorhanden (Warnung) → auf block heben | B-F5 |
| `enrich_section` nicht in der 404-Authz-Matrix | Authz-Matrix-Test **aus den URL-Patterns generieren** (nicht handgepflegte Liste) → kein View fällt durch | B-F6 |
| #114 4 Pushes / 3 CI-Fails (ruff/a11y/flow) | Lokales Pre-Push-Gate (`make test-pg` + `ruff format` + Browser-Smoke) vor erstem Push bei UX-Änderungen (`lint-failure-no-local-gate`) | C-F1 |
| #108/#109 in rote main-Gate gemergt | Session-Start: `gh run list --branch main` grün prüfen, bevor PRs in main gemergt werden | C-F2 |
| #109/#110 7s-Merge → „cancelled"-Run deployte Prod | Bei back-to-back-Merges einen Deploy-Settle-Pause (1 Deploy abwarten) — vermeidet Audit-Ambiguität | C-F3 |
| ADR-259 same-session accepted, Review nur LLM | Plattform-Governance-ADR (org-weit) nicht same-session accepten; menschlicher Review-Slot vor Accept (über LLM-Zweitmeinung hinaus) | C-F4 |

## 5. Längsschnitt (retro_kpis.py — maschinell)
**3 meiner Survivors sind Wiederholungen bereits gate-pflichtiger Slugs (≥2 über Retros):**
- **`lint-failure-no-local-gate`** (C-F1) — gate-pflichtig laut Tool. Erneutes Vorkommen → das Gate ist überfällig (lokales Pre-Push-Gate erzwingen).
- **`claim-before-cheapest-check`** (A-F2/A-F3) — gate-pflichtig + Drift-Memory `gate-claim-before-cheapest-check` existiert. „2 Reviews"-Claim ohne `ls`-Check ist ein Lehrbuch-Fall.
- **`planned-phase-no-issue`** (A-F5) — gate-pflichtig. Defer ohne Issue erneut.

`refuted_rate=0.00` — rechnerisch `phase3_refuted/(findings_total−pre_refuted) = 0/16 = 0.0`, liegt **unter** der 0.2-Untergrenze (theater-Bereich der Skill-Band-Definition). Ob das die Befundqualität spiegelt, ist hier nicht zu beurteilen. (Skeptiker nuancierten faktisch: 44→47min, C-F1-Sequenz qualifiziert.)

## 6. Verankerung (Vorschläge — Mensch entscheidet)

**memory_candidates:**
- `adr-number-collision-open-pr-queue` (drift) — *Vor ADR-Nummern-Vergabe den OFFENEN PR-Queue prüfen (`gh pr list --search`), nicht nur `ls docs/adr/`. Beleg 2026-06-30: ADR-259 (Anti-Kollisions-ADR) kollidierte selbst mit offenem platform-PR #708. `ls` sah nur gemergte ADRs.*
- `adr-review-claim-vs-handoff-file` (drift, type feedback) — *„N externe Reviews" erst behaupten nach `ls ~/shared/adr-handoff-ADR-NNN-*`. Beleg: „2 Reviews each" war für ADR-182 (0) und ADR-183 (1) falsch. Verschärft `[[gate-claim-before-cheapest-check]]`.*
- `deprecation-grace-couples-to-dropped-column` (drift) — *Grace-Deprecation (owner-Spalte) hatte 2 Kopplungen an den zu-droppenden Pfad: Sole-Owner-Signal (tot, PROTECT zuerst) + GDPR-Purge-Filter. Beim Deprecaten die neue Logik SOFORT verdrahten + Drop-Issue anlegen, nicht erst „später".*

**adr_candidates:**
- Keiner zwingend. F18/F16/F22 sind durch ADR-182/183/259 abgedeckt. Erwägung: ein **Prozess-Gate** (kein ADR) „Security-/Authz-ADR braucht externen Review vor Accept" — eher CLAUDE.md/Hook als ADR.

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf)

### 🟢 Offen — dein Zug
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 1 | **ADR-259-Nummernkollision auflösen** — #708 vs gemergtes ADR-259 (eines umnummerieren) | platform | PR #708 / ADR-259 | 🟢 offen | #708 auf nächste freie Nr. heben **oder** mein ADR-259; Owner-Call (du) |
| 2 | **owner-Drop + F14 als Issues anlegen**, bevor Epic #11 geschlossen wird | writing-hub | (neu) | 🟢 offen | 2 Tracking-Issues, dann #11 schließen (A-F5/A-F6) |

### 🔵 Offen — ich kann sofort
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 3 | **0011 auf GUC-Pfad umstellen** (`append_only_trigger_suspended` statt `session_replication_role`) — vor Managed-PG-Migration | writing-hub | (Folge-PR) | 🔵 ready | B-F1; Migration 0013 oder Doku-Warnung |
| 4 | **GDPR-Purge auf Membership-Query** umstellen (B-F4) + `permissions.require()` entfernen (B-F2) | writing-hub | (Folge-PR) | 🔵 ready | kleiner Cleanup-PR |
| 5 | **Authz-404-Matrix aus URLConf generieren** (B-F6) + `enrich_section` abdecken | writing-hub | (Folge-PR) | 🔵 ready | Test-Refactor |
| 6 | **`claim-before-cheapest-check`-Gate** + **`lint-failure-no-local-gate`-Gate** als Hook/CI eskalieren (beide ≥2) | platform | (Gate-PR) | 🔵 ready | retro_kpis-Pflicht |

### ✅ Erledigt (Session)
Epic #11 F13–F22 abgearbeitet; ADR-182/183/259 accepted; F16/F18 impl+deployt; #112/#116 closed; Worktrees/Leases sauber.

## 8. Nicht verifiziert (Restlücken)
- **B-F1 Managed-PG-Annahme:** dass `session_replication_role` auf RDS/CloudSQL scheitert ist Standard-PG-Verhalten, aber **nicht** gegen die reale Ziel-Infra getestet (writing-hub läuft auf selbst-gehostetem Docker-PG). Billigster Check: `SHOW is_superuser` als App-Rolle in Prod.
- **C-F1 Failure-Sequenz:** ob Runs 2/3 genau a11y vs Flow-Gate trennen, nicht auf Job-Namens-Ebene bestätigt (Step-Logs nötig) — Kern (kein Pre-Push-Gate) steht.
- **Score-Kalibrierung:** Scores sind befund-verankert, aber die Schwelle 2-vs-3 bei risiko_debt ist Ermessen.
