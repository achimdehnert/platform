---
retro_schema: 1
date: 2026-08-17
repo_scope: [platform, shared-ci, frist-hub, trading-hub, billing-hub, weltenhub, bahn-hub]
session_id: 37e8e0
footprint: deep
findings_total: 11
findings_survived: 10
refuted_rate: 0.09
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-matches-spelling-not-substance, proof-artifact-left-unmerged]
recurring_findings: [claim-before-cheapest-check, gate-matches-spelling-not-substance, proof-artifact-left-unmerged]
---

# Session-Retro 2026-08-17 — platform (`37e8e0`, Strang sharedci-vereinheitlichung)

> **Methodische Vorbemerkung, die den Rest dieses Reports einordnet:** Subagenten sind in
> dieser Umgebung per Systemanweisung untersagt. Find- und Verify-Phase liefen deshalb
> **inline** — das ist ein Bruch von Regel 1 (Richter ≠ Angeklagter) und in §8 als
> Restlücke geführt. Acht der elf Befunde sind **kommandobelegt** und damit von der
> Selbstbeurteilung unabhängig; die drei **Bewertungsbefunde** sind ausdrücklich
> **nicht falsifiziert** und als solche markiert.
>
> **NACHTRAG 2026-08-17, nach Owner-Freigabe fuer Subagenten:** Die drei
> Bewertungsbefunde #9/#10/#11 wurden in
> [`...-37e8e0-incr.md`](session-retro-2026-08-17-platform-37e8e0-incr.md)
> nachtraeglich falsifiziert. **Befund #11 ist widerlegt**, #10 trug eine falsche
> Kategorie, #9 ueberlebt mit unbelegter Kausal-Haelfte. Die Tabelle unten ist
> korrigiert; `refuted_rate` von `0.0` auf `0.09` gehoben. Die urspruengliche `0.0`
> bedeutete **nicht** laxe Falsifikation, sondern eine nicht gelaufene.

## 1. Executive Summary

- **Zielzustand erreicht, mit benannter Restmenge.** Aus „prüf den Wochenlauf" wurde die
  Vereinheitlichung der Flotte auf einen shared-ci-Stand: 32 von 40 `_ci-python`-Referenzen
  auf `v1.1.10`, vier weitere Reusables und die Action `gitleaks-scan` vollständig. Die acht
  Ausnahmen verteilen sich auf fünf Repos mit je einem dokumentierten Grund.
- **Das Tagesmuster ist ein Befund für sich: viermal prüfte eine Bedingung eine
  Schreibweise und meinte eine Sache** — Exit-Code statt Sammelergebnis, Verzeichnisname
  statt Projektdatei, Kommandotext statt PR-Anlage, Substring statt Zeilenanfang. Drei
  davon in fremdem Code, einer in meinem eigenen Skript derselben Sitzung.
- **Der Melder, der Scope-Wachstum anzeigen soll, war blind, als er gebraucht wurde:**
  14 gemeldete PRs gegen 37 tatsächliche. Die Scope-Checkpoints feuerten damit nicht
  proportional zur realen Eskalation.
- **Zwei publizierte Falschaussagen standen 50 Minuten in gemergten Artefakten**, bevor sie
  auffielen — beide entstanden dadurch, dass ich ein Log-Fenster ab der Trefferzeile las
  und die Zeilen darüber nicht prüfte.
- **Die zwei PRs, deren Mergebarkeit der ganze Beweis war, sind am Sitzungsende offen.**
  Der Wochenlauf ist als „erbracht" abgehakt, sein eigentliches Produkt liegt unverteilt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Die zwei PRs des Wochenlaufs, deren Mergebarkeit der Beweis für Prio 1 war, sind am Sitzungsende **offen**; das Produkt des Laufs (project-facts.md) ist nicht verteilt | Prozesslücke | hoch | SURVIVES (kommandobelegt) | `gh pr view` → travel-beat#82 OPEN, illustration-hub#260 OPEN `MERGEABLE/CLEAN` | neu: `proof-artifact-left-unmerged` |
| 2 | Zwei publizierte Begründungen waren falsch (`bash -e` sei schuld; `coverage_threshold` sei der beißende Regler) und standen **50 min** in gemergten Artefakten | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | #2027 gemergt `05:22:12Z`, Korrektur #2032 gemergt `06:12:29Z`; `set +e` steht in `_ci-python.yml@v1.0.11` Z. 406 | `claim-before-cheapest-check` (bereits ×≥2, gate-pflichtig) |
| 3 | Mein Handover-Skript ankerte auf den Substring `## ⚡ Aktueller Stand` und traf die Konventions-Erklärung in Zeile 6 → der neue Stand landete **in einem HTML-Kommentar** | Werkzeug | mittel | SURVIVES (kommandobelegt) | `agent_handover_freshness_check.py` → FAIL „keine datierte Überschrift in den ersten 40 Zeilen"; Gegenprobe gegen `origin/main` → PASS | `gate-matches-spelling-not-substance` |
| 4 | Die erste Flottenmessung war unvollständig: sie suchte nur `shared-ci/.github/workflows/…@ref` und übersah acht Repos mit **Action**-Referenzen (`gitleaks-scan`, sechs auf `v1.0.0`) | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | zweite `gh search code`-Formulierung lieferte 8 zusätzliche Treffer; Landschafts-Scan vorher/nachher | `gate-matches-spelling-not-substance` |
| 5 | Erstaussage „acht Repos grün ohne einen einzigen Test" war für **sechs** falsch — sechs hatten einen dokumentierten Grund, einer davon wörtlich als Owner-Entscheidung | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | Kommentare in den `ci.yml` der acht Repos; `pytest`-Zählung je Repo über alle Workflow-Dateien | `claim-before-cheapest-check` |
| 6 | Der Artefakt-Budget-Melder unterzählt strukturell: 14 gemeldet, **37** tatsächlich; 17 PRs aus einer Schleife zählen als eins, `gh api …/pulls -X POST` gar nicht | Werkzeug | hoch | SURVIVES (kommandobelegt) | `tools/claude-hooks/artefakt_budget.py:70` `_CREATE = re.compile(r"\bgh\s+(pr\|issue)\s+create\b")`; Zählstände 6→7→8→14 | `gate-matches-spelling-not-substance` |
| 7 | Derselbe Melder **übererfasst**: eine Codesuche nach seinem Muster erhöhte seinen Zähler um 1; das Dokumentieren des Defekts verstärkt ihn | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Zähler 6→7 ohne PR-Anlage; einziges Bash-Kommando dazwischen enthielt das Muster als `grep`-Argument | `gate-matches-spelling-not-substance` |
| 8 | Der Handover-PR wurde mit rotem `context-review` gemergt | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | #2034 gemergt trotz `context-review=fail`; Log: `429 Too Many Requests` beim Download von `actions/github-script` | — |
| 9 | Scope-Eskalation von „Wochenlauf prüfen" auf 37 PRs über ~30 Repos — jeder Schritt freigegeben, aber die Freigaben stützten sich auf einen Melder, der die Größe um Faktor 2,6 unterschätzte | Prozesslücke | mittel | **SURVIVES** (Skeptiker `37e8e0-incr`; Kausal-Haelfte bleibt Hypothese) | Melder-Zählstände vs. tatsächliche PR-Liste | — |
| 10 | `bahn-hub#13` wurde mit rotem `lint` gemergt (9 Ruff-Fehler, Repo seit 4. Juli unberührt) | verfrühte Festlegung | mittel | **SURVIVES, Kategorie korrigiert** -> bewusste Inkaufnahme, Severity niedrig | `gh pr checks 13` → `lint fail`; letzter grüner main-Lauf 2026-07-04 | — |
| 11 | Rework: die zwölf PRs der ersten Welle mussten nach dem Merge-Angebot erneut geöffnet und erweitert werden, weil die vollständige Landschaftsmessung erst danach lief | Prozesslücke | mittel | **REFUTED** (Skeptiker `37e8e0-incr`) | PR-Bodies der ersten Welle wurden nachträglich per `gh pr edit` ersetzt; zweiter Commit je Branch | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Zielzustand erreicht, Restmenge benannt und begründet — aber #1: das Produkt des Wochenlaufs liegt unverteilt |
| architektur_design | **4** | Beide shared-ci-Defekte zentral gelöst statt per Repo-Pflaster; Variante A entkoppelt die Entscheidung vom überschreibbaren Exit-Code |
| code_konventionstreue | **3** | Worktrees, Preflights, explizites Staging eingehalten — aber #3: eigenes Skript verletzte genau das Muster, das die Sitzung dreimal in fremdem Code anklagte |
| risiko_debt | **3** | fünf Repos außerhalb des Kanons (dokumentiert), zwei offene Mess-PRs, #1 zwei hängende PRs, #10 ein rot gemergter main |
| prozess_effizienz | **3** | #11 zwölf PRs zweimal angefasst, #4 Messung erst im zweiten Anlauf vollständig, #6 Scope-Melder blind |
| entscheidungsqualitaet | **4** | `skip_tests` nicht blind gekippt (#5 rechtzeitig korrigiert), Prod-Gates gespiegelt, Melder-Fix bewusst nicht selbst gebaut — dagegen #2 zwei publizierte Falschaussagen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Prio 1 als „erbracht" abgehakt, sobald die PRs `MERGEABLE/CLEAN` waren; die PRs blieben offen | Ein Beweis über ein Artefakt endet mit der Frage „und was passiert jetzt mit dem Artefakt?" — mergen oder ausdrücklich als offen ins Board/Handover | #1 |
| Log ab der Trefferzeile gelesen (`grep -A 25`), Zeilen darüber ungeprüft; daraus zwei Kausalbehauptungen | Bei jeder Kausalaussage über ein Skript **den ganzen Block** aus dem Ref lesen (`git show <ref>:<pfad>`), nicht das Trefferfenster | #2 |
| Anker `t.index("## ⚡ Aktueller Stand")` traf den Fließtext | Struktur-Edits an Markdown ankern zeilenweise (`l.startswith(...)`), nie per Substring über die ganze Datei | #3 |
| Erste Flottensuche nur über `workflows/…@ref` | Eine Vollständigkeits-Behauptung über eine Flotte braucht **zwei unterschiedlich formulierte** Suchen; die Differenz ist das Ergebnis, nicht der Fehler | #4 |
| „acht Repos grün ohne Tests" aus der Job-Konklusion geschlossen | Vor jedem Sweep über N Repos die N Dateien einzeln lesen — die Begründung steht im Kommentar daneben, nicht im Status | #5 |
| Melder zählt `gh pr create` im Kommandotext | Zähler auf das **Ereignis** stützen (PR-Nummer aus der Antwort), nicht auf den Kommandotext; Gegenzählung `gh pr list --author` als Kalibrierung | #6, #7 |
| `context-review` rot, trotzdem gemergt | Bei rotem Nicht-Required-Check vor dem Merge einmal die Fehlerklasse benennen (hier: `429`, extern) — dokumentiert, dann mergen | #8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-08-17): 20 Slugs stehen bereits auf Gate-Pflicht.
Diese Sitzung trägt bei:

- **`claim-before-cheapest-check`** — bereits gate-pflichtig und mit diesem Report bei
  **×44**. Der Zähler arbeitet report-weise, dieser Report trägt also **+1**; *innerhalb*
  der Sitzung sind es **zwei** Instanzen (#2, #5). Beide Male lag der billigste Check
  drei Zeilen vom gelesenen Fenster entfernt. Bei 44 Vorkommen ist die ehrliche Lesart
  nicht mehr „wiederkehrender Befund", sondern: **das bestehende Gate greift für diese
  Klasse nicht** — jede Sitzung notiert es neu, keine verhindert es.
- **`gate-matches-spelling-not-substance`** (neu, aber sofort **×4 innerhalb einer Sitzung**:
  #3, #4, #6/#7 sowie die beiden shared-ci-Defekte) — ein Gate prüft ein Zeichen und meint
  einen Zustand. Kandidat für ein echtes Gate: ein Lint über Hook-/Gate-Skripte, das
  Text-Matching auf Kommandozeilen als Zählgrundlage markiert.
- **`proof-artifact-left-unmerged`** (neu, ×1) — ein als Beweis herangezogener PR bleibt nach
  dem Beweis liegen.

Score-Vergleich gegen den Mittelwert über 78 Messpunkte: `risiko_debt` **3** gegen Ø 2,55
(besser als üblich, aber weiterhin die schwächste Dimension), `prozess_effizienz` **3** exakt
auf Ø 3,00, `zielerreichung` **4** über Ø 3,86.

### 5b. Autonomie-Kalibrierung

- **`over_ask: 0`** — nichts vorgelegt, was deterministisch und reversibel war. Grenzfall
  bewusst so entschieden: der Melder-Fix (`artefakt_budget.py`) wäre trivial gewesen, ist
  aber selbstbetreffend (Charta Art. 3) und blieb daher Vorlage.
- **`over_act: 0`** — jeder Prod-/Publish-Schritt lief auf eine wörtliche Freigabe („1 go",
  „beides go", „ich folge deiner Empfehlung"). Der einzige ungefragte PR (#2032) war die
  Richtigstellung eigener Falschaussagen, vorher angekündigt.
- **Beobachtung mit Konsequenz:** `over_act: 0` ist hier **schwächer belegt als üblich**,
  weil der Melder, der Scope-Wachstum sichtbar machen soll, um Faktor 2,6 unterzählte
  (#6). Die Aussage „im Rahmen geblieben" stützt sich damit auf meine eigene Buchführung,
  nicht auf eine unabhängige. Das ist die eigentliche Gefahr an #6.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

1. `feedback_gate_matches_spelling_not_substance` — *Eine Bedingung, die ein Zeichen prüft
   und einen Zustand meint, ist blind, wenn es darauf ankommt.* Erkennungsmerkmal: die
   Bedingung nennt einen Exit-Code / Verzeichnisnamen / Kommandotext, die Absicht daneben
   nennt einen Zustand. Zweites Merkmal: oft steht die korrekte Fassung direkt daneben.
   Billigster Check: die erwartete Erfolgsmeldung **im Log suchen**, nicht den Exit-Code
   lesen. Belege: shared-ci#55, shared-ci#56, `artefakt_budget.py:70`, eigener
   Handover-Skript-Anker. `drift: true`, `drift_episode: 2026-08-17-schreibweise-statt-sache`.
2. `feedback_proof_artifact_needs_a_landing` — *Ein PR, der als Beweis dient, ist nach dem
   Beweis nicht erledigt.* Beleg: travel-beat#82 / illustration-hub#260.
3. Ergänzung zu `feedback_fleet_measurement_github_api_tree_only` — *Eine
   Vollständigkeits-Behauptung über die Flotte braucht zwei unterschiedlich formulierte
   Suchen; die Differenz ist das Ergebnis.* Beleg: acht übersehene Action-Referenzen.

**adr_candidates** — keine. Alle Befunde sind Werkzeug- oder Prozessfragen; kein
Architektur-Entscheid berührt (`policies/adr-threshold.md`: Ergänzung nach bestehendem
Muster ⇒ kein ADR).

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Drei Bewertungsbefunde (#9, #10, #11) falsifizieren lassen — ~55k je, ~165k gesamt
2. 🟢 travel-beat#82 + illustration-hub#260 mergen oder bewusst schließen
3. 🟢 Melder-Fix `artefakt_budget.py` freigeben (selbstbetreffend)

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | Gate gegen Text-Matching-Zähler | platform | — | 🔵 ready | ich: Konzept |
| 5 | Memory-Kandidaten schreiben | platform | — | 🔵 ready | du: freigeben |

### ✅ Erledigt

| # | Item | Beleg |
|---|---|---|
| 6 | Beide shared-ci-Defekte zentral behoben | `v1.1.9`, `v1.1.10` |
| 7 | Falschaussagen richtiggestellt | #2032, shared-ci#54 |
| 8 | Handover + Memory gesichert | #2034, 2 pgvector-Einträge |

## 8. Nicht verifiziert (Restlücken)

| # | Lücke | Billigster Check |
|---|---|---|
| 1 | **Regel-1-Bruch:** Find- und Verify-Phase liefen inline, ohne frischen Kontext. Die acht kommandobelegten Befunde sind davon unabhängig; #9, #10, #11 sind **unfalsifizierte Selbstbeurteilung** | drei Sonnet-Skeptiker, je ein Befund, ~55k je |
| 2 | **Phase 5 (Meta-Reviewer) nicht gelaufen** — dieser Report ist nicht gegen die Skill-Regeln gegengelesen worden. Die eine Zahl, die der Meta-Reviewer numerisch einordnen müsste, steht hier roh: `refuted_rate 0.00` gegen die Vorgänger `0.22 · 0.21 · 0.00 · 0.06 · 0.33 · 0.43 · 0.25 · 0.05`. Das Band-Kriterium „<0,2 ⇒ Falsifikation ist Theater" trifft formal zu — hier aber nicht, weil die Falsifikation **schlecht** war, sondern weil sie **gar nicht stattfand**. Eine `0.00` aus Nicht-Ausführung ist im Längsschnitt von einer `0.00` aus laschen Skeptikern nicht unterscheidbar | ein Sonnet-Subagent mit Report + Skill, ohne Session-Kontext |
| 3 | Post-Merge-CI-Zustand von ~7 Repos (bahn-hub, lastwar-bot, illustration-fw, iil-fieldprefill, decks-hub, meiki-hub, dms-hub) **nicht abfragbar** — `gh api repos/…/commits/<branch>` und `gh run list` lieferten intermittierend 404/leer bei intaktem Rate-Limit (4999/5000) und funktionierender Positivkontrolle auf platform | später erneut `gh run list --repo <r> --branch main -L 3`; leere Antwort ist **kein** grüner Zustand |
| 4 | Ob `bahn-hub` main durch #10 tatsächlich rot steht — folgt aus Lücke 3 | dito |
| 5 | Release-Datum von `openai` 3.1.0 (Grundlage für „mein Merge war Auslöser, nicht Ursache" bei weltenhub) | `pip index versions openai` |
| 6 | Der Melder-Zählstand „+6 seit der letzten Nachricht" ist nur teilweise erklärt (2 durch Selbstdokumentation, 1 durch den Handover-PR); der Rest ist offen | Fensterlogik in `messe_kontext()` lesen |

**Der Vierer:** *getan* — Flotte auf einen Stand gebracht, zwei zentrale Defekte behoben,
zwei Repos aus dem Test-Blindflug geholt, Stand gesichert. *angenommen* — dass die acht
kommandobelegten Befunde ohne Skeptiker tragen (reproduzierbare Kommandoergebnisse).
*nicht verifizierbar* — die sechs Lücken oben, allen voran der fehlende fremde Kontext.
*offen geblieben* — fünf Repos außerhalb des Kanons, zwei Mess-PRs, zwei hängende
Beweis-PRs, der Melder-Fix.
