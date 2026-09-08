---
id: ADR-302
status: proposed
decision_date: 2026-09-07
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-068-adaptive-model-routing.md]
related: [ADR-066, ADR-068, ADR-084, ADR-095, ADR-108, ADR-208]
implementation_status: none
last_reviewed: 2026-09-07
staleness_months: 6
---

<!--
  ADR-302 — Basis: docs/templates/adr-template.md v2.1
-->

# ADR-302: Modell-Routing wird entkoppelt, nicht gelernt — Änderung an ADR-068

## Metadaten

| Feld | Wert |
|---|---|
| Status | proposed |
| Ändert | ADR-068 (Adaptive Model Routing and Quality Feedback Loop) |
| Auslöser | Auswertung von HyDRA / HydraFusion, platform#2750 |

## Context and Problem Statement

ADR-068 wurde am 2026-02-23 angenommen und steht seither auf
`implementation_status: partial`. Sein eigenes Frontmatter benennt die beiden
fehlenden Teile:

- „Noch Stub: `_llm_route()` nutzt statische Default-Tabelle statt LLM-Call"
- „Noch fehlend: Feedback-Loop historische Metriken → Routing-Matrix"

Beide sind sechseinhalb Monate offen. Bevor sie gebaut werden, ist die Frage
fällig, ob sie überhaupt der richtige Zielzustand sind.

Im Juni 2026 hat Microsoft mit **HyDRA** (arXiv 2605.17106) ein produktiv
laufendes Routing-System offengelegt, GitHub setzt es als *HydraFusion* in der
Copilot-CLI ein. Es löst dieselbe Aufgabe wie ADR-068 — und trifft an zwei
Stellen die **gegenteilige** Entscheidung. Diese zwei Stellen sind genau
unsere zwei offenen Punkte.

## Decision Drivers

- **D1** — Ein halb gebauter Beschluss soll nicht aus Trägheit fertiggebaut
  werden, wenn die Fachwelt seine Prämisse inzwischen widerlegt hat.
- **D2** — Modellwechsel sind bei uns häufig (Fable 5.1, Opus 5, Sonnet 5
  allein in den letzten Monaten). Was bei jedem Wechsel Arbeit macht, ist
  falsch gebaut.
- **D3** — ADR-068 nennt selbst „~1–2 s Latenz durch Router-LLM-Call" als
  negative Konsequenz. Latenz, die ein Router verursacht, frisst den Gewinn.
- **D4** — Evidenz vor Behauptung: eine geratene Schwierigkeitsklasse ist
  keine Messung.

## Considered Options

### Option A — ADR-068 unverändert fertigbauen

Router-LLM-Call implementieren, Feedback-Loop bauen, Routing-Matrix lernen
lassen.

### Option B — Entkoppeln statt lernen (gewählt)

Drei Änderungen an ADR-068:

1. **Modellprofile raus aus dem Code**, in eine Konfigurationsdatei mit
   Fähigkeitsvektor und Preis je Modell. Die Entscheidungslogik kennt keine
   Modellnamen mehr.
2. **Kein Router-LLM-Call.** Die Zuordnung bleibt eine Tabelle, bekommt aber
   einen **zur Laufzeit stellbaren Regler**, der Qualität gegen Kosten
   verschiebt, ohne dass etwas neu gebaut oder trainiert wird.
3. **Kein lernender Feedback-Loop.** Stattdessen ein **Differenz-Label**:
   die Schwierigkeit einer Aufgabenklasse wird gemessen als der Abstand
   zwischen dem Ergebnis des billigen und dem des starken Modells — nicht
   geschätzt.

### Option C — Routing ganz aufgeben, alles auf das stärkste Modell

## Pros and Cons of the Options

### Option A — unverändert fertigbauen

- Gut: kein neuer Beschluss nötig.
- Schlecht: HyDRA hat den lernenden Loop **bewusst weggelassen** und lief
  damit vier Monate produktiv über sechs Modell-Aufnahmen und drei
  Entfernungen — **ohne ein einziges Nachtrainieren**, weil die Profile in
  einer YAML liegen. Ein Loop, der bei jedem Modellwechsel neu kalibriert
  werden muss, ist bei D2 die teuerste denkbare Bauform.
- Schlecht: der Router-LLM-Call kostet laut ADR-068 selbst 1–2 s. HyDRA
  erreicht 55 ms P50 / 120 ms P99 auf CPU — mit einem 149M-Encoder, ganz
  ohne LLM.

### Option B — entkoppeln (gewählt)

- Gut: Modellwechsel wird zur Konfigurationsänderung.
- Gut: der Regler ersetzt die Lernphase durch eine Stellschraube, die sofort
  wirkt und jederzeit zurückgedreht werden kann.
- Gut: das Differenz-Label ist bei uns **messbar**, ohne neue Erhebung —
  siehe „Datenlage" unten.
- Schlecht: die Fähigkeitsvektoren müssen einmal von Hand gesetzt werden.
- Schlecht: ohne Loop passt sich nichts von allein an; Nachjustieren bleibt
  ein bewusster Zug.

### Option C — alles auf das stärkste Modell

- Gut: einfachste denkbare Lösung, keine Fehlleitung möglich.
- Schlecht: verschenkt den Kostenunterschied vollständig.

## Decision Outcome

**Gewählt: Option B.** ADR-068 bleibt in Kraft; die drei oben genannten Punkte
ersetzen den Router-LLM-Call und den lernenden Feedback-Loop.

### Was aus ADR-068 unverändert bleibt

- Die Tier-Leiter und die Routing-Matrix als Struktur.
- `QualityEvaluator` / `AuditStore` / `CostLog` aus ADR-108.
- Der Audit-Trail je Routing-Entscheidung.

### Was ersetzt wird

| ADR-068 | ADR-302 |
|---|---|
| `_llm_route()` als LLM-Call | Tabelle plus Regler, kein LLM im Entscheidungspfad |
| Feedback-Loop historische Metriken → Matrix | Differenz-Label, offline neu berechnet, bewusst angestoßen |
| Modelle im Code / in ADR-Tabellen | Fähigkeitsvektor und Preis je Modell in Konfiguration |

### Der Regler

Ein einziger Schwellwert entscheidet, wie viel Fähigkeits-Defizit ein Modell
haben darf, bevor eskaliert wird. Klein = teuer und gut, groß = billig und
riskant. HyDRA belegt die Spannweite auf SWE-Bench Verified: von 87,5 %
Qualitätsanteil bei 12,9 % Ersparnis bis 82,4 % bei 72,5 % Ersparnis — eine
Stellschraube, drei Betriebspunkte, kein Neubau.

### Fähigkeitsvektor statt Skalar

Eine Aufgabe kann wenig Schlussfolgern und viel Werkzeuggebrauch verlangen.
Eine skalare Tier-Leiter kann das nicht ausdrücken und provisioniert zu hoch.
Deshalb: Bedarf **je Dimension**, und ein Überschuss in einer Dimension darf
ein Defizit in einer anderen **nicht** ausgleichen.

## Datenlage — warum das Differenz-Label bei uns messbar ist

Drei Quellen tragen dieselbe Sitzungskennung:

| Quelle | Inhalt |
|---|---|
| `llm_calls` (Orchestrator-DB) | echte `cost_usd` je Zug, Sitzung als `task_id = cc-<session_id>` |
| `~/.claude/hooks/state/modellmix-ledger.tsv` | Delegationsanteil je Sitzung, 59 Zeilen ab 2026-09-03 |
| `docs/retros/*.md` | sechs Qualitätsdimensionen je Sitzung, 114 Dateien mit `session_id` |

Zusammengeführt ergibt das eine **realisierte** Kosten-Qualitäts-Tabelle.
HyDRA rechnet Kosten aus einer festen Preisliste, nicht aus echten
Tokenzahlen — wir können an dieser Stelle genauer sein als die Vorlage.

## Bekannte Grenzen der Vorlage

Ehrlich mitgenommen, damit sie nicht als gelöst gelten:

- Der LLM-Punktrichter von HyDRA erreicht gegen Menschen nur Krippendorff
  α = 0,24; das System selbst 0,40. Die Dimension Werkzeuggebrauch liegt bei
  α = −0,04, also auf Zufallsniveau. **Ein Punktrichter ist kein Maßstab,
  bevor seine Übereinstimmung gemessen ist** (platform#2737).
- Routing lässt sich durch präparierte Eingaben in Richtung billiges Modell
  drängen; Abwehr ist dort offene Arbeit. Für uns gilt unverändert:
  fremde Inhalte sind Daten, nie Befehle.
- GitHubs stärkste Zahl stammt aus dem eigenen, nicht nachspielbaren
  Benchmark. Derselbe Konstruktionsfehler droht unserer eigenen Rubrik.

## Positive Consequences

- Ein Modellwechsel ist eine Konfigurationszeile.
- Kein LLM im Entscheidungspfad, also keine Router-Latenz.
- Die Schwierigkeitsklassen werden belegbar statt geraten.

## Negative Consequences

- Fähigkeitsvektoren müssen einmal gesetzt und gelegentlich nachgezogen werden.
- Ohne Loop bleibt Nachjustieren ein bewusster Zug, kein Automatismus.
- Das Differenz-Label braucht eine Auswertung, die es noch nicht gibt.

## Umsetzungsschritte

1. Kosten-Qualitäts-Auswertung über die drei Quellen (platform#2750).
2. Nachbesserungsquote als Untergrenze aus den Sitzungsmitschriften ableiten.
3. Fähigkeitsvektoren und Preise in eine Konfigurationsdatei ziehen,
   anschlussfähig an den Auflöser aus ADR-208.
4. Regler einführen, drei Betriebspunkte dokumentieren.
5. `_llm_route()`-Stub aus ADR-068 ersatzlos streichen.

## Kill-Gate

Wenn bis **2026-12-31** kein Betriebspunkt gemessen und kein Fähigkeitsvektor
gesetzt ist, wird ADR-302 zurückgezogen und ADR-068 auf `rejected` gesetzt —
ein zweites halb gebautes Routing braucht niemand.

## Quellen

- HyDRA: Hybrid Dynamic Routing Architecture for Heterogeneous LLM Pools,
  arXiv 2605.17106
- GitHub Copilot CLI, Research Preview HydraFusion,
  community/discussions/206492
- Auswertung mit Belegen: platform#2750
