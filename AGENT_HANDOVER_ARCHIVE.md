# Agent Handover — Archiv

> Ausgelagerte „## ⚡ Vorheriger Stand"-Blöcke aus `AGENT_HANDOVER.md`, die älter als
> 2026-06-19 sind (Konvention: `AGENT_HANDOVER.md` hält nur den aktuellen Stand + 1
> vorherigen Stand; alles Ältere wandert hierher). Rein historisch — nicht als aktueller
> Stand lesen, nur als Kontext/Nachschlagewerk für vergangene Sessions.
>
> Ausgelagert: 2026-07-02 (Issue #821, Teil 2).

## ⚡ Vorheriger Stand (2026-06-12 — T5-Programm: ADR-243/244/245 proposed + 7-Issue-Sonnet-Queue)

**Diese Session (2026-06-12, Fable/Tier-4-5):**
- **Tier-4/5-Codebase-Analyse** (platform + 17 PyPI-Pakete, 6 parallele Agents; 3 falsifizierte
  Agent-Claims dokumentiert in CC-Memory `t5-optimierungsprogramm`).
- **PR #551 gemergt** (squash `bcdb910`): **ADR-243** iil-corefw (Shared Runtime Core) ·
  **ADR-244** Rule-Lifecycle-Loop (4 Engines inkl. Guardian!) · **ADR-245** Provider-Policy-Engine
  (free-tier-first als Code) — **alle `proposed`**, je `/adr-review`-t (4.2/3.8/3.7) + Findings
  als Fixups drin. Dazu **ADR-234 §11.2** (P0-Restschuld Verteilungs-Schicht) + INDEX-Reparatur
  (237–242 nachgetragen, **241 = reservierte Nummer ohne Datei**).
- **Sonnet-Queue erstellt** (alle `ai-assignable`): platform#552 shared-ci-Sweep (Tag-vs-main-Check
  Pflicht!) · platform#553 Pipeline-Doku · iil-testkit#6 Gotcha-Fixtures · iil-codeguard#2
  Suppression (Marker-Dialekte beachten, s. Issue-Kommentar) · iil-enrichment#2 + gaeb-toolkit#7
  publish.yml · risk-hub#177 (blocked by enrichment#2) · riskfw#4 (Owner-Entscheid Rename).

**Offen — erster Zug nächste Session:**
- **Externes ADR-243-Review einarbeiten:** Briefing liegt in
  `~/shared/adr-handoff-ADR-243-2026-06-12.md` (wartet auf GPT-Antwort vom User) →
  Step-5-Rückfluss-Gate (ID-Tagging `[valid]`/…), dann Accept-Entscheide 243→244/245
  (Sequenz: 245 braucht 243-Fehlerkategorien; 244-Severity-Heimat hängt an 243-Status).
- **Knowledge-Capture nachholen:** Outline-MCP war in dieser Session nicht gebunden —
  Session-Wissen liegt nur in pgvector (`session:platform:20260612*`) + CC-Memory.
- Plus unverändert: ADR-242 Phase 3/4, coach-hub#28, F4-Breite (s. Vorheriger Stand).

## ⚡ Vorheriger Stand (2026-06-11 — M6 ✅, ADR-242 accepted + Phase-2-Rollout ✅)

**Diese Session (2026-06-11):**
- **M6 Profil-B ✅ abgeschlossen** — PR #536 gemergt; bashrc-Block gesetzt; App public; Tokens iilgmbh+bahn-sqf grün.
- **ADR-242 accepted** — PR #535 gemergt; `status: accepted`, `implementation_status: in_progress`.
- **Rollout Phase 2 ✅** — 3 PRs parallel gemergt:
  - #540: `ci / gate` Aggregat-Job in `platform/_ci-python.yml` (required-check-Basis)
  - #541: `governance/rulesets/` — Template + Wave-1-Liste (7 Repos) + `tools/apply-branch-protection.sh`
  - #542: `workflow_dispatch`-Workflow `apply-branch-protection.yml` — Pilot über GitHub Actions UI
- **Permission** `Bash(gh api repos/*/rulesets*)` in `.claude/settings.local.json` gesetzt (ab nächster Session wirksam für direkten Script-Run).

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **ADR-242 Phase 3 (Pilot):** Workflow via GitHub Actions UI triggern: Actions → "ADR-242: Apply Branch Protection (Wave 1)" → `dry_run: true` → dann live. ODER: `bash tools/apply-branch-protection.sh` direkt (Permission in settings.local.json ab nächster Session).
- **ADR-242 Phase 4:** `branch-protection-meter` Workflow + Discord-Alert (ADR-242 §Rollout 4)
- **coach-hub #28**: STOP — `django-lms-lite` privater Repo, kein CI-Zugriff. Dep-Entscheid.
- **F4 CI-grün-Programm (Breite):** ~34 Repos rote main-CI; nächste Welle = Ruff/Config-Drift an der Quelle.

## ⚡ Vorheriger Stand (2026-06-10 — ref-sweep abgeschlossen; nur coach-hub#28 offen)

**Diese Session (2026-06-10, später):** **research-hub#6 gemergt** (squash, `7b3260d`). Zwei
unabhängige teardown-Bugs gefixt (beide mit Standalone-Repro reproduziert, dann CI-grün):
(1) async-ORM leakt worker-thread-DB-Connection (`asyncio.run` schließt sie nie) →
`being accessed by other users` — Fix `await sync_to_async(connections.close_all)()` im
Service; (2) `transaction=True`-flush-TRUNCATE ohne CASCADE scheitert an
`tenancy_module_membership` (django_tenancy FK→auth_user, ADR-130) — Fix conftest-Fixture
`sql_flush allow_cascade=True`. ⚠️ **Vorherige Diagnose „django-tenancy nicht für 3.12
verfügbar" war FALSCH** (Paket ist da, aus risk-hub/packages). Fleet-Pattern → Memory
`feedback_transaction_true_async_test_teardown`. Nur noch **coach-hub#28** offen (Dep-Entscheid).

**Diese Session (2026-06-10):** weltenhub#16 verifiziert gemergt (2026-06-09 16:46 UTC) → **ref-sweep 12/12 ✅ komplett**.

**Vorherige Session (2026-06-09 — F4-Fixes + Ref-Sweep-Abschluss):** `shared-ci v1.0.3` trägt `pg_isready -U test_user`-Fix. 5 multi-layer F4-Fixes für weltenhub, 3 für wedding-hub, 1 für onboarding-hub. Alle 12 Sweep-PRs gemergt (illustration#8, wedding#19, onboarding#2, travel-beat#38, tax-hub#4, recruiting-hub#7, dms-hub#3, cad-hub#23, billing-hub#6, mcp-hub#106/trading-hub#14, **weltenhub#16**). coach-hub#28 + research-hub#6 = STOP (research-hub#6 inzwischen gefixt+gemergt, s.o.).

**Davor (2026-06-09 — shared-ci v1.0.2):** `deploy_runs_on`-Fix → v1.0.2; mcp-hub + trading-hub forward-gefixt; alle 12 Sweep-PRs auf @v1.0.2 re-pointet. Drift: `feedback_sharedci_tag_stale_vs_platform_main`.

**Davor (2026-06-08):** F4-acute ✅, ADR-212 Phase-1 ✅, F1 .windsurf-Untrack ✅.

**Offen — direkt umsetzbar (erster Zug nächste Session):**
- **coach-hub #28**: STOP — `django-lms-lite` ist privater GitHub-Repo, kein CI-Zugriff (Test + Security Scan scheitern an `git clone … Authentication failed`). Entscheiden: Dep öffentlich machen / mirror / als Wheel vendoren / PAT-Zugriff fixen. = einzige offene ref-sweep-PR; Dep-Architektur-Entscheid, kein Test-Fix.
- **M6 Profil B fertig:** nur noch manuell: App auf **„Any account"** + Install auf `iilgmbh`+`bahn-sqf` → dann `claude-ent iilgmbh` = Org-Admin. Details: `docs/PROFILE_B.md`.
- **Branch-Protection-Lücke:** 0/14 Hubs haben required-status-checks auf `main` → no-bypass unenforced. ADR-Kandidat.
- **#7 risk-hub→Enterprise-Transfer:** deferred (gegated hinter KONZ-002 S2).
- **shared-ci Issue #3:** eigene CI (actionlint) für die reusable Workflows.

**Kontext-Memories (auto-load):** 🌀 `feedback_sharedci_tag_stale_vs_platform_main` · `project_profile_b_app_state` · `project_riskhub_prod_launch` · 🌀 `feedback_commit_on_main_recurs` · 🌀 `feedback_merge_to_main_triggers_deploy`.
