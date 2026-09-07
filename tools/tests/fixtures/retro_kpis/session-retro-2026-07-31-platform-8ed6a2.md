---
retro_schema: 1
date: 2026-07-31
repo_scope: [platform, dev-hub]
session_id: 8ed6a2
footprint: deep
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [check-built-without-wiring-step, closure-claim-without-artifact-update, sibling-known-bugclass-not-consulted]
recurring_findings: [always-instruction-without-enforcement, untested-tool-module-green-gate, claim-before-cheapest-check, deferred-item-no-tracking-issue, tracking-doc-stale-after-new-occurrence, platform-pinned-perma-dirty-loop, parallel-session-pr-collision, scope-checkpoint-not-durably-recorded]
---

# Session-Retro 2026-07-31 — platform / dev-hub (`8ed6a2`)

## 1. Executive Summary

- **Ein Bug ist auf `main` gelandet.** `policy_zone_freshness.sh` meldet bei
  Fetch-Fehlschlag `exit 0` / GRÜN, obwohl es nur gegen einen möglicherweise stalen
  lokalen `HEAD` prüft. Zwei unabhängige Fixtures reproduzieren es. Keiner der 8
  Mutationstests erreicht diesen Zweig.
- **Der Tag bestand fachlich aus Selbstkorrekturen** — vier davon habe ich selbst
  gefunden, drei fanden die Reviewer, drei fanden die Finder dieser Retro. Das Verfahren
  funktioniert; die Fehlerklasse ist jedes Mal dieselbe.
- **Acht von elf überlebenden Befunden tragen Slugs, die laut `retro_kpis.py` bereits
  bei ≥2 stehen und damit längst gate-pflichtig sind.** Die Diagnose ist deshalb nicht
  „neue Fehler", sondern „notierte Gate-Pflichten werden nicht durchgesetzt".
- **Ein neu gebautes Werkzeug hat keinen Aufrufer** — elf Minuten nachdem ich genau das
  im selben ADR als „Vorfall 1 in Reinform" beschrieben hatte.
- **Drei Befunde wurden widerlegt**, darunter zwei meiner eigenen Zwischenaussagen an den
  Betreiber. Beide hatte ich zu scharf formuliert.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `policy_zone_freshness.sh` meldet bei Fetch-Fehler GRÜN/`exit 0` gegen stalen lokalen `HEAD`; keine zweite Quelle | fehlende Validierung | kritisch | SURVIVES | Fake-Origin-Fixture mit echtem Divergenz-Commit, `exit 0` trotz Abweichung in `llm-routing.md` | `untested-tool-module-green-gate` ×≥2 |
| 2 | Der Fetch-Fehler-Zweig hat 0 von 8 Tests — `_run()` setzt `POLICY_ZONE_REF` unconditional | fehlende Validierung | kritisch | SURVIVES | `tools/tests/test_policy_zone_freshness.py` `_run()`; Skript-Zweig `if [[ -n "${POLICY_ZONE_REF:-}" ]]` | `untested-tool-module-green-gate` ×≥2 |
| 3 | Neuer Check hat nirgends einen Aufrufer; PR-Body behauptet dennoch „Schließt ADR-291 offener Punkt 6", ADR bleibt unangetastet | Werkzeug | hoch | SURVIVES | `git grep policy_zone_freshness origin/main` → nur Selbstreferenzen; auch `~/.claude/`, dev-hub, `crontab -l`, `/etc/systemd` → 0; ADR-291:299 unverändert | `always-instruction-without-enforcement` ×≥2 |
| 4 | `klickdummy_policy_sync.sh` existiert seit 2026-05-19 und wird in **keiner** ADR-291-Fassung erwähnt — auch nicht unter „C6", „C-6", „policy_sync", „ADR-211" | Wissenslücke | hoch | SURVIVES | `git log --diff-filter=A` → 2026-05-19 (`88bd846b`); 0 Treffer in `9e37cab0`, `98ad9cd8`, `c7bc48af` | `claim-before-cheapest-check` ×≥2 |
| 5 | Body von PR #1595 behauptet „Review zu ADR-291 steht aus", während derselbe PR zwei Commits enthält, die beide Reviews vollständig einarbeiten | Kommunikation | hoch | SURVIVES | Body erstellt 09:54:26Z; Commits `98ad9cd8` 10:20:18Z, `c7bc48af` 10:40:19Z; Merge 11:31:42Z; Diff ADR-291 +254/−77 | `tracking-doc-stale-after-new-occurrence` ×≥2 |
| 6 | dev-hub#188 (`severity:critical`) fehlt vollständig in `AGENT_HANDOVER.md`; #187 nur im Blockquote unter „Vorheriger Stand", nicht in der nummerierten Prioritätenliste | Prozesslücke | hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` — „188" trifft nur `mcp-hub#188`; Liste Z. 215–222 ohne beide | `deferred-item-no-tracking-issue` ×≥2 |
| 7 | Offener Punkt 6 („Wer entscheidet: Owner") wird 11 Min. später selbst implementiert und gemergt; `status`/`implementation_status` bleiben unverändert | Prozesslücke | hoch | SURVIVES | `25409fee` 13:12:14Z → `cf046b86` 13:23:19Z; `cf046b86` fasst das ADR nicht an; ADR-291:299 unverändert | `scope-checkpoint-not-durably-recorded` ×≥2 |
| 8 | Komplexitäts-Bilanz in ADR-291 verbucht im Präsens einen Effekt von B1, das laut eigener Reihenfolge-Tabelle nicht erreichbar ist (Schritt 1 „ADR-290 accepted" nicht erfüllt); das tatsächlich gebaute Artefakt (264 Z.) fehlt in der Bilanz | Überclaim | mittel | SURVIVES | ADR-290 `status: proposed`; `git show cf046b86 --shortstat` → 264 Zeilen | — |
| 9 | Policy-Pin ohne Frische-Garantie zur Nutzungszeit: Pin von fremder Session gesetzt, danach 17 Commits Rückstand, darunter PR #1601 mit genau den zwei betroffenen Policies | Werkzeug | mittel | SURVIVES | `git rev-list --count 6d9c692b..0d078b29` → 17; #1601 ändert `llm-routing.md`, `session-routing.md`; Refresh-Hook nur bei SessionStart | `platform-pinned-perma-dirty-loop` ×≥2 · `parallel-session-pr-collision` ×≥2 |
| 10 | PR #1593 vermeidbarer Dangling-PR — Einzeiler-Fix, 36 Min. später von #1595 vollständig mit abgedeckt | Prozesslücke | mittel | SURVIVES | #1593 created 09:18:47Z / closed 09:54:39Z, nie gemergt; #1595 created 09:54:26Z, Commit-Body nennt den Fix | — |
| 11 | Alle 6 gemergten Scope-PRs: ein Reviewer, Review-Body leer, 0 Inline-Kommentare; die einzigen inhaltlichen Thread-Kommentare stammen von `github-actions[bot]` | Prozesslücke | niedrig | SURVIVES | `gh pr view --json reviews` ×6 (bodylen 0); `gh api …/pulls/<n>/comments` → 0; Issue-Kommentare 2–6, alle Bot | bekannt via `feedback_platform_pr_needs_second_owner_review` |
| 12 | „Faktenfehler zu `policies/` überlebte zwei externe Reviews" | fehlende Validierung | — | **REFUTED** | Der Satz stand nicht in Fassung 1 (`9e37cab0`: 0 Treffer) und nicht in `98ad9cd8`; er entstand erst in `c7bc48af` **als Antwort auf REC-4 der zweiten Runde** und wurde im Folgecommit `8e06a057` selbst korrigiert — kein Reviewer sah ihn je | — |
| 13 | „ADR-290/291 auf `proposed` = Entscheidungsvorlage statt Umsetzung, Auftrag verfehlt" | verfrühte Festlegung | — | **REFUTED** | `proposed` + `implementation_status: none` ist im Plattform-Lifecycle (proposed → accepted → implementiert) der **korrekte** Endzustand einer abgeschlossenen ADR-Revision; verwechselt Freigabestatus mit Aufgaben-Erledigung; Lifecycle belegt in Memory `feedback_accepted_adr_amendment_needs_execution_pr` (Existenz geprüft) | — |
| 14 | „`set -uo pipefail` ohne `-e` erzeugt einen unbehandelten Fehlerpfad" | Stil | — | **REFUTED** | Zwei Fixtures (unborn-HEAD-Repo, Normalaufruf) unter `bash -e` gegengetestet: identisches Verhalten, identischer Exit-Code. Der reale `git fatal:`-Leak auf stderr hat eine andere Ursache (fehlendes `2>/dev/null`) | — |

**Defekter Root-Cause-Anker, vor Phase 3 entfernt (zählt NICHT als `pre_refuted`):** Der 5-Why des Scope-Finders zu Befund 3
stützte sich auf das Memory `feedback_doc_capability_claims_need_tool_grep`. Existenz-Check:
Datei nicht vorhanden, nicht im Index verlinkt (156 Index-Links geprüft, 0 tot). Als
Phantom-Referenz entfernt, bevor sie in die Falsifikation ging.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Alle acht Aufträge lieferten Artefakte, aber eine Lieferung enthält einen Bug (#1/#2) und eine ist ohne Aufrufer wirkungslos (#3) |
| architektur_design | **3** | Die A/B-Trennung in ADR-291 Fassung 2 ist tragfähig und extern bestätigt; zugleich reproduziert der neue Check eine Fehlerklasse, die das Schwesterskript bereits gelöst hatte (#1), und die Bestandsaufnahme fehlte ganz (#4) |
| code_konventionstreue | **3** | Commit-Format, Append-only-Handover, keine Backticks in `-m`, alle Gates grün — aber die am selben Tag eingeführte Berichtspflicht wurde im ersten Einsatz durch den eigenen PR-Body verletzt (#5) |
| risiko_debt | **2** | Ein falsch-grüner Check auf `main`, sein kritischer Pfad ungetestet, ohne Aufrufer (#1–#3); zwei P1-Issues erzeugt, aber im Kontinuitätsdokument unsichtbar (#6) |
| prozess_effizienz | **3** | Hoher Durchsatz und funktionierende Selbstkorrektur, aber ein Dangling-PR (#10), vier Korrektur-Commits nach Fassung 2 und dreimal dieselbe Fehlerklasse |
| entscheidungsqualitaet | **3** | Gut: C6 **nicht** in CI verdrahtet, weil vorher geprüft; Halt bei `proposed`; Append-only statt Umschreiben. Schlecht: Abschluss-Claim ohne Artefakt-Deckung (#3), Owner-Punkt selbst umgesetzt (#7) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Check fällt bei Fetch-Fehler auf lokalen `HEAD` zurück und meldet `exit 0` | Fetch-Fehlschlag ist **kein grüner Zustand**: eigener Rückgabewert (z. B. `3` „Bezug nicht erhebbar"), nie `0`. Kein Konsument darf „konnte nicht prüfen" von „geprüft, in Ordnung" unterscheiden müssen | #1 |
| 8 Mutationstests, alle mit gesetztem `POLICY_ZONE_REF` — Fetch-Zweig nie durchlaufen | Jede Testbarkeits-Naht, die einen Codepfad **überspringt**, braucht mindestens einen Test, der sie **nicht** setzt. Regel: „Naht eingebaut ⇒ Test ohne Naht" | #2 |
| Werkzeug gebaut, PR-Body sagt „schließt Punkt 6", ADR unangetastet, kein Aufrufer | Ein Abschluss-Claim verlangt vor dem Merge einen Grep-Beweis für die Verdrahtung **und** die Statusänderung im referenzierten Artefakt. Ohne beides heißt der PR „liefert Baustein für Punkt 6" | #3 |
| ADR über einen fehlenden Mechanismus geschrieben, ohne nach dem Mechanismus zu suchen | Vor dem Entwurf eines neuen Gates: **Bestandsaufnahme** — `git log --diff-filter=A -- scripts/checks/`, `ls scripts/checks/`, Grep nach Zweck-Synonymen. Ergebnis in den Context-Abschnitt, auch wenn es leer ist | #4 |
| PR-Body beim Erstellen geschrieben, danach zwei substanzielle Commits, Body nicht nachgezogen | Vor dem Merge: Body gegen die finale Commit-Liste abgleichen. Der Vier-Punkte-Schluss ist erst gültig, wenn er den **letzten** Commit kennt | #5 |
| Zwei P1-Issues angelegt, keines in der Prioritätenliste des Handovers | Ein Tracking-Artefakt zählt erst, wenn es **dort** steht, wo die nächste Sitzung liest. Issue anlegen **und** Handover-Prioliste ergänzen — im selben Zug | #6 |
| Offener Punkt „Wer entscheidet: Owner" 11 Min. später selbst umgesetzt | Ein als Owner-Entscheidung markierter Punkt wird vor der Umsetzung **im Artefakt** abgehakt (Zeile ändern, Verweis auf die Freigabe). Chat-Zustimmung ohne Artefakt-Spur reicht für einen Punkt nicht, den man selbst als Gate geschrieben hat | #7 |
| Bilanz verbucht Wirkung von B1 im Präsens, ohne das real Gebaute zu nennen | Die Komplexitäts-Bilanz zählt **nur**, was im selben Merge liegt; Zukünftiges im Futur und namentlich als „noch nicht gebaut" | #8 |
| Pin von fremder Session gesetzt, 17 Commits Rückstand unbemerkt bis zum Zufallsfund | Frische des Pins **zur Nutzungszeit** prüfen, nicht nur beim SessionStart — vor jedem Zitat aus einer Policy | #9 |
| Einzeiler-Fix als eigener PR, während dasselbe Artefakt in einem größeren Zyklus steckt | Klein-Fix an einem Artefakt, das gerade überarbeitet wird, wandert in die laufende Überarbeitung statt in einen eigenen PR | #10 |
| Sechs Freigaben ohne Text, inhaltliche Prüfung nur durch Bots | Für Governance-PRs (ADR/Policy/Skill) mindestens ein benannter inhaltlicher Prüfpunkt im Review-Body — oder ausdrücklich vermerken, dass die Prüfung extern lief | #11 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über alle Retros in `docs/retros/`:

- **18 Slugs stehen bei ≥2 und sind damit gate-pflichtig.** Acht davon treten in dieser
  Session erneut auf: `always-instruction-without-enforcement`,
  `untested-tool-module-green-gate`, `claim-before-cheapest-check`,
  `deferred-item-no-tracking-issue`, `tracking-doc-stale-after-new-occurrence`,
  `platform-pinned-perma-dirty-loop`, `parallel-session-pr-collision`,
  `scope-checkpoint-not-durably-recorded` (×9 — der höchste Zähler im ganzen Register).
- **`risiko_debt` ist über 60 Messungen mit Ø 2,55 die schwächste Dimension** (alle
  anderen 3,03–3,83). Der heutige Wert 2 liegt darunter und passt ins Muster:
  Werkzeug gebaut aber nicht verdrahtet, Issues erzeugt aber nicht im Handover.
- **`refuted_rate` 0,21** = 3/14, im gesunden Band (Trend der Vorgänger: 0,05–0,56).
  `pre_refuted: 0` — die entfernte Phantom-Referenz war kein eigener Befund, sondern ein
  defekter Root-Cause-Anker **innerhalb** von Befund #3; sie zählt daher nicht als
  vor-widerlegter Befund (Korrektur nach Meta-Review).

**Der eigentliche Längsschnitt-Befund:** Von elf überlebenden Befunden sind acht
Wiederholungen bereits gate-pflichtiger Muster. Nicht ein einziger davon wurde durch ein
bestehendes Gate gefangen — alle wurden durch Menschen, externe Reviews oder diese Retro
gefunden. Die Gate-Pflicht existiert als Notiz, nicht als Mechanismus.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 1 | Der Pinned-Refresh wurde dem Betreiber vorgelegt, obwohl er deterministisch und über `git checkout --detach <alt>` reversibel ist. Vorlegen war vertretbar (Wirkung auf fremde Sessions), aber die Gate-Liste nennt diesen Fall nicht |
| `over_act` | 1 | Befund #7: ein selbst als „Wer entscheidet: Owner" markierter Punkt wurde 11 Minuten später selbst umgesetzt und gemergt. Chat-Zustimmung lag vor, Artefakt-Spur nicht |

Kein Muster ≥2 in dieser Session; keine Charter-Schärfung abgeleitet. Beide Werte sind zu
beobachten, nicht zu verankern.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: feedback_fetch_failure_is_not_a_green_state
description: Ein Check, der seinen Bezugspunkt nicht erheben kann, darf nie exit 0 melden
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-policy-zone-false-green
---
Kann ein Prüfwerkzeug seine **Referenz nicht erheben** (Fetch schlägt fehl, Remote
unerreichbar, Manifest fehlt), ist das ein **eigener Rückgabewert** — nie `0`. Ein
Fallback auf einen lokalen Stand ist ein Fallback auf eine *möglicherweise stale* Quelle;
für jeden automatisierten Konsumenten ist `exit 0` von echtem Grün nicht unterscheidbar,
egal wie ehrlich der Text daneben ist.

**Warum:** Am 2026-07-31 in `policy_zone_freshness.sh` gebaut und am selben Tag gemergt.
Zwei unabhängige Fixtures zeigten `exit 0` bei doppelt stalem Zustand. Dieselbe
Fehlerklasse war im Schwesterskript `klickdummy_policy_sync.sh` bereits gelöst
(Doppel-Stale-Blind-Spot) — die Lösung stand im Kommentarblock, der als Vorlage diente.

**How to apply:** Vor dem Bau eines Checks die **Rückgabewert-Tabelle** schreiben, mit
einer eigenen Zeile für „Bezug nicht erhebbar". Danach prüfen, ob ein Testfall diesen Wert
erzwingt. Verwandt: [[feedback_run_conclusion_not_tool_health]].
```

```markdown
---
name: feedback_testability_seam_needs_a_test_without_it
description: Eine Naht, die einen Codepfad überspringt, braucht einen Test, der sie nicht setzt
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-policy-zone-false-green
---
Wird für die Testbarkeit eine **Naht** eingebaut (Env-Override, Injection-Punkt, Flag),
überspringt sie einen echten Codepfad. Mindestens ein Test muss die Naht **weglassen** —
sonst ist ausgerechnet der umgangene Pfad der einzige ungetestete.

**Warum:** `POLICY_ZONE_REF` wurde als Testbarkeits-Naht eingeführt und in allen 8
Mutationstests unconditional gesetzt. Der dadurch übersprungene Fetch-Zweig enthielt den
einzigen kritischen Bug. 8 grüne Tests, 0 Abdeckung genau dort.

**How to apply:** Beim Einbau einer Naht sofort den Gegentest anlegen. Verwandt:
[[feedback_fetch_failure_is_not_a_green_state]], [[feedback_dry_run_does_not_cover_write_path]].
```

```markdown
---
name: feedback_new_gate_needs_bestandsaufnahme_first
description: Vor dem Entwurf eines neuen Prüfmechanismus erst suchen, ob es ihn schon gibt
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-c6-uebersehen
---
Bevor ein ADR oder ein Konzept einen **fehlenden** Prüfmechanismus postuliert: im Repo
nach dem Mechanismus suchen. `ls scripts/checks/`, `git log --diff-filter=A`, Grep nach
Zweck-Synonymen. Das Ergebnis gehört in den Context-Abschnitt — auch wenn es leer ist.

**Warum:** ADR-291 beschrieb in beiden Fassungen eine fehlende Zonen-Prüfung.
`scripts/checks/klickdummy_policy_sync.sh` existierte seit 73 Tagen und prüft genau diesen
Pfad — in keiner Fassung erwähnt, unter keinem Synonym. Entdeckt erst durch Zufall beim
Abarbeiten eines anderen Punktes.

**How to apply:** Bestandsaufnahme als erster Schritt jedes Gate-Entwurfs, nicht als
Gegenprobe danach. Verwandt: [[feedback_absence_claim_needs_full_family_grep]].
```

```markdown
---
name: feedback_tracking_artifact_must_reach_the_read_surface
description: Ein Issue zählt erst als getrackt, wenn es dort steht, wo die nächste Sitzung liest
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-31-handover-ohne-p1-issues
---
Ein GitHub-Issue ist ein Tracking-Artefakt, aber **kein Kontinuitäts-Artefakt**. Es zählt
erst, wenn es an der Stelle steht, die eine frische Sitzung tatsächlich liest — bei uns die
nummerierte Prioritätenliste in `AGENT_HANDOVER.md`. Ein Blockquote im Fließtext genügt
nicht.

**Warum:** dev-hub#188 (`severity:critical`) kam in 480 Zeilen `AGENT_HANDOVER.md` gar
nicht vor; #187 nur in einem Korrektur-Absatz. Beide entstanden am selben Tag aus einer
Prod-Diagnose.

**How to apply:** Issue anlegen **und** Handover-Prioliste ergänzen, im selben Zug.
Verwandt: [[feedback_unfinished_work_state_must_persist]].
```

### adr_candidates

Keine. Die Session hat bereits zwei ADRs erzeugt; alle Befunde sind Prozess- oder
Werkzeugkorrekturen unterhalb der ADR-Schwelle (`policies/adr-threshold.md`: „reine
Ergänzung nach bestehendem Muster → CHANGELOG + PR").

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

1. 🔵 Fetch-Fehler bekommt eigenen Rückgabewert, nie `0` — https://github.com/achimdehnert/platform/blob/main/scripts/checks/policy_zone_freshness.sh
2. 🔵 Testfall ohne gesetzte `POLICY_ZONE_REF`-Naht — https://github.com/achimdehnert/platform/blob/main/tools/tests/test_policy_zone_freshness.py
3. 🔵 Abschluss-Claim „schließt Punkt 6" richtigstellen — https://github.com/achimdehnert/platform/pull/1607
4. 🔵 dev-hub#187 und #188 in die Handover-Prioliste — https://github.com/achimdehnert/platform/blob/main/AGENT_HANDOVER.md
5. 🔵 Komplexitäts-Bilanz: Präsens → Futur, gebautes Artefakt nennen — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-291-freigabekern-gate.md

### 🟢 Offen — dein Zug

6. 🟢 Vier Memory-Kandidaten verankern (Abschnitt 6) — https://github.com/achimdehnert/platform/blob/main/docs/retros/session-retro-2026-07-31-platform-8ed6a2.md
7. 🟢 Offenen Punkt 6 im ADR abhaken oder Umsetzung zurücknehmen — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-291-freigabekern-gate.md
8. 🟢 Pin-Frische zur Nutzungszeit entscheiden — https://github.com/achimdehnert/dev-hub/issues/187

Die Voll-URLs erzwingen hier die Listenform statt einer Tabelle: Bei 80 Spalten sprengt
eine GitHub-URL jede Zeile mit weiteren Spalten (CLAUDE.md, Action-Board Regel 4).

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| Ob `wirdigital` außerhalb von GitHub inhaltlich geprüft hat — Abwesenheit von Beleg ist kein Ausschluss | Rückfrage beim Owner |
| Ob es auf **anderen** Hosts einen Aufrufer für `policy_zone_freshness.sh` gibt — nur diese Maschine geprüft | `ssh <host> 'crontab -l; ls ~/.claude/hooks'` |
| Warum `feedback_doc_capability_claims_need_tool_grep` zwischen Sessionstart und jetzt aus dem Index verschwand | `git log` über das Memory-Verzeichnis, falls versioniert |
| Ob eine zweite, unabhängige Schranke im Gesamtsystem den Falsch-Grün-Fall praktisch auffängt | Vollständige Durchsicht der SessionStart-Kette |
| Ob weitere Tasks aus jüngeren dev-hub-Merges auf Prod fehlen — nur `mail_agent` geprüft | `celery -A config inspect registered` gegen die Task-Liste im Repo |
| Zuordnung „Umsetzungen 1-3 und 4 5" zu einzelnen PRs — ohne Sitzungsprotokoll nicht artefakt-prüfbar | entfällt (Betreiber-Wissen) |
