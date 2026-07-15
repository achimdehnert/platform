# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

> **Stand: Juni 2026** — CC-first (ADR-230), cc-skill-dist, 7 MCP-Server

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-15 — Deploy-Health-Triage gelöst · ADR-270-Vorbedingung gefixt · 2 adversariale Retros (c494a2 + Increment) · Ausführungstreue-Programm gestartet)

**Diese Session (2026-07-15):** Session-Start-Reconciliation fand Prio 1 (cad-hub#42) bereits erledigt (Handover war stale). Danach: reaktive Deploy-Health-Triage + ADR-270-Nacharbeit + Owner-Block-#1094-Experiment, gefolgt von zwei adversarialen Retros (Haupt-Retro + Same-Day-Increment) und einem daraus abgeleiteten Ausführungstreue-Programm.

- **ADR-270-Vorbedingung gefixt ([#1152](https://github.com/achimdehnert/platform/pull/1152) gemergt):** `guardian.yml` + `ci-security.yml` triggerten nur auf `pull_request`, nicht auf `merge_group` — hätte beim ersten Merge-Queue-Einsatz ALLE Merges eingefroren (ADR-270 harte Vorbedingung). Jetzt behoben, präventiv (platform hat noch keine Merge-Queue aktiv).
- **trading-hub#150 gemergt:** Docker-Build-Smoke-Test brauchte `DB_PASSWORD` zusätzlich zu `DJANGO_SECRET_KEY` (SEC-2-Guard aus #108 vergessen) — PR existierte schon vorbereitet, nur verifiziert+gemergt.
- **coach-hub Deploy gelöst (PR [#40](https://github.com/achimdehnert/coach-hub/pull/40) gemergt, live verifiziert `/livez/` 200):** Root Cause war **NICHT** `PROJECT_PAT` wie am 07-12 vermutet, sondern zwei gestapelte Ursachen: (1) transiente Runner-Kontention beim gitleaks-Checkout (Re-Run bewies es), (2) coach-hub war auf `shared-ci@v1.0.5` gepinnt — der Git-Auth-Fix für private Deps kam erst in v1.0.6. Bump auf v1.0.11 (existierender PR #40 war bereits vorbereitet, nur stale/unrebased — rebased statt dupliziert).
- **Neuer Fund, getrackt statt gefixt ([#1158](https://github.com/achimdehnert/platform/issues/1158)):** `secrets: inherit` liefert cross-org (shared-ci in `iilgmbh`, Consumer in `achimdehnert`) für den **`ci:`-Job** kein Secret (bestätigt leer trotz vorhandenem Repo-Secret) — derselbe Bug wie #1067, dort aber nur für den `deploy:`-Job gefixt. Betrifft mind. coach-hub + risk-hub identisch unfixed. Non-blocking (pip-audit `continue-on-error`), Scope-Checkpoint statt Sofort-Fix (User-Entscheid: Fleet-Issue statt Einzel-Repo-Patch).
- **Owner-Block #1094 — Mail-Digest-Experiment:** 6 offene Punkte (PyPI-Owner, 7×Trusted-Publisher, aifw-Yank-Entscheid, 2 Releases, Portfolio-Termin) als Mail an pg@dehnert.team gesendet statt auf eine Sync-Session zu warten — v2 mit Direkt-Links (GitHub-Release-Prefill für outlinefw/weltenfw, PyPI-Settings-Links unverifiziert). Antwort noch nicht geprüft — Follow-through braucht Text-Paste in eine Session (kein Mailbox-Zugriff hier).
- **Adversarialer Retro `session-retro-2026-07-15-platform-c494a2` ([#1162](https://github.com/achimdehnert/platform/pull/1162), noch offen):** 9 Befunde, 8 überlebten Falsifikation. Kern: 2 bereits Gate-pflichtige Muster (`claim-before-cheapest-check`, `scope-checkpoint-not-durably-recorded`) reproduziert — u. a. ein Root-Cause-Satz ("transiente Kontention") mit mehr Bestimmtheit formuliert als die Log-Beleglage trug.
- **Same-Day-Increment-Retro ([#1165](https://github.com/achimdehnert/platform/pull/1165) gemergt):** prüfte die Follow-through-Arbeit des Haupt-Retros. Fand: die #1122-Handover-Konsolidierung hatte real 4 Inhalte verloren trotz „kein Inhalt verloren"-Behauptung (durch 2 unabhängige Finder bestätigt) — beide Gate-pflichtigen Muster recurrierten **innerhalb desselben Tages**, in dem sie benannt wurden. Alle 5 identifizierten Sofort-Fixes umgesetzt: Inhalt in diesem PR restauriert, `session-start.md`-Checkliste um 2 selbst ausgelassene Phasen ergänzt ([#1166](https://github.com/achimdehnert/platform/pull/1166) gemergt), `~/.claude/CLAUDE.md` committed (war uncommitted trotz echtem Git-Repo), Nachtrags-Kommentare mit Autorisierungs-Zitat auf #1079/#1122/#1164.
- **Ausführungstreue-Programm gestartet:** neue Hausregel in `~/.claude/CLAUDE.md` (lange Multi-Phasen-Dokumente brauchen eine Abschluss-Checkliste, sonst sind Pflicht-Phasen strukturell überspringbar) + Memory `feedback_execution_fidelity_long_documents` + Tracking-Issue [#1167](https://github.com/achimdehnert/platform/issues/1167) (57 ADRs + 19 KONZ-Dokumente auf dasselbe Muster noch ungeprüft).
- **Reviewer-Engpass sichtbar geworden:** 28-30 offene platform-PRs hängen `REVIEW_REQUIRED` auf demselben Einzel-Reviewer (`wirdigital`). #1159/#1163/#1165/#1166 per Auto-Merge gequeued, alle 4 nach Freigabe gemergt — #1162 (Haupt-Retro) bleibt als einziger PR dieser Session offen.
- **Ausführungstreue-Audit #1167 umgesetzt:** Skill-Template-Fix (`/konzept` §13 braucht jetzt eine Kriterium→Status-Tabelle, [#1169](https://github.com/achimdehnert/platform/pull/1169) gemergt — 18/19 aktive KONZ-Dokumente hatten denselben Gap, Bestandsdokumente bewusst NICHT retrofittet) + 11 aktive ADRs (von 57) bekamen Phasen-Status-Tabellen mit Beleg pro Zeile ([#1170](https://github.com/achimdehnert/platform/pull/1170) gemergt, gebündelt statt 11 Einzel-PRs). Dabei 2 echte Selbstwidersprüche in bestehenden ADRs gefunden und transparent geflaggt statt still korrigiert (ADR-057 Phase 2, ADR-178 Phase 2 — beide "complete/done" behauptet, während ein Detail im selben Abschnitt das Gegenteil zeigt).

## ⚡ Vorheriger Stand (2026-07-13 — usage_sweep.py (#1076) shipped + erster Lauf · trading-hub Deploy-403 gefixt · KONZ-017 #998 gemergt · PyPI-OIDC-Readiness codeguard/ingest · App-Repo-Scope-Grenze geklärt)

**Diese Session (2026-07-13, Sonnet 5):** `/issues-offen`-Lauf + Owner-Block-Nacharbeit + neues Tool. Wichtigster Prozess-Fund: eigener stale lokaler Klon (iil-codeguard/iil-ingest, 5 Commits alt) fast in eine Migration auf eine bereits gelöschte Datei gelaufen — vor dem Bauen gegen origin/main geprüft, Kurs korrigiert.

- **usage_sweep.py gebaut + gemergt ([#1116](https://github.com/achimdehnert/platform/pull/1116), schließt [#1076](https://github.com/achimdehnert/platform/issues/1076)):** Quartals-Nutzungs-Sweep (4 Messungen, n/m/k-Konvention). Erster echter Lauf → [#1115](https://github.com/achimdehnert/platform/issues/1115) (46 Skill- + 56 Label-Kandidaten). Nachtriage fand Methodik-Lücke: lokale Transkripte reichen nur 30 Tage zurück, nicht 180 wie im Default-Fenster behauptet — als Korrektur im Issue dokumentiert. Engere Liste (37) nach Ausschluss von Sub-Referenz-Fragmenten + Notfall-Skills (hotfix/rollback/backup by-design selten genutzt). Rückbau-Entscheidung bleibt beim Owner (bewusst kein Auto-Delete).
- **trading-hub Deploy-403 diagnostiziert + gefixt:** GHCR-403 beim Import-Smoke-Pull direkt nach erfolgreichem Push (Propagations-Lag, nicht die bekannte Package-Actions-Access-Klasse). `gh run rerun --failed` → grün, `/livez` 200 verifiziert. Deploy-Health-Issue [#1070](https://github.com/achimdehnert/platform/issues/1070) mit Root-Cause geschlossen.
- **KONZ-017 W1 (sync-drift-meter #998) gemergt via [#1009](https://github.com/achimdehnert/platform/pull/1009):** self-hosted GITHUB_DIR-Pfad-Mismatch behoben (dynamische Auflösung + platform-Symlink-Fix). PR lag 5 Tage `REVIEW_REQUIRED` — nach Freigabe via Auto-Merge gemergt.
- **Owner-Block [#1094](https://github.com/achimdehnert/platform/issues/1094) nachgearbeitet:** stale shared-ci#20-Checkbox korrigiert (war schon CLOSED, Zeile nicht abgehakt). Diagnose der „7 Nicht-pur-OIDC-Repos": 5 sind pypa-Action-ready (nur PyPI-UI-Bindung fehlt), 2 (iil-codeguard/iil-ingest) publizierten noch über `twine`+Token OHNE `id-token:write` — UND der reale Publish-Workflow liegt zentral in `platform` (`publish-iil-{codeguard,ingest}.yml`, PAT-Checkout), nicht im Paket-Repo (eigenes `publish.yml` war am 2026-06-30 bewusst als ungegateter Zweitpfad entfernt worden — mein lokaler Klon war stale und zeigte noch die gelöschte Datei). Fix: [#1118](https://github.com/achimdehnert/platform/pull/1118) (id-token:write + pypa-Action, additiv, Token bleibt bis Binding-Beweis) — **wichtig für später: Trusted-Publisher-Binding muss auf `repo=platform` + Workflow-Dateiname zeigen, nicht auf das Paket-Repo.**
- **App-Repo-Scope-Grenze geklärt (User-Korrektur mitten in der Session):** „arbeite an platform/mcp/dev, nicht an apps" — trading-hub-Branch-Protection-Vorschlag ([#1117](https://github.com/achimdehnert/platform/issues/1117)) und PR [#130](https://github.com/achimdehnert/trading-hub/pull/130) (README-Fix, grün/mergefähig) bewusst zurückgestellt, nicht ausgeführt.
- **2 False-Positive-docu-quality-Issues geschlossen** (dev-hub [#1107](https://github.com/achimdehnert/platform/issues/1107)/[#1101](https://github.com/achimdehnert/platform/issues/1101), alle Findings gegen aktuellen Code verifiziert widerlegt) + Befund zur docu-update-agent-False-Positive-Rate getrackt ([#1114](https://github.com/achimdehnert/platform/issues/1114)).
- **Governance-Detail geklärt:** 2. Owner-Review-Pflicht macht Sinn (required checks sind eng: nur guardian+gitleaks, nicht der volle Testlauf — Review ist die einzige menschliche Instanz vor Governance-SSoT). Auto-Merge auf #1116/#1009/#1118 aktiviert, damit Review der einzige verbleibende manuelle Schritt ist.

## Nächste Schritte (kompakt)

1. Owner-Block [#1094](https://github.com/achimdehnert/platform/issues/1094) abarbeiten — Mail-Digest raus (07-15), Antwort/Fortschritt noch zu prüfen
2. Fleet-Follow-up [#1158](https://github.com/achimdehnert/platform/issues/1158): `secrets: inherit` cross-org im `ci:`-Job fixen (mind. coach-hub + risk-hub betroffen)
3. Stub-Issues via Sonnet-Session (`/model sonnet` + `/issues-offen`)
4. trading-hub Branch-Protection [#1117](https://github.com/achimdehnert/platform/issues/1117) — seit 07-13 bewusst zurückgestellt (App-Repo-Scope), weiterhin offen
5. KONZ-018 W1: testkit-Dedup, Freshness-Pilot promptfw
6. usage-sweep [#1115](https://github.com/achimdehnert/platform/issues/1115): 37 Skill-/Label-Kandidaten aus 07-13 — Einzelfall-Rückbau-Entscheidung weiterhin offen
7. Orchestrator-MCP „Invalid Bearer Token" (seit 07-13 unbearbeitet) — Memory-Warm-Start/Recurring-Errors tot; Token gegen Secrets-Ablage prüfen
8. Haupt-Retro [#1162](https://github.com/achimdehnert/platform/pull/1162) reviewen/mergen — einziger PR dieser Session, der noch offen ist

> **Erledigt 2026-07-15:** cad-hub#42 (war schon vor Session-Start gemergt, Handover war stale) · trading-hub#150 · coach-hub#40 · ADR-270-Vorbedingung (#1152) · Increment-Retro (#1165) · session-start-Checkliste-Nachbesserung (#1166) · Ausführungstreue-Audit #1167 (konzept-Skill-Fix #1169 + 11 ADR-Tabellen #1170).
> **Erledigt 2026-07-13 (nachgezogen, war nur in PR #1122 unmerged dokumentiert):** KONZ-017 W1 sync-drift-meter #998 (#1009 gemergt) · usage_sweep.py (#1116 gemergt) · trading-hub Deploy-403 (#1070 zu) · PyPI-OIDC-Readiness codeguard/ingest (#1118 gemergt) · trading-hub PR #130 (README-Fix, inzwischen gemergt).

> **Ältere Stände** (2026-07-10 Mail-Skill, 2026-06-20 F4/Wave-2 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — Tracking **[#811](https://github.com/achimdehnert/platform/issues/811)**. **Realer Stand 2026-07-10 (gegen #811+Retro abgeglichen, weiter als der Issue selbst zeigt):** Phase 1 (learn-hub, recruiting-hub, travel-beat) komplett, gemergt UND live Wave-3-geschützt. Zusätzlich 3 Repos außerhalb der ursprünglichen Worklist live geschützt (weltenhub, illustration-hub, research-hub) — **nachträglich offiziell in #811 aufgenommen** (Entscheid Achim 07-10). Phase 2 (~23 Standalone-Libs): 13/23 verifiziert+gemergt; Rest-Kohorte in **[#987](https://github.com/achimdehnert/platform/issues/987)** (Task A: gaeb-toolkit/riskfw/weltenfw nur PR-Head-Verify; Task B: outlinefw/promptfw gated auf shared-ci#20); 5 strukturell exkludiert. Formales Phase-3-Apply-Artefakt (`wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter) **existiert noch nicht** — die 6 Live-Rulesets liefen ad-hoc außerhalb dieses Prozesses. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

> **Fortschritt 2026-07-08 (unmerged geblieben, PR #985, jetzt konsolidiert):** Phase 2 zu 13/23 verifiziert+gemergt; shared-ci#20-Blocker gefunden; Rest-Kohorte in #987 aufgeteilt (Task A/B). Details: s. Aktueller Stand.
>
> **Fortschritt 2026-07-09/10 (ABGEGLICHEN gegen #811 + Retro, 2026-07-10):** Wave-3-Ruleset live auf 6 Repos (nicht 9 — Memory-Zahl war falsch, korrigiert gegen Retro-Ground-Truth), davon 3 außerhalb der #811-Worklist (weltenhub/illustration-hub/research-hub, jetzt nachträglich aufgenommen) + Live-Incident selbst behoben; ADR-270 accepted. **Formales Phase-3-Apply-Artefakt fehlt weiterhin.** Details: s. Aktueller Stand + #811-Kommentar.
>
> **Fortschritt 2026-07-10 (NEU, offen):** weltenhub-Redis-Incident gelöst (s. Aktueller Stand). Drei Folge-Items offen, alle Human-Decision/Freigabe, keine autonome Ausführung: (1) `ausschreibungs-hub-staging` authentik-Provider/-Application vorbereitet (client_id/signing_key/scopes/redirect geklärt gegen risk-hub-Referenz-Pattern), Freigabe-Block gestellt, Session endete vor Bestätigung — nächste Session kann direkt ausführen, kein erneutes Research nötig. (2) `staging-demo.schutztat.de` DNS-Record (→178.104.184.168) — Entscheid offen. (3) "platform"-Governance-DB (`PLATFORM_DB_HOST=bfagent_db`, degradiert aifw-AI-Features) — Entscheid offen, braucht erst Konsumenten-Inventar. (4) KONZ-platform-015 liegt lokal in `platform` (untracked, main geschützt) — braucht Worktree+PR zum Mergen, dann User-Accept-Entscheid für die Empfehlungen REC-1..REC-7. (5) **Deploy-Health-Scan (session-start) fand 3 neue `failure`** auf coach-hub/trading-hub/pptx-hub, nicht triagiert — s. Aktueller Stand.

> **PR-Hygiene (erledigt 2026-07-02, Freigabe Achim):** #753 + #746 geschlossen (Duplikate von gemergtem #808) · **#760 gemergt** (Registry iil-adrfw/codeguard — Registry-Lücke zu) · **#759 gemergt** (gen_adr_index.py; Rebase-Konflikt in INDEX.md durch Generator-Lauf gelöst, 206 aktive + 48 archivierte ADRs indiziert).

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): Drift-Score live prüfen — `python3 tools/cc-skill-dist/doctor.py` (Zahl driftet mit jedem neuen/geänderten Skill, hier nicht einfrieren)

---

## 1. MCP-Server & Tool-Calls

**Claude Code (aktuell, `mcp__<server>__<tool>` Format) — wichtigste Tool-Calls:**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

**Server-Übersicht (7):**

| Server | Zweck |
|--------|-------|
| **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| **paperless-docs** | Dokumente, Rechnungen, Archive |
| **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Windsurf-Legacy (kein Coding mehr, ADR-230)

Windsurf-Agents nutzten die o. g. Server über numerische Prefixe (`mcp0_`–`mcp6_` in
derselben Reihenfolge wie oben). Seit ADR-230 wird Windsurf **nicht mehr zum Coden**
eingesetzt (nur ADR-Review-Subset) — die Prefix-Tabelle ist nur noch für das Lesen
alter Sessions/Logs relevant, kein aktives Interface mehr.

---

## 2. Hetzner Infrastructure

| Rolle | IP | User |
|-------|-----|------|
| **Prod-Server** | `88.198.191.108` | `root` (via SSH-Key) |
| **Dev-Server (WSL)** | `localhost` | `devuser` |

**Kritische Regeln:**
- `devuser` hat **KEIN sudo-Passwort** → System-Pakete: `ssh root@localhost "apt-get install -y <pkg>"`
- PROD: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **NIEMALS** `ping` für Server-Check — Hetzner blockiert ICMP. TCP-Check stattdessen.

**Secrets:**
- Lokal: `~/.secrets/` (einzige Location seit 2026-05-30 — `~/shared/secrets/` konsolidiert + leer)
- Server: `/opt/shared-secrets/api-keys.env` (chmod 600, root-only)
- Repo-spezifisch: `.env.prod` (nie in Git)

---

## 3. Deploy Targets (Prod — 88.198.191.108)

| Repo | Domain | Health |
|------|--------|--------|
| `risk-hub` | schutztat.de | https://schutztat.de/healthz/ |
| `coach-hub` | kiohnerisiko.de | https://kiohnerisiko.de/healthz/ |
| `billing-hub` | billing.iil.pet | https://billing.iil.pet/healthz/ |
| `travel-beat` | travel-beat.iil.pet | https://travel-beat.iil.pet/healthz/ |
| `weltenhub` | weltenforger.com | https://weltenforger.com/healthz/ |
| `trading-hub` | trading-hub.iil.pet | https://trading-hub.iil.pet/healthz/ |
| `cad-hub` | nl2cad.de | https://nl2cad.de/healthz/ |
| `pptx-hub` | prezimo.com | https://prezimo.com/healthz/ |
| `ausschreibungs-hub` | bieterpilot.de | https://bieterpilot.de/healthz/ |
| `dms-hub` | dms.iil.pet | https://dms.iil.pet/healthz/ |
| `wedding-hub` | wedding-hub.iil.pet | https://wedding-hub.iil.pet/healthz/ |

**Deploy-Befehl:** `bash ~/github/platform/scripts/ship.sh <repo>`
**Health-Check:** `mcp2_deploy_check(action="health", repo="<repo>")`

---

## 4. Master Repo Identifier

**Alle Repos in einer Registry** (Anzahl live: `python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`):

```bash
# project-facts.md für alle Repos generieren (nur fehlende)
python3 ~/github/platform/scripts/gen_project_facts.py

# Alle neu generieren
python3 ~/github/platform/scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 ~/github/platform/scripts/gen_project_facts.py risk-hub
```

- Registry: `platform/scripts/repo-registry.yaml`
- Output: `<repo>/.windsurf/rules/project-facts.md` (trigger: always_on)
- Läuft automatisch bei `/session-start` (Step 0.3b) und `/session-ende` (Phase 3.2)

---

## 5. CC-Skills & Windsurf Rules

**CC-Skills (primär, ADR-230):** Quelle `platform/.windsurf/workflows/` → verteilt nach `~/.claude/commands/` via `cc-skill-dist`:
```bash
python3 ~/github/platform/tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 ~/github/platform/tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf Rules** (nur ADR/Review-Subset, kein Coding mehr seit ADR-230):
- Quelle: `platform/.windsurf/rules/` + `platform/.windsurf/workflows/` (tool_targets: windsurf-review)
- Verteilen: `python3 tools/cc-skill-dist/windsurf-subset.py`

**project-facts.md** (repo-spezifisch, generiert):
```bash
python3 ~/github/platform/scripts/gen_project_facts.py          # nur fehlende
python3 ~/github/platform/scripts/gen_project_facts.py --force  # alle
```

---

## 6. GitHub

**Account:** `achimdehnert`
**MCP:** `mcp1_*` für alle GitHub-Operationen
**Reusable Workflows:** `achimdehnert/platform/.github/workflows/_ci-python.yml` etc.

**Repo-Kategorien:**
- **Django Hubs** (21): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

(Diese Kategorien sind kein vollständiges Abbild von `registry/canonical.yaml` — Gesamtzahl
live siehe oben unter §4; bei Abweichung ist die Registry maßgeblich, nicht diese Liste.)

---

## 7. pgvector Memory (Orchestrator)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (Image: `pgvector/pgvector:pg16`) |
| **Läuft auf** | Prod-Server `88.198.191.108` |
| **Port auf Prod** | `127.0.0.1:15435` (Host-Binding des Containers) |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop, User `adehnert`) |

```bash
# Status prüfen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres

# Manuell starten (ohne sudo)
ssh -N -L 15435:localhost:15435 -i ~/.ssh/id_ed25519 root@88.198.191.108 &

# Via systemd (empfohlen — Autostart bei Neustart)
sudo systemctl start ssh-tunnel-postgres
```

- **Kein Fallback auf Cascade Memory** — pgvector MUSS laufen
- Tunnel-Ziel: `remote:localhost:15435` (nicht `:5432` — der Container bindet auf 15435)
