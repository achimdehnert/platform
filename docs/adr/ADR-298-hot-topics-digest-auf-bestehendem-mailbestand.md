---
status: proposed
decision_date: 2026-08-29
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-286, ADR-293, ADR-294, ADR-295]
implementation_status: not_started
last_reviewed: 2026-08-29
staleness_months: 6
---

<!--
  ADR-298 — Basis: docs/templates/adr-template.md v2.1
-->

# ADR-298: Den Hot-Topics-Digest auf den bestehenden Mailbestand setzen statt auf einen vierten Postfach-Zugang

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-08-29                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-286 (Mail-Agent), ADR-293 (Vollständige Verfügbarkeit), ADR-294 (LLM-Gateway), ADR-295 (Zweiter Standort) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                          |
|----------------|------------|---------------------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `tools/mail_agent/` (Transport bleibt hier) |
| `news-hub`     | Primär     | Digest-App: Themenbildung, Recherche, Darstellung        |
| `dev-hub`      | Sekundär   | `apps/mail_agent/` — liefert die Lesenaht                |
| `researchfw`   | Sekundär   | Recherche-Stufe (Suche, Citations)                       |

---

## Decision Drivers

- **Kein vierter Postfach-Zugang**: Transport zu den Konten ist mit ADR-286 in
  `platform/tools/mail_agent` gebündelt. Ein zweiter Leser derselben Postfächer
  verdoppelt Zugangsdaten, Rate-Limits und Fehlerbilder.
- **Löschbarkeit bleibt beantwortbar**: ADR-293 macht Volltext und Anhänge dauerhaft
  verfügbar, aber verschlüsselt und einzeln schredderbar. Ein Digest, der Mailtexte
  in eine eigene Datenhaltung kopiert, hebelt Crypto-Shredding aus.
- **Die Ausschlussregel ist die Speichergrenze** (ADR-293 §3.2): Was der Mail-Agent
  nicht indexiert, darf auch der Digest nicht sehen. Zwei Regelwerke driften.
- **Datensouveränität**: Mailinhalte gehen für Themenbildung und Zusammenfassung an
  ein Cloud-LLM. Das ist eine Grenzüberschreitung, die benannt und begrenzt gehört.
- **Recherche ist gelöst**: `iil-researchfw` liefert asynchrone Suche mit Citations;
  eine zweite Recherche-Implementierung wäre Doppelarbeit.

---

## 1. Context and Problem Statement

Aus Newsletter-Ordnern dreier Konten (privat, IIL, Hochschule) soll ein regelmäßiger
„Hot-Topics-Letter" entstehen: wiederkehrende Themen werden erkannt, extern
nachrecherchiert und mit Belegen dargestellt — im Zuschnitt einer Nachrichten-Übersicht,
nicht als Weiterleitung einzelner Mails.

Die naheliegende Bauform — eine neue App liest die Postfächer selbst — kollidiert mit
einer bereits getroffenen Architektur: Für Mail existiert seit ADR-286 eine eigene Lane
mit Transport, Ausschlussregel, Verschlüsselung und Löschpfad.

### 1.1 Ist-Zustand

| Baustein | Ort | Zustand |
|---|---|---|
| Mail-Transport (IMAP/Graph) | `platform/tools/mail_agent` | in Betrieb (ADR-286) |
| Mail-Modelle, Volltext, Ausschlussregel | `dev-hub/apps/mail_agent` | Volltext-Beschluss ADR-293, teilweise umgesetzt |
| Zweiter Standort des Bestands | Dev-Host | beschlossen ADR-295, Umsetzung offen |
| Recherche (Suche, Citations, Export) | `iil-researchfw` | veröffentlicht, nutzbar |
| LLM-Zugang | ADR-294 (Gateway) / `aifw` | Gateway vorgeschlagen, `aifw` in Betrieb |
| Digest-Anwendung | `news-hub` | neu, leer |

### 1.2 Warum jetzt

Das Repo `news-hub` und der akzeptierte Zielzustand existieren seit 2026-08-29. Die
Entscheidung, woher der Digest seine Mails nimmt, fällt vor der ersten Zeile Code —
danach ist sie nur noch teuer korrigierbar.

---

## 2. Considered Options

### Option A: Digest liest den Mail-Agent-Bestand über eine benannte Lesenaht ✅

`news-hub` bekommt **keine** Postfach-Zugangsdaten. Der Mail-Agent stellt eine
read-only Naht bereit (Kommando-Export oder schmale HTTP-Sicht), die je Konto und
Ordner die im Umfang liegenden Nachrichten mit Herkunftsangabe liefert.

**Pros:**
- Ein Transport, ein Umfang, eine Ausschlussregel — kein zweites Regelwerk
- Crypto-Shredding bleibt wirksam: der Digest hält Verweise, keine Zweitkopie der Texte
- `news-hub` bleibt ohne Postfach-Geheimnisse und damit deutlich weniger schutzbedürftig
- Die Naht ist testbar, ohne ein echtes Postfach anzufassen

**Cons:**
- Abhängigkeit von einem Repo, dessen Volltext-Umsetzung erst teilweise steht
- Die Naht muss gebaut werden, bevor der Digest echte Daten sieht

### Option B: Digest wird eine App in `dev-hub` neben dem Mail-Agent

**Pros:**
- Direkter Zugriff auf die Modelle, keine Naht nötig
- Kein weiteres Repo im Betrieb

**Cons:**
- `dev-hub` ist das Entwickler-Portal; ein persönlicher Nachrichten-Digest ist dort
  thematisch fremd → **Abgelehnt weil:** die Hub-Grenzen sonst bedeutungslos werden
- Recherche- und Darstellungs-Abhängigkeiten wandern in ein Repo, das sie nicht braucht

### Option C: `news-hub` öffnet einen eigenen Postfach-Zugang

**Pros:**
- Sofort startfähig, keine Abhängigkeit von fremdem Umsetzungsstand

**Cons:**
- Vierter Leser derselben Postfächer, zweite Kopie der Zugangsdaten
- Zweites Ausschluss-Regelwerk, das gegen ADR-293 driften kann
- Mailtexte lägen doppelt → **Abgelehnt weil:** eine Löschanfrage nicht mehr an einer
  Stelle beantwortbar wäre

---

## 3. Decision Outcome

**Gewählte Option: Option A — Lesenaht auf den bestehenden Mailbestand.**

Der Digest ist ein Konsument, kein zweiter Mail-Client. Option C wäre schneller, würde
aber genau die Eigenschaft zerstören, die ADR-293 teuer erkauft hat: dass eine Löschung
an einer Stelle wirkt. Option B löst das technische Problem, verletzt aber die
Repo-Grenzen — der Digest ist kein Entwickler-Werkzeug.

Die Konsequenz für den Zielzustand ist ausdrücklich: **ohne die Naht gibt es keinen
echten Lauf.** Bis sie steht, arbeitet `news-hub` gegen synthetische Proben.

---

## 4. Implementation Details

### 4.1 Lesenaht (dev-hub → news-hub)

Vertrag je Nachricht, bewusst schmal:

| Feld | Zweck |
|---|---|
| `konto`, `ordner` | Herkunft, zugleich Filter des Laufs |
| `betreff`, `datum` | Beleg-Angabe im Digest |
| `text` | Eingabe der Themenbildung |
| `nachricht_ref` | Rückverweis; der Digest speichert **keinen** Zweittext dauerhaft |

Die Ordnerliste ist **Pflichtargument** des Laufs. Kein implizites „alle Ordner": der
Umfang eines Laufs ist genau die übergebene Liste, und ein leeres Argument ist ein
Fehler, kein Vollscan.

### 4.2 Themenbildung und Recherche

1. Gruppierung der Nachrichten des Zeitfensters zu Themen — deterministisch, damit ein
   zweiter Lauf über dasselbe Fenster dieselben Themen-IDs liefert.
2. Je Thema eine Recherche über `iil-researchfw` (Suche + Citations).
3. **Beleg-Pflicht:** Ein Thema erscheint nur mit mindestens einer Mail-Herkunft **und**
   mindestens einer externen Quelle mit URL. Themen ohne Beleg fallen aus dem Digest —
   sie werden nicht „unbelegt" markiert, sondern weggelassen.

### 4.3 LLM-Zugang

Standard ist T1a nach `policies/llm-routing.md`: `groq/openai/gpt-oss-120b`, Fallback
`cerebras/gpt-oss-120b`. Der Zugang läuft über `aifw` bzw. — sobald verfügbar — über das
Gateway aus ADR-294; **kein** eigener Provider-Client in `news-hub`.

Gemessen am 2026-08-29: Der Groq-Schlüssel dieser Umgebung läuft nicht auf dem
Free-Tier (Limits um Größenordnungen darüber). Der Digest kostet also Geld, wenn auch
wenig — die Annahme „kostenlos" gehört nicht in die Planung.

### 4.4 Was den Bestand nie verlässt

Anhänge werden nicht an das LLM gegeben. Übergeben wird der Nachrichtentext der im
Umfang liegenden Newsletter — Werbepost von Absendern, die diese Texte selbst
verbreiten. Für Konten oder Ordner mit anderem Charakter gilt diese Entscheidung nicht;
sie deckt ausschließlich Newsletter-Ordner.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `dev-hub` | 1 — Lesenaht bereitstellen | ⬜ Ausstehend | – | Vertrag §4.1 |
| `news-hub` | 2 — Themenbildung + Recherche | ⬜ Ausstehend | – | gegen synthetische Proben |
| `news-hub` | 3 — Darstellung, klick-only begehbar | ⬜ Ausstehend | – | UX-Gate |
| `news-hub` | 4 — erster echter Lauf | ⬜ Ausstehend | – | erst nach Phase 1 |

---

## 6. Consequences

### 6.1 Good

- Postfach-Zugangsdaten bleiben an einer Stelle
- Eine Löschanfrage bleibt an einer Stelle beantwortbar
- Der Umfang des Digests ist per Konstruktion eine Teilmenge des Mail-Umfangs
- Recherche und LLM-Zugang werden konsumiert, nicht nachgebaut

### 6.2 Bad

- `news-hub` ist bis zur Lesenaht nicht mit echten Daten lauffähig
- Eine zusätzliche Repo-Grenze im Betriebsweg (dev-hub → news-hub)

### 6.3 Nicht in Scope

- Versand des Digests per Mail — bleibt Owner-Entscheidung
- Jede schreibende Postfach-Operation
- Konten oder Ordner außerhalb der benannten Newsletter-Ordner

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Mailtexte an Cloud-LLM weiter als gedacht | Mittel | Hoch | §4.4 begrenzt auf Newsletter-Ordner; Ordnerliste ist Pflichtargument |
| Zweitkopie der Texte schleicht sich ein (Cache, Log) | Mittel | Hoch | Test, der die Persistenz auf Verweise prüft; keine Volltextspalte im Digest-Schema |
| Lesenaht verzögert sich, Druck auf Option C | Mittel | Mittel | Phase 2/3 laufen gegen synthetische Proben weiter |
| Themenbildung nicht deterministisch | Mittel | Niedrig | K1 des Zielzustands: zweiter Lauf muss identisch sein |

---

## 8. Confirmation

1. **Abhängigkeits-Gate in `news-hub`-CI**: Ein Test schlägt fehl, sobald das Repo eine
   Postfach-Bibliothek oder Postfach-Zugangsdaten einführt (Import- und
   Konfigurations-Prüfung). Das ist die maschinelle Form von „kein vierter Zugang".
2. **Beleg-Test**: Ein Test erzeugt einen Digest aus synthetischen Proben und prüft,
   dass jedes ausgegebene Thema mindestens eine Mail-Herkunft und mindestens eine
   externe URL trägt — ein Thema ohne Beleg darf nicht in der Ausgabe erscheinen.
3. **Kein-Zweittext-Test**: Nach einem Lauf enthält die Digest-Datenhaltung keine
   Nachrichtentexte, nur Verweise (`nachricht_ref`).
4. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft —
   Staleness-Schwelle: 6 Monate.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — festgehaltene Architektur-Entscheidung mit Begründung |
| **LLM** | Large Language Model — Sprachmodell, hier für Themenbildung und Zusammenfassung |
| **Crypto-Shredding** | Löschen durch Vernichten des Schlüssels statt der Daten |
| **Lesenaht** | Schmale, nur lesende Schnittstelle zwischen zwei Komponenten |
| **Considered Options** | Abschnitt mit den geprüften Alternativen |
| **Confirmation** | Abschnitt mit den Mechanismen, die die Einhaltung prüfbar machen |

---

## 9. More Information

- ADR-286: Mail-Agent mit Metadaten-Index und zweckgebundener Volltext-Persistenz — Grundlage der Lane
- ADR-293: Vollständige Verfügbarkeit statt Just-in-Time — macht den Bestand überhaupt konsumierbar
- ADR-294: LLM-Gateway statt litellm je Prozess — Zielbild des LLM-Zugangs
- ADR-295: Mailbestand an einem zweiten Standort — betrifft die Verfügbarkeit der Lesenaht
- Zielzustand und Akzeptanzkriterien: `news-hub` Issue #1 (privat)

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-08-29 | Achim Dehnert | Initial: Status Proposed |
