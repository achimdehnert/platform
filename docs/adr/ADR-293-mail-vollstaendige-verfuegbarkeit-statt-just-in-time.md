---
status: proposed
decision_date: 2026-08-03
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-286]
related: [ADR-288, ADR-284, ADR-283]
implementation_status: partial
last_reviewed: 2026-08-03
staleness_months: 6
tags: [mail, datenhaltung, dsgvo, recherche, verfuegbarkeit]
---

# ADR-293: Mail — vollständige Verfügbarkeit statt Just-in-Time; Option D fällt

> **Nummern-Hinweis:** 293 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Metadaten

| Attribut | Wert |
|----------|------|
| **Status** | Proposed |
| **Scope** | platform (Mail-Agent: dev-hub `apps/mail_agent`, platform `tools/mail_agent`) |
| **Erstellt** | 2026-08-03 |
| **Autor** | Achim Dehnert |
| **Amends** | [ADR-286](ADR-286-mail-agent-crypto-shredding-derived-index.md) — ersetzt dessen §3 Decision Outcome |
| **Supersedes** | – |

## Repo-Zugehörigkeit

Entscheidung liegt in `platform`, Umsetzung in **zwei** Repos: `dev-hub`
(`apps/mail_agent`, Modelle und Kommandos) und `platform`
(`tools/mail_agent`, IMAP-/Graph-Transport und Ausschlussregel).

---

## Decision Drivers

- **Owner-Maxime (2026-08-03, wörtlich):** „für mail gilt ADR-286 (D) nicht → wir
  verwenden ALLES was für die Anwendung notwendig ist. MAXIME: Optimale Mailrecherche
  und Verfügbarkeit."
- Der Ist-Zustand liefert diese Maxime nachweislich nicht: **4 Volltexte bei 15.123
  indexierten Nachrichten**, **0 Zeilen** Anhangs-Inventar.
- Die Kostenannahme, die Option D mit trug, ist gemessen worden und trägt nicht mehr
  (§2).
- Löschbarkeit muss weiterhin beantwortbar bleiben — sie darf nur nicht mehr *durch
  Nicht-Speicherung* erkauft werden.

---

## 1. Context and Problem Statement

ADR-286 entschied am 2026-07-24 **Option D**: Postgres hält standardmäßig nur
minimierte Metadaten; Bodies und Anhänge werden bei Bedarf live aus dem Postfach
geholt, dauerhaft gespeichert wird nur, was ein **aktiver Vorgang** ausdrücklich
rechtfertigt. Beide externen Reviews hatten D unabhängig vorgeschlagen, und der
tragende Grund war ausdrücklich benannt: Art. 17 ist „per Konstruktion" erfüllt, wenn
es keinen Body-Store gibt.

Diese Konstruktion hat den Zweck erfüllt, für den sie gebaut wurde, und genau dabei
ihren Preis gezeigt. Das Tor sitzt in `mail_volltext` und ist bewusst hart
formuliert — „ohne Umgehungsschalter, ein `--trotzdem`-Flag wäre die Erlaubnis,
ADR-286 im Alltag zu unterlaufen". Es wirkt wie beabsichtigt: **ohne** einen
angelegten, offenen Vorgang gibt es keinen Volltext. In der Praxis heißt das, dass
eine Recherche erst dann etwas findet, wenn jemand vorher wusste, wonach zu suchen
ist und dafür einen Vorgang angelegt hat. Für eine Suche über einen gewachsenen
Bestand ist das die falsche Reihenfolge: **man legt keinen Vorgang an, um
herauszufinden, ob es einen gibt.**

### 1.1 Ist-Zustand, gemessen

| Messung | Wert | Quelle |
|---|---|---|
| Indexierte Nachrichten (3 Konten) | 15.123 | Prod-DB, 2026-08-03 |
| davon mit persistiertem Volltext | **4** | `PersistedBody` |
| Zeilen im Anhangs-Inventar | **0** | `mail_agent_attachment` |
| IMAP-Kopien mit Anhangs-Flag | **0 von 7.158** | dev-hub#210 |

Die letzte Zeile war ein eigenständiger Defekt (der Ingest forderte die
Nachrichtenstruktur nicht an), behoben in dev-hub#215. Sie gehört hierher, weil sie
zeigt, wie wenig auffällt, wenn ohnehin niemand an die Inhalte kommt: **ein Bestand,
den man nicht durchsuchen kann, verbirgt auch seine eigenen Lücken.**

### 1.2 Warum jetzt

Der Mail-Agent ist seit dem 2026-08-02 mit allen drei Postfächern verbunden und
liefert Vorgangsketten in unter 120 ms aus der Datenbank. Die Metadaten-Schicht steht
also. Was fehlt, ist genau die Schicht, die ADR-286 bewusst nicht gebaut hat — und
ohne sie beantwortet das System Fragen nach dem *Inhalt* nicht: Rechnung, Anmeldung,
Bescheid, Formular. Bei Behörden- und Rechnungsverkehr steckt der fachliche Kern
regelmäßig im **Anhang**, nicht im Nachrichtentext.

---

## 2. Die Kostenannahme, neu gemessen

Option D wurde auch mit Volumen begründet. Diese Annahme ist am 2026-08-03 am echten
Postfach nachgemessen worden — per `RFC822.SIZE`, einer Serverangabe, ohne einen
einzigen Body zu übertragen:

| Konto hnu | Nachrichten | Roh |
|---|---|---|
| Postfach gesamt | 26.442 | 8,7 GB |
| **im Umfang** (nach `indexierung.py`) | **3.585** | **1,5 GB** |
| ausgeschlossen | 22.857 | 7,2 GB |

**Der Unterschied liegt vollständig in der Ausschlussregel**, die der Owner am
2026-07-28 freigegeben hat: Jahresarchive bis einschließlich 2024, Papierkorb/Junk,
Kalender/Kontakte/Aufgaben, Newsletter. Die zehn größten Ordner des Postfachs sind
ausnahmslos solche — der relevante Bestand ist ein Sechstel des Postfachs und ein
Sechstel seines Volumens.

Hochgerechnet auf alle drei Konten liegt der relevante Rohbestand in der
Größenordnung **5–6 GB**; freier Plattenplatz auf dem Prod-Host: **53 GB von 150 GB**.
Damit ist die Vollspeicherung des relevanten Umfangs keine Grenzfrage mehr. Sie war
es 2026-07-24 auch nicht — sie war nur nicht gemessen.

**Diese Zahl ist der eigentliche Grund, warum die Entscheidung heute anders ausfällt
als vor zehn Tagen.** Nicht ein geänderter Geschmack, sondern eine Größenordnung, die
niemand erhoben hatte: die Ausschlussregel, die zwischenzeitlich entstand, hat das
Problem, das Option D lösen sollte, bereits zu fünf Sechsteln erledigt.

**Nicht gemessen:** `mittwald` (Konfiguration liegt nur auf dem Prod-Host) und `iil`
(Graph kennt kein `RFC822.SIZE`). Beide werden beim ersten Volllauf mitgemessen,
**bevor** geschrieben wird. Die Hochrechnung oben ist eine Hochrechnung und wird hier
nicht als Messwert geführt.

---

## 3. Decision Outcome

**Für die Mail-Lane gilt Option D nicht mehr.** An ihre Stelle tritt die in ADR-286 §2
als **Option A** beschriebene Variante: **Nachrichtentext und Anhänge werden für den
gesamten Umfang dauerhaft persistiert** — verschlüsselt, einzeln schredderbar.

Konkret ersetzt dieser Beschluss §3 von ADR-286. Was daraus folgt:

1. **Das Vorgangs-Tor in `mail_volltext` entfällt.** Ein Volltext-Lauf braucht keinen
   aktiven Vorgang mehr; er läuft über den Umfang eines Kontos.
2. **Der Umfang bleibt die Grenze.** Was `indexierung.py` ausschließt, wird auch nicht
   im Volltext geholt. Die Ausschlussregel ist damit nicht länger nur eine
   Indexier-, sondern die **Speicher**grenze — und sie ist der Grund, warum diese
   Entscheidung verhältnismäßig bleibt.
3. **Verschlüsselung und Crypto-Shredding bleiben** — nicht als Tor, sondern als
   Fähigkeit. Sie kosten hier nichts (der Pfad ist gebaut) und sind das, was eine
   Löschanfrage weiterhin beantwortbar macht.
4. **Anhänge bekommen ein Inventar** (Name, Typ, Größe, Teilnummer) und sind über die
   Rohnachricht abrufbar. Ein separater Objektspeicher wird **nicht** eingeführt: die
   Bytes stecken in der persistierten Rohnachricht, `blob_ref` bleibt unbenutzt frei.

### 3.1 Was von ADR-286 unverändert in Kraft bleibt

Ausdrücklich, damit dieser Beschluss nicht mehr abräumt als er soll:

| Abschnitt | Inhalt | Status |
|---|---|---|
| §4.1 | Identitätsmodell, kein `UNIQUE(internet_message_id)` | **gilt** |
| §4.2 | Metadaten sind Personendaten | **gilt** |
| §4.3 | Erasure-Ledger, monoton und restore-fest | **gilt** |
| §4.4 | Löschumfang-Matrix (Art. 17) | **gilt**, erweitert um Body + Anhang |
| §4.5 | Envelope-Encryption, zufälliger DEK | **gilt als Fähigkeit**, nicht mehr als Tor |
| §4.6 | Konsistenz, Delta-Sync, ehrliche Deckungsgrenzen | **gilt** |
| §4.8–§4.11 | Sachverhalts-Ebenen, Vorgangs-Graph, Auswertung, Beteiligung | **gilt** |

### 3.2 Was fällt

| Abschnitt | Bisher | Jetzt |
|---|---|---|
| §3 | „Gewählte Option: D" | Option A für den Umfang |
| §4.5 | Persistenz **nur** im aktiven Vorgang | Persistenz für den Umfang |
| §4.10.7 | „Extraktion beim Einlesen oder nie, weil Bodies nicht persistiert sind" | Prämisse entfällt — Bodies sind persistiert, Ableitung ist wiederholbar |

§4.10.7 ist die feinste, aber folgenreichste Änderung: die Regel „beim Einlesen oder
nie" war eine **Folge** der Nicht-Speicherung, kein Selbstzweck. Mit persistierter
Rohnachricht wird ein Parserwechsel zu einer lokalen Neuableitung, statt zu einem
erneuten Postfach-Durchlauf. Das war unter D technisch nicht möglich.

---

## 4. Consequences

### 4.1 Good

- Recherche über Text **und** Anhang wird ohne Vorbedingung möglich — die Maxime ist
  erfüllbar statt nur formuliert.
- Ein Parserwechsel kostet keine Postfach-Last mehr (siehe §3.2).
- Die Anhangs-Ebene, in der bei Behörden- und Rechnungsverkehr die Substanz liegt,
  wird überhaupt erst erreichbar.

### 4.2 Bad — ehrlich benannt

- **Art. 17 ist nicht mehr „per Konstruktion" erfüllt.** Er wird zu einer *Operation*:
  Crypto-Shredding je Nachricht. Das ist ein realer Rückschritt gegenüber ADR-286 und
  der Kern dessen, was hier eingetauscht wird. Die Fähigkeit existiert und ist
  getestet — aber sie muss künftig **ausgeführt** werden, statt gegenstandslos zu sein.
- Backups enthalten ab jetzt Mailinhalt. Wer ein Backup hält, hält Personendaten.
- Der Schlüssel-Lebenszyklus wird größer und wichtiger: ein verlorener Schlüssel macht
  den Bestand unlesbar, ein kopierter macht ihn lesbar.
- Die Postfächer enthalten **echte** Personendaten (Studierende, Mandanten,
  MEiKI-Kommunikation). Der Umfang dieser Entscheidung ist deshalb kein Testbestand.

### 4.3 Nicht in Scope

- Kein Objektspeicher, kein CDN, keine Auslagerung (§3.4).
- Keine Ausweitung des Umfangs: ausgeschlossene Ordner bleiben ausgeschlossen. Wer den
  Umfang ändern will, ändert `indexierung.py` — und das ist eine eigene Entscheidung.

---

## 5. Risks

| Risiko | Wahrscheinlichkeit | Wirkung | Gegenmaßnahme |
|---|---|---|---|
| Löschanfrage trifft auf nicht ausgeführtes Shredding | Mittel | Hoch | §6 Gate 3: Shredding-Pfad am echten Bestand belegt, nicht nur getestet |
| Volumen läuft aus dem Ruder (Anhänge wachsen) | Mittel | Mittel | §6 Gate 2: Messung **vor** dem Schreiben, je Konto |
| Backup enthält Klartext, weil Verschlüsselung übersprungen wird | Niedrig | Hoch | Persistenz läuft ausschließlich über `persist_body`; ein Schreibpfad daran vorbei ist ein Testfehler |
| Ausschlussregel wird stillschweigend aufgeweicht | Mittel | Hoch | Die Regel ist die Speichergrenze — Änderungen brauchen einen eigenen Beschluss |

---

## 6. Confirmation

Der Beschluss gilt als umgesetzt, wenn **alle** vier Punkte belegt sind:

1. **Gate 1 — Tor entfernt und ersetzt.** `mail_volltext` läuft ohne Vorgang über den
   Umfang eines Kontos; der Code verweist auf **diesen** ADR, nicht mehr auf
   ADR-286 §4.5. Beleg: Testlauf + Codestelle.
2. **Gate 2 — Volumen gemessen, bevor geschrieben wird.** Für `mittwald` und `iil`
   liegt eine echte Messung vor, keine Hochrechnung. Beleg: Zahlen im PR.
3. **Gate 3 — Löschung belegt.** Für eine reale Nachricht wird Crypto-Shredding
   ausgeführt und danach nachgewiesen, dass Body **und** Anhangstext nicht mehr
   lesbar sind. Ein bestandener Test allein genügt hier nicht.
4. **Gate 4 — Deckung ehrlich.** Der Deckungsausweis unterscheidet „kein Volltext
   vorhanden" von „Volltext nicht abrufbar" (§4.6 ADR-286 gilt weiter). Ein Lauf mit
   Teilfehlern meldet `partial`, nicht `complete`.

---

## 7. More Information

- [ADR-286](ADR-286-mail-agent-crypto-shredding-derived-index.md) — der geänderte Beschluss
- [ADR-288](ADR-288-mail-recherche-hybride-projektion.md) — Identität und abgeleitete Artefakte
- `platform/tools/mail_agent/indexierung.py` — die Ausschlussregel, die hier zur Speichergrenze wird
- dev-hub#209 / dev-hub#210 / dev-hub#215 — Anhangs-Inventar

---

## 8. Changelog

| Datum | Autor | Änderung |
|---|---|---|
| 2026-08-03 | Achim Dehnert (Umsetzung: Claude Code) | Erstfassung. Owner-Entscheidung, dass Option D für die Mail-Lane nicht gilt. Ausgelöst durch den gemessenen Ist-Zustand (4 Volltexte bei 15.123 Nachrichten, 0 Anhangs-Zeilen) und die Volumen-Neumessung (relevanter Umfang hnu = 1,5 GB von 8,7 GB, weil die Ausschlussregel vom 2026-07-28 fünf Sechstel bereits entfernt). Der Rückschritt bei Art. 17 ist in §4.2 ausdrücklich als Preis benannt, nicht weggeschrieben. |
