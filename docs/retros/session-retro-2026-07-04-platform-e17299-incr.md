---
retro_schema: 1
date: 2026-07-04
repo_scope: [platform, iil-adrfw, outlinefw]
session_id: e17299-incr
footprint: full
footprint_reduction_reason: >-
  Rule-B-Trigger waere deep (3 Repos beruehrt). Downscale auf full, weil alle
  3 Bedingungen erfuellt sind: (a) reine CI-Workflow-/Branch-Protection-Config-
  Aenderung, keine Prod-Anwendungs-/Datenaenderung; (b) voll revertierbar
  (Workflow-Ref-Rueckstellung + Protection-Re-Edit, keine DB-Migration);
  (c) findings_total-Schaetzung <=10 (real: 4). Anchor-Minimum "nie lean"
  eingehalten (footprint=full, nicht lean).
findings_total: 4
findings_survived: 3
refuted_rate: 0.25
phase3_refuted: 1
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [critical-alert-no-ticket]
recurring_findings: [critical-alert-no-ticket]
---

# Session-Retro 2026-07-04 (Increment) — _ci-pypi Gate-Aggregat + F5/F6-Fix (platform#920, iil-adrfw#48/#49, outlinefw#15)

Increment-Retro auf `session-retro-2026-07-04-platform-e17299.md` (F5/F6). Scope:
platform#920 (`_ci-pypi.yml`: gate-Aggregat-Job, `mypy_blocking`, `enable_bandit`),
iil-adrfw#48 (Dependabot-Fix)+#49 (Consumer-Verifikation), outlinefw#15, iil-adrfw-
Branch-Protection jetzt `contexts: ["ci / gate"]` / `strict: false`. Methode: 1
Collector (haiku) + 1 Finder + 1 Skeptiker (sonnet, Dimension "Entscheidungen &
Fehler"), Falsifikation binär, Belege unabhängig aus `origin/main`/`gh api` gezogen.

## 1. Executive Summary

- F5 (Matrix-Job-Namen in Branch-Protection) und F6 (mypy/bandit-Paritätsverlust)
  aus dem Vorgänger-Retro sind **beide artefakt-belegt geschlossen**: `gate`-Job
  live in `_ci-pypi.yml@main`, iil-adrfw-Protection zeigt nur noch `ci / gate`,
  `mypy_blocking:true` + `enable_bandit:true` in iil-adrfw/outlinefw-Callern gesetzt.
- Härtester Survivor: **bandit ist seit der Reaktivierung (PR#49, 14:12 UTC)
  dauerhaft rot** (4 ungefixte Low-Findings) — ohne Fix, Baseline oder Issue.
  Das ist bereits das **zweite** Vorkommen des Musters „chronisch roter Check ohne
  Ticket" (`critical-alert-no-ticket`, erstmals im Basis-Retro F4) ⇒ **Gate-Pflicht**.
- Das Ein-Check-Gate-Design ist aktuell **nicht** live ausgenutzt schwächer als
  vorher: kein einziger der 15 weiteren `_ci-pypi.yml`-Caller setzt
  `enable_build:false`/`enable_security_scan:false` (fleet-weit verifiziert), und
  14/15 dieser Repos haben ohnehin **gar keine** Branch-Protection. Das
  Architektur-Risiko (statische `gate.needs`-Liste ohne Konsistenz-Test) bleibt
  aber ein echter, unadressierter Survivor.
- Der ursprüngliche Verdacht „mypy-Rename bricht woanders Branch-Protection" ist
  **REFUTED**: es existiert fleet-weit schlicht keine weitere Protection, die
  brechen könnte — kein Befund.
- Der Direct-Push auf den Dependabot-Branch (PR#48) verlief unfallfrei, aber
  ungeprüft gegen das reale Risiko: `rebase-strategy` steht auf Default `auto`,
  nicht `disabled` — ein Force-Push-Overwrite-Fenster war real, nur nicht getroffen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| 1 | Gate-Aggregat löst F5 (Matrix-Kopplung), verschiebt die Kopplung aber auf eine manuell gepflegte `gate.needs: [lint, secrets-scan, test, build, mypy, security, bandit]`-Liste ohne automatisierten Test, der "jeder `if:inputs.enable_X`-Job steht in `needs`" erzwingt. Aktuell 0 Lücke (alle 4 bedingten Jobs erfasst) und 0/15 Caller setzen `enable_build:false`/`enable_security_scan:false` — reines Zukunftsrisiko, kein Live-Schaden | Prozesslücke | mittel | SURVIVES | `_ci-pypi.yml@origin/main` Job `gate.needs`; `gh search code` 0 Treffer `enable_build: false`/`enable_security_scan: false` org-weit; `tools/tests/test_pypi_fleet_inventory.py` prüft nur Caller-Referenz, nicht `needs`-Konsistenz | — (neu) |
| 2 | Bandit seit Reaktivierung (Commit 6b01990, PR#49, 14:12:37Z) auf jedem seitherigen main-Lauf `failure` (4 Findings: B110/B112 in `src/iil_adrfw/cli.py:389/520/638`, B101 in `src/iil_adrfw/server.py:510` — alle Low-Severity/High-Confidence), ohne Fix, Suppression oder Baseline vor der Aktivierung; `gate` verschluckt es intern (`continue-on-error`), aber der GitHub-Check bleibt für jeden Betrachter dauerhaft rot | fehlende Validierung | hoch | SURVIVES | `gh api .../commits/6b01990/check-runs`: `ci / SAST (bandit, non-blocking)` = failure; Bandit-Job-Log Run 28708849022 (4 Findings); main hat seit 6b01990 noch keinen Folgecommit (n=1 Lauf, "dauerhaft" ist zum jetzigen Zeitpunkt eine Ein-Punkt-Beobachtung) | **`critical-alert-no-ticket` ×2** (35c665 F4, hier) ⇒ GATE-PFLICHT |
| 3 | Fix für iil-adrfw#48 als Commit direkt auf den Dependabot-Branch gepusht (Achim Dehnert, 14:06:29Z, ~1h40 nach Dependabots Commit), statt PR schließen+eigener Branch oder `@dependabot`-Kommando. Kein sichtbarer Schaden (Merge 4,4 Min später, keine Dependabot-Folge-Events), aber `iil-adrfw/.github/dependabot.yml` hat **keinen** `rebase-strategy: disabled` gesetzt (Default `auto`) — ein Dependabot-Rebase vor dem Merge hätte den manuellen Commit force-push-überschreiben können | verfrühte Festlegung | niedrig | SURVIVES | PR#48 Commits+Timeline (`gh api .../issues/48/timeline`: nur merged/closed/head_ref_deleted, keine Dependabot-Recreate-Events); `dependabot.yml` ohne `rebase-strategy`-Key | — (neu) |
| 4 | mypy-Job-Rename ("Type Check (mypy, non-blocking)" → "Type Check (mypy)") könnte fleet-weit Branch-Protection auf den alten Namen brechen | — | — | **REFUTED — kein Befund** | Von 15 `_ci-pypi.yml@main`-Callern haben 14 (alle außer iil-adrfw) **gar keine** Branch-Protection (`gh api .../branches/main/protection` → 404 bei jedem); iil-adrfw selbst zeigt bereits nur `contexts:["ci / gate"]`, keinen Einzel-Job-Namen. `gh search code` für den alten String: 0 Treffer org-weit. Es gibt fleet-weit nichts, das durch den Rename brechen könnte | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | F5+F6 beide artefakt-belegt geschlossen (gate-Job live, mypy_blocking+enable_bandit gesetzt, #48 gemergt); Abzug: bandit-Reaktivierung erzeugt neue ungetriagte Debt (#2) |
| architektur_design | 4 | Gate-Pattern sauber aus `_ci-python.yml` übernommen, im YAML gut kommentiert (Retro-e17299-Referenzen im Code); Abzug: `gate.needs` als manuelle Liste ohne Konsistenz-Test (#1) |
| code_konventionstreue | 4 | 1 Commit, klare Commit-Messages, saubere Doku-Kommentare im Workflow; Rename vollständig referenzfrei (#4 REFUTED bestätigt Sauberkeit) |
| risiko_debt | 3 | Neue Debt: dauerrotes bandit ohne Baseline (#2, jetzt 2. Vorkommen der Alarm-Müdigkeits-Familie); Architektur-Zukunftsrisiko #1 unadressiert |
| prozess_effizienz | 4 | 3-Repo-Fix in <1h koordiniert (temporärer @feature-ref auf PR#49/#15 vor Merge, danach zurück auf @main) — sauberes Vor-Merge-Verifikationsmuster; Abzug: kein Baseline-Schritt vor bandit-Enable |
| entscheidungsqualitaet | 4 | Trade-off-Entscheidungen im Code klar begründet (Kommentare zu enable_build/gate-Semantik); Abzug: bandit-Reaktivierung ohne Vorab-Scan, Direct-Push ohne rebase-strategy-Check |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| `gate.needs` ist eine statische, von Hand gepflegte Job-Liste ohne Test, der neue `if:inputs.enable_X`-Jobs erzwingt einzutragen | Ein leichtgewichtiger Test (z. B. in `tools/tests/`) parst `_ci-pypi.yml`/`_ci-python.yml` und prüft: jeder Job mit `if: inputs.enable_*` erscheint in `gate.needs` — CI-Fail bei Abweichung | #1 |
| bandit wurde reaktiviert (Parität zur Vorgänger-CI), ohne vorher einen Baseline-Scan zu fahren; 4 Findings blieben ungefixt/unsuppressed → dauerrot ab dem ersten Lauf | Vor Reaktivierung eines vorher entfallenen (Advisory- oder Blocking-)Gates: einmal offline/lokal scannen, Findings fixen ODER mit Begründung + Baseline-Datei suppressen, danach erst den Input auf `true` setzen | #2 |
| Fix für #48 direkt auf den Dependabot-Branch gepusht, ohne vorher `dependabot.yml`-`rebase-strategy` zu prüfen | Vor Direct-Push auf einen `dependabot/*`-Branch: `rebase-strategy` prüfen — nur bei `disabled` direkt pushen, sonst `@dependabot rebase` abwarten oder PR schließen + eigenen Branch nutzen | #3 |

## 5. Längsschnitt (`retro_kpis.py`, Lauf 2026-07-04)

- **`critical-alert-no-ticket` steht jetzt auf ×2** (35c665 F4 „Sync ADRs to DevHub chronisch rot ohne Issue", hier: bandit dauerrot ohne Issue/Baseline) ⇒ **GATE-PFLICHT** laut Tool-Schwelle. Beide Fälle: ein Check wird dauerhaft rot toleriert, weil er technisch non-blocking ist — das Muster ist nicht repo-spezifisch, sondern eine wiederkehrende Lücke im Umgang mit "advisory rot". Konkreter Gate-Vorschlag in §6.
- Alle 5 bereits gate-pflichtigen Slugs aus dem Gesamt-Längsschnitt (`claim-before-cheapest-check`, `lint-failure-no-local-gate`, `parallel-session-pr-collision`, `planned-phase-no-issue`, `scope-checkpoint-not-durably-recorded`) tauchen in DIESEM Increment **nicht** erneut auf — kein neuer Beleg für sie in den geprüften Artefakten.
- `refuted_rate` 0.25 liegt im gesunden Band (Vorwerte 0.00–0.50 über 8 Retros).
- §5b Autonomie-Kalibrierung: `over_ask=0`, `over_act=0` bei den verifizierbaren Fakten (keine Prod-Anwendungsänderung, keine Merges ohne CI-Grün). **Eine Lücke bleibt unverifiziert** (s. §8): ob die Branch-Protection-Änderung auf iil-adrfw (Security-Config-Gate laut Autonomie-Charter) vor der Ausführung einen dokumentierten Freigabe-Nachweis hatte — dazu liegt in den geprüften Artefakten (PR-Bodies, Commits) kein Beleg vor, weder positiv noch negativ.

## 6. Verankerung (Vorschläge — Entscheid beim Menschen)

**memory_candidates:**
1. `feedback_advisory_gate_reactivation_needs_baseline` (drift: true, drift_episode: 2026-07-04-bandit-dauerrot) — „Ein vorher entfallenes Advisory-/Blocking-Gate (bandit, mypy, …) NIE blind per Input reaktivieren — erst einmal offline scannen, Findings fixen oder mit Baseline/Begründung suppressen, dann Input auf true. Realfall: iil-adrfw bandit-Reaktivierung (platform#920/iil-adrfw#49) lief seit dem ersten Lauf permanent rot (4 Low-Findings), kein Issue/Baseline. Zweites Vorkommen der Familie `critical-alert-no-ticket` (erstmals 35c665 „Sync ADRs to DevHub")."
2. `feedback_dependabot_direct_push_check_rebase_strategy` — „Vor Direct-Push auf einen `dependabot/*`-Branch `dependabot.yml`-`rebase-strategy` prüfen (nur `disabled` ist überschreib-sicher); sonst `@dependabot rebase` oder eigener Branch. Realfall iil-adrfw#48: unfallfrei, aber `rebase-strategy` stand auf Default `auto` — Risiko war real, nur nicht getroffen."

**gate_candidates:**
1. `critical-alert-no-ticket` (jetzt ×2) — GATE-PFLICHT: ein CI-Check, der 2 aufeinanderfolgende main-Läufe `failure` zeigt (auch wenn `continue-on-error`/non-blocking), erzeugt automatisch ein Tracking-Issue mit Log-Auszug, statt stillschweigend zu bleiben. Kandidat für einen kleinen Scheduled-Workflow oder eine Ergänzung zu `repo_health_check.py`.

**adr_candidates:** keiner — reine Ergänzung nach bestehendem `_ci-python.yml`-Gate-Muster, kein neuer Architektur-Entscheid (folgt `adr-threshold.md`).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 1 | bandit-Findings triagieren (4× Low: 3× try/except in cli.py, 1× B101 assert in server.py) — fixen oder mit Begründung suppressen | iil-adrfw | neu | 🟢 | entscheiden (du) — fixen vs. `# nosec` mit Begründung |
| 2 | `critical-alert-no-ticket`-Gate umsetzen (2. Vorkommen, gate-pflichtig) | platform | neu | 🟢 | entscheiden (du) — Umfang/Ort des Gates |
| 3 | Konsistenz-Test `gate.needs` vs. `if:inputs.enable_*`-Jobs ergänzen | platform | neu | 🔵 | ich, nach Freigabe |
| 4 | 2 Memory-Kandidaten aus §6 annehmen/ablehnen | — | — | 🟢 | entscheiden (du) |
| 5 | F5/F6 aus Basis-Retro als geschlossen markieren | platform | e17299-Report | ✅ | — |

## 8. Nicht verifiziert (Restlücken)

- Ob die Branch-Protection-Änderung auf iil-adrfw (Security-Config-Gate) vor Ausführung einen dokumentierten Freigabe-Nachweis hatte — kein Beleg weder für noch gegen in PR-Bodies/Commits gefunden; billigster Check: Chat-Verlauf der Ursprungssession nach explizitem Freigabe-Wort durchsuchen.
- Ob outlinefw (PR#15) denselben bandit-Dauerrot-Zustand zeigt wie iil-adrfw — outlinefw-Caller aktiviert laut Rohdaten nur `enable_mypy`/`mypy_blocking`, nicht `enable_bandit`; nicht am Live-Check verifiziert, da kein `gh api`-Pull für outlinefw-Checks durchgeführt wurde. Billigster Check: `gh api repos/achimdehnert/outlinefw/commits/<main-sha>/check-runs`.
- Ob die 4. Bandit-Finding-Zeile (B101 in `server.py:510`) im ursprünglichen Log tatsächlich vollständig ist oder das Log weitere Findings abschneidet — nicht mit einem vollständigen Rohlog-Dump verifiziert, nur mit der Metrik-Zusammenfassung (4 Issues total).
- Ob ein Bandit-main-Lauf NACH 6b01990 existiert, der den Dauerrot-Charakter über mehr als einen Datenpunkt bestätigt — zum Zeitpunkt dieser Retro ist 6b01990 noch HEAD von iil-adrfw/main (n=1).
