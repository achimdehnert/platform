# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## ⚡ Aktueller Stand (2026-07-20/21 — zwei Parallel-Sessions: Mail/Postfach-Strukturierung + Tools-Strang (estimate_job-Fehldiagnose, break-glass-meter, Parallel-Session-Fixes A1/C1))

**Zwei Sessions liefen am 2026-07-20 parallel im selben Repo** (bewusster Provokations-/Härtungstest der Parallel-Session-Mechanik). Beide Stränge hier zusammengeführt — genau der A2-Deckungs-Verlust, der dabei sichtbar wurde: #1283 (Mail-Session-Handover) entstalte nur die Nächste-Schritte-Liste, schrieb aber **keinen** neuen Aktueller-Stand; der Tools-Strang fehlte danach ganz. Dieser Block schließt die Lücke sequenziell (Mail-Session war fertig → kein Parallel-Konflikt mehr).

**Strang A — Mail/Postfach (eigene Session, Memory `session:platform:20260721:mail-struct-ollama-0720`):**
- Postfach achim.dehnert@iil.gmbh strukturiert: Posteingang 2.852 → 1.461, ~1.391 Mails in 4 verifizierten Wellen (Read-back je Welle) in 3-Ebenen-Ordnermodell (kunde/partner/altkunde, Top-Level-Präfix `IIL.*`).
- Ollama auf dev (88.99.38.75) installiert: systemd, bindet **nur** 127.0.0.1:11434, Modell qwen2.5:3b, CPU. Zugriff via SSH-Tunnel.
- **Dienst H (LLM ordnet Partner-Mail dem Kundenprojekt zu) FALSIFIZIERT:** qwen2.5:3b Betreff-Klassifikation 10/10 unklar, Kundendomain in To/CC nur 9% → Partnerordner bleiben Heimat, LLM-Routing verworfen.
- Kundenmail-Draft-Stil-Korrektur (Owner, „weniger KI-like"): erster Satz = Empfehlung, keine „Warum:"-Marker, Bestätigung eingebettet → Memory `feedback_client_mail_style_no_ai_preamble`.
- **Offen:** [#1281](https://github.com/achimdehnert/platform/issues/1281) (graph_mail: `--subject` als UND-Filter zu `--move` + `--draft`-Read-back). Rest-Posteingang ~1.461 schrittweise; 2 Fach-Entwürfe (AVV/Dillingen) als Draft, Owner sendet selbst. Kunden-/Ordner-Zuordnung liegt lokal (`~/.claude/mail-folders.env`, DSGVO, nicht im Repo).

**Strang B — Tools (diese Session, reaktiv aus Session-Start-Findings):**
- **ADR-156-Fehldiagnose korrigiert ([#1278](https://github.com/achimdehnert/platform/pull/1278) gemergt):** Commit `496a35c` (04-29) erklärte `estimate_job`/`discord_notify`/`deploy_check` fälschlich für „existiert nicht mehr (Issue #80)" — reine Prefix-Drift (`mcp2_` → `mcp__orchestrator__`), die Tools leben. `/ship`+`/backup` restauriert, ADR-156 §v3.6-Nachtrag. Live-Beleg: `estimate_job(deploy, risk-hub)` liefert 135s-Schätzung.
- **verify-adr156 falsch-grün gefixt ([mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180), OFFEN — braucht `--admin`):** der Check grepte den nackten String `estimate_job` und matchte damit den Verneinungssatz → `/ship`+`/backup` ~3 Monate falsch-grün. Assertion jetzt auf Aufruf-Form `^mcp__orchestrator__estimate_job:`. **Merge blockiert:** mcp-hub hat 1 Collaborator + Ruleset „1 Approval", GitHub verbietet Self-Approval → Sackgasse, Admin-Bypass nötig (`gh pr merge 180 --admin --squash`, `[skip ci]` da deploy.yml auf push:main triggert).
- **deploy_check-Defekt getrackt ([mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181)):** Tool existiert, scheitert aber server-seitig an fehlender `ports.yaml` — echter Defekt, Server-Pfad, nicht in dieser Session gefixt.
- **break-glass-meter gebaut ([#1279](https://github.com/achimdehnert/platform/pull/1279) gemergt):** KONZ-004 (branch-protection, prod, review_by 11 Tage überfällig) hatte für seine Kill-Gate-Hälfte „≥1 Break-Glass/Woche" **kein Messinstrument** — der bestehende Meter prüft nur Ruleset-Existenz, nicht Umgehungen (`rule-suites?result=bypass`). Zähler + Workflow-Step + Label `break-glass`; Erstmessung 0 Break-Glass (falsifiziert gegen `result=pass`=11). Grenze: rule-suites ist kein Vollarchiv.
- **KONZ-002 §16 (Owner-Entscheidungen 2026-07-20, im selben PR):** (a) Kostenneutralität **Owner-attestiert** (Kriterium verlangt schriftliche GitHub-Bestätigung — Abweichung vermerkt, nicht geglättet); (b) Souveränitäts-Sign-off ttz-lif/meiki-lra **ausgesetzt** bis erste echte Kundendaten (mündliche Zusage, zustandsgebundener Wiederaufnahme-Trigger); (c) Portabilität war seit 06-03 grün (§15). Sunset-Pfad greift nach heutigem Stand nicht.
- **Parallel-Session-Fixes A1+C1 ([#1280](https://github.com/achimdehnert/platform/pull/1280) gemergt):** A1 = `session-memory` überschreibt fremde Session nicht mehr (`--session-id` macht Key eindeutig, sonst Ausweichen auf `-2`); C1 = `tools/session-leases` zeigt im Session-Start-Runner, wer parallel arbeitet. **A1 unter echter Doppellast bewiesen:** die Mail-Session nutzte auf dem frisch gemergten Code das `--session-id`-Flag → eindeutiger Key, keine Kollision.
- **Ausführungstreue-Audit [#1167](https://github.com/achimdehnert/platform/issues/1167) triagiert (Kommentar):** ADR-Seite ohne Retrofit schließbar (kein aktives Doku belegt Umsetzung — 07-09-Datum war 194-Datei-Frontmatter-Sweep, kein Aktivitätssignal); KONZ-Seite verengt auf 4 fällige review_by-Termine (alle 26 haben `kill_criteria`, es fehlt nur Status je Bedingung — Muster #1275/#1169). [#1275](https://github.com/achimdehnert/platform/pull/1275) gemergt.

**Beobachtung Parallel-Session-Mechanik (für spätere solide Lösung, KONZ-Kandidat):** A1 (Memory-Key) hat funktioniert. A2 (Handover) verlor real Deckung — nicht durch konkurrierende PRs (die verhinderte die Disziplin), sondern durch **disjunkte Handover, keiner vollständig**. Das ist „signifikant" i.S. der Beobachtungs-Ansage → solide Lösung (Handover-Fragmente je Session, beim Lesen zusammengeführt) lohnt jetzt. B1 (Merge-Lease) weiter offen.

## ⚡ Vorheriger Stand (2026-07-19 — OIDC-Publishing-Fleet-Umstieg: ADR-278 accepted, 7/7 Repos migriert, Enforcement-Gate live, #1094 geschlossen)

**Diese Session (2026-07-19, Opus):** reaktive Deploy-Triage → kompletter OIDC-Publishing-Umstieg der iil-Paket-Fleet; Owner-Block #1094 vollständig abgearbeitet + geschlossen.

- **Deploy-Triage:** billing-hub + trading-hub letzter Deploy `failure` = buildkit-Timeout auf `docker.sock` (transient, Runner-Kontention) → gestaffelter Re-Run beider, beide live. `error_pattern` geloggt (`error:self-hosted-runner:4e52af0faded`).
- **ADR-278 accepted ([#1266](https://github.com/achimdehnert/platform/pull/1266) gemergt):** iil-Pakete publizieren **ausschließlich via OIDC Trusted Publishing**; `password:`-basiertes PyPI-Publishing verboten + Enforcement-Gate `tools/check_publish_oidc_auth.py`.
- **3 Pakete live via OIDC publiziert:** iil-promptfw 0.8.1, iil-outlinefw 0.3.2, iil-weltenfw 0.4.1 (je Token→OIDC-Fix + Trusted-Publisher-Bindung).
- **7/7 Nicht-pur-OIDC-Repos umgestellt:** django-commons/aifw/learnfw (eigene publish.yml) + codeguard/ingest (zentral aus platform, [#1267](https://github.com/achimdehnert/platform/pull/1267) gemergt, Bindung auf `repo=platform`). 2 versteckte Auth-Defekte durch echtes Verifizieren gefunden+gefixt (django-commons#12, learnfw#9: `publish-pypi`-Job ohne `id-token`/`environment`). **Lehre:** id-token/environment **job-level** prüfen, nicht file-level (file-Grep zählt TestPyPI-Job mit).
- **Enforcement-Gate fleet-weit SCHARF:** shared-ci `publish-auth-guard` von warn-first auf **block** geschaltet (shared-ci#33, v1.0.14) — `continue-on-error` raus + in `gate.needs`. Alle 10 `_ci-pypi`-Consumer vorab safe-verifiziert; ein `password:`-Input im PyPI-Upload lässt `ci/gate` jetzt fleet-weit rot werden. **ADR-278-Strang damit komplett** (Regel + Detektion + Prävention scharf).
- **4 Pre-Rename-Alt-Dubletten geyankt** (aifw/promptfw/weltenfw/authoringfw) — Yank statt Delete (Name reserviert, kein Squatting). Trusted-Publisher-Bindung gehört auf **Repo-Namen**, nie Dist-Namen (`aifw`, nicht `iil-aifw`).
- **#1094 + #1265 geschlossen; [#1268](https://github.com/achimdehnert/platform/issues/1268) (Portfolio-Session) ausgelagert.** 2. Owner via per-Projekt-Collaborator (keine PyPI-Org `iil` vorhanden).
- **Memory:** MEMORY.md kompaktiert (128 Einträge, 16.9 KB); Session-Summary `session:platform:20260719` + Lehren gesichert.
- **Handover-Hygiene:** stale/konfliktbehafteter Handover-PR #1171 (07-16-Stand, „alles gemergt") geschlossen — dieser 07-19-Stand ersetzt ihn.

*(Zwischen 07-15 und heute, nicht in diesem Handover detailliert: 07-16 `/repo-optimize`-Vollzyklus (alles gemergt), 07-18 graph-mail-move-folder.)*

### ⚡ Abend-Session 2026-07-19 (Opus, dritte Session des Tages) — #1167-Umsetzung + Review-Stau vollständig entrotet

- **#1167 Ausführungstreue — Umsetzungsschritt geliefert ([#1275](https://github.com/achimdehnert/platform/pull/1275), offen):** geerdete Kriterium→Status-Tabellen (Muster #1169/#1170) für **KONZ-001** (pilot, review 07-20; Kill-Gate a–e: **1/5 erfüllt**, 4/5 offen-teilweise) und **KONZ-004** (prod; REC-2/REC-5 via ADR-242 live erfüllt, REC-1/REC-4/Kill-Gate-Messung/Rollback offen). **Korrektur am 07-19-Vormittags-Befund:** KONZ-016 ist **kein** Fix-Kandidat (hat bereits Decision-Ledger mit Status-Spalte — der Befund zählte nur `- [ ]`-Checkboxen); KONZ-018 bewusst ausgelassen (maschinen-`kill_criteria` + W2-5-Reminder-Issue = designierter Tracker, In-Doc-Tabelle wäre Doppelquelle). Beides durabel im #1167-Kommentar.
- **🌀 Systemischer ADR-validate-Blocker gefunden + gefixt ([#1276](https://github.com/achimdehnert/platform/pull/1276) GEMERGT):** 6 aktive ADRs (146/261/262/263/267/277) trugen deprecated Frontmatter-Keys (`date`→`decision_date`, `decision-makers`→`deciders`, `relates_to`→`related`, `review`→`review_status`). Weil `iil-adrfw validate docs/adr/` **alle** ADRs scannt, rötete **ein einziges** Alt-Key-ADR **jede** ADR-berührende PR. Reine KONZ-/Doc-PRs waren wegen Pfad-Filter nicht betroffen → fiel lange durch. Verifiziert `224/224`→`225/225`. Memory `reference_adr_frontmatter_schema_strict` korrigiert (listete `date`/`decision-makers` fälschlich als *erlaubt*) + 🌀-markiert.
- **ADR-272-Nummernkollision aufgelöst:** zwei **verschiedene** ADRs beanspruchten 272. `ADR-272-distribution-contract` liegt auf main → [#1086](https://github.com/achimdehnert/platform/pull/1086) behält 272; der promptfw-Text-Loop in [#1077](https://github.com/achimdehnert/platform/pull/1077) auf **ADR-279** umnummeriert (Datei+`id:`+H1, INDEX per `gen_adr_index.py` regeneriert = löste zugleich den Merge-Konflikt). `adr_open_pr_guard.py` hat die Kollision korrekt gefangen — das Gate funktioniert.
- **Review-Stau: 0 rote PRs übrig** (vorher 6). Gemergt: #1027 + #1026 (waren approved+grün, nur ungemergt). Grün gezogen: #1112 (stale ADR-INDEX), #1231 + #1141 (Symptom des #1276-Blockers, **nicht** stale-Index — Erst-Diagnose war falsch), #1086 + #1077 (Kollision), #1225 (`context-review` 503 = transient; der base64-Log-Blob war nur die HTML-Fehlerseite). **8 PRs mit Auto-Merge gequeued** — laufen bei Approval durch.
- **Engpass-Befund:** ~33 der ~40 offenen platform-PRs sind CI-grün und warten ausschließlich auf den 2.-Owner-Review. Der Stau ist ein **Review-Durchsatz**-Problem, kein technisches.


## Nächste Schritte (kompakt)

1. trading-hub Branch-Protection [#1117](https://github.com/achimdehnert/platform/issues/1117) — bewusst zurückgestellt (App-Repo-Scope), weiterhin offen
2. **Review-Durchsatz (größter Hebel):** ~29 offene platform-PRs sind CI-grün und warten nur auf den 2.-Owner-Review; ~10 davon mit Auto-Merge gequeued, 0 rote PRs. 2. Owner (`wirdigital`) baut den Stau aktiv per Hand ab (14 Merges am 2026-07-20). → [PR-Liste](https://github.com/achimdehnert/platform/pulls)
3. Ausführungstreue-Audit [#1167](https://github.com/achimdehnert/platform/issues/1167): Umsetzungsschritt gemergt ([#1275](https://github.com/achimdehnert/platform/pull/1275)). Rest-Strang offen: „lügender Index" ADR-072 + ADR-158 (Tabelle vorhanden, aber veraltet — Nachzieh-Welle wie #1170, Owner-Entscheid; **nicht verifiziert**, Stand aus Memory 07-19); Nebenfund Namenskollision KONZ-platform-001 weiterhin offen
4. KONZ-018 W1: testkit-Dedup, Freshness-Pilot promptfw
5. Stub-Issues via Sonnet-Session (`/model sonnet` + `/issues-offen`)

> **Erledigt 2026-07-20/21 (Tools-Strang + Mail, 2 Parallel-Sessions):** [#1278](https://github.com/achimdehnert/platform/pull/1278) (estimate_job-Fehldiagnose) · [#1279](https://github.com/achimdehnert/platform/pull/1279) (break-glass-meter, KONZ-004) · [#1280](https://github.com/achimdehnert/platform/pull/1280) (A1 Memory-Key + C1 Lease-Sicht) · [mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181) (deploy_check-Defekt getrackt) · Mail-Postfach strukturiert + Ollama-on-dev + Dienst-H falsifiziert ([#1281](https://github.com/achimdehnert/platform/issues/1281) offen). **Offen:** [mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180) braucht `--admin`-Merge (Self-Approval-Sackgasse).
> **Erledigt 2026-07-20:** [#1275](https://github.com/achimdehnert/platform/pull/1275) GEMERGT (Ausführungstreue-Umsetzung, KONZ-001+004 Kriterium→Status-Tabellen) · [#1115](https://github.com/achimdehnert/platform/issues/1115) GESCHLOSSEN (usage-sweep: Labels behalten, 36 Skills zurückgebaut via #1257, 3 sunset-reife Skills source- **und** dist-seitig entfernt; Kill-Kriterium *nicht* erfüllt → Sweep läuft weiter) · [#1271](https://github.com/achimdehnert/platform/issues/1271) GESCHLOSSEN (cc-skill-dist DRIFT-SCORE 44→0; alle 35 Orphans durch den einen Rückbau-Commit `cfa9c0f` erklärt, Zweitquellen-Hypothese falsifiziert). **Methodik-Auflage nächster Sweep:** „keine kanonische Source" ist **kein** Tot-Signal — trifft auch frisch zurückgebaute Skills; Status steckt im löschenden Commit (`doctor.py --kind commands` + Orphan↔Commit-Diff vor Teardown).
> **Erledigt 2026-07-19:** Owner-Block #1094 komplett + geschlossen (7/7 OIDC-Bindungen, 3 Pakete live, 4 Alt-Dubletten geyankt, 2. Owner) · ADR-278 accepted (#1266) · codeguard/ingest OIDC (#1267) · django-commons#12 + learnfw#9 Auth-Fixes · shared-ci publish-auth-guard v1.0.13 · #1265 zu, #1268 (Portfolio) ausgelagert · Handover-PR #1171 (stale) geschlossen · **Guard Block-Flip scharf** (shared-ci#33) + v1.0.14 fleet-weit gebumpt (promptfw#32/outlinefw#19) → ADR-278-Enforcement komplett.
> **Erledigt 2026-07-19 (Abend-Session):** #1167-Umsetzungsschritt geliefert (#1275: KONZ-001 + KONZ-004 Kriterium→Status-Tabellen; KONZ-016/018 begründet ausgelassen) · **#1276 GEMERGT** — systemischer ADR-Frontmatter-Blocker (6 ADRs, deprecated Keys) fleet-weit gefixt, `validate` 225/225 · ADR-272-Nummernkollision gelöst (#1077 → ADR-279 umnummeriert, #1086 behält 272) · **Review-Stau von 6 auf 0 rote PRs** (#1027/#1026 gemergt; #1112/#1231/#1141/#1086/#1077/#1225 grün gezogen). **Lehre:** „stale-Index" war bei #1231/#1141 die *falsche* Erst-Diagnose — echter Root-Cause war der repo-weite Schema-Verstoß; ein Log-Blob (base64-HTML) verdeckte bei #1225 einen simplen transienten 503.
> **Erledigt 2026-07-19 (Session-Start-Folgesession):** #1268 geschlossen (Portfolio: alle 6 Pakete behalten) · #1158 geschlossen (`secrets:inherit`: coach-hub bereits auf origin/main gefixt, risk-hub **False Positive** — same-org `iilgmbh` + keine private git-Dep) · #1115 Sweep-Entscheid (Labels behalten; Skill-„tot"-Signal via cc-skill-dist-Drift widerlegt → #1271) · #1167 Stichproben-Audit fortgesetzt (~8 Fix-Kandidaten). **Lehre:** #1 (Guard) + coach-hub-Teil von #2 waren bereits erledigt — nur sichtbar durch konsequente origin/main- statt lokale-Klon-Prüfung.
> **Erledigt 2026-07-18 (Session-Start-Reconciliation, keine neue Arbeit):** Orchestrator-MCP wieder funktional — „Invalid Bearer Token" nicht mehr reproduzierbar, live verifiziert per 3 erfolgreichen Tool-Calls (`agent_memory_search` + `check_recurring_errors` + Outline-Search) am 2026-07-18; Ursache des Wieder-Funktionierens unbekannt (nicht untersucht) · Haupt-Retro [#1162](https://github.com/achimdehnert/platform/pull/1162) ist MERGED + APPROVED (war als „offen" geführt, Handover war stale).
> **Erledigt 2026-07-15:** cad-hub#42 (war schon vor Session-Start gemergt, Handover war stale) · trading-hub#150 · coach-hub#40 · ADR-270-Vorbedingung (#1152) · Increment-Retro (#1165) · session-start-Checkliste-Nachbesserung (#1166).
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
