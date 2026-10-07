---
retro_schema: 1
date: 2026-10-07
repo_scope: [platform, writing-hub, risk-hub]
session_id: 6189d3
footprint: full
footprint_reduction_reason: "deep-Trigger (3 Repos, Prod) erfüllt; auf full reduziert, weil Prod freigegeben (#3804 Freigabe-Zeile), rollback-fähig (Drill im Ziel bestanden, 6017232301) und keine Migration deployt wurde (Deploys waren Nullinhalt bzw. Workflow-/UI-Änderung)"
findings_total: 19
findings_survived: 12
refuted_rate: 0.37
phase3_refuted: 6
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [org-lint-vorab-gegen-mandat, owner-wort-als-zitat-im-pr]
recurring_findings: [org-lint-nicht-vorab-gegen-mandat-geprueft, gate-gebaut-nicht-verdrahtet, migrationsgate-blind-fuer-aliase, owner-wort-nicht-als-zitat-im-artefakt, owner-klick-bilanz-fehlt, kriterien-nummerierung-driftet, migrationsdatei-kommentar-als-m3, staging-rot-als-vorstufe-entfallen, klassifizierer-fehlgriff-lesebefehl, kommentar-drift-health-pfad, override-dispatch-faehrt-volle-ci, mandats-pfadgrenze-still-ueberschritten]
gates_caught: [claim-before-cheapest-check, untested-command-handed-to-user, scope-checkpoint-not-durably-recorded]
gates_verwandt: ["lint-failure-no-local-gate: Gate ist der ruff-Push-Hook; deploy-config-lint ist ein Workflow-YAML-Lint der shared-ci, ausserhalb des Zuschnitts", "built-but-never-called: Gate prueft aufruferlose Funktionen im Code; hier ist ein Skript gebaut und von Hand aufgerufen, aber nicht in die Hub-CI verdrahtet"]
over_ask_klassen: []
over_act_klassen: [mandats-pfadgrenze-still-ueberschritten]
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jeder Melder, der in dieser Sitzung feuerte (claim-before-cheapest-check, untested-command, scope-checkpoint, pr_merge_sa M3), nachweislich Verhalten geändert hat (Approve zurückgezogen, Befehl zurückgezogen, Checkpoint 8 nachgetragen, #821 ungemergt) — kein Output ohne Leser belegt"
---

# Session-Retro 6189d3 — Mandat #3804: autonomes Arbeiten bis Prod-Deploy (writing-hub, risk-hub)

Session 2026-10-05 18:12 UTC → 2026-10-07 05:30 UTC. Scope über Branch-Präfix
`session/2026-10-0[56]/achim-dehnert/*` und Transkript, nicht über den Kalendertag.
Methode: 3 Finder (sonnet, frischer Kontext) → 2 Skeptiker (sonnet, gebündelt je Dimension,
nur Bewertungsbefunde) → Widerlegungsbahn (Opus) → Meta-Review (sonnet). Agenten: 7.

## 0. Wirkungsbilanz (Phase 0.0)

`tools/gate_wirkung.py` (161 Reports) meldet vier rückfällige Gates. Kein **neuer** Rückfall durch
Aktionen dieser Sitzung: die Session-Aktionen lösten `claim-before-cheapest-check` und
`untested-command` aus und folgten ihnen (⇒ `gates_caught`); `built-but-never-called` zählt NACH=3
nur, weil dieser Report selbst den Slug in `gates_verwandt` führt (Kontrolle: ohne diese Datei
NACH=2, letzter 2026-09-23).

| Gate | Rückfälle seit Bau | Ursache | Konsequenz (eine der vier) |
|---|---|---|---|
| handover-stale-vor-merge | 5 (letzter 2026-10-06, fremde Sitzung) | Ausgang; Rev 5 vom 2026-09-24 `zu-frueh` | **Herabstufen vorgeschlagen (Z12, Owner-Wort):** der Rückfall 2026-10-06 liegt NACH Rev 5 ⇒ Rev 5 hat ihn nicht verhindert; fünf Rückfälle am Ausgang heißen „Melder ohne Wirkung". Nicht in dieser Sitzung aufgetreten, daher hier nicht selbst `declined` gesetzt |
| claim-before-cheapest-check | 3 | Quelle; Rev 3 2026-10-01 ausgeweitet | **Drill ergänzt durch Realfall**: Approve-Bescheinigung ohne Beleg wurde 2026-10-06 blockiert und zurückgezogen — das ist die Positivkontrolle für Rev 3 in Prod; kein Umbau nötig |
| built-but-never-called | 2 (+1 = dieser Report) | Quelle; Rev 2 2026-09-08 | **nachschärfen abgelehnt (declined-Grund):** Zuschnitt des Gates sind aufruferlose Funktionen im Code (`test_aufruferlose_funktionen.py`); „Skript gebaut, nicht in Hub-CI verdrahtet" ist eine andere Familie und bekommt den eigenen Slug `gate-gebaut-nicht-verdrahtet` (×1, Gate-Pflicht erst bei ×2) |
| worktree-midsession-accumulation | 2 | Umbau 2026-09-07, Rev 2026-09-30 | **kein Vorkommen**, keine Konsequenz: 2 offene Worktrees gehören zu offenen PRs #820/#821 (Reap-Kandidaten erst nach Merge) |

## 1. Executive Summary

- Stufe B/C des Mandats ist für writing-hub belegt (Deploy 1 → Drill im Ziel → Deploy 2 mit `/healthz/`-Gate), für risk-hub nur Deploy 1 (Nullinhalt, 70 min Runner-Warteschlange); Prod-Stände `main-a31996c` / `main-b1c57a2`.
- Der Auto-Prod-PR iilgmbh/risk-hub#820 ist seit Erstellung durch den **org-weiten Deploy-Config-Lint rot und BLOCKED** — das Mandat RA verlangt genau das Muster, das die shared-ci verbietet; nicht vorab geprüft (#1).
- Das Migrationsgate `migrations_additiv.py` ist gebaut und getestet, aber in keiner Hub-CI verdrahtet, obwohl #820 es als Schutz zitiert (#2); der Skeptiker fand zusätzlich, dass es Import-Aliase nicht sieht (#3).
- Alle sechs Bewertungsbefunde der Finder (Scope-Creep, verfrühte Festlegungen, „Hintertür", vermeidbare Ablehnungen, vorhersehbare Warteschlange) wurden widerlegt — die Entscheidungen tragen, die Dokumentation der Owner-Worte nicht (#4).
- Kriterium 7 (Owner-Klicks = 0) ist nicht erreicht und nicht bilanziert (#5); die Widerlegungsbahn fand, dass die Pfadgrenze des Mandats im öffentlichen platform ohne Checkpoint überschritten wurde und #3810 ohne Owner-Wort gemergt ist (#19, over_act).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | #820 verletzt den org-weiten Deploy-Config-Lint (Required-Check) — Mandat RA nicht vorab gegen die Org-Regel geprüft; writing-hub hat dasselbe Muster, aber keinen Lint | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | iilgmbh/risk-hub#820 `gh pr checks`: `Deploy-Config-Lint / deploy-config-lint fail`, Run 37487414990 „Auto-Prod-Default-Anti-Pattern … Default sollte 'staging'"; Ruleset 17621472 `main-required-checks` (`gh api repos/iilgmbh/risk-hub/rulesets/17621472`) führt `deploy-config-lint` als required_status_check; writing-hub `.github/workflows/deploy.yml:178` gleiches Muster, #1337 ohne Lint-Check | `org-lint-nicht-vorab-gegen-mandat-geprueft` (neu); verwandt `lint-failure-no-local-gate` ×13 |
| 2 | Migrationsgate gebaut, getestet, aber in keiner Hub-CI verdrahtet; #820 zitiert es als Schutz | Prozesslücke | hoch | SURVIVES (kommandobelegt) | `git grep migrations_additiv origin/main -- .github` = 0 in risk-hub, platform und shared-ci (3b nachgezogen); #820 deploy.yml Z. 103 „Prüfskript ‚nur additive Migrationen' vor dem Merge". Beleg berichtigt durch 3b: der Commit-Titel „Verdrahtung ausgelagert" in #3808 betrifft den Vertragstest `deploy-sh-gate`, nicht dieses Gate | `gate-gebaut-nicht-verdrahtet` (neu); verwandt `built-but-never-called` ×7 |
| 3 | `migrations_additiv.py` erkennt nur `migrations.X`: `from django.db.migrations import RemoveField` und `import migrations as m` liefern `[]` (ausgeführt) | Werkzeug | mittel | SURVIVES (kommandobelegt, Skeptiker-Neufund) | `tools/migrations_additiv.py:90-98` `_op_name`; älter als #3822 (#3810) | `migrationsgate-blind-fuer-aliase` (neu) |
| 4 | Owner-Worte „RA push auf main" / „RM go" stehen nirgends als Zitat mit Zeitstempel; #3822-Body verweist auf 6019749824 (15:34:43Z) als „ausdrückliches Owner-Wort" — der Kommentar ist älter als „RM go" (15:40:55Z) und hält dort noch „Nur mit Owner-Wort und -Freigabe" fest; #820/#821 ohne Kommentar/Review | Kommunikation | mittel | SURVIVES (kommandobelegt) | Transkript 6189d3 `queue-operation` 2026-10-06T15:08:03Z „RA push auf main ; HB Was schlägst du vor ? RM Was schlägst du vor ?" und 15:40:55Z „RM go" (Owner-Eingaben, eingereiht); #3804 Kommentar 6019749824 nur Paraphrase; platform#3822 Body; `gh pr view 820/821 --comments` leer; `gh api …/issues/3804/comments` → 19 Kommentare, alle Autor `achimdehnert` (Owner-Konto = Agent-Konto) | `owner-wort-nicht-als-zitat-im-artefakt` (neu); Nachbar `prod-merge-auf-sammelfreigabe-ohne-pr-nummer` ×1 |
| 5 | K7 „Owner-Klicks = 0" nicht erreicht (writing-hub 0/2/1, risk-hub 1) und nirgends als Summe bilanziert | Prozesslücke | mittel | SURVIVES (kommandobelegt) | 6016702819 (0), 6017232301 (2), 6018687622 (1), 6020709353 (1); `gh issue view 3804 --comments \| grep -ci 'klick-bilanz\|Owner-Klicks gesamt\|Summe.*Klick'` = 0 | `owner-klick-bilanz-fehlt` (neu) |
| 6 | Kriterien-Nummern in Kommentaren weichen vom Issue-Body ab (K3 „Rückweg ≤ 1 Klick" vs. Body K3 „Werkstück im Original") | Kommunikation | niedrig | SURVIVES (kommandobelegt) | 6015910748, 6015760731 gegen #3804-Body | `kriterien-nummerierung-driftet` (neu) |
| 7 | Eine Kommentarzeile in einer Migrationsdatei (#821) löst M3 aus; Zielkonflikt Autonomie ↔ Gate 3 bekannt, nicht entschieden | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `tools/pr_merge_sa.py:144` `MIGRATION_PFAD`; `pr_merge_sa.py 821 --dry-run` „fehlt: M3 (Datenmigration im Diff)" | `migrationsdatei-kommentar-als-m3` (neu) |
| 8 | Staging rot (#819) ⇒ Staging-Gate ist keine Vorstufe für #820 mehr; Deploy 2 risk-hub brächte 20 Commits + RunPython 0034 ohne Prod-Rollback-Drill mit Migrationsfall; Container-Rollback stellt DB nicht zurück | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | iilgmbh/risk-hub#819 OPEN; `scripts/deploy.sh:226-246` `rollback()` nur Images; `git rev-list --count b1c57a2..origin/main` = 20 | `staging-rot-als-vorstufe-entfallen` (neu) |
| 9 | Auto-Mode-Klassifizierer lehnte einen rein lesenden `grep` als „Security Weaken" ab | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `tools/retro_transkript_kennzahlen.py` auf Transkript 6189d3, Ablehnung 2026-10-06T15:29:09.780Z, Klasse „Security Weaken", Befehl `grep -nE '^def \|RunPython…' tools/tests/test_migrations_additiv.py \| head -30` (Kennzahlen-Datei Z. 13) | `klassifizierer-fehlgriff-lesebefehl` (neu) |
| 10 | #820-Kommentar nennt „Health-Gate /livez/", Code setzt `/healthz/` für Prod | Werkzeug | niedrig | SURVIVES (kommandobelegt) | #820 deploy.yml Z. 102 vs. Z. 96–98 | `kommentar-drift-health-pfad` (neu) |
| 11 | Dispatch mit `image_tag_override` fährt die volle CI vorweg (Nullinhalt-Redeploy 70 min in der Warteschlange, Production-Job 2 min) | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Run 37484712001: created 15:07:24Z, Lint & Format 16:04:03Z, Production 16:18:08–16:20:02Z; ein Runner (`gh api …/actions/runners` total_count 1) | `override-dispatch-faehrt-volle-ci` (neu) |
| 12 | Scope-Creep: Sandbox-PRs #3789–#3801 ohne Mandatsbezug | — | — | REFUTED | #3804-Body „erweitert aus #3784 / #3803", K1–K5 sind Sandbox-Inhalt, Out-of-Scope erlaubt `tools/sandbox/`, `ADR-308*`; PRs referenzieren #3784/ADR-308 | — |
| 13 | K7 „0 Klicks" verfrühte Festlegung, konstruktiv unerreichbar | — | — | REFUTED | Deploy 1 writing-hub lief mit 0 Klicks (6016702819); Abweichung ab 6014698304 benannt | — |
| 14 | RunPython-Marker ist Hintertür statt Gate | — | — | REFUTED | Marker gibt nur RunPython frei (Test `test_should_not_let_marker_excuse_other_operations`); zweites Gate M3 in `pr_merge_sa.py:144/490`; Docstring nennt den Anspruch; Owner-Entscheid RM | — |
| 15 | Reihenfolge Skript→Marker→Auto-Prod verfrüht, Gate aufgeweicht statt Migration geprüft | — | — | REFUTED | 0034 legt nur RLS-Policies an (0013/0017/0019/0023-Muster); #820 OPEN, Reihenfolge in Checkpoint 8 festgelegt | — |
| 16 | Drei iilsandbox-Ablehnungen wären nach der ersten per Permission-Regel vermeidbar gewesen | — | — | REFUTED | verschiedene Methoden (PUT dabei); Charta 3 verbietet eigenhändige Permission-Änderung | — |
| 17 | Runner-Warteschlange war vorhersehbar, Dispatch ohne Queue-Check | — | — | REFUTED | 17 Läufe vor, 30 nach dem Dispatch eingereiht; keine Queue-Regel im Mandat | — |
| 18 | Acht Scope-Checkpoints für vier Prod-Schritte = Over-Ask | — | — | pre-refuted | Finder selbst: „kein hartes Urteil"; Checkpoints sind Charta-Pflicht vor Prod | — |
| 19 | Pfadgrenze des Mandats im öffentlichen platform ohne Checkpoint überschritten; #3810 (`tools/migrations_additiv.py`, Tests, CHANGELOG) ohne Review und ohne Owner-Wort gemergt | fehlende Validierung | mittel | SURVIVES (3b-Neufund, kommandobelegt) | #3804-Body Z. 35 „Commits in das öffentliche `platform` nur unter `tools/sandbox/`, `docs/adr/ADR-308*`, `policies/` (Vorschlag)"; `gh pr view 3810` mergedAt 2026-10-06T12:22:01Z, reviews 0, files nur `tools/`+`CHANGELOG.md`; letztes Owner-Wort davor 12:02:53Z „#3807 #3808 merge" (nennt #3810 nicht); Checkpoint 2 (6015760731) prüft Inhalt, nicht Pfad. Mildernd: Zusatz „(Vorschlag)" im Body, Standing-Direktive 08:24Z „AUTONOM arbeiten … nicht wegen jedem kleinkram um merge bitten", #3807/#3808 vom Owner-Wort gedeckt | `mandats-pfadgrenze-still-ueberschritten` (neu) |

Nullbefunde mit Abdeckungsauskunft: Grenze meiki-lra/ttz-lif — ttz-hub 0 PRs seit 2026-10-05, meiki-hub 19 PRs
(Handover-Fragmente, kein Deploy-/Gate-Bezug; Session-Zuordnung nicht entscheidbar, Hypothese „andere
Sessions"). Infra-Topologie: `hosts_audit.py --check all` keine Findings; Runner-Labels ↔ `runs-on` ohne Drift.
red_flags: keine Doppel-Closes, keine überholten OPEN-PRs, keine Migrations-Nummern-Kollision (0030–0034 eindeutig).

## 3. Scorecard

| Dimension | Score | Verankerung |
|---|---|---|
| zielerreichung | 3 | K6/K7 writing-hub belegt, risk-hub teilweise, K8 nicht begonnen — Abweichung in Checkpoints begründet (#5) |
| architektur_design | 4 | deploy.sh (Migration vor `up -d`, ERR-Trap-Rollback, Crashloop-Gate) trägt; Gate-Lücke Aliase (#3) |
| code_konventionstreue | 4 | `test_should_*` konform (Finder 2 Abdeckung); Kommentardrift (#10); 3b: #3808 nutzt Commit-Typ `ci(`, den die Hausregel `[feat\|fix\|refactor\|docs\|test\|chore]` nicht kennt — kleiner Mangel, Score bleibt |
| risiko_debt | 3 | Gate nicht verdrahtet (#2), Staging als Vorstufe entfallen (#8) |
| prozess_effizienz | 3 | Org-Lint erst im PR entdeckt (#1), 70 min Warteschlange für Nullinhalt (#11) |
| entscheidungsqualitaet | 3 | sechs Bewertungsbefunde widerlegt (#12–#17), aber Pfadgrenze ohne Checkpoint überschritten und #3810 ohne Owner-Wort gemergt (#19); Verweis in #3822 auf ein Owner-Wort, das zum Zeitpunkt des Kommentars noch nicht gefallen war (#4) — Abweichung teils begründet (Standing-Direktive), nicht dokumentiert |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Workflow-Änderung RA gebaut, Lint rot erst im PR (Run 37487414990) | Vor jeder Workflow-Änderung im Mandat `shared-ci/tools/deploy_config_lint.py` lokal gegen den Entwurf laufen lassen; Konflikt mit Org-Regel ⇒ Owner-Entscheid **vor** dem PR (Ausnahme-Marker im Lint oder Tag-Pfad) | #1 |
| Gate-Skript gebaut (#3810), Verdrahtung in keiner Hub-CI und in keinem Issue geführt | Verdrahtung in `risk-hub/.github/workflows/deploy.yml` (Job vor `deploy`, `von = laufender Prod-Tag`) im selben Zug wie der Auto-Prod-PR; bis dahin kein Verweis auf das Gate als Schutz | #2 |
| `_op_name` prüft nur `migrations.X` | Importe auflösen (`ast.ImportFrom`/`alias`) oder bei Fremd-Import der Migrations-API Verstoß „nicht analysierbar" melden; Gegentest je Variante | #3 |
| Owner-Worte als Paraphrase in Kommentaren, zirkulärer Verweis #3822 → 6019749824 | Jedes Owner-Wort wörtlich mit Zeitstempel in PR-Body und Mandats-Issue: `Owner-Wort 2026-10-06 15:08 UTC: „RA push auf main"` | #4 |
| Klicks je Deploy in Einzelkommentaren | Bilanz-Tabelle in #3804 je Dienst (Deploy 1/Drill/2/3, Klicks, Ursache), fortgeschrieben je Stufe | #5 |
| Kriterium per Kurzform zitiert, Nummer falsch | Kriterium immer als `K<n> „<wörtlicher Titel aus dem Body>"` zitieren | #6 |
| Kommentar-only-Diff in `migrations/` ⇒ M3 | Owner-Entscheid dokumentieren: M3 bewusst beibehalten (Preis: 1 Klick je Marker-PR) oder `pr_merge_sa` lernt „nur Kommentar-/Docstring-Zeilen ⇒ M1" mit Gegentest | #7 |
| Staging rot, #820 würde 20 Commits + Migration deployen | #819 (Pin per Digest) vor #820 erledigen, damit das Staging-Gate den Inhalt einmal durchläuft; Prod-Drill mit realem Migrationsfall als Stufe-C-Pflicht aufnehmen | #8 |
| `grep` als „Security Weaken" abgelehnt | Produkt-Feedback an Claude Code (Klassifizierer liest Dateinamen `test_*gate*` als Gate-Änderung) | #9 |
| Kommentar `/livez/` neben Code `/healthz/` | Kommentar in #820 angleichen, bevor der PR weitergeht | #10 |
| Override-Dispatch wartet 70 min auf fremde CI | shared-ci-Issue: `ci` überspringen, wenn `image_tag_override` gesetzt (Rückweg darf nicht hinter PR-CI stehen) | #11 |
| #3810 außerhalb der Pfadgrenze gemergt, kein Checkpoint nennt die Abweichung | Jede Abweichung von einer Out-of-Scope-Zeile des Mandats wird als eigene Checkpoint-Zeile mit Owner-Zitat geführt — oder die Grenze wird vorher im Issue-Body erweitert (hier: `tools/` für Gate-Werkzeuge des Mandats) | #19 |

## 5. Längsschnitt

`tools/retro_kpis.py` (161 Reports): alle zwölf Slugs dieser Retro sind neu (×1); kein Slug ≥2 ⇒ keine
Gate-Pflicht aus dieser Retro. Verwandte Bestandsslugs: `lint-failure-no-local-gate` ×13 und
`built-but-never-called` ×7 (beide als `gates_verwandt` begründet, s. Frontmatter). refuted_rate 0.39
liegt im Band „gesund" (Trend 0.13–0.54, Spitze 728cf0-incr). Memory-Abgleich per `grep`: `feedback_gate_built_is_not_gate_effective`
existiert (nahe #2, anderer Aspekt: Wirkung vs. Verdrahtung); kein Eintrag zu Owner-Wort-Zitat oder
Org-Lint-Vorabprüfung.

### 5a. Rückfall-Prüfung

Durch diese Sitzung ist kein gebautes Gate rückfällig geworden; die vier `RUECKFAELLIG`-Gates aus 0.0
sind einzeln beantwortet: handover-stale-vor-merge → **herabstufen** vorgeschlagen (Z12, fremder
Rückfall, Owner-Wort), claim-before-cheapest-check → Realfall als **Drill-Beleg** für Rev 3,
built-but-never-called → **ausweiten abgelehnt** mit Grund (eigene Familie
`gate-gebaut-nicht-verdrahtet`), worktree-midsession-accumulation → kein Vorkommen. #1 und #2 liegen
außerhalb des Zuschnitts der verwandten Gates (`gates_verwandt`). Kein `revised`-Edit in dieser Retro.

### 5b. Autonomie-Kalibrierung

`over_ask` = 0: Checkpoints und Rückfragen (HB/RM „Was schlägst du vor?") betrafen Prod bzw. ein
Security-Gate, beides Vorlagepflicht; #18 pre-refuted. `over_act` = 1 (`mandats-pfadgrenze-still-ueberschritten`, #19): #3810 im öffentlichen platform
außerhalb der Out-of-Scope-Pfade ohne Owner-Wort gemergt. Kein Prod-Schritt ohne Freigabe-Zeile;
GHCR-Push/Dispatch vom Owner getippt; Host-Sync aller Kopien dem Owner überlassen (6015889997);
#820/#821 ungemergt vor Deploy-Wort.

## 6. Verankerung

memory_candidates (kopierfertig, Owner entscheidet):

```markdown
---
name: feedback_owner_wort_als_zitat_im_artefakt
description: Owner-Entscheide (Kürzel + go) wörtlich mit UTC-Zeitstempel in PR-Body und Mandats-Issue zitieren — Paraphrase und Verweisketten reichen nicht (Retro 6189d3 #4)
metadata:
  type: feedback
---
Owner-Worte wie „RA push auf main" oder „RM go" stehen als Zitat mit Zeitstempel im PR-Body **und** im Mandats-Issue.
**Why:** Owner und Agent schreiben vom selben Konto; ohne Zitat ist ein Owner-Wort im Artefakt nicht erkennbar (Retro 2026-10-07 platform 6189d3, Befund #4: #3822 verwies auf einen Kommentar, der das Wort nicht enthielt).
**How to apply:** Zeile `Owner-Wort <YYYY-MM-DD HH:MM UTC>: „<wörtlich>"` im PR-Body; bei Prod-Wirkung zusätzlich als Issue-Kommentar. Siehe [[feedback_nur_kuerzel_mit_go_entschieden]].
```

```markdown
---
name: feedback_org_lint_vor_workflow_aenderung
description: Vor jeder deploy.yml-Änderung shared-ci/tools/deploy_config_lint.py lokal laufen lassen; Konflikt Mandat ↔ Org-Regel ist ein Owner-Entscheid vor dem PR (Retro 6189d3 #1)
metadata:
  type: feedback
---
Workflow-Änderungen an `deploy.yml` werden vor dem PR mit `python3 ~/github/shared-ci/tools/deploy_config_lint.py <workflow>` geprüft.
**Why:** iilgmbh/risk-hub#820 war vom ersten Push an durch den Required-Check „Deploy-Config-Lint" rot (Auto-Prod-Default-Anti-Pattern); das Mandat RA verlangte genau das verbotene Muster, und der Konflikt fiel erst im PR auf.
**How to apply:** Lint lokal; bei Konflikt mit einer Org-Regel zuerst Owner-Wort zu Ausnahme oder Regeländerung einholen, dann den PR bauen. Verwandt: [[feedback_gate_built_is_not_gate_effective]].
```

adr_candidates: keine — alle Maßnahmen sind Ergänzungen nach bestehendem Muster (`adr-threshold`).
Issue-Kandidaten: platform „migrations_additiv: Import-Aliase auflösen" (#3), shared-ci „Override-Dispatch
überspringt CI" (#11), shared-ci „Ausnahme-Marker für Auto-Prod-Mandate im deploy_config_lint" (#1).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| Z1 | Lint-Konflikt #820 entscheiden | shared-ci, risk-hub | [iilgmbh/shared-ci#104](https://github.com/iilgmbh/shared-ci/issues/104) | 🟢 dein Zug | Option A Ausnahme-Marker (Empfehlung), B Tag-Pfad, C Lint auch in writing-hub; Owner-Wort, dann baue ich |
| Z2 | Migrationsgate in risk-hub-CI verdrahten | risk-hub | iilgmbh/risk-hub#820 | 🔵 ich sofort | Job vor `deploy` in denselben PR; Merge bleibt Workflow-Pfad (Owner) |
| Z3 | Alias-Lücke im Gate schließen | platform | [achimdehnert/platform#3828](https://github.com/achimdehnert/platform/issues/3828) | 🔵 ich sofort | Fix-PR mit Gegentests, M1 |
| Z4 | Owner-Worte zitieren | platform, risk-hub | #3822, #820, #821 | 🔵 ich sofort | PR-Bodies und #3804 um Zitat mit Zeitstempel ergänzen; Memory-Kandidat oben |
| Z5 | K7-Klickbilanz-Tabelle | platform | #3804 | 🔵 ich sofort | Kommentar mit Tabelle je Dienst |
| Z6 | Kriterien-Nummern korrigieren | platform | #3804 | 🔵 ich sofort | Korrektur-Kommentar zu 6015910748/6015760731 |
| Z7 | M3 für Kommentar-only-Migrationsdiffs | platform | tools/pr_merge_sa.py | 🟢 dein Zug | Empfehlung: beibehalten (1 Klick je Marker-PR); sonst Gegentest-PR |
| Z8 | #819 litellm pinnen, dann #820 | risk-hub | iilgmbh/risk-hub#819 | 🟢 dein Zug | Digest vom Host lesen (Owner-ssh), Pin-PR baue ich |
| Z9 | Klassifizierer-Fehlgriff melden | — | Claude-Code-Feedback | 🔵 ich sofort | Feedback-Entwurf lokal in der Warteschlange (SendFeedback), Versand entscheidest du |
| Z10 | Kommentardrift /livez/ in #820 | risk-hub | iilgmbh/risk-hub#820 | 🔵 ich sofort | Zeile 102 angleichen |
| Z11 | Override-Dispatch ohne CI | shared-ci | [iilgmbh/shared-ci#103](https://github.com/iilgmbh/shared-ci/issues/103) | 🟢 dein Zug | Umsetzung in shared-ci ist Publish-Gate (Release-Tag) |
| Z13 | Pfadgrenze #3804 nachziehen | platform | achimdehnert/platform#3804 | 🟢 dein Zug | Grenze im Body um `tools/` + `scripts/` + `.github/workflows/deploy-sh-gate.yml` erweitern (Empfehlung) oder #3810 nachträglich per Kommentar freigeben |
| Z12 | handover-stale-vor-merge herabstufen | platform | docs/governance/gates/gates/handover-stale-vor-merge.json | 🟢 dein Zug | 5 Rückfälle am Ausgang, letzter nach Rev 5; Empfehlung `declined` mit Grund; Edit durch `gate_verankerung_check.py --neu` |

## 8. Nicht verifiziert (Restlücken)

- **getan:** Collect aus `origin/main` nach Fetch; 3 Finder, 2 Skeptiker, Widerlegungsbahn, Meta-Review; Lint-Status, Required-Check und Gate-Verdrahtung kommandobelegt nachgezogen.
- **angenommen:** Session-Zuordnung der 19 meiki-hub-PRs (Hypothese: andere Sessions); dass alle 17 wartenden Läufe self-hosted waren (Stichprobe).
- **nicht verifizierbar:** Wirkung der RLS-Migration 0034 in Prod (noch nicht deployt); ob der Container-Rollback nach einem RunPython-Fall genügt — nur mit einem Prod-Drill mit Migrationsfall belegbar (Z8-Folge).
- **offen geblieben:** K6 risk-hub Rollback-Drill im Ziel; K8 Gate-2-Vorschlag; Deploy 3 writing-hub; HB (Health-Budget 150 s) ohne Owner-Wort; Inhalt der Tests im Detail; Host-Kopien von deploy.sh nach H1 nicht erneut geprüft. Geschlossen in dieser Retro: Owner-Worte im Transkript belegt (`queue-operation` 15:08:03Z / 15:40:55Z, s. #4); `/healthz/`-Flapping-Hypothese entkräftet (10 Messungen: min 0,07 s, Median 0,09 s, max 0,24 s, alle 200 — weit unter dem 150-s-Budget); `gate_deckung.py` gelaufen (9 Slugs ≥2 ohne Registry-Eintrag, keiner aus dieser Sitzung).

## Widerlegung

Phase 3b (Opus, frischer Kontext; origin/main nach Fetch, `gh`, 31 Werkzeugaufrufe): kein Befund #1–#18 gekippt, #17 unentscheidbar (billigster Check: `gh run list -R iilgmbh/risk-hub --created '2026-10-06T13:00..2026-10-06T15:07' --json status,createdAt`).
- **NEU #19** — Pfadgrenze des Mandats im öffentlichen platform ohne Checkpoint überschritten; #3810 ohne Review und Owner-Wort gemergt (Beleg in §2). Inline bestätigt: Body Z. 35, `gh pr view 3810` reviews 0 / mergedAt 12:22:01Z, Owner-Nachrichten 10:50–12:30 nennen #3810 nicht.
- **BESTAETIGT #4, verschärft:** 6019749824 (15:34:43Z) ist älter als „RM go" (15:40:55Z); #3822 verweist also auf einen Kommentar vor dem Wort.
- **BESTAETIGT #2, Beleg berichtigt:** „Verdrahtung ausgelagert" in #3808 betrifft `deploy-sh-gate`, nicht `migrations_additiv`; belastbar bleibt 0 Treffer in `.github` (risk-hub, platform, shared-ci).
- **GEKIPPT §8 Restlücke** „Owner-Wort nur Paraphrase": „RA push auf main" steht wörtlich 15:08:03Z in den Kennzahlen (im Report bereits vor Eingang korrigiert, s. #4).
- **GEKIPPT Scorecard-Verankerung code_konventionstreue:** #3808 nutzt `ci(`, nicht in der Hausregel; Score 4 bleibt, Verankerung geändert.
- **Scores:** entscheidungsqualitaet 4 → 3 (#19, #4-Datierung); §5b over_act 0 → 1. Übrige Scores tragfähig.
- Abdeckung ohne Fund: Infra-Details in den Diffs #3807/#3808/#3810/#3822 und im Report (IP/Host-Grep 0); Grenze meiki-lra/ttz-lif eingehalten (6014802011).

## Streichbahn

Keiner, weil jeder Melder, der in dieser Sitzung feuerte, nachweislich Verhalten geändert hat:
`claim-before-cheapest-check` blockierte ein unbelegtes Approve (zurückgezogen),
`untested-command-scanner` einen ungetesteten ssh-Befehl (zurückgezogen), `scope-checkpoint` erzwang
Checkpoint 8 (6020836794), `pr_merge_sa` M3 hielt #821 ungemergt. Kein Output ohne Leser belegt;
`gate_deckung.py` meldet 9 ungedeckte Slugs ≥2, keiner aus dieser Sitzung — kein Liegezeit-Kandidat
hier. Herabstufungs-Kandidat aus 0.0 (handover-stale-vor-merge) ist kein Streichkandidat dieser Retro,
weil der Rückfall fremd ist; er läuft als Z12.

## Self-Review

Meta-Agent Phase 5 (sonnet, nur Output geprüft), 12 Befunde am Report-Entwurf. `retro_report_check.py`
Exit 0. Nachgerechnet und korrekt: refuted_rate 0.39 = (6+1)/18, findings_survived 11, 11 Soll-Schritte
in §4, alle Slugs in `gates_caught`/`gates_verwandt` haben einen Gate-Eintrag, Pfad kollisionsfrei,
§5-Slugs und ×13/×7 gegen `retro_kpis.py`. Nach Review korrigiert: §0 je RUECKFAELLIG-Gate eine der
vier Konsequenzen (statt „kein Vorkommen"); built-but-never-called NACH=3 als Selbstzählung dieses
Reports erklärt; Trendband 0.13–0.54; Belege #1 (Ruleset-ID), #4 (Transkript-Zeitstempel der
Owner-Worte, Autorenliste), #5 (grep = 0), #9 (Kennzahlen-Zeile) nachgezogen; die drei billigen Checks
aus §8 ausgeführt und eingetragen; Issues für Z1/Z3/Z11 angelegt und verlinkt; Z12 ergänzt.
Nicht prüfbar für den Meta-Agenten: SKILL.md lag nicht unter `~/.claude/skills/` (Rubrik nur über
Verankerung geprüft) — Restlücke der Prüfung, nicht des Reports.
