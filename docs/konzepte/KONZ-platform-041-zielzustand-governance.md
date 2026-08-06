---
concept_id: KONZ-platform-041
title: Zielzustand-Governance — ADR-Invarianten verdrahten statt neu deklarieren
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: [platform:ADR-211, platform:KONZ-platform-037, platform:KONZ-platform-038]
adr_threshold: "Kein sofortiger org-weiter ADR. Das invariants-Frontmatter-Schema (D1) ist ein Amendment-Kandidat an die betroffenen Pilot-ADRs; ein org-weiter ADR erst NACH bestandenem Kill-Gate (Muster KONZ-038: Entscheidung folgt Wirksamkeitsnachweis, nicht umgekehrt)."
review_by: 2026-09-06
kill_criteria: "K-A/K-B/K-C in §13, UND-verknüpft, Stichtag Tag 15 nach Pilot-Merge mind. jedoch 2 Ritual-Fenster; bei Nichterfüllung wird GESTRICHEN, nicht nachgebessert (Härte-Klausel wörtlich aus KONZ-037)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/konzepte/KONZ-platform-037-betriebszustand-als-spec.md, commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: direct}
  - {claim_id: C2, source_path: docs/konzepte/KONZ-platform-038-regel-lebenszyklus-evidenz-ritual.md, commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: direct}
  - {claim_id: C3, source_path: policies/zielzustand.md, commit_or_pr: "platform#1801 (gemergt 2026-08-06, 319af164)", opened_in_session: true, provenance: direct}
  - {claim_id: C4, source_path: scripts/drift_check.py, commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: direct}
  - {claim_id: C5, source_path: scripts/adr_audit.py, commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: direct}
  - {claim_id: C6, source_path: "docs/adr/ADR-167-*.md (drift_check_paths/staleness_months-Felder; grep scripts/+tools/ = 0 Konsumenten)", commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: subagent-steelman+diabolus}
  - {claim_id: C7, source_path: "docs/adr/ADR-151, ADR-037, ADR-186 (Destillations-Stichprobe 0/3 sauber; Status-Widersprüche Frontmatter vs Body)", commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: subagent-diabolus}
  - {claim_id: C8, source_path: "docs/konzepte/ (40 KONZ; 6 überfällig-ungepflegt, 1 vollzogen → Lifecycle-Vollzugsquote ~14%)", commit_or_pr: "Zählung 2026-08-06", opened_in_session: true, provenance: subagent-maintainer2028}
  - {claim_id: C9, source_path: "docs/adr/ Statuszählung: 181 accepted / 45 proposed / 8 superseded / 3 void (239 ADR-*.md; Zählweisen differieren 239-242)", commit_or_pr: "Zählung 2026-08-06", opened_in_session: true, provenance: subagent-diabolus+maintainer2028}
  - {claim_id: C10, source_path: "docs/governance/sunset-ledger.md (existiert, 0 Einträge)", commit_or_pr: origin/main@319af164, opened_in_session: true, provenance: subagent-steelman}
  - {claim_id: C11, source_path: "git log --diff-filter=A -- docs/adr/ → 305 ADR-Datei-Adds seit 2026-01 (~40/Monat, Renames zählen mit)", commit_or_pr: "Messung 2026-08-06, origin/main", opened_in_session: true, provenance: direct}
created: 2026-08-06
---

# KONZ-platform-041 — Zielzustand-Governance: ADR-Invarianten verdrahten statt neu deklarieren

**Tier-Entscheidung: T3** — Cross-Repo (platform + risk-hub Pilot, org-weite Option), neuer
Lifecycle-Baustein (Invarianten im ADR-Frontmatter), berührt SSoT-Fragen. Auto-Eskalation
greift mehrfach; keine Selbsteinstufungs-Frage. Adversarialer Fan-out mit drei unabhängigen
Agenten (Steelman / Advocatus Diabolus / Maintainer-2028) durchgeführt am 2026-08-06;
Konfliktmatrix in §6.4.

## 1 Executive Summary

**Basis:** Die Org hat Soll-Deklaration und Ist-Prüfung **beide bereits gebaut — und nie
miteinander verbunden**: 45–50 ADRs tragen maschinenlesbare Drift-Felder
(`drift_check_paths`, `staleness_months`), für die **kein Runner existiert** (grep über
`scripts/` + `tools/`: 0 Konsumenten, C6); `scripts/drift_check.py` prüft Cross-Repo-Drift,
aber gegen **hartkodierte** Regeln statt gegen ADRs (C4). Belegte Folge: ADR-Drift wird per
Zufall gefunden, nicht per Gate (ADR-167 HealthBypass-Drift; risk-hub `.delay()` trotz
ADR-052 — beide monatelang unentdeckt, beide nur als 🌀-Memory statt als ADR-Konsequenz).
Zugleich kennt der ADR-Bestand (181 accepted, 45 proposed im Limbo, 8 superseded, C9)
praktisch nur eine Richtung: Anbau.

**Analyse:** Das Problem ist keine fehlende Deklarationsschicht, sondern die **fehlende
Kante** zwischen existierenden Enden — plus fehlender Rückbau-Pfad für ADRs (KONZ-038 hat
ihn nur für Regeln gebaut). Ein ursprünglicher Entwurf dieses Konzepts (separate
`zielzustand.yaml` als abgenommenes LLM-Destillat über alle accepted ADRs) wurde im
adversarialen Review **falsifiziert** und ist gestrichen: Destillations-Stichprobe 0/3
sauber (C7), Abnahme+Regeneration strukturell unvereinbar, Voll-Coverage bei gemessener
Lifecycle-Vollzugsquote von ~14 % (C8) nicht wartbar.

**Fazit:** Zielzustand-Governance heißt hier: (1) Invarianten leben **im ADR-Frontmatter**
(SSoT bleibt das ADR), (2) ein **budgetierter Runner** führt sie aus — gegen das Ziel wird
immer getestet, (3) „100 % definiert" wird als **100 % Klassifikation** maschinell erzwungen
(Delta-Selbsttest, Invariante 0) bei budgetierter Prüftiefe, (4) jeder rote Befund mündet
nach fester Regel in eine **Zwei-Arme-Entscheidung**: Ist anpassen ODER ADR
amend/supersede — Rückbau statt Anbau.

**Handlungsempfehlung:** MVC in §12 (D1–D6) umsetzen — Pilot platform + risk-hub, Erst-
Rückbau-Kandidat ist der belegte ADR-052/`.delay()`-Fall. Kill-Gate §13 vorab registriert.

## 2 Scope & Evidenzbasis

**Im Scope:** Die Entscheidungsschicht (ADRs, Pilot-Auswahl) zweier Repos: platform
(trägt zugleich die org-bindenden Entscheidungen) und risk-hub (belegter Drift-Fall).
Verdrahtung: Frontmatter-Invarianten → mechanische Projektion → Runner in CI/Ritual →
Zwei-Arme-Auflösung.

**Nicht im Scope:**
- **Steuerungsschicht** (Memory, Skills, Policies, Hooks): bleibt vollständig bei
  KONZ-038 (C2). Die Owner-Weisung 2026-08-06 „Memory-Rückbau-Default = Löschen statt
  deprecate" wird als **Amendment-Vorschlag an KONZ-038 §5.4** formuliert (§12 D6), hier
  nicht entschieden — sonst baut dieses Konzept den Parallel-Pfad, den es bekämpft.
- **Betriebszustand** von Diensten: KONZ-037 (C1). Von dort werden Mechaniken *geborgt*
  (Negativprobe, Budget, 5-rote-Läufe-Regel), nicht dupliziert.
- **Oberflächen**: ADR-211.
- **Org-weiter Rollout über die zwei Pilot-Repos hinaus**: explizit erst nach bestandenem
  Kill-Gate (§13) — die Selbstbeschränkungs-Klausel aus KONZ-037 („keine Übertragung vor
  der eigenen Bilanz") wird wörtlich übernommen.

**Evidenzbasis:** Manifest im Frontmatter. Direkt geöffnet in dieser Session: C1–C5.
Subagenten-verifiziert (drei unabhängige Reviewer, Pfade/Zeilen in deren Berichten):
C6–C10. Zahlenbestand mit Zählweisen-Caveat: 239–242 ADR-Dateien (C9).
**ADR-Zuwachsrate — nachgemessen (C11):** `git log --diff-filter=A -- docs/adr/` ergibt
**305 ADR-Datei-Adds seit 2026-01** (~40/Monat; Caveat: Renames/Moves zählen als Adds,
netto-Bestand ~240). Die im Review angenommene Rate (+60/Jahr) war fast eine
Größenordnung zu NIEDRIG — Voll-Coverage ist damit noch klarer unbezahlbar und das
Budget-Modell (D3) noch klarer alternativlos.

## 3 Infrastruktur-Fit

Alle Bausteine existieren; das MVC ist Komposition, kein Neubau (Steelman-Kernbefund):

| Baustein | Existiert als | Rolle hier |
|---|---|---|
| ADR-Frontmatter-Parse + CI-Diff-Gate | `scripts/gen_adr_index.py` → `index.json` | Generator bekommt zweite Emissions-Stufe (D2) |
| Drift-Felder je ADR | 45–50 ADRs, `drift_check_paths`/`staleness_months` (C6) | Migration in `invariants:`-Frontmatter (D1) |
| Cross-Repo-Prüf-Skelett | `scripts/drift_check.py` (C4) | Runner-Skelett (D3) |
| Negativprobe, Budget, `dormant`, 5-rote-Läufe-Regel | KONZ-037 §4.1/§4.2/§10.5 (C1) | wörtlich übernommen (D3, D5) |
| Ritual-Scheduling + Ausfall-Flip `stale` | KONZ-038 D3, `regel-ritual.yml`, Issue #1640 (C2) | Report-Kadenz, kein eigener Scheduler (D5) |
| Supersede-Nummernvergabe + Race-Guard | `scripts/adr_next_number.py`, `adr_open_pr_guard.py` | Rückbau-ADR-Stub (D5) |
| Sunset-Ledger (append-only) | `docs/governance/sunset-ledger.md`, 0 Einträge (C10) | jeder Rückbau loggt dorthin (D5) |
| Frontmatter-Schema-Validierung | iil-adrfw (`schemas`, `checkers/python_ast`, `freshness`) | `invariants:`-Schema + AST-Check-Typ (D1, D3) |

## 4 Steelman (des Vorhabens)

1. **Deklarations-Lücke ist belegt, nicht vermutet:** maschinenlesbare Soll-Felder ohne
   einen einzigen Konsumenten (C6) sind exakt der Zustand „deklariert, aber wirkungslos",
   den KONZ-037 als gefährlicher als Regellosigkeit einstuft — falsches Vertrauen.
2. **Drift ist zweifach dokumentiert und lag jeweils monatelang unentdeckt** (ADR-167,
   ADR-052/risk-hub) — beide per Zufall gefunden. Ein Runner hätte beide am ersten Lauf
   gemeldet; der `.delay()`-Fall ist ein Ein-Zeilen-AST-Check (iil-adrfw
   `checkers/python_ast`).
3. **Die Policy-Grundlage ist gemergt und bindend** (`policies/zielzustand.md`, C3):
   „existiert ein Artefakt mit Akzeptanzkriterien, IST das der Zielzustand — referenzieren
   statt neu erfinden." Bei ~240 ADRs ist Referenzieren ohne maschinelle Projektion
   praktisch unausführbar; dieses Konzept ist die Erfüllungsform der Policy, keine Idee
   daneben.
4. **Der ADR-Rückbau-Arm füllt die einzige Richtung, die im Bestand fehlt:** KONZ-038
   benennt die Einweg-Ratsche als Kernproblem, baut den Rückweg aber nur für Regeln.
   181 accepted vs. 8 superseded ist die größte ungedeckte Ratsche der Org.
5. **Right-sized durch Komposition:** Verdrahtung zweier existierender Enden plus geborgte,
   bereits adversarial gehärtete Mechaniken (037/038) — das Restrisiko ist Integration,
   nicht Erfindung.

## 5 Konzeptdefinition

**Kernthese (ein Satz):** Jede bindende Architektur-Entscheidung trägt ihre prüfbaren
Invarianten selbst (Frontmatter), ein budgetierter Runner testet immer gegen diese
Invarianten, und jeder rote Befund erzwingt nach fester Regel die Entscheidung
„Ist anpassen oder Entscheidung zurückbauen".

Begriffe:
- **Zielzustand (Repo):** die Menge der aktiven Invarianten aller accepted ADRs des Repos
  plus die explizite Klassifikation aller übrigen accepted ADRs (nicht-testbar /
  out-of-budget). Er ist eine *Projektion*, kein eigenes Dokument mit eigenem Zustand.
- **Invariante:** `{id, check (exit-code-fähig), negativprobe}` im ADR-Frontmatter. Kein
  `aussage`-Restatement-Feld — die Aussage IST der ADR-Text (verhindert Kopie-Drift).
- **Aktiv:** Invariante zählt ins Budget und hat eine bestandene Negativprobe; sonst
  `dormant` (KONZ-037-Semantik; „Drill" aus KONZ-038 K4 ist dieselbe Semantik — der
  Begriff **Negativprobe** wird hiermit kanonisiert).
- **Abnahme:** der Merge des PRs, der die Invariante ins ADR-Frontmatter schreibt. Kein
  separater Abnahme-Zustand, kein zweiter Kanal — PR-Review ist der einzige nachweislich
  gelebte Abnahme-Kanal der Org.
- **„100 % definiert" (ehrliche Form):** Delta-Selbsttest (Invariante 0):
  `Delta = count(accepted ADRs) − count(klassifiziert)`. Delta > 0 länger als 30 Tage ⇒
  die Projektion flippt auf `stale` und jeder Runner-Lauf meldet das in Zeile 1.
  Vollständig ist die **Klassifikation** (maschinell erzwungen und billig), nicht die
  Prüftiefe (budgetiert und teuer) — alles andere wäre die gamebare 100-%-Geste.
- **„Maximale Testcoverage gegen das Ziel":** Coverage = Budget-Auslastung mit
  bestandenen Negativproben, nicht Prozent über den ADR-Bestand. Sie wächst, indem rote
  Realfälle neue Invarianten verdienen (Vier-Wege-Prüfung aus KONZ-038 §5.7 vor jeder
  neuen) und dormante gestrichen werden — Schrumpfung eingebaut.

## 6 Adversariale Analyse

Drei unabhängige Agenten (sahen einander nicht), danach Synthese.

### 6.1 Advocatus Diabolus — übernommene Falsifikationen

| # | Angriff | Konsequenz im Konzept |
|---|---|---|
| AD-1 | Abnahme zerstört „nur abgeleitete Sicht"; Separatliste mit eigenem Zustand = vierte Wahrheit (von KONZ-038 §6 AD-3 bereits verboten) | Separat-YAML mit Status **gestrichen**; Invarianten leben IM ADR (D1); Projektion zustandslos (D2) |
| AD-3/C7 | Destillations-Stichprobe 0/3: Status-Frontmatter schmutzig (ADR-151 void vs Proposed; ADR-037 accepted+implemented, Kern-Deliverable existiert nicht; ADR-186 proposed aber gelebt) | LLM-Destillat **gestrichen**; Invarianten werden je ADR menschlich/PR-reviewt autorisiert; Status-Bereinigung der Pilot-ADRs ist Teil des MVC (D1) |
| AD-4 | Abnahme- und Arm-Pflicht ohne Enforcement; Nicht-Abnahme wird belohnt | Abnahme = PR-Merge (kein separater Schritt, der verhungern kann); Arm-Zwang als Ausgabeformat mit Frist (D5), nicht als Prosa-Pflicht |
| AD-6 | „100 % definiert" gamebar (alles nicht-testbar etikettieren); vakuose Invarianten bestehen Negativproben | 100 % = Klassifikation (Delta maschinell), Prüftiefe budgetiert; Kill-Gate misst Rückbau-**Vollzug** (K-B), nicht Destillierbarkeit |
| AD-8 | LLM-Destillat + Abnahme strukturell unvereinbar (Nichtdeterminismus, Modellwechsel ~3-monatlich) | entfällt mit AD-3-Konsequenz; Projektion ist deterministisch |
| AD-9 | Wartungskapazität für bestehende Prüf-Flotte fehlt bereits (0/18 Gates, 45 tote Felder, 3 Wochen unbemerkt-rot) | Budget max. 10 aktive Invarianten je Pilot-Repo, vom Runner selbst durchgesetzt (D3); kein Org-Rollout vor Kill-Gate |
| AD-10 | Memory-Löschen-Default kollidiert mit KONZ-038 §5.4 (zweipfadiger Rückbau + Ledger-Pflicht); 🌀-Löschung tötet die „lies das 🌀"-Mechanik | aus dem Scope genommen; als Amendment-**Vorschlag** an 038 formuliert, mit 🌀-Destillat-Ausnahme explizit (D6) |
| AD-11 | Kill-Gates: selbstbenotet / undatiert / geborgt-unbewährt | §13: maschinelle Messbasis, feste Stichtage, Vollzugs- statt Selbstauskunfts-Kriterien |
| AD-12 | `aussage`-Feld = Kopie mit LLM-Rauschen | Feld gestrichen; Referenz = `{id, quelle, check}` |

### 6.2 Maintainer-2028 — übernommene Prognosen

- **M-4 (grün lügendes Gate):** eine abgenommene, nicht regenerierte Soll-Fassung testet
  2028 grün gegen die Welt von 2026 → gelöst durch zustandslose Projektion + Delta-
  Invariante 0 (D2, D4): Veralten ist nicht mehr still möglich, es steht in Zeile 1.
- **M-6 (dritter Arm „deferred"):** nach 50 Findings gewinnt immer der Formal-Arm →
  gelöst durch die 5-rote-Läufe-Regel aus KONZ-037 §10.5: keine sechste Meldung, sondern
  Entscheidungsvorlage; unentschieden nach Frist ⇒ Runner setzt die Invariante auf
  `dormant` **und** schreibt die Schuld-Zeile ins Ritual-Issue — der Zustand ist dann
  ehrlich sichtbar statt still rot.
- **M-7 (Budget statt Coverage-Prozent):** übernommen als Kernmechanik (D3).
- **M-8 (Staleness-Selbsttest als Invariante 0):** übernommen wörtlich (D4).
- **M-9 (kein Org-YAML, nur 2 Piloten):** übernommen (§2 Scope).
- **M-10 (038-Abhängigkeit erbt Sterberisiko):** anerkannt; einzige echte Abhängigkeit ist
  das Ritual-Scheduling — Fallback ist ein eigener halbmonatlicher Workflow-Schritt, falls
  038s K-Gates feuern (D5-Fallback).

### 6.3 Steelman — übernommene Bauform

Zweite Emissions-Stufe von `gen_adr_index.py` statt neuem Generator; Frontmatter-Feld
statt HTML-Kommentar (Migration der existierenden Felder); PR-Merge als Abnahme;
Einhängung in `regel-ritual.yml`/#1640 statt eigenem Scheduler; Zwei-Buttons-
Entscheidungsvorlage (Issue-Template / ADR-Stub via `adr_next_number.py`); Kill-Gate-
Trias K-A/K-B/K-C (§13); Wiederverwendungs-Tabelle (§3).

### 6.4 Konfliktmatrix (Pflicht)

| # | Dissens | Steelman | Diabolus | Maintainer-2028 | Synthese-Entscheid |
|---|---|---|---|---|---|
| X1 | Braucht es ein Konzept? | ja, fehlende Kante | nein — Runner bauen reicht (Werkzeug statt Artefakt, 038 §5.7) | nur geschrumpft | Konzept ja, aber MVC **ist** der Werkzeugbau; das KONZ dokumentiert die eine echte Architektur-Entscheidung (Invarianten im ADR-Frontmatter, cross-cutting) |
| X2 | 100%-Anspruch | Coverage-Metrik | gamebar (AD-6) | Konstruktionsfehler (M-7) | 100 % Klassifikation maschinell (Delta), Prüftiefe budgetiert — Owner-Strategie erfüllt, ohne Selbstbetrug |
| X3 | LLM-Destillat | im Ur-Entwurf enthalten | falsifiziert (0/3) | Regenerations-Falle | **gestrichen** |
| X4 | Separat-YAML mit Abnahme | als Index-Erweiterung ok | vierte Wahrheit | Sediment ab Monat 6 | zustandslose Projektion ohne Abnahme; Abnahme = ADR-PR-Merge |
| X5 | Org-Ebene + Referenzkette | machbar | — | Abhängigkeitskette stirbt (M-9) | gestrichen bis Kill-Gate bestanden |
| X6 | Memory-Löschen-Default | — | 038-Kollision (AD-10) | 038 selbst unbewiesen (M-10) | Amendment-Vorschlag an 038, nicht 041-Mechanismus |
| X7 | Rückbau-ADR-Pflicht je Gap | Zwei-Buttons-Vorlage | Pflicht ohne Enforcement (AD-4) | dritter Arm entsteht (M-6) | 5-rote-Läufe-Regel + Frist + `dormant`-mit-Schuld-Zeile statt Prosa-Pflicht |

Keine unaufgelösten Dissense; X1 ist der einzige, bei dem der Diabolus überstimmt wird —
Begründung: das Frontmatter-Schema bindet künftige ADR-Autoren org-weit und braucht darum
eine dokumentierte, challengebare Entscheidung (adr-threshold: cross-cutting), die ein
reiner Werkzeug-PR nicht trägt.

## 7 Deep-Dive: die sechs Entscheidungen

**D1 — Invarianten leben im ADR-Frontmatter.** Schema (iil-adrfw `schemas`-konform):
```yaml
invariants:
  - id: ADR-052-I1
    check: "python_ast: no-call .delay() in risk-hub/apps/**"   # Check-Typen: python_ast | script | http | file
    negativprobe: "2026-08-XX bestanden"    # Datum des letzten Rot-Beweises; fehlt ⇒ dormant
```
Migration: die existierenden `drift_check_paths`/`staleness_months`-Kommentarblöcke der
Pilot-ADRs werden in dieses Feld überführt (nur Pilot-Umfang, kein Bestands-Big-Bang).
Status-Widersprüche Frontmatter↔Body (C7) werden für Pilot-ADRs im selben PR bereinigt —
das ist Datenhygiene am SSoT, kein neues Artefakt.

**D2 — Projektion statt Zweitdokument.** `gen_adr_index.py` emittiert zusätzlich
`docs/adr/zielzustand.json`: je accepted ADR → `{quelle, invariants[] | klassifikation:
nicht-testbar | out-of-budget}`. Deterministisch, zustandslos, vom selben CI-Diff-Gate
regeneriert wie `index.json`. Die Datei KANN nicht abweichen und trägt keinen eigenen
Status — damit ist „keine zweite SSoT" Bauform, nicht Behauptung.

**D3 — Budgetierter Runner.** Runner (Erweiterung des `drift_check.py`-Skeletts) führt
die aktiven Invarianten aus. Budget: **max. 10 aktive Invarianten je Repo**, vom Runner
selbst durchgesetzt (11. Invariante ⇒ Lauf rot mit genau dieser Meldung — KONZ-037 §4.2
wörtlich). Invariante ohne bestandene Negativprobe zählt nicht als aktiv (`dormant`).
Blockierungs-Staffel (M-1: blockierende Checks überleben, Reports sterben): Budget- und
Schema-Verletzungen blockieren CI sofort; Invarianten-Rot läuft über die 5-Läufe-
Eskalation (D5) und wird erst mit Ablauf der Entscheidungsvorlage-Frist blockierend —
verhindert die Rot-Lawine (R1), ohne im Report-Modus zu verrotten.

**D4 — Invariante 0 (Staleness-Selbsttest).** Wie §5 definiert; zusätzlich altert das
jüngste Negativproben-Datum je Repo analog `review_by` (KONZ-037): älter als 90 Tage ⇒
Invariante `dormant`. Verrottung sieht damit nie wie Erfolg aus.

**D5 — Zwei-Arme-Auflösung mit Fristen.** Roter Check erscheint im Ritual-Lauf
(`regel-ritual.yml` → Issue #1640; Fallback bei 038-Kill: eigener Schritt im selben
Workflow-File). Nach **5 aufeinanderfolgenden roten Läufen ohne Zustandsänderung**: keine
sechste Meldung, sondern Entscheidungsvorlage mit genau zwei Ausgängen — (a) Issue
„Ist anpassen" (vorbefüllt) oder (b) ADR-Stub supersede/amend via `adr_next_number.py`.
Jeder Rückbau-Vollzug loggt in `docs/governance/sunset-ledger.md`. Bleibt die Vorlage ein
weiteres Ritual-Fenster unentschieden ⇒ Invariante `dormant` + dauerhafte Schuld-Zeile im
Ritual-Issue (ehrlich sichtbar statt still rot; M-6).

**D6 — Grenzziehung + ein Amendment-Vorschlag.** Steuerungsschicht bleibt KONZ-038.
An 038 §5.4 wird vorgeschlagen (dort zu entscheiden, ungebündelt): *Vollzugsform* des
Evidenz-Sunset für Maschinen-Memory ist **Löschen** (git-History = Archiv, Ledger-Eintrag
bleibt Pflicht), nicht ein `deprecated`-Verbleib in der geladenen Menge — Ausnahme:
falsifizierte Hypothesen werden vor Löschung zum 🌀-Destillat (2–3 Zeilen) eingedampft,
weil die „lies das 🌀 vor Empfehlung"-Mechanik geladene Präsenz braucht (AD-10 iii).
Begründung der Owner-Weisung 2026-08-06: Memory wird injiziert, nicht nachgeschlagen —
ein deprecated-Eintrag kostet Kontext und leitet weiter fehl.

## 8 Alternativen

| Alternative | Warum verworfen |
|---|---|
| A1: Nur Runner bauen, kein Konzept (Diabolus-Urteil) | Frontmatter-Schema bindet künftige ADR-Autoren org-weit → challengebare Entscheidung nötig (X1); sonst entsteht Schema per Fakt statt per Entscheid — die ADR-167-Kommentarfelder zeigen genau dieses Muster und seine Folge (0 Konsumenten) |
| A2: Ur-Entwurf (LLM-Destillat + abgenommene zielzustand.yaml, Voll-Coverage, Org-Ebene) | dreifach falsifiziert: 0/3-Stichprobe (C7), Abnahme/Regenerations-Dilemma (AD-8), Basisraten (C8, M-4) |
| A3: Voll-Migration aller ~181 accepted ADRs sofort | Kapazität nachweislich nicht vorhanden (AD-9); Big-Bang erzeugt die Rot-Lawine, die ab Tag 2 ignoriert wird (AD-5) |
| A4: Warten bis KONZ-037/038 ihre Kill-Gates bestanden haben | ehrlichste Gegenposition; verworfen, weil der Pilot bewusst NUR geborgte Mechanik + 2 Repos nutzt und sein eigenes Kill-Gate früher fällt als deren Rollout-Entscheidungen — scheitern 037/038, stirbt hier nur der Scheduling-Anschluss (D5-Fallback), nicht die Mechanik |

## 9 Out-of-the-Box

- **Rückbau-Quote als Gesundheitsmetrik:** `superseded_pro_Quartal / neue_ADRs_pro_Quartal`
  einmal je Ritual-Fenster im Report ausweisen (eine Zeile, keine neue Infrastruktur).
  Eine Org, die nur anbaut, sieht es dann.
- **Invarianten-Vererbung bei Supersede:** ein Supersede-ADR erbt per Default die
  Invarianten des Vorgängers zur expliziten Übernahme/Streichung — Rückbau ohne
  Prüfverlust.
- **`proposed`-Limbo-Kampagne** (45 ADRs, teils >1 Jahr alt, C9): nicht Teil dieses MVC,
  aber der natürliche zweite Nutzer der Zwei-Buttons-Vorlage — als Folgekandidat im
  Ritual-Issue notiert, nicht hier beschlossen.

## 10 Befunde

| # | Befund | Evidenz | Schwere |
|---|---|---|---|
| B1 | 45–50 ADRs mit maschinenlesbaren Drift-Feldern, 0 Konsumenten | C6 | hoch |
| B2 | drift_check.py prüft gegen hartkodiertes Soll, nicht gegen ADRs | C4 | hoch |
| B3 | ADR-Status-Frontmatter schmutzig: 0/3-Stichprobe intern widersprüchlich | C7 | hoch |
| B4 | 181 accepted vs 8 superseded — ADR-Ratsche kennt nur Anbau | C9 | hoch |
| B5 | Lifecycle-Vollzugsquote fälliger KONZ ~14 % (1/7) | C8 | hoch |
| B6 | Sunset-Ledger existiert mit 0 Einträgen | C10 | mittel |
| B7 | Belegte, bekannte ADR-Drift (ADR-052/.delay()) seit Monaten ohne ADR-Konsequenz | 🌀-Memory + C2-Kontext | hoch |

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme | Restrisiko |
|---|---|---|---|
| R1 | Rot-Lawine → Report ab Tag 2 ignoriert (empirisch belegt: 5 Merges unbemerkt-rot) | Budget 10, Pilot-Umfang, 5-Läufe-Eskalation statt Dauer-Rot | mittel |
| R2 | Solo-Owner-Kapazität: auch 10 Invarianten × 2 Repos werden nicht gewartet | Negativproben-Alterung ⇒ automatisches `dormant`; Kill-Gate K-B misst Vollzug, nicht Vorsatz | mittel-hoch |
| R3 | 038-Ritual stirbt (eigenes Kill-Fenster 2026-09-16) → Scheduling weg | D5-Fallback: eigener Schritt im Workflow-File, kein neuer Scheduler | niedrig |
| R4 | Frontmatter-Schema wird wie die Kommentarfelder deklariert-aber-ignoriert | Schema nur MIT Runner im selben PR mergen (Verdrahtungs-Kopplung als MVC-Regel M1) | niedrig |
| R5 | Status-Bereinigung (D1) eskaliert zum Bestands-Big-Bang | harte Pilot-Grenze: nur ADRs, die eine Invariante bekommen; Rest bleibt unangetastet | niedrig |

## 12 Empfehlungen (MVC — ungebündelt entscheidbar)

| # | Entscheidung | Artefakt | Aufwand |
|---|---|---|---|
| D1 | `invariants:`-Frontmatter-Schema + Migration Pilot-ADRs (inkl. Status-Hygiene nur dort) | iil-adrfw-Schema + 3–5 Pilot-ADR-PRs | S |
| D2 | Zweite Emissions-Stufe `zielzustand.json` in `gen_adr_index.py` (zustandslos) | Skript-PR + CI-Diff-Gate | S |
| D3 | Budgetierter Runner (10/Repo, Negativprobe-Pflicht, `dormant`) | `scripts/zielzustand_runner.py` (drift_check-Skelett) | M |
| D4 | Invariante 0 (Delta-Selbsttest) + Negativproben-Alterung 90 d | im Runner | S |
| D5 | Ritual-Einhängung + Zwei-Buttons-Vorlage + Sunset-Ledger-Pflicht + Fristen | Workflow-Schritt + 2 Templates | M |
| D6 | Amendment-Vorschlag an KONZ-038 §5.4 (Memory-Löschen als Sunset-Vollzugsform, 🌀-Ausnahme) | eigener kleiner PR an KONZ-038, dort entscheiden | S |

**MVC-Regel M1 (aus R4):** D1 wird nie ohne D3 gemergt — Schema und Runner landen
gekoppelt, damit nie wieder ein deklariertes Feld ohne Konsumenten entsteht.

**Erst-Pilotfall (verbindlich):** ADR-052/risk-hub-`.delay()` — Invariante als
AST-Check, designierter Rückbau- ODER Umsetzungs-Kandidat für K-B.

## 13 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** D1–D5 umsetzen (Pilot platform + risk-hub), D6 als
separaten Vorschlag an KONZ-038 geben. Kein Org-Rollout, kein ADR vor Kill-Gate-Bilanz.

**Kill-Gate — Stichtag: Tag 15 nach Merge des letzten MVC-PRs, mindestens jedoch 2
Ritual-Fenster (was später eintritt). Alle drei UND-verknüpft; bei Nichterfüllung wird
GESTRICHEN, nicht nachgebessert:**

- **K-A (Klassifikation):** Delta = 0 für beide Pilot-Repos, maschinell aus
  `zielzustand.json` gemessen (jedes accepted ADR ist Invariante, nicht-testbar oder
  out-of-budget) — Zähler/Nenner aus dem Generator, nicht aus Selbstauskunft.
- **K-B (Rückbau- oder Umsetzungs-Vollzug):** ≥1 gemergtes Supersede-/Amend-ADR ODER
  gemergter Ist-Fix, dessen Ursprung nachweislich ein roter Runner-Befund ist (Link im
  PR/ADR-Body auf den Report-Kommentar). Designierter Erstfall: ADR-052/`.delay()`.
- **K-C (Negativproben-Quote):** 100 % der als aktiv gezählten Invarianten haben eine
  bestandene, datierte Negativprobe; jede ohne zählt als `dormant` und fällt aus K-A's
  Invarianten-Zähler.

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| K-A Delta=0 beide Piloten | offen | — |
| K-B ≥1 Vollzug aus rotem Befund | offen | — |
| K-C 100 % Negativproben aktiv | offen | — |

**30/60/90:**
- **30 Tage:** D1+D3 gekoppelt gemergt (M1), D2, D4; Erst-Invariante ADR-052 aktiv mit
  Negativprobe; erster Ritual-Report mit Delta-Zeile.
- **60 Tage:** Kill-Gate-Stichtag spätestens hier; Bilanz K-A/K-B/K-C in dieser Tabelle;
  bei Bestehen: Entscheidungsvorlage Org-ADR + Ausbreitungsplan (je Repo einzeln, Budget
  je Repo), bei Nichtbestehen: Streichung + Sunset-Ledger-Eintrag für dieses Konzept.
- **90 Tage:** nur bei Bestehen — zweites Domain-Repo, `proposed`-Limbo-Kampagne als
  eigener Vorschlag (§9), Rückbau-Quote im Ritual-Report etabliert.
