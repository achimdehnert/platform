---
id: ADR-250
title: "Reengineering-Pipeline: Analyse→UCs→KD→Mockup→Deploy als Round-Trip-Kreislauf mit UX-Gate am Klickdummy + Mermaid-UC-Konvention"
status: accepted
date: 2026-06-17
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, achimdehnert, meiki-lra, ttz-lif, bahn-sqf]
domains: [methodology, reengineering, klickdummy, governance]
supersedes: []
amends: []
depends_on: [ADR-211]
related: [ADR-211, ADR-213]
tags: [methodology, reengineering, klickdummy, ux, process, mermaid]
scope:
  include_paths:
    - "docs/adr/ADR-250-*"
---

# ADR-250 — Reengineering-Pipeline mit UX-Gate am Klickdummy + Mermaid-UC-Konvention

## 1. Kontext

### 1.1 Ausgangslage
Bei der apocenna→apo-hub-Neuimplementierung (apo-hub:ADR-001) wurde ein Klickdummy
mit 32 Screens gebaut, **dann** direkt App-Code geschrieben. Beim Acceptance-Test
gegen Realdaten (apo.iil.pet, 2026-06-17) trat eine Reihe von Findings auf (F1–F13),
deren **gemeinsame Wurzel** ist: die implementierte App ist beim Coden über die
Klickdummy-/Use-Case-Spec **hinausgewachsen**, ohne dass UC-Spec und Klickdummy
mitgepflegt wurden. Beispiele: invertierte Rollen-Semantik (Inhaber stellt „Gesuch"
statt „Anfrage"), ungefilterte Aktions-Buttons ohne FSM-Grundlage, unvollständige
Registrierungs-Flows, fehlende Screens im KD.

### 1.2 Problem / Lücken
- **KD↔App-Drift:** Ohne disziplinierten Spec-first-Prozess driften Klickdummy/UCs
  und reale App auseinander; die Drift wird erst teuer im UAT/Prod sichtbar.
- **Waterfall passt nicht zur Realität:** Eine streng lineare Kette
  Analyse→UCs→KD→Mockup→Deploy bricht, sobald (a) Feedback aus späten Stufen
  (Staging-UAT) zurück muss, oder (b) man **mitten** einsteigt (UX-Tweak am KD,
  Bugfix am Deploy) statt jedes Mal bei der Analyse zu beginnen.
- **UC-Repräsentation uneinheitlich:** UCs liegen mal als Prosa, mal als Tabelle,
  mal als YAML vor — nicht konsequent maschinenlesbar **und** visuell.

### 1.3 Constraints
- Muss zu **ADR-211** (Klickdummy = Renderer einer maschinenlesbaren Spec;
  I1 bidirektionale Coverage) passen, nicht dagegen.
- Gilt **org-weit** für Reengineering/Refactoring-Vorhaben, nicht nur apocenna.
- Genesor (ADR-225/246) rendert UC-Coverage + Lineage bereits aus
  `docs/use-cases/UC-*.md` — die Konvention muss das nutzen, nicht umgehen.

## 2. Entscheidung

Wir etablieren die **Reengineering-Pipeline** als **Round-Trip-Kreislauf**, nicht
als Wasserfall:

```
Analyse → Use Cases → Klickdummy → Mockup → Deploy(Staging→Prod)
   ↑__________________ Feedback (Round-Trip) __________________|
   ↳ Jump-in an jeder Stufe erlaubt — mit Upstream-Reconcile-Pflicht
```

**Fünf verbindliche Festlegungen:**

1. **Spec-first, KD = UX-SSoT.** Use-Case-Spec + Klickdummy sind die maßgebliche
   Quelle der UX. Die reale App ist die *Realisierung*, nicht die Wahrheit.

2. **Full Round-Trip.** Feedback aus **jeder** Stufe (insb. Staging-UAT) **muss**
   nach UCs/KD zurückfließen, bevor es in Code zementiert wird. „Im Staging gesehen"
   → erst UC/KD aktualisieren → dann fixen.

3. **Jump-in erlaubt, Reconcile proportional + verpflichtend.** Man darf an der
   passenden Stufe einsteigen (Greenfield→Analyse; UX-Änderung→KD; Datenfix→Deploy).
   **Invariante:** was man anfasst, gleicht man **upstream** ab. Der **Umfang** des
   Reconcile richtet sich nach **Change-Klassen** (REC-4): `trivial` (Copy/Layout) ·
   `route` · `ux` · `fsm` · `daten-rolle` · `emergency`. Klasse + zugehöriger Reconcile-
   Umfang sind **CI-prüfbar** (aus dem Diff abgeleitet bzw. im PR deklariert *und*
   gegen den Diff plausibilisiert — keine reine Selbstdeklaration, sonst Schlupfloch).
   - **Emergency-Pfad (REC-5):** ein produktions-/sicherheitskritischer Fix darf **vor**
     dem KD/UC-Reconcile deployt werden, **erzeugt aber zwingend** ein nachgelagertes
     Reconcile-Ticket mit Frist, das in CI/genesor sichtbar ist und das Repo bis zur
     Erledigung als „reconcile-debt" markiert.

4. **UX-Gate am Klickdummy — als Freigabe-Nachweis, nicht als Commit-Reihenfolge
   (REC-6).** UX-Weiterentwicklung wird zuerst am KD (klickbar, auf genesor) validiert.
   Das Gate ist **nicht** „KD-Commit zeitlich vor Code-Commit" (zu grob — Spikes dürfen
   legitim auf den KD zurückwirken), sondern ein **versionierter Freigabe-Nachweis**:
   `{KD-Commit/Stand, Reviewer/Stakeholder, Status, Datum, betroffene UC-IDs}`. Erst mit
   diesem Nachweis darf der Staging-UX-Code mergen.

5. **Mermaid-UC-Konvention (geschichtet) mit FSM-Single-Source.** Jeder UC ist:
   - **Backbone:** YAML-Frontmatter (`uc_id, primaer_akteur, realisiert_von_klickdummy,
     related_screens, lifecycle_status`) — maschinenlesbar, treibt genesor-Coverage + I1.
   - **Visuelle Schicht:** **Mermaid im UC-Body** — Flow-Diagramm je UC + `stateDiagram`
     der FSM. **FSM-Single-Source (REC-2):** die **Übergangstabelle (Status × Rolle →
     erlaubte Aktionen) ist die primäre Quelle** (ein maschinenlesbares Artefakt, z. B.
     YAML/Tabelle im UC); `stateDiagram`, App-Code **und** Tests werden **daraus generiert
     bzw. dagegen validiert** — nicht drei handgepflegte Parallelstände.
   - **Mermaid-Subset + Lint (REC-7):** nur ein definiertes Diagramm-Subset ist erlaubt;
     ein Lint stellt sicher, dass Diagramme stabil rendern und nicht von der Spec abweichen.
   - Beides in **einer** Datei → rendert nativ auf GitHub **und** in genesor (ein
     Pflegestand). Mermaid **ersetzt die Frontmatter-Spec nicht**.

6. **Coverage ist zweischichtig: strukturell + semantisch (REC-1, REC-3).** I1
   (Route↔UC↔KD-Vollständigkeit) ist notwendig, aber **nicht hinreichend** — sie fängt
   die Pilot-Findings (invertierte Rollen, ungefilterte Status-Aktionen) **nicht**. Daher
   zusätzlich eine **semantische Coverage-Schicht**: je zustands-/rollenabhängigem UC eine
   **Scenario-Matrix** `Rolle × Status × Datenzustand → sichtbare/erlaubte Aktionen +
   erwartete Navigation`. Diese Matrix ist Teil der Spec, treibt KD-Zustände **und**
   App-Action-Tests (REC-11) aus **einer** Quelle.

## 3. Betrachtete Alternativen

- **A — Strenger Wasserfall (Analyse→…→Deploy, einmalig, linear).** Verworfen:
  bricht bei Feedback-Rückfluss und Mid-Pipeline-Einstieg; erzeugt genau die
  Big-Bang-Drift, die apocenna zeigte.
- **B — Code-first / Spec optional.** Verworfen: ist der Status quo, der F1–F13
  produziert hat (Drift wird erst im UAT/Prod teuer).
- **C — KD-only ohne Round-Trip (KD baut man einmal, dann nur noch Code).**
  Verworfen: ohne Feedback-Rückfluss veraltet der KD und verliert seinen
  SSoT-Status — dieselbe Drift, nur verzögert.
- **D — UC als reine Mermaid-Diagramme (kein strukturierter Backbone).**
  Verworfen: verletzt ADR-211 I1 (Markdown/Diagramme sind nicht
  maschinenlesbar-genug für Coverage); genesor könnte keine Coverage prüfen.

## 4. Begründung im Detail

Der Kern ist **„iterativ + nicht-linear, aber mit harter Reconcile-Invariante"**.
Round-Trip und Jump-in geben der Realität nach (Feedback kommt spät; man steigt
mitten ein), ohne die Spec-first-Disziplin aufzugeben — weil ADR-211 I1
(bidirektionale Coverage) als **mechanisches Gate** erzwingt, dass UC+KD bei
jedem Eingriff nachgezogen werden. Die Mermaid-Schicht macht UCs **gleichzeitig**
maschinenprüfbar (Frontmatter) und menschen-/Stakeholder-lesbar (Diagramm) —
ein Artefakt, zwei Oberflächen (GitHub + genesor), kein Doppel-Pflegestand.

## 5. Implementation Plan

1. **UC-Verzeichnis-Konvention:** `docs/use-cases/UC-*.md` je Repo (genesor liest
   das bereits). Frontmatter-Pflichtfelder + Mermaid-Body-Block + Scenario-Matrix.
2. **Lifecycle-Status (REC-9):** Frontmatter-Feld `lifecycle_status ∈ {draft, reviewed,
   approved, implemented, deprecated}`; genesor rendert den Zustand sichtbar (Coverage
   unterscheidet „spezifiziert" von „freigegeben" von „implementiert").
3. **Zweischichtiges Coverage-Gate:** (a) **strukturell** — `klickdummy-i1` +
   genesor-Coverage **100 %** (Route↔UC↔KD); (b) **semantisch** — je zustands-/rollen-UC
   existiert eine Scenario-Matrix; CI-rot bei Lücke in **beiden** Schichten.
4. **FSM-Single-Source (REC-2):** Übergangstabelle (Status×Rolle→Aktionen) als ein
   maschinenlesbares Artefakt im UC; `stateDiagram`, App-`allowed_actions()` **und**
   Action-Tests (REC-11: erlaubte *und* verbotene Aktionen je Status) werden daraus
   generiert/dagegen validiert.
5. **UX-Gate als Freigabe-Nachweis (REC-6):** PR-Template fordert
   `{KD-Stand, Reviewer, Status, Datum, UC-IDs}`; ohne diesen Nachweis kein UX-Code-Merge.
6. **Change-Klassen + Emergency (REC-4/5):** PR-Template deklariert die Change-Klasse;
   CI plausibilisiert sie gegen den Diff und fordert den klassen-passenden Reconcile-Umfang.
   Emergency-Merge erzeugt automatisch ein fristgebundenes Reconcile-Ticket (genesor-sichtbar).
7. **Lokale Dev-Checks (REC-8):** `make uc-check` (o. ä.) zeigt **vor CI** an, welche
   Route/UC/KD-Screen/Scenario-Matrix/FSM-Abdeckung für die aktuelle Änderung fehlt.
8. **Mermaid-Subset + Lint (REC-7):** definiertes Diagramm-Subset; Lint im CI.
9. **Geltungsbereich (REC-10):** dieses ADR markiert je Regel **org-weit** vs.
   **apocenna-Pilot-spezifisch**, damit Pilot-Eigenheiten nicht zur Standardmethodik werden.
   Org-weit: Round-Trip, Jump-in+Reconcile, zweischichtige Coverage, UX-Gate, Mermaid-UC,
   Lifecycle-Status. Pilot-spezifisch: konkrete F1–F13-Inhalte, RequestStatus-FSM-Details.
10. **Pilot = apocenna:** F1–F13 werden **nach** dieser Pipeline abgearbeitet
    (erst UC/KD + Scenario-Matrix vervollständigen/korrigieren → Freigabe am KD → dann
    Staging-Code mit Action-Tests).

## 6. Risiken

- **R1 Round-Trip-Overhead:** Bei trivialen Fixes wäre Voll-Round-Trip zu schwer.
  → Mitigation: Jump-in erlaubt minimal-invasive Pfade; Reconcile-Pflicht skaliert
  mit Umfang (1-Zeilen-Datenfix ≠ neuer Flow).
- **R2 „Jump-in" als Ausrede,** Upstream nie nachzuziehen → Drift kehrt zurück.
  → Mitigation: I1-Coverage-Gate ist mechanisch (CI-rot), nicht Disziplin-abhängig.
- **R3 Mermaid-Wildwuchs** (Diagramme driften vom Code). → Mitigation: FSM-Diagramm
  + Code teilen die Übergangstabelle als Single-Source; Diagramm aus Tabelle generiert
  bzw. gegen sie getestet, wo möglich.

## 7. Konsequenzen

### 7.1 Positiv
- KD/UC werden zur **durablen SSoT**; Drift wird **früh** (am KD) statt **teuer**
  (im UAT/Prod) sichtbar.
- Stakeholder validieren UX klickbar, bevor Code entsteht.
- UCs sind zugleich maschinenprüfbar und visuell — auf GitHub + genesor.

### 7.2 Trade-offs
- Mehr Vorab-Disziplin (UC+KD pflegen) gegen weniger Spät-Rework.
- Round-Trip kostet Latenz bei großen Änderungen (bewusst in Kauf genommen).

### 7.3 Nicht in Scope
- Konkrete KD-Tooling-Wahl (bleibt iil-klickdummy / ADR-211).
- Prod-Deploy-Mechanik (eigene ADRs).

## 8. Validation Criteria

- **V1 (strukturell):** genesor-Coverage **100 %** (jede App-Route ↔ UC + KD-Screen);
  `klickdummy-i1` grün.
- **V2 (Freigabe-Nachweis, REC-6):** UX-Änderungen tragen einen versionierten Nachweis
  `{KD-Stand, Reviewer, Status, Datum, UC-IDs}` — nicht bloß eine Commit-Reihenfolge.
- **V3 (FSM):** Jeder zustandsbehaftete UC hat ein `stateDiagram`; Diagramm, Code und
  Tests sind nachweislich aus **einer** Übergangstabelle abgeleitet/dagegen validiert.
- **V4 (Pilot):** apocenna — F1–F13 erst in UC/KD + Scenario-Matrix korrigiert + am KD
  freigegeben, dann in Staging umgesetzt.
- **V5 (semantisch, REC-1/3):** Je zustands-/rollenabhängigem UC existiert eine
  Scenario-Matrix (Rolle×Status×Datenzustand→Aktionen+Navigation); CI prüft Vorhandensein.
- **V6 (Action-Tests im Code, REC-11):** Automatisierte Tests belegen **erlaubte UND
  verbotene** Aktionen je (Status×Rolle) im App-Code — nicht nur im KD.
- **V7 (Lifecycle, REC-9):** Jeder UC trägt `lifecycle_status`; genesor rendert den Zustand.
- **V8 (lokal, REC-8):** `make uc-check` meldet fehlende Coverage vor CI (DX-Frühwarnung).
- **Optional (REC-12):** selektive Visual-Regression KD↔Staging für **zentrale** Screens
  als gezieltes Qualitätsnetz — **kein** pauschales hartes Gate (Fragilität bei
  Layout/Daten bewusst vermieden).

## 9. Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **KD** | Klickdummy — klickbarer Renderer der UX-Spec (ADR-211) |
| **UC** | Use Case — Anwendungsfall, hier als `docs/use-cases/UC-*.md` |
| **SSoT** | Single Source of Truth — maßgebliche Quelle |
| **FSM** | Finite State Machine — Zustandsmaschine (z. B. Vorgangs-Status) |
| **Round-Trip** | Rückfluss von Feedback aus späteren Stufen in frühere |
| **Jump-in** | Einstieg in die Pipeline an einer mittleren Stufe statt am Anfang |
| **Reconcile** | Upstream-Abgleich (UC+KD nachziehen) nach einem Eingriff |
| **UX-Gate** | Freigabe der UX am KD als Voraussetzung für Staging-Code |
| **genesor** | Cross-Repo-Klickdummy-/UC-Übersicht auf iil.pet/genesor (ADR-225/246) |

## 10. Referenzen

- `platform:ADR-211` — Klickdummy = Spec-Renderer, I1 bidirektionale Coverage
- `platform:ADR-225` / `platform:ADR-246` — genesor-Ingest (UC-Coverage + Lineage)
- `apo-hub:ADR-001` — apocenna-Neuimplementierung (Pilot dieser Pipeline)
- UAT-Findings F1–F13 + M1/M2: `~/shared/apocenna-uat-findings-2026-06-17.md`

## 11. Changelog

- 2026-06-17: Initial (Proposed). Aus apocenna-UAT-Empirie (M1/M2) abgeleitet;
  Round-Trip + Jump-in als Kern auf Nutzer-Vorgabe.
- 2026-06-17: **Rev nach externer Zweitmeinung** (`/adr-handoff-extern`, cross-provider).
  12/12 RECs als `[valid]` eingearbeitet (Step-5-Tag-Tabelle in §12). Kern-Schärfung:
  Coverage von *strukturell* auf **strukturell+semantisch** erweitert (§2.6, V5); FSM
  bekommt eine **Single-Source-Übergangstabelle** (§2.5, REC-2); **Change-Klassen +
  Emergency-Pfad** (§2.3); UX-Gate = **Freigabe-Nachweis** statt Commit-Reihenfolge (§2.4);
  Action-Tests im Code (V6), Lifecycle-Status (REC-9), Mermaid-Subset+Lint (REC-7),
  lokale Dev-Checks (REC-8), org-weit-vs-Pilot-Markierung (REC-10).
- 2026-06-17: **Status → Accepted** (nach eingearbeiteter externer Review; entscheidungsreif,
  Pilot apocenna setzt sie als erstes um).

## 12. Externe Zweitmeinung — Rückfluss-Gate (Nachweis)

Externe Review (cross-provider, eine Runde) auf Basis des Briefings
`~/shared/adr-handoff-ADR-250-2026-06-17.md`. Jede REC getaggt; nur `[valid]` eingearbeitet
(als Änderung mit eigener Begründung, nicht als wörtliche Übernahme).

| REC | Verdikt | Eingearbeitet in |
|-----|---------|------------------|
| REC-1 semant. Coverage | [valid] | §2.6, §8.V5 |
| REC-2 FSM-Single-Source | [valid] | §2.5, §5.4, §8.V3 |
| REC-3 Scenario-Matrix | [valid] | §2.6, §5.3, §8.V5 |
| REC-4 Change-Klassen | [valid] | §2.3, §5.6 (CI-prüfbar, kein Selbstdeklarations-Schlupfloch) |
| REC-5 Emergency-Pfad | [valid] | §2.3, §5.6 |
| REC-6 Freigabe-Nachweis | [valid] | §2.4, §5.5, §8.V2 |
| REC-7 Mermaid-Subset/Lint | [valid] | §2.5, §5.8 |
| REC-8 lokale Dev-Checks | [valid] | §5.7, §8.V8 |
| REC-9 Lifecycle-Status | [valid] | §5.2, §8.V7 |
| REC-10 org-weit vs Pilot | [valid] | §5.9 |
| REC-11 Action-Tests im Code | [valid] | §5.4, §8.V6 |
| REC-12 Visual-Regression | [valid, optional] | §8 (optionales Netz, kein hartes Gate) |

Keine REC als `[missversteht-Kontext]`/`[out-of-scope]` getaggt — die Review traf die
strukturell-vs-semantisch-Lücke, die der Pilot (F2/F13) empirisch belegt hatte.
