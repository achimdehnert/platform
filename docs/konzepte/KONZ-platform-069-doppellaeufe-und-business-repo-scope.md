---
concept_id: KONZ-platform-069
title: Deploy-Doppelläufe vermeiden und Sitzungs-Scope über Business-Repos begrenzen
pipeline_status: idea
tier: T3                   # Cross-Repo (shared-ci + ~23 Hub-Aufrufer), neue Boundary (Sitzung ↔ Business-Repo), Security-Perimeter (Workflow-Permission, PreToolUse-Deny)
owner: Achim Dehnert
spec_refs: []              # kein Klickdummy/Spec-Bezug — Betriebs- und Sitzungsregeln, keine ADR-211-Anwendung
adr_threshold: Amendment   # Teil B = Amendment an ADR-233 (Lease bekommt Scope-Bedeutung); Teil A = shared-ci-Änderung nach bestehendem Muster, kein ADR
review_by: 2027-01-15
kill_criteria: "A: Treten nach Rollout auf den zwei Pilot-Hubs bis 2026-12-15 weiterhin Prod-Doppeldeploys desselben SHA auf ODER wird ein nötiger Deploy fälschlich übersprungen (≥1 belegter Fall) → Teil A zurückbauen. B: >3 Fehlblockaden je 14 Tage ODER >5 Owner-Freigaben je Woche im Pilot bis 2026-12-15 → B3 auf advisory zurückstufen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "iilgmbh/ausschreibungs-hub Runs 38282397112 (push) + 38282431677 (workflow_dispatch), Commit 5e047b2", commit_or_pr: "platform#3812 Kommentare 6140343708, 6140440632", opened_in_session: true}
  - {claim_id: C2, source_path: "iilgmbh/ausschreibungs-hub .github/workflows/deploy.yml (concurrency Z.17–18, Dispatch-Default, Job-Übergabe target_environment, Pin Z.111)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C3, source_path: "iilgmbh/shared-ci .github/workflows/_deploy-unified.yml (permissions Z.12–14, resolve Z.108, deploy-staging concurrency Z.263–265, deploy-production concurrency Z.365–367)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C4, source_path: ".windsurf/workflows/ship.md (Schritt 2 push, Schritt 3 gh workflow run … production, ~Z.130–165)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C5, source_path: ".github/workflows/runner-health.yml (Z.170–186: cancel statt force-cancel, sleep 3, Redispatch deploy.yml)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C6, source_path: "tools/deploy_config_lint.py + .github/workflows/deploy-config-lint.yml (workflow_call)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C7, source_path: "Pins _deploy-unified über lokale Klone ~/github/*/.github/workflows/*.yml (13× v1.1.20, 3× v1.1.12, je 2× v1.1.24/v1.1.10/v1.0.11, je 1× v1.1.25/v1.1.13/v1.1.11/v1/main)", commit_or_pr: "Stand lokaler Klone 2026-10-13", opened_in_session: true}
  - {claim_id: C8, source_path: "registry/canonical.yaml (69 repos-Einträge, 31 mit domain, 38 ohne — u. a. meiki-hub, ttz-hub, buerger-hub, Bibliotheken; owner_prefix_rules + Overrides)", commit_or_pr: "origin/main 2026-10-13", opened_in_session: true}
  - {claim_id: C9, source_path: "tools/repo-session.sh (Lease-Felder Z.38–45 inkl. claude_session; start = ein Repo je Aufruf, usage Z.635)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C10, source_path: "tools/claude-hooks/block_direct_pr_merge.py (owner_texte Z.105–142 mit origin.kind human; ziel() Z.170)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C11, source_path: "tools/claude-hooks/scope_checkpoint_scanner.py (_repo_aus_pfad Z.260, _repos_aus_kommando Z.286; Stop-Hook, ab drittem Repo/Prod)", commit_or_pr: "7ac6f421", opened_in_session: true}
  - {claim_id: C12, source_path: "~/.claude/settings.json hooks: PreToolUse-Matcher nur Agent + Bash (15 Hooks), SessionStart 6, Stop 6", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C13, source_path: "~/.claude/policies/autonomy-gates.md Gate 4 Scope-Eskalation (Z.143–144: drittes Repo)", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C14, source_path: "Sitzungstranskript ausschreibungs-hub 753c6f03 (17:09:50 merge, 17:10:11 reject alter Lauf, kein Dispatch; billing-hub#83 gemergt; Checkpoint 17:10:48)", commit_or_pr: "lokal, nicht im Repo", opened_in_session: true}
  - {claim_id: C15, source_path: "Teilagenten-Funde: risk-hub ci.yml:13 nutzt deploy-config-lint mit Ausnahme-Marker deploy.yml:106; mcp-hub-Erzeuger deployment_mcp github_actions_tools.py:263, orchestrator telegram dispatcher.py:168", commit_or_pr: "Lauf 2026-10-13", opened_in_session: false}
created: 2026-10-13
---

# KONZ-platform-069 — Deploy-Doppelläufe vermeiden und Sitzungs-Scope über Business-Repos begrenzen

> **Auftrag (Owner-Wort 2026-10-13, Kapitäns-Sitzung):** „erstelle ein konzept wir wir sicherstellen
> dass "Doppelläufe" vermieden werden, sitzungen, die in "business-repos" starten dürfen nur durch
> owner erlaubnis änderungen an weiteren "Business-repos" -> z.b. writing-hub, cad-hub; eine sitzung
> kann auch mit mehrerer "business-repos" starten, dann ist dies ok"
>
> **Tier T3.** Das Konzept trifft drei Auto-Eskalations-Trigger: Es ist Cross-Repo (shared-ci und rund
> 23 Hub-Aufrufer), es zieht eine neue Grenze (Sitzung ↔ Business-Repo), und es berührt den
> Security-Perimeter (Workflow-Permission `actions: write`, ein PreToolUse-Deny). **Keine Umsetzung**:
> Das Dokument schlägt vor und schneidet die Schritte.
>
> Evidenz: `E2` = Datei in dieser Sitzung geöffnet, `E3` = Run/Issue in dieser Sitzung geöffnet,
> `H` = nicht selbst geprüft, `D` = Design-Setzung mit Alternative in §8.

## 1 Executive Summary

**Kernthese:** Beide Probleme werden beim **Empfänger** gelöst, nicht bei jedem Erzeuger.
Doppelläufe stoppt ein Deploy, der vor dem Ausrollen den **Ist-Stand des Hosts** prüft und nach
Erfolg gleichartige wartende Läufe abräumt. Fremde Business-Repos schützt ein PreToolUse-Hook, der
den Sitzungs-Scope aus den **vorhandenen Leases** und den **getippten Owner-Nachrichten** liest,
ohne neue Scope-Datei.

| Teil | Was | Wirkt gegen | Kosten |
|---|---|---|---|
| A1 | Prüfung im Prod-Job: Host schon auf Ziel-SHA → no-op | jeden Doppellauf, egal welcher Erzeuger | shared-ci-Tag + Pin-PR je Hub |
| A2 | Nach Erfolg: wartende Läufe mit gleichem SHA + Umgebung force-cancel | den zweiten Gate-Klick (F1) | `actions: write` in shared-ci und Aufrufern |
| A3 | Concurrency-Fallback = Job-Fallback in den Hubs | Läufe in verschiedenen Gruppen | eine Zeile je Hub |
| A4 | `/ship` Schritt 3 streichen, runner-health auf force-cancel | zwei bekannte Erzeuger | zwei kleine PRs in platform |
| B1 | Feld `sitzungs_klasse` in `registry/canonical.yaml` + Vollständigkeits-Lint | unklare Grenze | 69 Zeilen einmal füllen |
| B2 | Scope = Repos der Leases dieser Claude-Sitzung + Owner-Freigaben `scope +<repo>` | — (Datenquelle) | Mehrrepo-Start im Skill |
| B3 | PreToolUse-Guard, Deny nur auf sicher erkannte Schreibwege | Schreiben in fremde Business-Repos | ein Hook, ein Selbsttest |

## 2 Scope & Evidenzbasis

**Im Scope:** Prod-Deploys über `iilgmbh/shared-ci/_deploy-unified.yml` (alle Hub-Deploys) und
Claude-Code-Sitzungen auf dem Arbeitsplatz des Owners.
**Nicht im Scope:**
- Staging-Doppelläufe. Die bricht `cancel-in-progress: true` schon ab (C3).
- Windsurf-Sitzungen.
- Remote-Agenten ohne lokale Hooks (§6, Lücke L6).
- Die Frage, ob push→main nach Prod oder nach Staging gehört (§5 A5, Owner-Entscheid).

**Realfall Doppellauf (E3, C1):** ausschreibungs-hub, Commit 5e047b2, 2026-10-12.
- Run 38282397112 (push, 17:10:00Z) und Run 38282431677 (workflow_dispatch, 17:10:17Z) liefen gleichzeitig.
- Der Owner gab das Gate am Dispatch-Lauf frei. Der Push-Lauf rückte danach ans Gate nach.
- Er hätte denselben SHA ein zweites Mal ausgerollt. `gh run cancel` blieb zweimal ohne Wirkung, erst `force-cancel` beendete ihn.
- Zweiter Datenpunkt laut #3812: pptx-hub am 2026-10-07 (H, nicht neu geöffnet).

**Erzeuger von Deploy-Läufen:**

| Erzeuger | Beleg | Status |
|---|---|---|
| push-Trigger in `deploy.yml` der Hubs | C2 | E2 |
| `/ship` Schritt 3 dispatcht Prod direkt nach dem Push aus Schritt 2 | C4 | E2 |
| runner-health: Cancel hängender Läufe + Redispatch | C5 | E2 |
| deployment-mcp `cicd_manage dispatch`, Orchestrator-Telegram `trigger_deploy` | C15 | H |
| Actions-UI „Run workflow" | — | H |

**Ursache des Doppellaufs im Realfall (E2, C2, C3):** Der push-Lauf deployt nach Prod, sitzt aber
in der Concurrency-Gruppe `…-staging`. Grund: Der Workflow-Fallback ist `'staging'`, der
Job-Fallback `'production'`. Der Dispatch-Lauf sitzt in `…-production`, also serialisiert nichts
die beiden. Und selbst in einer gemeinsamen Gruppe hält nichts einen zweiten Lauf desselben SHA auf.
`_deploy-unified.yml` kennt keine Prüfung auf „schon deployt" (C3).

**Wer am 12.10. um 17:10:17 dispatchte, ist offen (H).** Die mergende Sitzung war es nicht (C14).
Für die Gegenmaßnahme spielt das keine Rolle, weil A1/A2 beim Empfänger greifen.

**Realfall Scope (E2, C14):** Eine Sitzung, gestartet in ausschreibungs-hub, mergte auch
billing-hub#83. Den Scope-Checkpoint legte sie erst 38 s danach ab. Der bestehende Stop-Hook
(C11) meldet erst ab dem **dritten** Repo und erst **nach** dem Schritt. Gate 4 der Autonomie-Policy
sagt dasselbe (C13). Der Auftrag verlangt: schon das **zweite** Business-Repo, und **vorher**.

## 3 Infrastruktur-Fit

- **shared-ci `_deploy-unified.yml`** (C3): Gemeinsamer Ablauf mit den Jobs resolve → build →
  deploy-staging | deploy-production. Prod hat `concurrency … cancel-in-progress: false` und das
  Environment-Gate. Die Permissions sind nur auf Workflow-Ebene erlaubt (Kommentar Z.6–8) und heute
  `contents: read, packages: write`. Eine Runs-Abfrage oder ein Cancel braucht `actions: read/write`,
  in shared-ci **und** in jedem Aufrufer.
- **Pin-Lage (C7):** 23 Aufrufer auf 10 verschiedenen Ständen, der neueste Tag (v1.1.25) nur in
  ausschreibungs-hub. **Eine Änderung in shared-ci wirkt erst, wenn der Hub-Pin nachzieht.** Das
  ist der eigentliche Preis von Teil A.
- **Leases (C9, ADR-233):** Jede `repo-session.sh start` legt eine Lease mit `repo` und
  `claude_session` an. Damit lässt sich die Frage „welche Repos hat diese Claude-Sitzung geöffnet"
  heute schon beantworten. Ein neuer Speicher ist nicht nötig.
- **Owner-Texte (C10):** `owner_texte()` liest getippte Owner-Nachrichten aus dem Transkript
  (`origin.kind == "human"`). Der Merge-Guard nutzt das schon für `OWNER_WORT`. Freigaben aus
  dieser Quelle kann der Agent nicht selbst erzeugen.
- **Hooks (C12):** PreToolUse hängt heute nur an `Bash` und `Agent`. Ein Guard auf `Edit`/`Write`
  wäre der erste seiner Art.
- **Registry (C8):** `registry/canonical.yaml` ist die SSoT der Repos. `domain` fehlt aber bei 38
  von 69 Einträgen und ist Katalog-Taxonomie, keine Rechtegrenze. Für meiki-lra/ttz-lif gibt es
  `owner_prefix_rules` und Overrides.

## 4 Steelman

**Status quo bei A:** Der Doppellauf ist selten (zwei Datenpunkte), und das Environment-Gate
fängt ihn ab. Der Owner sieht einen zweiten wartenden Lauf und lehnt ab. Das stimmt nur halb:
Im Realfall wäre der zweite Lauf nach der ersten Freigabe am Gate stehen geblieben, und jede
weitere Freigabe hätte ihn ausgerollt. `gh run cancel` meldet Erfolg ohne Wirkung. Das Gate ist
eine Bremse, aber eine, die den Owner zweimal klicken lässt und beim zweiten Klick nichts prüft.

**Status quo bei B:** Der Stop-Hook (C11) plus Hausregel „drittes Repo" haben den Realfall
gesehen und einen Checkpoint erzwungen. Mehr Vorab-Sperre heißt mehr Owner-Klicks, gegen das
Owner-Wort „Approval-Last aktiv verringern" (2026-10-05). Auch das trägt: Eine Sperre lohnt sich nur,
wenn sie selten feuert und dann recht hat. Daraus folgt die Staffelung in B3: Deny nur dort, wo das
Ziel-Repo sicher erkannt ist.

**Was am Entwurf am stärksten trägt (Steelman-Agent):** Die Empfänger-Prüfung deckt alle
Erzeuger ab, auch den unbekannten, ohne ihn zu finden. Und der Scope aus Leases plus Owner-Texten
braucht keinen Zustand, den der Agent fälschen könnte.

## 5 Konzeptdefinition

### Teil A — Doppelläufe

**A1 Ist-Stand-Prüfung im Prod-Job (D).** Der erste Schritt in `deploy-production`, also nach
dem Gate und unmittelbar vor dem Ausrollen: Den laufenden Image-Tag bzw. SHA am Host lesen. Ist er
gleich dem Ziel-SHA und ist weder `erneut: true` noch `image_tag_override` gesetzt, beendet sich
der Job erfolgreich als no-op. Er schreibt dann eine Notice und eine Job-Summary-Zeile
„Doppellauf: Host bereits auf <sha>, kein Deploy".
- Die Prüfung misst den **Zustand**, nicht den Lauf-Status. Ein abgelehnter oder abgebrochener
  Vorläufer kann deshalb keinen nötigen Deploy verhindern (Diabolus 1).
- Ein Roll-forward nach Rollback wird nicht geblockt, weil der Host dann einen anderen Stand hat
  (Diabolus 2).
- Ein Re-Deploy desselben SHA, etwa nach einer Secret-Änderung, geht über `erneut: true`.

**A2 Nachräumen nach Erfolg (D).** Letzter Schritt in `deploy-production` nach erfolgreichem
Deploy und Health-Check:
1. Läufe derselben Workflow-Datei mit gleichem `head_sha` im Zustand `waiting` oder `pending` abfragen.
2. Für `waiting`-Läufe mit `pending_deployments` die Umgebung lesen und nur `production` nehmen.
3. Diese Läufe per `force-cancel` beenden und den Status nachmessen.

Das erspart im Realfall den zweiten Gate-Klick. Preis: `actions: write` in shared-ci und
in jedem Aufrufer. Das ist eine Security-Config-Änderung und braucht ein Owner-Go (Gate 3).

**A3 Concurrency-Fallback angleichen.** In jedem Hub, dessen Workflow- und Job-Fallback
auseinanderlaufen (Realfall C2): gleicher Ausdruck in beiden. Allein verhindert das keinen
Doppellauf (Steelman 2), der zweite reiht sich nur ein. Zusammen mit A1 aber garantiert es, dass
der zweite Lauf **nach** dem ersten an die Ist-Stand-Prüfung kommt und sie dann no-op findet.

**A4 Zwei bekannte Erzeuger abstellen.**
- `/ship` Schritt 3 wird zu: „Läuft ein Deploy aus dem Push, dessen Gate freigeben, nicht neu dispatchen" (C4).
- runner-health nutzt `force-cancel` statt `cancel` und misst den Status nach (C5). Das vermeidet den Stillstand aus Diabolus 4.

**A5 Owner-Entscheid, nicht Teil dieses Konzepts.** Zwei Org-Standards widersprechen sich.
`deploy-config-lint` (C6) verlangt push→staging und kennt eine Ausnahme-Marke (risk-hub, C15/H).
ausschreibungs-hub nennt push→prod mit Gate „Org-Standard". A1–A3 wirken in beiden Varianten.
Die Lint-Regel für A3 wird erst geschrieben, wenn A5 entschieden ist (Maintainer 2).

### Teil B — Sitzungs-Scope über Business-Repos

**B1 Klassifikation: neues Feld in der SSoT (D).** `registry/canonical.yaml` bekommt je Eintrag
`sitzungs_klasse: business | plattform | bibliothek`.
- **Plattform:** platform, dev-hub, mcp-hub, chat-hub, shared-ci u. a.
- **Bibliothek:** *fw, iil-*, testkit u. a.
- **Business:** alle Fach-Apps inkl. meiki-lra/ttz-lif.

Der bestehende Registry-Lint prüft Vollständigkeit: Ein Eintrag ohne Feld ist ein Fehler. Der
Erstbefüllungs-Vorschlag kommt aus `type`, `domain` und `owner_prefix_rules`, die 69 Zeilen prüft
der Owner einmal. **Kein zweiter Ort:** Die generierte `registry/repos.yaml` erbt das Feld. Repos,
die nicht in canonical stehen, gelten als `unbekannt` → advisory, kein Deny (Maintainer 5).

**B2 Sitzungs-Scope ohne neuen Speicher.** Der Scope einer Claude-Sitzung setzt sich zusammen aus:
1. **Start-Menge** = `repo` aller Leases mit `claude_session == <diese Sitzung>` (C9). Ein
   Mehrrepo-Start ist damit nur der Skill-Teil `/session-start writing-hub cad-hub`, der
   `repo-session.sh start` je Repo aufruft. Das deckt „startet mit mehreren Business-Repos, dann ok".
2. **Freigaben** = Zeilen `scope +<repo>` aus getippten Owner-Nachrichten (C10). Gezählt wird nur
   eine Zeile, die genau so beginnt, außerhalb eingefügter Blöcke (Diabolus 12).
3. **Start-Repo** = Repo der ersten Lease dieser Sitzung, sonst Git-Root des ersten Transkript-cwd
   (H). Es wird nicht bei compact/clear neu gesetzt (Diabolus 8).

**B3 PreToolUse-Guard `business_scope_guard.py`.** Er greift nur, wenn das Start-Repo `business` ist.
Startet die Sitzung in platform/dev-hub, gilt weiter der Drittes-Repo-Checkpoint (C11).

| Weg | Ziel-Repo aus | Wirkung bei fremdem Business-Repo |
|---|---|---|
| Edit / Write / NotebookEdit | Git-Root des Pfads | **deny** |
| `git commit`, `git push` (auch `-C`, URL-Ziel) | Git-Root bzw. Remote-URL | **deny** |
| `gh pr create\|merge\|review`, `gh workflow run`, `gh release` | `-R` bzw. cwd-Remote | **deny** |
| `gh api` mit Methode ≠ GET oder `-f/-F` ohne `-X GET`, `graphql` mit mutation | Pfad `repos/<o>/<r>` | advisory + Journal |
| `gh issue create\|comment` | `-R` | erlaubt; deny nur mit Automatik-Label (`auto`, Diabolus 9) |
| MCP-Schreibwerkzeuge (github, orchestrator `run_git`/`run_command_safe`, deployment `cicd_manage`) | Argumente | advisory + Journal (H: Toolnamen) |
| Lesen jeder Art | — | frei |

Die Deny-Meldung enthält die kopierfertige Owner-Zeile `scope +<repo>`. Die Repo-Auflösung wird aus
`scope_checkpoint_scanner.py` in ein gemeinsames Modul gezogen (`_repo_aus_pfad`,
`_repos_aus_kommando`, `ziel()`), sodass Scanner und Guard dasselbe sehen (Diabolus 10).

**B4 Selbsttest statt Melder.** Eine SessionStart-Prüfung meldet „business_scope_guard nicht
verdrahtet", wenn der Eintrag in `~/.claude/settings.json` fehlt. Das Wiring geschieht je Maschine
von Hand (Maintainer 7). Der Guard schreibt jede Deny-, Advisory- und Freigabe-Zeile nach
`~/.repo-session/melder/business_scope.jsonl`. Gelesen wird die Datei **einmal** zum
Kill-Gate-Termin, nicht bei jedem Start (Maintainer 4).

**B5 Hausregel und Policy (Vorschlag, nicht selbst geändert, Charta Art. 3).**
- `~/.claude/CLAUDE.md` „Scope-Checkpoint" und `autonomy-gates.md` Gate 4 bekommen den Satz:
  „Sitzung mit Business-Start-Repo: schon das zweite Business-Repo braucht `scope +<repo>`."
- Änderung nur mit Owner-Wort.

### Step 2a — Ausführungsform

Frage 1 beendet beide Teile: A1, A2 und B3 sind je **ein** Prüfschritt an einer festen Stelle,
kein Ablauf mit Verzweigung. Es gibt keine Schleife. Einzige Wiederholung ist das Nachmessen nach
force-cancel, und das hat ein messbares Ende (`status == completed`, höchstens 3 Versuche).

## 6 Adversariale Analyse (Synthese der drei Agenten)

Drei unabhängige Agenten (Steelman, Advocatus Diabolus, Maintainer 2028) prüften den Entwurf v0.
Der Entwurf v0 hatte eine Prüfung im Resolve-Job auf Lauf-Status, eine eigene Scope-Datei, das
Feld `domain` als Grenze und einen Melder.

**Konfliktmatrix (belegte Dissense):**

| # | Frage | Steelman | Diabolus | Maintainer 2028 | Auflösung hier |
|---|---|---|---|---|---|
| K1 | Wo prüft A1? | Resolve-Job genügt, deckt F1 | Resolve prüft Stunden vor dem Gate: abgelehnter Vorläufer → keiner deployt | — | **Diabolus.** Prüfung im Prod-Job auf Host-Zustand (A1) |
| K2 | Wirkt „Schutz am Empfänger" wirklich zentral? | ja, ein Ort | nein: Pins + fehlende `actions`-Permission → PR je Hub | nein: 10 Pin-Stände, Dependabot hebt nicht (H) | **Diabolus/Maintainer.** Rollout offen als Preis, Pin-Zähler im Kill-Gate |
| K3 | Concurrency-Fallback (A2 alt) | streichen, verhindert nichts | — | Lint vertagen, Hub-Fix direkt | **Behalten als A3**, weil erst die gemeinsame Gruppe A1 die Reihenfolge sichert. Lint vertagt |
| K4 | Scope-Speicher | Owner-Texte im Transkript, keine Datei | Datei neben Leases = Doppelquelle | in die Lease schreiben | **Beides ohne neue Datei.** Start-Menge aus Leases (Feld `claude_session` existiert), Freigaben aus Owner-Texten |
| K5 | Business-Grenze | `domain` + Ausnahmeliste | `domain` fehlt bei 38/69, keine Rechtegrenze | `domain` Freitext, als Enum linten | **Diabolus.** Eigenes Feld `sitzungs_klasse` mit Vollständigkeits-Lint (B1) |
| K6 | Schärfe von B3 | deny nur sichere Wege | viele Lücken, B4 als Pflicht-Abgleich | schmal halten, B4 streichen | **Steelman/Maintainer.** Deny schmal, Rest advisory. Lücken offen benannt (unten) |
| K7 | Messung | Notice zählen | Runs-API kennt keine Inputs, „fälschlich geskippt" nicht messbar | Melder ohne Leser, streichen | **No-op-Notice + Job-Summary** als Zählgröße, einmal zum Termin ausgewertet. „Fälschlich" = Host nach Lauf ≠ main, messbar per `deploy_wirkung.py` |

**Bekannte Lücken von B3, bewusst offen (Diabolus 7):**
- L1: Klon nach `/tmp` bzw. `~/sandbox-laeufe` und Schreiben von dort.
- L2: Python-/Shell-Skripte, die selbst `gh`/`git` aufrufen.
- L3: `bash -c` mit zusammengesetzten Strings.
- L4: neue Sitzung `cd ~/github/cad-hub && claude -p`, die eine eigene Start-Menge hat.
- L5: `gh api graphql` über Variablen.
- L6: Remote-Agenten ohne lokale Hooks.

Begründung: B3 schützt gegen **Drift** eines loyalen Agenten (Charta Art. 7/8), nicht gegen einen
Angreifer. Wer eine dieser Lücken nutzt, umgeht absichtlich. Das ist ein Charta-Verstoß und bleibt
nach dem Ereignis sichtbar: Commits und PRs tragen den Actor, ein späterer Abgleich ist als H in §12
vorgemerkt.

## 7 Deep-Dive

**A1 am Realfall:**
1. Push-Lauf P (17:10:00) und Dispatch-Lauf D (17:10:17) liegen nach A3 beide in
   `deploy-<app>-production`.
2. Der Owner gibt D frei. D prüft, der Host steht auf dem alten SHA, also rollt D aus und meldet Erfolg.
3. A2 findet P (gleicher SHA, `waiting`, Umgebung production) und beendet ihn per force-cancel. Status nachgemessen.
4. Ohne A2, etwa wenn die Permission verweigert wird, wartet P weiter. Gibt der Owner P frei, findet A1 den Host auf dem Ziel-SHA und meldet no-op. Kein zweiter Rollout.

**A1 Gegenprobe Rollback:** Ein Rollback per `image_tag_override` überspringt die Prüfung. Ein
späterer Roll-forward auf main findet den Host auf dem Rollback-Stand ≠ main und rollt aus. Richtig.

**A1 Gegenprobe abgelehnter Vorläufer (Diabolus 1):**
1. P wird abgelehnt, D wartet.
2. Bei D-Freigabe zeigt der Host den alten SHA, also rollt D aus.
3. Kein Lauf hat einen anderen wegen eines Status übersprungen, also fehlt kein Deploy.

**B3 am Realfall C14:**
1. Die Sitzung startete in ausschreibungs-hub (business). Ihre Start-Menge war {ausschreibungs-hub}.
2. `gh pr merge 83 -R iilgmbh/billing-hub` → `ziel()` liefert billing-hub (business, nicht in der Menge) → deny.
3. Die Meldung lautet „Owner-Zeile: `scope +billing-hub`". Der Owner tippt die Zeile, der nächste Versuch läuft durch.

**B3 Gegenprobe Mehrrepo-Start:** Mit `/session-start writing-hub cad-hub` entstehen zwei Leases
mit derselben `claude_session`. Edits in beiden Worktrees laufen ohne Rückfrage.

## 8 Alternativen

| Alternative | Warum nicht |
|---|---|
| Jeden Erzeuger einzeln absichern (ship, runner-health, MCP, Telegram, UI) | Der unbekannte Erzeuger bleibt offen, neue Erzeuger brauchen jedes Mal einen Fix. A4 macht das nur für die zwei billigen |
| Resolve-Job prüft Lauf-Status (Entwurf v0) | verhindert nötige Deploys, wenn der Vorläufer abgelehnt wird (K1) |
| push→main nur noch staging (Lint-Standard) | löst den Realfall auch (P ginge nach staging), ist aber der offene Owner-Entscheid A5 und deckt Dispatch+Dispatch nicht |
| Scope-Datei je Sitzung + UserPromptSubmit-Hook (v0) | zweiter Zustand neben Leases, Schutz gegen Agenten-Edits braucht Bash-Parsing (K4) |
| Stop-Hook-Schwelle von 3 auf 2 senken | bleibt nachträglich, der Auftrag verlangt „nur durch Owner-Erlaubnis", also vorher |

## 9 Out-of-the-Box

- **GitHub-Deployments-API als Ist-Stand:** Statt per ssh am Host zu lesen, den letzten
  erfolgreichen Deployment-Eintrag der Umgebung abfragen. Das ist billiger, misst aber das Protokoll,
  nicht den Host. Für A1 gilt: Host vor Protokoll (Lehre „grün ≠ live").
- **Sitzungsstart als Vertrag:** `/session-start` gibt „Scope: writing-hub, cad-hub" im ersten
  Board aus. Der Owner sieht so beim Start, was ohne Rückfrage erlaubt ist.

## 10 Befunde

| ID | Befund | Schwere | Evidenz | Folge |
|---|---|---|---|---|
| BF1 | Concurrency-Fallbacks divergieren, push-Prod-Lauf sitzt in der Staging-Gruppe | hoch | C2 | A3 |
| BF2 | `_deploy-unified` prüft nicht auf „schon deployt" | hoch | C3 | A1 |
| BF3 | `gh run cancel` wirkt nicht auf pending/waiting, runner-health nutzt genau das | mittel | C1, C5 | A4 |
| BF4 | `/ship` dispatcht Prod direkt nach einem Push, der bei Push→Prod-Hubs schon deployt | mittel | C4 | A4 |
| BF5 | 23 Aufrufer auf 10 Pin-Ständen, shared-ci-Änderungen kommen nicht an | hoch | C7 | Rollout-Preis, Kill-Gate |
| BF6 | `domain` fehlt bei 38/69 Registry-Einträgen, darunter meiki-hub, ttz-hub | mittel | C8 | B1 |
| BF7 | Kein PreToolUse auf Edit/Write, Scope-Prüfung nur nachträglich ab drittem Repo | hoch | C11, C12, C13 | B3 |
| BF8 | Faktenbrief v0 behauptete, deploy-config-lint nutzten nur dev-hub und platform. Belegt ist risk-hub als Nutzer, dev-hub widersprüchlich | niedrig | C15 (H) | korrigiert in A5 |

## 11 Top-5-Risiken

1. **Pin-Rollout bleibt stecken** (BF5). A1/A2 wirken nur in Hubs mit neuem Pin. Gegenmittel:
   Pilot auf zwei Hubs (ausschreibungs-hub, pptx-hub), Pin-Zähler im Kill-Gate.
2. **`actions: write` in einem Deploy-Workflow** erweitert, was ein kompromittierter Build-Schritt
   tun kann (Läufe abbrechen). Gegenmittel: Owner-Go nach Gate 3. Ohne Go entfällt A2 und A1 allein
   genügt mit einem zweiten, aber harmlosen Gate-Klick.
3. **Ist-Stand-Lesung am Host scheitert** (ssh, Format des Image-Tags je Hub). Dann gilt fail-open:
   Deploy läuft wie heute, Notice „Ist-Stand nicht lesbar". Ein falscher no-op wäre schlimmer als ein
   doppelter Deploy.
4. **Fehlblockaden in B3** durch falsche Repo-Auflösung (Worktree-Pfade, Submodule). Gegenmittel:
   Testfälle je Zeile der Tabelle in §5, Kill-Gate auf Fehlblockaden.
5. **Approval-Last steigt** (Diabolus 11). Gegenmittel: Grundlinie messen, bevor B3 scharf wird.
   Gezählt werden in den Transkripten der letzten 30 Tage die Business-Sitzungen mit Schreiben in ein
   zweites Business-Repo. Obergrenze im Kill-Gate.

## 12 Empfehlungen

| REC | Konkret | Repo | Gate |
|---|---|---|---|
| R1 | `_deploy-unified.yml`: A1-Schritt am Anfang von `deploy-production`, Input `erneut` (bool, default false), neuer Minor-Tag | shared-ci | Merge = shared-ci-Normalbetrieb |
| R2 | A2-Schritt + `actions: write` | shared-ci | **Owner-Go (Gate 3)** |
| R3 | Pilot: ausschreibungs-hub + pptx-hub Pin heben, A3-Fallback angleichen, Permissions der Aufrufer | 2 Hubs | Prod-Wirkung erst beim nächsten Deploy, Gate wie immer |
| R4 | `/ship` Schritt 3 umschreiben, runner-health force-cancel + Nachmessen | platform | — |
| R5 | `sitzungs_klasse` in canonical.yaml + Lint + Erstbefüllung als PR, Owner prüft 69 Zeilen | platform | Owner-Review der Klassen |
| R6 | Grundlinie Approval-Last aus Transkripten (Skript in `tools/`, einmalig) | platform | — |
| R7 | `business_scope_guard.py` + gemeinsames Repo-Auflösungs-Modul + Tests `test_should_…` + SessionStart-Selbsttest, erst **advisory** für 14 Tage, dann deny | platform | Hook-Verteilung = Org-Schreibrecht → Vier-Augen-Review |
| R8 | `/session-start` mit mehreren Repos (je Repo `repo-session.sh start`), ADR-233-Amendment „Leases einer Claude-Sitzung = Scope" | platform | Amendment |
| R9 | Hausregel/Gate-4-Satz (B5) | ~/.claude | **Owner-Wort** (Charta Art. 3) |
| R10 | Nachträglicher Abgleich Commits/PRs des Actors außerhalb des Scopes (gegen L1–L6) | platform | vertagt, erst nach Kill-Gate B |

## 13 Entscheidung + Kill-Gate + 30/60/90

**Empfehlung:** Teil A mit R1, R3 und R4 sofort, R2 nach Owner-Go. Teil B mit R5, R6, dann R7
advisory, R8. Der deny-Schalter folgt erst nach Grundlinie und 14 Tagen advisory.

**Kill-Gate A (Stichtag 2026-12-15, Prüfer: Owner):**
- (a) Ein Prod-Doppeldeploy desselben SHA in einem Pilot-Hub nach Rollout → A1 wirkt nicht, zurückbauen.
- (b) Ein belegter fälschlicher no-op (Host nach dem Lauf ≠ main, obwohl der Lauf main ausrollen sollte) → A1 zurückbauen.
- (c) Unter 5 Hubs mit Wächter-Pin bis 2027-01-15 → Teil A als Org-Maßnahme gescheitert, bleibt Pilot.

**Kill-Gate B (Stichtag 2026-12-15):**
- (d) Mehr als 3 Fehlblockaden je 14 Tage im deny-Betrieb → zurück auf advisory.
- (e) Mehr als 5 Owner-Freigaben `scope +` je Woche → die Grenze ist zu eng. Klassen oder Gruppen-Freigaben neu schneiden.
- (f) Eine belegte Schreibaktion in ein fremdes Business-Repo über einen Deny-Weg → B3 defekt.

**Exception-Budget:** bis 2026-11-15 je Teil zwei bewusste Ausnahmen (`erneut: true` ohne Anlass,
`scope +` als Sammelfreigabe), jeweils mit Issue-Zeile.

**Rückbau:**
- A1/A2: neuer shared-ci-Tag ohne die Schritte. Der Input `erneut` bleibt als toter Input bis zum nächsten Major (Maintainer 1).
- B3: Hook-Eintrag aus `settings.json` entfernen. Leases und Owner-Texte bleiben ohnehin bestehen.
- B1: Das Feld bleibt als Katalog-Information.

**30/60/90:**
- **30 d:** R1, R3, R4, R5, R6 gemergt, Pilot-Hubs auf Wächter-Pin, Grundlinie gemessen.
- **60 d:** R7 advisory ausgewertet, deny-Entscheid, R8.
- **90 d:** Kill-Gates ausgewertet, Rollout auf weitere Hubs oder Rückbau.

| Kriterium | Status | Beleg |
|---|---|---|
| (a) kein Prod-Doppeldeploy in Pilot-Hubs nach Rollout | offen | — |
| (b) kein fälschlicher no-op | offen | — |
| (c) ≥5 Hubs mit Wächter-Pin bis 2027-01-15 | offen | — |
| (d) ≤3 Fehlblockaden je 14 Tage | offen | — |
| (e) ≤5 Owner-Freigaben je Woche | offen | — |
| (f) keine Schreibaktion über Deny-Weg | offen | — |

**Ehrliche Enforcement-Grenze:** `review_by`, `kill_criteria` und `superseded_by_spec` dieses
Dokuments liest heute kein Lifecycle-Gate. Die Kontrolle ist ein Review-Gate, kein Exit-Code.
