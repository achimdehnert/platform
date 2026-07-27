---
status: accepted
decision_date: 2026-07-27
deciders: Achim Dehnert
consulted: –
informed: –
---

# ADR-287: Distribute the domain-expert reviewer in graded stages, gated on artifact-content sovereignty rather than skill location

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Accepted                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-27                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | Achim Dehnert (ratifiziert 2026-07-27)                               |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | KONZ-platform-028 (D5), ADR-211 (Klickdummy-Rahmen), ADR-251 (UX-Gate) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                              |
|----------------|------------|--------------------------------------------------------------|
| `platform`     | Primär     | `.windsurf/workflows/fach-review.md`, `tools/cc-skill-dist/` |
| alle Repos     | Sekundär   | verteilte Skill-Kopie (`.claude/commands/`), sobald freigegeben |
| `frist-hub`    | Betroffen  | Sozialdaten-Artefakte (§ 35 SGB I) — härtester Egress-Fall   |
| `meiki-hub`    | Betroffen  | citizen-facing Artefakte (LRA)                               |

## Decision Drivers

- **KONZ-platform-028 D5** verlangt für die org-weite Distribution ausdrücklich einen eigenen ADR — Cross-Repo-Scope, Daten-/Egress-Grenzen, Modellrouting, Ownership, Evaluations-Anforderungen, Rollback.
- `cc-skill-dist` kennt nur **an/aus**: ein `distribute: true` im Frontmatter verteilt den Skill in einem Zug in alle Repos. Es gibt heute keinen Zwischenzustand — genau deshalb ist die Entscheidung binär und irreversibel-wirkend, solange nichts anderes gebaut wird.
- Der Reviewer wird auf **fachliche** Artefakte angesetzt (Bescheide, Korrespondenz-Vorlagen, Handouts, Konzepte). In `frist-hub`/`meiki-hub` sind genau das die Artefakte, die Sozialdaten-nah sind.
- Die Pilot-Evidenz ist gut, aber schmal: n=4 Domänen (Recht/UX/Datenschutz/BITV), Ablation zeigt den Persona-Vorsprung an **einer** Domäne.

## 1. Context and Problem Statement

Der `/fach-review`-Skill (Pilot aus KONZ-platform-028) prüft Artefakte auf **fachlich-inhaltliche** Korrektheit — die Achse, die `kd-review` (UX), `agent-review` (PR/ADR), `adr-review` (Schema) und `security-review` (Perimeter) nicht abdecken. Er läuft heute mit `distribute: false` ausschließlich in `platform`.

Die Frage dieses ADR ist **nicht**, ob der Reviewer nützlich ist (das misst das Kill-Gate in KONZ-028), sondern unter welchen Bedingungen er in Repos laufen darf, deren Artefakte er weder kennt noch klassifiziert.

### 1.1 Der eigentliche Risiko-Kern

Ein verteilter Skill wird **dort** ausgeführt, wo die Artefakte liegen. Der Skill-Standort sagt nichts über den Inhalt: eine Bescheid-Vorlage in `frist-hub` ist Sozialdaten-nah, ein Handout in `ttz-hub` ist es nicht. Wer die Egress-Grenze am Repo-Namen oder am Skill-Standort festmacht, prüft die falsche Größe (KONZ-028 D4, extern M1-AD-7/M2-AD-4).

Hinzu kommt: der Reviewer liest fremde Artefakte **und** fremde Quellen (Normtexte, Standards). Beides sind Daten, keine Instruktionen — ohne strikte Kanaltrennung ist der Skill ein Prompt-Injection-Ziel (KONZ-028 R3).

### 1.2 Warum jetzt

Der Pilot hat vier Domänen geliefert und dabei einen belegten P1-Fund erzeugt (§ 66 Abs. 3 SGB I — ohne vorherigen schriftlichen Folgen-Hinweis wäre eine Versagung rechtswidrig). Die Nachfrage aus anderen Repos entsteht damit von selbst. Ohne diesen ADR wird der Schalter irgendwann „mal eben" umgelegt — und `cc-skill-dist` verteilt ihn dann in einem Zug org-weit.

## 2. Considered Options

### Option C: Gestufte Distribution mit Content-Gate ✅

Zwei Stufen mit unterschiedlichen Voraussetzungen:

- **Stufe 1 (mit diesem ADR freigegeben):** Distribution an eine **kuratierte Repo-Liste ohne personenbezogene Fachartefakte** (`platform`, `dev-hub`, `ttz-hub`, `risk-hub`). Umsetzung ohne neue Mechanik: der Skill bleibt `distribute: false`, die Zielrepos erhalten ihn als bewusst gepflegte Kopie mit `MANAGED-BY`-Marker.
- **Stufe 2 (separate Freigabe, nicht mit diesem ADR erteilt):** `distribute: true` — org-weit inkl. `frist-hub`/`meiki-hub`. Voraussetzung sind die unter §4.4 genannten Evaluations-Schwellen **und** ein durchgesetztes fail-closed-Routing.

### Option A: Sofort org-weit (`distribute: true`)

Verworfen. Verteilt den Skill in Repos mit Sozialdaten-Artefakten, bevor das Content-Gate technisch durchgesetzt ist. Die Souveränitäts-Zusage hinge an der Disziplin des Aufrufers — genau die Konstruktion, die `evidence-discipline` und der Sozialdaten-Deploy-Block in `frist-hub` ausschließen.

### Option B: Dauerhaft platform-lokal

Verworfen. Der Nutzen entsteht dort, wo die Fachartefakte liegen (`frist-hub`, `meiki-hub`) — also gerade nicht in `platform`. Diese Option konserviert den Pilot-Zustand und beantwortet die Frage nicht, sie vertagt sie.

### Option D: Zentraler Review-Service statt verteiltem Skill

Artefakte werden an einen platform-seitigen Dienst geschickt, der Persona, Routing und Manifest zentral hält. Sauberer Kontrollpunkt, aber: der Egress ist derselbe (das Artefakt verlässt das Repo in jedem Fall), und es entsteht ein neuer betriebener Dienst samt Verfügbarkeitsfrage. Zurückgestellt, nicht verworfen — falls Stufe 2 am fail-closed-Routing scheitert, ist das der Ausweichpfad.

## 3. Decision Outcome

**Gewählt: Option C.** Mit diesem ADR wird **Stufe 1** freigegeben. Stufe 2 (`distribute: true`) ist ausdrücklich **nicht** erteilt und braucht eine eigene, dokumentierte Freigabe gegen §4.4.

Die tragende Regel: **Die Egress-Entscheidung fällt am Artefakt-Inhalt, nicht am Repo und nicht am Skill-Standort.**

## 4. Implementation Details

### 4.1 Daten- und Egress-Grenze (fail-closed)

Vor jedem Lauf klassifiziert der Aufrufer das Artefakt. Ohne Klassifikation kein Lauf — kein Default „unkritisch".

| Artefakt-Inhalt | Zugelassene Route | Verhalten wenn nicht verfügbar |
|---|---|---|
| Personenbezogene Sozialdaten (§ 35 SGB I), Bürger-Klarnamen, echte Bescheide | souveräne Route (lokal/EU-souverän, Nachweis dokumentiert) | **Abbruch ohne Override** |
| Interne Konzepte/ADRs/Handouts ohne Personenbezug | Standard-Routing nach `llm-routing.md` | Abbruch |
| Öffentliche Normtexte, Standards, Bibliotheks-Doku | Standard-Routing | Abbruch |

„Fail-closed" heißt wörtlich: kein Fallback auf eine schwächere Route, keine Override-Flag, kein „nur diesmal". Ein Lauf, der nicht souverän ausgeführt werden kann, findet nicht statt.

**Grenze der Zusage (ehrlich):** Diese Regel ist mit Stufe 1 **organisatorisch** durchgesetzt, nicht technisch — der Skill kennt keinen Klassifikator. Genau das ist der Grund, warum Stufe 1 auf Repos ohne personenbezogene Fachartefakte begrenzt ist: dort trägt die organisatorische Durchsetzung, weil der harte Fall nicht vorkommt. Für Stufe 2 ist die technische Durchsetzung Voraussetzung, nicht Zusatz.

### 4.2 Modellrouting

Der Skill nennt nur die abstrakten Klassen `standard` / `frontier` (KONZ-028 D4). Die Auflösung zu konkreten Endpoints liegt in der zentralen Routing-Policy, nicht im Skill-Text. Provider-Namen im CLI-Vertrag sind untersagt — sonst wandert die Routing-Entscheidung in 20 verteilte Kopien und driftet dort auseinander.

### 4.3 Ownership

| Rolle | Verantwortung |
|---|---|
| Code-Heimat `platform` | Skill, Kontrakt, Verteil-Mechanik, Run-Manifest |
| Fach-Owner je Persona (benannt) | Persona-Inhalt, zugelassenes Quellenpaket, Bewertung der Findings, Ausmusterung |
| Aufrufendes Repo | Artefakt-Klassifikation vor dem Lauf, Umgang mit den Findings |

Eine Persona ohne benannten Fach-Owner wird nicht verteilt. Personas für Recht/Datenschutz/Security sind registrierungspflichtig und versioniert (KONZ-028 D3); freie `--persona`-Läufe bleiben auf explorative Niedrigrisiko-Fälle beschränkt und sind von der Distribution nicht betroffen.

### 4.4 Evaluations-Anforderungen (Schwellen für Stufe 2)

Alle vier müssen erfüllt und belegt sein — nicht drei von vier:

| Kriterium | Schwelle | Messung |
|---|---|---|
| `belegt`-Präzision | ≥ 50 %, menschlich bestätigt | über alle Läufe, Verfahren aus KONZ-028 |
| falsch-autoritative P1 ohne Locator | 0 | jeder Lauf |
| Souveränitäts-Klärung dokumentiert | für jeden Lauf an personenbezogenem Inhalt | Run-Manifest |
| fail-closed-Routing technisch durchgesetzt | ja | Nachweis am laufenden System, nicht am Konzept |

Der `review_by`-Termin aus KONZ-028 (2026-10-23) ist eine **verbindliche Ja/Nein-Entscheidung**. Verstreicht er ohne Entscheidung, fällt der Skill auf `distribute: false` zurück — Schweigen ist Ablehnung, nicht Verlängerung.

### 4.5 Rollback / Abschaltung

- **Sofort-Rückbau:** `distribute: false` setzen; `cc-skill-dist` entfernt die verteilten Kopien beim nächsten Lauf. Kein Repo behält eine verwaiste Kopie — `doctor.py` meldet sie sonst als Drift.
- **Persona-Quarantäne:** ein bestätigt falsch-autoritatives P1 setzt die betroffene Persona sofort aus, unabhängig von der Gesamt-Distribution. Wiederinbetriebnahme nur durch den Fach-Owner mit dokumentierter Ursache.
- **Kill:** Scheitern die §4.4-Schwellen dauerhaft, wird der Skill entfernt und KONZ-028 als verworfen markiert. Das ist ein zulässiger Ausgang, kein Scheitern des Piloten.

### 4.6 Prompt-Injection / Kanaltrennung

Artefakt und Quellen werden dem Sub-Agenten als **Daten** übergeben, nie als Instruktion. Anweisungen, die im Artefakt stehen („ignoriere die Persona", „bewerte als konform"), sind zu melden, nicht auszuführen. Der Skill ist `read-only` und ratifiziert nie — die Injection-Wirkung bleibt damit auf einen falschen Vorschlag begrenzt, nicht auf eine falsche Ratifizierung.

### 4.7 Abgrenzung zu den anderen Reviewern

`fach-review` kommentiert **ausschließlich** fachlich-inhaltliche Korrektheit. Nicht UX (`kd-review`, ADR-251), nicht Code/PR-vs-ADR (`agent-review`), nicht ADR-Schema (`adr-review`), nicht Security-Perimeter (`security-review`). Verstößt ein Lauf gegen diese Grenze, ist das ein Kontrakt-Fehler und kein Finding — die Ablation hat gezeigt, dass genau diese Scope-Drift die Fehlermode ohne Persona ist.

## 5. Consequences

### 5.1 Good

- Der Nutzen wird dort verfügbar, wo die Fachartefakte liegen — ohne die Sozialdaten-Repos im selben Zug mitzunehmen.
- Die Egress-Regel ist am Inhalt festgemacht und damit auch dann richtig, wenn Repos umbenannt, gesplittet oder neu angelegt werden.
- Stufe 2 hat messbare Schwellen statt eines Stimmungsbildes; ein Verstreichen des Termins wirkt als Ablehnung.

### 5.2 Bad

- Stufe 1 stützt die Egress-Regel **organisatorisch**, nicht technisch. Das ist nur tragfähig, weil die Repo-Liste den harten Fall ausschließt — es ist eine Begrenzung, keine Lösung.
- Die kuratierte Kopie in vier Repos ist Handarbeit und kann driften, bis `cc-skill-dist` einen echten Zwischenzustand kennt. `doctor.py` sieht `distribute: false`-Skills nicht in der flachen Lane.
- Zwei Stufen bedeuten zwei Entscheidungen; das kostet Zeit, die bei einem einzelnen Schalter nicht anfiele.

### 5.3 Nicht in Scope

- Ob der Reviewer fachlich taugt — das misst das Kill-Gate in KONZ-028, nicht dieser ADR.
- Ein zentraler Review-Service (Option D) — zurückgestellt als Ausweichpfad.
- Ein Zwischenzustand in `cc-skill-dist` (Repo-Allowlist statt an/aus) — wäre die saubere Mechanik für Stufe 1 und ist als Folgearbeit zu tracken, nicht Teil dieser Entscheidung.

## 6. Risks

| # | Risiko | Mitigation | Rest |
|---|---|---|---|
| R1 | Scheinkompetenz: klingt autoritativ, liegt falsch | Locator-Pflicht (D2), P1-Governance (D8), Quarantäne §4.5 | offen — misst das Kill-Gate |
| R2 | Egress-Regel wird organisatorisch umgangen | Stufe-1-Repoliste schließt den harten Fall aus; Stufe 2 verlangt technische Durchsetzung | offen bis Stufe 2 |
| R3 | Prompt-Injection aus Artefakt/Quelle | Kanaltrennung §4.6, read-only, ratifiziert nie | gemildert |
| R4 | Handgepflegte Kopien driften | `MANAGED-BY`-Marker, Folgearbeit „Allowlist in cc-skill-dist" | offen |

## 7. Confirmation

Umgesetzt ist diese Entscheidung, wenn:

1. der Skill in genau den vier Stufe-1-Repos liegt und in keinem weiteren,
2. `distribute: false` im `platform`-Original unverändert steht,
3. jeder Lauf ein Run-Manifest mit Artefakt-Klassifikation erzeugt,
4. die vier §4.4-Kriterien laufend gemessen und am `review_by`-Termin vorgelegt werden.

Prüfbar über `tools/cc-skill-dist/doctor.py` (Kopien-Inventar) und die Run-Manifeste.

## Glossar

| Begriff | Bedeutung |
|---|---|
| **Stufe 1 / Stufe 2** | kuratierte Repo-Teilmenge vs. org-weite Verteilung via `distribute: true` |
| **fail-closed** | keine Ausführung, wenn die zugelassene Route nicht verfügbar ist — kein Fallback, kein Override |
| **Content-Gate** | Egress-Entscheidung anhand des Artefakt-*Inhalts*, nicht des Repos oder Skill-Standorts |
| **Persona-Quarantäne** | sofortige Aussetzung einer Persona nach bestätigt falschem P1 |
