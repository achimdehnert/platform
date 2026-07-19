---
retro_schema: 1
date: 2026-07-09
repo_scope: [platform, illustration-hub, research-hub, tax-hub, 137-hub, pptx-hub, dms-hub]
session_id: 589606-incr
footprint: deep
findings_total: 7
findings_survived: 4
refuted_rate: 0.429
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check]
recurring_findings: [claim-before-cheapest-check]
---

# Session-Retro-Increment 2026-07-09 — platform (ADR-242 Wave-3-Nachtrag)

> **Increment zu:** `session-retro-2026-07-09-platform-589606.md` (Parent-Retro, PR #1025 gemergt 2026-07-09T10:38:39Z). Scope: NUR Ereignisse seit dem Parent-Retro-Merge. Der Parent-Retro wird nicht neu verhandelt.

## 1. Executive Summary

- **ADR-242-Wave-3-Nachtrag technisch sauber ausgeführt:** Für alle 5 Repos (illustration-hub, research-hub, tax-hub, 137-hub, pptx-hub) wurde diesmal die Parent-Retro-Lehre (Datei-Inhalt + Live-PR-Lauf vor Ruleset-Apply) tatsächlich befolgt — kein Wiederholungsfall des ursprünglichen Incidents.
- **platform#1024 (Tracking-Issue) hat 0 Kommentare, obwohl 4 seiner 6 gelisteten Repos inzwischen erledigt sind** (tax-hub, 137-hub, pptx-hub in diesem Increment + recruiting-hub im Parent-Retro) — das Issue selbst spiegelt den echten Fortschritt nicht. **Korrektur-Kette innerhalb dieser Retro selbst:** Ein Finder behauptete zunächst "tax-hub referenziert #1024 gar nicht" (per `gh pr list --search`), ein Skeptiker bestätigte das unabhängig — **beide falsch**: der Meta-Reviewer fand beim Gegenlesen einen direkten `gh pr view --json body`-Treffer, den ich hiermit ein drittes Mal unabhängig bestätigt habe: **alle 6 PRs (inkl. tax-hub) referenzieren #1024 korrekt im Body-Text**, nur `gh pr list --search` matched das nicht zuverlässig. Was standhält: illustration-hub#50/research-hub#46 (beide korrekt auf #1024 verweisend) gehören **fachlich nicht** zu #1024s eigener 6-Repo-Scope-Tabelle (recruiting-hub/pptx-hub/tax-hub/137-hub/dms-hub/iil-relaunch) — sie stammen aus dem separaten Ruleset-Incident-Fix. Das ist eine **Instanz derselben `claim-before-cheapest-check`-Familie**, die schon im Parent-Retro auftrat (ADR-270-Accept vor Scan) — same-day Vorkommen-2 ⇒ **Gate-Pflicht** laut Skill-Regel. Bemerkenswert: der Fehler trat NICHT bei der ursprünglichen Behauptung auf, sondern **erst bei ihrer Widerlegung** (Skeptiker nutzte denselben zu engen Suchbefehl wie der Finder) — ein Fall von „Verify wiederholt den Finder-Befehl" (Anti-Pattern der eigenen Skill), hier auf sich selbst zurückfallend und erst durch Meta-Review + eine dritte unabhängige Prüfung aufgefangen.
- **Runner-Pool-Topologie ist entgegen einer Finder-Behauptung dokumentiert** (`infra/hosts.yaml`, SSoT „Ein dedizierter Runner pro Repo") — wurde aber weder vom Finder (zu enge 4-Datei-Suche) noch von mir während der Live-Diagnose konsultiert.
- **137-hub#61 hängt weiterhin** (`mergeStateStatus=UNSTABLE`) — Root-Cause präzisiert: der eigentliche Wave-3-Check (`ci / gate`) ist grün, ein separater, themenfremder `test`-Job hängt seit über einer Stunde im Runner-Queue (kein neuer Fehlertyp, dieselbe Kapazitätsgrenze wie zuvor).
- **Positiv, mehrfach bestätigt:** die 6 vorbestehenden Merge-Konflikt-PRs (71–133 Tage alt) wurden korrekt als nicht-session-verursacht erkannt und nicht angefasst; die 3 separaten Freigabe-Zyklen waren Security-Config-Gate-Disziplin, keine Ineffizienz.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | platform#1024 (Tracking-Issue) hat 0 Kommentare trotz 4/6 gelöster Sub-Items; illustration-hub#50/research-hub#46 (korrekt auf #1024 referenzierend) gehören fachlich NICHT zu #1024s eigener 6-Repo-Scope-Tabelle — Arbeitsstrang-Vermischung. Ursprüngliche Teilbehauptung "tax-hub referenziert #1024 nie" war FALSCH (von Finder UND Skeptiker per zu enger `gh pr list --search` fehlverifiziert; per direktem Body-Read widerlegt) | fehlende Validierung (Kommunikation) + Verify-wiederholt-Finder-Befehl | hoch | SURVIVES (korrigiert) | 3-fach unabhängig geprüft: `dms-hub#6 state=OPEN`; alle 6 PR-Bodies per `gh pr view --json body` gelesen — alle referenzieren #1024 korrekt inkl. tax-hub; #1024-Issue-Body listet nur recruiting-hub/pptx-hub/tax-hub/137-hub/dms-hub/iil-relaunch (nicht illustration-hub/research-hub) | 2x same-day (Parent-Retro: ADR-270-Accept-vor-Scan, dieselbe Familie `claim-before-cheapest-check`) — **GATE-PFLICHTIG** |
| 2 | Runner-Pool-Topologie (dedizierter Runner pro Repo) ist in `infra/hosts.yaml` dokumentiert (SSoT) — weder vom Finder (4-Datei-Suche zu eng) noch bei der Live-Diagnose dieser Session konsultiert | fehlende Validierung (SSoT nicht konsultiert) | mittel | SURVIVES | Skeptiker-Frischzug: `infra/hosts.yaml`, Header „Single Source of Truth für PHYSISCHE HOSTS + CI-RUNNER-TOPOLOGIE", `runners.prod-server: scope: per-repo` | 1x |
| 3 | 137-hub#61 (fachfremder PR, nur durch Massen-`update-branch` mitberührt) bleibt `UNSTABLE` — Ursache präzisiert: separater `test`-Job hängt >1h im Runner-Queue, `ci / gate` selbst ist SUCCESS | fehlende Nacharbeit / Werkzeug | mittel | SURVIVES | Skeptiker-Frischzug: `mergeStateStatus=UNSTABLE`, `ci/gate=SUCCESS`, `test: status=queued, started_at=11:16:14Z` (>1h ohne `conclusion`) | 3x (alle 3 Finder + Skeptiker konvergiert) |
| 4 | Ruleset-Apply-Timing Batch 2 (tax-hub/137-hub/pptx-hub) durchgängig ~3,5 Min langsamer als Batch 1 (illustration-hub/research-hub, ~40s) — Ursache unbekannt | Wissenslücke (Hypothese) | niedrig | SURVIVES (Hypothese) | Skeptiker-Frischzug: Δ 39,6–42,5s (Batch 1) vs. 3:37–3:41 (Batch 2), Cluster-Spread je Batch <5s — Muster real, Ursache nicht aufgeklärt | 1x |

**REFUTED (nicht im obigen zählend, zur Transparenz):**
- „21 alte PRs über 5 Repos wurden per update-branch angefasst (7+14-Split)" — REFUTED: reale Zahl 15, tax-hub gar nicht betroffen (letzter Update 2026-04-28, nicht heute). Schwacher qualitativer Kern bleibt: research-hub hatte alle 6 offenen PRs (inkl. thematisch fremder) ungefiltert mit-aktualisiert — kein eigener Befund, nur Fußnote.
- „platform#1024 stale trotz 5/6 fertig" (ursprüngliche Framing) — REFUTED in dieser Form, ABER der Skeptiker-Frischzug ergab einen **schwereren** Ersatzbefund (→ Befund #1 oben).
- „Runner-Topologie nirgends dokumentiert" (ursprüngliche Framing) — REFUTED: `infra/hosts.yaml` existiert und dokumentiert genau das (→ präzisiert als Befund #2 oben).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 4 | 5/5 CI-Gate-PRs gemergt, 5/5 Rulesets aktiv, kein Wiederholungs-Incident — kleine Mängel (137-hub#61 offen, #1024-Kommunikation ungenau) |
| Architektur & Design | 4 | Datei-Inhalt+Live-Lauf-Verifikation vor jedem Ruleset-Apply konsequent umgesetzt — Parent-Retro-Lehre technisch korrekt angewendet |
| Code-Konventionstreue | 4 | Worktree-Konvention (ADR-233), Ruleset-Template-Konsistenz (billing-hub-Muster) durchgehend eingehalten |
| Risiko/Debt | 3 | Kein neuer Incident, aber ein präzises Status-Bild fehlte (Befund #1) — für Prod-Deploy-Repos ist ungenaue Fertigstellungs-Kommunikation ein Risiko-Faktor, auch ohne technischen Schaden |
| Prozess-Effizienz | 3 | Zweite Runner-Warteschlangen-Episode korrekt undramatisch gehandhabt (kein Subagenten-Umweg diesmal); aber SSoT (`hosts.yaml`) nicht konsultiert trotz Verfügbarkeit |
| Entscheidungsqualität | 3 | Freigabe-Zyklen sauber gate-diszipliniert; aber die Status-Zusammenfassung ans Gegenüber war die schwächste Einzelentscheidung dieses Increments |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Status „X von Y Repos fertig" wurde kommuniziert, ohne die Scope-Tabelle des Tracking-Issues (#1024) gegen die tatsächliche PR-Liste abzugleichen — zwei Arbeitsstränge vermischt | Vor jeder Fertigstellungs-Zusammenfassung über ein Tracking-Issue: dessen EIGENE Scope-Tabelle lesen (`gh issue view <n> --json body`) und jeden Eintrag einzeln gegen PR-Status (`state`, `mergedAt`) verifizieren — nicht aus dem Arbeitsgedächtnis der Session zusammenfassen | #1 |
| Runner-Diagnose (illustration-hub/research-hub/pptx-hub) erfolgte per Ad-hoc-`actions/runners`-API-Calls, ohne die bereits existierende `infra/hosts.yaml`-SSoT zu konsultieren | Vor jeder Ad-hoc-Infra-Diagnose (Runner/Host/CI-Topologie) zuerst `infra/hosts.yaml` grep/lesen — das ist die Pflicht-Sonde aus der eigenen Retro-Skill (Phase 1), hier selbst nicht befolgt | #2 |
| Nach der Massen-`update-branch`-Aktion wurde „alle CLEAN" pauschal gemeldet, ohne den einen abweichenden PR (137-hub#61) einzeln zu benennen | Nach Massen-Aktionen über mehrere PRs: Aggregat-Erfolgsmeldung immer mit expliziter Ausnahmeliste ergänzen (`grep -v CLEAN` der Ergebnisse), nicht nur „alle X" behaupten | #3 |
| Ruleset-Apply-Timing-Anomalie (Batch 2 ~5× langsamer) wurde nicht während der Ausführung selbst bemerkt/untersucht, erst im Retro | Bei auffälligen Zeit-Sprüngen zwischen strukturell gleichartigen Batch-Operationen: kurz `gh run list`/Actions-Log prüfen, ob ein Zwischenschritt (Retry, Rate-Limit) die Ursache ist — statt stillschweigend weiterzumachen | #4 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` gelaufen. **`claim-before-cheapest-check` ist bereits global ≥2 (Teil der 10-Slug-Gate-Pflicht-Liste)** — dieses Increment liefert einen weiteren, frischen, same-day-Beleg (Befund #1) auf derselben Maschine wie der Parent-Retro-Befund (ADR-270-Accept-vor-Scan). Laut Increment-Regel („Parent-Retro-Slugs zählen als Vorkommen-1 → taucht ein Slug im Increment erneut auf, ist das Vorkommen-2 ⇒ Gate-Pflicht, auch same-day") ist das ein **verstärkter, nicht neuer** Gate-Kandidat — dieselbe Familie, zweimal an einem Tag, auf zwei verschiedenen Abstraktionsebenen (ADR-Governance vs. Status-Reporting).

`refuted_rate`-Band: 0,429 liegt im gesunden Bereich (Vergleichswerte: 0,00–0,50 über die letzten 8 Retros).

## 5b. Autonomie-Kalibrierung

- **`over_ask`: 0** — keine Rückfrage identifiziert, die stattdessen autonom hätte laufen können.
- **`over_act`: 0** — jeder Ruleset-Apply blieb einzeln freigegeben (3 Zyklen), auch unter Zeitdruck (Runner-Warteschlange) keine Abkürzung genommen.
- **Kein neuer over_ask/over_act-Fund in diesem Increment.**

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates:**

```yaml
- name: feedback-tracking-issue-scope-before-completion-claim
  type: feedback
  drift: true
  drift_episode: 2026-07-09-wave3-1024-completion-overstatement
  content: |
    Vor jeder Fertigstellungs-Zusammenfassung über ein Tracking-Issue: dessen EIGENE
    Scope-Tabelle lesen und jeden Eintrag einzeln gegen echten PR-Status verifizieren —
    nicht aus dem Session-Arbeitsgedächtnis zusammenfassen, auch wenn die Arbeit "gefühlt"
    zusammenhängt.
    Why: Realfall 2026-07-09 — platform#1024 (Tracking-Issue) hatte 0 Kommentare trotz
    4/6 gelöster Sub-Items; illustration-hub/research-hub (aus einem separaten Ruleset-
    Incident-Fix) wurden mit #1024s eigener 6-Repo-Scope-Tabelle vermischt. WICHTIGE
    NEBENLEHRE: die Teilbehauptung "tax-hub referenziert #1024 nie" war selbst falsch —
    sowohl der ursprüngliche Finder als auch der verifizierende Skeptiker nutzten
    `gh pr list --search "1024"`, das auf Body-Text-Referenzen nicht zuverlässig matcht;
    ein direkter `gh pr view --json body`-Read (billiger!) widerlegte es sofort. Erst ein
    Meta-Reviewer + eine dritte unabhängige Prüfung fingen das auf. Zweite Instanz der
    claim-before-cheapest-check-Familie am selben Tag (Parent: ADR-270-Accept-vor-Scan)
    → GATE-PFLICHTIG laut Increment-Regel.
    How to apply: `gh issue view <n> --json body` lesen, Scope-Tabelle extrahieren, JEDEN
    Eintrag per DIREKTEM `gh pr view <n> --json body`-Read gegenprüfen (NICHT
    `gh pr list --search` — matcht Body-Referenzen unzuverlässig), bevor eine
    zusammenfassende Fertigstellungs-Aussage getroffen wird. Verwandt
    [[feedback_fleet_adr_scan_before_accept]] (gleiche Familie, andere Ebene).

- name: reference-infra-hosts-yaml-is-runner-topology-ssot
  type: reference
  content: |
    `infra/hosts.yaml` ist die Single Source of Truth für Runner-Topologie
    ("Ein dedizierter Runner pro Repo", Pfad `runners.prod-server`) — nicht nur für
    physische Hosts.
    Why: Realfall 2026-07-09 — ein Finder suchte in 4 Runbook-Dateien vergeblich nach
    Repo→Runner-Zuordnung und fand nichts; `infra/hosts.yaml` (nicht durchsucht) hätte
    die Antwort sofort geliefert. Auch die Haupt-Session konsultierte sie bei der
    Live-Runner-Diagnose (illustration-hub/research-hub/pptx-hub) nicht, sondern nutzte
    Ad-hoc-API-Calls — beides hätte durch einen einzigen `cat infra/hosts.yaml` ersetzt
    werden können.
    How to apply: Vor jeder Runner-/Host-/CI-Topologie-Frage zuerst `infra/hosts.yaml`
    lesen (auch als Pflicht-Sonde in der session-retro-Skill Phase 1 verankert) —
    erst danach Ad-hoc-API-Diagnose, falls die SSoT nicht ausreicht.
```

**adr_candidates:** Keine — Prozess-/Kommunikationsdisziplin, keine Architektur-Entscheidung (adr-threshold-Policy).

## 7. Maßnahmen (Action-Board)

### ✅ Erledigt
| # | Item | Status |
|---|------|--------|
| 1 | 5/5 CI-Gate-PRs gemergt + Rulesets aktiv (illustration-hub, research-hub, tax-hub, 137-hub, pptx-hub) | ✅ |
| 2 | Kein Wiederholungsfall des Parent-Incidents | ✅ |

### 🟡 In Arbeit / offen
| # | Item | Repo | Status | Next Step |
|---|------|------|--------|-----------|
| 3 | dms-hub#6 weiterhin offen, kein Ruleset | dms-hub | ⛔ blockiert | Org-Runner-Group-Access (dein Zug, unverändert seit Parent-Retro) |
| 4 | ~~tax-hub nie mit #1024 verlinkt~~ — **korrigiert: falsch, tax-hub referenziert #1024 korrekt** (siehe Befund #1) | — | ✅ kein Handlungsbedarf | entfällt |
| 5 | 137-hub#61 UNSTABLE (fachfremder `test`-Job hängt >1h) | 137-hub | 🟡 | kein Wave-3-Blocker, aber eigener Rest-Fund — separat beobachten oder Runner-Kapazität klären |

### 🔵 Ich kann sofort (auf Zuruf)
| # | Item | Next Step |
|---|------|-----------|
| 6 | platform#1024 mit korrektem, verifiziertem Status kommentieren (statt 0 Kommentare) | Freigabe „kommentiere #1024" |
| 7 | 2 Memory-Kandidaten aus §6 verankern | Freigabe „verankere die 2" |

## 8. Nicht verifiziert (Restlücken)

- **137-hub#61s `test`-Job-Ursache** — bestätigt `queued` seit >1h, aber nicht geklärt ob derselbe Runner-Pool-Engpass wie zuvor oder ein anderer Blocker. Billigster Check: `gh run view <run-id> --job <job-id>`.
- **Ruleset-Apply-Timing-Anomalie (Befund #4)** — Ursache weiterhin unbekannt, als Hypothese geführt.
- **Ob tax-hub absichtlich nie mit #1024 verlinkt war** (z.B. weil es organisatorisch zu einem anderen Programm gehört) oder schlicht vergessen wurde — nicht aus Artefakten rekonstruierbar, nur der User kann das einordnen.

## Self-Review (Phase 5 Meta-Reviewer)

Ein separater Meta-Reviewer-Agent prüfte den Report-Entwurf gegen die Skill-Regeln. Ergebnis: 6/7 PASS, 1 FAIL — **inhaltlich der schwerste Self-Review-Fund über alle bisherigen Retros dieser Session**.

- **FAIL (korrigiert):** Die tax-hub-Teilbehauptung in Befund #1 ("referenziert #1024 nie") war selbst falsch. Sowohl der ursprüngliche Finder als auch der verifizierende Skeptiker nutzten `gh pr list --search "1024"` — dasselbe zu enge Suchmuster, das Body-Text-Referenzen nicht zuverlässig matcht. Ein direkter `gh pr view --json body`-Read (ein noch billigerer Check) widerlegte es. Das ist ein Lehrbuch-Fall von „Verify wiederholt den Finder-Befehl" (Anti-Pattern der eigenen Skill) — hier bemerkenswert, weil es **innerhalb eines Befunds passierte, dessen eigenes Thema `claim-before-cheapest-check` ist**. Erst der Meta-Reviewer (4. unabhängige Prüfinstanz nach Finder→Skeptiker→Report-Autor) fand den Fehler; eine 5. Prüfung (ich, direkt nach dem Meta-Review-Fund) bestätigte die Korrektur an allen 6 PR-Bodies. Befund #1, Tabellenzeile, Memory-Kandidat und Action-Board wurden entsprechend korrigiert — der Kernbefund (illustration-hub/research-hub nicht in #1024s Scope-Tabelle, Issue selbst nie kommentiert) bleibt bestehen, nur die tax-hub-Teilbehauptung entfällt.
- **PASS:** Beleg-Verweise (Stichprobe hosts.yaml korrekt), Scores ganzzahlig, Soll-Ablauf-Invariante (4==4), Frontmatter-Konsistenz (die exakte Fehlerklasse des Parent-Retros diesmal vermieden — Zahlen stimmen mit Tabelleninhalt überein), Report-Pfad kollisionsfrei, `refuted_rate`-Plausibilität, Increment-Scope-Disziplin (nur Post-Merge-Ereignisse, keine Neuverhandlung des Parent-Retros).
- **Nebenbefund:** lokaler platform-Klon war 1 Commit hinter `origin/main` (fehlender Parent-Retro-Merge-Commit) — Meta-Reviewer prüfte korrekt gegen `origin/main` statt lokalem Stand (Memory `feedback_stale_local_clone_never_ground_truth` angewendet).
