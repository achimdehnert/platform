---
retro_schema: 1
date: 2026-08-25
repo_scope: [dev-hub, platform, mcp-hub, 137-hub, billing-hub, cad-hub, dms-hub, learn-hub, pptx-hub, travel-beat, weltenhub]
session_id: 8f9a23
footprint: deep
findings_total: 12
findings_survived: 9
refuted_rate: 0.25
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [pr-merged-but-last-push-missing, chained-shell-continues-after-block-failure, blacklist-guard-instead-of-whitelist]
recurring_findings: [claim-before-cheapest-check, partial-fix-not-generalized-to-sibling-artifacts, deferred-item-no-tracking-issue, handover-stale-vor-merge, scope-checkpoint-not-durably-recorded, gate-approval-needs-pr-comment, same-file-serial-prs]
gates_caught: [claim-before-cheapest-check, handover-stale-vor-merge]
over_ask: 0
over_act: 1
---

# Session-Retro 2026-08-25 — dev-hub (8f9a23)

**Methode:** deep. 1 Collector (haiku) · 3 Finder (sonnet, frischer Kontext, nur Artefakte) · 3 Skeptiker (sonnet; 1 Finder-Konflikt, 2 Bewertungsbefunde) · Meta-Reviewer (sonnet, nur Report). Haupt-Session hat in Phase 4 keine neuen `gh`/`git`-Befehle ausgeführt.
**Footprint:** 13 gemergte dev-hub-PRs (#283–#297), 2 Migrationen (`catalog/0003`, `releases/0003`), ~20 Prod-Deploys; Schreibzugriffe in 42 Repos (7+10 Dependabot-Merges, 81 Schließungen, 8 Fremd-Branches per Contents-API editiert und gemergt); platform#2288. Keine Reduktion von `deep` (Migration + Prod + ≥3 Repos; Befund-Dichte hoch).

## 1. Executive Summary

- Ziel #286 (Backlog + Handover) 5/5 belegt und geschlossen; Auftrag #289 (Referenzen statt Redundanzen) K1–K3 auf Prod belegt (Katalog stündlich aus `catalog-info.yaml`, SHA sichtbar, `make frische` deterministisch), K4/K5 offen.
- **Zwei falsche Fertig-Meldungen** aus derselben Wurzel: „K3 erfüllt, stündlich" (Commit nie in main, Owner-Squash kam vor dem Nachschub-Push) und „Branch bleibt bestehen" in 96 Schließ-Kommentaren (Dependabot löscht seine Branches). Beides `claim-before-cheapest-check` — das Gate ist verdrahtet und war hier blind, weil die Behauptungen auf einem *falschen* Werkzeug-Beleg standen, nicht auf keinem.
- Der Concurrency-Fix-Sweep vom 23.08. (13 Repos, Fremd-Session) trug in 9 von 13 Repos den falschen Prod-Default; dev-hub #285 hat ihn gemergt und Prod-Läufe abgebrochen (#288 korrigiert 22 min später); die 8 Geschwister wurden vor dem Merge gefunden und korrigiert.
- Autonomie sauber gegated (jeder Merge mit Owner-Wort), aber die Freigaben leben nur im Chat: mcp-hub-Ruleset-Bypass (`--admin`, 10 PRs) ohne Artefakt im Zielsystem.
- Rest-Debt getrackt bis auf eins: 5 Pakete ohne `x-pypi-packages` haben kein Issue in ihren Quell-Repos; Handover eingefroren auf dem Stand nach #290.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | „K3 erfüllt: Stand ≤ 1 h" (#289, 10:20 UTC) war falsch — Weg-B-Commit d7fd6b1 nach Owner-Squash von #293 gepusht, nie in main; Import lief 2 h nur manuell; Selbstkorrektur 10:45, Fix #296 | fehlende Validierung | hoch | SURVIVES | `git log origin/session/…/k3a-katalog-referenz --not origin/main` → d7fd6b1; `git show 5a963ae:config/settings/base.py` = daily; #289-Kommentare 10:20/10:45 | claim-before-cheapest-check ×67 · pr-merged-but-last-push-missing (neu) |
| 2 | Schließ-Kommentar der Welle E behauptet „Der Branch bleibt bestehen" — für Dependabot-PRs falsch (Branch nach Close gelöscht: travel-beat#69, pptx-hub#15 → 404) — 96-fach publiziert | fehlende Validierung | mittel | SURVIVES (neu aus Phase 3) | `gh api repos/achimdehnert/travel-beat/branches/dependabot/…-1.0.14` → 404; Kommentar 11:20:46Z | claim-before-cheapest-check (2. Instanz) |
| 3 | #285 (Fremd-Sweep platform#2229, 13 Repos) setzte Concurrency-Default `push→'staging'` + cancel-in-progress, obwohl dev-hub bei push nach production deployt; dev-hub mergte ihn ohne Repo-Check; Run 32816357360 mid-flight gekillt; #288 22 min später; 8 Geschwister-PRs trugen denselben Fehler und wurden vor Merge korrigiert | verfrühte Festlegung / fehlende Validierung | mittel | SURVIVES | `gh run view 32816357360 --json jobs` (Jobs gestartet, cancelled 06:18:27); #285-Body „nicht verifiziert"; 8×2. Commit + Merge 11:57 | partial-fix-not-generalized-to-sibling-artifacts ×6 |
| 4 | mcp-hub: 10 Dependabot-PRs per `--admin` gemergt (Bypass Ruleset `main-required-checks`, Review-Pflicht) — Freigabe nur im Chat („1 --admin"), kein Kommentar/Issue im Zielrepo; CI aller Stichproben grün | Kommunikation / Prozesslücke | mittel | SURVIVES | `gh pr view 221/213 -R achimdehnert/mcp-hub --json comments` → keine Freigabe-Spur; Ruleset active | scope-checkpoint-not-durably-recorded ×20 · gate-approval-needs-pr-comment (ohne Gate) |
| 5 | 5 Pakete ohne `x-pypi-packages` (docs-agent, iil-aifw, platform-context, iil-fieldprefill, nl2cad-ifc): „Korrektur im Quell-Repo" nur als Prosa in #289/#296 — kein Issue in dev-hub/mcp-hub/iil-fieldprefill/cad-hub (Gegenbeispiel B5 → platform#2288 korrekt) | still weggelassen | mittel | SURVIVES | `gh search issues --owner achimdehnert "catalog-info x-pypi-packages"` → 0 | deferred-item-no-tracking-issue ×27 — **Gate rückfällig** |
| 6 | `AGENT_HANDOVER.md` auf origin/main eingefroren nach #290 (Prio 0 = „#289 K2 🔵 ready"), obwohl #291–#297 gemergt; zugesagter Nachzieh-PR nicht erfolgt | Prozesslücke | mittel | SURVIVES | `git log origin/main -- AGENT_HANDOVER.md` → letzter 0b015fd | handover-stale-vor-merge ×18 (Runner 0.7.4 fing die erste Instanz am Start → gates_caught) |
| 7 | PR #290 eröffnet mit Commit-Message, die einen Handover-Diff behauptete, der fehlte; 67 s später Amend + Force-Push (`head_ref_force_pushed` 06:54:20Z); dazu #263-Schließkommentar zunächst mit Tool-Fehlermeldung („aborted: you must first push…"), 41 s später korrigiert; **dritte Instanz beim Schreiben dieses Reports:** Korrektur-Block scheiterte am Zitat, Commit + platform#2311 gingen unkorrigiert raus, Nachtrag als 2. Commit | Werkzeug | mittel | SURVIVES (Finder-Konflikt per Timeline entschieden) | `gh api …/issues/290/timeline` → head_ref_force_pushed; `gh pr view 263 --json comments` 06:20:42/06:21:23 | chained-shell-continues-after-block-failure (neu) |
| 8 | `beat_aufraeumen --auch NAME` schützt nur Settings- und Eigen-Einträge (Blacklist); ein benannter Migrations-Eintrag (`mail-agent-ingest-daily-iil`) ist löschbar und käme erst bei Fresh-DB wieder (RunPython läuft einmal) | Tech-Debt | niedrig | SURVIVES | `git show origin/main:apps/core/zeitplan.py` Z.85–89; `tests/test_zeitplan.py` ohne Test dafür; `apps/mail_agent/migrations/0011` RunPython | blacklist-guard-instead-of-whitelist (neu) |
| 9 | Serien-PRs #293→#297 (2 h 13 min) auf `apps/catalog/services.py`/`tasks.py` | Prozess | niedrig | SURVIVES (belegt, aber durch Gate 2 erzwungen: jeder Body „Gate 2 … Owner-Wort") | `gh pr view 293..297 --json files,body` | same-file-serial-prs ×6 |
| 10 | `TOLERANZ_CRONTAB` 2 h fest, „nicht begründet, nicht generalisiert" | Design-Debt | niedrig | REFUTED | Begründung steht in `frische.py:34–36`/`toleranz()`; keine wöchentliche Quelle in `QUELLEN`; kein konkretes Fehlurteil | — |
| 11 | Welle E ohne Vorab-Kriterien-Artefakt = Prozesslücke | Prozesslücke | mittel | REFUTED | Hausregel verlangt Artefakt *im selben Zug*; Schließ-Kommentar synchron zu `closedAt` mit Freigabe/Kriterium/Umfang; kein PR < 30 d geschlossen | — |
| 12 | „#290 ohne Handover-Diff / Force-Push — kein Artefakt" (Finder-3-Nullbefund) | — | — | REFUTED | Timeline-Event belegt das Gegenteil (→ #7) | — |

Positivkontrollen (kein Befund): #288 wirkt — die drei `cancelled`-Runs 07:14–07:15 hatten `jobs: []` (Pending-Replace, GitHub-Queue-Semantik), keine In-Progress-Kills mehr · Contents-API-Korrektur auf 8 Fremd-PRs statt eigener PRs vertretbar, Stichprobe cad-hub/billing-hub origin/main korrekt · Prod-Schreibzugriffe (`sync_catalog_info`, `beat_aufraeumen`) in PR-Bodies/Issue-Kommentaren dokumentiert · B5 korrekt Out-of-Scope + platform#2288 · #295 „kein Leser" per `git grep origin/main` bestätigt · #291 entfernte eine ORM-Query aus `apps/operations/views.py` (Service-Layer aktiv verbessert).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | #286 5/5 geschlossen; #289 K1–K3 Prod-belegt; K4/K5 offen; eine 2-h-Falschmeldung (#1) |
| architektur_design | 4 | Frische-/Zeitplan-Komponente lesen die Zusage aus Settings/Registry statt sie zu duplizieren; Restrisiko Blacklist (#8) |
| code_konventionstreue | 4 | Service-Layer eingehalten und in operations verbessert (Positivkontrolle #291, s. §2); 26+9+5 Tests; Commit-Format; Abzug für #8 (Blacklist-Schutz ohne Test) |
| risiko_debt | 3 | #5 untrackt, #6 Handover stale, #2 falsche Aussage in 96 Artefakten, #8 |
| prozess_effizienz | 3 | #1 (35 min Falschstand), #7 (2 Werkzeug-Pannen mit Korrektur), mcp-hub-Merges in 3 Durchgängen, #9 |
| entscheidungsqualitaet | 4 | Weg B (Owner-Entscheid statt Abschwächen), Contents-API-Korrektur, B5 Out-of-Scope, Welle E mit Kriterium; Abzug für #4 (Bypass ohne Artefakt) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Nach „1 done" wurde `gh pr checks` (Branch-Head) als Beleg für „in main" genommen; Owner-Squash lag vor dem Nachschub-Push | Nach jedem Merge den **eigenen letzten SHA bzw. Inhalt gegen `origin/main`** prüfen (`merge-base --is-ancestor` / `git show origin/main:<datei> \| grep <marker>`); Nachschub auf einen freigegebenen PR vorher ankündigen oder als eigenen PR schicken | #1 |
| Schließ-Kommentar mit Reversibilitäts-Aussage ohne Prüfung des Dependabot-Verhaltens | Vor einer Massen-Aktion die Aussage **an einem Exemplar** prüfen (1 Dependabot-PR schließen → `gh api …/branches/<b>`), dann den Text festlegen | #2 |
| Fremd-Sweep-PR #285 gemergt, ohne den Repo-eigenen Deploy-Default gegen den Diff zu halten | Für jeden Sweep-PR: Diff-Default gegen `deploy.yml` des Ziel-Repos (`target_environment \|\| '…'`) prüfen — genau der Check, der später die 8 Geschwister rettete, **vor** dem ersten Merge | #3 |
| `--admin`-Merges mit Chat-Wort, kein Artefakt | Bypass-Freigabe als **einen** Kommentar im Zielrepo (z. B. auf dem ersten gemergten PR oder einem Tracking-Issue) mit Wortlaut und Umfang, bevor der erste `--admin` läuft | #4 |
| „Korrektur im Quell-Repo" als Prosa in #289 | Je Quell-Repo ein Issue im selben Zug (wie B5 → platform#2288) — oder ein Verzicht mit Grund im Ziel-Issue; Prosa zählt nicht | #5 |
| Handover-Nachzug „im nächsten PR" ohne Fälligkeit | Handover-Stand an den **letzten** Merge einer Sitzung koppeln (session-ende Phase), nicht an den ersten; bei Verschiebung ein Fälligkeits-Trigger (Runner 0.7.4 meldet STALE — das ist der Trigger, er wurde ignoriert) | #6 |
| Verkettete Shell: Python-Heredoc scheitert (Anführungszeichen), `git commit`/`gh pr create` laufen trotzdem | Deutsche Texte nur per `<<'EOF'`/`--body-file -`/`-F -`; nach jeder Edit+Commit+PR-Kette den **PR-Diff** prüfen (`gh pr view N --json files`), nicht die Commit-Message | #7 |
| `--auch` prüft gegen eine Sperrliste (Settings + Eigen-Einträge) | Whitelist: `--auch` nur für Einträge, die weder in Settings noch per Migration angelegt sind — Migrations-Einträge markieren (z. B. `description="migration:mail_agent.0011"`) und im Abgleich als geschützt führen; Test dafür | #8 |
| Fünf Serien-PRs auf denselben Dateien, jeder mit eigenem Prod-Deploy | Bei Gate-2-Repos Folgebefunde eines Prod-Laufs **sammeln** und als eine Welle mit einem Owner-Wort mergen („Welle N go" existiert als Muster) — statt je Befund ein Deploy | #9 |

## 5. Längsschnitt (retro_kpis.py, Stand vor diesem Report)

`claim-before-cheapest-check` ×66 → 67 · `deferred-item-no-tracking-issue` ×26 → 27 · `scope-checkpoint-not-durably-recorded` ×19 → 20 · `handover-stale-vor-merge` ×17 → 18 · `partial-fix-not-generalized-to-sibling-artifacts` ×5 → 6 · `same-file-serial-prs` ×5 → 6. Alle sechs sind bereits GATE-PFLICHT (≥2). Drift-Memories dieser Sitzung (existieren, per `ls` geprüft): `drift_pr_merged_but_last_push_missing.md`, `drift_german_quotes_break_inline_strings.md`.

### 5a. Rückfall-Prüfung (gate_wirkung.py)

| Gate | Stand vor Report | Diese Sitzung | Antwort |
|---|---|---|---|
| `claim-before-cheapest-check` (blocking Stop-Hook, gebaut 2026-08-20) | RUECKFAELLIG, 4× seit Bau | 2 weitere (#1, #2) **plus** 1 gefangen (Hook feuerte auf „Repo-Health keine Zeitfelder", Positivkontrolle nachgeholt) | **ausweiten** — der Hook erkennt Behauptungen *ohne* Tool-Lauf im Turn; #1 und #2 standen auf einem Tool-Lauf, der die falsche Frage beantwortete (`gh pr checks` statt `origin/main`; Kommentartext statt Branch-Existenz). Marker-Klasse „merged/in main/bleibt bestehen/gelöscht" → verlangt Ref-Beleg (`merge-base`, `git show origin/main:`, `gh api …/branches`) |
| `deferred-item-no-tracking-issue` (advisory, 2026-08-23) | RUECKFAELLIG, 2× seit Bau | #5 (3. Rückfall) | **umbauen** — advisory reicht nicht; session-ende Phase 0f fragt nur Fremd-Repo-*Befunde* des Runners ab, nicht Prosa-Zusagen in PR-/Issue-Texten. Scanner über eigene Kommentare/Bodies auf „im Quell-Repo", „nicht hier", „Folge-PR", „später" → Issue oder Verzicht erzwingen |
| `scope-checkpoint-not-durably-recorded` (advisory, 2026-08-23) | RUECKFAELLIG, 2× seit Bau (letzter Rückfall 2026-08-25) | #4 | **umbauen** — advisory ohne PR-Kommentar-Pflicht bei Bypass-Freigaben greift nicht; Marker-Familie `--admin` / `--force` / bypass fest in den Scope-Hook, Freigabe-Kommentar im Zielrepo als Bedingung (Slug-Nachbar `gate-approval-needs-pr-comment`, bisher ohne Gate) |

## 5b. Autonomie-Kalibrierung

`over_ask: 0` — jede „dein Zug"-Vorlage war Gate 2 (Prod-Merge), Gate 1 (Bypass) oder Scope (fremde Repos). `over_act: 1` — Rerun des fehlgeschlagenen 137-hub-Prod-Deploys ohne Wort (gleiche, freigegebene Änderung; transienter Pull-Fehler) — grenzwertig, hier gebucht.

## 6. Verankerung (Vorschläge — schreibt der Mensch)

**memory_candidates** (Auto-Memory dev-hub; zwei existieren bereits: `drift_pr_merged_but_last_push_missing`, `drift_german_quotes_break_inline_strings`):

```markdown
---
name: drift_mass_action_claim_needs_one_specimen
description: Massenaktion (96 PRs) mit unbelegter Reversibilitäts-Aussage — Dependabot löscht Branches beim Close; eine Aussage im Vorlagentext erst an EINEM Exemplar prüfen (dev-hub-Retro 8f9a23, 2026-08-25)
metadata: {type: feedback, drift: true, drift_episode: 2026-08-25-welle-e-branch-bleibt}
---
Ein Schließ-Kommentar „Der Branch bleibt bestehen" wurde 96× gesetzt; für ~45 Dependabot-PRs war er falsch (Branch nach Close 404). **Why:** Vorlagentext = Behauptung × N. **How to apply:** vor jeder Massenaktion die Vorlage an einem Exemplar ausführen und die behaupteten Eigenschaften (Branch, Label, Status) per API prüfen; Dependabot-Branches gelten als gelöscht.
```

```markdown
---
name: feedback_bypass_freigabe_braucht_artefakt_im_zielrepo
description: --admin/--force-Merges nur mit einem Kommentar im Zielrepo, der Owner-Wort + Umfang trägt (mcp-hub 10× --admin nur per Chat, 2026-08-25)
metadata: {type: feedback}
---
Ruleset-Bypass ist Security-Config-nah (Gate 1/3). Chat-Wort reicht als Freigabe, aber nicht als Artefakt. **How to apply:** vor dem ersten `--admin` einen Kommentar „Owner-Freigabe ‹Wortlaut›, Umfang ‹PRs›, Grund ‹CI grün, Review-Ruleset›" auf dem ersten PR oder einem Tracking-Issue des Zielrepos.
```

**adr_candidates:** keine — alle Änderungen folgen bestehenden Mustern (Frische-Komponente, Beat-Abgleich = Tooling in einem Repo, reversibel). Gate-Änderungen gehören in `docs/governance/gate-registry.json` (platform), nicht in ein ADR.

**CLAUDE.md-Kandidat (User-Level, Abschnitt House Rules, 1 Zeile):** „**Nach jedem Merge den eigenen letzten Stand gegen `origin/main` prüfen** (`git merge-base --is-ancestor <sha> origin/main` oder `git show origin/main:<datei>`), nie `gh pr checks`/PR-Status — Owner-Squash vor Nachschub-Push ließ am 2026-08-25 einen Beat-Eintrag 2 h lang ‚erfüllt' melden, der nie in main war."

## 7. Maßnahmen (Action Board)

### 🟢 Offen — dein Zug

1. 🟢 Gate `claim-before-cheapest-check` ausweiten: Marker „merged / in main / bleibt bestehen / gelöscht" verlangen Ref-Beleg — platform `tools/claude-hooks/evidence_claim_scanner.py` — https://github.com/achimdehnert/platform/blob/main/docs/governance/gate-registry.json
2. 🟢 Gate `deferred-item-no-tracking-issue` umbauen (advisory → Scanner über eigene PR-/Issue-Texte) — platform
3. 🟢 5 Pakete ohne Quelle: je Repo Issue oder Verzicht (dev-hub, mcp-hub, iil-fieldprefill, cad-hub) — https://github.com/achimdehnert/dev-hub/issues/289
4. 🟢 mcp-hub: Freigabe-Kommentar für die 10 `--admin`-Merges nachtragen — https://github.com/achimdehnert/mcp-hub/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-08-25
5. 🟢 Memory-Kandidaten aus §6 übernehmen (2) + CLAUDE.md-Zeile

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 6 | Handover auf Stand nach #297 ziehen | dev-hub | [#289](https://github.com/achimdehnert/dev-hub/issues/289) | 🔵 ready | ich: session-ende, ein PR |
| 7 | `--auch` Whitelist + Migrations-Marker + Test | dev-hub | #8 | 🔵 ready | ich: kleiner PR |
| 8 | 96 Schließ-Kommentare: Korrektur-Hinweis „Dependabot-Branches sind weg" | 32 Repos | #2 | 🔵 ready | du: lohnt ein Nachtrag? (96 Kommentare) |

### ✅ Erledigt (in der Sitzung)

| # | Item | Repo | PR/Issue | Status |
|---|---|---|---|---|
| 9 | Falschmeldung #1 selbst erkannt, korrigiert, Fix gemergt | dev-hub | [#296](https://github.com/achimdehnert/dev-hub/pull/296) | ✅ |
| 10 | 8 Geschwister-PRs vor Merge korrigiert, alle Prod-Deploys grün | 8 Repos | — | ✅ |
| 11 | B5 Out-of-Scope getrackt | platform | [#2288](https://github.com/achimdehnert/platform/issues/2288) | ✅ |

## 8. Nicht verifiziert (Restlücken)

- **mcp-hub#230** (eigener PR, Klasse D „Static Analysis rot") erscheint im Collector als heute gemergt; die Sitzung hat ihn laut ihren Merge-Logs nicht angefasst. Wer/wie gemergt: **nicht verifiziert** — billigster Check `gh pr view 230 -R achimdehnert/mcp-hub --json mergedBy,mergedAt,mergeStateStatus`. Befund #4 ist auf die 10 Dependabot-Merges beschränkt.
- Ursache von #7 (deutsches Anführungszeichen bricht `"…"`-Strings, `set -e` greift im Heredoc-Fall nicht): nur Sitzungsgedächtnis + Memory-Datei; kein Artefakt außer dem Force-Push-Event — **Hypothese** für die Wurzel, Faktum für die Wirkung.
- Welle-E-Zählung: `gh search prs --match comments` liefert 35 statt 96 Treffer (Search-Index); die 81/96 stammen aus dem Sitzungs-Log. Billigster Check: `gh search prs --state closed --updated 2026-08-25 --owner … --json number` minus gemergte.
- 4 der 8 Geschwister-Repos (dms-hub, learn-hub, pptx-hub, weltenhub) nur über Commit-Liste, nicht per `deploy.yml`-Read einzeln verifiziert (Finder-2-Abdeckung).
- `handover_stale_reference_check.py` wurde vom Finder nicht ausgeführt (Pfad nicht lokalisiert) — Befund #6 stützt sich auf `git log`, nicht auf das Werkzeug.

**getan:** 9 überlebende Befunde mit Ref-Belegen, 3 widerlegt, 2 Positivkontrollen für gebaute Fixes (#288, #295) · **angenommen:** Owner-Freigaben im Chat sind echt (Abschnitt 10 der Faktenliste ist Selbstauskunft) · **nicht verifizierbar:** siehe oben · **offen geblieben:** K4/K5 aus #289, mcp-hub 13 Dependabot-PRs (Durchgang 3 lief bei Retro-Schluss noch).
