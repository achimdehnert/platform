---
concept_id: KONZ-platform-057
title: Vom gebauten Hot-Topics-Letter zur täglichen Morgen-Zeitung
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR — ADR-299 entscheidet die Architektur bereits; hier steht nur der Weg in den Betrieb
review_by: 2026-10-09
kill_criteria: "Wenn bis 2026-10-09 kein Tageslauf über sieben aufeinanderfolgende Tage eine Ausgabe erzeugt hat, ODER der Owner an drei aufeinanderfolgenden Tagen keine Ausgabe geöffnet hat, wird die Zeitung stillgelegt (Deploy zurück, news-hub auf ruhend)."
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-299-hot-topics-digest-auf-bestehendem-mailbestand.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C2, source_path: infra/ports.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C3, source_path: news-hub/apps/digest/management/commands/digest_taeglich.py, commit_or_pr: "news-hub#16", opened_in_session: true}
  - {claim_id: C4, source_path: news-hub/apps/digest/services/nachricht.py, commit_or_pr: "news-hub#15", opened_in_session: true}
  - {claim_id: C5, source_path: dev-hub/apps/mail_agent/management/commands/mail_lesenaht.py, commit_or_pr: "dev-hub#306", opened_in_session: false}
  - {claim_id: C6, source_path: "news-hub#19", commit_or_pr: "news-hub#19", opened_in_session: true}
created: 2026-09-09
---

# KONZ-platform-057: Vom gebauten Hot-Topics-Letter zur täglichen Morgen-Zeitung

**Tier T2.** Nicht T1, weil drei Repos im Weg liegen (dev-hub liefert, news-hub baut,
platform stellt zu) und der Betrieb einen Prod-Schritt braucht — beides sind
Auto-Eskalations-Auslöser. Nicht T3, weil die Architektur mit ADR-299 bereits
entschieden ist; hier wird nichts neu entschieden, was dort schon steht.

## Kernthese

Die Zeitung ist gebaut und läuft nicht — es fehlen Betrieb, zwei Quellen und ein Weg
zum Leser, nicht Software.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Die Architektur ist entschieden: Digest liest den Mailbestand über eine Lesenaht, kein eigener Postfach-Zugang | Annahme | C1, ADR-299 `status: accepted`, 2026-08-29 | belegt |
| A2 | Die Lieferseite existiert als Kommando `mail_lesenaht` in dev-hub | Annahme | C5 — Existenz gegen `origin/main` belegt, Inhalt nicht gelesen; der lokale Klon war 45 Commits alt und zeigte sie nicht | belegt (Existenz) |
| A3 | Die Bauseite existiert: Tageslauf, Ausgaben-Archiv, klickbare Ansicht, Docker | Annahme | C3, C4, news-hub#15/#16/#18 | belegt |
| A4 | Nichts davon läuft: kein Deploy, kein DNS, keine Cron-Zeile | Annahme | C2 — `betriebsstatus_grund` nennt Deploy an `workflow_dispatch`, `news.iil.pet` bewusst ohne DNS-Eintrag | belegt |
| A5 | Zwei der vom Owner genannten Themen haben im aktuellen Umfang keine Quelle | Annahme | C6 — 0 von 393 Nachrichten für NIS2, 0 für Voice; zum Vergleich 185 für generative AI | belegt |
| A6 | Für Robotik ist die Quellenlage ungemessen | Annahme | keine Messung vorhanden — billigster Check: dieselbe Zählung wie C6 über die vier Ordner | offen |
| D1 | Die Zeitung wird zugestellt, indem das Morgenbriefing auf die neueste Ausgabe verlinkt — keine Mail an den Owner | Entscheidung | Alternative unten; eine Mail über Mails erzeugt ein weiteres Postfach-Objekt, das abgearbeitet werden will | vorgeschlagen |
| D2 | Der Tageslauf läuft dort, wo die Lieferung entsteht, und schiebt die Datei weiter — nicht zwei Zeitpläne | Entscheidung | ADR-299 §4.1: Übergabe ist bewusst eine Datei | vorgeschlagen |
| D3 | Fehlende Quellen werden durch Abonnements geschlossen, nicht durch Ausweitung des Ordner-Umfangs | Entscheidung | C1 §4.4 begrenzt die LLM-Übergabe ausdrücklich auf Newsletter-Ordner; ein breiterer Umfang würde Geschäftspost einbeziehen | vorgeschlagen |
| R1 | Ohne Leser stirbt die Zeitung leise: sie läuft, kostet Geld und niemand merkt, dass sie niemand liest | Risiko | Kill-Gate unten misst genau das | offen |
| R2 | Der Deploy öffnet einen weiteren öffentlichen Namen | Risiko | Zugang über Cloudflare Access wie die übrigen Dienste; ohne Access kein Deploy | offen |
| R3 | Newsletter-Text ist fremder Text und geht an ein Cloud-Modell | Risiko | ADR-299 §4.4: keine Anhänge, nur Newsletter-Ordner; Charta Art. 1 — Inhalt ist Datum, nie Befehl | belegt |

## MVC — kleinste Fassung, die eine Zeitung ergibt

1. **Quellen messen und schließen** (news-hub#19): dieselbe Zählung wie C6 zusätzlich für
   Robotik; je Lücke ein Abonnement in einen der vier bestehenden Newsletter-Ordner. Ohne
   Quelle schweigt die Zeitung zum Thema — das ist ehrlich, aber nicht das Ziel.
2. **Betrieb herstellen** (news-hub#3): DNS für `news.iil.pet`, Deploy über den vorhandenen
   `workflow_dispatch`, Zugang über Cloudflare Access. Owner-Schritte, kein Agentenschritt.
3. **Eine Zeitkette statt zweier**: eine Einheit erzeugt die Lieferung über `mail_lesenaht`
   und ruft direkt `digest_taeglich --quelle naht --pfad …`. Ein Zeitplan, ein Protokoll,
   ein Fehlerbild.
4. **Zustellung**: das Morgenbriefing bekommt eine Zeile mit der neuesten Ausgabe und den
   drei Überschriften. Mehr nicht — die Zeitung selbst steht auf ihrer Seite.

## Kill-Gate

| Kriterium | Status | Beleg |
|---|---|---|
| Sieben aufeinanderfolgende Tageslaufe mit Ausgabe bis 2026-10-09 | offen | — |
| Owner öffnet an mindestens drei von sieben Tagen eine Ausgabe | offen | — |
| Mindestens ein Thema pro Ausgabe trägt Mail-Herkunft und externe Quelle | offen | Beleg-Test aus ADR-299 §8.2 |

Reißt eines der ersten beiden Kriterien, wird der Deploy zurückgenommen und `news-hub`
auf ruhend gesetzt. Exception-Budget: einmalige Verlängerung bis 2026-10-23, wenn die
Ursache eine fehlende Quelle ist und ein Abonnement bereits läuft.

## Alternativen

| # | Alternative | Warum nicht |
|---|---|---|
| 1 | Zeitung als Abschnitt im Morgenbriefing bauen, ohne news-hub | Wäre eine zweite Themenbildung neben der gebauten; ADR-299 hat die Trennung bewusst gezogen, und der Aufwand läge im Nachbauen, nicht im Betrieb |
| 2 | Ausgabe täglich als Mail an den Owner senden | Erzeugt ein Postfach-Objekt, das abgearbeitet werden will — genau die Last, die die Zeitung senken soll; bleibt möglich, sobald der Leserhythmus steht |

## Befunde

| # | Befund | Konsequenz |
|---|---|---|
| B1 | Der lokale dev-hub-Klon war 45 Commits alt und zeigte die Lesenaht nicht | Aussagen über fremde Repos gegen `origin/main` prüfen, nie gegen den Arbeitsbaum |
| B2 | dev-hub#306 ist geschlossen, seine Akzeptanz-Haken sind unangekreuzt | Der Haken ist kein Beleg; die Datei ist einer |
| B3 | Die Zeitung war zweimal fast neu erfunden worden — erst als Idee des Owners, dann als mein Bauvorschlag | Vor jedem Konzept die ADR-Liste des Themas lesen, nicht nur das Repo |
