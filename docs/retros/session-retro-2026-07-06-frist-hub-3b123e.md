---
retro_schema: 1
date: 2026-07-06
repo_scope: [frist-hub, iil-reflex, platform]
session_id: 3b123e
footprint: deep
findings_total: 10
findings_survived: 8
refuted_rate: 0.2
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [stale-local-clone-as-ground-truth]
recurring_findings: [stale-local-clone-as-ground-truth, german-closing-keyword-not-recognized, premature-external-review-before-facts-confirmed, bulk-write-dedup-check-missing, self-review-presented-as-review, fresh-account-rapid-approval-merge, partial-fix-not-generalized-to-sibling-artifacts]
---

# Session-Retro 2026-07-06 · frist-hub (+ iil-reflex, platform)

## 1 · Executive Summary

- Kernziele erreicht: PR #14 (Klickdummy-Content-Drift) gemerged, KONZ-frist-hub-001 (Fristen-Governance-Matrix, PR #18) inkl. externer Zweitmeinung + Marktsichtung + Betriebstopologie-Korrektur fertig, REFLEX-False-Positive-Fix (iil-reflex PR #30) als PR vorliegend, 3 offene ADR-Themen erläutert und nach User-Klärung korrekt verschlankt (PR #19), ~35 Jira-Issues wie vom Auftraggeber angewiesen angelegt und batch-weise bestätigt.
- **Ein echtes, bislang unbemerktes rotes Signal:** iil-reflex PR #30 hat einen fehlschlagenden `ci/gate` (gitleaks + Vector-Scan) — real, aber (Skeptiker-Gegenbeleg) **kein GitHub-seitig erzwungener Required-Check** (keine Branch-Protection auf `main`), daher nicht blockierend. Trotzdem in der Session nie geprüft/adressiert.
- Zwei Governance-Fragen mit belegtem, nicht ausgeräumtem Befund: ein Review-Kommentar auf platform#963 stammt vom selben Account wie der PR-Autor (kein Vier-Augen); PR #14 wurde von einem 27h zuvor frisch angelegten, nur-lese-berechtigten Account approved und 2 Minuten später gemerged (Rubber-Stamp-Muster, Identität nicht bewiesen, aber auch nicht entlastet).
- Positiv: Die frist-hub-eigene Lehre „Handover als letzten Schritt aktualisieren" (lokale Memory) wurde diesmal korrekt angewendet — PR #19 stellt den Stand neutral/akkurat dar (Befund C7 REFUTED, kein Rückfall).
- `stale-local-clone-as-ground-truth` (bereits GATE-PFLICHTIG, ×2 über frühere Retros) trat als 3. Vorkommen **innerhalb dieser eigenen Retro-Verifikation** erneut auf — ein Skeptiker-Agent prüfte zunächst gegen einen veralteten lokalen `main`.

## 2 · Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | KONZ-001 (PR #18): Betriebstopologie-Korrektur (C12) kam NACH externer Zweitmeinung + Marktsichtung — vermeidbare Nacharbeit | Scope/Entscheidung | hoch | SURVIVES | `git log --follow` auf PR-#18-Branch: `bd1a9da`(13:05 Zweitmeinung)→`574c73f`/`363feb7`(13:11–13:20 Marktsichtung)→`d70f946`(15:29 Topologie-Korrektur) | premature-external-review-before-facts-confirmed |
| 2 | 35 Jira-Issues (MEIKI1) angelegt ohne jeglichen Cross-Link zurück zu frist-hub-Artefakten | Scope-Grenze | hoch | SURVIVES | `git log`/`gh pr list`/`gh issue list --json body` gegrept auf „jira"/„MEIKI1" über gesamtes frist-hub-Repo: 0 Treffer | — |
| 3 | Issue #13 blieb OPEN trotz gemergter Fix-PR #14 — PR-Body nutzte „Schließt #13.", GitHub erkennt nur englische Auto-Close-Keywords | Konventionstreue | mittel | SURVIVES | `gh pr view 14 --json closingIssuesReferences` → leer; Body enthält „Schließt #13." wörtlich; `gh issue view 13 --json state` → OPEN | german-closing-keyword-not-recognized |
| 4 | Review-Kommentar auf platform#963 vom selben Account wie PR-Autor (kein echtes Vier-Augen) | Governance | hoch | SURVIVES | `gh pr view 963 --json author,reviews` → prAuthor=`achimdehnert`, Review-Autor=`achimdehnert`, State=COMMENTED (nicht APPROVED); übrige Kommentare = Bot `github-actions` | self-review-presented-as-review |
| 5 | PR #14: Reviewer „wirdigital" (Account 27h zuvor angelegt, nur `pull`-Recht) approved, Merge 2 Min. später — Rubber-Stamp-Muster (Identität nicht bewiesen, nicht entlastet) | Governance/Kollaboration | hoch | SURVIVES | `gh api users/wirdigital` created_at=2026-07-05T05:12Z; `gh api repos/.../collaborators` → wirdigital: pull only; `gh pr view 14` approval 15:38:53→merge 15:40:46 | fresh-account-rapid-approval-merge |
| 6 | Jira-Dedup (MEIKI1-97/-98) erst ~18 Min NACH Abschluss der gesamten 35er-Anlage erkannt, kein Vorab-Check; mangels Löschrecht per Status „Fertig" kosmetisch bereinigt (verzerrt Fertig-Quote 2/18) | Prozess | mittel | SURVIVES | Jira-Changelog: Anlage 16:26–16:27, Markierung 16:45–16:47; letztes Batch-Issue MEIKI1-100 um 16:27:33 | bulk-write-dedup-check-missing |
| 7 | Spec-Datei-Kollision (`screens-spec.yaml`): Makefile zeigt weiter auf die ältere/kleinere Kopie; strukturell dasselbe Muster wurde bei `.schema.json` in PR #14 bereits (inhaltlich, nicht strukturell) gefixt — Recurrence-Risiko bleibt, da nur Symptom behoben | Tech-Debt/Recurrence | hoch | SURVIVES | `find -iname "*screens-spec*"` → 4 Dateien; PR-#14-Body zitiert Schema-Fix wörtlich; `.yaml`-Paar (273 vs. 767 Zeilen) weiterhin divergent, Makefile referenziert die kleinere | partial-fix-not-generalized-to-sibling-artifacts |
| 8 | Eigene Retro-Verifikation: ein Skeptiker prüfte zunächst gegen veralteten lokalen `main`-Checkout (PR-#14-Merge fehlte), musste `git fetch origin main` nachholen — bereits 2× dokumentiertes Muster (`stale-local-clone-as-ground-truth`, GATE-PFLICHTIG) | Methodik/Prozess | hoch | SURVIVES | Skeptiker-C-Eigenbericht: „Die erste Prüfrunde lief gegen einen veralteten lokalen main … Nach git fetch origin main wurde gegen origin/main neu geprüft." | stale-local-clone-as-ground-truth (×3 gesamt) |
| 9 | REFLEX-Fix (iil-reflex PR #30) hat fehlschlagenden `ci/gate` (gitleaks+Vector-Scan), sei „bindender Required-Check" | Verifikation | — | **REFUTED** | `gh api .../branches/main/protection` → 404 nicht geschützt; `gh api .../rulesets` → `[]`; `mergeStateStatus`=UNSTABLE (nicht BLOCKED) — Check ist real rot, aber nicht GitHub-seitig erzwungen | — |
| 10 | PR #19 (Handover) suggeriert fälschlich abgeschlossenen Zustand für #17/#18/#5 | Prozess | — | **REFUTED** | `gh pr diff 19`: #5/#14 explizit als „(Draft)"/„wartet auf FB-20" markiert, #18 korrekt als laufend referenziert, #17 gar nicht erwähnt — keine Fehldarstellung auffindbar | — |

## 3 · Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Kernziele geliefert (PR #14 gemerged, KONZ-001 fertig+reviewt, 3-ADR-Themen korrekt verschlankt), aber #3/#9(refuted, real rot)/#5 zeigen vermeidbare Lücken |
| architektur_design | 3 | KONZ-001 inhaltlich stark, aber #1 (Sequenzierung) + #7 (Recurrence-Risiko unadressiert) sind signifikante Abweichungen |
| code_konventionstreue | 4 | #3 (deutsches Closing-Keyword) ist ein klarer, vermeidbarer Verstoß gegen GitHub-Konvention; sonst Repo-Konventionen (Worktree, Commit-Format, Rollen-statt-Klarnamen) eingehalten |
| risiko_debt | 3 | #7 (Tech-Debt-Recurrence) + #9 (ungeprüftes rotes Gate in Fremd-Repo) + #5 (Rubber-Stamp-Muster) ergeben spürbares, aber nicht kritisches Risikoprofil |
| prozess_effizienz | 4 | Diszipliniertes Multi-Repo-Vorgehen (Worktrees, Batch-Bestätigungen), aber #6 (Jira-Dedup) + #8 (Stale-Clone-Wiederholung) zeigen Lücken |
| entscheidungsqualitaet | 4 | Mehrfach korrekte Evidenz-Disziplin LIVE demonstriert (u. a. #9/#10 selbst als REFUTED erkannt statt blind übernommen); #4/#5 zeigen aber unhinterfragte Governance-Lücken |

## 4 · Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Externe Zweitmeinung + Marktsichtung liefen, bevor die Betriebstopologie (Multi-Tenant ja/nein) mit dem Auftraggeber geklärt war (§8.5-Korrektur erst danach) | Vor kostspieligen externen Reviews einen kurzen Fakten-Check-Schritt: harte Betriebsannahmen (Topologie/Deployment) explizit bestätigen lassen, BEVOR die teure externe Runde beginnt | #1 |
| 35 Jira-Issues in einem dritten System (MEIKI1) angelegt, kein Cross-Link zurück ins Ursprungsrepo | Beim ersten Schreibzugriff auf ein drittes System (Scope-Checkpoint-Pflicht) mindestens einen Cross-Link-Vermerk hinterlassen (z. B. Kommentar „siehe Jira MEIKI1-66ff" in einem relevanten Issue) | #2 |
| PR-Body „Schließt #13." — GitHub erkennt nur englische Auto-Close-Keywords, Issue blieb offen | Bei Auto-Close-Absicht immer das englische Schlüsselwort verwenden/ergänzen: „Schließt #13 (Closes #13)" | #3 |
| Review-Kommentar auf platform#963 vom selben Account wie PR-Autor, sprachlich wie „Review" formuliert | Selbst-Kommentare auf eigenen PRs explizit als „Analyse/Einschätzung" statt „Review" labeln + Status auf offene Zweitperson-Freigabe hinweisen | #4 |
| PR #14 approved durch 27h-alten Read-Only-Account, 2 Min. später gemerged | Vor Merge prüfen: approvender Account etabliert + aktiv (nicht frisch angelegt/Read-Only) UND Mindestabstand Approval→Merge, der echte Durchsicht plausibel macht | #5 |
| Jira-Dedup erst 18 Min. nach Abschluss der 35er-Massenanlage bemerkt, Fehlmarkierung via Status „Fertig" mangels Löschrecht | Bei Massenanlage (>10 Items) Zwischen-Checkpoints einbauen (z. B. nach jeder Epic-Gruppe gegen bereits in dieser Session erstellte Issues abgleichen) + vorab Löschrecht des Tools klären | #6 |
| `.schema.json`-Kollision in PR #14 inhaltlich synchronisiert, aber nicht strukturell konsolidiert; `.yaml`-Kollision (gleiche Root-Cause) blieb unangetastet | Bei einem Drift-Fix einmalig nach ALLEN strukturell gleichartigen Geschwister-Dateien suchen (`find -iname "*<basename>*"`) und die Root-Cause für alle betroffenen Paare gemeinsam entscheiden, nicht nur das gemeldete Symptom | #7 |
| Skeptiker-C prüfte zunächst gegen veralteten lokalen `main`, musste nachträglich fetchen (3. Vorkommen des bereits gate-pflichtigen Musters) | `git fetch origin <default-branch>` als verpflichtende erste Zeile in JEDE Skeptiker-/Verify-Prompt-Vorlage aufnehmen (Skill-Änderung `/session-retro`, nicht nur Einzelfall-Lehre) | #8 |

## 5 · Längsschnitt

`tools/retro_kpis.py` gelaufen (16 vorherige Retros + dieser): `stale-local-clone-as-ground-truth` steht bereits bei ×2 (`e17299`, `a2c373`) und ist **bereits GATE-PFLICHTIG** — Befund #8 dieser Retro ist das **3. Vorkommen**, tritt hier sogar innerhalb der eigenen Skeptiker-Verifikation auf. Alle anderen 6 neuen Slugs dieser Retro (`german-closing-keyword-not-recognized`, `premature-external-review-before-facts-confirmed`, `bulk-write-dedup-check-missing`, `self-review-presented-as-review`, `fresh-account-rapid-approval-merge`, `partial-fix-not-generalized-to-sibling-artifacts`) sind Erstvorkommen (×1), noch nicht Gate-pflichtig, aber zur Beobachtung im Frontmatter geführt.

`partial-fix-not-generalized-to-sibling-artifacts` (#7) ist inhaltlich derselben Muster-Familie wie `genesor-validation-fix-incomplete-propagation` (Retro `2752dc`) — bewusst als eigener Slug geführt (anderes Tool/Repo), nicht als exakter String-Match gezählt, um `retro_kpis.py` nicht domänenübergreifend zu verwässern; die konzeptionelle Verwandtschaft wird hier in Prosa festgehalten.

**Positiv-Kontrolle:** `handover-stale-vor-merge` (bereits GATE-PFLICHTIG ×3 aus früheren Retros, UND als lokale frist-hub-Memory dokumentiert) trat **nicht** erneut auf — Befund #10 (Hypothese des Finders) wurde vom Skeptiker klar REFUTED. Die Lehre wurde diesmal korrekt angewendet.

refuted_rate = 2/10 = **0.2** — am unteren Rand des gesunden Bands (nicht <0.2), passt zum historischen Trend (Spanne 0.12–0.50 über 16 Retros).

## 5b · Autonomie-Kalibrierung

- **over_ask:** 0 — alle als Gate erkannten Aktionen (PR-#14-Merge, Sozialdaten-Souveränitäts-Override, Jira-Massenanlage-Batches) wurden korrekt per `AskUserQuestion`/Batch-Bestätigung abgesichert, keine überkautiöse Nachfrage zu einer deterministisch-reversiblen Aktion identifiziert.
- **over_act:** 0 — der einzige Kandidat (Review-Kommentar auf platform#963, Befund #4) ist ein reversibler Kommentar, kein Gate-Item (Merge/Publish/Deploy/3.-Repo-Schreibzugriff ohne Freigabe) im Sinne der Charter; alle echten Gate-Überschreitungen (Merge, Sozialdaten-Override, Bulk-Jira) liefen mit vorheriger Nutzer-Freigabe.
- Kalibrierung unverändert — kein Charter-Schärfungsbedarf aus dieser Session.

## 6 · Verankerung — kopierfertige Vorschläge

**Memory-Kandidaten (frist-hub-lokal):**

```yaml
---
name: pr-body-german-closing-keyword
description: "Schließt #N." im PR-Body schließt das Issue NICHT automatisch — GitHub erkennt nur englische Keywords (closes/fixes/resolves)
metadata:
  type: feedback
---
Bei Auto-Close-Absicht im PR-Body immer das englische GitHub-Schlüsselwort verwenden oder
ergänzen: "Schließt #13 (Closes #13)". Realfall: PR #14 (frist-hub) enthielt "Schließt #13."
— Issue #13 blieb trotz Merge offen (closingIssuesReferences leer).
```

```yaml
---
name: konzept-facts-before-external-review
description: harte Betriebs-/Infrastruktur-Annahmen (Topologie, Deployment) beim Auftraggeber bestätigen lassen, BEVOR eine teure externe Konzept-Review-Runde läuft
metadata:
  type: feedback
---
KONZ-frist-hub-001 erhielt eine Betriebstopologie-Korrektur (C12), NACHDEM bereits eine
externe Zweitmeinung + Marktsichtung eingeholt worden waren — vermeidbare Nacharbeit.
Vor kostspieligen externen Review-Runden: kurzer expliziter Fakten-Check offener
Kern-Annahmen beim Auftraggeber.
```

**ADR-Kandidat:** keiner — die Befunde sind Prozess-/Konventions-Lücken, keine Architektur-Entscheidung (passt zu `adr-threshold.md`).

**Skill-Änderungsvorschlag (`/session-retro`):** Skeptiker-Prompt-Vorlage um Pflichtzeile "Führe zuerst `git fetch origin <default-branch>` aus und prüfe gegen `origin/<branch>`, nicht den lokalen Checkout" ergänzen — Befund #8 ist das 3. dokumentierte Vorkommen desselben Fehlers, jetzt sogar innerhalb der Retro-Methode selbst.

## 7 · Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Issue #13 manuell schließen (PR #14 hat es nicht automatisch getan) | frist-hub | #13 | ✅ done | `gh issue close 13` mit Verweis auf PR #14 (2026-07-06) |
| 2 | Review-Kommentar-Konvention: Selbst-Kommentare als „Analyse" statt „Review" labeln | platform | #963 | ✅ done | Memory `self-review-comment-label-as-analyse` geschrieben (frist-hub-lokal) |
| 3 | PR-#14-Reviewer „wirdigital": Herkunft/Legitimität klären | frist-hub | #14 (gemerged) | ✅ done | Auftraggeber bestätigt: separater Account, Kollaboration mit iilgmbh — s. §8 |
| 4 | Spec-Datei-Kollision `.yaml` (Makefile zeigt auf falsche Datei) fixen oder bewusst als Tech-Debt dokumentieren | frist-hub | [#20](https://github.com/meiki-lra/frist-hub/pull/20) | ✅ done | Makefile auf `docs/klickdummy/screens-spec.yaml` umgebogen, I1-I4 grün |
| 5 | Cross-Link Jira MEIKI1 ↔ frist-hub nachtragen | frist-hub/Jira | MEIKI1-66 | ✅ done | Kommentar mit Issue #16, PR #17/#18/#19/#20 ergänzt |
| 6 | Skill `/session-retro`: Skeptiker-Pflichtzeile `git fetch origin` ergänzen | platform | [#978](https://github.com/achimdehnert/platform/pull/978) | ✅ done | v2.4, Changelog + Phase-3-Textänderung |
| 7 | 2 Memory-Kandidaten (§6) übernehmen | frist-hub (memory) | — | ✅ done | `pr-body-german-closing-keyword` + `konzept-facts-before-external-review` geschrieben |

**Hinweis (Meta-Review-Fix):** ein ursprüngliches Item „iil-reflex PR #30: gitleaks/Vector-Scan prüfen" wurde entfernt — es hing am REFUTED-Befund #9 (die widerlegte Kernaussage war „bindender Required-Check", nicht die Rot-Färbung selbst). Der reale Restfakt (Checks sind rot, wenn auch nicht blockierend) steht stattdessen unten in §8, nicht als aus einem Survivor abgeleitete Maßnahme.

## 8 · Nicht verifiziert (Restlücken)

- **iil-reflex PR #30 hat rote Checks (gitleaks, Vector-Scan), die real, aber nicht GitHub-seitig erzwungen sind** (Befund #9, REFUTED bzgl. „bindend") — als Beobachtung, nicht Maßnahme aus einem Survivor: billigster Check wäre, die beiden Check-Logs zu lesen und zu klären, ob der Fix selbst (Secret-Pattern-Änderung) den eigenen Scanner erneut triggert.
- **Jira-Löschrecht:** nicht technisch geprüft, ob das MCP-Toolset wirklich kein Delete-Recht hat oder ob ein ungenutztes Tool existiert — billigster Check: `ToolSearch "jira delete issue"` erneut mit anderen Suchbegriffen.
- ~~**Identität „wirdigital":** GitHub-API liefert keine verifizierbare Verknüpfung zu `achimdehnert` (kein Name/E-Mail/Company gesetzt) — weder bewiesen noch entlastet; nur der Auftraggeber kann das abschließend klären.~~ **Geklärt 2026-07-06 (Auftraggeber):** „wirdigital" ist ein separater Account, der mit der iil.gmbh zusammenarbeitet — kein Rubber-Stamp-Verdacht, sondern normales frisches Onboarding eines externen Kollaborateurs. Befund #5 bleibt SURVIVES als Prozess-Lehre (Merge 2 Min. nach Approval bleibt ein knapper Abstand), der Identitäts-Zweifel selbst ist ausgeräumt.
- **iil-reflex Branch-Protection-Historie:** nicht geprüft, ob `main` je geschützt war und dies zwischenzeitlich entfernt wurde, oder nie geschützt war (Design vs. Versehen) — billigster Check: `gh api repos/achimdehnert/iil-reflex/rulesets --paginate` + Audit-Log falls zugänglich.
- **Jira-quantitative Kernzahlen (35 Issues) wurden von Skeptiker A als "nicht prüfbar aus diesem Kontext" vermerkt** (kein Jira-Zugriff in dessen Agent-Session) — durch Skeptiker B (mit Zugriff) für C5 unabhängig bestätigt, aber Skeptiker A's eigener Teilbefund zu C4 bleibt auf den git-Beleg beschränkt.
