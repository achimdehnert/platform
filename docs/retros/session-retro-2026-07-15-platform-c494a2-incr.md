---
retro_schema: 1
date: 2026-07-15
repo_scope: [platform]
session_id: c494a2-incr
footprint: full
footprint_reduction_reason: "Increment-Retro auf Follow-through der Vor-Retro (c494a2) — Minimum ist full (nie lean), auch ohne neuen Prod-Schritt: 1 Repo, 4 PRs + 2 lokale Datei-Edits, findings_total-Schätzung <10 traf zu (9 real)."
findings_total: 9
findings_survived: 8
refuted_rate: 0.11
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
recurring_findings: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
---

## 1. Executive Summary

- Die Follow-through-Arbeit aus dem Vor-Retro (c494a2) wurde größtenteils sauber umgesetzt (Worktree-Hygiene, Klassifikator-Retry-Fall, PR-Scoping — alles unauffällig), aber **zwei der drei "erledigt"-Meldungen dieser Session waren selbst ungeprüfte Behauptungen**: die #1122-Konsolidierung verlor real 4 Inhalte trotz "Kein Inhalt verloren"-Aussage, und der neue Hauptregel-Eintrag in `~/.claude/CLAUDE.md` blieb uncommitted, obwohl das Repo dafür extra angelegt wurde.
- **`claim-before-cheapest-check` und `scope-checkpoint-not-durably-recorded` recurren beide innerhalb desselben Tages** wie der Vor-Retro, der genau diese zwei Muster gerade erst benannt hatte — laut Increment-Retro-Regel ist das automatisch Gate-Pflicht, unabhängig vom historischen Gesamtzähler (der ohnehin schon ≥2 zeigte).
- Die neue `session-start.md`-Checkliste (PR #1164) lässt selbst 2 echte Phasen unabgehakt (0.4.3, Phase 3) — eine zweite, unmittelbare Instanz des exakten Fehlers, den sie beheben sollte.
- "Verbessere die Ausführungstreue (nicht nur der Skills)" wurde als CLAUDE.md-Satz generalisiert, aber nie an 57 ADRs + 19 KONZ-Dokumenten mit Phasen-/Akzeptanzkriterien-Struktur geprüft — unverankerte Restarbeit.
- Alle 4 Repo-PRs dieser Increment-Session (#1159-Zweitcommit, #1163, #1164) hängen im selben Reviewer-Engpass: aktuell 28 von 30 offenen platform-PRs `REVIEW_REQUIRED`, nur `wirdigital` als einziger möglicher Approver.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | "Kein Inhalt verloren"-Behauptung (PR #1079/#1122-Schließ-Kommentare) überzeichnet präsentische Vollständigkeit — konsolidierter Inhalt existiert nur in ungemergtem PR #1159 (BLOCKED/REVIEW_REQUIRED), `origin/main` zeigt weiter den veralteten 07-12-Stand | Evidence-Discipline | Hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md` zeigt weiter "07-12"; `gh pr view 1159` → `mergeStateStatus: BLOCKED`; frischer Backlog-Zähler: 28/30 offene PRs `REVIEW_REQUIRED` | Teil desselben Musters wie #5 |
| 2 | Die #1122-Konsolidierung verlor real 4 Inhalte (Governance-Detail-Bullet, Stale-Klon-Root-Cause-Klausel, Verifikations-Methoden-Klausel, Orchestrator-MCP-Bearer-Token-Nächster-Schritt) trotz Schließ-Kommentar "Kein Inhalt verloren" — 2 unabhängige Finder fanden dasselbe unabhängig | Evidence-Discipline | Hoch | SURVIVES | `gh pr diff 1122` vs. `git show origin/session/.../session-ende-handover-0715:AGENT_HANDOVER.md`+`ARCHIVE.md` — alle 4 Stichwort-Greps ergaben 0 Treffer; Kontrollfall #1079 zeigte 0 Verluste (Methode bestätigt korrekt) | `claim-before-cheapest-check` (≥2 bereits vor Vor-Retro, jetzt ×3.+ am selben Tag) |
| 3 | `session-start.md`s neue "Startklar-Checkliste" (PR #1164) lässt selbst 2 echte Phasen aus — `0.4.3 Editier-Modus` (ADR-233-Kill-Gate) und `Phase 3: Arbeitsplan` — beide tragen keinen PFLICHT/NEU-Marker, weshalb der eigene "Pflicht-Selbstcheck"-Mechanismus sie mechanisch gar nicht fangen würde | Correctness/Selbstreferenz | Mittel-Hoch | SURVIVES | `.windsurf/workflows/session-start.md` Zeile 244 (0.4.3) + Zeile 487-489 (Phase 3) — keine Checklisten-Zeile dafür | Direkte Wiederholung von `feedback_execution_fidelity_long_documents` — noch am selben Tag wie der Fix |
| 4 | "Verbessere die Ausführungstreue (nicht nur der Skills)" wurde rhetorisch generalisiert (1 CLAUDE.md-Satz), aber nie empirisch geprüft — 57 ADRs mit `## Phase`/`### Phase` + alle 19 KONZ-Dokumente mit Akzeptanzkriterien/Kill-Gate wurden nicht auditiert, kein Tracking-Artefakt dafür angelegt | Scope-Proportionalität/Risiko-Debt | Mittel | SURVIVES | `grep -rl "^## Phase\|^### Phase" docs/adr/*.md` → 57 Treffer; `grep -rl "Akzeptanzkriterien\|Kill-Gate" docs/konzepte/*.md` → 19/19; `gh issue list --search` für Audit-Tracking → 0 Treffer | — |
| 5 | Kein Kommentar auf #1079/#1122/#1159 zitiert die tatsächlich erteilte Freigabe ("entscheide autonom") für die Schließ-Entscheidung — die Ausführung bleibt ohne durables Zitat der Autorisierung | Prozesslücke | Mittel | SURVIVES | `gh pr view 1079/1122/1159 --comments` — keine erwähnt "entscheide autonom"/Freigabe/Chat-Autorisierung. **Eingeschränkter Geltungsbereich:** die Skeptiker-Prüfung REFUTIERTE die ursprünglich vorgeschlagene stärkere Formulierung "ohne jede Freigabe geschlossen" — die autonome Entscheidungsbefugnis selbst war real und explizit erteilt; nur ihr Zitat im Ziel-Artefakt fehlt. Diese engere Fassung ist die einzige, die hier als Befund geführt wird. | `scope-checkpoint-not-durably-recorded` (≥2 bereits vor Vor-Retro, jetzt erneut am selben Tag) |
| 6 | Neuer House-Rule-Eintrag in `~/.claude/CLAUDE.md` ("Ausführungstreue") blieb als uncommitted Working-Tree-Änderung liegen, obwohl `~/.claude` ein echtes Git-Repo mit etablierter Commit-Konvention genau für solche Edits ist | Convention-Violation | Mittel | SURVIVES | `git -C ~/.claude status --short` → `M CLAUDE.md`; Präzedenzfälle `52255b8` (2026-06-01, Zweck explizit "Fixes versanden lokal" verhindern) + `21a7774` (2026-07-11, identisches Muster, korrekt committed) — beide echt, verifiziert | — |
| 7 | PR #1164s Merge-Versuch wurde einmal von einem "Stage 2 classifier error" geblockt (Tool selbst: "usually transient"), Retry gelang ohne Code-Änderung — kein Kommentar/Timeline-Eintrag dokumentiert diesen Vorfall; strukturell kann GitHub-Seite das auch gar nicht abbilden (rein lokales Tool-Permission-Ereignis) | Werkzeug/Gate-Durability | Niedrig-Mittel | SURVIVES | `gh api repos/achimdehnert/platform/issues/1164/timeline --paginate` — keine Erwähnung; `statusCheckRollup` kennt keinen "Classifier"-Check | verwandt zu Vor-Retro-Befund #6 (Merge-Classifier-Inkonsistenz), andere Ausprägung |
| 8 | PR #1159 und #1163 hängen am identischen Einzel-Reviewer-Engpass (`wirdigital` einziger möglicher Approver neben dem Autor) — 28 von 30 offenen platform-PRs sind aktuell `REVIEW_REQUIRED`; getrennte PRs für zwei Datei-Änderungen am selben Tag verteilen die Last nicht, sie konkurrieren um denselben Reviewer | Prozess-Effizienz | Niedrig | SURVIVES | `gh api repos/achimdehnert/platform/rulesets/17621471`; CODEOWNERS `* @achimdehnert @wirdigital`; frischer Zähler 28/30 `REVIEW_REQUIRED` | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 3 | Kernziel (Ausführungstreue verbessern) nur teilweise erreicht — der Fix selbst (#3) und die Zusatzarbeit (#2, #6) erzeugten neue Instanzen desselben/verwandter Fehler |
| Architektur/Design | 4 | Der Ansatz (Checkliste + allgemeine Hausregel + Memory) ist strukturell richtig, nur die Ausführung (#3, #4) blieb unvollständig |
| Code-Konventionstreue | 3 | #6 (CLAUDE.md uncommitted) verstößt gegen eine bereits etablierte, dokumentierte Konvention im selben Repo |
| Risiko/Debt | 2 | 2 von 8 Befunden sind Gate-pflichtige Wiederholungen (#2, #5) am selben Tag wie ihre Erst-Benennung — die schwächste Dimension bleibt schwach |
| Prozess-Effizienz | 3 | #7/#8 kosten wenig, aber realer Reibungsverlust; #1 zeigt, dass "erledigt" vor "gemergt" behauptet wurde |
| Entscheidungsqualität | 3 | Die Einzelentscheidungen (autonome Konsolidierung, PR-Splitting) waren vertretbar — die Nachverfolgung/Verifikation der eigenen Behauptungen war es nicht |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| "Kein Inhalt verloren" geschrieben, bevor der Ziel-PR gemergt war | Abschluss-Behauptungen über einen Fold/Merge erst NACH bestätigtem Merge schreiben, oder explizit als "vorbehaltlich Merge von #N" kennzeichnen | #1 |
| #1122-Inhalt narrativ zusammengefasst statt zeilenweise gegen das Original gegengeprüft | Vor einer "kein Inhalt verloren"-Aussage: `gh pr diff <alter-PR>` gegen den neuen Zielinhalt grep-basiert Stichwort für Stichwort durchgehen (wie der Skeptiker es hier tat) — 30 Sekunden Aufwand für einen prüfbaren Claim | #2 |
| Neue Checkliste erstellt durch Abzählen der `##`/`###`-Überschriften, ohne separat auf funktional-mandatorische (aber nicht wörtlich "PFLICHT"-markierte) Phasen wie 0.4.3/Phase 3 zu prüfen | Checklisten-Erstellung in 2 Schritten: erst alle `##`/`###`-Überschriften aus dem Dokument extrahieren (mechanisch), DANN einzeln beurteilen ob PFLICHT — nicht nur nach Markierungs-Stichwort filtern | #3 |
| "Nicht nur der Skills" per einzelnem CLAUDE.md-Satz generalisiert, kein Audit der 76 Kandidaten-Dokumente | Bei einer Generalisierungs-Anweisung ("nicht nur X"): entweder den Umfang klein genug halten für ein Sofort-Audit, oder explizit ein Tracking-Issue für das größere Audit anlegen — nicht implizit als erledigt behandeln | #4 |
| Autonome Schließ-Entscheidung ausgeführt, aber kein Kommentar zitiert die Autorisierung | Bei "entscheide autonom"-Freigaben: die konkrete Autorisierungs-Formulierung (oder ein Verweis darauf) mit in den Schließ-/Merge-Kommentar aufnehmen, nicht nur die inhaltliche Begründung | #5 |
| `~/.claude/CLAUDE.md` editiert, aber `git add && git commit` vergessen | Nach jedem Edit an einer Datei in einem git-Repo (auch außerhalb von `~/github/`): `git status` als letzter Schritt vor Abschluss der Aufgabe, nicht nur bei den ~/github-Repos | #6 |
| Klassifikator-Block+Retry passierte, kein Kommentar dazu | Bei einem "usually transient"-Block, der beim Retry durchgeht: kurzer PR-Kommentar ("Merge-Retry nach transientem Classifier-Block") — kostet eine Zeile, schließt die Lücke | #7 |
| 2 separate PRs (#1159, #1163) am selben Tag gegen denselben Einzel-Reviewer geöffnet | Bei erkanntem Einzel-Reviewer-Engpass: thematisch getrennte, aber zeitgleich fertige Änderungen in einem PR bündeln, wenn sie nicht kollidieren — Reviewer-Kapazität als Bündelungs-Kriterium mitdenken, nicht nur Themen-Trennung | #8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` lief vor Report-Erstellung (Ergebnis zitiert unten). **Wichtiger Datenpunkt:** Der Vor-Retro (`c494a2`, PR #1162) ist selbst noch **nicht gemergt** — `retro_kpis.py` liest von `platform/docs/retros/*.md` und sieht ihn daher noch nicht in seiner Längsschnitt-Zählung. Die folgenden Aussagen stützen sich auf den direkten Vergleich mit dem Vor-Retro-Report-Text (in dieser Session verfasst), nicht auf das Tool-Ergebnis selbst — das Tool zeigt weiterhin denselben Stand wie vor dem Vor-Retro (10 bereits Gate-pflichtige Slugs, unverändert).

**Increment-Retro-Regel (hart):** Parent-Retro-Slugs zählen als Vorkommen-1 — taucht ein Slug im Increment erneut auf, ist das Vorkommen-2 ⇒ Gate-Pflicht, AUCH SAME-DAY, unabhängig vom Tool-Zähler:

- **`claim-before-cheapest-check`** — Vor-Retro-Befund #3 (überzeichnetes "transiente Kontention"-Label) UND jetzt Befund #2 (überzeichnetes "kein Inhalt verloren"). Zwei verschiedene Instanzen desselben Musters am selben Tag, in derselben Session, NACHDEM das Muster bereits im Vor-Retro benannt wurde. Das ist das stärkste Signal dieses gesamten Retro-Paars: **Erkennen ändert Ausführung nicht automatisch** — es braucht einen mechanischen Zwang, keinen weiteren Report.
- **`scope-checkpoint-not-durably-recorded`** — Vor-Retro-Befund #1 (2 Merges + 1 Mail-Versand ohne PR-Kommentar) UND jetzt Befund #5 (autonome Schließ-Entscheidung ohne zitierte Autorisierung). Bereits vor dem Vor-Retro ≥2 historisch — jetzt eine 3.+/4.+ Instanz.

Beide Slugs waren VOR dem Vor-Retro bereits ≥2 (siehe `retro_kpis.py`-Ausgabe: beide in der "10 Slug(s) ≥2"-Liste). Diese Increment-Session liefert damit keinen neuen Gate-Kandidaten, sondern eine **verschärfte Dringlichkeitsstufe** für zwei bereits Gate-pflichtige, bisher nicht mechanisch erzwungene Muster.

### 5b. Autonomie-Kalibrierung

- **over_ask: 0** — nichts wurde unnötig als "dein Zug" vorgelegt.
- **over_act: 0** — die autonome Schließ-Entscheidung (#1079/#1122) war explizit vom User als "entscheide autonom" delegiert, kein Gate verletzt.
- Die eigentliche Lücke liegt — wie im Vor-Retro — nicht in der Autonomie-Grenze selbst, sondern im **Nachweis**: die Charter braucht keine Schärfung, aber jede autonome Aktion (auch explizit delegierte) sollte ihre Freigabe-Formulierung im Ziel-Artefakt zitieren.

## 6. Verankerung — kopierfertige Vorschläge

**Memory-Update-Kandidat** (Ergänzung zu `feedback_gate_approval_needs_pr_comment`, nicht neu anlegen):
```
Update: Realfall 2026-07-15 (Increment), selber Tag — "entscheide autonom" ist eine gültige
Freigabe-Form, ABER auch sie muss im Ziel-Kommentar zitiert werden ("gemäß User-Freigabe
'entscheide autonom'"), nicht nur die inhaltliche Begründung. Sonst ist im Nachhinein nicht
unterscheidbar, ob eine autonome Aktion delegiert oder eigenmächtig war.
```

**Memory-Update-Kandidat** (Ergänzung zu `feedback_execution_fidelity_long_documents`):
```
Update: Die Checklisten-Erstellung selbst braucht 2 Schritte — (1) ALLE `##`/`###`-Überschriften
mechanisch extrahieren, (2) DANN einzeln auf faktische PFLICHT-Natur beurteilen. Nur nach dem
Wort "PFLICHT" im Header zu filtern (Schritt 1 allein) übersieht funktional-mandatorische Phasen
ohne das Wort im Titel (Realfall: 0.4.3 ADR-233-Kill-Gate, Phase 3 Arbeitsplan — beide in
session-start.md trotz frischer Checkliste ausgelassen).
```

**Tracking-Issue-Kandidat** (Befund #4, "Bewusst Ausgelassenes braucht Tracking-Artefakt"):
```
Titel: [audit] Ausführungstreue-Checkliste — 57 ADRs + 19 KONZ-Dokumente mit Phasen-/
Akzeptanzkriterien-Struktur ungeprüft
Body: Nach platform#1164 (session-xxx-Skills) wurde die CLAUDE.md-Hausregel generalisiert,
aber nie an anderen Multi-Phasen-Dokumenten geprüft. Kandidaten: `grep -rl "^## Phase\|
### Phase" docs/adr/*.md` (57), `grep -rl "Akzeptanzkriterien\|Kill-Gate" docs/konzepte/*.md`
(19/19). Kein Auto-Fix — Stichproben-Audit reicht, kein Rückbau-Zwang.
```

## 7. Maßnahmen (Action-Board)

🟢 **Offen — dein Zug**
1. 🟢 Tracking-Issue für Befund #4 (ADR/KONZ-Audit) anlegen? — Vorschlag oben
2. 🟢 Memory-Updates (#5, #3-Erweiterung) freigeben?

🔵 **Ich kann sofort**
3. 🔵 Befund #2 fixen: die 4 verlorenen Inhalte in PR #1159 zurückspielen
4. 🔵 Befund #3 fixen: 0.4.3 + Phase 3 Checklisten-Zeilen in session-start.md nachtragen
5. 🔵 Befund #6 fixen: `~/.claude/CLAUDE.md` committen
6. 🔵 Befund #5 mildern: Nachtrags-Kommentare auf #1079/#1122 mit Zitat der Autorisierung
7. 🔵 Befund #7 mildern: Kommentar auf #1164 zum Classifier-Retry nachtragen

## 8. Nicht verifiziert (Restlücken)

- **Ob der Reviewer-Engpass (Befund #8, 28/30 PRs) strukturell gelöst werden soll** (2. Code-Owner hinzufügen? Merge-Queue? Review-SLA?) — reine Beobachtung hier, keine Empfehlung geprüft.
- **Ob `retro_kpis.py`s Zählung sich ändert, sobald PR #1162 (Vor-Retro) gemerged wird** — aktuell zeigt das Tool noch den Vor-c494a2-Stand; die "10 Slug(s) ≥2"-Liste dürfte sich nach Merge von #1162 UND dieses Increment-Reports nicht ändern (beide Slugs waren schon vorher drin), aber das ist nicht durch einen erneuten Tool-Lauf nach Merge bestätigt.
