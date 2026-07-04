---
retro_schema: 1
date: 2026-07-04
repo_scope: [platform, aifw, authoringfw, gaeb-toolkit, iil-adrfw, iil-codeguard, iil-django-commons, iil-enrichment, iil-fieldprefill, iil-ingest, iil-klickdummy, iil-reflex, illustration-fw, learnfw, nl2cad, outlinefw, promptfw, researchfw, riskfw, weltenfw]
session_id: e17299
footprint: deep
findings_total: 12
findings_survived: 8
refuted_rate: 0.33
phase3_refuted: 4
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [stale-local-clone-as-ground-truth, scope-checkpoint-not-durably-recorded]
recurring_findings: [stale-local-clone-as-ground-truth, scope-checkpoint-not-durably-recorded, claim-before-cheapest-check]
---

# Session-Retro 2026-07-04 — Dirty-Repo-Ursache (ADR-265) + PyPI-Fleet-Programm (ADR-266)

Session-Umfang: 8 User-Aufträge; platform #907/#908/#910/#912/#915 gemergt; ADR-265-Rollout
als Direct-Commits auf ~21 mains; 19 Dependabot- + 20 CI-Konvergenz-PRs (18/19 konvergiert,
nl2cad by-design ausgenommen); iil-adrfw-Protection umgestellt. Methode: 1 Collector (haiku),
3 Finder + 3 Skeptiker + 1 Meta (sonnet), Falsifikation binär.

## 1. Executive Summary

- Alle 8 Aufträge artefakt-belegt geliefert; kein Prod-Schaden, kein Publish, alle
  Fleet-mains grün (Stichproben-verifiziert).
- Härtester Survivor: die CI-Konvergenz ließ bei iil-adrfw und outlinefw **blockierendes
  mypy (und bandit) still entfallen** — kein PR-Body, kein ADR nennt den Trade-off (F6).
- Das als „Aufsetzpunkt für Folge-Sessions" deklarierte ADR-266 ist nach dem eigenen
  Rollout **selbstwidersprüchlich stale** (Statuskorrektur sagt „Stufe 3 umgesetzt",
  Bullets sagen „⬜ gegated"; nl2cad-Ausnahme fehlt) (F1).
- Wiederholungsmuster bestätigt: **stale lokale Klone als Ground Truth** schlug in EINER
  Session zweimal zu (ADR-265-Beweistabelle F2; Inventar-Tool v1 F9) — Instanzen der
  ≥2-Familie `claim-before-cheapest-check` → Gate-Pflicht, nicht N-tes Memo.
- Falsifikation wirkte: 4/12 Befunden REFUTED (u. a. „vermeidbare Doppelwelle" — war
  dokumentierte Strategie; „Ground-Truth-Label irreführend" — Lifecycle sauber deklariert);
  ein Finder beging selbst den Org-Blindfleck, den er anklagte (404-Claim).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| F1 | ADR-266 („Aufsetzpunkt für Folge-Sessions") nach 2b/3-Rollout stale + selbstwidersprüchlich (Korrektur-Block vs. Stufen-Bullets im selben Commit; „Freigabe einholen" trotz erteilter Freigabe; nl2cad-Ausnahme undokumentiert) | Prozesslücke | hoch | SURVIVES | ADR-266@main letzter Commit 857362c 09:20Z; 30 Programm-PRs gemergt 12:22–13:10Z; nl2cad#36 CLOSED mit Begründung | handover-stale-vor-merge ×1 (44240f) |
| F2 | ADR-265-Beweistabelle stale: billing-hub als „54 getrackte Dateien" geführt, real seit 2026-06-01 sauber (billing-hub#5); Rollout-Sektion erzeugt Leerlauf-Schritt | fehlende Validierung | mittel | SURVIVES | billing-hub git/trees/main: 0 .windsurf-Pfade; Fix-PR #5 v. 01.06.; ADR-265-Tabelle „Beleg (2026-07-04)" | claim-before-cheapest-check ≥2 (retro_kpis) |
| F2b | Finder-Zusatzclaim „frist-hub/iil-voice-agent existieren nicht (404)" | Werkzeug | niedrig | REFUTED | meiki-lra/frist-hub + iilgmbh/iil-voice-agent existieren; Finder prüfte nur achimdehnert | — |
| F3 | Neuer Dependabot-Mechanismus erzeugte sofort roten, ungetriagten Folge-PR (iil-adrfw#48: ResolutionImpossible pydantic-core vs constraints.txt) ohne dokumentierten Triage-Pfad (nur Merge-Verbot) | fehlende Validierung | hoch | SURVIVES | gh pr checks 48 → security fail; run 28706164641 Log; dependabot.yml-Kommentar ≠ Prozess | — |
| F4 | „Sync ADRs to DevHub" chronisch rot seit ≥2026-06-19 (gemischt: 401 Unauthorized + exit 137/OOM), Session mergte 5 ADR-PRs hinein ohne Issue/Vermerk | Kommunikation | mittel | SURVIVES | 40/40 Runs failure; Log-Beispiele 03.07. (401) + 04.07. (137); gh issue list-Suchen leer | critical-alert-no-ticket ×1 (35c665) |
| F5 | iil-adrfw Required-Check bindet Python-Version in Protection-Vertrag („…py3.12…"); stabiler Aggregat-Job (`gate`, if always) existiert im Schwester-Reusable _ci-python.yml:596, wurde nicht übertragen | verfrühte Festlegung | mittel-hoch | SURVIVES | branch protection contexts; _ci-pypi.yml:147 Matrix-Name; _ci-python.yml gate-Job | feedback_adr242_wave1_doc_vs_reality (Memory, verwandt) |
| F6 | CI-Konvergenz ließ mypy still entfallen (iil-adrfw `types` + outlinefw `typecheck` waren BLOCKIEREND; Reusable: default off + non-blocking; bandit bei iil-adrfw ersatzlos); Trade-off in keinem Artefakt benannt | fehlende Validierung | hoch | SURVIVES | alte ci.yml-Blobs (pre-Konvergenz-SHAs) iil-adrfw/outlinefw vs. Thin-Caller; grep mypy/bandit ADR-266 → 0 | verification-query-independent (Memory, verwandt) |
| F7 | registry/pypi-fleet.yaml „Ground Truth"-Label irreführend (kein Auto-Refresh) | — | niedrig | REFUTED | _meta deklariert Regenerier-Holschuld; Live-Diff iil-adrfw/outlinefw: kein Drift; Drift-Klasse wird als eigenes Finding gemeldet | — |
| F8 | CI-Doppelwelle (16 PRs erst rot, 2. Fix-Welle) vermeidbar durch Vorab-ruff | — | niedrig | REFUTED | PR-Bodies deklarieren „rot = ehrliches Backlog, offen lassen" als Strategie; 4/16 direkt grün; Testklasse wäre lokal nicht gefangen; Zahlen des Befunds (16/19) falsch | lint-failure-no-local-gate ≥2 (retro_kpis; hier dennoch REFUTED — dokumentierte Strategie) |
| F9 | Inventar-Tool v1 scannte lokale Klone → 3 Phantom-K2-Verstöße in gemergtem ADR-266@#910; Korrektur #912 nach ~26 min; bekannte Lehre nicht vorab angewendet | fehlende Validierung | niedrig | SURVIVES | git diff 3c5e9e7 857362c (Statuskorrektur-Block); #912-Body | claim-before-cheapest-check ≥2; feedback_verification_query_must_be_independent_of_impl (Memory, existiert) |
| F10 | Governance-Doppelstandard Direct-Push vs. PR ohne Regel | — | niedrig | REFUTED | ADR-265-Rollout-Abschnitt spezifiziert „geschützte mains via PR, ungeschützte direkt"; Verhalten deckungsgleich | — |
| F10b | Rollout-Freigabe + Modus-Regel nicht durabel verankert: PR-#907-Body nannte Rollout noch „gegated, folgt nach Freigabe"; die real erteilte Freigabe (Chat) ist artefakt-unsichtbar; Regel lebt nur im ADR-265-Fließtext, nicht in Policy | Kommunikation | niedrig | SURVIVES | #907-Body vs. Rollout-Commits 08:22–08:24Z (5–7 min nach Merge); grep autonomy-gates.md → kein Push-Modus-Absatz | scope-checkpoint-not-durably-recorded ×2→3 (retro_kpis: gate-pflichtig) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle 8 Aufträge geliefert (PR-/Commit-Belege); Abzug: F1 (Aufsetzpunkt-Doc verfehlt Auftrag-4-Anspruch „nahtlos aufsetzen") |
| architektur_design | 3 | Guards/Health-Design überlebten Falsifikation (F7 refuted, health-Workflow security-sauber); Abzug: F5 (besseres Muster existierte im selben Repo), F6 (Gate-Katalog nicht diffgeprüft) |
| code_konventionstreue | 4 | ruff/pytest/ADR-Schema/Commit-Scopes durchgehend eingehalten (CI-Belege); Abzug: F2 (Beleg-Integrität eines ADR) |
| risiko_debt | 3 | Neue Debt: F6 (stiller Blocking-Verlust), F5 (tickende Merge-Blockade), F3 (roter Bot-PR ohne Pfad); dagegen Debt-Abbau: tote Publisher raus, 469-Commits-Policy-Stau gelöst |
| prozess_effizienz | 4 | 40+ PRs, 2 Wellen, ~26-min-Selbstkorrektur (F9), F8 refuted (Strategie statt Rework); Abzug: F4 (ungeflaggter Dauerrot-Fund) |
| entscheidungsqualitaet | 3 | nl2cad-Ausnahme + K2-Falsifikation + Binding-Stopp (2a) sauber; Abzug: F2 (stale Tabelle übernommen), F6 (Trade-off unbenannt entschieden) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| ADR-266 zuletzt 09:20Z committet; 30 Programm-PRs mergten danach; Doc blieb stehen | Fleet-Sweep endet erst mit „Doc-Sync-Commit": nach letztem Merge zurück ins Programm-ADR (Stufen-Status, Ausnahmen, Endbilanz) — als fester letzter Schritt jeder Welle | F1 |
| ADR-265-Tabelle übernahm Diagnose-Zahlen aus lokalem Scan; billing-hub war remote längst sauber | Jede Beweistabelle in einem ADR trägt nur Werte, die gegen origin/main bzw. Remote-API gezogen wurden; vor Commit ein Zeilen-Stichproben-Recheck (1 Repo pro Tabelle remote nachziehen) | F2 |
| dependabot.yml fleet-weit aktiviert; erster roter Folge-PR (#48) blieb unadressiert | Mechanismus-Einführung enthält Triage-Absatz im Programm-ADR (wer, wann, SLA) + Erstlauf-Sichtung der Folge-PRs am selben Tag als Abschluss-Schritt | F3 |
| 40/40 rote „Sync ADRs to DevHub"-Runs sichtbar, kein Issue geöffnet | Beim ersten Kontakt mit einem chronisch roten Workflow im eigenen Wirkungsbereich: 2-Minuten-Issue mit Log-Auszug + Fehlerklasse(n), auch wenn vorbestehend | F4 |
| Required-Checks 1:1 auf Matrix-Jobnamen gesetzt („…py3.12…"), obwohl _ci-python.yml ein gate-Aggregat vorlebt | _ci-pypi.yml bekommt denselben `gate`-Sammel-Job (needs: alle, if: always); Protections zeigen nur auf `gate` | F5 |
| Thin-Caller ersetzten alte CI ohne Job-Katalog-Diff; blockierendes mypy/bandit entfiel unbenannt | Vor jedem CI-Replace: Diff „Jobs alt vs. Jobs neu" (maschinell: Jobnamen+blocking-Flags); jeder Wegfall wird im PR-Body als Trade-off gelistet oder per Input reaktiviert | F6 |
| Inventar-Tool v1 las lokale Working-Trees; Phantom-Befunde erreichten main für 26 min | Neue Fleet-Scanner lesen ab erster Version origin/main/Remote (die Lehre stand in 2 Memories); Tool-Erstlauf wird gegen 1 bekannt-wahres Repo validiert, bevor Output in ADRs fließt | F9 |
| Rollout lief 5 min nach #907-Merge, dessen Body noch „gegated" sagte; Freigabe nur im Chat | Erteilte Freigaben werden im Artefakt nachgetragen (PR-Kommentar „Rollout freigegeben durch A.D. <Datum>" vor Ausführung) — deckungsgleich mit Gate `scope-checkpoint-not-durably-recorded` | F10b |

## 5. Längsschnitt (retro_kpis.py, Lauf 2026-07-04)

- `scope-checkpoint-not-durably-recorded` stand VOR dieser Retro auf ×2 (gate-pflichtig; PR-Template-Gate via #894 existiert) — F10b ist Vorkommen 3: **das bestehende Gate greift nicht für Chat-Freigaben zwischen PRs** → Gate nachschärfen, nicht neu erfinden.
- `claim-before-cheapest-check` ≥2 (gate-pflichtig laut Tool) — F2+F9 sind zwei neue Instanzen in EINER Session; der Marker-Scanner-Hook fängt die Unterklasse „lokaler Klon als Ground Truth" nicht → spezifisches Gate nötig (s. §6).
- `lint-failure-no-local-gate` ≥2 im Tool — der hiesige Kandidat F8 wurde jedoch REFUTED (dokumentierte Strategie); kein neues Vorkommen gezählt.
- refuted_rate 0.33 liegt im gesunden Band (Vorwerte 0.00–0.50).
- §5b Autonomie-Kalibrierung: over_ask=0, over_act=0 — alle Gates (Merges, Protection, Rollout) wurden menschlich freigegeben; die Classifier-Blocks (2× Mass-Aktion) wurden nicht umgangen, sondern in PR-Flow bzw. User-Items übersetzt. Kein Charter-Schärfungsbedarf aus dieser Session; F10b betrifft die Dokumentation der Freigabe, nicht ihre Einholung.

## 6. Verankerung (Vorschläge — Entscheid beim Menschen)

memory_candidates:
1. `feedback_stale_local_clone_never_ground_truth` (drift: true, drift_episode: 2026-07-04-pypi-fleet) — „Fleet-Aussagen (Tabellen in ADRs, Scanner-Output, Rollout-Ziellisten) NIE aus lokalen Working-Trees/Klonen ableiten; immer origin/main (`git fetch` + `ls-tree`/`show`) oder Remote-API. Realfälle 2026-07-04 ×2: ADR-265-Beweistabelle (billing-hub 54→real 0) und pypi_fleet_inventory v1 (3 Phantom-K2 auf main, Korrektur #912). Familie claim-before-cheapest-check (≥2 ⇒ Gate): billigster Check = 1 Tabellenzeile remote nachziehen."
2. `feedback_ci_replace_requires_job_catalog_diff` — „Vor Ersatz einer Repo-CI durch ein Reusable: Jobnamen+Blocking-Flags alt vs. neu diffen; jeder Wegfall (mypy, bandit, docs) wird im PR-Body als Trade-off benannt oder per Input reaktiviert. Realfall 2026-07-04: iil-adrfw (types blockierend + bandit) und outlinefw (mypy strict blockierend) verloren Gates unbenannt (#46, #13)."

adr_candidates / gate_candidates:
1. `_ci-pypi.yml` Amendment (kein neues ADR — folgt bestehendem _ci-python-Muster): `gate`-Aggregat-Job ergänzen; Doku-Satz „Protections zeigen nur auf gate"; iil-adrfw-Protection danach auf `gate` umstellen (eliminiert F5-Klasse fleet-weit).
2. Gate-Nachschärfung `scope-checkpoint-not-durably-recorded` (Vorkommen 3): Ausführungs-Skripte für gegatete Rollouts verlangen einen Freigabe-Nachweis-String (PR-Kommentar-URL) als Parameter — ohne Artefakt-Link kein Lauf.
3. ADR-266-Pflege-PR (kein neues ADR): Stufen-Status synchronisieren, nl2cad-Ausnahme + Dependabot-Triage-Absatz + billing-hub-Zeilen-Korrektur in ADR-265.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 1 | ADR-265/266-Pflege-PR: Stufen-Status, nl2cad-Ausnahme, Dependabot-Triage-Absatz, billing-hub-Tabellenkorrektur | platform | ADR-265/266 | 🔵 | ich, nach Retro-Merge |
| 2 | `gate`-Aggregat-Job in _ci-pypi.yml + iil-adrfw-Protection auf `gate` | platform, iil-adrfw | _ci-pypi.yml | 🔵 | ich (Protection-Teil = deine Freigabe) |
| 3 | mypy-Parität wiederherstellen: `enable_mypy: true` für iil-adrfw/outlinefw-Caller ODER Trade-off im ADR dokumentieren; bandit-Frage (Reusable-Input?) entscheiden | iil-adrfw, outlinefw, platform | #46/#13-Folge | 🟢 | Richtung entscheiden (du) |
| 4 | Issue „Sync ADRs to DevHub dauerrot seit 19.06. (401 + OOM/137)" mit Log-Auszügen öffnen | platform | neu | 🔵 | ich |
| 5 | iil-adrfw#48 triagieren (pydantic-core-Pin in constraints.txt vs. Bump) | iil-adrfw | #48 | 🟢 | entscheiden (du) od. ich mit Freigabe |
| 6 | 2 Memory-Kandidaten aus §6 annehmen/ablehnen | — | — | 🟢 | entscheiden (du) |
| 7 | Session-Ziele geliefert: ADR-265-Rollout (21 Repos), ADR-266 Stufen 1–3, 18/19 CI-Konvergenz, 33 PRs gemergt, Protection umgestellt | fleet | #907–#915 u. a. | ✅ | — |

## 8. Nicht verifiziert (Restlücken)

- Ob weitere der 15 konvergierten Repos (über die 4 Stichproben hinaus) blockierende mypy-/Sonstige-Jobs verloren (billigster Check: Schleife über pre-Konvergenz-ci.yml-Blobs, grep mypy+continue-on-error).
- Ob die 19 Dependabot-Erstlauf-PRs außer iil-adrfw#48 weitere rote enthalten (billigster Check: `gh pr list --author app/dependabot` + checks über alle 19 Repos).
- Wirkung des `[skip ci]`-Rollouts auf Repos mit main-basierten Scheduled-Workflows (nicht geprüft; billigster Check: je Rollout-Repo `gh run list --branch main --limit 1` nach 08:30Z).
- decks-hub/risk-hub/ttz-hub-Artefakt-Triage (aus Vormittags-Board) — unverändert offen, kein neuer Stand erhoben.
