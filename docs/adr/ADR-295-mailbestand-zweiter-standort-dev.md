---
status: proposed
decision_date: 2026-08-11
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: [ADR-293]
related: [ADR-286, ADR-288, ADR-045]
implementation_status: none
last_reviewed: 2026-08-11
staleness_months: 6
tags: [mail, datenhaltung, dsgvo, dev-umgebung, loeschung]
---

# ADR-295: Mailbestand an einem zweiten Standort (Dev-Host)

> **Nummern-Hinweis:** 295 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

- **Status:** Proposed
- **Datum:** 2026-08-11
- **Amends:** ADR-293 (§4.3 „keine Auslagerung")
- **Betrifft:** `dev-hub` `apps/mail_agent`, Dev-Desktop

---

## 1. Kontext

ADR-293 hat entschieden, dass der Mailbestand **vollständig** gespeichert wird — Kopfdaten,
Texte und Anhangstexte, verschlüsselt, mit Crypto-Shredding als Löschweg. §4.2 dieses ADR
benennt ausdrücklich, was dort liegt: „Die Postfächer enthalten **echte** Personendaten
(Studierende, Mandanten, MEiKI-Kommunikation). Der Umfang dieser Entscheidung ist deshalb
kein Testbestand."

Derselbe ADR schließt in §4.3 aus, was hier beschlossen werden soll:

> Kein Objektspeicher, kein CDN, **keine Auslagerung** (§3.4).

und in der Risikotabelle:

> Ausschlussregel wird stillschweigend aufgeweicht — **Die Regel ist die Speichergrenze;
> Änderungen brauchen einen eigenen Beschluss.**

Dieser ADR ist dieser Beschluss. Er entsteht nicht aus einem Architekturbedarf, sondern aus
einer Arbeitsweise: Der Owner hat am 2026-08-11 entschieden, Entwicklungszyklen auf dem
Dev-Host zu fahren statt gegen Produktion, und den Bestand dort mit **Echtdaten** zu
belegen, abgesichert über Cloudflare Access.

**Zur Ehrlichkeit gehört der Gegenbefund:** Am selben Tag wurde belegt, dass die bisher
teuerste offene Messung (KONZ-platform-043 B12, Abstand Gegenüber → Faden) **lesend gegen
Produktion** in unter einer Minute lief, ohne Kopie und ohne Rückstand. Der Bedarf an einem
zweiten Bestand folgt also nicht aus dieser Messung. Er folgt aus dem Wunsch nach schnellen
Zyklen an der **Oberfläche** — Ansichten, Listen, Sortierungen —, wo ein realistischer
Bestand Unterschiede sichtbar macht, die ein Demo-Mandant verdeckt.

---

## 2. Entscheidung

**Der Mailbestand wird ein zweites Mal auf dem Dev-Host vorgehalten**, in derselben Form wie
in Produktion (verschlüsselte Bodies, gleiche Ausschlussregel), zugänglich ausschließlich
hinter Cloudflare Access. Der **HNU-Kanal ist eingeschlossen** — ausdrückliche
Owner-Entscheidung vom 2026-08-11 auf einen benannten Einwand hin.

**Was Cloudflare Access dabei leistet und was nicht.** Es regelt, *wer liest*. Es ist keine
Rechtsgrundlage, kein Löschmechanismus und keine Aussage über Sicherungskopien. Die drei
Punkte, an denen ADR-293 sein Risikomodell aufhängt, verdoppeln sich mit diesem Beschluss
und werden deshalb hier einzeln geregelt.

### 2.1 Löschung (Art. 17) gilt für beide Bestände

ADR-293 hat Art. 17 von einer Konstruktionsgarantie in eine **Operation** verwandelt:
Crypto-Shredding je Nachricht, „die Fähigkeit existiert und ist getestet — aber sie muss
künftig **ausgeführt** werden". Mit zwei Beständen heißt das:

- Eine Löschanfrage ist erst erledigt, wenn sie an **beiden** Orten ausgeführt **und an
  beiden belegt** ist. Ein Beleg für einen Ort ist kein Beleg.
- Der Löschweg braucht eine Stelle, die weiß, dass es zwei Orte gibt. Solange dieses
  Wissen nur in diesem ADR steht, ist es eine Fußnote, kein Mechanismus.
- Der zweite Bestand ist damit der teuerste Teil dieses Beschlusses — nicht sein
  Speicherplatz, sondern seine Löschpflicht.

### 2.2 Schlüssel

ADR-293: „ein verlorener Schlüssel macht den Bestand unlesbar, ein **kopierter** macht ihn
lesbar." Der zweite Standort braucht Zugriff auf lesbare Bodies, also einen Schlüssel.

**Festlegung:** Der Dev-Bestand bekommt einen **eigenen** Schlüssel; die Übertragung
findet auf der Ebene der entschlüsselten Nachricht statt, die am Ziel neu verschlüsselt
wird. Der Produktionsschlüssel verlässt den Produktionshost nicht. Begründung: Ein
kopierter Schlüssel macht jede spätere Kompromittierung des Dev-Hosts zu einer
Kompromittierung des Produktionsbestands — auch rückwirkend über alte Sicherungen. Ein
eigener Schlüssel begrenzt den Schaden auf den Bestand, der tatsächlich dort liegt.

### 2.3 Sicherungen

Was auf dem Dev-Host gesichert wird, ist nicht Teil dieses Beschlusses, sondern seine
**Voraussetzung**: Wer den Bestand dorthin bringt, muss wissen, wohin dessen Sicherungen
laufen und wie lange sie liegen. Ist das nicht beantwortet, entsteht eine dritte Kopie, die
niemand geplant hat — und Art. 17 gilt auch für sie.

### 2.4 Umfang und Alterung

- Die **Ausschlussregel bleibt unverändert** (ADR-293 §4.3): ausgeschlossene Ordner sind
  auch hier ausgeschlossen. Dieser ADR erweitert den Umfang nicht, er erlaubt einen
  zweiten Ort für denselben Umfang.
- Der Dev-Bestand ist **kein zweiter Primärbestand**. Er wird nicht fortgeschrieben,
  sondern periodisch ersetzt; zwischen zwei Ersetzungen ist er veraltet, und Aussagen aus
  ihm sind keine Aussagen über den echten Stand.
- Der Bestand hat ein **Ablaufdatum**: Ohne ausdrückliche Verlängerung wird er zum
  `review_by`-Termin dieses ADR gelöscht. Ein Bestand ohne Ablauf wird zum Dauerzustand,
  den niemand mehr entschieden hat.

---

## 3. Nicht in Scope

- Keine Ausweitung des Umfangs gegenüber ADR-293 (dieselbe Ausschlussregel).
- Kein dritter Standort, kein Objektspeicher, kein Export außerhalb dieser beiden Hosts.
- Keine Änderung an der Ingest-Strecke: Der Dev-Bestand entsteht durch Übertragung, nicht
  durch einen zweiten Abruf der Postfächer.
- Keine Aussage über die Dev-Deployment-Strecke selbst — die hat ihr eigenes Artefakt
  ([dev-hub#269](https://github.com/achimdehnert/dev-hub/issues/269)).

---

## 4. Risiken

| Risiko | Wahrscheinlichkeit | Wirkung | Gegenmaßnahme |
|---|---|---|---|
| Löschanfrage wird nur am Primärbestand ausgeführt | **Hoch** | Hoch | Gate 1: Löschweg kennt beide Orte, an einer realen Nachricht belegt |
| Dev-Sicherungen enthalten Mailinhalt, ungeplant | Mittel | Hoch | Gate 3: Sicherungsziel und Aufbewahrung vor der Übertragung geklärt |
| Zugang zum Dev-Bestand ist schwächer als gedacht | Mittel | Hoch | Gate 2: Positivkontrolle — unangemeldeter Aufruf wird nachweislich abgewiesen |
| Der Bestand veraltet und wird für aktuell gehalten | **Hoch** | Mittel | §2.4: kein Fortschreiben; Stand wird in der Oberfläche ausgewiesen |
| Der Bestand bleibt liegen, wenn der Anlass entfällt | Hoch | Mittel | §2.4 Ablaufdatum; Gate 5 |
| Aus dev-Containern zeigen Plattform-Domains auf Produktion | Bekannt | Mittel | [dev-hub#269](https://github.com/achimdehnert/dev-hub/issues/269), vor der Übertragung zu schließen |

---

## 5. Confirmation

Der Beschluss gilt als umgesetzt, wenn **alle fünf** Punkte belegt sind. Kein Punkt ist
durch einen bestandenen Test allein erfüllt — verlangt ist jeweils die Ausführung am
echten Ziel.

1. **Gate 1 — Löschung an beiden Orten.** Für **eine reale Nachricht** wird
   Crypto-Shredding an beiden Beständen ausgeführt, und danach ist an beiden nachgewiesen,
   dass Body **und** Anhangstext nicht mehr lesbar sind. Der Löschweg referenziert beide
   Orte im Code oder in einem Runbook, das er nachweislich abarbeitet.
2. **Gate 2 — Zugang belegt, mit Positivkontrolle.** Ein unangemeldeter Aufruf der
   Dev-Oberfläche wird abgewiesen (Statuscode im PR), **und** ein angemeldeter Aufruf
   gelingt. Nur die zweite Hälfte beweist, dass die erste etwas misst.
3. **Gate 3 — Sicherungen geklärt, bevor übertragen wird.** Ziel, Verschlüsselung und
   Aufbewahrungsdauer der Dev-Sicherungen sind benannt. Werden keine angefertigt, steht
   auch das ausdrücklich da.
4. **Gate 4 — eigener Schlüssel.** Der Produktionsschlüssel ist nachweislich nicht auf dem
   Dev-Host; der Dev-Bestand ist mit einem eigenen Schlüssel lesbar.
5. **Gate 5 — Ablauf verankert.** Das Ablaufdatum steht nicht nur hier, sondern in einem
   Artefakt, das zum Termin gelesen wird (Issue mit Fälligkeit oder Cron-Melder).

---

## 6. Alternativen

| Option | Beschreibung | Verdikt |
|---|---|---|
| **A** | Demo-Mandant (`seed_mail_agent_demo`) auf dev, Echtbestand nur in Produktion | Verworfen durch Owner-Entscheidung — deckt den Zweck, aber der Bestand ist zu klein und zu glatt für Oberflächen-Unterschiede |
| **B** | Kein zweiter Bestand; Messungen lesend gegen Produktion | Bleibt für Messungen der richtige Weg (B12 belegt es), löst die Oberflächen-Zyklen aber nicht |
| **C** | Nur **Kopfdaten** auf dev, keine Bodies | Nicht gewählt; wäre die deutlich risikoärmere Hälfte — Löschpflicht und Schlüsselfrage entfielen weitgehend, und für Listen, Sortierungen und Zähler reichen Kopfdaten. **Empfehlung des Autors, falls der Beschluss noch einmal aufgemacht wird.** |
| **D** | **Vollbestand auf dev hinter Cloudflare Access** | **Gewählt** (Owner, 2026-08-11) |

---

## 7. Offenlegung

Der Autor dieses ADR hat gegen die Entscheidung argumentiert und ist ihr dann gefolgt. Die
Argumente stehen in §1, §2 und Option C; sie sind nicht entkräftet, sondern überstimmt. Das
gehört hierhin, damit ein späterer Leser die Abwägung sieht und nicht nur das Ergebnis.

Was **nicht** mehr gilt: Der frühere Einwand „für den HNU-Kanal gilt live lesen, nichts
speichern" ist für den Primärbestand durch ADR-293 überholt. Er trug diesen Beschluss
nicht.
