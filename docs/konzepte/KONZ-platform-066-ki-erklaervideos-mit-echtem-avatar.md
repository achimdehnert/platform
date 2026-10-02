---
concept_id: KONZ-platform-066
title: KI-gestützte Erklärvideos mit gekennzeichnetem Avatar unter echtem Namen
pipeline_status: idea
tier: T1                   # reines Konzept, keine Konvention, kein Werkzeug, keine Außenwirkung — T2, sobald ein Anbieter Gesichts-/Stimmdaten erhält
owner: Achim Dehnert
spec_refs: []
adr_threshold: none        # kein Architekturentscheid; Werkzeugwahl ist eine Beschaffungsfrage (siehe D2)
review_by: 2026-12-31
kill_criteria: "Das Pilotvideo (Schritt 4) erreicht in der internen Sichtung nicht das Urteil ‚so würde ich es unter meinem Namen zeigen', ODER ein Kennzeichnungs-/Datenschutzbefund zum gewählten Anbieter lässt sich nicht ausräumen — dann keine Veröffentlichung, Konzept bleibt idea."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "https://github.com/achimdehnert/platform/issues/3649", commit_or_pr: "#3649", opened_in_session: true}
  - {claim_id: C2, source_path: "https://medium.com/@Nestora/i-found-the-faceless-ai-account-quietly-making-400-000-a-year-selling-18-ebooks-ca0c2ad3617e", commit_or_pr: "Artikel, abgelegt 2026-09-30", opened_in_session: true}
created: 2026-09-30
---

# KONZ-platform-066 — KI-Erklärvideos mit gekennzeichnetem Avatar unter echtem Namen

> Auftrag: [#3649](https://github.com/achimdehnert/platform/issues/3649), Owner-Freigabe
> 2026-09-30 im Raum Achim/Lotse. **Tier T1** — dieses Dokument beschreibt einen möglichen
> Weg; es kauft nichts, produziert nichts und veröffentlicht nichts.

## Kernthese

Der NESTORA-Artikel beschreibt eine Produktionskette (Skript → Avatar → Stimme → Kurzvideo),
die handwerklich brauchbar ist, und hängt sie an ein Geschäftsmodell, das auf einer
erfundenen Person, verdeckter Urheberschaft und zugespitzten Heilsversprechen beruht. Wir
übernehmen die Kette und drehen jedes Vorzeichen um: **echte Person, echter Name, echtes
Fachgebiet, sichtbar als KI-Avatar gekennzeichnet.** Der Avatar spart Drehzeit, er ersetzt
weder die Person noch die fachliche Verantwortung.

## 1 Zielgruppe, Themen, Format

**Zielgruppen**

| Kanal | Zielgruppe | Zweck |
|---|---|---|
| LinkedIn | Entscheider in Verwaltung und Mittelstand, Datenschutzbeauftragte | Sichtbarkeit der IIL-Beratung, Gesprächsanlass |
| YouTube (öffentlich oder „nicht gelistet") | Studierende, Fachöffentlichkeit | Nachschlagbare Erklärstücke zu Vorlesungsinhalten |
| Intern / Lernplattform | Kursteilnehmende, Kundenteams nach Projektstart | Wiederholbare Einweisung statt Einzeltermin |

**Beispielthemen** aus dem tatsächlichen Arbeitsfeld

| # | Thema | Kanal | Kernfrage in einem Satz |
|---|---|---|---|
| T1 | DSGVO: Was ein KI-Chatbot im Unternehmen datenschutzrechtlich braucht | LinkedIn | Welche drei Dokumente müssen vor dem Start stehen? |
| T2 | EU AI Act für Nicht-Juristen: Risikoklassen in 90 Sekunden | LinkedIn, YouTube | Fällt mein Anwendungsfall unter „hohes Risiko"? |
| T3 | KI-Beratung: Warum ein Pilot ein Abbruchkriterium braucht | LinkedIn | Woran erkenne ich, dass ein KI-Projekt gestoppt werden sollte? |
| T4 | KI-Assistenz in der Verwaltung am Beispiel MEiKI | intern, später öffentlich | Was darf ein Assistent im Bürgerkontakt, was nicht? |
| T5 | Vorlesungsbaustein: ein Grundlagenkapitel als Kurzvideo | YouTube „nicht gelistet", Lernplattform | Ein Begriff, ein Beispiel, eine Übungsfrage |

T4 berührt einen Kunden (Landratsamt). Vor jeder Veröffentlichung braucht es dessen
Zustimmung; bis dahin nur intern. T5 setzt voraus, dass die Rechte an Folien und Material
bei uns liegen oder die Hochschule zustimmt.

**Format**

- Länge: 60–120 Sekunden für LinkedIn, 3–6 Minuten für YouTube/Lernplattform.
- Seitenverhältnis: 1:1 oder 4:5 für LinkedIn, 16:9 für YouTube und intern.
- Untertitel immer eingebrannt (LinkedIn läuft überwiegend stumm), Sprache Deutsch;
  Englisch nur, wenn ein Thema es trägt.
- Fester Rahmen: Einblendung „KI-Avatar von Achim Dehnert, Inhalt von ihm verfasst und
  geprüft" in den ersten Sekunden und im Abspann, dazu der Hinweis im Beitragstext.

## 2 Produktionsweg

| Schritt | Was passiert | Wer | Artefakt |
|---|---|---|---|
| P1 Thema | Eine Kernfrage, ein Kanal, eine Länge festlegen | Owner | Themenzeile |
| P2 Quellen | Aussagen mit Quelle belegen (Gesetzestext, eigene Projekterfahrung, Literatur) | Lotse, Owner prüft | Quellenliste |
| P3 Skript | Sprechtext mit KI-Hilfe entwerfen, in Owner-Stimme; jede Tatsachenbehauptung an P2 gebunden | Lotse, Owner redigiert | Skript mit Belegspalte |
| P4 Szenenplan | Skript in Szenen zerlegen (Text, Einblendung, Folie), **bevor** Rechenguthaben verbraucht wird | Lotse | Szenenliste |
| P5 Avatar + Stimme | Einmalig: Avatar aus eigener Videoaufnahme, Stimme aus eigener Sprachaufnahme; danach je Video Skript einspielen | Owner (Aufnahme), Werkzeug | Rohvideo |
| P6 Schnitt | Folien/Grafiken, Untertitel, Kennzeichnung, Abspann | Lotse oder Werkzeug | Schnittfassung |
| P7 Abnahme | Owner sieht die Endfassung vollständig an und gibt frei | Owner | Freigabe als Artefakt |

P4 ist die eine Idee aus dem Artikel, die wir unverändert übernehmen: Fehler im Skript
werden auf Papier gefunden, nicht nach der kostenpflichtigen Generierung.

**Avatar und Stimme — Regeln**

- Ausschließlich das eigene Gesicht und die eigene Stimme des Owners, aus eigener Aufnahme,
  mit dokumentierter Einwilligung. Kein erfundenes Gesicht, keine Stimme Dritter.
- Sichtbare Kennzeichnung als KI-Avatar in jedem Video (Einblendung + Beitragstext),
  zusätzlich die Plattform-Kennzeichnung für synthetische Inhalte, wo es sie gibt.
  Das Video darf nicht wie eine echte Aufnahme wirken wollen.
- Gesicht und Stimme sind biometrische Daten (Art. 9 DSGVO). Ein Anbieter erhält sie erst
  nach Prüfung von Auftragsverarbeitung, Speicherort, Löschweg und Nutzung zum
  Modelltraining (D2). Die Rohaufnahmen bleiben bei uns.

**Werkzeugkandidaten** (keine Kaufentscheidung; Preise und Vertragsbedingungen ungeprüft)

| Rolle | Kandidat | Warum ansehen | Offen |
|---|---|---|---|
| Avatar-Video (Dienst) | Synthesia | Europäischer Anbieter, Avatar aus eigener Aufnahme, Firmenfokus | AVV, Speicherort, Trainingsnutzung |
| Avatar-Video (Dienst) | HeyGen | Verbreitet, eigener Avatar, Stimmklon, viele Sprachen | US-Anbieter, Datenweg |
| Avatar-Video (Dienst) | Colossyan, D-ID | Schulungsfokus bzw. einfache Porträt-Animation | Qualität bei Deutsch |
| Stimme (Dienst) | ElevenLabs | Stimmklon mit guter deutscher Aussprache | Datenweg, Einwilligungsprozess |
| Stimme (selbst betrieben) | OmniVoice, XTTS/Piper | Läuft auf eigener Hardware, keine Weitergabe der Stimme | Qualität, Aufwand |
| Lippensynchron (selbst betrieben) | LivePortrait, MuseTalk | Gesicht verlässt das Haus nicht | Bildqualität, Rechenzeit |
| Schnitt/Untertitel | DaVinci Resolve, Descript, CapCut | Untertitel, Einblendungen, Zusammenschnitt | CapCut: Datenweg |

Der selbst betriebene Weg ist datenschutzlich der saubere, aber der teurere in Arbeitszeit.
Empfehlung für den Piloten: **ein Dienst mit geprüftem AVV** für Avatar und Stimme; der
selbst betriebene Weg bleibt Option, falls D2 keinen Anbieter übrig lässt.

## 3 Abgrenzung — was wir nicht tun

Bezug: NESTORA, „I Found the Faceless AI Account Quietly Making $400,000 a Year Selling
$18 Ebooks" (Medium, September 2026), vom Owner am 2026-09-30 abgelegt.

| Praxis im Artikel | Unsere Regel |
|---|---|
| Erfundene Person („alter jamaikanischer Arzt"), Gesicht nach fremdem Pinterest-Foto nachgebaut | Nur der Owner selbst, aus eigener Aufnahme. Keine Kunstfigur, keine Anlehnung an fremde Gesichter. |
| Konto ohne erkennbaren Urheber („faceless", anonym) | Klarname, Impressum, verlinktes Profil. Wer spricht, ist jederzeit feststellbar. |
| Wirkung „so echt, dass ich nicht zweifelte" als Qualitätsziel | Ziel ist Verständlichkeit, nicht Verwechselbarkeit. Kennzeichnung in jedem Video. |
| Die Behauptung, das Publikum wisse ohnehin, dass es KI ist | Wir verlassen uns nicht darauf; wir sagen es. |
| Gesundheitsversprechen ohne Beleg („2000 Jahre altes Augenheilmittel") | Keine Gesundheits-, Heil- oder Erfolgsversprechen. Jede Tatsachenbehauptung hat eine Quelle (P2), Rechtsthemen tragen den Hinweis „keine Rechtsberatung im Einzelfall". |
| Themenwahl nach Suchvolumen und Wettbewerb, Ideen vom Agenten „was gerade funktioniert" | Themen kommen aus unserer Arbeit und unseren Kundenfragen, nicht aus Keyword-Werkzeugen. |
| Algorithmus-Taktik (Verweildauer-Ziel 75 %, Haken in zwei Sekunden) als Leitgröße | Keine Klickköder, keine künstliche Spannung. Ein klarer Einstieg ja, eine Täuschung über den Inhalt nein. |
| Produkt kopieren, „was schon verkauft", KI-E-Book ungeprüft hochladen | Kein Verkauf über die Videos, keine KI-erzeugten Produkte. Die Videos verweisen höchstens auf Beratung, Lehre oder Veröffentlichtes, das wir selbst verantworten. |
| Umsatzzahlen als Beweis, am Ende ein Kurs-Angebot | Kein Erfolgsversprechen, keine Einnahmezahlen als Werbung. |

Wer diese Tabelle bricht, bricht das Konzept; das Video erscheint dann nicht.

## 4 Aufwand und nächste Schritte

**Grobe Aufwandsschätzung** (Schätzung, nicht gemessen)

| Posten | Einmalig | Je Video (60–120 s) |
|---|---|---|
| Anbieterprüfung (AVV, Speicherort, Löschweg) | 3–5 h | — |
| Aufnahme für Avatar und Stimme, Einwilligung dokumentieren | 2–3 h | — |
| Einrichtung Vorlage (Kennzeichnung, Abspann, Untertitelstil) | 2–4 h | — |
| Thema, Quellen, Skript bis Owner-Freigabe | — | 2–3 h, davon Owner ca. 45 min |
| Szenenplan, Generierung, Schnitt | — | 1–2 h |
| Abnahme durch den Owner | — | 15–30 min |

Einmalig also etwa 1–1,5 Arbeitstage, danach je Kurzvideo etwa ein halber Tag, von dem der
Owner rund eine Stunde selbst trägt. Längere YouTube-Stücke etwa das Doppelte. Lizenzkosten
sind nicht erhoben; sie werden in Schritt 2 mit Quelle nachgetragen.

**Offene Entscheidungen des Owners**

- **D1** Kanal und Reihenfolge der Themen: Empfehlung LinkedIn mit T1 oder T3 als Pilot.
- **D2** Anbieterweg: Dienst mit AVV oder selbst betrieben. Empfehlung Dienst, sofern die
  Prüfung in Schritt 2 besteht.
- **D3** Kennzeichnungstext und -ort verbindlich festlegen (Vorschlag steht in Abschnitt 1).

**Nächste Schritte** (jeder ohne Kauf, ohne Vertrag, ohne Veröffentlichung)

1. Owner entscheidet D1–D3.
2. Anbieterprüfung für zwei Kandidaten auf dem Papier: AVV, Speicherort, Trainingsnutzung,
   Löschweg, Preise mit Quelle. Ergebnis als Nachtrag in diesem Konzept.
3. Skript und Szenenplan für das Pilotthema nach P1–P4, Owner redigiert.
4. Erst nach eigener Freigabe: Probelauf im kostenlosen Kontingent des gewählten Anbieters.
   Das ist der Schritt, in dem Gesicht und Stimme das Haus verlassen — eigenes Gate.
5. Interne Sichtung des Pilotvideos gegen Abschnitt 3 und das Kill-Kriterium; danach
   entscheidet der Owner über Veröffentlichung und Abo.

## Offene Prüfpunkte (Hypothesen)

- Kennzeichnungspflicht für synthetische Personen-Darstellungen nach Art. 50 EU AI Act und
  deren Geltungsbeginn — vor Veröffentlichung am Gesetzestext prüfen.
- Kennzeichnungsfunktionen für KI-Inhalte bei LinkedIn und YouTube — Stand der jeweiligen
  Plattformregeln vor dem Piloten nachsehen.
- Die Anbieterbeschreibungen in Abschnitt 2 stammen aus allgemeinem Wissen, nicht aus
  geprüften Vertragsunterlagen.
