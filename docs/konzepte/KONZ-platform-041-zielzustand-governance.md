---
concept_id: KONZ-platform-041
title: Zielzustand-Governance — ADR-Invarianten verdrahten statt neu deklarieren
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: [platform:ADR-211, platform:KONZ-platform-037, platform:KONZ-platform-038]
adr_threshold: "Kein sofortiger org-weiter ADR. X1 ist ein PILOT-LOKALER Experimentvertrag (R2-REC-13): Normativität nur für platform + risk-hub; das iil-adrfw-Schema wird org-weit nur als OPTIONAL-validiert abgelegt (R1-REC-2). Bestandenes Kill-Gate erzeugt den Org-ADR-Kandidaten; gescheitertes Kill-Gate erzeugt einen Streichungs-PR (Schema, Runner, Projektion, Konzeptstatus)."
review_by: 2026-09-06
kill_criteria: "K-A/K-B1/K-B2/K-C in §13, UND-verknüpft, Stichtag Tag 15 nach Pilot-Merge mind. jedoch 2 Ritual-Fenster; bei Nichterfüllung wird GESTRICHEN, nicht nachgebessert — inkl. automatischem Streichungs-PR (§13)."
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
  - {claim_id: C12, source_path: "Externe Zweitmeinung, 2 unabhängige Runden (Cross-Provider, via Betreiber; Briefing ~/shared/adr-handoff-KONZ-platform-041-2026-08-06.md); 27 RECs, Tag-Tabelle §6.5", commit_or_pr: "2026-08-06", opened_in_session: true, provenance: external-review}
  - {claim_id: C13, source_path: "risk-hub@a072bce: docs/adr/ADR-053-celery-worker-fuer-event-tasks.md (status accepted, implementation_status none) vs. docker-compose.prod.yml:176 (Service risk-hub-celery), :38 (Redis noeviction+appendonly+Volume), src/gbu/tasks.py:96 + src/brandschutz/tasks.py:155 (.delay() aktiv laut ADR-053); ADR-052 = proposed, regelt periodische Jobs", commit_or_pr: "Pilot-Preflight 2026-08-06", opened_in_session: true, provenance: direct}
created: 2026-08-06
---

# KONZ-platform-041 — Zielzustand-Governance: ADR-Invarianten verdrahten statt neu deklarieren

**Tier-Entscheidung: T3** — Cross-Repo (platform + risk-hub Pilot, org-weite Option), neuer
Lifecycle-Baustein (Invarianten-Referenzen im ADR-Frontmatter), berührt SSoT-Fragen.
Adversarialer Fan-out mit drei unabhängigen internen Agenten (Steelman / Advocatus Diabolus /
Maintainer-2028) am 2026-08-06, Konfliktmatrix §6.4; danach **zwei unabhängige externe
Review-Runden** (Cross-Provider), Rückfluss-Tagging aller 27 Empfehlungen in §6.5.

> **Rev 3 (2026-08-06, Pilot-Preflight):** Der als „verbindlich" gesetzte Erstfall
> (ADR-052/`.delay()`) wurde beim ersten realen Anwendungsversuch **falsifiziert** und
> durch die belegte risk-hub-**ADR-053-`implementation_status`-Drift** ersetzt (B9, C13).
> Das ist kein Betriebsunfall, sondern der erste Nutzen dieses Konzepts: Der Versuch, eine
> Entscheidung maschinell prüfbar zu machen, hat die Entscheidung selbst als falsch
> zitiert entlarvt — bevor ein Check darauf gebaut wurde.

## 1 Executive Summary

**Basis:** Die Org hat Soll-Deklaration und Ist-Prüfung **beide bereits gebaut — und nie
miteinander verbunden**: 45–50 ADRs tragen maschinenlesbare Drift-Felder
(`drift_check_paths`, `staleness_months`), für die **kein Runner existiert** (grep über
`scripts/` + `tools/`: 0 Konsumenten, C6); `scripts/drift_check.py` prüft Cross-Repo-Drift,
aber gegen **hartkodierte** Regeln statt gegen ADRs (C4). Belegte Folge: ADR-Drift wird per
Zufall gefunden, nicht per Gate (ADR-167 HealthBypass-Drift; risk-hub ADR-053
`implementation_status: none` trotz vollständiger Umsetzung — beide monatelang
unentdeckt, C13). Zugleich kennt der ADR-Bestand (181 accepted,
45 proposed im Limbo, 8 superseded, C9) praktisch nur eine Richtung: Anbau.

**Analyse:** Das Problem ist keine fehlende Deklarationsschicht, sondern die **fehlende
Kante** zwischen existierenden Enden — plus fehlender Rückbau-Pfad für ADRs. Ein
ursprünglicher Entwurf (separate `zielzustand.yaml` als abgenommenes LLM-Destillat über
alle accepted ADRs) wurde intern **falsifiziert** und gestrichen (0/3-Destillations-
Stichprobe C7, Abnahme/Regenerations-Dilemma, Basisraten C8). Die externe Zweitprüfung
(§6.5) bestätigte Analyse und Scope-Schnitt, falsifizierte aber das erste Kill-Gate-Design
(selbstgetippte Negativprobe, zeitlich unerreichbares K-B) und die Metrik-Präsentation —
beides in dieser Revision behoben.

**Fazit:** Zielzustand-Governance heißt hier: (1) ADRs tragen **Invarianten-Referenzen**
(Frontmatter referenziert reviewten Check-Code — SSoT bleibt das ADR, Ausführbares bleibt
Code), (2) ein **budgetierter Runner** testet immer gegen das Ziel, mit maschinell
ausgeführten Negativproben je Lauf, (3) Vollständigkeit wird als **Klassifikations-Delta**
berichtet — maschinell erzwungen, immer mit Mischungs-Aufschlüsselung, nie als
„100 % / Coverage" (das wäre Theater), (4) jeder bestätigte Verstoß mündet fristgebunden
in eine **Zwei-Arme-Entscheidung**: Ist anpassen ODER ADR amend/supersede — Rückbau statt
Anbau.

**Handlungsempfehlung:** MVC §12 (D1–D7) umsetzen — Pilot platform + risk-hub,
Erstfall **risk-hub ADR-053 `implementation_status`-Drift** (Plumbing-Beweis, Rev 3 —
der ursprünglich benannte ADR-052/`.delay()`-Fall wurde im Pilot-Preflight
falsifiziert, §10 B9) + ein verblindeter Zweitfall (Lifecycle-Beweis). Kill-Gate §13
vorab registriert.

## 2 Scope & Evidenzbasis

**Im Scope:** Die Entscheidungsschicht (ADRs) zweier Pilot-Repos: platform und risk-hub.
Verdrahtung: Frontmatter-Referenzen → reviewter Check-Code → ephemere Projektion →
budgetierter Runner in CI/Ritual → Zwei-Arme-Auflösung.

**Verbindlichkeits-Klarstellung (R1-REC-2/AD-8, R2-REC-13):** Dieses Konzept ist ein
**pilot-lokaler Experimentvertrag**. Org-weit passiert vor der Kill-Gate-Bilanz genau
eines: das `invariants`-Schema wird in iil-adrfw als **optionales, validiertes** Feld
abgelegt (unschädlich — kein Repo muss es nutzen). **Pflicht** wird das Feld nur im
CI-Gate der beiden Pilot-Repos, und nur für dort NEU accepted werdende ADRs. Das ist die
org-weite Komponente, benannt als das, was sie ist — nicht versteckt.

**Nicht im Scope:**
- **Steuerungsschicht** (Memory, Skills, Policies, Hooks): bleibt vollständig bei
  KONZ-038 (C2). Die Owner-Weisung 2026-08-06 „Memory-Rückbau-Default = Löschen statt
  deprecate" wird als **Amendment-Vorschlag an KONZ-038 §5.4** formuliert (§12 D6), hier
  nicht entschieden.
- **Betriebszustand** von Diensten: KONZ-037 (C1). **Abhängigkeits-Klarstellung
  (R1-REC-7, R2-REC-11):** 041 borgt von 037/038 die *Idee* der Mechaniken (Negativprobe,
  Budget, dormant, Eskalation), **normiert sie aber in §5/§7 eigenständig** — scheitern
  037/038 an ihren eigenen Kill-Gates, verantwortet 041 seine Mechanik selbst; die einzige
  externe *Laufzeit*-Abhängigkeit ist das Ritual-Scheduling, mit Fallback (D5).
- **Oberflächen**: ADR-211.
- **Org-weiter Rollout** (Invarianten/Gates über die Piloten hinaus): erst nach
  bestandenem Kill-Gate.

**Evidenzbasis:** Manifest im Frontmatter. Direkt geöffnet: C1–C5, C11. Subagenten-
verifiziert: C6–C10. Extern reviewt: C12. Zahlenbestand mit Zählweisen-Caveat: 239–242
ADR-Dateien (C9). **ADR-Zuwachsrate nachgemessen (C11):** 305 ADR-Datei-Adds seit 2026-01
(~40/Monat; Renames zählen mit, netto ~240) — Voll-Coverage ist damit klar unbezahlbar,
das Budget-Modell (D3) alternativlos. **Maschinenwahrheit (R2-REC-10):** Für alle
Zählungen gilt das ADR-**Frontmatter** als alleinige Maschinenwahrheit; Frontmatter↔Body-
Widersprüche (C7) werden nicht interpretiert, sondern als eigene Zähl-Zeile im Report
ausgewiesen.

## 3 Infrastruktur-Fit

Alle Bausteine existieren; das MVC ist Komposition, kein Neubau:

| Baustein | Existiert als | Rolle hier |
|---|---|---|
| ADR-Frontmatter-Parse + CI-Gate | `scripts/gen_adr_index.py` → `index.json` | Generator bekommt zweite Emissions-Stufe (D2) |
| Drift-Felder je ADR | 45–50 ADRs, `drift_check_paths`/`staleness_months` (C6) | Migration in `invariants:`-Referenzen (D1) |
| Cross-Repo-Prüf-Skelett | `scripts/drift_check.py` (C4) | Runner-Skelett (D3) |
| Negativprobe/Budget/dormant (Ideengeber) | KONZ-037 §4 (C1) | in §5/§7 eigenständig normiert (R2-REC-11) |
| Ritual-Scheduling + Ausfall-Flip `stale` | KONZ-038 D3, `regel-ritual.yml` (C2) | Kadenz-Anschluss mit Fallback (D5) |
| Supersede-Nummernvergabe + Race-Guard | `scripts/adr_next_number.py`, `adr_open_pr_guard.py` | Rückbau-ADR-Stub (D5) |
| Sunset-Ledger (append-only) | `docs/governance/sunset-ledger.md`, 0 Einträge (C10) | jeder Rückbau loggt dorthin (D5) |
| Frontmatter-Schema-Validierung + AST-Checker | iil-adrfw (`schemas`, `checkers/python_ast`) | `invariants:`-Schema + Check-Typ (D1, D3) |

## 4 Steelman (des Vorhabens)

1. **Deklarations-Lücke belegt, nicht vermutet:** maschinenlesbare Soll-Felder ohne einen
   einzigen Konsumenten (C6) sind der Zustand „deklariert, aber wirkungslos" — falsches
   Vertrauen, gefährlicher als Regellosigkeit.
2. **Drift zweifach dokumentiert, jeweils monatelang unentdeckt** (ADR-167;
   risk-hub ADR-053, C13) — beide per Zufall gefunden. Der ADR-053-Fall ist ein
   deklarativer Datei-Check und zeigt die teuerste Drift-Klasse: nicht der Code weicht
   vom ADR ab, sondern das **ADR-Frontmatter behauptet das Gegenteil des Codes** — eine
   🌀-Memory hat diesen Irrtum 53 Tage lang als Fakt weitergetragen und im
   Pilot-Preflight einen Auftrag auf eine falsche Prämisse geführt (B9).
3. **Policy-Grundlage gemergt und bindend** (`policies/zielzustand.md`, C3): „Artefakt
   mit Akzeptanzkriterien IST der Zielzustand — referenzieren statt neu erfinden." Bei
   ~240 ADRs ist Referenzieren ohne maschinelle Projektion praktisch unausführbar.
4. **Der ADR-Rückbau-Arm füllt die einzige fehlende Richtung:** 181 accepted vs.
   8 superseded ist die größte ungedeckte Ratsche der Org; KONZ-038 baut den Rückweg nur
   für Regeln.
5. **Right-sized durch Komposition:** Verdrahtung existierender Enden; Restrisiko ist
   Integration, nicht Erfindung. Das System kann nicht grün geboren werden — der
   verbindliche Erstfall ist ein belegter Rot-Fall.

## 5 Konzeptdefinition

**Kernthese (ein Satz):** Jede bindende Architektur-Entscheidung referenziert ihre
prüfbaren Invarianten (reviewter Check-Code, im ADR nur die Referenz), ein budgetierter
Runner testet immer gegen diese Invarianten mit maschinell bewiesener Rot-Fähigkeit, und
jeder bestätigte Verstoß erzwingt fristgebunden die Entscheidung „Ist anpassen oder
Entscheidung zurückbauen".

Begriffe (hier eigenständig normiert; Ideen-Herkunft KONZ-037/038 — R2-REC-11):
- **Zielzustand (Repo):** aktive Invarianten aller accepted ADRs des Repos plus explizite
  Klassifikation der übrigen. Eine *Projektion* (ephemer, D2), kein Dokument mit eigenem
  Zustand.
- **Invariante:** `{id, check_ref, severity}` im ADR-Frontmatter; `check_ref` zeigt auf
  eine reviewte Check-Datei unter `checks/` (D1). Kein `aussage`-Feld, keine ausführbaren
  Strings im Frontmatter (R1-REC-3, R2-REC-9/12).
- **Klassifikation (explizites Frontmatter-Feld, R2-REC-1):** je accepted ADR
  `zielzustand: invariant | nicht-testbar | out-of-budget`. `nicht-testbar` NUR mit
  Pflicht-Begründung (ein Satz, R1-REC-4). Fehlt das Feld ⇒ zählt als `out-of-budget`
  (ehrliche Default-Schuld, nicht stilles Grün).
- **Deckungs-Sprache (R2-REC-2):** ein ADR mit aktiven Invarianten gilt als **„partiell
  gedeckt"** — nie als „gedeckt". Eine Invariante prüft einen Anker der Entscheidung,
  nicht die Entscheidung.
- **Aktiv:** zählt ins Budget UND die Negativprobe wurde im letzten Runner-Lauf
  **maschinell ausgeführt und bestanden** (R1-REC-1) — sonst `dormant:<grund>`.
- **Negativprobe (maschinell, R1-REC-1/R2-REC-8):** je Invariante eine Fixture unter
  `tests/negativproben/<invariant-id>/`, die der Runner in JEDEM Lauf gegen den Check
  anwendet und auf Rot prüft; Datum + Checker-Version landen in der Projektion, nie
  als handgetipptes Frontmatter-Feld.
- **dormant-Trias (R1-REC-9):** `dormant:aged` (Negativprobe zuletzt >90 d nicht
  bestanden/gelaufen) · `dormant:unresolved` (Entscheidungsvorlage über Frist
  unentschieden) · `dormant:budget` (verdrängt). `dormant:unresolved` zählt weiter als
  **offene Schuld** und belastet das Budget (R2-REC-4 Kern: der Friedhof darf den Report
  nicht grüner machen).
- **Abnahme:** der Merge des PRs, der Invarianten-Referenz + Check + Fixture einführt.
  PR-Review ist der einzige nachweislich gelebte Abnahme-Kanal.
- **Klassifikations-Delta (Metrik — R1-REC-4, R2-REC-14; ersetzt „100 % definiert"):**
  `Delta = count(accepted) − count(explizit klassifiziert)`. Wird IMMER mit Mischung
  berichtet, Zeile 1 jedes Reports:
  `Delta=n | aktiv a | dormant(aged/unres/budget) x/y/z | nicht-testbar m | out-of-budget k | body-konflikt b`.
  Delta > 0 länger als 30 Tage ⇒ Projektion `stale` in Zeile 1. Vollständig ist die
  **Klassifikation** (billig, maschinell erzwungen), nie die Prüftiefe — jede
  „Coverage"-Lesart ist damit strukturell unmöglich gemacht, nicht nur verboten.
- **Runner-Ergebnis-Trias (R2-REC-3):** `pass | violation | error`. Nur eine bestätigte
  `violation` löst die Zwei-Arme-Entscheidung aus; `error` (Check defekt, Infra) geht in
  einen Betriebsfehler-Pfad und zählt NIE als grün.

## 6 Adversariale Analyse

### 6.1 Interner Advocatus Diabolus — übernommene Falsifikationen

| # | Angriff | Konsequenz im Konzept |
|---|---|---|
| AD-1 | Abnahme zerstört „nur abgeleitete Sicht"; Separatliste mit Zustand = vierte Wahrheit | Separat-YAML gestrichen; Referenzen im ADR (D1); Projektion ephemer (D2) |
| AD-3/C7 | Destillations-Stichprobe 0/3: Status-Frontmatter schmutzig | LLM-Destillat gestrichen; Invarianten PR-reviewt; Frontmatter = Maschinenwahrheit, Body-Konflikte separat gezählt (D7) |
| AD-4 | Pflichten ohne Enforcement | Abnahme = PR-Merge; Fristen maschinell (D5) |
| AD-6 | „100 %" gamebar | Klassifikations-Delta mit Pflicht-Mischung (§5); Kill-Gate misst Vollzug |
| AD-8 | LLM-Destillat + Abnahme unvereinbar | entfällt; Projektion deterministisch |
| AD-9 | Wartungskapazität fehlt bereits | Budget 10/Repo + Org-Deckel 30 (D3); Pilot-Grenze |
| AD-10 | Memory-Löschen kollidiert mit KONZ-038 §5.4 | aus dem Scope; Amendment-Vorschlag (D6) |
| AD-11 | Kill-Gates selbstbenotet/undatiert/geborgt | §13 neu: maschinell, datiert, zweistufig |
| AD-12 | `aussage`-Feld = Kopie | gestrichen |

### 6.2 Interner Maintainer-2028 — übernommene Prognosen

M-4 (grün lügendes Gate → ephemere Projektion + Delta-Zeile 1) · M-6 (dritter Arm →
Fristen + `dormant:unresolved` als sichtbare Schuld) · M-7 (Budget statt Coverage-%) ·
M-8 (Delta-Selbsttest als Invariante 0) · M-9 (kein Org-YAML, 2 Piloten) · M-10
(037/038-Risiko → Mechanik eigenständig normiert, §2) · M-1 (blockierende Checks
überleben, Reports sterben → Blockierungs-Staffel D3).

### 6.3 Interner Steelman — übernommene Bauform

Zweite Emissions-Stufe von `gen_adr_index.py`; Frontmatter-Referenzen statt
HTML-Kommentare; PR-Merge als Abnahme; Ritual-Kadenz statt eigenem Scheduler;
Zwei-Buttons-Entscheidungsvorlage; Kill-Gate-Trias; Wiederverwendungs-Tabelle (§3).

### 6.4 Interne Konfliktmatrix

| # | Dissens | Synthese-Entscheid (Stand nach externem Review) |
|---|---|---|
| X1 | Konzept vs. nur Werkzeug | Konzept ja — aber als **pilot-lokaler Experimentvertrag** (R2-REC-13), nicht als org-bindender Entscheid; org-weit nur das optionale Schema (§2) |
| X2 | 100%-Anspruch | Klassifikations-Delta mit Pflicht-Mischung — „100 %"-Sprache ganz gestrichen (R1-REC-4) |
| X3 | LLM-Destillat | gestrichen (bestätigt von beiden externen Runden) |
| X4 | Separat-YAML mit Abnahme | ephemere Projektion, nicht committet (R1-REC-12, R2-OOB-2) |
| X5 | Org-Ebene + Referenzkette | gestrichen bis Kill-Gate bestanden |
| X6 | Memory-Löschen-Default | Amendment-Vorschlag an 038 (D6) |
| X7 | Rückbau-Pflicht je Gap | Fristen + `dormant:unresolved` als gezählte Schuld (D5) |

### 6.5 Externe Zweitmeinung — Rückfluss-Tagging (2 unabhängige Runden, 2026-08-06)

Beide Runden urteilten **„Überarbeiten, nicht ablehnen"**; beide bestätigten explizit:
Streichung des LLM-Destillats, zustandslose/ephemere Projektion, PR-Merge als Abnahme,
Budget statt Coverage-%, Zwei-Arme-Auflösung, verbindlicher Erstfall, Kopplungsregel M1.
Kernkritik beider Runden unabhängig voneinander: das Kill-Gate der Vorfassung war kein
Messinstrument (handgetippte Negativprobe; K-B zeitlich unerreichbar; ADR-052 als
vorbekannter Fall beweist Verdrahtung, nicht Governance). Vollzähligkeit: Runde 1 =
13 RECs, Runde 2 = 14 RECs, 27 Zeilen unten (mechanisch gegengezählt).

| ID | Verdikt | Aktion |
|---|---|---|
| R1-REC-1 | [valid] · blockierend | übernommen: Negativprobe = Fixture, maschinell je Lauf, Datum+Checker-Version in Projektion (§5, D3, K-C) |
| R1-REC-2 | [valid] | übernommen: Schema org-weit optional-validiert, Pilot-CI hart für neue accepted; Schema-Bindung explizit benannt (§2, D1) |
| R1-REC-3 | [valid] | übernommen: Frontmatter nur `{id, check_ref, severity}` + `zielzustand`-Feld; Checks als reviewte Dateien; MVC nur `python_ast`/`file`; `script`/`http` erst nach eigener Sicherheitsentscheidung (D1) |
| R1-REC-4 | [valid] | übernommen: Pflicht-Mischungszeile, `nicht-testbar` mit Begründung + Stichprobe 3/Fenster, Metrik heißt „Klassifikations-Delta" (§5, D4) |
| R1-REC-5 | [valid] | übernommen (beide Richtungen): K-A auf eingefrorenen benannten Pilot-ADR-Satz; Klassifikationskampagne als eigene MVC-Position D7 |
| R1-REC-6 | [valid] | übernommen: Lauf = Ritual-Lauf; Eskalation nach 2 roten Fenstern ODER 14 Tagen, was früher (D5) |
| R1-REC-7 | [valid] | übernommen: 037-Mechanik in §5/§7 eigenständig normiert; A4-Begründung korrigiert (§2, §8) |
| R1-REC-8 | [valid] | übernommen: Org-Deckel 30 aktive Invarianten, vom Runner durchgesetzt (D3) |
| R1-REC-9 | [valid] | übernommen: dormant-Trias `aged/unresolved/budget`, getrennt gezählt (§5) |
| R1-REC-10 | [valid] | übernommen via ephemere Projektion: nichts wird per Default publiziert; Ritual-Issue trägt nur die Aggregat-Zeile (D2) |
| R1-REC-11 | [valid] | übernommen: Baseline vor D7-Statushygiene eingefroren, `accepted vorher/nachher` im Kill-Gate-Beleg (§13) |
| R1-REC-12 | [valid] | übernommen: eigenes festes Report-Issue für 041; Projektion aus dem Commit-/Diff-Pfad genommen (D2, D5) |
| R1-REC-13 | [valid] | übernommen als 60-Tage-Kandidat, kein MVC-Blocker: `enforces:`-Feld für bestehende CI-Checks (§9, §13 60 d) |
| R2-REC-1 | [valid] teilweise | `zielzustand`-Klassifikation wird explizites, schemavalidiertes Feld; Abwesenheit ⇒ `out-of-budget` bleibt ableitbar (als ausgewiesene Default-Schuld, nicht als Grün); `owner`/`review_by` je Disposition ABGELEHNT — repliziert die unbezahlbare Pflegearbeit (Basisrate 14 %, C8) |
| R2-REC-2 | [valid] teilweise | Deckungs-Sprache „partiell gedeckt" übernommen (§5); volles Anker-Klassifikationssystem ABGELEHNT — Authoring-Aufwand je ADR skaliert genau wie die verworfene Voll-Migration (A3); Invarianten-IDs adressieren Anker bereits implizit |
| R2-REC-3 | [valid] | übernommen: Ergebnis-Trias `pass/violation/error`; nur bestätigte violation triggert Zwei-Arme; error = Betriebsfehler-Pfad, nie grün (§5, D3, D5) |
| R2-REC-4 | [valid] teilweise | Kern übernommen: `dormant:unresolved` zählt als offene Schuld + belastet Budget weiter (kein grüner Friedhof, M28-3); Pflicht-Waiver mit Owner/Frist ABGELEHNT — bei 14 % Entscheidungs-Vollzug bliebe sonst Dauer-Rot ⇒ empirisch belegter Report-Tod (5 Merges unbemerkt-rot) |
| R2-REC-5 | [valid] teilweise | deterministische Auswahl-/Verdrängungsregel übernommen (D3); zweidimensionales Risiko-/Kosten-Budget ABGELEHNT — erzeugt genau die Urteilsarbeit, die die knappste Ressource ist; `severity`-Feld (R2-REC-7) deckt die Risikodimension minimal ab |
| R2-REC-6 | [valid] | übernommen: Kill-Gate zweistufig — K-B1 Plumbing (ADR-052) + K-B2 Lifecycle (verblindeter Zweitfall + real durchlaufene Eskalation) (§13) |
| R2-REC-7 | [valid] teilweise | binäres `severity: critical\|normal` übernommen: critical ⇒ Entscheidungsvorlage nach 1 rotem Lauf (D1, D5); volles Kritikalitäts-Schema mit SLOs ABGELEHNT (Overhead vor Wirksamkeitsnachweis) |
| R2-REC-8 | [valid] | übernommen, Umsetzung = R1-REC-1: maschinelle Fixture-Ausführung, Checker-Version + Datum in Projektion (§5) |
| R2-REC-9 | [valid] | übernommen = R1-REC-3: nur allowlistete `check_ref`-Dateien, kein Netz, least-privilege, keine Secrets in Fork-Kontexten (D1, D3) |
| R2-REC-10 | [valid] | übernommen: Frontmatter = alleinige Maschinenwahrheit, Body-Konflikte separate Zähl-Zeile (§2, §5); Kampagne als D7 mit Aufwand + Abbruchkriterium |
| R2-REC-11 | [valid] | übernommen = R1-REC-7: Mechanik eigenständig normiert; „nur Scheduling ist echte Abhängigkeit"-Aussage ersetzt (§2) |
| R2-REC-12 | [valid] | übernommen = R1-REC-3 + Zusatz: CI prüft Referenzintegrität (jede check_ref existiert, keine verwaisten Checks) (D1) |
| R2-REC-13 | [valid] | übernommen: X1 als pilot-lokaler Experimentvertrag; Bestehen ⇒ Org-ADR-Kandidat, Scheitern ⇒ automatischer Streichungs-PR (Frontmatter, §13) |
| R2-REC-14 | [valid] | übernommen, Umsetzung = R1-REC-4-Mischungszeile inkl. getrennter Kennzahlen (§5) |

Nicht übernommene Teil-Aspekte sind oben je Zeile begründet; kein REC wurde als
[missversteht-Kontext] oder [out-of-scope] verworfen. Befund-IDs der Runden (AD-*/M28-*)
sind über die REC-Zuordnungen der Reviews vollständig abgedeckt; zwei Befunde ohne
eigene REC sind hier explizit adressiert: R1-AD-5/R2-AD-7 (Codeausführung aus Frontmatter
im öffentlichen Repo) durch D1-Restriktion + Fork-PR-Regel, R1-M28-5 (publizierte Karte
ungeprüfter Zusagen) durch die ephemere Projektion (D2).

## 7 Deep-Dive: die sieben Entscheidungen

**D1 — Invarianten-REFERENZEN im ADR-Frontmatter, Check-Code als reviewte Datei
(R1-REC-3, R2-REC-9/12).** Schema (iil-adrfw, org-weit optional-validiert; Pilot-CI:
Pflicht für neue accepted ADRs — R1-REC-2):
```yaml
zielzustand: invariant            # invariant | nicht-testbar | out-of-budget
zielzustand_begruendung: "…"      # PFLICHT bei nicht-testbar (ein Satz)
invariants:                       # nur bei zielzustand: invariant
  - id: ADR-053-I1
    check_ref: checks/adr-053-i1.yaml   # reviewte Datei; Typen im MVC: python_ast | file
    severity: critical                  # critical | normal
```
Kein ausführbarer String im Frontmatter; `script`/`http` sind bis zu einer eigenen
Sicherheitsentscheidung ausgeschlossen (öffentliches Repo — Fork-PR-Frontmatter darf nie
Kommandozeile des Runners werden; Runner läuft ohne Secrets/Schreibrechte in
PR-Kontexten). CI prüft Referenzintegrität: jede `check_ref` existiert, kein Check ohne
referenzierendes ADR (verwaist), jede Invariante hat eine Fixture. Migration: die
existierenden `drift_check_paths`-Kommentarblöcke der Pilot-ADRs → dieses Schema.
Check-Refactorings editieren Code, nie historische ADRs.

**D2 — Ephemere Projektion (R1-REC-10/12, R2-OOB-2).** `gen_adr_index.py` bekommt eine
zweite Emissions-Stufe `zielzustand.json` — erzeugt **im CI-Lauf als Artefakt und als
Aggregat-Zeile im Report-Issue, NICHT auf main committet**. Damit entfallen: Diff-Gate-
Merge-Konflikte bei ~40 Adds/Monat (R1-M28-6), die publizierte Karte ungeprüfter Zusagen
im öffentlichen Repo (R1-M28-5), und jede Möglichkeit, die Projektion mit einer Wahrheit
zu verwechseln. Inhalt je accepted ADR: Klassifikation, Invarianten mit letztem
Negativproben-Datum + Checker-Version, Ergebnis-Trias des letzten Laufs.

**D3 — Budgetierter Runner.** Erweiterung des `drift_check.py`-Skeletts. Ergebnis je
Invariante: `pass | violation | error` (R2-REC-3). Budget: **max. 10 aktive Invarianten
je Repo UND max. 30 org-weit** (R1-REC-8), vom Runner selbst durchgesetzt (Überschreitung
⇒ Lauf rot mit genau dieser Meldung). **Auswahl-/Verdrängungsregel (R2-REC-5,
deterministisch):** Priorität 1 = belegte Drift-Realfälle, 2 = `severity: critical`,
3 = Rest nach ADR-Alter absteigend; Verdrängung nur durch einen PR, der explizit eine
bestehende Invariante auf `dormant:budget` setzt — nie stillschweigend. **Negativprobe
maschinell (R1-REC-1):** der Runner führt in JEDEM Lauf jede Fixture unter
`tests/negativproben/<id>/` gegen den Check aus und verlangt Rot; besteht sie nicht ⇒
`dormant:aged`, zählt nicht als aktiv. Blockierungs-Staffel (M-1): Budget-, Schema- und
Referenzintegritäts-Verletzungen blockieren CI sofort; `violation` eskaliert über D5;
`error` alarmiert im Betriebsfehler-Pfad und zählt nie als grün.

**D4 — Invariante 0 (Klassifikations-Delta-Selbsttest).** Wie §5: Delta + Pflicht-
Mischungszeile ist Zeile 1 jedes Reports; Delta > 0 über 30 Tage ⇒ `stale` in Zeile 1.
`nicht-testbar`-Stichprobe: 3 zufällige Einträge je Ritual-Fenster werden im Report zur
Sichtprüfung gelistet (R1-REC-4). Negativproben-Alterung: letzte bestandene maschinelle
Ausführung > 90 Tage ⇒ `dormant:aged` — gealtert wird eine Tatsache, kein Feld.

**D5 — Zwei-Arme-Auflösung mit Fristen.** **Lauf := Ritual-Lauf** (R1-REC-6). Kadenz:
Anschluss an `regel-ritual.yml`, aber **eigenes festes Report-Issue** für 041
(R1-REC-12); Fallback bei 038-Ende: eigener Schritt im selben Workflow-File.
Eskalation einer bestätigten `violation`: Entscheidungsvorlage nach **2 roten
Ritual-Fenstern ODER 14 Tagen, je nachdem was früher eintritt**; bei
`severity: critical` nach **1 rotem Lauf** (R2-REC-7). Die Vorlage hat genau zwei
Ausgänge: (a) Issue „Ist anpassen" (vorbefüllt) oder (b) ADR-Stub supersede/amend via
`adr_next_number.py`. Jeder Rückbau-Vollzug loggt in den Sunset-Ledger. Bleibt die
Vorlage ein weiteres Fenster unentschieden ⇒ `dormant:unresolved` — zählt weiter als
offene Schuld, belastet das Budget, steht dauerhaft im Report (R2-REC-4-Kern).
`error`-Ergebnisse durchlaufen NICHT die Zwei-Arme-Mechanik, sondern den
Betriebsfehler-Pfad (Check reparieren).

**D6 — Grenzziehung + ein Amendment-Vorschlag (unverändert).** Steuerungsschicht bleibt
KONZ-038. An 038 §5.4 wird vorgeschlagen (dort zu entscheiden, ungebündelt):
Vollzugsform des Evidenz-Sunset für Maschinen-Memory ist **Löschen** (git-History =
Archiv, Ledger-Eintrag bleibt Pflicht), nicht `deprecated`-Verbleib in der geladenen
Menge — Ausnahme: falsifizierte Hypothesen werden vor Löschung zum 🌀-Destillat
eingedampft. Begründung: Memory wird injiziert, nicht nachgeschlagen.

**D7 — Klassifikationskampagne Pilot-Repos (NEU — R1-REC-5, R2-REC-10).** Eigene,
aufwandsgeschätzte MVC-Position: alle accepted ADRs der beiden Pilot-Repos erhalten das
`zielzustand`-Feld (Mehrheit erwartbar `out-of-budget` — das ist der ehrliche Zustand).
**Baseline-Einfrierung (R1-REC-11):** `count(accepted)` wird VOR Beginn der Kampagne
committet; der Kill-Gate-Beleg weist `vorher/nachher` aus, damit der Nenner nicht Teil
des Ergebnisses ist. Abbruchkriterium: > 4 h Gesamtaufwand ⇒ Kampagne stoppt, K-A wird
auf den bis dahin klassifizierten, benannten Satz eingeschränkt und das ausgewiesen.

**MVC-Regel M1 (unverändert):** D1 wird nie ohne D3 gemergt — Schema und Runner landen
gekoppelt, damit nie wieder ein deklariertes Feld ohne Konsumenten entsteht.

## 8 Alternativen

| Alternative | Warum verworfen |
|---|---|
| A1: Nur Runner bauen, kein Konzept | Bedarf bestätigt durch beide externe Runden (R2-PRO-1: Autorenvertrag + Ausführungssemantik + Rückbauprozess brauchen ein challengebares Artefakt); ABER der Preis wurde extern korrekt nachgetragen: 041 ist die dritte laufende Lifecycle-Verpflichtung eines Solo-Owners — Antwort: pilot-lokaler Experimentvertrag mit automatischem Streichungs-PR statt drittem unabhängigem Dauer-Artefakt (R2-REC-13) |
| A2: Ur-Entwurf (LLM-Destillat + abgenommene YAML, Voll-Coverage, Org-Ebene) | dreifach intern falsifiziert, extern doppelt bestätigt |
| A3: Voll-Migration aller ~181 accepted ADRs sofort | Kapazität nachweislich nicht vorhanden; D7 ersetzt das durch eine billige Klassifikations- (nicht Invarianten-)Kampagne mit Abbruchkriterium |
| A4: Warten bis KONZ-037/038 ihre Kill-Gates bestanden haben | Korrigiert (R1-REC-7): das frühere Scheduling-Argument deckte nur 038. Ehrliche Antwort für 037: 041 **normiert die geborgten Mechaniken eigenständig** (§5) — scheitert 037, fällt Attribution, nicht Fundament; ein Warten würde den belegten Drift-Realfall (risk-hub ADR-053, B7) weitere Monate ungeprüft lassen |
| A5 (extern, R1-OOB-3): nur `review_by` auf alle accepted ADRs, kein Runner | als Ersatz verworfen (erzeugt Urteilsarbeit = knappste Ressource, hohes „46. totes Feld"-Risiko); als möglicher Folgekandidat nach bestandenem Kill-Gate notiert (§9) |

## 9 Out-of-the-Box

- **`enforces:`-Rückrichtung (R1-REC-13/OOB-1, 60-Tage-Kandidat):** bestehende CI-Checks/
  Tests bekommen ein optionales Feld `enforces: platform:ADR-NNN`; die Projektion emittiert
  das mit — kostenlose Verkleinerung der `out-of-budget`-Menge aus dem vorhandenen
  Testbestand, ohne Budget zu verbrauchen.
- **Rückbau-Quote als Gesundheitsmetrik:** `superseded_pro_Quartal / neue_ADRs_pro_Quartal`
  als eine Zeile im Ritual-Report.
- **Invarianten-Vererbung bei Supersede:** Supersede-ADR erbt die Invarianten des
  Vorgängers zur expliziten Übernahme/Streichung.
- **`proposed`-Limbo-Kampagne** (45 ADRs) und **A5/`review_by`-Kadenz**: Folgekandidaten
  nach bestandenem Kill-Gate, nicht Teil des MVC.

## 10 Befunde

| # | Befund | Evidenz | Schwere |
|---|---|---|---|
| B1 | 45–50 ADRs mit maschinenlesbaren Drift-Feldern, 0 Konsumenten | C6 | hoch |
| B2 | drift_check.py prüft gegen hartkodiertes Soll, nicht gegen ADRs | C4 | hoch |
| B3 | ADR-Status-Frontmatter schmutzig: 0/3-Stichprobe intern widersprüchlich | C7 | hoch |
| B4 | 181 accepted vs 8 superseded — ADR-Ratsche kennt nur Anbau | C9 | hoch |
| B5 | Lifecycle-Vollzugsquote fälliger KONZ ~14 % (1/7) | C8 | hoch |
| B6 | Sunset-Ledger existiert mit 0 Einträgen | C10 | mittel |
| B7 | Belegte ADR-Drift (risk-hub ADR-053: accepted + real umgesetzt, Frontmatter sagt `implementation_status: none`) seit ~7 Wochen unbemerkt | C13 | hoch |
| B8 | Kill-Gate der Vorfassung war papier-bestehbar (Negativprobe als String; K-B zeitlich unerreichbar) — von zwei externen Runden unabhängig gefunden | C12 | hoch |
| B9 | **Der ursprünglich „verbindliche Erstfall" (ADR-052/`.delay()`) war selbst falsch** — ADR-052 ist `proposed` und regelt periodische Jobs, nicht `.delay()`; ADR-053 hat den Worker beschlossen und umgesetzt. Quelle des Irrtums: eine 53 Tage alte 🌀-Memory, deren offene Entscheidung 4 Tage später fiel und die nie nachgezogen wurde. Sie führte den Pilot-Auftrag auf eine falsche Prämisse. | C13 | hoch |

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme | Restrisiko |
|---|---|---|---|
| R1 | Rot-Lawine → Report ignoriert | Budget + Fristen-Eskalation statt Dauer-Rot; error≠violation-Trennung | mittel |
| R2 | Solo-Owner-Kapazität | Org-Deckel 30; maschinelle Negativproben statt Pflege-Feldern; D7-Abbruchkriterium; `dormant`-Automatik mit sichtbarer Schuld | mittel |
| R3 | 037/038 scheitern an eigenen Kill-Gates | Mechanik eigenständig normiert (§2/§5); Scheduling-Fallback (D5) | niedrig |
| R4 | Schema deklariert-aber-ignoriert (ADR-167-Muster) | M1: Schema nie ohne Runner im selben PR; CI-Referenzintegrität | niedrig |
| R5 | Fork-PR-Codeausführung im öffentlichen Repo | keine ausführbaren Frontmatter-Strings; nur allowlistete deklarative check_refs; Runner ohne Secrets in PR-Kontexten (D1) | niedrig |

## 12 Empfehlungen (MVC — ungebündelt entscheidbar)

| # | Entscheidung | Artefakt | Aufwand |
|---|---|---|---|
| D1 | `zielzustand`/`invariants`-Schema (Referenzen, severity) + Checks-Registry + Migration Pilot-ADRs | iil-adrfw-Schema (optional) + Pilot-CI-Gate + `checks/` + 3–5 ADR-PRs | M |
| D2 | Ephemere Projektion `zielzustand.json` (CI-Artefakt + Aggregat-Zeile, nicht committet) | `gen_adr_index.py`-Stufe | S |
| D3 | Budgetierter Runner (10/Repo, 30 org-weit, pass/violation/error, maschinelle Negativproben je Lauf, Auswahlregel) | `scripts/zielzustand_runner.py` + `tests/negativproben/` | M |
| D4 | Invariante 0 (Delta + Mischungszeile) + Alterung 90 d + Stichprobe | im Runner | S |
| D5 | Eigenes Report-Issue + Fristen-Eskalation (2 Fenster/14 d; critical: 1 Lauf) + Zwei-Buttons + Ledger-Pflicht | Workflow-Schritt + 2 Templates + Issue | M |
| D6 | Amendment-Vorschlag an KONZ-038 §5.4 (Memory-Löschen, 🌀-Ausnahme) | kleiner PR an KONZ-038 | S |
| D7 | Klassifikationskampagne Pilot-Repos (Baseline eingefroren, Abbruch > 4 h) | Feld-PRs + Baseline-Commit | M |

**M1:** D1 nie ohne D3 mergen. **Erstfälle (verbindlich, Rev 3):** risk-hub **ADR-053
`implementation_status`-Drift** als Plumbing-Fall (K-B1) — die Invariante prüft die drei
belegten ADR-053-Zusagen (Celery-Service, durabler Redis-Broker, async Dispatch) gegen
das Repo und vergleicht das Ergebnis mit dem deklarierten `implementation_status`;
erwartetes Reallauf-Ergebnis ist `violation` (Evidenz „implementiert" vs. Deklaration
„none"). **Plus ein verblindeter Zweitfall** für K-B2: eine vom Owner erst
NACH Runner-Merge ausgewählte Invariante, deren Verletzung per Mutation eingespielt wird
und die volle Eskalation (Fristen, Vorlage, Entscheidung, Ledger) real durchläuft.

## 13 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** D1–D5 + D7 umsetzen (Pilot platform + risk-hub), D6
separat an KONZ-038. Kein Org-Rollout von Invarianten/Gates, kein Org-ADR vor der Bilanz.
**Scheitern ⇒ automatischer Streichungs-PR** (Schema-Feld aus iil-adrfw, Runner,
Workflow-Schritt, Konzept auf `sunset` + Sunset-Ledger-Eintrag) — kein Zombie-Verbleib
(R2-REC-13/M28-5).

**Kill-Gate — Stichtag: Tag 15 nach Merge des letzten MVC-PRs, mindestens jedoch 2
Ritual-Fenster (was später eintritt). Alle vier UND-verknüpft; bei Nichterfüllung wird
GESTRICHEN, nicht nachgebessert:**

- **K-A (Klassifikation):** Delta = 0 über den **benannten, vor D7 eingefrorenen
  Pilot-ADR-Satz** (Baseline-Commit; Beleg weist `accepted vorher/nachher` aus).
  Maschinell aus der Projektion gemessen; Body-Konflikte separat gezählt, nicht
  weginterpretiert.
- **K-B1 (Plumbing-Vollzug):** der ADR-053-Erstfall ist als `violation` erkannt UND sein
  Arm ist vollzogen (gemergter Ist-Fix — hier: `implementation_status` auf den belegten
  Wert korrigiert — ODER gemergtes Supersede-/Amend-ADR, je mit Link auf den Report).
- **K-B2 (Lifecycle-Vollzug, verblindet):** der Zweitfall (§12) hat die volle
  Eskalationsmechanik real durchlaufen — Fristen ausgelöst, Vorlage erzeugt, Entscheidung
  getroffen, Ledger-Eintrag — ohne manuelles Eingreifen außerhalb der Mechanik.
- **K-C (Negativproben-Quote, maschinell):** 100 % der als aktiv gezählten Invarianten
  haben eine im letzten Lauf **maschinell ausgeführte und bestandene** Fixture-
  Negativprobe (Datum + Checker-Version aus der Projektion, nicht aus Frontmatter).

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| K-A Delta=0 (eingefrorener Pilot-Satz) | offen | — |
| K-B1 Plumbing-Vollzug ADR-053 | offen | — |
| K-B2 Lifecycle-Vollzug verblindeter Zweitfall | offen | — |
| K-C 100 % maschinelle Negativproben aktiv | offen | — |

**30/60/90:**
- **30 Tage:** D1+D3 gekoppelt gemergt (M1), D2, D4, D7-Baseline; ADR-053-Invariante
  aktiv mit maschineller Negativprobe; erster Ritual-Report mit Delta-Mischungszeile;
  Zweitfall-Mutation eingespielt.
- **60 Tage:** Kill-Gate-Bilanz in obiger Tabelle. Bestehen ⇒ Org-ADR-Vorlage +
  Ausbreitungsplan (je Repo einzeln, Repo-Budget bleibt, Org-Deckel bleibt) +
  `enforces:`-Rückrichtung (§9). Scheitern ⇒ Streichungs-PR wie oben.
- **90 Tage:** nur bei Bestehen — zweites Domain-Repo, `proposed`-Limbo-Kampagne als
  eigener Vorschlag, Rückbau-Quote im Report etabliert.
