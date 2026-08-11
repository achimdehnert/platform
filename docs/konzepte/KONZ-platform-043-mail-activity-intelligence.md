---
concept_id: KONZ-platform-043
title: Mail Activity Intelligence — Arbeitssicht aus drei Postfächern, und die Frage, worauf sie gebaut wird
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR
review_by: 2026-11-11
kill_criteria: "Die Zuordnungsgenauigkeit liegt auf der geschichteten Referenzmenge samt Konfidenzintervall vollständig unter 80 % ODER der Anteil falsch erzeugter Aufgaben übersteigt im ersten Produktionsmonat 10 % der in diesem Monat erzeugten Aufgaben — dann ist die abgeleitete Arbeitssicht nicht vertrauenswürdig und das Vorhaben endet bei Stufe 2 (Semantic Foundation nach C1: Suche und Verlauf, ohne Aufgaben-Ableitung)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/shared/Technisches Konzept_ Mail Activity Intelligence System.md", commit_or_pr: "n/a (Owner-Eingabe 2026-08-11)", opened_in_session: true}
  - {claim_id: C2, source_path: "dev-hub/apps/mail_agent/models.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C3, source_path: "dev-hub/apps/mail_agent/views.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C4, source_path: "platform/docs/adr/ADR-288-mail-recherche-hybride-projektion.md", commit_or_pr: "status proposed", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-293-mail-vollstaendige-verfuegbarkeit-statt-just-in-time.md", commit_or_pr: "73d2419e (main)", opened_in_session: true}
  - {claim_id: C6, source_path: "~/.claude/mail-vorgaenge.json", commit_or_pr: "n/a (lokal)", opened_in_session: true}
  - {claim_id: C7, source_path: "dev-hub mail_vorgang liste (prod, via SSH)", commit_or_pr: "n/a (Laufausgabe)", opened_in_session: true}
  - {claim_id: C8, source_path: "zwei externe Reviews dieses Konzepts (Owner-Eingabe 2026-08-11, Sitzungs-Kanal; Rohtexte nicht im Repo)", commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C9, source_path: "platform/docs/adr/ADR-288-mail-recherche-hybride-projektion.md §1.4.1 + §1.4.2", commit_or_pr: "status proposed", opened_in_session: true}
  - {claim_id: C10, source_path: "dev-hub apps/mail_agent/management/commands/mail_wartet.py (REC-2-Umsetzung, Lauf gegen Produktivbestand 2026-08-11)", commit_or_pr: "dev-hub#267 (offen)", opened_in_session: true}
created: 2026-08-11
---

# KONZ-platform-043 — Mail Activity Intelligence

## 1 Executive Summary

Der Owner hat ein technisches Konzept eingebracht (C1): Aus drei Postfächern soll eine
Arbeitssicht entstehen — laufende Vorgänge, offene Aufgaben, Wartezustände, nächste
Aktionen —, gestützt auf PostgreSQL als Zustandsführer, pgvector als Kandidatensuche und
LLMs als Interpreten. Nicht eine weitere Mailoberfläche, sondern ein **Activity Cockpit**.

Das Konzept ist fachlich stark. Seine Arbeitsteilung — *SQL entscheidet, Vektor schlägt vor,
LLM interpretiert* — ist die richtige, und mehrere seiner Festlegungen sind schärfer als
alles, was bei uns bisher geschrieben steht: `proposed ≠ open` für abgeleitete Aufgaben,
Precision vor Recall, eine deterministische Zustandsmaschine über den LLM-Signalen, und eine
lückenlose Herkunftskette von der Aufgabe zurück zur Originalnachricht.

**Die eigentliche Entscheidung ist keine dieser Festlegungen, sondern eine, die das Konzept
gar nicht stellt: worauf gebaut wird.** Das Konzept ist als Neubau geschrieben (§20:
Projektstruktur `activity_intelligence/`, Stufe 0 „Produktionsfähige technische Basis
schaffen"). Bei uns läuft seit Wochen ein Mail-Bestand mit 11.964 Nachrichten aus denselben
drei Konten, mit funktionierenden Graph- und IMAP-Anbindungen, nächtlichem Abgleich und einer
ausgebauten Deckungsrechnung.

Ein erster Reflex lautet: Bestand ist Vorsprung. **Der Owner hat diesem Reflex ausdrücklich
widersprochen — „brownfield ist kein Vorteil, sondern ggf. Nachteil" —, und der Einwand
trägt.** Ein Bestand ist nur so viel wert, wie seine Annahmen noch gelten. Ein Teil unserer
Annahmen gilt nicht mehr, und ein anderer Teil steht heute im Widerspruch zu dem, was der
Owner als Ordnungsprinzip formuliert hat.

Dieses Konzept trennt darum, was der Reflex vermengt: **Die Ingest- und Deckungsschicht ist
ein echter Vermögenswert. Die Vorgangsschicht ist kein Fundament, sondern ein Stumpf mit
strittiger Identitätsregel.** Die Empfehlung folgt dieser Trennung, und §8 führt den
Neubau als vollwertige Alternative mit gemessenen Kosten — nicht als Strohmann.

---

## 2 Scope und Evidenzbasis

**In Scope:** Ob und worauf eine abgeleitete Arbeitssicht über die drei Postfächer gebaut
wird; welche Teile des Bestands tragen; welche Entscheidungen vorher fallen müssen.

**Out of Scope:** Die Bedienoberfläche im Detail, die Wahl konkreter Modelle, der Umbau
des todo-Boards (KONZ-platform-040 §14), Versand und jede Außenwirkung.

**Alle Zahlen unten sind Messungen vom 2026-08-11**, erhoben in der Sitzung, in der dieses
Konzept entstand. Was nicht gemessen wurde, ist als solches gekennzeichnet.

**Nicht geprüft, ausdrücklich:** die Qualität der bestehenden Threading-Auflösung an einer
Referenzmenge; die Laufzeit einer Einbettung über den Gesamtbestand; ob `pgvector` in der
dev-hub-Datenbank aktiviert ist (nur im Orchestrator belegt). Alle drei gehören in Stufe 0
jeder Variante.

### 2.1 Zwei Zählungen, zwei Bezugsrahmen — keine Abweichung

Dieses Dokument nennt zwei Bestandszahlen, die einander zu widersprechen scheinen. Sie
messen Verschiedenes:

| Zahl | Was gezählt wurde | Umfang | Quelle |
|---|---|---|---|
| **11.964** Nachrichten | **eingelesener** Bestand in `mail_agent`, normalisiert und persistiert | **drei** Konten | Messung 2026-08-11 (§1) |
| **14.016** Kopfsätze | **read-only Kopfzeilen-Vollaufbau**, nichts geschrieben | **vier** Konten, 180 behaltene Ordner | ADR-288 §1.4.2, Lauf 2026-07-29 (C9) |

Das vierte Konto ist in der Gate-5-Messung enthalten, im eingelesenen Bestand nicht. Zum
Größenverhältnis: Gate 0 derselben ADR zählte am 2026-07-29 **66.580** Nachrichten über 246
Ordner in vier Konten (C9) — die 14.016 sind die *behaltenen* Ordner nach Ausschluss, nicht
der Gesamtbestand. Die 2,7 Minuten in §8 beziehen sich ausschließlich auf diesen
Kopfzeilen-Lauf; Datenbankschreiben und Normalisierung sind darin **nicht** enthalten
(ADR-288 §1.4.2 führt das als offenen Rest von Gate 5).

### 2.2 Die Stufen aus C1 — Kurzfassung

Dieses Dokument verweist an mehreren Stellen auf „Stufe 0/2/3/4+". Die Stufen sind in C1
definiert, nicht hier; wer C1 nicht vorliegen hat, konnte das wichtigste Kriterium des
Kill-Gates bisher nicht prüfen. Kurzfassung (Bezeichnungen wörtlich aus C1):

| Stufe | Name in C1 | Was danach existiert |
|---|---|---|
| 0 | Technical Foundation | Schema, `pgvector`, Betriebsbasis |
| 1 | Mail Ingestion | drei Konten angebunden, inkrementell, Nachrichten gespeichert |
| 2 | Semantic Foundation | Bereinigung, Signatur/Zitat-Erkennung, Einbettungen — **Suche und Verlauf** |
| 3 | Activity Detection **MVP** | Kandidatensuche + Hybrid-Scoring → Nachricht wird einem Vorgang zugeordnet |
| 4 | Event Extraction | aus Nachrichten werden fachliche Ereignisse |
| 5 | Todo Intelligence | Aktionen, getrennt nach „für mich" / „für andere" |
| 6 | Activity State Engine | deterministische Zustandsmaschine über den Modellsignalen |
| 7 | Management Cockpit | das eigentliche Produkt: offene Aktionen, Wartezustände |
| 8 | Conversational Query | Fragen in natürlicher Sprache |
| 9 | weitere Quellen | über Mail hinaus |

**Zwei Lesarten sind damit auszuräumen.** Erstens: „endet bei Stufe 2" heißt *Suche und
Verlauf bleiben, Aufgaben-Ableitung entfällt* — die Zuordnung beginnt erst mit Stufe 3, die
Aufgaben erst mit Stufe 5. Zweitens: C1 trägt seinen **eigenen** MVP-Begriff (Stufe 3). Er ist
nicht identisch mit REC-2 dieses Dokuments und auch nicht mit dem Zuschnitt aus der externen
Zweitmeinung — siehe §14.1, wo die drei Größen nebeneinander stehen.

---

## 3 Infrastruktur-Fit

| Baustein des Konzepts (C1) | Zustand bei uns (C2, C7) |
|---|---|
| `emails` | `LogicalMessage` — mit `internet_message_id`, `thread_key`, `in_reply_to`, `references`, `kennung` (unique) |
| `email_recipients` | `MessageParticipant` mit Rolle `to`/`cc` |
| `threads` | teilweise — `thread_key` (normalisierter Betreff) plus RFC-Verkettung, keine eigene Entität |
| `attachments` | `Attachment` |
| `activity_emails` | `VorgangsZuordnung` — trägt bereits `quelle` (manuell/…) |
| `activities` | `Vorgang` — vier fachliche Felder, **2 Zeilen, 15 Zuordnungen** |
| `persons`, `organizations` | **fehlt** |
| `todos`, `waiting_items` | **fehlt** |
| `embeddings` | **fehlt** in `mail_agent` |
| `llm_runs`, `user_feedback` | **fehlt** |
| — (im Konzept nicht vorgesehen) | `CoverageSnapshot`, `BuildGeneration`, `FolderScan`, `SyncCursor`, `RawObject` |

Gemessen: 17 Modelle in `mail_agent`; die Level-1-Entitäten sind vollständig vorhanden, die
Level-2/3-Entitäten des Konzepts sämtlich abwesend (Positivkontrolle mitgeführt).

**Die letzte Zeile ist die wichtigste.** Wir haben etwas, das im Konzept fehlt: eine
Maschinerie, die festhält, *worüber* eine Aussage überhaupt reicht.

---

## 4 Steelman des eingebrachten Konzepts

Wohlwollend gelesen ist es kein Vorschlag für ein Mailprogramm, sondern für eine
**Zustandsmaschine über Kommunikationsereignissen**. Das ist der richtige Zuschnitt, und die
Begründung in §25 trifft: Modelliert wird nicht die Mailbox, sondern ein persistenter
Vorgangszustand, der aus mehreren Ereignissen abgeleitet ist.

Drei Festlegungen sind besser als das, was bei uns geschrieben steht:

**Die Zustandsmaschine entscheidet, das Modell schlägt vor** (§Stufe 6). Damit ist die
Instanz, die interpretiert, nicht die Instanz, die entscheidet. Das ist die strukturelle
Antwort auf eine Fehlerklasse, die in dieser Sitzung mehrfach aufgetreten ist: Ein plausibler
Schluss wurde zur Feststellung, ohne dass eine deterministische Prüfung dazwischenlag.

**`proposed ≠ open`** (§5.9). Unsichere Ableitungen werden Vorschlag, nicht Auftrag. Mit
gestaffelten Schwellen und der ausdrücklichen Regel, dass bei Aufgaben **Precision wichtiger
ist als Recall** — eine falsch erzeugte Aufgabe zerstört Vertrauen schneller, als zehn
richtige es aufbauen.

**Die Herkunftskette** (§11). Aufgabe → Ereignis → Nachricht → Original, plus `llm_runs` mit
Modell, Prompt-Version, Eingabe-Hash. Damit ist eine Fehlentscheidung nachträglich
untersuchbar statt nur ärgerlich.

Das Hybrid-Scoring (§7.2) verdient eigene Erwähnung, weil es ein Problem löst, das der Owner
unabhängig davon benannt hat: Der Betreff trägt nicht, das Gegenüber allein auch nicht.
Gemessen: 13 Gegenüber auf 16 Vorgänge. Ein Mandant führt zwei fachlich getrennte Sachen,
eine Hochschule drei — dieselbe Gegenseite, verschiedene Angelegenheiten. Identität ist
**Gegenüber × Sache**, und genau das rechnet das Scoring aus Thread, Semantik, Personen,
Betreff und Zeit.

---

## 5 Konzeptdefinition

**Kernthese.** Die Arbeitssicht ist ableitbar, und die Ableitungsregeln des eingebrachten
Konzepts sind tragfähig. Was fehlt, ist eine Zusicherung, **worüber die Ableitung reicht** —
und eine Entscheidung, ob die bestehende Vorgangsschicht Fundament oder Altlast ist.

**Zielbild.** Ein Bestand, drei Schichten: unveränderte Quelle · wiederaufbaubare Ableitung ·
Arbeitszustand. Jede aggregierte Zahl trägt ihre Deckung. Jede Aufgabe trägt ihre Herkunft.
Jede automatische Zuordnung ist korrigierbar, und die Korrektur wird gespeichert.

**Was dieses Konzept hinzufügt**, das in C1 nicht steht:

1. **Deckung als Feld erster Klasse** (§7.1)
2. **Datenhoheit als Sperre, nicht als Schalter** (§7.2)
3. **Ein Zuhause für Aufgaben ohne Mailbezug** (§7.3)
4. **Die Bau-Entscheidung als eigener Punkt** (§8)

---

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus

**„Ihr baut ein Vertrauenssystem, obwohl ihr eine 16-Zeilen-Datei nicht konsistent haltet."**
Trifft. Am selben Tag lief ein handgepflegter Zähler aus dem Tritt, und ein Vorgang bündelte
acht Gegenüber. Das Konzept setzt auf Präzisionsziele über 90 %; die operative Disziplin, die
das trägt, ist nicht belegt. → §11 R1, und Kill-Gate.

**„Der Nutzen ist behauptet, nicht gemessen."** Niemand hat erhoben, wie viel Zeit heute für
das Auffinden offener Punkte draufgeht. Ohne diese Zahl ist jede Aufwandsentscheidung
gefühlsbasiert. → §12 REC-1.

**„500 annotierte Mails sind für einen Ein-Personen-Betrieb unrealistisch."** Trifft
teilweise. §22 in C1 nennt sie als Testgrundlage. Bei drei Konten mit Mandanten- und
Prüfungsdaten ist zudem offen, wo diese Annotationen liegen dürfen. → §12 REC-4 schlägt eine
kleinere, geschichtete Menge vor.

**„Die Deckungsforderung macht das Produkt unbenutzbar."** Ein Cockpit, das unter jeder Zahl
schreibt, was es nicht weiß, ermüdet. → Gegenrede in §7.1: Die Deckung gehört an die
Aussage, die von ihr abhängt, nicht an jede Zahl.

**„Ihr wollt Vektoren, weil es modern klingt."** Zu prüfen, nicht abzuwehren: Die
Notwendigkeit ist an *einem* Fall belegt — ein Gegenüber mit zwei getrennten Sachen. Ein Fall
ist eine Motivation, kein Beweis. → §12 REC-3 verlangt die Messung *vor* dem Einbau.

### 6.2 Maintainer 2028

Was findet jemand in zwei Jahren vor? Im günstigen Fall eine Zustandsmaschine mit
nachvollziehbaren Ableitungen. Im ungünstigen: eine Tabelle `activities` neben einer Tabelle
`Vorgang`, beide teilbefüllt, und niemand weiß mehr, welche gilt.

**Das ist die realistische Fehlerform**, und sie ist heute schon einmal eingetreten: Ein
Vorgangsbestand in der Datenbank (2 Zeilen) neben einem in einer Datei (16 Zeilen), beide
gepflegt, keiner maßgeblich. Wer Level 2 neu baut, ohne den Stumpf zu beerdigen, bekommt
denselben Zustand mit einer Tabelle mehr.

→ §12 REC-6: Die Ablösung des Bestehenden ist Teil der Lieferung, nicht ein Nachlauf.

### 6.3 Was diese Analyse nicht geleistet hat

Sie ist aus einer Feder. Für ein T3-Konzept sieht der Ablauf drei unabhängige Kritiker vor.
Zwei Agenten liefen in derselben Sitzung gegen ein anderes Konzept desselben Autors und
fanden vier Fehler, die dem Autor bei eigener Kritik entgangen waren. Es gibt keinen Grund
anzunehmen, dass es hier anders wäre. **Die externe Zweitmeinung ist deshalb nicht optional,
sondern Teil der Abnahme.**

> **Nachtrag 2026-08-11:** Zwei unabhängige Runden sind eingegangen (C8) und in §14
> ausgewertet. Die Erwartung hat sich bestätigt — beide fanden Mängel, die dem Autor bei
> eigener Kritik entgangen waren, darunter einen Befund mit falscher Normreferenz (B9) und
> ein Kill-Gate, dessen Schwellen statistisch nicht tragen (§13). Dieser Abschnitt bleibt
> stehen, weil sein Grund fortbesteht: Die *Analyse* ist weiterhin aus einer Feder, geprüft
> ist nur ihr Ergebnis.

---

## 7 Deep-Dive

### 7.1 Deckung — der schwerste Mangel des eingebrachten Konzepts

C1 §13.1 zeigt ein Dashboard: „47 laufende Activities · 5 Action Required · 3 Overdue". Es
sagt nirgends, worüber diese Zahlen reichen.

Bei uns ist das keine Feinheit. Gemessen am 2026-08-11: Der Index kennt alles bis zum
nächtlichen Lauf um 03:30 — was danach eintrifft, ist ihm unbekannt. **22 Nachrichten tragen
kein Datum** und fallen damit aus jeder Zeitfensterabfrage. Ordner sind bewusst
ausgeschlossen. Eine Aussage „5 benötigen deine Aktion" ist unter diesen Bedingungen keine
Zahl, sondern ein Eindruck.

Genau dagegen existiert bei uns bereits Maschinerie — `CoverageSnapshot`, `FolderScan`,
`BuildGeneration` — und eine Entscheidung: ADR-288 §8 Gate 1 verlangt, dass ohne vollständige
Deckung kein Punkt als `open` gilt, sondern als `unknown`. **Das ist der Beitrag, den unsere
Seite einbringt, und er ist nicht nachträglich einbaubar** — er bestimmt das Schema.

**Zur Ermüdungs-Gegenrede:** Die Deckung gehört nicht unter jede Zahl. Sie gehört an
**Negativ- und Vollständigkeitsaussagen** — „nichts offen bei X", „alle Fristen erfasst",
„seit N Tagen keine Antwort". Positive Einzeltreffer („diese Mail ist eingegangen") tragen
sich selbst. Die Regel lautet: *Eine Aussage, die sich umkehrt, wenn eine Nachricht fehlt,
braucht eine Deckungsangabe.*

### 7.2 Datenhoheit — Sperre, nicht Schalter

C1 §17 schlägt Kennzeichen je Konto vor (`external_llm_allowed`). Der Gedanke stimmt, die
Härte reicht nicht.

Die drei Konten sind nicht gleichartig. Eines führt Korrespondenz mit Mandanten eines
externen Datenschutzbeauftragten. Eines führt Prüfungsvorgänge Studierender, für die die
Hochschule Verantwortlicher ist — nicht wir. Für diesen Kanal galt zwischenzeitlich
ausdrücklich „live lesen, nichts speichern".

Daraus folgt mehr als ein Schalter:

- Die Klassifikation gehört an die **Nachricht**, nicht nur an das Konto — ein Mandantenname
  in einer privaten Mail bleibt ein Mandantenname.
- Verboten ist nicht nur der externe Anbieter, sondern **jede Ausleitung ohne benannte
  Rechtsgrundlage**, einschließlich Einbettungen: Ein Einbettungsvektor ist eine Ableitung
  aus personenbezogenem Inhalt.
- Eine Sperre, die stillschweigend leer läuft, ist gefährlicher als keine. Sie braucht eine
  Positivkontrolle: Der Prüfer muss nachweislich auch Treffer erzeugen können.

### 7.3 Aufgaben ohne Mailbezug

Gemessen: 3 von 16 Vorgängen entstehen aus keinem Postfach — eine private Rechnung, eine
Buchung in der Buchhaltung, eine Unterschrift auf Papier. Sie tragen bereits ein
Typ-Kennzeichen und sind maschinell erkennbar.

C1 kennt sie nicht. Ein Cockpit, das den Anspruch erhebt, *die* Arbeitssicht zu sein, muss
sie aufnehmen — sonst bleiben zwei Listen, und die Ablösung scheitert an dem Rest, der nicht
ableitbar ist.

Konsequenz für das Schema: Eine Aufgabe braucht **keinen** Pflicht-Fremdschlüssel auf eine
Nachricht. Die Herkunft wird zum Attribut (`abgeleitet` · `manuell` · `Regel`), nicht zur
Existenzbedingung.

---

## 8 Alternativen — die eigentliche Entscheidung

Der Owner hat dem Reflex „Bestand ist Vorsprung" widersprochen. Dieser Abschnitt nimmt den
Einwand ernst und führt den Neubau als vollwertige Option.

**Der Bestand zerfällt in zwei Teile mit sehr unterschiedlichem Wert:**

| Teil | Trägt noch? | Begründung |
|---|---|---|
| **Ingest + Deckung** (Level 1) | **ja** | Annahmen unverändert gültig: Nachrichten haben stabile Kennungen, Ordner wechseln, Deckung muss ausweisbar sein. Läuft nächtlich, drei Konten, zwei Transporte. |
| **Vorgangsschicht** (Level 2) | **nein** | 2 Zeilen. Geformt unter einer Annahme, die aufgehoben ist (Volltext-Beschränkung, ADR-286 Option D → durch ADR-293 für die Mail-Lane gefallen, C5). Identitätsregel strittig: ADR-286 §4.9 sagt Ordnername, der Owner sagt Gegenüber, C1 sagt gewichtetes Scoring — drei Antworten auf dieselbe Frage. |

| # | Option | Kosten | Risiko | Verdikt |
|---|---|---|---|---|
| A | Alles neu, eigenes Projekt | hoch — Ingest, Transporte, Deckung noch einmal | verliert die Deckungsmaschinerie, die C1 gar nicht kennt | verworfen, aber knapp |
| B | Alles auf dem Bestand erweitern | niedrig | erbt die strittige Identitätsregel und den Stumpf | **verworfen** — das ist der Reflex, dem der Owner widerspricht |
| C | **Level 1 behalten, Level 2/3 neu** | mittel | die Ablösung des Stumpfes muss erzwungen werden | **empfohlen** |
| D | Neu bauen, Bestand einmalig einlesen | mittel-hoch | doppelte Ingest-Pflege während der Umstellung | Rückfalloption zu C |

**Warum A knapp scheitert und nicht deutlich:** Der Neuaufbau des Ingest ist billiger, als er
aussieht. Gemessen (ADR-288 §8 Gate 5, C4): 14.016 Kopfsätze aus 180 Ordnern über vier Konten
und beide Transporte in **2,7 Minuten**. Ein Wiedereinlesen ist also keine Wochenaufgabe.
Was A wirklich verlöre, ist nicht der Bestand, sondern die **Deckungsrechnung** — und die ist
teuer, weil sie aus Fehlern entstanden ist, nicht aus Entwurf.

**Warum C und nicht B:** Weil auf Level 2 nichts zu erhalten ist. Zwei Zeilen sind kein
Fundament. Wer dort erweitert, übernimmt eine Identitätsregel, die drei widersprüchliche
Antworten hat — und genau diese Übernahme ist der Nachteil, den der Owner benennt.

---

## 9 Out-of-the-Box

**Braucht es überhaupt eine Ableitung, oder reicht Suchen?** Der teuerste Teil ist die
automatische Zuordnung. Ein Cockpit, das nur „diese Gegenüber haben seit N Tagen keine
Antwort" zeigt — rein aus Kopfdaten, ohne LLM, ohne Vektor —, wäre in Tagen baubar und
beantwortet vermutlich den größten Teil der Frage „was ist offen". **Das gehört vor die
große Lösung gemessen**, nicht danach. → §12 REC-2.

**Sollte der Zustand überhaupt gespeichert werden?** Denkbare Gegenposition: Der Zustand wird
bei jedem Aufruf neu abgeleitet, gespeichert wird nur die menschliche Korrektur. Das macht
Modellwechsel folgenlos und verhindert veralteten Zustand. Kostet Rechenzeit, spart ein
Konsistenzproblem. Für einen Bestand dieser Größe erwägenswert.

**Wo lebt es?** Bewusst offen gelassen. Der Autor dieses Konzepts ist derjenige, dessen
Fähigkeiten damit wachsen, und damit befangen. Kriterien statt Antwort in §12 REC-7.

---

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| B1 | C1 kennt keine Deckung; Aggregate wären unbelegt | C1 §13.1 |
| B2 | 22 Nachrichten ohne Datum fallen aus jeder Zeitabfrage | Messung 2026-08-11 |
| B3 | Level-2/3-Entitäten fehlen vollständig; Level 1 ist komplett | C2 |
| B4 | `Vorgang` hat 2 Zeilen — kein Fundament, ein Stumpf | C7 |
| B5 | Drei widersprüchliche Identitätsregeln (Ordnername · Gegenüber · Scoring) | ADR-286 §4.9, Owner 2026-08-11, C1 §7.2 |
| B6 | ADR-293 hat die Volltext-Beschränkung für die Mail-Lane aufgehoben — die Schemaform stammt noch von davor | C5 |
| B7 | 3 von 16 Vorgängen haben keinen Mailbezug | C6 |
| B8 | Identität ist Gegenüber × Sache, nicht Gegenüber | C6 (13 Gegenüber / 16 Vorgänge) |
| B9 | `UUID PK` in C1 verletzt **keine** belegte plattformweite Norm — die Konvention wird als Standard behandelt, ohne einer zu sein | ADR-022, ADR-109, ADR-097/139/146/153/172 |
| B10 | Zwei konkurrierende Vorgangsbestände existieren bereits | C6, C7 |
| B11 | Die Wartezeit-Verteilung steigt monoton — kein Tal zwischen „wartet noch" und „vorbei" | dev-hub#267, Lauf gegen Prod 2026-08-11 (C10) |

**Korrektur zu B9 — zweifach, und die erste Korrektur war selbst zu weit gefasst.**

*Erste Fassung:* „widerspricht ADR-022". **Falsch.** ADR-022 ist der *Platform Consistency
Standard* und entscheidet Dockerfile, Compose, Ports, Health-Endpunkte und CI/CD;
`grep -nE "UUID|JSONB" ADR-022*.md` liefert **null Treffer**.

*Zweite Fassung (2026-08-11, ebenfalls hier):* „die einschlägige Norm ist ADR-109 Fix H-1".
**Zu weit.** Der Text existiert wörtlich — `id = BigAutoField(primary_key=True)` und
`public_id = UUIDField(...)`, beide mit dem Zusatz „Platform-Pflicht" —, aber er steht
**innerhalb der Definition von `TenantModel`** aus `django_tenancy`, und ADR-109 adressiert
laut Kopf „alle Django-Hub-Repos mit **Frontend-UI**" im Rahmen der Mandantenführung. Er
bindet also mandantengeführte Modelle in Hubs mit aktiver Tenancy — kein flächendeckender
Primärschlüssel-Standard für jedes Modell jedes Repos.

*Belegter Stand.* Die Konvention lebt real in **App-ADRs** — ADR-097, 139, 146, 153, 172
enthalten je 1–3 Treffer auf `BigAutoField`/`DEFAULT_AUTO_FIELD` — und wird in der
Constraint-Liste des `/prompt`-Skills als „ADR-022 (Database-First)" geführt, also unter
einer Nummer, die sie nicht enthält. Gegenläufig: ADR-028 verwendet UUID-PKs, ADR-137 §2.6
führt die Ablösung in risk-hub als offenen Hygiene-Punkt.

**Konsequenz.** Der Neubau folgt der App-Konvention `BigAutoField` + `public_id` — nicht,
weil eine Norm ihn zwingt, sondern weil es das verbreitete Muster ist und die von der
externen Zweitmeinung geforderte *stabile, nicht aus dem Inhalt berechnete* Identität erfüllt
(sie hängt an der Existenz einer eigenen ID, nicht an deren Typ). Ob ADR-109 zusätzlich
bindet, entscheidet sich erst mit REC-7 (Ort) und der dortigen Tenancy-Einstellung. Zwei
Reste bleiben ausdrücklich offen:

- **Eine als Standard behandelte Konvention ohne Standard ist selbst ein Befund.** Ob sie
  einen eigenen ADR bekommt, ist zu entscheiden — nicht in diesem Konzept.
- Für `JSONB` existiert **keine** Norm. Die Wahl ist frei, aber im Folge-ADR
  begründungspflichtig, nicht stillschweigend aus C1 zu übernehmen.

**Zu B11 — das ist die erste harte Messung zur Kernfrage.** Der MVP (REC-2, dev-hub#267)
maß gegen den Produktivbestand: 28 Fälle im Fenster 7–14 Tage, 21 bei 15–30, 34 bei 31–60,
14 bei 61–90, 65 bei 91–180, 120 bei 181–365, 149 darüber. Die Verteilung steigt **monoton
mit dem Alter**; es gibt keine Senke, an der sich „wartet noch" von „ist längst vorbei"
trennen ließe. Jede Obergrenze ist damit eine Setzung, keine Entdeckung — gewählt wurden 30
Tage (Owner-Entscheid), Ergebnis 49 statt 431 Zeilen.

**Zwei Folgerungen, die im MVP selbst nicht stehen.** Erstens: Das Alter allein trägt die
Information nicht — genau das, was eine Vorgangs-Zustandsmaschine liefern soll. B11 spricht
damit **für** Option C, nicht gegen sie. Zweitens: Die 49 sind **Gegenüber, keine Vorgänge**.
Nach B8 ist Identität Gegenüber × Sache; ein Gegenüber mit zwei getrennten Sachen erzeugt im
MVP eine Zeile statt zwei. **49 ist eine Untergrenze.**

### B12 — der Abstand Gegenüber → Faden ist gemessen

Am 2026-08-11 nachgemessen, lesend gegen denselben Produktivbestand (C10, `--je-faden`;
gleiches Fenster 7–30 Tage, gleicher Zeitraum ab 2025):

| Größe | je Gegenüber | je Faden |
|---|---:|---:|
| Zeilen im Fenster | **49** | **168** |
| davon „ich schulde" | 13 | **70** |
| davon „ich warte" | 36 | 98 |
| jenseits der Obergrenze | 382 | 3.161 |
| beteiligte Gegenüber | 49 | **66** |

Deckung: 11.964 Nachrichten, Zustand `likely_open`, eine Lücke — die 22 ohne Datum (B2).
Die 49 reproduzieren die Erstmessung exakt; die Gruppierung je Adresse ist unverändert.

**Drei Dinge stehen damit fest, die vorher Vermutung waren.**

1. **Die Untergrenze ist um den Faktor 3,4 zu niedrig.** Aus 49 werden 168 Zeilen. Die
   Vorgangserkennung fügt also nicht eine Nuance hinzu, sondern den Großteil der Liste.
2. **Am stärksten verdeckt wird ausgerechnet „ich schulde": 13 → 70, Faktor 5,4** gegenüber
   3,4 im Mittel. Das ist strukturell und nicht zufällig: Je Adresse kippt **jede** Antwort in
   **irgendeiner** Sache die Richtung auf „ich warte" und verdeckt damit alle unbeantworteten
   Fäden desselben Gegenübers. Der Fall, für den das Cockpit gebaut wird — *was schulde ich?* —
   ist genau der, den die billige Gruppierung am zuverlässigsten verschluckt.
3. **17 Gegenüber tauchen je Adresse überhaupt nicht auf** (66 gegen 49). 28 der 66 führen
   mehr als einen Faden, einer führt 19.

**Was die Messung nicht sagt.** `thread_key` ist der normalisierte Betreff, mit Fehlern in
beide Richtungen (B5): Eine Sache mit wechselndem Betreff zerfällt, zwei Sachen unter „Re:
Anfrage" fallen zusammen. Die 168 sind deshalb **kein** Vorgangs-Istwert — die 19 Fäden eines
Gegenübers sind ebenso plausibel eine übertrennte Sache wie 19 echte. Falsifiziert ist
trotzdem etwas: Ein Abstand nahe null hätte entweder B8 widerlegt oder dem Betreff jedes
Trennsignal abgesprochen. Er ist nicht nahe null.

---

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmittel |
|---|---|---|---|
| R1 | Falsch erzeugte Aufgaben zerstören das Vertrauen | System wird umgangen, Aufwand verloren | `proposed ≠ open`; Kill-Gate auf Precision |
| R2 | Dritter Vorgangsbestand entsteht | genau der heutige Zustand plus eine Tabelle | Ablösung ist Lieferbestandteil (REC-6) |
| R3 | Deckung wird nachgerüstet statt eingebaut | Aggregate bleiben dauerhaft unbelegbar | Schema-Entscheidung in Stufe 0 |
| R4 | Personenbezogene Inhalte verlassen unbemerkt den Rechner | Rechtsverstoß, nicht nur Panne | Sperre je Nachricht + Positivkontrolle |
| R5 | Das Vorhaben bleibt in Stufe 3 stecken | Aufwand ohne Nutzen | REC-2: kleine Lösung zuerst messen |

---

## 12 Empfehlungen

| ID | Empfehlung | Konkret |
|---|---|---|
| REC-1 | Nutzen einmal messen, bevor gebaut wird | Zwei Wochen mitschreiben, wie lange das Auffinden offener Punkte dauert. Ohne diese Zahl ist die Aufwandsentscheidung gefühlsbasiert. |
| REC-2 | Die kleine Lösung zuerst | **Gebaut am 2026-08-11** — `mail_wartet`, dev-hub#267 (C10): „Gegenüber ohne Antwort seit N Tagen" rein aus Kopfdaten, ohne LLM und Vektor, Deckung geerbt aus `mail_suche`. Ergebnis und Grenze in B11. Die Vergleichsbasis existiert damit; was sie **nicht** liefert, ist der Nutzenwert — dafür bleibt REC-1 offen. |
| REC-3 | Vektoren erst nach Messung | Die Notwendigkeit ist an einem Fall belegt. Vor dem Einbau an einer geschichteten Stichprobe zeigen, wie oft Thread und Beteiligte allein nicht ausreichen. |
| REC-4 | Referenzmenge klein und geschichtet | Statt 500 annotierter Mails: 60–80 über die schwierigen Klassen (Weiterleitung, generischer Betreff, Ordnerwechsel, Mehrfachkopien, zwei Sachen bei einem Gegenüber). Ablage im Geltungsbereich der Datenhoheit. |
| REC-5 | Deckung ins Schema, nicht ins Dashboard | Jede aggregierte Aussage referenziert die Generation und den Deckungsstand, aus dem sie stammt. Nicht nachrüstbar. |
| REC-6 | Ablösung ist Lieferbestandteil | Eine Stufe gilt erst als fertig, wenn der abgelöste Bestand nachweislich leer oder nur noch Ausgabe ist. |
| REC-7 | Ort entscheiden, nicht ableiten | Kriterien: Wo liegen die Daten? Wer darf lesen? Was passiert bei Ausfall? Welcher Wirkungsradius bei Schreibrechten nach außen? Der Autor ist befangen — die Antwort gehört zum Owner. |
| REC-8 | Externe Zweitmeinung vor der Entscheidung | **Erledigt am 2026-08-11** (zwei unabhängige Runden, C8) — Auswertung in §14. Eine dritte Runde erst nach Einarbeitung, sonst kritisiert sie den alten Stand. |
| REC-9 | Zustand wird gespeichert, nicht je Aufruf abgeleitet | §9 warf die Frage auf und ließ sie offen. **Entschieden: persistent.** Ein je Aufruf neu abgeleiteter Zustand ist nicht korrigierbar — dieselbe Nachricht kann in zwei Läufen verschieden eingeordnet werden, und die menschliche Korrektur hätte kein Objekt, an dem sie haftet. Der Preis (veralteter Zustand nach Modellwechsel) wird über `ProcessingRun`/Generation getragen, nicht über Neuberechnung. Gegenprobe für die Umstimmung: Wird nur recherchiert statt gearbeitet, ist die Persistenzschicht überflüssig. |
| REC-10 | Nachrichten ohne Datum: eigenes Feld, kein stiller Fallback | B2 (22 Nachrichten) ist ein behebbarer Datenfehler, kein Naturgesetz. **Aber nicht durch Auffüllen von `date`:** Der naheliegende Fallback auf IMAP-`INTERNALDATE` ist der **Ankunftsstempel im Postfach**, nicht das Nachrichtendatum — bei umsortierten oder migrierten Nachrichten weichen beide um Jahre ab (bei uns belegte Fehlerklasse). Richtige Form: zweites Feld `received_at` mit Herkunftskennzeichen; jede Zeitabfrage entscheidet ausdrücklich, welches sie meint, und Aussagen über den Zeitraum weisen die Ersetzung aus. |
| REC-11 | Aufwand von Option C schätzen | REC-1 misst den Nutzen; die Kostenseite trägt bisher nur das Etikett „mittel" (§8). Für die 30-Tage-Entscheidung fehlt eine grobe Schätzung in Wochen **mit Unsicherheitsband**. Ohne sie ist die Rechnung, die REC-1 aufmacht, einseitig. |

---

## 13 Entscheidung, Kill-Gate, 30/60/90

**Vorgeschlagene Entscheidung:** Option C — Ingest- und Deckungsschicht behalten,
Vorgangs- und Arbeitsschicht neu. **Nicht sofort umsetzen:** REC-1 und REC-2 gehen voraus,
weil sie den Zuschnitt bestimmen.

**Kill-Gate.** Das Vorhaben endet bei Stufe 2 (Semantic Foundation, §2.2 — Suche und Verlauf
ohne Aufgaben-Ableitung), wenn eines eintritt:

| Kriterium | Status | Beleg |
|---|---|---|
| (a) Zuordnungsgenauigkeit **klar unter 80 %** — Bandregel unten | offen | Referenzmenge existiert nicht (REC-4) |
| (b) Über 10 % der **in einem Produktionsmonat erzeugten** Aufgaben sind falsch | offen | Nenner und Fenster jetzt benannt |
| (c) REC-2 zeigt: die kleine Lösung deckt den Nutzen bereits ab | **gebaut, unentschieden** | dev-hub#267 (C10), Auswertung unten |
| (d) Für **eines** der drei Konten ist keine Verarbeitung zulässig — Nutzenanteil unten | offen | Klassifikation fehlt |
| (e) Bis 2026-11-11 ist der Ort (REC-7) nicht entschieden | offen | `review_by` |

**Zu (a) — die 80 % sind eine Grauzone, keine Schwelle.** Bei der in REC-4 vorgeschlagenen
Menge von 60–80 Mails liegt das Konfidenzintervall um einen gemessenen Wert bei grob
± 9–10 Prozentpunkten. Eine gemessene 80 % kann damit weder das Bestehen noch das Reißen
belegen — eine harte Schwelle auf dieser Basis wäre Scheingenauigkeit. Es gilt darum eine
Bandregel:

| Gemessen (Punktschätzer, n = 60–80) | Lesart |
|---|---|
| Obergrenze des Intervalls **unter 80 %** | Kriterium (a) **gerissen**, Vorhaben endet bei Stufe 2 |
| Intervall **überlappt 80 %** | **unentschieden** — Referenzmenge auf ≥ 200 aufstocken, dann erneut messen |
| Untergrenze des Intervalls **über 80 %** | Kriterium (a) **bestanden** |

Die Aufstockung ist der teure Fall und dann zu bezahlen — nicht vorab, weil der Bandbereich
möglicherweise gar nicht eintritt. Der Datenhoheitsrahmen aus REC-4 gilt für die größere
Menge unverändert.

**Zu (b) — Nenner und Fenster waren offen.** „10 %" bezieht sich nicht auf die Referenzmenge,
sondern auf den **laufenden Betrieb**: Anteil der als falsch markierten an allen in einem
Kalendermonat automatisch erzeugten Aufgaben, gemessen ab dem ersten Monat mit mindestens 30
erzeugten Aufgaben. Grund für den Wechsel des Bezugs: Eine falsch erzeugte Aufgabe schadet
dort, wo sie jemandem vorgelegt wird, nicht auf einer Testmenge — und die Referenzmenge misst
Zuordnung, nicht Aufgaben-Erzeugung. Die Zählung setzt voraus, dass Ablehnungen dauerhaft
gespeichert werden (REC-9).

**Zu (c) — gebaut, und die Messung entscheidet es nicht.** REC-2 existiert seit 2026-08-11
(dev-hub#267, C10). Sie widerlegt (c) nicht und bestätigt es nicht: Der Melder liefert 49
verwertbare Zeilen statt 431, aber B11 zeigt, dass er ab ~30 Tagen nicht mehr trennen kann,
und die 49 sind Gegenüber statt Vorgänge. **Wer daraus jetzt „also die große Lösung" macht,
ersetzt einen ungemessenen Schluss durch einen anderen** — ob 49 Zeilen den Bedarf decken,
ist keine Eigenschaft der Verteilung, sondern die Frage von REC-1, und REC-1 ist ungemessen.
Kriterium (c) bleibt deshalb ausdrücklich **unentschieden**, nicht „bestanden".

**Nachtrag desselben Tages:** Die zweite Hälfte dieser Bedingung ist erfüllt — der Abstand
ist beziffert (B12: 49 → 168, bei „ich schulde" 13 → 70). Er spricht **gegen** (c): Die
kleine Lösung deckt den Nutzen erkennbar *nicht* ab, sondern verschluckt bei der wichtigsten
Frage rund vier Fünftel. Damit fehlt für (c) nur noch REC-1 — und REC-1 ist die Frage, ob der
verbleibende Aufwand sich lohnt, nicht mehr, ob die Baseline reicht.

**Zu (d) — „zwei der drei Konten" war gegriffen.** Die Schwelle stand ohne Begründung und ist
korrigiert. Die drei Konten tragen ungleichen Nutzen, und das entscheidende ist nicht die
Anzahl: Fällt das Konto mit der Mandantenkorrespondenz aus, verliert das Cockpit seinen
Kernfall, während der Ausfall eines der beiden anderen es lediglich verkleinert. Das
Kriterium greift deshalb schon bei **einem** Konto — aber erst, nachdem der Nutzenanteil je
Konto beziffert ist. **Diese Bezifferung ist noch nicht erfolgt** und ist Teil von REC-1: Wer
zwei Wochen mitschreibt, wie lange das Auffinden offener Punkte dauert, schreibt zugleich
mit, aus welchem Konto der jeweilige Punkt stammt. Bis dahin ist (d) mit dieser Fassung
schärfer, aber noch nicht messbar.

**Exception-Budget:** bis **2026-11-11** dürfen die zwei Vorgangsbestände nebeneinander
bestehen. Danach ist entweder abgelöst oder dieses Konzept auf `sunset`.

**30/60/90:**
- **30 Tage:** REC-1 gemessen, REC-2 gebaut und benutzt, externe Zweitmeinung eingearbeitet,
  Ort entschieden.
- **60 Tage:** Referenzmenge (REC-4) steht; Datenhoheits-Klassifikation je Konto und
  Nachrichtenklasse liegt vor; Deckungs-Schemaentscheidung getroffen.
- **90 Tage:** Zuordnung gemessen gegen die Referenzmenge; Entscheidung über Stufe 4+ auf
  Basis der Zahl, nicht der Absicht.

---

## 14 Externe Zweitmeinung (REC-8) — Eingang und Auswertung

Am 2026-08-11 sind zwei unabhängige Runden eingegangen (C8). Die eine kritisiert dieses
Dokument Punkt für Punkt; die andere hat das Ausgangsproblem **ohne Repo-Zugriff** eigenständig
durchgearbeitet und einen eigenen Lösungsraum aufgespannt (ALT-1 Domänenmodell-first,
ALT-2 Retrieval-first, ALT-3 temporaler Wissensgraph, Empfehlung ALT-1). Beide Runden
bestätigen die Richtung; die Änderungen betreffen Genauigkeit, nicht Kurs.

### 14.1 Drei MVP-Zuschnitte — die eigentliche Kollision

Die schärfste Differenz liegt nicht zwischen Kritik und Dokument, sondern **zwischen den
beiden Runden**. Runde 1 nennt REC-2 den klügsten Einzelvorschlag des Dokuments. Runde 2
überspringt ihn und beginnt sofort mit der Domänenschicht, weil aus ihrer Sicht die eine
tragende Entscheidung lautet: *Der Zustand der Arbeit muss persistent und korrigierbar sein.*
REC-2 hat genau diese Persistenz nicht.

| Merkmal | REC-2 (dieses Dokument) | Zuschnitt Runde 2 | Stufe 3 „MVP" (C1) |
|---|---|---|---|
| Beantwortet | „Wer antwortet nicht?" | „Was ist mein Arbeitszustand?" | „Wohin gehört diese Mail?" |
| Neue Entitäten | keine | sieben | Vorgang + Zuordnung |
| Zuordnung | keine | manuell/halbautomatisch | automatisch, Hybrid-Scoring |
| LLM / Vektor | nein | optional | ja |
| Persistenter Zustand | nein | ja, der Kern | teilweise |
| Aufwand | Tage | Wochen | Monate |

**Auflösung, und sie ist keine Vertagung:** Die drei beantworten verschiedene Fragen. REC-2
misst, **ob** die große Lösung nötig ist — es ist die Vergleichsbasis für Kill-Kriterium (c)
und sonst nichts. Der Zuschnitt aus Runde 2 ist die Antwort auf die Frage, **wie** Option C
zugeschnitten wird, falls (c) nicht greift. Die Reihenfolge REC-1 → REC-2 → Option C bleibt
damit unverändert. Zwei Folgerungen sind aber neu:

**REC-2 ist nicht schema-frei.** Runde 2 verlangt, dass jede aggregierte Zahl an einen
Deckungs-Schnappschuss gebunden ist — unabhängig hergeleitet und deckungsgleich mit §7.1.
Das trifft REC-2 unmittelbar: „Gegenüber X hat seit 14 Tagen nicht geantwortet" ist genau
eine Aussage, die sich umkehrt, wenn eine Nachricht fehlt. Der Kopfdaten-Melder muss die
Generation von Tag 1 mitführen. Teuer ist das nicht — `CoverageSnapshot` und
`BuildGeneration` existieren bereits (§3); Runde 2 führt sie ohne Repo-Kenntnis als *neu*
anzulegende Objekte auf. Die Aussage in §9, REC-2 sei „in Tagen baubar", bleibt bestehen,
aber nicht mehr in der Lesart „ohne Schema-Entscheidung".

**REC-2 ist die einzige heute unstrittig zulässige Stufe.** Runde 1 erhebt den schärfsten
Einwand des gesamten Eingangs gegen §7.2: Ein Klassifikator, der Inhalte liest, um zu
entscheiden, ob Inhalte verarbeitet werden dürfen, **ist selbst Verarbeitung**. Der Einwand
trifft; §7.2 spezifiziert die Sperre unvollständig, und die dort geforderte Positivkontrolle
prüft in dieser Fassung das Falsche. Auflösung: Die Klassifikation muss lokal und vor jeder
Ausleitung stattfinden — der Satz fehlt und ist nachzutragen (offen, siehe §14.3). **REC-2
ist von dem Einwand nicht berührt**, weil es keine Inhalte anfasst: Absender, Empfänger,
Zeitstempel. Das ist ein Argument für den Kopfdaten-Melder, das in keiner der beiden Runden
steht und das dieses Dokument bisher nicht führte.

### 14.2 Unabhängige Bestätigungen

Runde 2 kannte weder Repo noch dieses Dokument und kam auf fünf derselben Festlegungen:

| Runde 2 | hier |
|---|---|
| Deckung an jedem Aggregat, gebunden an einen Schnappschuss | §7.1, REC-5 |
| Aufgaben ohne Mailbezug als vollwertige Objekte | §7.3 |
| eigene Vorgangs-ID, nicht aus Betreff oder Gegenüber berechnet | B5, B8 |
| Vektoren nur zur Kandidatenerzeugung, nie als Identitätsregel | REC-3 |
| Ingest behalten, Vorgangsschicht neu bewerten | §8 Option C |

Die letzte Zeile wiegt am schwersten. Runde 2 formuliert die Bedingung, unter der sie den
Bestand verwerfen würde: wenn dessen Identität faktisch der normalisierte Betreff ist. Genau
das ist bei uns der Fall — `thread_key` **ist** der normalisierte Betreff (§3). Option C ist
damit von außen bestätigt, ohne dass der Kritiker den Code gesehen hat.

### 14.3 Was eingearbeitet ist — und was offen bleibt

| Punkt aus C8 | Status |
|---|---|
| Zahlen 11.964 vs. 14.016 unerklärt | **eingearbeitet** — §2.1 |
| Stufen nur in C1 definiert, Kill-Gate dadurch ungeprüfbar | **eingearbeitet** — §2.2 |
| Kill-Gate (a): 80 % statistisch nicht tragfähig bei n = 70 | **eingearbeitet** — §13 Bandregel |
| Kill-Gate (b): Nenner und Zeitfenster offen | **eingearbeitet** — §13 |
| Kill-Gate (d): „zwei der drei Konten" unbegründet | **eingearbeitet** — §13, Schwelle auf eines |
| §9 ließ „Zustand speichern?" offen | **eingearbeitet** — REC-9 |
| B2 (22 ohne Datum) konstatiert statt behandelt | **eingearbeitet** — REC-10, mit Gegenrede |
| B9 ohne Konsequenz | **eingearbeitet** — §10, Normreferenz zugleich korrigiert |
| Kosten von Option C bleiben qualitativ | **offen** — REC-11, Schätzung nicht geliefert |
| Zirkularität der Datenhoheits-Klassifikation (§7.2) | **offen** — Lösung benannt (§14.1), Text nicht nachgezogen |
| Korrektur-Operationen (zusammenführen, trennen, verschieben, nicht zugehörig) | **offen** — im Schema nicht vorgesehen |
| Menschliche Korrektur als eigene Quelle, nicht als Überschreiben | **offen** — REC-9 nennt die Persistenz, nicht die Trennung |
| Retrieval-first (ALT-2) wurde nie als Alternative geführt | **offen** — §8 führt vier *Bau*-Optionen, keine *Architektur*-Optionen |

Die vier offenen Punkte sind **nicht vertagt, sondern hier verankert**: Sie stehen dieser
Auswertung nach im Dokument und gehen in die Abnahme ein. Der letzte wiegt am schwersten —
§8 hat den Lösungsraum nie geöffnet, sondern nur gefragt, worauf gebaut wird. Runde 2
verwirft ALT-2 mit einem Argument, das hier nirgends steht: Dieselbe Nachricht wird bei zwei
Läufen verschieden eingeordnet, womit Aggregate und Fristen unbelastbar werden. Das Argument
stützt die Empfehlung — aber es gehört in §8, nicht in eine Fußnote der Kritik.

**Eine dritte Runde jetzt würde den alten Stand kritisieren.** Sie ist erst nach Schließung
der vier offenen Punkte sinnvoll.

### 14.4 Gegenprobe am gebauten MVP

Wenige Stunden nach dieser Auswertung wurde REC-2 gebaut (dev-hub#267, C10). Damit sind zwei
Aussagen aus §14.1 nicht mehr Herleitung, sondern Befund — und eine dritte kommt hinzu, die
keine der beiden Runden vorhergesehen hat.

| Aussage in §14.1 | Stand nach dem MVP |
|---|---|
| REC-2 ist nicht schema-frei, die Deckung muss von Tag 1 mit | **belegt** — `open` nur bei vollständiger Deckung, sonst `likely_open`; geerbt aus `mail_suche`, nicht neu gebaut |
| REC-2 ist vom Zirkularitäts-Einwand nicht berührt | **belegt** — `inhaltsfrage=False` ist ausdrückliche Festlegung; gelesen wird der Umschlag, nicht der Text |
| — | **neu: B11**, die Verteilung hat kein Tal |

Drei Grenzen des MVP bestätigen zugleich Festlegungen dieses Konzepts, ohne dass er sie
verletzt — er beansprucht sie nicht:

- **Aufgaben ohne Mailbezug (§7.3)** sind für ihn strukturell unsichtbar. Er kann *die*
  Arbeitssicht nie sein, nur eine Spalte darin.
- **B2 (22 Nachrichten ohne Datum)** trifft ihn unmittelbar, weil er über das Alter filtert:
  Sie fallen aus jedem Fenster und erscheinen in keiner Zeile der Verteilung. Das ist der
  praktische Fall zu **REC-10** — und dort in der schärferen Form, weil ein
  `INTERNALDATE`-Fallback die Verteilung verschöbe, ohne dass es jemand sähe.
- **B8 (Gegenüber × Sache)** wird von ihm bewusst nicht bedient; daher die Untergrenze in B11.

Eine Festlegung des MVP ist **besser als alles, was dieses Konzept dazu schreibt**: Die
Zweiseitigkeits-Bedingung („nur Gegenüber, denen ich selbst geschrieben habe") entfernt
Verteiler, ohne dass jemand eine Ausschlussliste pflegt. §7.2 diskutiert Ausschlussregeln,
ohne eine anzugeben, die sich selbst trägt. Sie gehört bei einem Neubau übernommen.
