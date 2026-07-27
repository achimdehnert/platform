---
concept_id: KONZ-platform-035
title: Deckungsausweis — Vollständigkeit von Sachverhalts-Darlegungen aus E-Mail
pipeline_status: pilot   # Owner-Entscheid 2026-07-27: angenommen; Pilot laeuft bis zur KG-Frist 2026-09-30
tier: T3
owner: Achim Dehnert
spec_refs: []          # kein Klickdummy; betrifft Werkzeug- und Antwortkonvention (begründet leer)
adr_threshold: Amendment   # ADR-284 §2 dehnt den Coverage-Contract auf Live-Antworten aus
review_by: 2026-10-27
kill_criteria: "ZWEI Gates. KG-RECALL: ein einziger False Negative auf der Referenzmenge beendet den Pilot. KG-PROCESS: ein produktiver Ausweis mit unbekannten Teilfehlern, fehlenden Pflichtfeldern oder unbegründeter Scope-Abweichung; ODER Scope-Abweichung in mehr als 1/3 der Darlegungen bis 2026-09-30. Beides -> verwerfen, nicht flicken."
superseded_by_spec: null
ai_sparring_by:
  - tool: other
    date: 2026-07-27
    role: adversarial-review
    summary: "Externe Runde 1: Verdikt ueberarbeiten. Kern: fehlender Watermark reproduziert die 'still veraltete Sicherheit' aus ADR-284 §9; §7.2-Syllogismus ueberdehnt; Kill-Gate ohne Entdeckungskanal. Tag-Tabelle im Body §14."
  - tool: other
    date: 2026-07-27
    role: adversarial-review
    summary: "Externe Runde 2: Verdikt ueberarbeiten. Kern: Taxonomie vermischt Ursachen, Beobachtbarkeit und Urteilsgrenzen; Erfassungs-/Konsistenzklasse fehlt; Kill-Gate braucht Referenzmenge statt entdeckter Auslassungen. Tag-Tabelle im Body §14."
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-284-mail-intelligence-action-system.md, commit_or_pr: "2c3b2f11/main", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-286-mail-agent-crypto-shredding-derived-index.md, commit_or_pr: "#1488", opened_in_session: true}
  - {claim_id: C3, source_path: tools/mail_agent/read_mail.py, commit_or_pr: "#1487", opened_in_session: true}
  - {claim_id: C4, source_path: tools/mail_agent/graph_mail.py, commit_or_pr: "#1485", opened_in_session: true}
  - {claim_id: C5, source_path: tools/mail_agent/vorgang.py, commit_or_pr: "#1490", opened_in_session: true}
  - {claim_id: C6, source_path: .windsurf/workflows/mailcheck.md, commit_or_pr: "#1485", opened_in_session: true}
  - {claim_id: C7, source_path: "session-run", commit_or_pr: "vorgang.py --topic SUBJECT 2026-07-27", opened_in_session: true}
  - {claim_id: C8, source_path: "~/shared/adr-handoff-KONZ-platform-035-2026-07-27.md", commit_or_pr: "externe Runden 1+2, 2026-07-27", opened_in_session: true}
created: 2026-07-27
---

# KONZ-platform-035: Deckungsausweis

**Tier T3.** Die Konvention wirkt über die org-weit verteilten Mail-Skills in alle Repos, und ein
Pflicht-Scope über *alle* Ordner verschiebt den Datenschutz-Perimeter. Beides sind T3-Trigger.
Der Agenten-Fan-out entfiel zugunsten **zweier externer Zweitmeinungen** verschiedener Anbieter
(§14) — beide Verdikt „überarbeiten", beide eingearbeitet.

## Kernthese

**Vollständigkeit ist nicht garantierbar, Deckung ist ausweisbar** — deshalb trägt jede
Sachverhalts-Darlegung ihren Deckungsausweis, und ohne ihn gilt sie als unvollständig.

---

## 1 Executive Summary

Am 2026-07-27 sind an einem Tag **drei** Sachverhalts-Darlegungen unvollständig gewesen, jede aus
einem anderen Grund. Keiner davon war Nachlässigkeit; jeder war eine Abfrage, die plausibel
aussah und weniger maß, als sie zu messen schien. Der teuerste Fall führte dazu, dass eine
betroffene Person eine **zweite** Authentifizierungsanfrage in einem laufenden Art.-17-Verfahren
erhielt.

**Vorschlag:** Jede Sachverhalts-Darlegung trägt einen maschinell erzeugten **Deckungsausweis** —
welche Frage, welcher Anlass, welche Konten von wie vielen, wie viele Ordner, **zu welchem
Zeitpunkt und Quell-Watermark**, welche Retrievalpfade mit je eigener Trefferzahl, welche
Teilfehler aufgetreten sind, und ausdrücklich: **was nicht gedeckt war**.

**Der Kern ist eine Umkehrung der Beweislast.** Heute behauptet die Antwort implizit
Vollständigkeit und niemand kann sie prüfen. Künftig weist sie ihre Grenzen aus.

**Zwei Dinge, die dieses Konzept nach externer Kritik ausdrücklich *nicht* mehr behauptet:**
Es beweist keine Unmöglichkeit (§7.2), und es misst seine Wirksamkeit nicht an entdeckten
Auslassungen allein, sondern an einer **Referenzmenge mit bekannter Grundgesamtheit** (§13).

---

## 2 Scope & Evidenzbasis

**Geöffnet in dieser Session** (C1–C8): ADR-284 (Coverage-Contract, Scope-Tabelle), ADR-286 §4.9,
die drei Mail-Werkzeuge samt der heute an ihnen vorgenommenen Änderungen, der `/mailcheck`-Skill,
ein Live-Lauf der ordnerübergreifenden Suche, und die beiden externen Reviews.

**Nicht geöffnet, deshalb Hypothese:** das Verhalten auf Postfächern, die deutlich größer sind als
die gemessenen (46.065 Nachrichten / 110 Ordner), und ob die Laufzeitmessung auf anderen Servern
trägt.

**Außerhalb:** der Index aus ADR-284 Phase 1 (existiert nicht), semantische Relevanzbestimmung
(§7.2), und jede Persistenz — dieses Konzept fügt kein speicherndes Element hinzu.

---

## 3 Infrastruktur-Fit

| Baustein | Ort | Stand |
|---|---|---|
| Filterfreie Ordner-Aufzählung | `graph_mail --find --all` (C4) | vorhanden, seit #1485 |
| Laute Warnung bei stiller Verwerfung | `graph_mail._match_messages` (C4) | vorhanden, seit #1485 |
| Nenner in jeder Liste | `read_mail._bilanz` (C3) | vorhanden, seit #1487 |
| Ordnerübergreifende Sachsuche | `vorgang.py --topic` (C5) | vorhanden, seit #1490 |
| Warnung zur Trefferqualität | `vorgang.such_hinweis` (C5) | vorhanden, seit #1490 |
| **Gemeinsame Deckungsaussage** | — | **fehlt** |
| **Unabhängige Zweitzählung** | — | **fehlt** (§12 REC-9) |
| **Referenzmenge mit bekannter Grundgesamtheit** | — | **fehlt** (§13 KG-RECALL) |

**Root-Cause-Prüfung.** ADR-284 §2 Nr. 1 führt **bereits** einen Coverage-Contract — „100 % der
für den Connector sichtbaren Nachrichten in explizit benannten Accounts + Ordner-Scope **zu einem
ausgewiesenen Quell-Watermark**". §3 bindet ihn aber auf **Phase 1 = den Index**; die Live-Antwort
fällt in keine Phase.

**Der Vertrag existiert, er bindet nur das Falsche.** Ein Amendment ist nötig, kein Neubau.

*Nachtrag nach externer Kritik:* Die erste Fassung dieses Konzepts zitierte genau diesen Satz und
ließ den **Watermark** dann selbst weg — und hätte damit die „still veraltete Sicherheit"
reproduziert, die ADR-284 §9 als schlimmer als keine bezeichnet. Beide Reviewer haben das
unabhängig gefunden.

---

## 4 Steelman

Die stärkste Fassung argumentiert nicht mit Ordnung, sondern mit **Haftung**.

Wer eine Auskunft gibt, haftet für ihre Richtigkeit. Eine Auskunft aus unvollständigem Material
ist falsch, auch wenn jeder einzelne Satz zutrifft. Das ist der Unterschied zwischen einem Irrtum
und einem Fehler: Der Irrtum ist eine falsche Aussage, der Fehler ein Verfahren, das falsche
Aussagen erzeugt, ohne dass es auffällt.

Der Ausweis verwandelt eine **unprüfbare Zusicherung** in eine **nachrechenbare Angabe**. Zwei
Dinge folgen daraus, die keine Sorgfaltsermahnung leistet: Eine Lücke wird **sichtbar, ohne dass
jemand sie sucht**, und die Aussage wird **fremdprüfbar** — ein Dritter kann den Deckungsbereich
beurteilen, ohne die Arbeit zu wiederholen.

Und es ist wohlfeil: Die Werkzeuge messen die Zahlen ohnehin. Heute werfen sie sie weg.

---

## 5 Konzeptdefinition

### 5.1 Fünf Schichten, nicht vier gleichrangige Klassen

Die erste Fassung führte vier gleichrangige „Lücken". Beide Reviewer haben unabhängig
festgestellt, dass das **Ursachen, Beobachtbarkeitsmängel und Urteilsgrenzen auf eine Ebene**
mischt. Korrigiert zu einem Schichtenmodell — die Schichten dürfen sich überlagern, und der Text
behauptet keine Trennschärfe, die im Betrieb nicht besteht.

| # | Schicht | Was schiefgeht | Realfall / Beispiel | mechanisch lösbar |
|---|---|---|---|---|
| **L1** | **Suchraum** | falsche oder zu wenige Konten, Ordner, Zeitfenster | Darlegung aus INBOX allein — 3 von 11 Nachrichten, drei davon im Papierkorb (C7) | **ja** |
| **L2** | **Retrieval** | ungeeignete Felder, Normalisierung, Kriterien | Platzhalter `--from "@"` verwarf 21 von 34 (X.500-DN ohne `@`) (C4) | **ja** |
| **L3** | **Erfassung / Konsistenz** | Pagination, Timeout, Berechtigung, Connector-Sichtbarkeit, **nicht atomarer Scan** | ein Lauf über 110 Ordner dauert 10–77 s; das Postfach ändert sich dabei (C5) | **ja** |
| **L4** | **Beobachtbarkeit** | das Ergebnis wirkt vollständig, weil Nenner, Fehlerliste oder Trunkierungsangabe fehlen | `--list N` gab N Zeilen und sonst nichts (C3) | **ja** |
| **L5** | **Relevanz / Zuordnung** | Kandidat gefunden, aber nicht richtig eingeordnet | dieselbe Nachricht gehört zu zwei Vorgängen (ADR-286 §4.9) | **nein** — §7.2 |

**L1–L4 sind Verfahrensfehler** und mechanisierbar. **L5 ist ein Urteilsproblem** und bleibt beim
Menschen. Der eigentliche Beitrag ist dieser Schnitt, nicht die Feingliederung darüber.

**L3 war in der ersten Fassung nicht vorhanden** und ist die wichtigste Ergänzung: Ein Ordner mit
Timeout, abgebrochener Pagination oder Berechtigungsfehler darf **nicht** als „durchsucht" zählen —
sonst ist der Nenner eine Lüge mit Nachkommastellen.

### 5.2 Der Deckungsausweis

Maschinell erzeugt, **vor** der Trefferliste — nicht als Fußnote, weil Fußnoten nach dreimal Lesen
unsichtbar werden.

| Feld | Warum |
|---|---|
| `frage` | Vollständigkeit ist ohne Frage undefiniert (§7.1) |
| `anlass` | Die DSGVO-Begründung hängt an Anlassbezogenheit (§7.4) — ohne Feld ist sie unprüfbar |
| `konten_vorhanden` / `konten_durchsucht` | L1 eine Ebene über den Ordnern; ohne Verhältnis bleibt die Konten-Auswahl der stille Scope |
| `ordner_vorhanden` / `ordner_durchsucht` | der Nenner |
| `scan_started_at` / `scan_finished_at` / `source_watermark` | **L3.** Bei 10–77 s Laufzeit ist der Postfachzustand kein Punkt, sondern ein Intervall |
| `retrievalpfade: {pfad: treffer}` | ein Pfad mit **0** Treffern ist ein Befund — im Gesamtergebnis unsichtbar |
| `ordner_fehlgeschlagen` / `timeouts` / `berechtigungsfehler` / `seiten_unvollstaendig` | **L3.** „durchsucht" ist ohne diese Felder semantisch unbestimmt |
| `geprueft` / `vorhanden` | Trunkierung |
| `nicht_gedeckt: [{was, grund}]` | die eigentliche Aussage — strukturiert, nicht als Freitext |
| `query_fingerprint` / `tool_version` / `format_version` | Reproduzierbarkeit; ein Ausweis ohne sie ist später nicht mit anderen vergleichbar |
| `erzeuger: maschinell \| manuell` | Handbetrieb bleibt zulässig, aber unterscheidbar |

**Primär ist ein versioniertes Objekt `deckungsausweis.v1`, sekundär dessen Markdown-Rendering.**
Alle Skills nutzen denselben Renderer. Ein reiner Textblock über fünf Skills hinweg wäre genau die
Doppelquelle, die die SSoT-Konvention verbietet — und er wäre 2028 auseinandergelaufen.

### 5.3 Die fünf Regeln

**R-1 — Pflicht-Scope ist alles, auf zwei Ebenen.**
*Ordner:* alle Ordner eines benannten Kontos, **einschließlich Gesendet und Papierkorb**.
*Konten:* Default sind **alle drei Postfächer**. Der Ausschluss eines Kontos ist eine benannte,
begründete Abweichung im Feld `nicht_gedeckt` — nie ein stiller Default.
Belegt durch L1: drei der elf Nachrichten lagen im Papierkorb, und gelöscht heißt dort nicht
irrelevant, sondern meistens *erledigt* — also gerade die Information über den Stand.

**R-2 — Mehrere verschiedenartige Retrievalpfade**, nicht mehrere Parameter derselben
Implementierung. Zwei Felder desselben Client-Filters teilen dessen Blindstellen. Der
aussagekräftige Kontrast ist **Client-Filter gegen Server-Suche** (`IMAP SEARCH` / Graph
`$search`) — zwei Implementierungen. Der Wert liegt in der **Divergenz**: Findet ein Pfad nichts,
wo ein anderer trifft, ist das ein Befund über die Abfrage.

**R-3 — Kalibrierung je Pfad, nicht je Lauf.** Eine bekannte Nachricht belegt **einen** Pfad. Eine
Vollständigkeitsaussage ist nur zulässig, wenn **alle im Lauf verwendeten Pfade** erfolgreich
kalibriert wurden. Erscheint das Kalibrierobjekt nicht, ist **nicht die Menge leer, sondern die
Abfrage kaputt**.

**R-4 — Über-Einschluss vor Unter-Einschluss.** Die Kosten sind asymmetrisch (§7.3).

**R-5 — Maschinell erzeugt; Handbetrieb ist gesperrt für Vollständigkeitsaussagen.** Ein manueller
Ausweis trägt `erzeuger: manuell`, `fallback_grund` und den Satz **„Dieser Ausweis erlaubt keine
Vollständigkeitsaussage."** Ohne diese Sperre wird der Ausnahmeweg bei jedem Werkzeugproblem zum
bevorzugten Pfad — und entwertet genau die Nachprüfbarkeit, auf der alles beruht.

---

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus

**Wo entsteht eine Doppelquelle?** Der Ausweis speichert nichts und ist so flüchtig wie die
Antwort. *Aber:* Sobald jemand ihn archiviert, entsteht ein Artefakt mit Aussagekraft über einen
Zeitpunkt — deshalb sind `source_watermark`, `tool_version` und `query_fingerprint` **Pflicht**,
nicht Kür (§5.2). Die Persistenz-Entscheidung selbst bleibt vertagt (REC-6).

**Wo wird SSoT nur behauptet?** Beim Wort „alle". Der Ausweis nennt Konten deshalb **namentlich
und als Verhältnis**, nicht als Menge.

**Wo wird ein Werkzeug faktisch zur Boundary?** Wird der Ausweis Voraussetzung, ist das erzeugende
Werkzeug kritischer Pfad. → R-5 lässt Handbetrieb zu, aber **ohne** Vollständigkeitsaussage.

**Wo manuelle Pflicht ohne Enforcement?** *Hier hat die externe Kritik das Konzept korrigiert —
zu seinen Gunsten.* Die erste Fassung erklärte pauschal „Review-Gate, kein Exit-Code". Das war zu
bescheiden: Für R-1 **ist** ein Exit-Code baubar. Prüfbar sind

```
erzeuger == "maschinell"
UND ordner_durchsucht == ordner_vorhanden ODER nicht_gedeckt nichtleer mit Grund
UND konten_durchsucht == konten_vorhanden ODER nicht_gedeckt nichtleer mit Grund
UND ordner_fehlgeschlagen == 0 ODER als nicht_gedeckt ausgewiesen
UND alle verwendeten Pfade kalibriert
```

Nicht maschinell prüfbar bleiben nur **Angemessenheit der Frage** und **Relevanz** — und beide
liegen ohnehin beim Menschen. Der ehrliche Satz lautet also: **Exit-Code für das Verfahren,
Urteil für den Inhalt.**

**Wo ist „sichtbar machen" schwächer als „verhindern"?** Beim Scope. Deshalb ist R-1 als Pflicht
formuliert und das Weglassen als begründungspflichtige Abweichung — plus einer Schwelle (§13),
weil eine Abweichung ohne Konsequenz nur eine Statistik ist.

**Wo kann man formal erfüllen und praktisch umgehen?** Durch einen engen, korrekt ausgewiesenen
Scope. Die erste Fassung hatte dagegen kein Mittel. Jetzt zwei: die **Abweichungsschwelle** (>1/3
der Darlegungen ⇒ Pflicht-Scope gilt als umgangen) und **KG-RECALL**, das auf einer Referenzmenge
misst und von der Scope-Wahl im Produktivbetrieb unabhängig ist.

**Wo wird ein bestehendes Problem verschlimmert?** Laufzeit (R2 in §11) und Datenschutz: Ein
Pflicht-Scope **berührt mehr personenbezogene Daten**. → §7.4.

### 6.2 Maintainer-2028

Der Ausweis dokumentiert **nicht Arbeit**, sondern macht **eine Fehlerklasse unmöglich** — die
stille Teilmenge, die wie eine Vollmenge aussieht. Wird er zur Pflichtübung ohne Bezug zur Frage,
ist er zu **streichen**, nicht zu erweitern. Die Frage an ihn lautet nie „ist er da", sondern
„hätte er den Fehler gefangen".

Und: Die fünf Schichten aus §5.1 sind das Denkgerüst. Wer etwas verbessern will, sollte prüfen,
**welche** er adressiert. Ein Vorschlag ohne Zuordnung löst vermutlich ein anderes Problem.

---

## 7 Deep-Dive

### 7.1 Vollständigkeit ist relativ zu einer Frage

„Alle relevanten Mails" ist ohne Frage nicht definiert. Dieselbe Nachricht ist relevant für *„was
habe ich zugesagt"* und irrelevant für *„wer wartet auf Rückmeldung"*. Relevanz ist keine
Eigenschaft der Nachricht, sondern eine **Relation zwischen Nachricht und Frage**.

Daraus folgt der Aufbau des Ausweises: Er muss die **Frage mitführen**. Ein Ausweis ohne Frage ist
so leer wie ein Messergebnis ohne Einheit.

### 7.2 Die Garantiegrenze — korrigiert nach externer Kritik

Die erste Fassung formulierte einen **Unmöglichkeitsbeweis**: vollständige Relevanz erfordere
vollständige Inhaltskenntnis, diese sei verwehrt, also sei vollständige Relevanz unmöglich.

**Beide Reviewer haben denselben inneren Widerspruch gefunden**, und sie haben recht: §7.4 Nr. 1
verteidigt die **anlassbezogene** Lektüre ausdrücklich als zulässig. Dasselbe Argument, das den
Voll-Scope rechtfertigt, erlaubt also auch das Lesen der Treffer. Der Syllogismus trug nicht.

**Korrekte Formulierung — enger im Quantor, unverändert in der Konsequenz:**

> Eine belastbare **Garantie**, für **beliebige** Sachverhalte sämtliche relevanten Nachrichten zu
> erfassen, ist ohne vollständige **systematische** Inhaltsauswertung nicht erreichbar. Diese
> Auswertung ist durch die Bedingung ausgeschlossen, unter der die Datenschutz-Folgenabschätzung
> freigegeben wurde.

Drei Ebenen sind deshalb getrennt zu halten:

| Ebene | Wer | Was garantiert wird |
|---|---|---|
| **Kandidatenermittlung** | Maschine | Deckung: welcher Bereich vollständig untersucht wurde |
| **Relevanzentscheidung** | Mensch | keine Garantie — Urteil |
| **Garantieanspruch des Gesamtergebnisses** | — | ausdrücklich **kein** Vollständigkeitsversprechen |

Die praktische Konsequenz ist dieselbe wie vorher — nur ruht sie jetzt auf einem stehenden
Entscheid („Relevanz bleibt beim Menschen", draft-first) plus einer Rechtsbedingung, statt auf
einem Beweis, der den Angriff einlud, den er abwehren sollte.

### 7.3 Die Kostenasymmetrie

| Fehler | Kosten |
|---|---|
| Eine Nachricht **zu viel** | Aufmerksamkeit für Sekunden |
| Eine Nachricht **zu wenig** | falsche Auskunft, verschenkte Frist, doppelte Handlung gegenüber Dritten — am 2026-07-27 real eingetreten |

Das Verhältnis ist um Größenordnungen asymmetrisch. R-4 ist deshalb keine Vorsichtsregel, sondern
die Konsequenz aus dieser Tabelle.

### 7.4 Der Datenschutz-Einwand gegen den eigenen Vorschlag

Ein Pflicht-Scope **liest mehr**. Drei Entkräftungen:

1. **Anlassbezogen, nicht systematisch** — läuft nur auf eine konkrete Frage.
2. **Nichts wird gespeichert** — kein abgeleitetes Artefakt nach ADR-286 §4.4.
3. **Der Zugriff bestand ohnehin** — es wird nur vollständiger gelesen, was ohnehin im eigenen
   Postfach liegt.

**Der verbleibende Rest ist jetzt operationalisiert, nicht nur benannt.** Die erste Fassung nannte
Häufigkeit als Risiko und ließ es dabei — ein externer Reviewer hat zu Recht darauf gezeigt, dass
die gesamte Rechtfertigung daran hängt. Deshalb:

- Der Ausweis trägt ein Pflichtfeld `anlass`. Ohne Anlass kein Lauf.
- **Eine Wiederholung derselben Frage über denselben Scope innerhalb von 24 Stunden ohne neuen
  Anlass ist keine anlassbezogene Verarbeitung mehr** und wird abgelehnt, nicht ausgewiesen.
- Die Regel steht **einmal** im Amendment, nicht in drei Skill-Dateien (§12 REC-5).

### 7.5 Warum ein Index das Problem nicht erledigt

Ein Index deckt, **was er indexiert hat** — die Scope-Frage stellt sich dort identisch, nur früher
und mit dem Zusatzrisiko, dass eine veraltete Deckung wie eine aktuelle aussieht. ADR-284 §9 sagt
es selbst: *„Ein still veralteter Index (falsche 100-%-Sicherheit) ist schlimmer als keiner."*

**Erhaltungs-Kriterium für den Fall, dass Phase 1 gebaut wird** (ergänzt nach externer Kritik):
Der Index-Ausweis muss **mindestens** dieselben Felder tragen wie der Live-Ausweis, plus den
Watermark des letzten erfolgreichen Sync. Ein Index-Ausweis ohne Staleness-Angabe ist eine
Rückstufung gegenüber dem Live-Fall, nicht ein Fortschritt.

---

## 8 Alternativen

| # | Alternative | Bewertung |
|---|---|---|
| 1 | **Freitext-Vorbehalt** an jede Antwort | Nicht prüfbar, deshalb wirkungslos. Die heutigen Fehlschläge hätten ihn getragen und wären trotzdem falsch gewesen: Sie hatten keine fehlende Warnung, sie hatten falsche Zahlen. |
| 2 | **Erst den Index bauen** | Löst es nicht (§7.5) und verschiebt es um Monate — in genau dem Zeitraum, in dem die Fehler auftreten. |
| 3 | **Nur Werkzeuge härten, keine Konvention** | Wurde heute gemacht und **reicht nicht**: Das dritte Versagen geschah *nach* der Härtung, mit den gehärteten Werkzeugen, weil niemand verpflichtet war, sie vollständig einzusetzen. Der Beleg gegen diese Alternative ist derselbe Tag. |
| 4 | **Vier-Augen-Prinzip** statt Ausweis | Ein zweiter Mensch mit derselben Abfrage sieht dieselbe Teilmenge. Gegen L2 wirkungslos. |
| 5 | **Seed-and-Expand statt Voll-Scope** | Als **Ersatz** verworfen: eine strukturell unverbundene Nachricht bleibt unentdeckt. Als **zusätzlicher Retrievalpfad** mit eigener Trefferzahl aufgenommen (§9.6) — dort ist sie wertvoll. |

---

## 9 Out-of-the-Box

**9.1 — Negativ-Nachweis statt Positiv-Behauptung.** Der Ausweis könnte mit **„das habe ich nicht
durchsucht"** beginnen. Eine Aufzählung von Lücken lässt sich nicht überlesen wie eine Zahl. Im
Pilot gegen die Standardform messen.

**9.2 — Server-Zweitzählung als unabhängiger Nenner.** `IMAP STATUS (MESSAGES)` bzw. Graph
`totalItemCount` je Ordner als vom Suchwerkzeug **unabhängige** Quelle für „vorhanden". Weicht die
eigene Enumeration ab, bricht der Lauf laut ab. Das bricht die Selbstreferenz des Nenners: Bisher
stammten Zähler und Nenner aus derselben Aufzählung, nicht-enumerierte Ordner blieben also
**unsichtbar-unsichtbar**. → REC-9.

**9.3 — Divergenz zweier Implementierungen.** Client-Filter gegen Server-Suche, nur die Differenz
melden. Stimmen beide überein, ist das ein starkes Deckungsindiz; weichen sie ab, ist die
Abweichung der interessanteste Teil des Ergebnisses. Lagert zudem Laufzeit auf den Server aus.

**9.4 — Der Ausweis als Artefakt am Vorgang.** Für regulierte Vorgänge erheblich, erzeugt aber ein
persistentes Artefakt mit Personenbezug → eigener Entscheid (REC-6).

**9.5 — Kalibrierung als stehender Kanarienvogel je Pfad.** Fehlt das Kalibrierobjekt, bricht der
Lauf ab, statt ein plausibles Teilergebnis zu liefern. Der einzige Vorschlag, der L2
**verhindert** statt sie sichtbar zu machen.

**9.6 — Seed-and-Expand als ergänzender Pfad.** Von einer sicher bekannten Nachricht aus
deterministisch über Message-ID, Thread-Beziehungen, Beteiligte und zitierte Referenzen erweitern,
bis keine neuen Verbindungen entstehen. Billig, datensparsam, mit nachvollziehbarem
Abschlusszustand — aber blind für strukturell unverbundene Nachrichten. Deshalb **Pfad, nicht
Ersatz**.

---

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| B1 | Der Coverage-Contract aus ADR-284 §2 bindet nur Phase 1; die Live-Antwort ist ungeregelt | E1 (C1) |
| B2 | Alle drei Fehlschläge traten in Live-Antworten auf — der Index existiert nicht | E3 (C3/C4/C7) |
| B3 | Ein Platzhalter-Filter verwarf 21 von 34 gesendeten Nachrichten still | E3 (C4) |
| B4 | Eine Trefferliste ohne Nenner ist von einer Vollerhebung nicht unterscheidbar | E3 (C3) |
| B5 | Ein Sachverhalt verteilte sich über **fünf** Ordner inkl. Papierkorb; die Darlegung aus INBOX zeigte 3 von 11 | E3 (C7) |
| B6 | Die Feldwahl entscheidet mehr als der Suchbegriff: 0 / 327 / 678 Treffer für denselben Term | E3 (C5) |
| B7 | Gehärtete Werkzeuge allein genügen nicht — B5 geschah **nach** der Härtung | E3 (C3/C4 vs. C7) |
| B8 | Eine ordnerübergreifende Suche dauert 10–77 s; der Postfachzustand ist also ein **Intervall**, kein Punkt | E3 (C5) |
| B9 | Die erste Fassung zitierte den Coverage-Contract und ließ dessen Watermark weg — beide Reviewer fanden es unabhängig | E4 (C8) |
| B10 | Die erste Fassung widersprach sich selbst: §7.2 behauptete Unmöglichkeit, §7.4 erlaubte anlassbezogene Lektüre | E4 (C8) |

---

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | Der Ausweis wird Formalie: vorhanden, ungelesen, falsche Zahlen | Exit-Code für das Verfahren (§6.1) + KG-RECALL misst auf einer Referenzmenge, nicht an Ausweis-Präsenz |
| R2 | Laufzeit macht den Pflicht-Scope unattraktiv, er wird faktisch umgangen | Kosten ausweisen statt Scope kürzen; **Schwelle >1/3 Abweichungen ⇒ gescheitert** (§13); Server-Suche entlastet (§9.3) |
| R3 | Häufige Vollsuchen nähern sich dem systematischen Lesen an | Pflichtfeld `anlass`; Wiederholung derselben Frage über denselben Scope binnen 24 h ohne neuen Anlass wird **abgelehnt** (§7.4) |
| R4 | Handbetrieb wird vom Ausnahme- zum Hauptpfad | R-5: manueller Ausweis trägt den Sperrsatz gegen Vollständigkeitsaussagen |
| R5 | Scheinsicherheit — der Ausweis suggeriert Vollständigkeit, belegt aber nur Deckung | §7.2 ist Pflichtbestandteil; die Garantiegrenze steht **im Ausweis-Text**, nicht nur im Konzept |

---

## 12 Empfehlungen

| # | Empfehlung | Konkret |
|---|---|---|
| REC-1 | Ausweis als **versioniertes Objekt**, Markdown sekundär | `deckungsausweis(frage, anlass, konten_vorhanden, konten_durchsucht, ordner_vorhanden, ordner_durchsucht, scan_started_at, scan_finished_at, source_watermark, retrievalpfade: dict[str,int], kriterien_wortlaut: dict[str,str], ordner_fehlgeschlagen, timeouts, berechtigungsfehler, seiten_unvollstaendig, nicht_gedeckt: list[dict], query_fingerprint, tool_version, format_version=1, erzeuger) -> DeckungsausweisV1` in `tools/mail_agent/vorgang.py`; ein Renderer für alle Skills |
| REC-2 | Ausgabe **vor** der Trefferliste | in `cmd_topic` und `cmd_show` |
| REC-3 | Zweiter Retrievalpfad als **andere Implementierung** | Client-Filter gegen `IMAP SEARCH` / Graph `$search`, getrennte Trefferzahl, Divergenz-Triage |
| REC-4 | Kalibrierung **je Pfad** | `vorgang.py --calibrate` gibt je Retrievalpfad einen Status aus; Vollständigkeitsaussage nur bei allen verwendeten Pfaden grün |
| REC-5 | Pflicht **einmal** verankern | Der Pflicht-Wortlaut steht im Amendment zu ADR-284 §2. `mailcheck.md`, `briefing.md`, `iil-mail.md` erhalten nur einen Verweis-Satz mit Referenz — **kein** eigener Wortlaut (SSoT) |
| REC-6 | Persistenz **nicht** im MVC | Der Ausweis als Vorgangs-Notiz ist ein eigener Entscheid mit Personenbezug — vertagt, nicht vergessen |
| REC-7 | ADR-284 amendieren | §2 Nr. 1 erweitern: Der Coverage-Contract gilt auch für Live-Antworten |
| REC-8 | Exit-Code für das Verfahren | Hook prüft die Bedingungskette aus §6.1 — nicht die Anwesenheit des Ausweises |
| REC-9 | Unabhängige Zweitzählung | `vorgang.py --verify-denominator`: eigene Enumeration gegen `STATUS (MESSAGES)` / `totalItemCount`, lauter Abbruch außerhalb definierter Toleranz |
| REC-10 | Referenzmenge aufbauen | `tests/fixtures/mail_coverage_cases.yaml` + Testpostfach mit bekannter Grundgesamtheit: Papierkorb, X.500-Absender, fehlende Betreffs, doppelte Threads, Pagination, während des Laufs eintreffende Nachrichten |

---

## 13 Entscheidung + Kill-Gate

**Entscheidung:** Konzept **annehmen und pilotieren** — REC-1 bis REC-5 sowie REC-8 bis REC-10
umsetzen, REC-6 vertagen, REC-7 als Amendment nachziehen.

### Zwei Gates statt einem

Die erste Fassung maß **nur entdeckte** Auslassungen. Beide Reviewer haben unabhängig
festgestellt, dass ein Bestehen dann vor allem geringe Entdeckungswahrscheinlichkeit belegt.
Deshalb getrennt:

**KG-RECALL (Wirksamkeit).** `tests/mail_agent/test_deckungsausweis_recall.py` läuft gegen eine
**Referenzmenge mit bekannter Grundgesamtheit** (REC-10). **Ein einziger False Negative beendet
den Pilot.** Das ist die einzige Messung, die von der Scope-Wahl im Produktivbetrieb unabhängig
ist.

**KG-PROCESS (Verfahren).** Gescheitert bei
- einem produktiven Ausweis mit **unbekannten Teilfehlern**, fehlenden Pflichtfeldern oder
  unbegründeter Scope-Abweichung; **oder**
- einer Scope-Abweichung in **mehr als 1/3** der Darlegungen bis 2026-09-30. Die Zahl ist hier
  fixiert und wird **nicht** im Pilot nachverhandelt — sonst wandert sie mit dem Ergebnis.

**Produktiv entdeckte Auslassungen** bleiben ein zusätzliches Stoppsignal, sind aber nicht mehr
die einzige Wirksamkeitsmessung.

**Exception-Budget:** einmalige Verlängerung bis **2026-10-31**, danach ohne weitere.

**Owner-Entscheid 2026-07-27: angenommen.** `pipeline_status` auf `pilot`. Die Umsetzung
läuft in platform#1492 (REC-1/2/3/4/7/9); REC-6 bleibt vertagt, REC-10 steht aus.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Ausweis maschinell erzeugt, als Objekt `v1`, vor der Trefferliste | erfüllt | `deckungsausweis.py`, `vorgang.py:cmd_topic` (#1492) |
| K2 Pflicht-Scope auf **beiden** Ebenen: alle Ordner **und** alle Konten, Abweichung begründet | teilweise | Konten werden gezählt und Abweichungen begründet; ein Lauf über *mehrere* Konten fehlt (#1492) |
| K3 Mindestens zwei **verschiedenartige** Retrievalpfade mit getrennter Trefferzahl | erfüllt | `pfad_server_suche` / `pfad_client_filter`, `divergenz()` (#1492) |
| K4 Kalibrierung je Pfad; Vollständigkeitsaussage nur bei allen Pfaden grün | erfüllt | `kalibriere_pfade()`, `unkalibrierte_pfade()` (#1492) |
| K5 **KG-RECALL** grün auf der Referenzmenge (0 False Negatives) | offen | REC-10 nicht gebaut — ohne Referenzmenge nicht messbar |
| K6 Garantiegrenze (§7.2) steht im Ausweis-Text, nicht nur im Konzept | offen | — |
| K7 `source_watermark`, `scan_started_at`/`_finished_at`, `tool_version`, `query_fingerprint` in jedem Ausweis | erfüllt | Pflichtfelder in `Ausweis` (#1492) |
| K8 Exit-Code-Hook prüft die Bedingungskette aus §6.1 | offen | REC-8 nicht gebaut |
| K9 Scope-Abweichung ≤ 1/3 der Darlegungen | offen | Pilot läuft erst an — Messung ab jetzt bis 2026-09-30 |
| K10 Unabhängige Zweitzählung läuft und bricht bei Abweichung ab | teilweise | `nenner_pruefen()` läuft und sperrt die Aussage; ein *Abbruch* ist es nicht (#1492) |

### 30/60/90

**Bis Tag 30:** REC-1 bis REC-3 und REC-10 gebaut — die Referenzmenge zuerst, weil ohne sie
KG-RECALL nicht messbar ist. Erste zehn realen Darlegungen mit Ausweis. K1–K3, K7.

**Bis Tag 60:** REC-4, REC-5, REC-8, REC-9 live. Erste KG-RECALL-Messung. K4, K5, K6, K8, K10.

**Bis Tag 90:** Entscheid über REC-6 (Persistenz) und über die Darstellungsform aus §9.1. K9
abschließend — oder Sunset nach Kill-Gate.

---

## 14 Externe Zweitmeinungen — Rückfluss-Bilanz

Zwei unabhängige externe Runden verschiedener Anbieter am 2026-07-27, beide Verdikt
**„überarbeiten"** (kein Fall für Ablehnung). Die Runden sahen einander nicht.

**Bemerkenswert: kein einziger Befund wurde als `[missversteht-Kontext]` getaggt.** Bei zwei
unabhängigen Anbietern spricht das dafür, dass das Briefing den Kontext tatsächlich mitgeliefert
hat — und es heißt zugleich, dass die Kritik nicht auf Unkenntnis beruht.

| Befund-Cluster | Verdikt | Aktion in dieser Fassung |
|---|---|---|
| §7.2-Syllogismus überdehnt; widerspricht §7.4 Nr. 1 (**beide Runden**) | [valid] | §7.2 neu gefasst: engerer Quantor, Drei-Ebenen-Trennung, kein Beweis mehr |
| Taxonomie vermischt Ursachen, Beobachtbarkeit, Urteilsgrenzen; Erfassungsklasse fehlt (**beide**) | [valid] | §5.1 auf Schichtenmodell L1–L5; L3 Erfassung/Konsistenz neu |
| Watermark fehlt, obwohl ADR-284 §2 ihn zum Contract zählt (**beide**) | [valid] | Pflichtfelder in §5.2, REC-1, K7 |
| Kill-Gate ohne Entdeckungskanal misst Entdeckungswahrscheinlichkeit (**beide**) | [valid] | Aufteilung KG-RECALL / KG-PROCESS; Referenzmenge REC-10 |
| „Außerhalb = kein Fehlschlag" macht Scope-Verengung folgenlos (**beide**) | [valid] | Schwelle >1/3 fixiert; KG-RECALL als scope-unabhängige Messung |
| Konten-Ebene ungeregelt — L1 kehrt eine Ebene höher wieder (**beide**) | [valid] | R-1 zweistufig; `konten_vorhanden`/`konten_durchsucht` |
| Nenner selbstreferenziell; „durchsucht" bei Teilfehlern unbestimmt (**beide**) | [valid] | REC-9 Server-Zweitzählung; Fehlerfelder in §5.2 |
| REC-5 verletzt die eigene SSoT-Konvention (**beide**) | [valid] | Pflicht einmal im Amendment; versioniertes Objekt statt Textblock |
| Zwei Kriterien ≠ zwei unabhängige Wege (**beide**) | [valid] | R-2 auf verschiedenartige **Implementierungen** |
| Exit-Code ist baubar, das Konzept verkauft sich zu schwach | [valid] | §6.1 mit ausformulierter Bedingungskette; REC-8 |
| Kalibrierung belegt einen Pfad, nicht das Verfahren | [valid] | R-3 und REC-4 je Pfad |
| Häufigkeit nicht operationalisiert, obwohl die DSFA-Begründung daran hängt | [valid] | Feld `anlass`; 24-Stunden-Regel in §7.4 |
| Handbetrieb wird zum Hauptpfad | [valid] | R-5 mit Sperrsatz |
| Archivierter Ausweis ohne Version/Fingerprint nicht reproduzierbar | [valid] | `tool_version`, `query_fingerprint`, `format_version` |
| §7.5 ohne Erhaltungs-Kriterium für den Index-Fall | [valid] | Kriterium ergänzt |
| Seed-and-Expand als ergänzender Pfad | [valid, vertagt] | §9.6 und Alternative 5 — nicht im MVC |
| Stichproben-Inhaltsaudit zur Messung von L5 | [out-of-scope] | Der Reviewer verwirft ihn selbst: kollidiert mit der DSFA-Bedingung. Übernommen als Begründung, warum L5 unvermessen bleibt |
| Verbot wiederholter Vollsuchen **in den drei Skill-Dateien** | [valid, angepasst] | Regel ja — aber im Amendment, nicht in drei Dateien (Konflikt mit der SSoT-Korrektur) |

`ai_sparring_by` ist bewusst **non-accountable**: Zwei externe KI-Reviews ersetzen keine
menschliche Owner-Review.

---

## Threshold

**Amendment an ADR-284**, kein neuer org-weiter ADR. Der Coverage-Contract existiert bereits als
Entscheidung (§2 Nr. 1); ihn auf Live-Antworten auszudehnen ist eine Erweiterung nach bestehendem
Muster. Die Architekturentscheidung ist getroffen, nur ihr Geltungsbereich war zu eng.
