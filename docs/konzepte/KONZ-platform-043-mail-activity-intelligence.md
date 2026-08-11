---
concept_id: KONZ-platform-043
title: Mail Activity Intelligence — Arbeitssicht aus drei Postfächern, und die Frage, worauf sie gebaut wird
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: org-weiter ADR
review_by: 2026-11-11
kill_criteria: "Die Genauigkeit der Vorgangs-Zuordnung bleibt auf einer annotierten Referenzmenge unter 80 % ODER der Anteil falsch erzeugter To-dos übersteigt 10 % — dann ist die abgeleitete Arbeitssicht nicht vertrauenswürdig und das Vorhaben endet bei Stufe 2 (Suche und Verlauf), ohne Aufgaben-Ableitung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/shared/Technisches Konzept_ Mail Activity Intelligence System.md", commit_or_pr: "n/a (Owner-Eingabe 2026-08-11)", opened_in_session: true}
  - {claim_id: C2, source_path: "dev-hub/apps/mail_agent/models.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C3, source_path: "dev-hub/apps/mail_agent/views.py", commit_or_pr: "n/a (Arbeitskopie)", opened_in_session: true}
  - {claim_id: C4, source_path: "platform/docs/adr/ADR-288-mail-recherche-hybride-projektion.md", commit_or_pr: "status proposed", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-293-mail-vollstaendige-verfuegbarkeit-statt-just-in-time.md", commit_or_pr: "73d2419e (main)", opened_in_session: true}
  - {claim_id: C6, source_path: "~/.claude/mail-vorgaenge.json", commit_or_pr: "n/a (lokal)", opened_in_session: true}
  - {claim_id: C7, source_path: "dev-hub mail_vorgang liste (prod, via SSH)", commit_or_pr: "n/a (Laufausgabe)", opened_in_session: true}
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
| B9 | `UUID PK` und `JSONB` in C1 widersprechen ADR-022 | C1 §5 |
| B10 | Zwei konkurrierende Vorgangsbestände existieren bereits | C6, C7 |

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
| REC-2 | Die kleine Lösung zuerst | „Gegenüber ohne Antwort seit N Tagen" rein aus Kopfdaten, ohne LLM und Vektor. Misst den Großteil des Nutzens zu einem Bruchteil der Kosten und ist die Vergleichsbasis für alles Weitere. |
| REC-3 | Vektoren erst nach Messung | Die Notwendigkeit ist an einem Fall belegt. Vor dem Einbau an einer geschichteten Stichprobe zeigen, wie oft Thread und Beteiligte allein nicht ausreichen. |
| REC-4 | Referenzmenge klein und geschichtet | Statt 500 annotierter Mails: 60–80 über die schwierigen Klassen (Weiterleitung, generischer Betreff, Ordnerwechsel, Mehrfachkopien, zwei Sachen bei einem Gegenüber). Ablage im Geltungsbereich der Datenhoheit. |
| REC-5 | Deckung ins Schema, nicht ins Dashboard | Jede aggregierte Aussage referenziert die Generation und den Deckungsstand, aus dem sie stammt. Nicht nachrüstbar. |
| REC-6 | Ablösung ist Lieferbestandteil | Eine Stufe gilt erst als fertig, wenn der abgelöste Bestand nachweislich leer oder nur noch Ausgabe ist. |
| REC-7 | Ort entscheiden, nicht ableiten | Kriterien: Wo liegen die Daten? Wer darf lesen? Was passiert bei Ausfall? Welcher Wirkungsradius bei Schreibrechten nach außen? Der Autor ist befangen — die Antwort gehört zum Owner. |
| REC-8 | Externe Zweitmeinung vor der Entscheidung | Die adversariale Analyse ist aus einer Feder; in derselben Sitzung fand ein unabhängiger Kritiker vier Fehler in einem vergleichbaren Dokument desselben Autors. |

---

## 13 Entscheidung, Kill-Gate, 30/60/90

**Vorgeschlagene Entscheidung:** Option C — Ingest- und Deckungsschicht behalten,
Vorgangs- und Arbeitsschicht neu. **Nicht sofort umsetzen:** REC-1 und REC-2 gehen voraus,
weil sie den Zuschnitt bestimmen.

**Kill-Gate.** Das Vorhaben endet bei Stufe 2 (Suche und Verlauf), wenn eines eintritt:

| Kriterium | Status | Beleg |
|---|---|---|
| (a) Zuordnungsgenauigkeit unter 80 % auf der Referenzmenge | offen | Referenzmenge existiert nicht (REC-4) |
| (b) Anteil falsch erzeugter Aufgaben über 10 % | offen | — |
| (c) REC-2 zeigt: die kleine Lösung deckt den Nutzen bereits ab | offen | nicht gebaut |
| (d) Datenhoheit lässt für zwei der drei Konten keine Verarbeitung zu | offen | Klassifikation fehlt |
| (e) Bis 2026-11-11 ist der Ort (REC-7) nicht entschieden | offen | `review_by` |

**Exception-Budget:** bis **2026-11-11** dürfen die zwei Vorgangsbestände nebeneinander
bestehen. Danach ist entweder abgelöst oder dieses Konzept auf `sunset`.

**30/60/90:**
- **30 Tage:** REC-1 gemessen, REC-2 gebaut und benutzt, externe Zweitmeinung eingearbeitet,
  Ort entschieden.
- **60 Tage:** Referenzmenge (REC-4) steht; Datenhoheits-Klassifikation je Konto und
  Nachrichtenklasse liegt vor; Deckungs-Schemaentscheidung getroffen.
- **90 Tage:** Zuordnung gemessen gegen die Referenzmenge; Entscheidung über Stufe 4+ auf
  Basis der Zahl, nicht der Absicht.
