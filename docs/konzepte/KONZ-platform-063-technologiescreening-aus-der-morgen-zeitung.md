---
concept_id: KONZ-platform-063
title: Laufendes Technologiescreening aus der Morgen-Zeitung — Präsentation und Auswahl
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR — ADR-299 entscheidet die Architektur der Zeitung; hier kommt ein dritter Leser desselben Bestands dazu, keine neue Architektur. Wird Stufe 1 gebaut und bekommt das Register eine eigene Tabelle, ist das ein Amendment an ADR-299, kein neuer ADR.
review_by: 2026-10-01
kill_criteria: "Stufe 1 wird nicht gebaut, wenn die Messreihe aus Stufe 0 bis 2026-10-01 nicht in mindestens zwei von drei Messungen je ≥3 konkrete Technologien mit höchstens 1 Fehltreffer liefert. Unabhängig davon stirbt dieses Konzept am selben Tag wie die Morgen-Zeitung, falls deren Kill-Gate (KONZ-platform-057, 2026-10-09) zieht."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: news-hub/apps/digest/models.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C2, source_path: news-hub/apps/digest/services/themenbildung.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C3, source_path: news-hub/apps/digest/services/bewertung.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C4, source_path: news-hub/apps/digest/services/speicher.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C5, source_path: news-hub/apps/digest/services/sonderblock.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C6, source_path: news-hub/docs/betrieb/morgen-zeitung.md, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C7, source_path: docs/adr/ADR-299-hot-topics-digest-auf-bestehendem-mailbestand.md, commit_or_pr: e163a4c7, opened_in_session: true}
  - {claim_id: C8, source_path: docs/konzepte/KONZ-platform-057-morgenzeitung-aus-dem-hot-topics-letter.md, commit_or_pr: e163a4c7, opened_in_session: true}
  - {claim_id: C9, source_path: tools/chat_agent/vorschlaege.py, commit_or_pr: "#3376", opened_in_session: true}
  - {claim_id: C10, source_path: chat-hub/deploy/lotse_auftrag.py, commit_or_pr: 53f705e, opened_in_session: true}
  - {claim_id: C11, source_path: chat-hub/deploy/lotse_briefing.sh, commit_or_pr: "chat-hub#128", opened_in_session: true}
  - {claim_id: C12, source_path: "Prod-Messung 88.198.191.108 · docker exec news_hub_web manage.py shell", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C13, source_path: tools/screening_backtest.py, commit_or_pr: "#3382", opened_in_session: true}
  - {claim_id: C14, source_path: "news-hub#19, #33, #65", commit_or_pr: "gh issue list news-hub", opened_in_session: true}
  - {claim_id: C15, source_path: "platform#3375", commit_or_pr: "#3375", opened_in_session: true}
  - {claim_id: C16, source_path: "journalctl -u news-hub-tageslauf.service, 2026-09-22 06:16 UTC", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C17, source_path: "Ordner-Inventar iil/AI-News · tools/mail_agent/graph_mail.py --find --all --source AI-News", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C18, source_path: news-hub/deployment/scripts/tageslauf.sh, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C19, source_path: "Messung 2 (Variante C) — Urteil des Sitzungsmodells über das Fenster 09-15…09-21, Protokoll in platform#3383", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C20, source_path: "https://www.latent.space/feed + /robots.txt, HTTP 200, 20 Einträge", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C21, source_path: news-hub/apps/digest/services/vertiefung.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C22, source_path: news-hub/apps/digest/services/web_naht.py, commit_or_pr: 8bf3fa9, opened_in_session: true}
  - {claim_id: C23, source_path: "Messung 2 (vorgezogen) — vier T1a-Läufe (openai/gpt-oss-120b) über dasselbe Fenster, Protokoll in platform#3383", commit_or_pr: "2026-09-22", opened_in_session: true}
  - {claim_id: C24, source_path: "Positivkontrolle des Beleg-Checks — 8 Proben (echt/frei erfunden/plausibel erfunden/halb erfunden/Kurzwort/leer), lax 2 Fehlurteile, verschärft 0; Wiederholungslauf 8/8 streng bestanden", commit_or_pr: "2026-09-22", opened_in_session: true}
created: 2026-09-22
updated: 2026-09-22
---

# KONZ-platform-063: Laufendes Technologiescreening aus der Morgen-Zeitung

**Tier T3.** Nicht T2, weil drei Repos beteiligt sind (news-hub erkennt, platform fragt,
chat-hub stellt zu), weil ein neuer Lebenszyklus entsteht (eine Technologie wird
*beobachtet → vorgeschlagen → ausgewählt/verworfen*) und weil ein dauerhaftes Artefakt
angelegt würde. Jeder dieser drei Punkte ist ein nicht verhandelbarer Eskalations-Auslöser;
die Selbsteinstufung „ist doch nur ein Leser mehr" wäre falsch.

---

## 1. Executive Summary

**Empfehlung: als MVP annehmen — aber in zwei Stufen, und Stufe 1 erst nach einer Messung.**

Die Hälfte des Wunsches aus [#3375](https://github.com/achimdehnert/platform/issues/3375)
ist bereits gebaut: Präsentation und Auswahl. Die Morgen-Meldung trägt seit
[chat-hub#128](https://github.com/iilgmbh/chat-hub/pull/128) die Ausgabe von
`tools/chat_agent/vorschlaege.py` unverändert mit, ein 👍 des Owners ist eine gebundene,
einmalige, ownerechte Freigabe, und `lotse_auftrag.py uebergeben` legt daraus ein Issue mit
Label `uebergabe-kapitaen` an, das die Kapitäns-Sitzung liest. Für „präsentieren und
auswählen" muss nichts Neues gebaut werden (C9, C10, C11).

Die andere Hälfte — das Erkennen — trägt der Bestand **heute noch nicht**. Gemessen am
2026-09-22 auf Prod: 31 Läufe, 116 Themen, aber nur **32 distinkte Schlagworte**, das
zweithäufigste davon `unsubscribe` (C12). Eine Rückrechnung der naheliegenden Aufsteiger-Regel
(„an ≥2 Tagen in 7 genannt, in den 21 Tagen davor nie") über den echten Bestand liefert
**zwei Treffer, davon einen Müll-Treffer** (C13). Der erste statistisch gültige Vergleich wäre
ohnehin erst am 2026-10-06 möglich — drei Tage vor dem Kill-Gate der Zeitung selbst (C8).

**Kernidee:** Neuheit nicht gegen ein statistisches Zeitfenster messen, sondern gegen ein
**Register bekannter Technologien**, das mit jeder Woche wächst. Damit ist die Aussage
„das ist neu" ab dem ersten Tag tragfähig und wird nicht von der Kürze der Historie erschlagen.

**Wichtigste Stärke:** kein neuer Zustellweg, kein neuer Zeitgeber, keine neue Freigabegeste —
der dritte Leser erbt eine Kette, die läuft. **Wichtigstes Risiko:** das Screening erbt auch die
Quellenlage, und die ist das Postfach des Owners, nicht der Markt (0 von 393 Nachrichten zu
NIS2 und Voice Agents, C14). **Kleinste sinnvolle Version:** ein lesendes Messkommando, das
zeigt, was die Regel in den letzten Wochen geliefert *hätte* — ohne eine Zeile zu schreiben.
**Größte Unsicherheit:** ob daraus überhaupt ein Vorlauf entsteht oder nur ein Nachlauf auf die
Redaktionsagenda der abonnierten Newsletter.

**Nachtrag 2026-09-22, nach dem Merge (Owner-Auftrag „latent.space bzw. medium — bzw. eine
Analyse des Ordners AI-News").** Der Ordner ist ausgezählt: **101 Mails seit dem 2026-08-04 von
genau drei Absendern** — `medium.com` (44), `thesequence@substack.com` (30),
`theprohuman@mail.beehiiv.com` (27), C17. Medium ist damit bereits die stärkste Quelle des
Screenings, nicht die fehlende. Der einzige Fehltreffer der Erstmessung stammt
aus der Heftzeile eines dieser drei Absender — Rauschen ist damit absenderspezifisch und gezielt
dämpfbar (REC-14), statt über immer längere Allgemeinwortlisten.

**Zweiter Nachtrag, wenige Stunden später (Owner-Wort: „nur free verwenden und selbst — auf
Basis der Themen, LLM soll beurteilen — tiefer recherchieren").** Das kippt die Konstruktion
zum Besseren und macht das vorherige REC-13 (Abo) gegenstandslos: `latent.space` kommt über
seinen öffentlichen Feed als zweite Web-Naht neben `fav0` (C20, C22), also frei und ohne
Postfach; die Auswahl trifft ein **Urteil** statt einer Wortregel; und die Tiefe holt die
bereits gebaute `Vertiefung` (C21), die je Thema mehr Quellen zieht und jede Aussage an einen
nummerierten Beleg mit Auszug bindet. Gegenprobe auf demselben Fenster: die Wortregel fand
einen brauchbaren Namen, das Urteil sieben (C19). Einschränkung, die dazugehört: geurteilt hat
das Sitzungsmodell, nicht das günstige Modell, das später laufen soll — Messung 2 wiederholt es
damit.

---

## 2. Scope & Evidenzbasis

**Input:** der Volltext des Wunsches in #3375 (C15).

**In dieser Sitzung geöffnet:** `models.py`, `themenbildung.py`, `bewertung.py`, `speicher.py`,
`sonderblock.py`, `docs/betrieb/morgen-zeitung.md` (alle news-hub @ 8bf3fa9); ADR-299 §4.1–§4.4
und KONZ-platform-057 (platform @ e163a4c7); `tools/chat_agent/vorschlaege.py` (platform,
#3376); `deploy/lotse_auftrag.py` und `deploy/lotse_briefing.sh` (chat-hub @ 53f705e);
offene Issues news-hub #19/#33/#65.

**Eigene Messungen (2026-09-22, Prod-Host, lesend):**

| Messung | Wert | Claim |
|---|---|---|
| Läufe (2026-09-09…09-22) | 31 | C12 |
| Themen gesamt | 116 | C12 |
| distinkte Schlagworte | 32 (`model` 10, `unsubscribe` 8, `astra` 8, `that`/`this` je 7) | C12 |
| Schlagworte genau 1× | 14 | C12 |
| Quellen | 824 (476 Mail, 348 extern, 0 Web) | C12 |
| Themen ohne Titel | **0 von 116** | C12 |
| Tage mit Inhalt | 10 von 14 (leer: 09-11…09-13 wegen Groq-401, 09-22) | C12, C16 |
| Rückrechnung Aufsteiger-Regel | 2 Treffer, davon 1 Müll | C13 |
| Namenskandidaten im Korpus | 307 aus 464 Zeilen | C13 |
| **Absender im Ordner `AI-News`** | **3** — `medium.com` 44, `thesequence@substack.com` 30, `theprohuman@mail.beehiiv.com` 27 | C17 |
| Zeitraum des Ordners | 101 Mails, 2026-08-04…09-22 | C17 |

**Annahmen (markiert):** dass der Owner wöchentlich *einen* Vorschlag lieber liest als täglich
drei (H — aus der Attention-Begründung in `vorschlaege.py`, nicht gemessen); dass ein
Wochen-LLM-Aufruf im Rahmen der bestehenden Kostenstelle bleibt (H — Kosten werden heute
nirgends erfasst, siehe M28-4).

**Nicht prüfbar in dieser Sitzung:** ob der Owner die Zeitung überhaupt öffnet — „Öffnungen
je Tag: nicht erhoben" (C6). Genau daran hängt das Kill-Gate von KONZ-057.

---

## 3. Infrastruktur-Fit

| Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---|---|---|---|---|
| ADR-299 Lesenaht/Beleg-Pflicht | ja | Bestand als Korpus | – | mittel | §4.2 speichert Kandidaten **nicht**; was an der Beleg-Pflicht scheitert, ist für das Screening unsichtbar (C7) |
| `Lauf`/`Thema`/`Quelle` (C1) | ja | ganz | – | niedrig | 0 von 116 Themen ohne Titel — das Titelfeld trägt (C12) |
| `GespeicherterTitel`/`GespeichertesUrteil` (C1) | ja | Muster „je Fenster einfrieren" | – | mittel | Schlüssel hängt am Argument `--tage`; ein Nachlauf mit anderem Fenster erzeugt einen zweiten Satz (M28-2) |
| `digest_frische` + OnFailure-Alarm (C6) | ja | ganz | um einen Kandidaten-Melder | niedrig | Positivkontrolle heute: 0 Themen → Exit 1 → Alarm (C16) |
| `vorschlaege.py` (C9) | ja | Kanal + Kappe | um eine zweite Quelle | mittel | `MAX_FRAGEN = 3` ist ein geteiltes Aufmerksamkeitsbudget ohne Vorrangregel |
| `lotse_briefing.sh` (C11) | ja | ganz | – | niedrig | Kommando steht in der Erlaubnisliste, Ausgabe wird unverändert angehängt — kein chat-hub-Eingriff nötig |
| `lotse_auftrag.py uebergeben` (C10) | ja | ganz | – | niedrig | Auswahl = Issue `uebergabe-kapitaen`; die Kapitäns-Sitzung liest es mit `#N weiter` |
| `pruefe_go_reaktion` (C10) | ja | ganz | – | mittel | 👍 bindet an genau ein Ereignis, einmalig, Owner-only — aber dieselbe Geste wie für Befund-Fragen |
| `web_naht.py` (fav0) (C22) | ja | Muster für eine zweite freie Quelle | um `latent.space/feed` | mittel | Ausgabe muss den Vertrag aus `naht.py` unverändert passieren — das ist der eigentliche Test |
| `vertiefung.py` + `news-hub-vertiefen.timer` (C21) | ja | ganz | – | niedrig | Tiefenrecherche je Thema existiert samt Warteschlange und verschärfter Beleg-Pflicht; das Screening fordert sie an, statt eine eigene zu bauen |
| Genesor `pipeline_status` | ja | `idea` | – | niedrig | Off-Ramp über `review_by` 2026-10-01 |
| I4 Namensraum | ja | – | – | **hoch** | `manage.py digest_trend` ist bereits für das Kennzahlen-Journal reserviert (C6) — Name ist verbrannt |
| Deploy news-hub (C14) | ja | Tageslauf-Unit | – | hoch | `deploy.yml` bringt Host-Skripte/Units nicht auf den Host (#65) → **kein neuer Timer** |
| platform ist PUBLIC | ja | – | – | hoch | Vorschlagstexte landen in einem öffentlichen Issue-Tracker — Newsletter-Zitate und Absender haben dort nichts verloren |

---

## 4. Steelman

Der Hebel liegt nicht in mehr Information, sondern in der zweiten Ableitung: Ein generischer
Tech-Radar beantwortet „was existiert" — eine Frage, die niemand hier hat. Die offene Frage ist
„was wird in *meinem* Zufluss gerade häufiger", und die kann nur der eigene Bestand beantworten.
Die 824 Quellen sind keine Rohdaten, sondern eine über Jahre gewachsene Abonnement-Entscheidung:
ein Relevanzfilter, den ein externer Radar erst nachbauen müsste. Dazu kommt der Zeitstempel —
der Zufluss datiert, wann etwas auftaucht, nicht wann ein Analyst es kuratiert hat.

Der gemessene Schlagwort-Befund ist kein Gegenargument, sondern die Bauanweisung: dass
`unsubscribe` das zweithäufigste Schlagwort ist, weiß man **vor** dem Bau, und die Substanz
steckt nachweislich woanders — in den Titeln („Self-Evolving Search Index für Retrieval-Augmented
Agents", „Grok Imagine Image 2.0 steigt auf Platz 4", „Two New OCR Models Land on Hugging Face").
Ein Vorschlag pro Woche ist außerdem die Rate-Begrenzung, nicht ihr Verzicht: Ablehnen kostet
nichts (kein 👍), Annehmen erzeugt genau ein Issue in einer Kette, die schon benutzt wird. Der
dritte Leser fügt **keine** neue Außenwirkung hinzu — er erbt Präsentationsweg, Freigabeweg und
das Determinismus-Muster.

---

## 5. Konzeptdefinition

### 5.1 Kernthese

Dieses Konzept sagt: **Das Screening wird ein dritter, lesender Leser des bestehenden
Tageslaufs; „neu" wird gegen ein wachsendes Register bekannter Technologien bestimmt statt
gegen ein statistisches Zeitfenster; und gebaut wird erst, wenn eine Rückrechnung auf dem
echten Bestand zeigt, dass dabei Brauchbares herauskommt.**

### 5.2 Problem

**Beobachtung.** Die Zeitung erzeugt täglich 3–5 Themen mit technologiedichten Titeln und
externen Belegen. Niemand fragt diesen Strom je die Frage „was davon ist neu und für uns
verwertbar?" — er wird gelesen und vergessen (C12).

**Beobachtung.** Der Weg vom Vorschlag zur Umsetzung existiert vollständig: Morgen-Meldung →
👍 → Issue `uebergabe-kapitaen` → Kapitäns-Sitzung (C9, C10, C11).

**Interpretation.** Der Wunsch in #3375 wird deshalb zu 50 % von bereits gebauter Infrastruktur
bedient. Die fehlende Hälfte ist ausschließlich die Erkennung.

**Hypothese (H).** Ein Vorlauf entsteht, weil Newsletter früher schreiben als Analysten
kuratieren. Falsifikation: bei drei ausgewählten Vorschlägen prüfen, ob der Owner sie vorher
schon kannte; kannte er alle, ist es Nachlauf, kein Vorlauf.

**Beobachtung (nachgetragen 2026-09-22).** Die Grundlage ist schmaler als „vier Ordner"
vermuten lässt: der Ordner `AI-News` trägt genau drei Absender (C17). Zwei davon sind
Sammel-Newsletter, die dieselben Meldungen weiterverarbeiten — Übereinstimmung zwischen ihnen
belegt also nicht, dass ein Thema breit auftaucht, sondern dass zwei Redaktionen dieselbe
Quelle gelesen haben.

**Offene Frage.** Ob diese Grundlage für ein Screening taugt, wenn zwei der vom Owner selbst
genannten Themen darin 0 Treffer haben (C14, news-hub#19) — und ob eine vierte Quelle
(REC-13) daran genug ändert.

**Warum jetzt.** Weil der Bestand jetzt groß genug ist, um die Frage *zu messen* (10 Tage mit
Inhalt), und noch klein genug, dass eine Fehlkonstruktion billig zurückzubauen ist.

### 5.3 Zielbild

Möglich wird: einmal pro Woche eine belegte Aussage „diese Technologie ist in deinem Zufluss neu
aufgetaucht, sie gehört in Topf *Kompetenz* oder *Portfolio*, der erste Schritt wäre X" — mit
einem Daumen als Entscheidung und einem Issue als Ergebnis. Sichtbar riskant wird: dass der
eigene Zufluss schmal ist; das Register zeigt es, weil ganze Felder darin fehlen. Leichter wird
die Entscheidung „womit beschäftigen wir uns als Nächstes", weil sie ein datiertes Protokoll
bekommt statt eines Bauchgefühls.

### 5.4 Nicht-Ziele

Kein Markt-Radar und kein Anspruch auf Vollständigkeit — was nicht im Zufluss ist, wird nicht
gefunden. Keine automatische Umsetzung: eine Auswahl erzeugt **ausschließlich ein Issue**, nie
eine Installation, nie einen Deploy. Kein neuer System-of-Record für Themen — die Themen bleiben
in `Thema`/`Quelle`. Kein neuer Zeitgeber und kein neuer Dienst. Keine Bewertung von Anbietern,
keine Empfehlung mit Außenwirkung.

### 5.5 Artefakte

| Artefakt | Neu/Geändert | Owner | Normativ? | Generiert? | Lebenszyklus | Risiko |
|---|---|---|---|---|---|---|
| `tools/screening_backtest.py` (platform) | neu, **Stufe 0** | Achim | nein | nein | stirbt mit dem Konzept | niedrig |
| `docs/konzepte/KONZ-platform-063*.md` | neu | Achim | nein | nein | `review_by` 2026-10-01 | niedrig |
| `manage.py technologie_nennungen` (news-hub) | neu, **Stufe 1** | Achim | nein | nein | an Tageslauf gehängt | mittel |
| `manage.py technologie_woche` (news-hub) | neu, **Stufe 1** | Achim | nein | nein | montags im Tageslauf | mittel |
| Register (Tabelle `Technologie`) | neu, **Stufe 1** | Achim | **ja** (einzige Wahrheit über Status) | nein | Amendment ADR-299 | hoch |
| Zweite Quelle in `vorschlaege.py` | geändert, **Stufe 1** | Achim | nein | nein | – | mittel |

### 5.6 Datenmodell (nur Stufe 1)

Eine Tabelle, ein Zweck: **Entscheidungen** über Technologien. Keine Kopie von Themen.

| Feld | Typ | Pflicht | Bedeutung | Validierung | Failure-Mode |
|---|---|---|---|---|---|
| `name` | Text, unique | ja | normalisierter Technologiename | eindeutig, case-insensitiv | Dublette bei Schreibvarianten → Normalisierung wie `themen_id` (C2) |
| `erste_nennung` | Datum | ja | Tag, an dem sie zuerst im Bestand auftauchte | ≤ heute | bei Nachlauf rückwirkend falsch → aus `Thema.lauf.bis` ableiten, nicht aus `--tage` (M28-2) |
| `belege` | JSON (Liste URL) | ja | Quellen-URLs aus `Quelle` | ≥1 | leer ⇒ kein Vorschlag |
| `topf` | Auswahl | ja | `kompetenz` \| `portfolio` \| `offen` | – | Fehleinordnung ist billig: der Owner korrigiert beim Daumen |
| `status` | Auswahl | ja | `beobachtet` \| `vorgeschlagen` \| `ausgewaehlt` \| `verworfen` | Übergänge nur vorwärts | – |
| `issue_url` | URL | nein | gesetzt bei `ausgewaehlt` | – | fehlt ⇒ Abgleich-Kommando meldet Exit 1 |
| `gefragt_am` | Datum | nein | wann zuletzt gefragt | – | – |

**Keine zweite Wahrheit:** Name, Datum und Belege sind aus `Thema`/`Quelle` ableitbar und werden
nur deshalb festgeschrieben, weil das Register sonst bei jedem Lauf neu raten müsste, was schon
bekannt war. Der einzige **nicht** ableitbare Teil ist `status`/`topf`/`issue_url` — und genau
dafür existiert die Tabelle. Abgleich-Kommando mit Exit-Code gegen `Thema` ist Pflicht (REC-6).

### 5.7 Prozessmodell

| Schritt | Was passiert | Wer entscheidet | Artefakt | Gate | Bei Abweichung |
|---|---|---|---|---|---|
| idea (heute) | Rückrechnung auf dem Bestand | Agent | dieses Doc + `screening_backtest.py` | – | – |
| Stufe-0-Messung | 3 Wochen lang wöchentlich messen, nichts schreiben | Owner liest | Messprotokoll im Issue | **Qualitätsschwelle** (§13) | Schwelle gerissen ⇒ `sunset` |
| Stufe 1 | Register + Wochenfrage + Melder | Owner gibt frei | PR news-hub + platform | CI grün, Amendment ADR-299 | – |
| Betrieb | montags 1 Frage, 👍 ⇒ Issue | Owner | Issue `uebergabe-kapitaen` | Sperrliste | kein 👍 ⇒ nichts |
| sunset | stirbt mit der Zeitung oder am Kill-Gate | Owner | `pipeline_status: sunset` | – | – |

### 5.8 Enforcement-Modell

| Regel | Level | Mechanismus | Owner | Ausnahme? | Ablaufdatum? |
|---|---|---|---|---|---|
| Auswahl erzeugt nur ein Issue | Runtime-Guard | `GESPERRT` in `vorschlaege.py` + Textprüfung in `pruefe_go_reaktion` | Achim | nein | – |
| Kandidaten je Wochenlauf > 0 | CI/Betrieb | eigener Exit-Code, wie `digest_frische` | Achim | `--leer-erlaubt` | ja, je Lauf |
| Register ↔ `Thema` konsistent | Betrieb | Abgleich-Kommando, Exit 1 bei Drift | Achim | nein | – |
| Keine Newsletter-Zitate im Issue | Review | Vorschlagstext trägt nur Name, Zahlen, externe URL | Achim | nein | – |
| Screening stirbt mit der Zeitung | Governance | Zeile im Kill-Gate von KONZ-057 | Achim | nein | 2026-10-09 |

### 5.9 Minimal Viable Concept (Stufe 0 — in dieser PR geliefert)

**Was:** `tools/screening_backtest.py` liest einen aus der news-hub-Datenbank gezogenen
TSV-Auszug (`art⇥tag⇥titel`) und rechnet zwei Regeln rückwirkend über den echten Bestand:
Variante A (Aufsteiger: an ≥2 **Tagen** in 7, in den 21 davor nie) und Variante B (Erst-Nennung
im Fenster). Gezählt wird je **Tag**, nie je Lauf — bei 31 Läufen an 14 Tagen würde sonst ein
Nachlauf desselben Tages die Schwelle allein erfüllen.

**Was bewusst nicht drin ist:** kein Schreibzugriff, kein Modellaufruf, keine Migration, kein
Timer, keine Zustellung, kein Register.

**Erfolgsnachweis:** drei Wochenmessungen; Erfolg heißt ≥3 konkrete Technologien je Woche bei
höchstens 1 Fehltreffer (§13).

**Rückbau:** eine Datei löschen.

**Erstes Ergebnis (2026-09-22, C13):** Korpus 464 Zeilen über 10 Tage mit Inhalt, 307
Namenskandidaten. Variante A im Fenster 09-15…09-21: **2 Treffer** — `GPT-6 Astra` (brauchbar)
und `Sequence Radar Issue Last` (Newsletter-Fließtext, Müll). Variante B: 196 Erst-Nennungen,
davon 2 an ≥2 Tagen. **Das reißt die Schwelle heute klar.** Die naheliegende Regel ist damit
widerlegt, bevor eine Zeile Produktionscode dafür geschrieben wurde — das ist der Zweck dieser
Stufe.

### 5.9a Variante C — das Modell urteilt, die Wortregel zählt nur (Owner-Weisung 2026-09-22)

**Owner-Wort:** „nur free verwenden und selbst (auf Basis der Themen — LLM soll beurteilen)
tiefer recherchieren." Damit ist die Konstruktion entschieden: nicht mehr Zufluss abwarten,
sondern aus dem vorhandenen Zufluss **urteilen** und die Tiefe selbst holen.

**Warum das die gemessene Sackgasse verlässt.** Variante A und B zählen Wortketten und finden im
gemessenen Fenster zwei Namen, davon einen Fehltreffer (C13). Dasselbe Fenster, von einem Modell
beurteilt statt gezählt, liefert **sieben** konkrete, einsortierbare Technologien (C19) — die
Rohdaten waren nie das Problem, die Regel war es.

**Zwei freie Quellen statt eines Abos** (C17, C20):

1. Der Bestand, der ohnehin da ist — drei Absender im Ordner `AI-News`.
2. `latent.space` als **zweite Web-Naht nach dem Muster von `fav0`**: der öffentliche Feed
   `https://www.latent.space/feed` antwortet mit HTTP 200 und liegt nicht unter den in
   `robots.txt` gesperrten Pfaden; 20 Einträge, fast täglich, davon die `[AINews]`-Tagesschau.
   Kein Postfach, kein Abo, kein vierter Zugang im Sinne von ADR-299 §4.1 — dieselbe Naht, die
   `fav0.com` schon benutzt.

### 5.9b Wer urteilt? — gemessen, nicht angenommen (2026-09-22, C23)

Die offene Frage aus §13 („taugt das günstige Modell dafür?") wurde am selben Tag beantwortet,
indem dasselbe Fenster viermal durch das **T1a-Modell** (`openai/gpt-oss-120b`, derselbe Pfad wie
Titel und Bewertung) geschickt wurde. Ergebnis:

| Lauf | Kandidaten | Fehltreffer | Einordnung | Tokens |
|---|---|---|---|---|
| T1a naiv | 17 | ~5 (HP-ZBook-Bundle, Desktop-App für Arch Linux, „AI Data Centers senken Strompreise") | brauchbar gemischt | 3.375 |
| T1a streng | 8 | 0 formale, aber **eine erfundene Begründung** (Astra als „LLM-Variante für klinische Anwendungen" — stammt aus einer anderen Schlagzeile) | **8 von 8 `portfolio`** — die Einordnung ist zusammengebrochen | 3.018 |
| T1a streng + billige Selbstkritik | 8 | dieselben | dieselbe | +1.193 |
| **T1a + Belegpflicht (H3)** | **8** | **0 erfundene Belege** (8/8 Zitate maschinell im Stoff gefunden) | **4 `kompetenz` / 4 `portfolio`** | 3.421 |

**Drei Befunde, alle belegt:**

1. **Allein taugt das günstige Modell nicht.** Naiv nimmt es Hardware-Bundles und Desktop-Apps
   als „Technologie"; streng verliert es genau die drei wertvollsten Kandidaten der
   Vergleichsliste (lokales Modell für sensible Daten, OCR-Modelle, selbstfortschreibender
   Suchindex) und erfindet eine Begründung dazu.
2. **Eine billige zweite Meinung ist wertlos.** Der Kritik-Durchgang strich **0 von 8** Einträgen
   und kostete 1.193 Tokens. Zwei billige Läufe sind nicht ein teurer.
3. **Die Belegpflicht repariert mechanisch, was das Modell nicht kann.** Sobald jeder Kandidat
   die Schlagzeile wörtlich zitieren muss und ein simpler Zeichenkettenvergleich das prüft,
   verschwinden erfundene Begründungen (0 von 8) und die Einordnung erholt sich (4/4 statt 8/0).
   Das ist kein Modellverdienst, sondern dieselbe Beleg-Pflicht, die ADR-299 §4.2 dem Tageslauf
   schon auferlegt — hier nur auf das Urteil angewandt.

**Positivkontrolle des Beleg-Checks (C24) — und ein Loch darin.** Ein Prüfer, der nie anschlägt,
belegt keine Abwesenheit. Der Check wurde deshalb gegen acht Proben gehalten: zwei echte Zitate,
ein frei erfundenes, ein plausibel erfundenes („…Two New OCR Models… *and beat Google Cloud
Vision*"), ein halb erfundenes (ein Wort im echten Zitat getauscht), zwei Kurzwörter, ein leeres.

| Prüfer | Fehlurteile |
|---|---|
| die zuerst benutzte, laxe Fassung (`Zitat in Zeile ODER Zeile in Zitat`) | **2 von 8** — „AI" und „Astra" gingen durch, weil jedes Kurzwort Teilzeichenkette irgendeiner Schlagzeile ist |
| verschärft: Mindestlänge 25 Zeichen **und** nur „Zitat in Zeile" | **0 von 8** |

Der Lauf wurde mit dem verschärften Prüfer wiederholt: **8 von 8 bestehen auch streng**, die
Belege sind 37–74 normalisierte Zeichen lang, also echte Schlagzeilen. Die Zahl „0 erfunden"
hält damit — aber sie hielt vorher aus dem falschen Grund mit. In REC-19 steht deshalb die
verschärfte Fassung, nicht die laxe.

**Nicht bitstabil:** zwei Läufe mit leicht umformulierter Regel 4/5 lieferten 8 Kandidaten mit
sechs Überschneidungen (`Jev` und `ChatGPT Work` fielen weg, `ChatGPT Desktop` kam dazu).
Temperatur 0 macht den Aufruf reproduzierbar, den *Prompt* aber nicht — wer die Regeln anfasst,
misst neu.

**Entscheidung D4 — geteiltes Urteil statt eines Modells.** Das günstige Modell **sammelt breit
mit Belegpflicht**, ein mechanischer Beleg-Check wirft alles ohne auffindbares Zitat raus, und
das **teure Modell wählt aus und ordnet ein**. Tragend ist die Messung: der naive T1a-Lauf
enthielt 6 der 7 Kandidaten der Vergleichsliste — die Wiedererkennung ist also da, es fehlt die
Beurteilung der Geschäftsnähe. Der teure Schritt liest danach 8–17 Kandidatenzeilen statt 111
Schlagzeilen und läuft in der Briefing-Lane, die ohnehin werktags startet — er kostet also
nichts zusätzlich, während der wöchentliche Sammellauf bei rund 3.400 Tokens liegt.

**Tiefe kommt aus der vorhandenen Vertiefung.** `apps/digest/services/vertiefung.py` holt je
Thema mehr Quellen als der Tageslauf, nimmt den Kontext der tragenden Nachrichten dazu und
synthetisiert über dasselbe Groq-Modell — mit verschärfter Beleg-Pflicht: jede Aussage verweist
auf eine nummerierte Quelle **und** jede Quelle trägt einen echten Auszug (C21). Das Screening
fordert diese Vertiefung für die beurteilten Kandidaten an, statt eine eigene Recherche zu bauen.
Der Warteschlangen-Läufer dafür existiert (`news-hub-vertiefen.timer`, alle fünf Minuten).

**Kosten bleiben, wo sie sind:** ein Urteil je Woche über die Titel des Fensters, Vertiefung nur
für die Kandidaten, alles auf dem T1a-Modell aus `policies/llm-routing.md` — kein neuer Anbieter,
kein Abo, keine bezahlte Quelle.

### 5.10 Full Concept (Stufe 1, nur nach bestandener Messung)

Register als Neuheits-Maßstab statt Zeitfenster; ein LLM-Urteil **pro Woche** (nicht pro Lauf)
über die Titel des Fensters, das die konkreten Technologien benennt, die noch nicht im Register
stehen; Einordnung in `kompetenz`/`portfolio` mit einem Satz Begründung; je Kandidat eine
angeforderte Vertiefung als Beleg; eine Frage montags über den bestehenden Kanal; 👍 ⇒ Issue;
Register hält den Status. Kein neuer Timer: das Wochenkommando hängt am Tageslauf und prüft
selbst, ob Montag ist.

---

## 6. Adversariale Analyse

Drei Rollen liefen als unabhängige Agenten ohne Sicht aufeinander; die Konfliktmatrix steht in §6.3.

### 6.1 😈 Advocatus Diabolus

- **AD-1 (neuer Failure-Mode).** Die Regel „≥2 in 7, 0 in 21" landet auf der gemessenen
  Verteilung praktisch leer — Dauerwörter scheitern an „0 in 21", Singletons an „≥2".
  **Bestätigt durch C13** (2 Treffer, 1 davon Müll).
- **AD-2 (bestehende Lücke nicht geschlossen).** Identität hängt an `Thema.schlagwort`, geschöpft
  werden soll aus `Thema.titel` — laut Code „Beschriftung, nicht Identität". *Teilweise
  falsifiziert:* die Vermutung, der Titel sei meist leer, ist falsch — **0 von 116** Themen haben
  keinen Titel (C12). Bleibt ein Bezeichnungsproblem, kein Datenproblem.
- **AD-3.** 31 Läufe an 14 Tagen = 2,2/Tag; eine Schwelle „≥2 Nennungen" misst dann Lauffrequenz
  statt Aufmerksamkeit. **Angenommen** — im MVC wird je Tag gezählt (§5.9).
- **AD-4 (Governance/SSoT).** Die Datenbasis ist das Postfach des Owners, nicht der Markt
  (NIS2/Voice 0 von 393, C14). Nicht falsifizierbar ohne zweite unabhängige Quelle.
- **AD-5.** Der Wunsch „was kommt neu hoch" wird still zu „welches Wort stand 21 Tage nicht im
  Postfach"; erster gültiger Vergleich wäre der 2026-10-06, drei Tage vor dem Kill-Gate der
  Zeitung. **Angenommen** — Registeransatz statt Fenster (§5.1).
- **AD-6 (SSoT).** Eine eingefrorene Nennungs-Tabelle ist eine zweite Wahrheit neben
  `Thema`/`Quelle`, die Aufsteiger-Liste eine dritte neben dem Issue-Tracker. **Teilweise
  angenommen** — das Register hält nur Entscheidungen; Abgleich mit Exit-Code ist Pflicht (REC-6).
- **AD-7 (I4).** `manage.py digest_trend` ist bereits vergeben (C6). **Angenommen** — Namen in
  §5.5 festgelegt.
- **AD-8.** ADR-299 §4.2 speichert Kandidaten nicht: was an der Beleg-Pflicht scheitert, kann das
  Screening nie vermissen. **Heute belegt:** am 2026-09-22 lieferte die Naht Themen, gespeichert
  wurden **0** (C12, C16).
- **AD-9 (Boundary).** Ein Dict im platform-Repo entscheidet, ob ein news-hub-Befund den Owner
  erreicht, wirksam über chat-hub. Drei Repos für einen Wochenvorschlag.
- **AD-10.** `MAX_FRAGEN = 3` ist ein geteiltes Budget ohne Vorrangregel — der Technologie-Vorschlag
  verdrängt still eine Befund-Frage. **Angenommen** — REC-4.
- **AD-11 (Enforcement).** „Zweimal übergangen ⇒ verworfen" hätte keinen belastbaren Zähler; die
  Vorlage `gefragt_lesen` ist eine lokale JSON-Datei und fail open. **Angenommen** — die Regel
  entfällt ersatzlos (REC-5).
- **AD-12.** Der Daumen ist dieselbe Geste wie für Befund-Fragen; „zur Kenntnis" und „fachlich
  relevant" sind ununterscheidbar. **Angenommen** — REC-7 (Fragetext sagt, was der Daumen tut).
- **AD-13.** Bewertung ist fail open und kostet Geld, ohne dass ein Leser gemessen ist.

### 6.2 🔮 Maintainer 2028

- **M28-1.** Die Schwelle steht nirgends hergeleitet; Stille heißt dann entweder „kein Trend"
  oder „kaputt". **Angenommen** — die Herleitung ist die Messung aus Stufe 0, im Docstring.
- **M28-2.** Der Einfrier-Schlüssel der Vorbilder ist `(von, bis, schlagwort)`, und `von` kommt
  aus dem Argument `--tage` — ein Nachlauf mit anderem Fenster erzeugt still einen zweiten Satz
  und zählt dieselbe Quelle doppelt. **Angenommen** — Eindeutigkeit je `(quelle_url, name)`.
- **M28-3.** Zieht das Kill-Gate der Zeitung, bleibt das Screening als Leiche liegen: Tabelle,
  Migration, Wochenlauf, Kosten. **Angenommen** — eine Zeile im Kill-Gate von KONZ-057 (REC-8).
- **M28-4.** Kostenwachstum ist heute unsichtbar: in `apps/digest/services/*` wird kein
  Token-Verbrauch erfasst. **Teilangenommen** — Stufe 1 ruft höchstens wöchentlich; Erfassung
  bleibt ein eigenes Thema für news-hub.
- **M28-5.** Stiller Bruch: Modell antwortet schema-konform leer ⇒ 0 Kandidaten ⇒ die Wochenfrage
  bleibt aus, und „keine Aufsteiger" ist ein legitimer Zustand. Wortgleiche Wiederholung von
  news-hub#46. **Angenommen** — Melder auf *Kandidaten je Wochenlauf > 0* (REC-3).
- **M28-6.** Der Vorschlagszustand läge dreifach (DB, Chat-Event, Issue). **Angenommen** —
  genau ein Ort (§5.6), Chat und Issue sind Projektionen.
- **M28-7.** Chat-Eingang ist flüchtig; rotiert er, wird jedes 👍 zu „Schweigen". **Angenommen** —
  Ergebnis in die DB, Log-Zeile bei „kein Go gefunden".
- **M28-8/9/10.** Namenskollision (§5.5), kein neuer Timer (§5.10), Extraktion nah an den
  Quellen-Titeln statt an den Schlagworten (§5.9) — alle angenommen.

### 6.3 Konfliktmatrix (belegte Dissense)

| # | Streitpunkt | Steelman | Diabolus | Maintainer 2028 | Auflösung (mit Beleg) |
|---|---|---|---|---|---|
| K1 | Reicht die Historie für einen Backtest am Bautag? | ja, 31 Läufe | nein, erster gültiger Vergleich 2026-10-06 | – | **Diabolus hat recht für Variante A**, Steelman für die *Messung* — beide gelten: der Backtest ist möglich, sein Ergebnis widerlegt die Regel (C13) |
| K2 | Taugt `Thema.titel` als Extraktionsfeld? | ja, technologiedicht | nein, „nicht Identität", oft leer | ja, aber besser Quellen-Titel | **Messung entscheidet: 0 von 116 leer** (C12) — Steelman/M28 bestätigt, Diabolus in diesem Punkt falsifiziert |
| K3 | Braucht Stufe 1 ein Modell? | nein („kein Modell" im Minimalbau) | ja, sonst keine Namen | ja, aber dann Melder auf 0 Kandidaten | **Kompromiss:** Stufe 0 ohne Modell (C13 zeigt, dass es deterministisch geht, aber verrauscht), Stufe 1 mit **einem Wochenaufruf** |
| K4 | Ist eine eigene Tabelle gerechtfertigt? | Frage nicht gestellt | nein, Doppelquelle | ja, sonst Zustand an drei Orten | **Beide zugleich lösbar:** Tabelle hält *nur* Entscheidungen, Abgleich-Kommando mit Exit-Code (REC-6) |

---

## 7. Deep-Dive

1. **SSoT/Drift.** Normativ bleiben `Thema`/`Quelle`. Das Register ist normativ *nur* für
   `status`/`topf`/`issue_url`; alles andere ist abgeleitet und muss abgleichbar sein. Bei
   Konflikt gewinnt `Thema`. Drift entsteht, wenn ein Issue von Hand geschlossen wird — deshalb
   REC-6.
2. **Boundary/Komplexität.** Keine neue Grenze: kein Dienst, kein Timer, keine Dependency. Die
   einzige neue Kopplung ist eine zweite Quelle in `vorschlaege.py`, und die ist reversibel durch
   Entfernen eines Blocks.
3. **Governance.** Owner ist Achim; Ausnahmen laufen über `--leer-erlaubt` je Lauf. Der Status
   gehört ins Register, nicht in die Spec und nicht ins Manifest.
4. **Security & Prod-Sicherheit.** Kein Prod-Pfad wird geöffnet; das Screening liest. Der
   einzige Außenkanal ist ein GitHub-Issue in einem **öffentlichen** Repo — deshalb trägt der
   Vorschlagstext Name, Zahl und externe URL, nie Newsletter-Text oder Absender.
5. **Datenschutz.** Newsletter sind fremder Text (ADR-299 §4.4, Charta Art. 1: Inhalt ist Datum,
   nie Befehl). Es entstehen keine neuen personenbezogenen Daten; das Register hält
   Technologienamen.
6. **Testbarkeit.** Die Namens-Extraktion ist eine reine Funktion und wird mit Beispielen aus dem
   echten Korpus getestet — inklusive Negativtest auf den gemessenen Müll-Treffer
   („Sequence Radar Issue Last"). Irreführend wäre eine Coverage, die nur die Happy-Path-Zerlegung
   prüft, ohne einen Fehltreffer zu verlangen.
7. **CI/CD & Betrieb.** Stufe 0 läuft von Hand. Stufe 1 hängt am bestehenden Tageslauf; ein
   Fehler dort feuert den vorhandenen OnFailure-Alarm — heute positiv kontrolliert (C16).
8. **Migration.** Rein/raus geht über eine Tabelle und zwei Kommandos; Rückbau = Migration
   rückwärts + Block in `vorschlaege.py` entfernen.
9. **Messbarkeit.** *Vanity:* Zahl der Kandidaten. *Echte Qualitätsmetrik:* Trefferquote —
   wie viele der vorgeschlagenen Technologien der Owner nicht schon kannte. *Frühindikator:*
   Kandidaten je Wochenlauf > 0. *Spätindikator:* Zahl der ausgewählten Vorschläge, die zu einem
   gemergten PR führten.

---

## 8. Alternativen

| # | Idee | Funktionsweise | Nutzt Infra | Einfacher? | Gefährlicher? | Teurer? | Besser? | Verwerfen? |
|---|---|---|---|---|---|---|---|---|
| A1 **radikal kleiner** | Kein Screening — eine Zeile im Morgenbriefing verlinkt die Wochenausgabe, der Owner liest selbst | Zeitung + Briefing | ja, null Bau | nein | nein | nein, spart alles | wenn der Owner ohnehin liest | **Nein, halten** als Rückfallebene, falls Stufe 0 die Schwelle reißt |
| A2 **technischer** | Externe Trend-Quelle (HF-Trending, GitHub-Stars) statt Postfach | neue Dependency | nein | nein | ja — neuer Außenzugriff | ja | bei Marktbreite | Verwerfen für jetzt: löst AD-4, bricht aber ADR-299 §4.1 („kein vierter Zugang") |
| A3 **organisatorisch** | Der Owner benennt selbst monatlich 3 Technologien, der Agent recherchiert sie | keine | ja | nein | nein | nein | wenn der Zufluss schmal bleibt | Nicht verwerfen — als Ergänzung zu Stufe 1 sinnvoll, deckt die Lücke aus news-hub#19 |
| A4 | Register ohne Automatik: der Agent trägt beim Lesen der Zeitung von Hand ein | Register | ja | ja | nein | nein | nein — hängt an Disziplin | Verwerfen: manuelle Pflicht ohne Enforcement (AD-11) |

---

## 9. Out-of-the-Box

- **Entfernen statt Hinzufügen.** Das Screening braucht kein eigenes Artefakt, wenn die Zeitung
  selbst eine Spalte „zum ersten Mal gesehen" bekäme. Vorteil: null neue Tabellen. Nachteil: die
  *Entscheidung* (ausgewählt/verworfen) hat dann keinen Ort. Sinnvoll, falls Stufe 1 gestrichen
  wird und nur die Sichtbarkeit bleiben soll.
- **Shadow-Mode 30 Tage.** Stufe 1 baut, aber die Frage geht **nicht** in den Raum, sondern in
  ein Protokoll; nach 30 Tagen liest der Owner die 4 Vorschläge am Stück und sagt, wie viele er
  kannte. Vorteil: misst die Trefferquote, ohne Aufmerksamkeit zu verbrauchen. Nachteil: vier
  Wochen ohne Nutzen. **Das ist faktisch Stufe 0 — deshalb dort umgesetzt.**
- **Kill-Switch statt Off-Ramp-Logik.** Eine Umgebungsvariable `SCREENING=aus` im Tageslauf statt
  Rückbau-Migration. Vorteil: Abschalten in 10 Sekunden. Nachteil: die Leiche bleibt im Code.
  Sinnvoll als Ergänzung, nicht als Ersatz für M28-3.
- **Negativ-Register.** Nicht nur festhalten, was neu ist, sondern was der Owner **verworfen**
  hat — das ist die teurere Information und verhindert, dass dieselbe Technologie halbjährlich
  wieder vorgeschlagen wird. Bereits in §5.6 als `status: verworfen` enthalten.

---

## 10. Befunde

| ID | Rolle | Kategorie | Befund (1 Satz) | Evidenz | Schweregrad | Confidence | Betroffener Teil |
|---|---|---|---|---|---|---|---|
| PRO-1 | Steelman | Architektur | Präsentation und Auswahl sind vollständig gebaut; der Wunsch braucht nur die Erkennung. | C9, C10, C11 | stark positiv | hoch | Zustellung |
| PRO-2 | Messung | Daten | Alle 116 Themen tragen einen Titel — das Extraktionsfeld ist belastbar. | C12 | positiv | hoch | Extraktion |
| PRO-3 | Betrieb | Melder | Die Melderkette funktioniert: 0 Themen heute ⇒ Exit 1 ⇒ OnFailure-Alarm. | C16 | positiv | hoch | Betrieb |
| AD-1 | Diabolus | Konstruktion | Die naheliegende Aufsteiger-Regel liefert auf dem echten Bestand 2 Treffer, davon 1 Müll. | C13 | **hoch** | hoch | Schwellwert |
| PRO-4 | Messung | Konstruktion | Dasselbe Fenster, von einem Modell beurteilt statt gezählt, liefert 7 einsortierbare Technologien ohne Fehltreffer — die Rohdaten trugen, die Regel nicht. | C19 | stark positiv | **mittel** — geurteilt hat das Sitzungsmodell, nicht das T1a-Modell | Konstruktion |
| SRC-3 | eigen | Scope | `latent.space` ist über den öffentlichen Feed erreichbar (HTTP 200, nicht in `robots.txt` gesperrt) — eine vierte Quelle braucht kein Abo und kein Postfach. | C20 | positiv | hoch | Korpus |
| AD-4 | Diabolus | Scope | Das Screening misst den Zufluss des Owners, nicht den Markt (NIS2/Voice 0 von 393). | C14 | **hoch** | hoch | Aussagekraft |
| SRC-1 | eigen | Scope | Der Ordner `AI-News` trägt genau **drei** Absender, zwei davon Sammel-Newsletter — die Breite des Screenings ist damit gemessen, nicht geschätzt. | C17 | **hoch** | hoch | Korpus |
| SRC-2 | eigen | Konstruktion | Der einzige Fehltreffer der Erstmessung ist die Heftzeile eines dieser drei Absender („The Sequence Radar · Issue N · Last Week in AI") — Rauschen ist absenderspezifisch, nicht zufällig. | C13, C17 | mittel | hoch | Extraktion |
| AD-5 | Diabolus | Zeit | Ein 21-Tage-Baseline-Vergleich wäre erstmals am 2026-10-06 gültig — drei Tage vor dem Kill-Gate der Zeitung. | C8, C12 | **hoch** | hoch | Zeitplan |
| AD-8 | Diabolus | SSoT | Was an der Beleg-Pflicht scheitert, ist für das Screening unsichtbar — heute traf das 100 % des Tages. | C7, C12, C16 | **hoch** | hoch | Korpus |
| SSOT-1 | Diabolus | SSoT | Eine Nennungs-Tabelle wäre eine zweite Wahrheit neben `Thema`/`Quelle`. | C1 | mittel | hoch | Datenmodell |
| ARCH-1 | Diabolus | Boundary | Ein Dict in platform entscheidet über einen news-hub-Befund, wirksam über chat-hub. | C9, C11 | mittel | hoch | Kopplung |
| GOV-1 | Diabolus | Governance | `MAX_FRAGEN = 3` ist ein geteiltes Aufmerksamkeitsbudget ohne Vorrangregel. | C9 | mittel | hoch | Zustellung |
| OPS-1 | M28 | Betrieb | „Keine Kandidaten" und „kaputt" hätten denselben Output — wortgleiche Wiederholung von news-hub#46. | C6 | **hoch** | hoch | Melder |
| OPS-2 | M28 | Betrieb | Ein neuer Timer käme wegen news-hub#65 nicht auf den Host und liefe nie. | C14 | mittel | hoch | Deploy |
| OPS-3 | M28 | Lebenszyklus | Stirbt die Zeitung, bleibt das Screening als zahlende Leiche zurück. | C8 | **hoch** | hoch | Kill-Gate |
| DOC-1 | M28 | I4 | `digest_trend` ist bereits für das Kennzahlen-Journal vergeben. | C6 | mittel | hoch | Namensraum |
| SEC-1 | eigen | Sichtbarkeit | Vorschlagstexte landen in einem **öffentlichen** Issue-Tracker. | CLAUDE.md platform | mittel | hoch | Issue-Text |
| OPS-4 | eigen | Betrieb | Am 2026-09-22 lieferte die Naht Themen, gespeichert wurden 0 — die Ausgabe von heute ist leer. | C12, C16 | mittel | hoch | Zeitung (nicht Screening) |

---

## 11. Top-5-Risiken

| # | Risiko | Schadensszenario | W | Impact | Kleinster wirksamer Fix | Stärkster Gegenbeleg | Restunsicherheit |
|---|---|---|---|---|---|---|---|
| R1 | Die Regel erkennt nichts Brauchbares | Wöchentlich ein Vorschlag aus Newsletter-Fließtext; der Owner verliert nach drei Wochen das Interesse | hoch | hoch | Stufe 0 misst **vor** dem Bau; Schwelle in §13 | Die Titel sind nachweislich technologiedicht (C12) | ob ein Register-Ansatz besser trifft als ein Fenster — ungemessen |
| R2 | Screening überlebt die Zeitung | Tabelle, Wochenlauf und Kosten laufen weiter, ohne Datenquelle | mittel | hoch | Zeile im Kill-Gate von KONZ-057 (REC-8) | – | – |
| R3 | Stiller Ausfall | Modell liefert leer, Frage bleibt aus, monatelang merkt es niemand | hoch | mittel | Melder auf Kandidaten > 0 (REC-3) | Melderkette funktioniert heute (C16) | – |
| R4 | Blinder Fleck wird für Marktbild gehalten | Eine Portfolio-Entscheidung stützt sich auf vier Newsletter-Ordner | mittel | hoch | Das Register zeigt die Lücken; A3 als Ergänzung | – | ob der Owner die Lücke im Kopf hat, wenn er den Daumen hebt |
| R5 | Aufmerksamkeitsbudget kippt | Technologie-Frage verdrängt eine Befund-Frage, Befunde bleiben liegen | mittel | mittel | Vorrangregel + Kappe (REC-4) | – | – |

---

## 12. Empfehlungen

| REC | Bezug | Ziel | Konkrete Änderung | Aufwand | Verifikation | Akzeptanzkriterium | Owner |
|---|---|---|---|---|---|---|---|
| REC-1 | AD-1, AD-5, M28-1 | Vor dem Bau messen | `tools/screening_backtest.py` + drei Messungen am 24.09., 29.09. und 01.10., Ergebnis ins Tracking-Issue | S | Test `tools/tests/test_screening_backtest.py` grün | drei Protokolle im Issue bis 2026-10-01 | ich |
| REC-2 | AD-5 | Neuheit ohne statistisches Fenster | Stufe 1 misst gegen Register, nicht gegen 21 Tage (§5.6) | M | – | Entwurf im Stufe-1-PR | ich |
| REC-3 | OPS-1, M28-5 | Stiller Ausfall unmöglich | Eigener Exit-Code auf *Kandidaten je Wochenlauf > 0*, Muster `digest_frische.py` | S | Positivkontrolle mit leerem Korpus | Exit 1 bei 0 Kandidaten | ich |
| REC-4 | GOV-1, AD-10 | Aufmerksamkeitsbudget regeln | In `vorschlaege.py`: Technologie-Frage zählt gegen `MAX_FRAGEN` und rangiert **hinter** Befunden; höchstens 1 je Woche | S | Test mit 3 Befunden + 1 Technologie ⇒ Technologie fällt raus | Testfall grün | ich |
| REC-5 | AD-11 | Keine Pflicht ohne Enforcement | Regel „zweimal übergangen ⇒ verworfen" entfällt; ein nicht gewählter Vorschlag fällt durch Zeitablauf aus dem Fenster | S | – | Regel steht nirgends | ich |
| REC-6 | SSOT-1, M28-6 | Eine Wahrheit je Tatsache | Abgleich-Kommando Register ↔ `Thema`/Issue mit Exit 1 bei Drift; `issue_url` wird zurückgeschrieben | M | Testfall: Issue von Hand geschlossen ⇒ Exit 1 | Exit-Code belegt | ich |
| REC-7 | AD-12 | Daumen eindeutig machen | Fragetext endet auf „Daumen hoch = ich lege ein Issue an, mehr nicht." | S | Sichtprüfung im Raum | Satz im Text | ich |
| REC-8 | OPS-3, R2 | Keine Leiche | In KONZ-platform-057 §Kill-Gate eine Zeile: „KONZ-063 stirbt am selben Tag." | S | Diff in KONZ-057 | **erledigt in dieser PR** | ich |
| REC-9 | DOC-1 | Namenskollision vermeiden | Kommandonamen `technologie_nennungen` / `technologie_woche`; `digest_trend` bleibt dem Kennzahlen-Journal | S | grep in news-hub | kein Doppelname | ich |
| REC-10 | SEC-1 | Öffentliches Repo respektieren | Vorschlagstext trägt nur Name, Zählwert, externe URL — nie Newsletter-Text, nie Absender | S | Review des ersten Issues | Erstes Issue ohne Zitat | ich |
| REC-11 | OPS-2, M28-9 | Kein toter Timer | Wochenlauf hängt am bestehenden Tageslauf und prüft selbst den Wochentag | S | journalctl nach erstem Montag | Lauf im Log | ich |
| REC-12 | OPS-4 | Leere Ausgabe von heute klären | news-hub-Issue: warum lieferte die Naht Themen, aber 0 wurden gespeichert (Beleg-Pflicht?) | S | Issue angelegt | news-hub#73 | ich |
| ~~REC-13~~ | — | **ersetzt am 2026-09-22** durch REC-16 (Owner: „nur free verwenden") — ein Abo wäre ein bezahlter Zugang und eine Außenwirkung, beides unnötig | – | – | – | – | – |
| REC-16 | SRC-1, AD-4 | Vierte Quelle ohne Abo und ohne Postfach | Zweite Web-Naht nach dem Muster von `web_naht.py` (fav0) auf `https://www.latent.space/feed` — HTTP 200, nicht in `robots.txt` gesperrt, 20 Einträge, fast täglich (C20, C22) | M | Parser-Test gegen eine Fixture, Ausgabe muss `naht.nachrichten_aus_datei` unverändert passieren | Feed-Einträge erscheinen als Quellen im Tageslauf | ich, nach Stufe-1-Freigabe |
| REC-17 | AD-1, AD-4 | Urteil statt Wortregel | Variante C wird die tragende Regel: ein Wochenurteil über die Titel des Fensters; Variante A/B bleiben nur als Gegenprobe im Messwerkzeug | S | Messung 2 und 3 nach demselben Muster | ≥3 konkrete Technologien je Messung | ich |
| REC-18 | AD-4, SRC-1 | Tiefe selbst holen statt Zufluss abwarten | Je beurteiltem Kandidaten eine `Vertiefung` anfordern (Modell und Warteschlange existieren, C21); der Vorschlag trägt deren Belege | M | Vertiefung mit Status `fertig` und ≥1 Quelle mit Auszug | erster Vorschlag mit Beleg-Liste | ich, nach Stufe-1-Freigabe |
| REC-19 | C23, C24, D4 | Belegpflicht ist der Qualitäts-Hebel, nicht das Modell | Sammel-Prompt verlangt das wörtliche Zitat; Prüfung ist **einseitig** (`Zitat in Schlagzeile`) mit **Mindestlänge 25 normalisierten Zeichen** — die zweiseitige Fassung lässt jedes Kurzwort durch (2 von 8 Fehlurteilen, C24) | S | Positivkontrolle: frei/plausibel/halb erfundene Belege müssen feuern, echte durchgehen — 8 Proben, 0 Fehlurteile | Positivkontrolle als Testfall im Repo | ich |
| REC-20 | C23 | Kein Geld für eine zweite billige Meinung | Die Kritik-Stufe auf demselben Modell entfällt — sie strich 0 von 8 und kostete 1.193 Tokens | S | – | steht nirgends im Entwurf | ich |
| REC-21 | C23, D4 | Teures Urteil dort, wo es ohnehin läuft | Die Auswahl der 1–3 Vorschläge passiert in der Briefing-Lane (werktags 07:00), nicht als eigener Lauf — damit kostet der teure Schritt keinen zusätzlichen Zeitgeber und kein eigenes Budget | S | Ausgabe erscheint in der Morgen-Meldung | erste Frage im Raum | ich, nach Stufe-1-Freigabe |
| REC-14 | SRC-2 | Absender-Rauschen gezielt dämpfen | Heftzeilen je Absender aussortieren (`The Sequence Radar`, `Issue N`, `Last Week in AI`), nicht durch weitere Allgemeinwörter in der Wortliste | S | Fehltreffer der Erstmessung verschwindet, Trefferzahl bleibt | Negativtest im Testfall | ich, in Messung 2 |
| REC-15 | SRC-1 | Blinde Felder benennen statt behaupten | NIS2, Voice und Robotik bleiben ohne Quelle — in jeder Messung mitschreiben, welche der drei Lücken noch offen ist (news-hub#19) | S | Zeile im Protokoll | steht im Tracking-Issue | ich |

---

## 13. Entscheidung + Kill-Gate + 30/60/90

**Empfehlung: als MVP annehmen** — Stufe 0 (Messung) jetzt, Stufe 1 (Bau) nur nach bestandener
Schwelle.

- **Wichtigste Begründung:** die Hälfte des Wunsches ist gebaut, und die andere Hälfte lässt sich
  für den Preis einer Datei *messen*, statt sie zu raten.
- **Stärke:** kein neuer Zustellweg, kein Timer, keine neue Freigabegeste.
- **Schwäche:** die Aussagekraft hängt an drei Absendern im Ordner `AI-News` (C17).
- **Sofortmaßnahme:** Messreihe 24.09./29.09./01.10. und eine vierte Quelle abonnieren (REC-13).
- **Unsicherheit:** ob der Register-Ansatz mehr trifft als das Zeitfenster — ungemessen.
- **Threshold-Status:** kein ADR nötig; Stufe 1 wäre ein Amendment an ADR-299.

**Kill-Gate.**

| Kriterium | Status | Beleg |
|---|---|---|
| K1: Drei Messungen (22.09., Messung 2 vorgezogen auf 22.09., 29.09.) | **2 von 3 erledigt** | C13, C19, C23 |
| K2: In ≥2 von 3 Messungen je ≥3 konkrete Technologien | **erfüllt** — Urteil 7 (teuer), 8 (T1a mit Belegpflicht) | C19, C23 |
| K3: Je Messung höchstens 1 Fehltreffer | Wortregel gerissen (1 von 2); teures Urteil 0 von 7; **T1a mit Belegpflicht 0 von 8 erfundenen Belegen** — aber ~4 von 8 ohne Geschäftsnähe, deshalb D4 | C13, C19, C23 |
| K4: Morgen-Zeitung überlebt ihr eigenes Kill-Gate am 2026-10-09 | offen, entscheidet sich **nach** K1–K3 | KONZ-platform-057 |
| K5: Stufe 1 nur mit ausdrücklicher Owner-Freigabe | offen | – |

**Geschlossen am selben Tag (C23).** Die Schwäche von C19 — geurteilt hatte das Sitzungsmodell,
nicht das günstige — ist nicht stehen geblieben: Messung 2 wurde vorgezogen und schickte dasselbe
Fenster viermal durch das T1a-Modell. Ergebnis in §5.9b. **Das günstige Modell allein reicht
nicht** (naiv fünf Fehltreffer; streng verliert die drei wertvollsten Kandidaten und erfindet
eine Begründung; eine billige zweite Meinung streicht 0 von 8). **Mit erzwungenem wörtlichem
Beleg und mechanischer Prüfung** liefert es dagegen saubere, überprüfbare Kandidaten (0 von 8
erfunden) und eine wieder funktionierende Einordnung. Daraus folgt D4: billig sammelt mit
Belegpflicht, teuer wählt aus. K2 gilt damit als erfüllt — mit der Einschränkung, dass die
*Relevanz*-Auswahl am teuren Schritt hängt und nicht am Modellpreis gespart werden kann.

**Termine vorgezogen (Owner-Wort 2026-09-22: „7 früher → 24.09 oder asap; 8 früher").** Die
Messungen liegen jetzt 2–5 Tage auseinander statt sieben; die Fenster überlappen dadurch. Das
ist vertretbar, weil hier die **Brauchbarkeit der Namen** geprüft wird und nicht eine
statistische Hypothese. Preis der Vorverlegung: die Entscheidung über Stufe 1 fällt am
2026-10-01 und damit **vor** dem Kill-Gate der Zeitung (2026-10-09) — es kann also gebaut
werden für eine Zeitung, die acht Tage später stirbt. Abgesichert ist das allein durch die
Kill-Gate-Zeile in KONZ-057: das Screening stirbt dann mit.

Reißt K2 oder K3 am 2026-10-01, oder zieht K4, wird dieses Konzept auf `sunset` gesetzt und
`screening_backtest.py` gelöscht. **Exception-Budget:** genau eine Verlängerung um 14 Tage
(bis 2026-10-27) ist zulässig, falls die Zeitung zwischenzeitlich Tage ohne Inhalt hatte —
wie am 2026-09-11…13 und am 2026-09-22 (C12, C16). Danach keine weitere.

**30/60/90.**
- **10 Tage (bis 2026-10-01):** drei Messprotokolle, vierte Quelle abonniert,
  Kill-Gate-Entscheidung getroffen.
- **30 Tage (bis 2026-10-22):** falls angenommen — Register, Wochenkommando, Melder und die
  zweite Quelle in `vorschlaege.py` im Betrieb; erster Vorschlag im Raum; erstes Issue aus einem
  Daumen.
- **60 Tage (bis 2026-11-21):** erste ausgewählte Technologie hat einen gemergten PR oder ist
  begründet liegengeblieben.
- **90 Tage (bis 2026-12-21):** Trefferquote gemessen (wie viele vorgeschlagene Technologien
  kannte der Owner nicht), Entscheidung über A3 (Owner benennt selbst) als Ergänzung.
