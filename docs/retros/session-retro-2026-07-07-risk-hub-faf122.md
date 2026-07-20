---
retro_schema: 1
date: 2026-07-07
repo_scope: [risk-hub, iil-klickdummy, platform]
session_id: faf122
footprint: full
footprint_reduction_reason: "Rule-B-Trigger (≥3 Repos berührt: risk-hub, iil-klickdummy, platform) zieht `deep`; downgestuft auf `full`, weil alle drei Downgrade-Bedingungen erfüllt sind: (a) jeder Publish/Release-Schritt (v1.32.0, v1.32.1) wurde vom User explizit freigegeben (AskUserQuestion-Äquivalent im Transkript, wörtlich 'ja iil-klickdummy als v1.32.0 releasen' / 'ja release v1.32.1'), (b) voll rollback-fähig, keine DB-Migration in keinem der 3 Repos, (c) findings_total-Schätzung lag bei ≤10 (tatsächlich 12, leicht überschritten aber im Rahmen)."
findings_total: 12
findings_survived: 11
refuted_rate: 0.083
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [ci-gate-claimed-not-wired-into-workflow, zero-review-merge-on-unprotected-repo, branch-protection-doc-vs-reality-drift]
recurring_findings: [claim-before-cheapest-check]
---

## 1. Executive Summary

- **Kernziel verfehlt trotz erheblichem Cross-Repo-Aufwand:** Der eigentliche Zweck der ganzen Kette (3 Repos, 5 PRs, 2 PyPI-Releases, 1 ADR-Amendment) — die KD-Sitemap-Staleness strukturell per CI-Gate zu verhindern — wurde **nicht erreicht**: `klickdummy-sitemap-drift` ist nur in ein Makefile-Meta-Target eingehängt, das kein GitHub-Actions-Workflow aufruft (Befund #1, kritisch, doppelt verifiziert).
- **Die Extraktion selbst führte einen Bug ein, den das Original nie hatte** (`spec_date` wurde dynamisch statt statisch, Befund #2) — gefangen durch echtes Downstream-CI-Feedback, in <1h sauber gefixt (Befund #6 als Fix-Forward-Referenz, positiv).
- **Review-/Gate-Hygiene war lückenhaft an mehreren Stellen:** ein PR wurde mit ungereviewtem Zweit-Commit gemergt (#3), zwei PRs im Release-Repo liefen ganz ohne Review (#4), eine Freigabe erfolgte vor CI-Abschluss (#8) — bei gleichzeitig sauber eingehaltener Publish-Gate-Disziplin (User wurde vor jedem PyPI-Release explizit gefragt).
- **Infrastruktur-Drift entdeckt, nicht durch diese Session verursacht:** weder risk-hub noch iil-klickdummy erzwingen technisch das, was ihre eigene Dokumentation behauptet (#9, #10).
- **Längsschnitt-Treffer:** Befund #1 ist eine weitere (16.) Instanz des bereits gate-pflichtigen Musters `claim-before-cheapest-check` — dasselbe Muster, das schon im eigenen CLAUDE.md als Gate dokumentiert ist, wurde in dieser Session erneut verletzt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `klickdummy-sitemap-drift` nie in `.github/workflows/ci.yml` verdrahtet — CI ruft nur `make klickdummy-parity-drift` (ci.yml:116) direkt auf, nicht das neue Target/den Meta-Target `klickdummy` | fehlende Validierung | kritisch | SURVIVES | `grep -n klickdummy .github/workflows/ci.yml` (risk-hub); Makefile Z.130-139 | claim-before-cheapest-check (×16 über alle Retros) |
| 2 | Extraktion (iil-klickdummy PR #143) führte `datetime.date.today()`-Nichtdeterminismus ein; Original (`scripts/gen_kd_sitemap.py`) hatte einen Literal-String `"2026-05-27"`, nie `date.today()` | fehlende Validierung | hoch | SURVIVES | `git show 7049f22^:scripts/gen_kd_sitemap.py` (kein datetime-Import); PR #145 Commit-Body | neu |
| 3 | risk-hub PR #401 gemergt mit zweitem Commit (`bc1c6f4`, 09:18:30Z), der nie erneut reviewt wurde — Freigabe (08:46:44Z) galt nur für Commit `7049f22` | Prozesslücke | mittel | SURVIVES | `gh pr view 401 --json commits,reviews` | neu |
| 4 | iil-klickdummy PR #143 (Feature) und #144 (PyPI-Release v1.32.0) mit `reviews: []`, `reviewDecision: ""` — kompletter Merge ohne jeglichen Human-Review | Prozesslücke | hoch | SURVIVES | `gh pr view 143/144 --json reviews,reviewDecision` | neu |
| 5 | v1.32.0 released ohne Idempotenz-/Determinismus-Test, obwohl Schwestermodul `gen_e2e.py` exakt so ein Testmuster (`test_generated_suite_is_deterministic`) bereits vorführt | fehlende Validierung | hoch | SURVIVES | `git show a5b8982:tests/test_gen_sitemap.py` (keine Rerun-Tests); Testmuster existiert in `tests/test_gen_e2e.py` | neu |
| 6 | Gleiches Nichtdeterminismus-Muster (`date.today()` in generiertem Artefakt) existiert ungetestet auch in `gen_e2e.py`s `*.manifest.json`-Output (Zeile 553) — aktuell nicht CI-gegatet, aber identische Bug-Klasse bleibt nach dem Vorfall unadressiert | Werkzeug / fehlende Validierung | mittel | SURVIVES | `grep -n "generated.*date.today" src/iil_klickdummy/gen_e2e.py`; `tests/test_gen_e2e.py` prüft nur die `.py`-Datei, nie das Manifest | neu |
| 7 | v1.32.1-Hotfix-Release-PR (#145) dokumentiert die Gate-4-Freigabe **nicht** im PR-Body, obwohl v1.32.0 (#144) das tat — inkonsistente Audit-Spur trotz identischer gated Aktion (PyPI-Publish) | Kommunikation / Prozesslücke | mittel | SURVIVES | `gh pr view 144 --json body` (enthält Satz) vs. `gh pr view 145 --json body` (fehlt) | neu |
| 8 | Reviewer-Freigabe auf #401 (08:46:44Z) erfolgte ~9 Minuten **bevor** die CI für denselben Commit fertig war (Parity-Drift schloss erst 08:54:22Z mit `failure` ab) | fehlende Validierung | mittel | SURVIVES | `gh api .../commits/7049f228.../check-runs` (Abschlusszeiten aller Jobs vs. Approval-Zeitstempel) | neu |
| 9 | risk-hub `main`-Branch-Protection erzwingt **keinen** Pull-Request-Review und listet die Klickdummy-Checks nicht als Required Status Checks — die "Review"-Praxis ist reine Team-Konvention, kein technisches Gate | Werkzeug | mittel | SURVIVES | `gh api repos/iilgmbh/risk-hub/branches/main/protection` (`required_status_checks.contexts` ohne Klickdummy-Checks, kein `required_pull_request_reviews`) | neu (Kandidat für `branch-protection-doc-vs-reality-drift`) |
| 10 | iil-klickdummy `main`-Branch hat **überhaupt keine** Branch-Protection — Feature- und Release-PRs sind technisch komplett ungeschützt | Prozesslücke | hoch | SURVIVES | `gh api repos/iilgmbh/iil-klickdummy/branches/main/protection` → 404 "Branch not protected" | neu |
| 11 | *(positiv)* Fix-Forward-Entscheidung (v1.32.1 same-day statt Yank/Verzögerung) war angemessen — Bug wurde vor Merge des betroffenen Konsumenten-PRs gefangen, kein Schaden propagiert | — | niedrig | SURVIVES | `git branch --contains 7049f228 -r` (Commit existiert nie auf `origin/main`); Check-Run-Historie zeigt Rot→Grün-Zyklus vollständig vor Merge | neu |
| 12 | ADR-211 Rev24 zitiere falsche "verifizierte" Knoten-Zahl (19/46 behauptet vs. angeblich abweichender Ist-Stand) | verfrühte Festlegung (Finder-Fehleinschätzung) | niedrig | **REFUTED** | Skeptiker-Check: `klickdummy/_shared/kd-tree.json` auf `origin/main` zeigt exakt `roots:19, order:46` — Zahlen stimmen; Finder1 hatte fälschlich das interne `nodes`-Dict (28 Einträge) mit dem im ADR zitierten `order`-Feld verwechselt | — |

## 3. Scorecard

| Dimension | Score (1–5) | Anker |
|---|---|---|
| Zielerreichung | 3 | Kernziel (CI-Gate) verfehlt (#1), aber Sitemap selbst aktualisiert + ADR-Vertrag sauber dokumentiert — begründete signifikante Abweichung |
| Architektur/Design | 4 | Extraktion folgt etabliertem Präzedenzmuster (Rev-15-Konvention), sauber modularisiert; ein Mangel (fehlender Determinismus-Test) |
| Code-Konventionstreue | 4 | ruff/format sauber, Commit-Konventionen eingehalten; kleine Abweichung (Naming-Convention-Warning ignoriert, konsistent mit Nachbarmodulen) |
| Risiko/Debt | 2 | Ein Bug geshippt+gefixt, aber strukturell identisches Risiko bleibt offen (#6) UND das eigentliche Gate fehlt (#1) — reales Restrisiko |
| Prozess-Effizienz | 3 | ~2h20 Gesamtlaufzeit, ~25-30% Rework durch den Bug, aber schneller Feedback-Loop; mehrere Review-Lücken (#3,#4,#8) |
| Entscheidungsqualität | 3 | Fix-Forward + Gate-4-Disziplin bei Releases war gut; Zero-Review-Merges + fehlende CI-Verdrahtungs-Verifikation sind echte Mängel |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `klickdummy-sitemap-drift` nur ins Makefile-Metatarget eingehängt, nie in `ci.yml` — Behauptung "Gate scharf" ungeprüft übernommen | Nach jedem neuen CI-Gate-Target die tatsächliche Workflow-YAML lesen (`grep -n <target> .github/workflows/*.yml`) und einen echten CI-Lauf beobachten, der es auslöst — `make <target>` lokal grün ist kein Beleg für "in CI" | #1 |
| Extraktion führte `date.today()` neu ein, wo das Original einen Literal hatte — kein Verhaltens-Diff gegen das Original gezogen | Bei Portierung bestehenden Codes explizit fragen "was macht die neue Version anders, auch unabsichtlich" — als PR-Checkpunkt, nicht "funktional äquivalent" behaupten | #2 |
| PR #401 mit zweitem, ungereviewtem Commit gemergt — Freigabe galt nur für den ersten | Nach Push auf einen bereits approved PR: erneut um Review bitten ODER den Diff des neuen Commits explizit zusammenfassen und bewusste Zweitfreigabe einholen | #3 |
| iil-klickdummy #143/#144 ohne jeglichen Review gemergt, weil Branch-Protection es nicht erzwingt | Für PyPI-publizierende PRs in Repos ohne erzwungene Review-Pflicht selbst `gh pr review --request` nutzen, nicht auf fehlende technische Durchsetzung verlassen | #4 |
| v1.32.0 ohne Idempotenz-Test released, obwohl Schwestermodul das Muster vorführt | Bei neuen Generator-Modulen das Testmuster des nächstverwandten bestehenden Moduls als Checkliste kopieren, bevor released wird | #5 |
| Gleiches Nichtdeterminismus-Muster bleibt in `gen_e2e.py`s Manifest ungetestet liegen | Nach gefundenem Bug-Muster das ganze Package durchsuchen (`grep -rn "date.today\|datetime.now" src/`) und je Fundstelle einen Follow-up-Issue anlegen | #6 |
| v1.32.1-PR dokumentiert Gate-4-Freigabe nicht, obwohl v1.32.0 das tat | Jede Publish-auslösende PR bekommt dieselbe Standardzeile ("Gate-4-Freigabe vom User erteilt am …") als feste Konvention | #7 |
| Freigabe auf #401 erfolgte ~9 Min vor CI-Abschluss | Vor Merge-Entscheidung aktiv auf CI-Abschluss warten, bevor eine Freigabe erteilt/akzeptiert wird | #8 |
| risk-hub-Branch-Protection erzwingt keinen Review, deckt Klickdummy-Checks nicht ab — Doku (CLAUDE.md) behauptet etwas anderes | Branch-Protection-Config einmalig gegen dokumentierte Erwartung abgleichen (`gh api .../protection`) und als eigenen Issue/PR nachziehen | #9 |
| iil-klickdummy `main` hat keine Branch-Protection | Für Pakete mit realen Cross-Repo-Konsumenten minimale Branch-Protection (≥1 Required-Review auf Release-PRs) einrichten, bevor der nächste Release-Zyklus startet | #10 |
| Fix-Forward (v1.32.1 same-day) war die richtige Reaktion — kein Schaden propagiert | Dieses Muster (Root-Cause + Fix + Regressionstest + Patch-Release binnen <1h) als Standard-Reaktion beibehalten — keine Änderung nötig | #11 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (16 Reports, inkl. dieser Session nicht mitgezählt da noch ungeschrieben zum Ausführungszeitpunkt):

```
🚨 GATE-PFLICHT  claim-before-cheapest-check  ×15  [0181a7-incr, 73003f, a50bc6, 54a76c, 17c08c, …]
🚨 GATE-PFLICHT  scope-checkpoint-not-durably-recorded  ×3
🚨 GATE-PFLICHT  planned-phase-no-issue  ×3
🚨 GATE-PFLICHT  handover-stale-vor-merge  ×3
… (5 weitere ×2)
refuted_rate-Band: gesund (weder 3× >0.8 noch <0.2)
```

**Befund #1 dieser Session ist Vorkommen #16 von `claim-before-cheapest-check`** — demselben Muster, das bereits im eigenen `~/.claude/CLAUDE.md` als House-Rule-Gate dokumentiert ist ("'gebaut + lokal grün' ≠ 'funktioniert in Prod' → das Werkzeug einmal echt im Zielkontext laufen lassen, bevor 'validiert/fertig'"). Diese Session hat exakt diese eigene Regel verletzt: die Behauptung "Gate scharf, CI-gebunden" wurde auf Basis eines grünen lokalen `make`-Laufs getroffen, ohne die tatsächliche `ci.yml` zu lesen. Das ist kein neues Muster, das einen neuen Gate-Kandidaten braucht — es ist ein weiterer Beleg, dass das **bestehende** Gate nicht ausreichend verinnerlicht/automatisiert ist. Die anderen 10 Befunde sind Erstvorkommen (keine ≥2-Bestätigung), aber #9 (`branch-protection-doc-vs-reality-drift`) und #4 (`zero-review-merge-on-unprotected-repo`) werden als Kandidaten fürs nächste Mal vorgemerkt.

### 5b. Autonomie-Kalibrierung

- **over_ask: 0.** Kein Fall gefunden, in dem etwas nachweislich deterministisch/reversibel dem User vorgelegt wurde, das autonom hätte laufen können — alle Freigabe-Anfragen (2× PyPI-Release, 1× `--admin`-Merge-Alternative abgelehnt) betrafen echte Gate-4/Gate-3-Situationen.
- **over_act: 0 (formal), 1 Grenzfall.** Kein Verstoß gegen die 5 definierten Gates. Grenzfall: iil-klickdummy PR #143 (Feature-Merge, PyPI-Publish-Vorstufe) wurde autonom gemergt, weil das Repo keine Review-Pflicht technisch erzwingt — das ist **policy-konform** (Merge selbst ist bei fehlender Branch-Protection kein definiertes Gate), aber genau dieser Merge trug den Determinismus-Bug, der dann zwei weitere PRs + einen zweiten Release-Zyklus erzwang. Kein Charter-Verstoß, aber ein Beleg dafür, dass "kein technisches Gate" nicht automatisch "kein Risiko" bedeutet — Kandidat für eine zukünftige Charter-Präzisierung (Publish-Vorstufen-PRs in unprotected Repos selbst gaten), aber mit nur 1 Beleg (keine ≥2-Bestätigung) noch keine Gate-Pflicht.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**Memory-Kandidat 1 (feedback, reinforcement eines bestehenden Gates):**
```markdown
---
name: feedback-ci-gate-wired-into-workflow-not-just-makefile
description: "Gate scharf" heißt Workflow-YAML ruft das Target auf — nicht nur ein Makefile-Metatarget, das lokal grün läuft
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-07-klickdummy-sitemap-gate-not-wired
---
Ein neues CI-Gate-Target in ein Makefile-Metatarget (z.B. `klickdummy: ... neues-target`) einzuhängen ist NICHT dasselbe wie es in `.github/workflows/*.yml` aufzurufen — CI-Jobs rufen oft Einzeltargets direkt auf (`make klickdummy-parity-drift`), nicht den Metatarget.

**Why:** risk-hub-Session 2026-07-07 baute `klickdummy-sitemap-drift`, verifizierte es lokal grün, behauptete "Gate scharf" — aber `.github/workflows/ci.yml` ruft nur `make klickdummy-parity-drift` direkt auf (Zeile 116), nie den Metatarget. Das Gate lief nie in CI. 16. Instanz des bereits gate-pflichtigen Musters `claim-before-cheapest-check`.

**How to apply:** Nach jedem neuen CI-Gate-Target `grep -n <target> .github/workflows/*.yml` — Metatarget-Mitgliedschaft allein reicht nie als Beleg für "in CI aktiv".
```

**Memory-Kandidat 2 (project, risk-hub-spezifisch):**
```markdown
---
name: project_riskhub_branch_protection_doc_vs_reality_2026-07-07
description: risk-hub main-Branch-Protection erzwingt keinen Review + deckt Klickdummy-Checks nicht ab, obwohl CLAUDE.md das Gegenteil suggeriert
metadata:
  type: project
---
`gh api repos/iilgmbh/risk-hub/branches/main/protection` (Stand 2026-07-07): required_status_checks = [Lint+Test, Banned Patterns Scan, Template+Code Validation, Staging Gate (e2e)] — OHNE Klickdummy Parity-Drift/Renderer-#2, und KEIN required_pull_request_reviews-Block. Die "Review vor Merge"-Praxis in diesem Repo ist reine Team-Konvention, kein technisches Gate.

**Why:** entdeckt während Session-Retro 2026-07-07; ein rotes Parity-Drift hätte den Merge-Button nicht blockiert.

**How to apply:** Vor der nächsten Aussage "CI-Gate blockiert Merges" für risk-hub/iil-klickdummy die Branch-Protection live abfragen, nicht aus CLAUDE.md/Makefile-Kommentaren ableiten.
```

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | `klickdummy-sitemap-drift` tatsächlich in `.github/workflows/ci.yml` aufrufen | risk-hub | [#403](https://github.com/iilgmbh/risk-hub/pull/403) | ✅ done (2026-07-07, gemergt, approved wirdigital) | — |
| 2 | `gen_e2e.py`-Manifest-Nichtdeterminismus (Befund #6) fixen oder Issue anlegen | iil-klickdummy | — | 🟢 offen | du: priorisieren |
| 3 | Branch-Protection risk-hub + iil-klickdummy gegen dokumentierte Erwartung abgleichen | beide | — | 🟢 offen | du: Scope/Umfang entscheiden (Review-Pflicht einführen?) |
| 4 | Memory-Kandidaten 1+2 verankern (oder ablehnen) | — | s. §6 | 🔵 ich kann sofort | du: go/no-go |
| 5 | Gate-4-PR-Body-Zeile als feste Konvention (Befund #7) | org-weit | — | 🟡 Vorschlag | du: adr-threshold-Check, ggf. claude-skills.md-Ergänzung |

## 7b. Nachtrag (2026-07-07, gleicher Tag)

Befund #1 (kritisch) wurde noch am selben Tag geschlossen: [risk-hub#403](https://github.com/iilgmbh/risk-hub/pull/403) fügt den fehlenden Step `Sitemap-Freshness-Drift-Gate` direkt in den bestehenden `klickdummy-parity-drift`-Job in `.github/workflows/ci.yml` ein (kein neuer Job nötig, gleiches Setup). **Billigster Check diesmal tatsächlich gezogen, nicht nur behauptet:** CI-Run [28874173906](https://github.com/iilgmbh/risk-hub/actions/runs/28874173906/job/85644639950) zeigt in den Logs `ADR-211 S14 - Sitemap-Freshness: re-generieren + git diff` → `ok Sitemap aktuell (kein Drift)` — der Step lief nachweislich in Actions, nicht nur lokal. Von wirdigital approved, gemergt 2026-07-07T15:01:51Z. Damit ist die 16. `claim-before-cheapest-check`-Instanz aus §5 innerhalb desselben Tages korrigiert.

## 8. Nicht verifiziert (Restlücken)

- **Kommunikationsqualität zwischen den Gates** (wurde der wachsende Scope dem User in Echtzeit gespiegelt, nicht nur an den Gate-Checkpoints selbst?) — aus reinen Git/GitHub-Artefakten nicht rekonstruierbar (Finder3 §8). Aus dem tatsächlichen Sitzungs-Transkript (dieselbe Session, die diesen Retro anfordert) lässt sich das aber direkt belegen: ein expliziter Scope-Checkpoint wurde vor der 3-Repo-Eskalation gestellt (Freigabe-Block "ja 1 2 3"), und vor jedem der beiden PyPI-Releases wurde separat gefragt. Als Hypothese geführt, nicht als Skeptiker-SURVIVES, da diese Quelle kein `gh`/`git`-Artefakt ist.
- **C4 (unverifizierbar):** die behauptete fehlgeschlagene `gh pr merge`-Attempte auf platform#980 vor Freigabe lässt sich aus GitHub's Event-Trail strukturell nicht beweisen oder widerlegen (lokale CLI-Fehler hinterlassen keine Server-Events). Billigster verbleibender Check: keiner verfügbar — als dauerhafte Wissenslücke akzeptieren.
- **Phase 6 (Extern-Handoff) nicht durchgeführt** — Footprint `full`, nicht `deep`; kein externer Methoden-Check dieser Retro selbst.
