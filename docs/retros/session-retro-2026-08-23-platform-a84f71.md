---
retro_schema: 1
date: 2026-08-23
repo_scope: [platform]
session_id: a84f71
footprint: full
findings_total: 11
findings_survived: 8
refuted_rate: 0.27
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [gate-modul-prueft-weniger-als-sein-name]
recurring_findings: [claim-before-cheapest-check, same-file-serial-prs, partial-fix-not-generalized-to-sibling-artifacts, gate-matches-spelling-not-substance]
gates_caught: []
---

# Session-Retro 2026-08-23 — platform (a84f71): drei Gate-PRs, und zwei Verzichte, die am selben Tag widerlegt wurden

## 1. Executive Summary

- **Das Sitzungsziel wurde erreicht** (rückfällige Gates 4 → 1, das verbliebene benannt und befristet), und beide Selbstanklagen der Finder fielen in der Falsifikation — die Fehlerrichtung war Strenge, nicht Nachsicht.
- **Der schwerste Fund kam aus einem widerlegten Befund:** Das Gate `lint-failure-no-local-gate` ist `blocking`, heißt „lint" und führt `ruff format --check` aus — es kann Linter-Regeln wie E402 **strukturell nie** sehen. Kein Rückfall, sondern eine Lücke seit Bau am 2026-08-04.
- **Zwei Verzichte dieser Sitzung sind am selben Tag von der Realität widerlegt worden:** `gate-matches-spelling-not-substance` (Befund 5) und `partial-fix-not-generalized-to-sibling-artifacts` (Befund 1) wurden als „Meta-Muster, nicht mechanisch erkennbar" in die `declined`-Liste eingetragen — und traten beide binnen Stunden erneut auf, beide mechanisch nachweisbar.
- **Der eigene Fix reproduzierte seinen eigenen Fehler:** Der Default-Flip in `record()` wurde nur an den WARN-Zweigen nachgezogen; zwei PASS-Zweige etikettieren fremde Repos jetzt als `platform`.
- **Zwei Ursachenbehauptungen ohne den billigsten Check** — „Automerge war schneller" (real: ein anderer Account mergte) und eine Selbstanklage im Commit-Text, die der Skeptiker widerlegte.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Default-Flip in `record()` nur an WARN-Zweigen nachgezogen: `0.4 repo-sync` (Z. 152) und `0.7 deploy-scan` (Z. 391) melden PASS ohne 4. Argument und etikettieren fremde Repos als `platform` | fehlende Validierung | mittel | SURVIVES | `git show origin/main:tools/session_start_checks.sh \| sed -n '152p;391p'` — beide ohne 4. Arg; `0.7` scannt laut Z. 313 zehn Fremd-Repos, `platform` ist keins davon. Mildernd: bei PASS heilt `befund_journal.aufnehmen()` phasenweit, das Etikett wirkt dort nicht — nur in der Summary-Tabelle (Hypothese, s. §8) | `partial-fix-not-generalized-to-sibling-artifacts` |
| 2 | `--sitzungsende`-Bypass in `worktree-reaper.classify()` überspringt die Karenz **ohne** Altersprüfung; ein von zwei Sitzungen geteilter, sauberer Baum mit gemergtem PR kann entfernt werden, während die zweite Sitzung noch läuft | fehlende Validierung | hoch | SURVIVES | `tools/worktree-reaper.py` Z. 273-277 (kein `alter`-Guard) vs. Z. 278-287 (mit Guard); Aufrufer `tools/hooks/reap_worktrees.sh` reicht `cwd` unbesehen durch. Mildernd: `dirty` bleibt SKIP, Branch bleibt, Restore-Manifest existiert — Verlust ist das Verzeichnis, nicht die Arbeit | — |
| 3 | `policy_frische.py` ruft nirgends `git fetch`; der Vergleich läuft gegen den **lokalen** Tracking-Ref. Docstring behauptet „gegen origin/main" ohne diese Einschränkung | Werkzeug | mittel | SURVIVES | `tools/policy_frische.py` `kanonisch()` Z. 51-53; eigener Test `tools/tests/test_policy_frische.py:39-45` baut einen lokalen Branch *namens* `origin/main` und kommentiert das ausdrücklich. Im Runner-Pfad durch Phase 0.2 entschärft, bei manuellem Aufruf nicht | — |
| 4 | `kalibrier_stand()`: bei fehlendem oder `0`-`min_beurteilbar` kann „entscheidungsreif" nie eintreten; Fenster hängt bis Fristablauf in „sammelt". Kein Test deckt den Rand | Werkzeug | niedrig | SURVIVES | `tools/gate_wirkung.py` Bedingung `beurteilbar >= mindest and mindest > 0`; `tools/tests/test_gate_wirkung.py:331-397` ohne diesen Fall. Aktuell unerreicht (einziges Fenster hat `min_beurteilbar: 10`) | — |
| 5 | Gate `lint-failure-no-local-gate` (`blocking`) führt `ruff format --check` aus, nicht `ruff check` — Linter-Regeln liegen seit Bau außerhalb seiner Reichweite, obwohl der Slug sie verspricht | Werkzeug | hoch | SURVIVES | Skeptiker-Experiment: Datei mit E402, sauber formatiert → `ruff format --check` „already formatted", exit 0; `ruff check` meldet 2× E402. Modul-Zeile: `$RUFF format --check --force-exclude`. Hook war verdrahtet (`settings.json` PreToolUse/Bash) und aktiv (`pyproject.toml` hat `[tool.ruff]`) | `gate-matches-spelling-not-substance` |
| 6 | Commit-Text `ff74c42f` behauptet einen Disziplinbruch („das Gate existiert genau dafür und ich habe es nicht benutzt"), der nicht stattfand — das Gate hätte E402 auch bei Benutzung nicht gefangen | fehlende Validierung | mittel | SURVIVES | Selbstanklage in `git show ff74c42f`; widerlegt durch Befund 5. Der billigste Check (Modul lesen) kostete den Skeptiker einen Blick | `claim-before-cheapest-check` |
| 7 | „Automerge war schneller" als Erklärung für den bereits gemergten PR #2237 — ungeprüfte Ursachenbehauptung | fehlende Validierung | mittel | SURVIVES | `gh pr view 2237 --json mergedBy` → `login: wirdigital`; `automerge`-Check steht bei allen drei PRs auf `skipping`. Billigster Check wäre genau diese eine Abfrage gewesen | `claim-before-cheapest-check` |
| 8 | Drei serielle PRs derselben Sitzung ändern dieselben zwei Dateien (`gate-registry.json`, `session_start_checks.sh`), gemergt 13:21 / 14:26 / 15:03 | Prozesslücke | mittel | SURVIVES | `gh pr view {2236,2237,2238} --json files`. Derselbe Slug steht in #2238 auf der Liste der neun noch ungegateten Muster | `same-file-serial-prs` |
| 9 | Scope Creep: Gate gebaut statt entschieden (`platform-pinned-perma-dirty-loop`) | verfrühte Festlegung | mittel | **REFUTED** | Issue #2234 verlangt für diesen Slug wörtlich „vor dem Ablegen einmal pruefen, ob die Ursache wirklich weg ist"; die Prüfung war Teil des Auftrags, ihr Ergebnis erzwang die Eskalation. „Gate bauen" ist laut Issue-Kopf einer der drei zulässigen Abschlüsse | — |
| 10 | Freigabe ohne Wirkung: Punkt 31 wurde vorgelegt, obwohl die Änderung schon gemergt war | Prozesslücke | mittel | **REFUTED** | `~/.claude/hooks/managed/manifest.json` `generated_at: 14:27:51Z` vs. PR #2237 `mergedAt: 14:26:00Z` — die Verteilung lief 1:51 min **nach** dem Merge. Detektor (gemergt) und Verteilung (danach) sind zwei Schritte | — |
| 11 | Gate `lint-failure-no-local-gate` ist rückfällig geworden | Werkzeug | hoch | **REFUTED** | Rückfall setzt einen früheren Fang-Zustand voraus; das Modul konnte E402 nie sehen. Ersetzt durch Befund 5 | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle sechs Aufträge geliefert; Sitzungsziel erreicht (4 → 1 rückfällig, das verbliebene benannt und befristet). Abzug für Befund 1 |
| architektur_design | 3 | Der Default-Flip ist die richtige Richtung, aber unvollständig durchgezogen (1); der Karenz-Bypass hat eine Guard-Lücke (2) |
| code_konventionstreue | 4 | Worktree statt Haupt-Tree, Commit-Format, 2857 Tests grün, alle Drills frisch, ruff sauber am Ende. Abzug für den E402-Push |
| risiko_debt | 3 | Neue Debt aus (2) und (3), aber nichts ungetrackt: #2234, #2235, #1187 und #2143 decken jede aufgeschobene Zeile |
| prozess_effizienz | 3 | Drei PRs auf dieselben zwei Dateien (8), ein CI-Rot mit Nachbesserungs-Commit |
| entscheidungsqualitaet | 3 | Die technischen Entscheidungen hielten der Falsifikation stand (9, 10 REFUTED), aber zwei Ursachenbehauptungen gingen ohne den billigsten Check in durable Artefakte (6, 7) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Default in `record()` geflippt, danach nur die WARN-Zweige annotiert (Z. 152/391 blieben) | Beim Ändern eines **Defaults** alle Aufrufstellen einmal mechanisch auflisten (`grep -n 'record "'`) und jede einzeln beurteilen — nicht nur die, die man gerade im Blick hat | #1 |
| Karenz-Bypass springt direkt auf REAP_MERGED, sobald der Pfad genannt ist | Der Bypass verlangt zusätzlich, dass **kein anderes Lease** auf denselben Pfad zeigt; sonst greift die Karenz weiter | #2 |
| `policy_frische.py` vergleicht gegen einen Ref, den es selbst nie aktualisiert | Entweder selbst `git fetch` fahren, oder im Bericht ausgeben, wie alt der Ref ist — eine Frische-Aussage, die ihre eigene Frische nicht kennt, ist keine | #3 |
| Randfall `min_beurteilbar=0` blieb ungetestet, weil er aktuell nicht vorkommt | Beim Schreiben einer Schwellwert-Bedingung den Wert `0`/fehlend als eigenen Drill mitnehmen — „kommt nicht vor" ist eine Annahme über die Zukunft | #4 |
| Gate-Slug versprach „lint", Modul prüfte „format"; niemand hat je gefragt, ob der Drill den namensgebenden Fall abdeckt | Beim Registrieren eines Gates einen Drill verlangen, der **den Fall aus dem Slug-Namen** auslöst — und für den Bestand einmal nachziehen | #5 |
| Eigenes Versagen im Commit-Text behauptet, ohne das Gate-Modul gelesen zu haben | Eine Selbstanklage ist eine prüfbare Behauptung wie jede andere: erst das Modul lesen, dann sich anklagen | #6 |
| Ursache für einen fremden Merge geraten („Automerge") statt `mergedBy` abzufragen | Bei jeder Aussage über die Ursache eines beobachteten Ereignisses die eine Abfrage fahren, die sie belegt — hier `gh pr view --json mergedBy` | #7 |
| Drei Aufträge, drei PRs, dieselben zwei Dateien | Aufträge, die dieselbe Datei anfassen, in einem PR bündeln — oder bewusst seriell und das im PR-Text als Entscheidung benennen | #8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 89 Reports:
- **37 Slugs ≥2 ⇒ Gate-Pflicht**, davon 8 bewusst ohne Gate (Owner-Entscheidung, fünf davon aus dieser Sitzung) und **9 ohne registriertes Gate**.
- `refuted_rate`-Band: `8d6869:0.40 · beefc148:0.55 · f9cbb7:0.30 · b62038:0.00 · 1904bf:0.50 · 8d6869-incr:0.00 · b4f5fb:0.37 · b82988:0.09` — dieser Report mit **0.27** liegt im Band.
- Score-Mittel: `risiko_debt` 2,55 bleibt über 89 Messungen die schwächste Dimension.

Drift-Memory-Abgleich (Existenz per `ls` geprüft): `feedback_comment_claims_a_guard_the_code_does_not_have` (deckt Befund 5), `feedback_claim_reaches_further_than_the_look` (6, 7), `feedback_gate_built_is_not_gate_effective` (5), `feedback_null_from_own_filter_needs_positive_control`, `feedback_shared_worktree_multisession_git_collision` (2) — alle vorhanden, keine Phantom-Referenz.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`: **1 Gate rückfällig** — `claim-before-cheapest-check` (2× seit Umbau 2026-08-20). Die Befunde 6 und 7 dieses Reports sind zwei **weitere** Vorkommen.

Antwort auf den Rückfall: **ausweiten**. Das Gate sieht Behauptungen über Zustände; die hier aufgetretene Familie ist eine andere — **Behauptungen über die URSACHE eines beobachteten Ereignisses** („Automerge war schneller", „ich habe das Gate nicht benutzt"). Beide sind syntaktisch Erklärungen, nicht Zustandsaussagen, und beide waren mit genau einer Abfrage prüfbar. Das läuft nicht ins Kalibrierfenster (Frist 2026-09-20) hinein, sondern ist ein eigener Musterzweig.

**Ehrlichkeits-Sperre beachtet:** 11 der 26 Gates stehen auf `zu-frueh`, sechs davon durch diese Sitzung (drei Umbauten mit `revised: 2026-08-23`, drei Neuregistrierungen). `zu-frueh` ist **kein** Wirksamkeitsbeleg — die Reduktion von 4 auf 1 rückfällige Gates ist ein Zwischenstand, keine belegte Verbesserung.

**Zwei Verzichte dieser Sitzung sind am selben Tag widerlegt worden.** In die `declined`-Liste ging `gate-matches-spelling-not-substance` mit der Begründung, kein Scanner könne generisch erkennen, dass ein Gate die Schreibweise statt der Sache trifft — Befund 5 ist genau dieser Fall, und er war mit einem Experiment nachweisbar. Ebenso `partial-fix-not-generalized-to-sibling-artifacts`, widerlegt durch Befund 1. Beide Verzichte gehören überprüft, bevor sie stehen bleiben.

## 5b. Autonomie-Kalibrierung

- `over_ask`: **0** belegt. Der einzige Kandidat (Punkt 31) wurde in Befund 10 widerlegt — die Verteilung war zum Zeitpunkt der Vorlage nachweislich noch nicht gelaufen.
- `over_act`: **0**. Alle drei Merges lagen ausdrückliche Owner-Anweisungen zugrunde; die Hook-Verteilung auf die Live-Maschine war die vom Owner mit „31 … go" freigegebene Handlung.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: feedback-gate-modul-prueft-weniger-als-sein-name
description: Ein registriertes Gate kann seit Bau weniger prüfen, als sein Slug verspricht — den namensgebenden Fall einmal auslösen
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-23-lint-gate-prueft-format-nicht-lint
---

`lint-failure-no-local-gate` steht als `blocking` in der Registry, heißt „lint" und
führt `ruff format --check` aus. Linter-Regeln wie E402 lagen seit dem Bau am
2026-08-04 außerhalb seiner Reichweite; ein E402-Push ging durch und machte die CI
zweimal rot (2026-08-23, PR #2236).

**Why:** Registry, Drill und Verdrahtung waren alle grün — geprüft wurde nie, ob der
Drill den Fall auslöst, der im Slug steht. Ein Gate kann vollständig gebaut,
verdrahtet und gedrillt sein und trotzdem die Sache verfehlen, die es benennt.

**How to apply:** Beim Registrieren eines Gates einen Drill verlangen, der den
namensgebenden Fall wirklich auslöst — und beim Bestand einmal nachziehen:
für jedes Gate fragen, welches Kommando sein Modul ausführt und ob dieses
Kommando den Slug einlöst. Verwandt: [[feedback-comment-claims-a-guard-the-code-does-not-have]],
[[feedback-gate-built-is-not-gate-effective]].
```

```markdown
---
name: feedback-cause-claim-needs-the-one-query
description: Eine Aussage über die URSACHE eines beobachteten Ereignisses braucht die eine Abfrage, die sie belegt
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-23-automerge-war-es-nicht
---

Auf „already merged" folgte die Erklärung „Automerge war schneller". Real hatte ein
anderer Account (`wirdigital`) gemergt; `automerge` stand bei allen drei PRs auf
`skipping`. Der billigste Check war eine einzige Abfrage: `gh pr view <n> --json mergedBy`.

**Why:** Der Evidenz-Scanner fängt Behauptungen über Zustände („CI ist grün"). Eine
Ursachen-Erklärung sieht wie eine Nebenbemerkung aus und ist doch eine prüfbare
Behauptung — sie war hier falsch und stand danach im Gesprächsverlauf.

**How to apply:** Sobald ein Satz erklärt, WARUM etwas passiert ist, die Abfrage
nennen, die es belegt — oder den Satz als Vermutung kennzeichnen. Gilt auch für
Selbstanklagen: „ich habe X nicht benutzt" ist prüfbar und war 2026-08-23 falsch.
Verwandt: [[feedback-claim-reaches-further-than-the-look]].
```

**adr_candidates** — keine. Alle Befunde sind Werkzeug- oder Prozessfragen unterhalb der ADR-Schwelle (`~/.claude/policies/adr-threshold.md`: reine Ergänzung nach bestehendem Muster braucht kein ADR).

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Zwei Verzichte revidieren (heute widerlegt) — https://github.com/achimdehnert/platform/issues/2234
2. 🟢 Gate-Bestand: Drill löst den namensgebenden Fall aus? — https://github.com/achimdehnert/platform/issues/2143

### 🔵 Offen — ich kann sofort

3. 🔵 `ruff check` in `block_unformatted_push.sh` — Befund 5
4. 🔵 Karenz-Bypass: fremdes Lease auf gleichem Pfad — Befund 2
5. 🔵 PASS-Zweige 0.4/0.7 nachziehen — Befund 1
6. 🔵 `policy_frische.py` Ref-Alter ausgeben — Befund 3
7. 🔵 Drill für `min_beurteilbar=0` — Befund 4

## 8. Nicht verifiziert (Restlücken)

- **Befund 1, mildernder Umstand:** dass ein PASS-Etikett im Journal wirkungslos ist (weil `aufnehmen()` phasenweit heilt), stammt aus dem Lesen der Datei **während** der Sitzung, nicht aus unabhängiger Prüfung. Als Hypothese geführt. Billigster Check: `grep -n "PASS" -A6 tools/befund_journal.py` durch einen fremden Kontext.
- **Worktree-Hygiene:** Die drei Session-Worktrees existieren nach dem Merge ihrer PRs weiter. Ob das ein Rückfall von `worktree-midsession-accumulation` ist, lässt sich erst nach dem nächsten SessionEnd sagen — der Fix aus #2237 greift genau dort. Der Prozess-Finder konnte es nicht entscheiden (kein Sitzungs-Log-Zugriff). Billigster Check: nach dem nächsten Sitzungsende `git worktree list | grep 2026-08-23`.
- **Freigabe für den Merge von #2237 durch `wirdigital`:** Dass die Owner-Anweisung „merge #2237" vorlag, ist durch den Gesprächsverlauf gedeckt, nicht durch ein Artefakt. Der Merge selbst kam von einem anderen Account. Billigster Check: Owner fragen, ob der Merge abgestimmt war.
- **Nicht abgesucht:** die Inhalte der übrigen Drills (`test_evidence_claim_scanner.py` u.a.) — außerhalb der drei Finder-Dimensionen.

**Getan** — drei PRs gemergt und aus dem kanonischen Pfad als wirksam geprüft; rückfällige Gates 4 → 1; ungedeckte Slugs 18 → 9; zwei Hook-Lanes verteilt.
**Angenommen** — dass `zu-frueh` sich in den nächsten Retros zu „wirksam" wandelt; dass das SessionEnd-Event ein `cwd`-Feld trägt.
**Nicht verifizierbar** — die drei Punkte oben.
**Offen geblieben** — neun Gate-Vorschläge (#2234), das Kalibrierfenster bis 2026-09-20, die Ausweitung `lint-failure-no-local-gate` auf Tests (#1187).
