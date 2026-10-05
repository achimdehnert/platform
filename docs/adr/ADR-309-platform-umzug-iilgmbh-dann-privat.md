---
id: ADR-309
status: proposed
decision_date: 2026-10-05
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-255, ADR-263]
implementation_status: in_progress
last_reviewed: 2026-10-05
staleness_months: 3
---

<!--
  ADR-309 — Basis: docs/templates/adr-template.md v2.1
  Nummer vergibt tools/adr_allocate.py kurz vor dem Merge (ADR-228).
-->

# ADR-309: platform zieht in die Org iilgmbh und wird erst dort privat

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed — Zielzustand vom Owner am 2026-10-04 angenommen            |
| **Scope**       | platform (Repo-Ort und Sichtbarkeit)                                 |
| **Erstellt**    | 2026-10-05                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-255 (Org-Migration iilgmbh, nimmt platform ausdrücklich aus), ADR-263 (Flotten-Workflows), KONZ-platform-039, #3234 |

## Repo-Zugehörigkeit

| Repo             | Rolle      | Betroffene Pfade / Komponenten                                  |
|------------------|------------|-----------------------------------------------------------------|
| `platform`       | Primär     | Repo-Ort, Sichtbarkeit, `tools/sichtbarkeits_drift_melder.py`   |
| `iilgmbh/shared-ci` | Sekundär | Kanon der wiederverwendbaren Workflows nach dem Schnitt         |
| Konsumenten-Repos | Betroffen | `uses:`-, Raw- und Klon-Verweise auf platform                   |

---

## Decision Drivers

- **platform ist öffentlich**, und jeder Commit ist eine Veröffentlichung (CLAUDE.md, Beinahe-Vorfall #1670).
- **Der Schutz darf beim Privatschalten nicht sinken.** Secret-Scanning und Push-Schutz sind heute an.
- **Keine laufenden Zusatzkosten** durch das Privatschalten.
- **Kein Bruch in fremder CI.** Die Konsumenten werden vorher umgehängt, nicht danach repariert.
- **Wiedereinstieg ohne Vorwissen:** Eine spätere Sitzung soll den Stand aus einem Befehl ablesen können, nicht aus Dokumenten.

## 1. Context and Problem Statement

KONZ-platform-039 hat entschieden, dass platform nicht öffentlich bleiben soll. Die Umsetzung
(#3234) hängt Konsumenten auf `iilgmbh/shared-ci` um; ein Melder zählt, was noch an platform
hängt. Offen blieb, **wohin** das Privatschalten führt. Bisher war ein Schalter im Privatkonto
gemeint („Flip“).

Die Prüfung vom 2026-10-04 zeigt zwei Folgen dieses Flips, die nichts brechen und deshalb erst
spät auffielen:

1. **Secret-Schutz fällt weg.** Secret-Scanning und Push-Schutz gibt es für private Repos eines
   Privatkontos nicht (GitHub-Doku „About secret scanning“). Bei platform sind beide heute aktiv,
   weil das Repo öffentlich ist. Nach dem Flip wäre das Repo mit den meisten Konfigurationsdateien
   der Flotte das einzige ohne diesen Schutz.
2. **Actions-Minuten werden abgerechnet.** Öffentliche Repos verbrauchen kein Kontingent. platform
   verbraucht im Monat ein Vielfaches des Freikontingents eines Privatkontos, mit steigender
   Tendenz. Ein Vergleichsfall aus Welle 1 der Org-Migration kostet seit seinem Flip monatlich.
   Die Beträge stehen intern, nicht hier.

Die Org `iilgmbh` hat beides: Secret-Schutz ist für private Repos automatisch aktiv, und das
Org-Kontingent deckt die bisherige Org-Last ohne Nettokosten.

## 2. Considered Options

| Option | Kern | Schutz | Kosten | Bruch |
|---|---|---|---|---|
| **A** Öffentlich lassen | nur Bereinigung + Routine | bleibt | 0 | keiner |
| **B1** Flip im Privatkonto | Schalter in `achimdehnert` | **fällt weg** | **laufend** | wie B2 |
| **B2** Umzug nach `iilgmbh`, dann privat | Transfer, danach Schalter | bleibt | 0 erwartet (H1) | wie B1 |
| **C** Neues privates Repo, altes archivieren | frische Historie | bleibt (in Org) | 0 erwartet | alle Verweise, Historie bleibt trotzdem öffentlich |

**A** verwirft KONZ-039 bereits. **C** bricht mehr als B2 und schützt die alte Historie trotzdem
nicht. **B1** verschlechtert Schutz und Kosten. Es bleibt **B2**.

## 3. Decision Outcome

**Gewählt: B2.** platform wird nach `iilgmbh/platform` übertragen und erst dort privat geschaltet.
Öffentlich bleibt nur `iilgmbh/shared-ci`.

### Reihenfolge (verbindlich)

1. **Konsumenten auf null.** Der Melder steht bei 0 / 0 / 1 / 0 (Aufrufer / Raw / Kopien / Fristen),
   und zwar sieben Kalendertage lang (K5).
2. **Bestand aufnehmen.** Repo-Runner, Webhooks, Rulesets, Environments und Deploy-Keys
   auflisten.
3. **Transfer** nach `iilgmbh`. Nicht während eines Deploys.
4. **Abgleich.** Den Bestand aus Schritt 2 mit dem neuen Ort vergleichen.
5. **Privat schalten.** Danach einmal echt prüfen: Prod-Klon per Deploy-Key, ein Konsument mit
   eigenem Token, Secret-Schutz an.

Schritt 1 steht vor dem Transfer, nicht danach. Die Probe G2 zeigt, warum: Ein Transfer allein
bricht verbliebene Reusable-Workflow-Aufrufer schon, solange das Repo noch öffentlich ist.

### Probe G2 (2026-10-05, Wegwerf-Repo, Transfer Privatkonto → iilgmbh)

| Pfad über den alten Namen | nach Transfer, öffentlich | nach Privatschalten |
|---|---|---|
| Reusable Workflow (`uses: …/.github/workflows/…`) | **bricht** („workflow was not found“, zweimal) | bricht |
| Composite Action (`uses: …/.github/actions/…`) | trägt (Weiterleitung) | — |
| Raw-Download anonym | trägt | 404 |
| Klon anonym | trägt | scheitert |
| Klon mit Benutzer-Token | trägt | trägt |
| Deploy-Key (SSH) | trägt | nach rund einer Minute „disabled“ wieder tragfähig |
| Secrets, Environment-Secrets, Environments, Deploy-Key | ziehen mit um | — |
| Secret-Scanning und Push-Schutz | in der Org automatisch an | bleiben an |

## 4. Consequences

**Positiv**

- Der Schutz bleibt beim Privatschalten erhalten.
- Es entstehen keine Zusatzkosten, solange H1 hält.
- Neue Infrastruktur-Angaben werden nicht mehr veröffentlicht.

**Negativ / bewusst hingenommen**

- **Die öffentliche Historie bleibt abrufbar.** Das gilt für Klone, Archive und einen bestehenden
  fremden Fork. Das Privatschalten wirkt nur nach vorn. Was dort steht, ist als veröffentlicht zu
  behandeln.
- **Die Einstiegshürde steigt.** `bootstrap.sh` (Public Interface) braucht danach einen Token. Ein
  dokumentierter Fallback muss vor Schritt 5 stehen.
- **Kurze Sperre der Deploy-Keys** nach dem Privatschalten, darum nicht während eines Deploys.

### Hypothesen (vor Schritt 3 prüfen)

| id | Hypothese | Prüfung | Owner |
|---|---|---|---|
| H1 | Das Org-Kontingent deckt die Actions-Minuten von platform | Org-Billing, Kontingent gegen Monatslast | **Geprüft 2026-10-05, gilt heute mit Reserve.** Enterprise-Kontingent laut GitHub-Doku: 50 000 Linux-Minuten pro Monat. Lastsumme im September (Org plus platform): etwa drei Viertel davon, netto 0. Risiko: Die Last von platform hat sich von August auf September mehr als verdoppelt. Eine weitere Verdopplung sprengt das Kontingent. Die Wache des Melders meldet netto > 0 (KG2). |
| H2 | Repo-Runner, Webhooks und Rulesets ziehen mit um | Schritt 2 gegen Schritt 4 | Sitzung |

## 5. Stand und Wiedereinstieg

Den Stand führt kein Dokument, sondern der Melder:

```
python3 tools/sichtbarkeits_drift_melder.py --kurz          # Stand, Prognose, K5-Serie
python3 tools/sichtbarkeits_drift_melder.py --json          # dazu naechster_zug je Restposten
python3 tools/sichtbarkeits_drift_melder.py --kurz --oeffentlich   # für Texte in diesem Repo
```

Der Sitzungsstart ruft ihn täglich auf und schreibt eine hostlokale Messreihe. Daraus ergeben
sich das prognostizierte Null-Datum, die K5-Serie und Rückfälle. Die Wache des Melders meldet
fehlenden Secret-Schutz und bezahlte Minuten, vor und nach dem Umzug.

## 6. Kill-Gate

| id | Kriterium | Schwelle | Folge |
|---|---|---|---|
| KG1 | Secret-Schutz nach dem Privatschalten | ein Merkmal nicht `enabled` | sofort öffentlich zurück, Ursache klären |
| KG2 | Actions-Kosten von platform netto | > 0 in einem Monat | Kontingent oder Runner klären; ohne Lösung in 30 Tagen zurück |
| KG3 | CI-Bruch in einem Konsumenten nach Schritt 3 oder 5 | > 24 h | Schritt zurückdrehen (Transfer und Sichtbarkeit sind umkehrbar) |

**Sunset:** Dieses ADR geht auf `implemented`, wenn platform in `iilgmbh` privat ist und der
Melder 30 Tage nichts meldet.

## 7. Offene Owner-Gates

- ~~**H1 prüfen:** das Org-Kontingent im Billing ablesen.~~ Erledigt 2026-10-05, siehe Hypothesen-Tabelle.
- **Schritt 3 und 5 auslösen:** Transfer und Sichtbarkeitsschalter sind Owner-Sache
  (Security-Config-Gate).
