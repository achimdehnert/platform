---
retro_schema: 1
date: 2026-07-15
repo_scope: [platform, trading-hub, coach-hub]
session_id: c494a2
footprint: full
footprint_reduction_reason: "Rule-B deep trigger fired (3 repos + 2 prod-deploys), downgraded one level to full: (a) both merges preceded by explicit human 'go' in the session transcript, (b) fully rollback-capable / no DB migration / same deployment pattern, (c) findings_total estimated ≤10 pre-run (came in at 13 raw / 9 survived, consistent with the estimate)."
findings_total: 13
findings_survived: 9
refuted_rate: 0.31
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [scope-checkpoint-not-durably-recorded, claim-before-cheapest-check, handover-stale-vor-merge, workaround-without-tracking-anchor]
recurring_findings: [scope-checkpoint-not-durably-recorded, claim-before-cheapest-check, handover-stale-vor-merge, workaround-without-tracking-anchor]
---

## 1. Executive Summary

- Deploy-Health-Triage für trading-hub (#150) und coach-hub (#40) erfolgreich abgeschlossen und **live verifiziert** (`/livez/` 200 auf beiden), plus eine präventive ADR-270-Vorbedingung gefixt (platform#1152) — alle drei Kernziele der Session wurden erreicht.
- **Kein** der beiden Merges (trading-hub#150, coach-hub#40) und **keine** der Mail-Sende-Aktionen (Owner-Block #1094) hinterließ einen durablen Freigabe-Nachweis — Zustimmung existiert nur im Chat-Transkript, nicht in einem PR-Kommentar/Review. Dieses Muster ist bereits ein Gate-pflichtiger Wiederholungsfund (`scope-checkpoint-not-durably-recorded`, jetzt 3.+ Vorkommen).
- Eine Root-Cause-Aussage ("transiente Runner-Kontention") wurde mit mehr Bestimmtheit ins Handover geschrieben, als das Log-Beleg trägt — ein Skeptiker bestätigte einen echten Prozess-Kill im Log, aber nicht spezifisch "Kontention" als Mechanismus. Ebenfalls ein bereits Gate-pflichtiger Wiederholungsfund (`claim-before-cheapest-check`).
- `AGENT_HANDOVER.md`/`ARCHIVE.md` hat jetzt **3 konkurrierende offene PRs** auf denselben Dateien (#1159 dieser Session, #1122 seit 07-13, #1079 seit 07-11) — die Session eröffnete einen dritten, ohne die bestehenden zwei zu prüfen oder zu flaggen. Ebenfalls bereits Gate-pflichtig (`handover-stale-vor-merge`).
- Zwei Duplicate-Work-Beinahe-Fehler (trading-hub, coach-hub) wurden **vor** dem Bauen eines Fixes durch einen `gh pr list`-Check abgefangen — kein Schaden entstanden, aber der Check kam jeweils erst NACH dem Anlegen eines leeren Worktrees, nicht davor.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Kein durables Artefakt belegt die menschliche Freigabe für 3 gegatete Aktionen dieser Session (Merge trading-hub#150, Merge coach-hub#40, Mail-Versand #1094) — Zustimmung nur im Chat, PR-/Issue-Kommentare durchweg leer | Prozesslücke/Kommunikation | Mittel | SURVIVES | `gh pr view 150/40 --json comments,reviews` → beide `{"comments":[],"reviews":[]}`; `gh issue view 1094 --json comments` → 0 Kommentare | `scope-checkpoint-not-durably-recorded` (bereits ≥2 vor diesem Report) |
| 2 | PR #1152 Test-Plan-Checkbox blieb unabgehakt, obwohl die referenzierten Checks (`guardian`, `gitleaks secret scan`) ~55 Min. vor Merge bereits grün waren | Werkzeug | Niedrig | SURVIVES | `gh pr view 1152 --json body,statusCheckRollup` | — |
| 3 | Root-Cause-Label "transiente Runner-Kontention" (AGENT_HANDOVER.md) überzeichnet die Beleglage — Log zeigt einen real gekillten Git-Prozess (`Terminate orphan process`), aber keinen bestätigten Konkurrenz-Mechanismus | Evidence-Discipline | Mittel | SURVIVES | Label zu stark, nicht die Beobachtung selbst — `gh api .../actions/jobs/87131506440/logs` (Fetch bricht ab, Orphan-Kill, kein `##[error]`); Re-Run 17,5h später grün, gleicher Commit | `claim-before-cheapest-check` (bereits ≥2 vor diesem Report) |
| 4 | Neuer `merge_group`-Codepfad in `guardian.yml` (Required Security Gate) hat 0 reale Ausführungen — platform hat noch keine Merge-Queue; erste echte Probe steht aus | fehlende Validierung | Niedrig | SURVIVES | Als Restrisiko zu werten, nicht als Fehlentscheidung — `gh api repos/achimdehnert/platform/rulesets/17621471` (kein `merge_queue`-Rule-Typ); PR #1152 Review `wirdigital APPROVED`, 2. Owner-Review + YAML-Validierung vorhanden | — |
| 5 | trading-hub PR #150 Commit-Typ `hotfix(docker): ...` verstößt gegen die dokumentierte Commit-Konvention (`[feat\|fix\|refactor\|docs\|test\|chore]`); beim Review/Merge nicht geflaggt | Konventionsverstoß | Niedrig | SURVIVES | `gh pr view 150 --json commits`; `trading-hub/CLAUDE.md` enthält keine abweichende Commit-Konvention | — |
| 6 | Kein durables Tracking-Artefakt existiert für das Verhalten des Merge-Autorisierungs-Classifiers in dieser Session (laut Selbstbericht blockierte er einen Merge-Versuch für trading-hub#150, ließ einen strukturell gleichen für coach-hub#40 durch) — die Abwesenheit eines Artefakts ist der Befund, NICHT die behauptete Inkonsistenz selbst, die als reine Session-Aussage unverifiziert bleibt (s. §8) | Werkzeug/Sicherheits-blinder-Fleck | Niedrig-Mittel | SURVIVES | `mergedBy` identisch (`achimdehnert`) in beiden PRs — bestätigt nur die Abwesenheit eines Artefakts, ist für die Inkonsistenz-Behauptung selbst uninformativ; keine Such-Treffer für einen Tracking-Issue | — |
| 7 | Wiederholter Wait-Loop/Monitor-Scripting-Bug (laut Selbstbericht 2× in dieser Session: `2>&1` korrumpierte `jq`-Input) hinterließ kein Lessons-Artefakt, trotz sonst starker Drift-Lesson-Disziplin dieses Repos | Prozesslücke | Niedrig | SURVIVES | Bestätigt: keine der 2 in dieser Session geschriebenen Memories erwähnt es — `grep -rl "monitor\|jq" ~/.claude/.../memory/*.md` → nur ein unverwandter, älterer Treffer (`feedback_subagent_wait_loop_cutoff.md`, 07-09, anderes Repo/Incident) | `workaround-without-tracking-anchor` (war ×1 vor diesem Report → jetzt ×2, neu Gate-pflichtig) |
| 8 | `AGENT_HANDOVER.md`/`ARCHIVE.md` hat jetzt 3 konkurrierende offene PRs auf denselben Dateien (#1159 heute, #1122 seit 07-13, #1079 seit 07-11) — diese Session eröffnete #1159 ohne die bestehenden zwei zu prüfen oder auf sie hinzuweisen | Prozesslücke | Mittel | SURVIVES | `gh pr list --search "handover"` (3 offen, `--name-only`-Diff bestätigt identische Zieldateien); PR #1159-Body erwähnt weder #1122 noch #1079 | `handover-stale-vor-merge` (bereits ≥2 vor diesem Report) |
| 9 | coach-hub PR #40 wurde nur deshalb sicher (ohne Verlust von PR #45, das 11 Min. vorher gemergt wurde) gemergt, weil GitHubs Rebase-bei-Merge-Klick das automatisch nachzog — nicht weil die Session unmittelbar vor dem Merge erneut fetchte/rebasete | fehlende Validierung | Niedrig | SURVIVES | Merge-Commit `fbea273` hat einzigen Parent `e3fee51` (= PR #45); Timeline zeigt genau 1 Force-Push um 09:32:30, **vor** #45s Merge um 09:43:39 | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 4 | Beide Deploy-Failures gelöst + live verifiziert, ADR-270-Lücke präventiv geschlossen — kleine Mängel (#1, #8), Kernziele erreicht |
| Architektur/Design | 4 | Fixes sauber gescoped (kein Scope-Creep in PR #1152/#150/#40), aber #4 (untested Pfad in kritischem Gate) als kleiner Mangel |
| Code-Konventionstreue | 3 | #5 (Commit-Typ-Verstoß unbemerkt gemergt) — teilweise erreicht, Review hätte greifen sollen |
| Risiko/Debt | 2 | 3 von 9 Befunden sind bereits mehrfach-wiederkehrende, Gate-pflichtige Muster (#1, #3, #8) — die schwächste Dimension dieses Repos bleibt schwach |
| Prozess-Effizienz | 3 | 2 Duplicate-Work-Beinahe-Fehler (abgefangen, aber erst nach Worktree-Anlage) + 2× derselbe Monitor-Bug — Reibung, kein Totalausfall |
| Entscheidungsqualität | 4 | Fresh-Fetch-Disziplin, Scope-Checkpoint bei #1158 sauber eingehalten, Root-Cause-Korrektur mid-Session — einzelner Abzug für #3 (Übergewissheit) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Freigabe für Merge/Mail-Versand nur im Chat erteilt, kein PR-Kommentar/Review-Objekt erzeugt | Vor jeder Gate-Aktion (Merge, Mail-Versand) einen kurzen PR-/Issue-Kommentar mit der Freigabe-Kurzform hinterlegen (`gh pr comment <n> --body "Freigegeben: <Stichwort>"`), bevor die Aktion ausgeführt wird | #1 |
| PR #1152 Test-Plan-Checkbox blieb unabgehakt, obwohl die referenzierten Checks bereits grün waren | Nach Merge kurz die eigene Test-Plan-Liste im PR-Body gegen den tatsächlichen `statusCheckRollup` abgleichen und offene Checkboxen nachziehen, bevor der PR als erledigt gilt | #2 |
| "transiente Runner-Kontention" ins Handover geschrieben, ohne die Log-Beleglage explizit zu benennen | Root-Cause-Sätze im Handover mit Beleg-Stärke kennzeichnen ("bestätigt: Prozess wurde gekillt" vs. "Hypothese: Kontention als Mechanismus, nicht unabhängig bestätigt") | #3 |
| `merge_group`-Codepfad gemergt, ohne im PR-Body zu vermerken, dass er bis zur ersten Merge-Queue-Aktivierung ungetestet bleibt | PR-Body für präventive/noch-nicht-auslösbare Codepfade einen expliziten "Nicht getestet bis <Trigger-Bedingung>"-Hinweis aufnehmen, plus Reminder-Issue für den ersten echten Durchlauf | #4 |
| PR #150 (fremd erstellt) ohne Commit-Konventions-Check gemergt | Vor dem Mergen eines fremden, vorbereiteten PRs kurz `gh pr view --json commits` gegen die Commit-Konvention der Ziel-CLAUDE.md prüfen — auch bei "nur verifizieren, nicht selbst bauen" | #5 |
| Merge-Classifier blockierte einmal, ließ einmal durch — keine Nachfrage, warum | Bei inkonsistentem Tool-/Classifier-Verhalten innerhalb derselben Session einmal kurz nachhaken (User informieren: "gleiche Aktion, unterschiedliches Ergebnis — worin liegt der Unterschied?") statt stillschweigend weiterzumachen | #6 |
| Monitor-Bug (`2>&1`+`jq`) zweimal aufgetreten, kein Lessons-Eintrag geschrieben | Nach dem 2. Auftreten derselben Tool-Klasse von Bug in einer Session: kurze Memory-Notiz anlegen (auch wenn kein Repo-Artefakt existiert — der Bug selbst ist die Lektion) | #7 |
| Neues Handover-PR (#1159) eröffnet, ohne `gh pr list --search handover` vorher laufen zu lassen | Vor jedem Handover-Update-PR: kurzer Check auf bereits offene Handover-PRs; falls vorhanden, im neuen PR-Body verlinken oder auf dem neueren aufbauen statt eine 3. Parallel-Version zu erzeugen | #8 |
| Rebase von PR #40 einmal vor #45s Merge durchgeführt, danach nicht erneut gefetcht/geprüft vor dem finalen Merge-Klick | Unmittelbar vor dem finalen Merge-Klick (nicht nur beim Rebase-Schritt) einmal `git fetch origin main` + Diff-Check, auch wenn GitHubs Rebase-Merge es oft automatisch heilt | #9 |

## 5. Längsschnitt

`tools/retro_kpis.py` lief vor Report-Erstellung (Ergebnis oben zitiert). **4 Slugs erreichen oder überschreiten mit diesem Report die Gate-Schwelle (≥2 Vorkommen):**

- **`scope-checkpoint-not-durably-recorded`** (Befund #1) — bereits vor diesem Report ≥2, jetzt 3.+ Vorkommen. Betrifft hier: 2 Auto-Deploy-Merges + 1 Mail-Versand ohne PR-/Issue-Kommentar-Spur.
- **`claim-before-cheapest-check`** (Befund #3) — bereits vor diesem Report ≥2 (Top-10-Liste des Tools), jetzt erneut. Diesmal eine mildere Auto-Deploy-Ausprägung: der billigste Check (Log lesen) wurde zwar gemacht, aber die daraus gezogene Schlussfolgerung war präziser formuliert als die Beleglage hergab.
- **`handover-stale-vor-merge`** (Befund #8) — bereits vor diesem Report ≥2, jetzt erneut: 3 konkurrierende Handover-PRs gleichzeitig offen.
- **`workaround-without-tracking-anchor`** (Befund #7) — war ×1 vor diesem Report, wird mit diesem Report zu ×2 und damit neu Gate-pflichtig.

Alle vier sind **etablierte, wiederkehrende Muster über mehrere Retros hinweg** — keines davon ist neu für diese Session, aber diese Session hat alle vier live reproduziert. Das Long-Tail-Signal ist eindeutig: die Org bräuchte für alle vier tatsächlich einen **erzwingenden Mechanismus (Hook/CI-Check)**, kein weiteres Memo.

### 5b. Autonomie-Kalibrierung

- **over_ask: 0** — nichts wurde dem User als "dein Zug" vorgelegt, das nachweislich deterministisch/reversibel gewesen wäre und autonom hätte laufen können. Beide Merges waren zu Recht gegatet (Auto-Deploy-Repos).
- **over_act: 0** — keine autonome Aktion verletzte ein Gate; beide Merges hatten eine (wenn auch nur Chat-basierte) explizite Freigabe vorher.
- Die eigentliche Kalibrierungs-Lücke liegt nicht in over_ask/over_act, sondern **orthogonal dazu**: Freigaben wurden korrekt eingeholt, aber nicht **artefaktiert** (Befund #1) — das ist ein Tracking-Gap, kein Autonomie-Grenzen-Gap. Die Autonomie-Charter selbst braucht hier keine Schärfung; was fehlt, ist ein Schritt "Freigabe in einen PR-Kommentar spiegeln", bevor die Aktion ausgeführt wird.

## 6. Verankerung — kopierfertige Vorschläge

**Memory-Kandidat (feedback, drift:true):**
```yaml
---
name: feedback_gate_approval_needs_pr_comment
description: "Chat-Freigabe für Merge/Mail-Versand/Publish reicht als Autorisierung, aber hinterlässt kein durables Artefakt — vor der Aktion einen kurzen PR-/Issue-Kommentar mit der Freigabe setzen. 3. Vorkommen (scope-checkpoint-not-durably-recorded), Gate-pflichtig laut retro_kpis.py."
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-15-gate-approval-no-artifact
---
Realfall 2026-07-15 (session-retro-2026-07-15-platform-c494a2): trading-hub#150-Merge,
coach-hub#40-Merge und ein Mail-Versand (Owner-Block #1094) hatten alle eine explizite
"go"-Freigabe im Chat, aber KEIN PR-/Issue-Kommentar/Review dokumentiert das. Bereits
3.+ Vorkommen über Retros (`scope-checkpoint-not-durably-recorded`, retro_kpis.py) —
Gate-pflichtig: vor jeder gegateten Aktion (Merge auf Auto-Deploy-Repo, Mail-Versand,
Publish) EINEN Kommentar/Reply mit der Freigabe-Kurzform hinterlegen, bevor die Aktion
ausgeführt wird. Verwandt: [[feedback_veto_needs_durable_artifact]].
```

**ADR-Kandidat:** keiner — dies ist ein Prozess-/Tooling-Gap, keine Architektur-Entscheidung.

**Skill-Edit-Kandidat (session-ende.md oder ein neuer Pre-Merge-Check):** einen optionalen Schritt "vor Merge/Publish: `gh pr comment <n> --body '<Freigabe-Kurzform>'`" in die Merge-Gate-Beschreibung der Autonomie-Charter-Memory aufnehmen (nicht in diesem Retro selbst umgesetzt — Verankerung entscheidet der Mensch).

## 7. Maßnahmen (Action-Board)

🟢 **Offen — dein Zug**
1. 🟢 Memory-Kandidat oben (`feedback_gate_approval_needs_pr_comment`) freigeben zum Schreiben? — 3. Wiederholung, Gate-pflichtig laut `retro_kpis.py`
2. 🟢 3 konkurrierende Handover-PRs (#1159/#1122/#1079) — welches soll gewinnen, Rest schließen/rebasen?
3. 🟢 Root-Cause-Satz in `AGENT_HANDOVER.md` zu coach-hub hedgen ("Kontention" → "vermuteter Prozess-Kill, Mechanismus nicht bestätigt")?

🔵 **Offen — ich kann sofort**
4. 🔵 PR #1152 Test-Plan-Checkbox nachträglich abhaken (kosmetisch, PR bereits gemergt — nur falls gewünscht)
5. 🔵 Reminder-Issue für den ersten echten `merge_group`-Durchlauf anlegen, sobald eine Merge-Queue aktiviert wird

✅ **Erledigt**
6. ✅ Alle 3 Findings-Dimensionen durch unabhängige Sonnet-Finder + Sonnet-Skeptiker mit frischem `git fetch` verifiziert
7. ✅ Finder-Konflikt (transiente-Kontention-Label) sauber an einen dedizierten Skeptiker geroutet statt selbst aufgelöst
8. ✅ `retro_kpis.py` Pflicht-Lauf vor Report-Erstellung durchgeführt

## 8. Nicht verifiziert (Restlücken)

- **Ob die Merge-Classifier-Inkonsistenz (Befund #6) real war oder nur ein Wahrnehmungs-Artefakt der Session ist** — beide `mergedBy`-Felder sind identisch und uninformativ; der billigste weitere Check wäre, die tatsächliche Classifier-Log/Policy-Konfiguration einzusehen (außerhalb des Artefakt-Zugriffs dieses Retros).
- **Ob "Kontention" (Befund #3) tatsächlich von einem konkurrierenden Job auf demselben Self-Hosted-Runner stammte** — der Skeptiker prüfte nur platform/trading-hub im selben Zeitfenster, nicht alle ~25 Repos, die denselben Runner-Host teilen. Billigster nächster Check: Runner-Auslastungs-Log für `prod-server` im Fenster 2026-07-14 15:42–15:43Z.
- **Ob die Mail an pg@dehnert.team inhaltlich korrekt ankam** (Links funktionsfähig, insbesondere die unverifizierten PyPI-Settings-URLs) — kein Mailbox-Zugriff in dieser Session; einziger Beleg ist der `send_mail.py`-Exit-Status "OK".
