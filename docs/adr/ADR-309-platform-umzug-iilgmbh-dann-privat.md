---
id: ADR-309
status: proposed
decision_date: 2026-10-05
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-255]
related: [ADR-255, ADR-263]
implementation_status: in_progress
last_reviewed: 2026-10-05
staleness_months: 3
---

<!--
  ADR-309 — Basis: docs/templates/adr-template.md v2.1
-->

# ADR-309: platform zieht in die Org iilgmbh und wird erst dort privat

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed — Zielzustand vom Owner am 2026-10-04 angenommen            |
| **Scope**       | platform (Repo-Ort und Sichtbarkeit)                                 |
| **Erstellt**    | 2026-10-05                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | Gegenprüfung 2026-10-05: frischer Agent, nur lesend (Retro 8a0235 R7); Befunde eingearbeitet |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Amends**      | ADR-255: dessen Ausnahme für platform entfällt, platform zieht doch nach `iilgmbh` |
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
| **B3** Neues privates Repo, altes archivieren | frische Historie | bleibt (in Org) | 0 erwartet | alle Verweise, Historie bleibt trotzdem öffentlich |

Die Buchstaben sind nicht die Varianten aus KONZ-039. Dort heißt „C“ Schnitt **und** Bereinigung;
das ist B2 zusammen mit Schritt 1b.

**A** verwirft KONZ-039 bereits. **B3** bricht mehr als B2 und schützt die alte Historie trotzdem
nicht. **B1** verschlechtert Schutz und Kosten. Es bleibt **B2**.

Eine Verlagerung GitHub-gehosteter Jobs auf Self-hosted-Runner ist keine eigene Option, sondern
die Antwort auf KG2. Sie senkt die Last unter B1 und B2 gleichermaßen, ändert aber nichts am
Secret-Schutz.

## 3. Decision Outcome

**Gewählt: B2.** platform wird nach `iilgmbh/platform` übertragen und erst dort privat geschaltet.
Öffentlich bleibt nur `iilgmbh/shared-ci`.

### Reihenfolge (verbindlich)

1. **Konsumenten auf null.** Der Melder steht bei 0 / 0 / 1 / 0 (Aufrufer / Raw / Kopien / Fristen),
   und zwar sieben Kalendertage lang (K5).
   - **1b Bereinigung.** Die Mandantendaten-Fundstellen aus #1836 sind entfernt, belegt mit einer
     Kontrollprobe (roh N → 0, #3234 AK 8). Das Privatschalten wirkt nur nach vorn; was bis
     dahin öffentlich steht, bleibt es.
   - **1c Bootstrap.** `bootstrap.sh` klont authentifiziert und ist einmal auf frischer Umgebung
     gelaufen (#3234 AK 7). Ohne das sperrt Schritt 5 neue Umgebungen aus.
2. **Bestand aufnehmen.** Repo-Runner, Webhooks, Rulesets, Environments und Deploy-Keys
   auflisten. Dazu alles, was an Owner **und** Repo-Namen gebunden ist und den Transfer
   deshalb nicht übersteht:
   - **OIDC Trusted Publishing** auf PyPI. platform veröffentlicht selbst
     (`publish-iil-codeguard.yml`, `publish-iil-ingest.yml`). Der Publisher ist auf
     `achimdehnert/platform` eingetragen und muss für `iilgmbh/platform` neu angelegt werden.
   - **GitHub-App-Installationen** am Benutzerkonto, die platform einschließen.
   - **Fine-grained PATs** mit Resource-Owner `achimdehnert`. Sie verlieren den Zugriff nach dem
     Transfer, auch wenn sie bisher als „trägt“ galten (H4).
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
| Deploy-Key (SSH) | trägt | rund eine Minute „disabled“, danach trägt er wieder |
| Secrets, Environment-Secrets, Environments, Deploy-Key | ziehen mit um | — |
| Secret-Scanning und Push-Schutz | in der Org automatisch an | bleiben an |

## 4. Consequences

**Positiv**

- Der Schutz bleibt beim Privatschalten erhalten.
- Es entstehen keine Zusatzkosten, solange H1 und H3 halten.
- Neue Infrastruktur-Angaben werden nicht mehr veröffentlicht.

**Negativ / bewusst hingenommen**

- **Die öffentliche Historie bleibt abrufbar.** Das gilt für Klone, Archive und einen bestehenden
  fremden Fork. Das Privatschalten wirkt nur nach vorn. Was dort steht, ist als veröffentlicht zu
  behandeln.
- **Die Einstiegshürde steigt.** `bootstrap.sh` (Public Interface) braucht danach einen Token.
  Schritt 1c regelt das vor dem Privatschalten.
- **Kurze Sperre der Deploy-Keys** nach dem Privatschalten, darum nicht während eines Deploys.
- **Nur bedingt umkehrbar.** Der Transfer lässt sich zurückdrehen, die Sichtbarkeit nur in
  Richtung privat: Zurück auf öffentlich veröffentlicht alles, was seit Schritt 5 committet wurde.
  Den bestehenden öffentlichen Fork spaltet GitHub beim Privatschalten ab, er bleibt öffentlich.
  Sterne und Watcher gehen laut Hinweis der Oberfläche verloren (nicht gegengeprüft).

### Hypothesen (vor Schritt 3 prüfen)

| id | Hypothese | Prüfung | Stand | Owner |
|---|---|---|---|---|
| H1 | Das Org-Kontingent deckt die Actions-Minuten von platform | Org-Billing, Kontingent gegen Monatslast; Beleg: `python3 tools/sichtbarkeits_drift_melder.py`, Abschnitt Wache | **Geprüft 2026-10-05, gilt heute mit Reserve.** Enterprise-Kontingent laut GitHub-Doku: 50 000 Linux-Minuten pro Monat. Lastsumme im September (Org plus platform): etwa drei Viertel davon, netto 0. Risiko: Die Last von platform hat sich von August auf September mehr als verdoppelt. Eine weitere Verdopplung sprengt das Kontingent. Die Wache des Melders meldet netto > 0 (KG2). Vorher warnt sie, wenn die Hochrechnung des Monats (Org plus platform) mehr als 80 % des Kontingents belegt. Sie schlägt seit dem 2026-10-05 an (#3786). Ob das Org-Abo eine Testphase mit Ablaufdatum ist, ist ungeprüft. | Achim Dehnert |
| H2 | Repo-Runner, Webhooks und Rulesets ziehen mit um; OIDC-Publisher und App-Installationen sind am neuen Ort neu angelegt | Schritt 2 gegen Schritt 4 | offen | Achim Dehnert |
| H3 | Das Privatschalten bringt keine zusätzlichen Kosten für den Secret-Schutz | Abrechnung je aktivem Committer: Committer von platform gegen die schon gezählten der Org | offen, KG2 misst das noch nicht (#3787) | Achim Dehnert |
| H4 | Konsumenten-Checkouts mit eigenem Token tragen nach dem Transfer | Token-Typ je Checkout; fine-grained PATs mit Resource-Owner `achimdehnert` brechen | offen, Hypothese der Gegenprüfung; der Melder zählt diese Checkouts bisher nicht (#3787) | Achim Dehnert |

## 5. Stand und Wiedereinstieg

Den Stand führt kein Dokument, sondern der Melder:

```
python3 tools/sichtbarkeits_drift_melder.py --kurz          # Stand, Prognose, K5-Serie
python3 tools/sichtbarkeits_drift_melder.py --json          # dazu naechster_zug je Restposten
python3 tools/sichtbarkeits_drift_melder.py --kurz --oeffentlich   # für Texte in diesem Repo
```

Ein Tages-Timer auf dem Sitzungs-Host ruft ihn auf (`infra/host-maintenance/sichtbarkeits-melder.timer`),
der Sitzungsstart zusätzlich. Beide schreiben dieselbe hostlokale Messreihe. Daraus ergeben
sich das prognostizierte Null-Datum, die K5-Serie und Rückfälle. Die Wache des Melders meldet
fehlenden Secret-Schutz, bezahlte Minuten und eine Hochrechnung über 80 % des Org-Kontingents,
vor und nach dem Umzug.

## 6. Kill-Gate

Kein Kill-Gate führt zurück in die Öffentlichkeit. Das wäre selbst eine Veröffentlichung, und zwar
von allem, was in der privaten Phase entstanden ist.

| id | Kriterium | Schwelle | Folge | Owner |
|---|---|---|---|---|
| KG1 | Secret-Schutz nach dem Privatschalten | ein Merkmal nicht `enabled` | Schutz über die Code-Security-Konfiguration der Org erzwingen, Ursache klären; bis dahin keine Commits mit Konfigurationsdateien | Achim Dehnert |
| KG2 | Nettokosten der Org `iilgmbh`, alle Produkte | > 0 in einem Monat | teure Workflows auf Self-hosted-Runner ziehen oder das Kontingent klären, binnen 30 Tagen. Die Messung deckt heute nur Actions von platform ab (#3787) | Achim Dehnert |
| KG3 | CI-Bruch in einem Konsumenten nach Schritt 3 oder 5 | > 24 h | Konsumenten reparieren oder den Transfer zurückdrehen; die Sichtbarkeit bleibt privat | Achim Dehnert |

**Sunset:** Dieses ADR geht auf `implemented`, wenn platform in `iilgmbh` privat ist und der
Melder 30 Tage nichts meldet.

## 7. Offene Owner-Gates

- ~~**H1 prüfen:** das Org-Kontingent im Billing ablesen.~~ Erledigt 2026-10-05, siehe Hypothesen-Tabelle.
- **Schritt 3 und 5 auslösen:** Transfer und Sichtbarkeitsschalter sind Owner-Sache
  (Security-Config-Gate).
- **PyPI-Publisher** für `iilgmbh/platform` im PyPI-Konto anlegen (Schritt 2, H2).
- **Frist von KONZ-039 (`review_by` 2026-10-31)** verlängern oder das Konzept auf dieses ADR
  verweisen lassen. Läuft sie ab, zählt der Melder eine abgelaufene Frist, und K5 kann nicht
  greifen. Ohne Entscheidung fällt KONZ-039 laut eigenem Text auf Variante A zurück.
- **#3234 angleichen:** Der Issue-Text nennt noch den Flip im Privatkonto, eine „Rückdrehung“ in
  AK 6 und Transfers als Out of Scope. Maßgeblich ist dieses ADR.
