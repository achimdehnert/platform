---
retro_schema: 1
date: 2026-07-06
repo_scope: [iil-voice-agent]
session_id: 9206ac
footprint: full
findings_total: 10
findings_survived: 9
refuted_rate: 0.10
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [handover-stale-vor-merge]
recurring_findings: [handover-stale-vor-merge]
---

## 1. Executive Summary

- 4 PRs gemergt (#40 deltaLink-Persistenz, #31 Browser-Bot-UI+Intent-Guard, #41 email.policy-Bugfix, #43 Handover-Doku), 1 neues Issue (#42, Aggregations-Limit von Top-k-RAG) — alle CI-Läufe grün, keine roten Gates, keine verwaisten Worktrees/Branches.
- **Größter Befund ist ein bekanntes, bereits Gate-pflichtiges Muster (`handover-stale-vor-merge`, jetzt ×4 über Retros — s. §5):** `AGENT_HANDOVER.md` wurde nur punktuell nachgetragen (2 Backlog-Zeilen) statt einer vollständigen neuen Session-Sektion — PR #31 (979 Zeilen, Browser-UI+Intent-Guard) und PR #41 (echter Produktionsbugfix) sind im Dokument nirgends erwähnt. Ein Gate dafür existiert bereits (`handoff-banner-gate.yml`), deckt aber weder `AGENT_HANDOVER.md` (nur `HANDOFF-*.md`) noch dieses Repo (nur `platform`/`platform-pinned`) ab — Scope-Lücke, nicht fehlende Idee.
- PR #40 wurde als einziger der vier PRs per echtem Merge-Commit (nicht Squash) und von einem anderen GitHub-Account (`wirdigital`, kein Bot) gemergt — main hat keinen Branch-Protection-Ruleset, der die dokumentierte Squash-Konvention (ADR-233) technisch erzwingt.
- Ein echter Produktionsbug wurde während eines Live-Smoke-Tests gefunden und mit falsifizierendem Regressionstest behoben (PR #41); die zugrundeliegende Behauptung „mypy hätte ihn gefangen" wurde vom Skeptiker empirisch widerlegt (REFUTED).
- Konstruktive Kleinbefunde: State-Persistenz degradiert bei Schema-Fehlern nicht sauber (crasht), zwei Guard-Features sind nur isoliert getestet, ein vorhersehbarer 6-Tage-Rebase-Konflikt hatte keinen Früh-Check.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `AGENT_HANDOVER.md` nicht aktualisiert für den Tag — Header noch `2026-07-02`, keine neue Session-Sektion, PR #31/#41 nirgends erwähnt | Prozesslücke | hoch | SURVIVES | `AGENT_HANDOVER.md:14`; Commit `c1485f1` (PR #43, nur +7/−1 Zeilen im Backlog-Block) | **handover-stale-vor-merge ×4** (f5e1d, 16fd96, 44240f, hier) — bereits Gate-pflichtig |
| 2 | PR #40 per echtem Merge-Commit (2 Parents, `58d2d04`) statt Squash gemergt, von Account `wirdigital` (Admin, kein Bot) statt `achimdehnert`; `main` ohne Branch-Protection-Ruleset | Prozesslücke | hoch | SURVIVES | `git show -s --format="%H %P" 58d2d04`; `gh pr view 40 --json mergedBy,author`; `gh api repos/iilgmbh/iil-voice-agent/branches/main/protection` → 404; `platform:ADR-233` Z.76 | 1 |
| 3 | `OneDriveRetriever._load_state()` fängt nur `(OSError, json.JSONDecodeError)` — bei schema-korrupter (aber syntaktisch validem) State-Datei crasht der Lade-Pfad unbehandelt, entgegen Docstring „kein Crash" | fehlende Validierung | mittel | SURVIVES | `src/voice_agent/adapters/onedrive_retriever.py:109-125`; reproduziert: `ValueError` bei `id_to_name` als Liste statt Dict | 1 |
| 4 | Kein Test deckt Intent-Guard (`intent_guard=True`) UND Anti-Injection-Context-Guard (`with_context_guard`/`ANSWER_ROUTE`) gemeinsam ab — beide korrekt verdrahtet, aber isoliert getestet | fehlende Validierung | niedrig-mittel | SURVIVES | `tests/test_intent_guard.py`, `tests/test_prompt_injection_guard.py` — kein Datei-Overlap; `src/voice_agent/core/agent.py:37,43,75,107-108,125,133,155` | 1 |
| 5 | `CORSMiddleware(allow_origins=["*"], ...)` in `src/voice_agent/web/app.py` (neu in PR #31) ohne Begründungs-/Scope-Kommentar | verfrühte Festlegung | niedrig | SURVIVES | `src/voice_agent/web/app.py:135-141` (Commit `ef66879`) | 1 |
| 6 | Rebase-Konflikt in `agent.py` war vorhersehbar: PR #31 lag 6 Tage (2026-06-30→07-06) unsynchronisiert, während `b4ccb83` (ADR-002/003, 2026-07-02) dieselbe Datei auf main änderte — kein automatisierter Früh-Check auf Main-Divergenz | Prozesslücke | mittel | SURVIVES | `gh pr view 31 --json createdAt,mergedAt`; `gh api repos/iilgmbh/iil-voice-agent/issues/31/events` (`head_ref_force_pushed` 14:23:34Z); `git log --since=... --until=... -- src/voice_agent/core/agent.py` → nur `b4ccb83`+`ef66879` | 1 |
| 7 | Commit-Typ `perf(web): ...` (`f422af1`) außerhalb des dokumentierten Enums `[feat\|fix\|refactor\|docs\|test\|chore]` | Prozesslücke | niedrig | SURVIVES | `git show -s --format=%s f422af1`; `~/.claude/CLAUDE.md:56`; Historie zeigt `perf` als Einzelfall (`git log --all --pretty=%s`) | 1 |
| 8 | Redundanter, gecancelter CI-Lauf durch PR #41/#43-Merges im 4-Sekunden-Abstand (kein rotes Gate, aber CI-Verschwendung) | Werkzeug | niedrig | SURVIVES | `gh run list` → Run `28803029970` (`conclusion: cancelled`, `createdAt: 15:28:10Z`); PR #41 `mergedAt:15:28:06Z`, PR #43 `mergedAt:15:28:10Z` | 1 |
| 9 | PR #41 ohne verlinkten GitHub-Issue (Fund nur inline im PR-Body dokumentiert) — Stilinkonsistenz gg. PR #40/#43, die Issues explizit referenzieren | Kommunikation | niedrig | SURVIVES | `gh pr view 41 --json body` (keine `#<Zahl>`-Referenz) vs. `gh pr view 40/43 --json body` (explizite Issue-Referenz) | 1 |
| — | „mypy hätte den `email.policy`-Bug typischerweise gefangen" | Werkzeug | mittel | REFUTED | Skeptiker reproduzierte das exakte Bug-Muster unter `mypy 1.20.2 --strict` → `Success: no issues found` (kein mypy im Repo ist zwar korrekt, aber die tragende Kausalbehauptung hält nicht) | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle 4 PR-Ziele erreicht (Persistenz, UI+Guard, Bugfix, Doku), CI grün — aber Doku-Ziel „Handover aktuell" verfehlt (#1) |
| architektur_design | 4 | Persistenz-Kopplung (deltaLink+Index) sauber motiviert, Konfliktauflösung in `agent.py` korrekt — aber Fehlerbehandlungs-/Test-Lücken (#3, #4) |
| code_konventionstreue | 3 | Zwei reale Konventionsbrüche: Merge-Methode (#2, außerhalb eigener Kontrolle) + Commit-Typ (#7) |
| risiko_debt | 3 | Neue Tech-Debt in Produktivcode: Schema-Crash-Pfad (#3) + unkommentierte CORS-Wildcard (#5); MVP-Status mildert Impact |
| prozess_effizienz | 4 | Reibungsloser Tag (kein Blocker, saubere Worktree-Reaps), aber vorhersehbarer Konflikt (#6) + redundanter CI-Lauf (#8) |
| entscheidungsqualitaet | 4 | Sauberes Scope-Abgrenzen (Issue #29 bewusst offen gelassen), Ground-Truth-Verifikation vor Behauptungen (AI-Aggregations-Test), Transparenz vor Force-Push — aber Doku-Lücke (#1) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR #43 trug nur 2 Backlog-Zeilen nach; PR #31/#41 blieben im 270-Zeilen-Handover unerwähnt (`c1485f1`, +7/−1) | Am Ende eines Arbeitstags mit mehreren gemergten PRs immer eine vollständige `### Session N`-Sektion anlegen (wie an allen Vortagen), die ALLE PRs des Tages auflistet — nicht nur die, für die zufällig ein Doku-PR geschrieben wird | #1 |
| PR #40 wurde von `wirdigital` per regulärem Merge-Commit gemergt; `main` hat keinen Branch-Protection-Ruleset, der Squash erzwingt (ADR-233 ist nur Text-Konvention) | Branch-Protection-Ruleset auf `main` aktivieren, das `squash` als einzige erlaubte Merge-Methode setzt (`allow_merge_commit=false`, `allow_rebase_merge=false`) — macht ADR-233 technisch statt nur textuell verbindlich | #2 |
| `_load_state()` fängt nur `OSError`/`JSONDecodeError`, crasht bei Schema-Fehlern trotz Docstring „kein Crash" | Schema-Validierung (`isinstance`-Checks auf `id_to_name`/`store`) in denselben try/except-Block wie das JSON-Parsing aufnehmen, damit der volle Lade-Pfad degradiert statt zu crashen | #3 |
| Intent-Guard und Context-Guard sind je isoliert getestet (`test_intent_guard.py` vs. `test_prompt_injection_guard.py`), kein gemeinsamer Test | Einen Integrationstest ergänzen, der `intent_guard=True` UND einen kontext-tragenden `agent.ask()`-Aufruf (der `ANSWER_ROUTE`/`with_context_guard` triggert) in derselben Sequenz prüft | #4 |
| CORS-Wildcard in `app.py` ohne Kommentar, obwohl andere Design-Entscheidungen im Repo konsequent kommentiert sind | Einen Ein-Zeiler-Kommentar über der `CORSMiddleware`-Config ergänzen: „lokaler MVP-Demo-Server — vor Prod-Einsatz auf konkrete Origins einschränken" | #5 |
| PR-#31-Branch lag 6 Tage unsynchronisiert, während main dieselbe Kern-Datei änderte — kein Früh-Check meldete die Divergenz | Im `/session-start`/`repo-session.sh`-Ritual einen Check ergänzen: bei offenen PRs älter als N Tage prüfen, ob main seit Branch-Erstellung in denselben Dateien divergiert ist, und als Warnung melden | #6 |
| Commit `f422af1` nutzt Typ `perf`, außerhalb des dokumentierten Enums, unbemerkt weil keine Automatisierung prüft | Einen Commit-Msg-Lint-Hook (Regex gegen das CLAUDE.md-Enum) einführen, der Typ-Abweichungen vor dem Commit abfängt | #7 |
| Zwei Merges (PR #41/#43) im 4-Sekunden-Abstand lösten einen redundanten, gecancelten CI-Lauf aus | Bei mehreren fertigen PRs eine kurze Sequenzierungspause einhalten (oder eine GitHub-Merge-Queue nutzen) statt Merges in Sekundenabstand abzusetzen | #8 |
| PR #41 referenziert keinen Issue, dokumentiert den Fund nur inline — anders als PR #29/#40/#42/#43 | Für jeden während der Arbeit entdeckten Bug (auch spontane Live-Smoke-Funde) konsequent zuerst ein Issue anlegen und im PR-Body verlinken, statt inline-only | #9 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Vorlauf, vor Commit dieses Reports) zeigt **`handover-stale-vor-merge` bereits ×3** (`f5e1d`, `16fd96`, `44240f`) — **bereits Gate-pflichtig laut Skill-Regel** (≥2). Befund #1 dieser Retro ist **derselbe Muster-Slug**, nicht ein neuer: mit diesem Report wird er zu **×4**. Das ist der eigentliche Hebel dieser Retro — nicht „noch ein Memo" schreiben, sondern den bestehenden Gate-Mechanismus prüfen.

**Bestehender Gate-Mechanismus (`handoff-banner-gate.yml` + `scripts/checks/handoff_banner_check.py`, aus Retro `f5e1d`) deckt diesen Fall NICHT ab:**
- Der Workflow triggert nur auf Pfade `docs/audits/HANDOFF-*.md` / `docs/**/HANDOFF-*.md` — `AGENT_HANDOVER.md` (Root-Level, anderer Dateiname) matcht dieses Glob nicht.
- Der Workflow ist nur in `platform`/`platform-pinned` verdrahtet (`grep -rl handoff_banner_check ~/github/*/.github/workflows/*.yml` → nur diese 2 Repos), nicht in `iil-voice-agent`.
- Der Check selbst prüft ein anderes Symptom (fehlendes „Live-Status"-Banner in den ersten 30 Zeilen) als der heutige Fall (Inhalt vollständig fehlt, kein Banner-Problem) — verwandtes, aber nicht identisches Failure-Pattern derselben Familie „Handover driftet von realem Repo-Zustand weg".

**Konsequenz:** Kein neues Gate von Grund auf nötig — aber der bestehende Mechanismus muss (a) auf `AGENT_HANDOVER.md`-artige Root-Handover-Dateien erweitert und (b) fleet-weit (nicht nur `platform`-Familie) verdrahtet werden, um diese Wiederholung zu verhindern. Das ist jetzt ein Gate-PR-Pflicht-Item, nicht mehr Backlog.

Gegen `<auto-memory>/MEMORY.md` (iil-voice-agent) abgeglichen: kein bestehendes Drift-Memory zu Branch-Protection/State-Persistenz-Schema/Rebase-Früh-Check (Befunde #2/#3/#6) — diese drei sind neue, repo-lokale Muster, keine Wiederholung.

## 5b. Autonomie-Kalibrierung

- **over_ask:** keiner identifiziert — jede Rückfrage in dieser Session (Force-Push auf fremden PR-Branch vor dem Überschreiben, Merge-Bestätigung) betraf einen tatsächlich schwer-reversiblen/fremden Artefakt-Zustand (History-Rewrite eines PRs aus einer Vorsession bzw. Merge nach main), kein deterministischer/reversibler Schritt wurde unnötig eskaliert.
- **over_act:** keiner identifiziert — kein Prod/Publish/Merge-auto-deploy/3.-Repo-Schritt wurde ohne Rückfrage ausgeführt; der einzige potenziell heikle Schritt (Force-Push) wurde vorab bestätigt.

## 6. Verankerung — kopierfertige Vorschläge

**gate_pr_candidate** (NICHT ein weiteres Memo — `handover-stale-vor-merge` ist bereits ×4, s. §5):

```yaml
- title: "Gate handover-stale-vor-merge auf AGENT_HANDOVER.md + fleet-weit erweitern"
  repo: platform
  files:
    - .github/workflows/handoff-banner-gate.yml   # paths um 'AGENT_HANDOVER.md' / repo-root-Handover-Namen erweitern
    - scripts/checks/handoff_banner_check.py       # Datei-Discovery-Glob erweitern
  body: |
    handoff-banner-gate.yml triggert nur auf docs/**/HANDOFF-*.md und ist nur in
    platform/platform-pinned verdrahtet. iil-voice-agent (und vermutlich weitere
    Repos) nutzen die abweichende Konvention AGENT_HANDOVER.md im Repo-Root — das
    Gate greift dort nie. Slug handover-stale-vor-merge ist damit 4× aufgetreten
    (f5e1d, 16fd96, 44240f, session-retro-2026-07-06-iil-voice-agent-9206ac),
    ohne dass der bestehende Gate-Mechanismus greifen konnte.
  label: model:sonnet-5
```

**memory_candidates** (Typ `project`, Repo iil-voice-agent — die anderen drei sind KEINE Wiederholungen, echte neue Muster):

```yaml
- name: main-branch-protection-vs-adr233-squash-convention
  description: ADR-233s Squash-Konvention ist nur Text — main hat keinen Branch-Protection-Ruleset, der sie technisch erzwingt.
  type: project
  body: |
    iil-voice-agent main hat keinen Branch-Protection-Ruleset (`gh api
    repos/iilgmbh/iil-voice-agent/branches/main/protection` → 404). PR #40 wurde
    dadurch per regulärem Merge-Commit statt Squash gemergt (abweichend von den
    anderen 3 PRs des Tages).
    Why: Textuelle Konventionen (ADR-233) werden ohne technische Durchsetzung
    irgendwann durchbrochen — hier folgenlos, aber im Prinzip ein Drift-Risiko.
    How to apply: Vor dem nächsten größeren Merge-Batch prüfen, ob ein
    Branch-Protection-Ruleset mit erzwungenem Squash-only sinnvoll ist — Beleg:
    session-retro-2026-07-06-iil-voice-agent-9206ac.md #2.
```

**adr_candidates:** keiner — kein Befund erreicht die ADR-Schwelle (kein neuer externer Dependency/Service-Boundary, keine Architektur-Umkehr, kein Cross-Repo-Impact; alle Befunde sind repo-lokale Prozess-/Code-Qualitäts-Punkte, siehe `policies/adr-threshold.md`).

## 7. Maßnahmen (Action Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1a | AGENT_HANDOVER.md um Session-6-Sektion (PR #31/#40/#41/#43) vervollständigen | iil-voice-agent | — | 🟢 offen | du: bestätigen, dann ich: PR |
| 1b | **Gate-PR-Pflicht:** `handoff-banner-gate.yml` auf `AGENT_HANDOVER.md`-Konvention + fleet-weit erweitern (Slug ×4) | platform | — | 🟢 offen | du: Scope-Entscheidung (welche Repos), dann ich: PR |
| 2 | Branch-Protection auf main (Squash-only) einrichten | iil-voice-agent | — | 🟢 offen | du: Entscheidung (Repo-Setting) |
| 3 | `_load_state()` Schema-Validierung ergänzen | iil-voice-agent | — | 🔵 ready | ich: PR mit Test |
| 4 | Integrationstest Intent-Guard + Context-Guard gemeinsam | iil-voice-agent | — | 🔵 ready | ich: PR |
| 5 | CORS-Kommentar in `app.py` ergänzen | iil-voice-agent | — | 🔵 ready | ich: PR (trivial) |
| 6 | Main-Divergenz-Früh-Check in `/session-start` ergänzen | iil-voice-agent / platform | — | 🔵 ready | ich: Vorschlag ausarbeiten |
| 7 | Commit-Typ-Lint-Hook | platform (fleet-weit relevant) | — | 🟢 offen | du: Scope-Entscheidung (repo-lokal vs. fleet) |
| 8 | Merge-Sequenzierung/Merge-Queue erwägen | iil-voice-agent | — | 🟢 offen | du: Aufwand vs. Nutzen abwägen (niedrige Prio) |
| 9 | Konvention „immer Issue vor PR bei Live-Funden" verankern | iil-voice-agent | — | 🔵 ready | ich: als Zeile in CLAUDE.md/Arbeitsregeln |

## 8. Nicht verifiziert (Restlücken)

- Ob `wirdigital` derselbe physische Mensch wie `achimdehnert` ist (zwei GitHub-Accounts derselben Person, z. B. Firma vs. privat), ist über die GitHub-API nicht entscheidbar — billigster Check: den User direkt fragen.
- Ob ein Branch-Protection-Ruleset mit Squash-only andere, heute nicht sichtbare Workflows (z. B. Dependabot-Auto-Merges) brechen würde, wurde nicht geprüft — billigster Check: Ruleset im Dry-Run/auf einem Test-Repo simulieren, bevor er auf `iil-voice-agent`/fleet-weit ausgerollt wird.
- Der Commit-Typ-Lint-Hook (#7 im Action Board) — ob das repo-lokal oder fleet-weit über `platform` gelöst werden soll, wurde nicht entschieden (Scope-Frage an den User delegiert).
