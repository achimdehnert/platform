---
concept_id: KONZ-platform-064
title: Paperless — Pflichtfelder Korrespondent/Dokumenttyp und Aufbewahrung je Dokumenttyp
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []            # kein Klickdummy/Spec-Bezug — doc-hub ist ein betriebener Fremdstack, keine ADR-211-Anwendung
adr_threshold: Amendment   # ADR-144 beschreibt die Wahl, nicht die Nutzungskonvention
review_by: 2026-12-23
kill_criteria: "Wenn 60 Tage nach Einfuehrung der Pflichtfelder der Anteil neuer Dokumente ohne Korrespondent ODER ohne Dokumenttyp ueber 20 % liegt, ist die Konvention ohne Durchsetzung wirkungslos und wird zurueckgenommen statt verschaerft."
evidence_manifest:
  - {claim_id: C1, source_path: "docs/adr/ADR-144-doc-hub-paperless-ngx.md", commit_or_pr: "7348114b", opened_in_session: true}
  - {claim_id: C2, source_path: "hetzner-prod:iil_dochub_db/paperless (psql)", commit_or_pr: "Messung 2026-09-23", opened_in_session: true}
  - {claim_id: C3, source_path: "hetzner-prod:/opt/doc-hub/scripts/auto-title.py", commit_or_pr: "md5 cf0b8ce6…", opened_in_session: true}
  - {claim_id: C4, source_path: "deployment/stacks/doc-hub/auto-title.py", commit_or_pr: "md5 3a094c1f…", opened_in_session: true}
  - {claim_id: C5, source_path: "https://github.com/achimdehnert/platform/issues/2083", commit_or_pr: "#2083", opened_in_session: true}
  - {claim_id: C6, source_path: "https://github.com/achimdehnert/doc-hub/issues/18", commit_or_pr: "doc-hub#18", opened_in_session: true}
  - {claim_id: C7, source_path: "hetzner-prod:iil_dochub_web /usr/src/paperless/consume", commit_or_pr: "Messung 2026-09-23", opened_in_session: true}
created: 2026-09-23
---

# KONZ-platform-064 — Paperless: Pflichtfelder und Aufbewahrung

> Auftrag: [platform#3414](https://github.com/achimdehnert/platform/issues/3414).
> **Tier T2**, weil das Konzept eine neue dauerhafte Konvention in einem betriebenen System
> setzt (zwei Pflichtfelder) und ein persistentes Artefakt darin anlegt (Aufbewahrungsfrist
> je Dokumenttyp). Kein T3: ein System, ein Repo, keine SSoT-Verschiebung, keine neue
> Abhaengigkeit.

## Kernthese

Paperless ist gut gewaehlt und wird getragen — was fehlt, ist nicht ein Werkzeug, sondern
die Antwort auf die Frage „wie lange muss das hier liegen bleiben", und die kann heute
niemand geben, weil das einzige Feld mit genau einem Wert je Dokument bei 60 % der Ablage
leer ist.

## Steelman — warum der heutige Zustand gut ist

Die Ablage funktioniert. 1410 Dokumente, jedes davon getaggt, kein einziges ohne Schlagwort;
in acht Wochen sind 584 dazugekommen, ohne dass der Einzug geklemmt haette. Die Titel werden
automatisch gebaut, das Dokumentdatum aus dem Inhalt gelesen, der Jahres-Tag daraus abgeleitet,
Steuerrelevantes weitergereicht — und das alles laeuft seit Monaten, ohne dass jemand es
taeglich anfassen muesste. Volltextsuche ueber OCR macht die leeren Strukturfelder im Alltag
kaum spuerbar: wer eine Rechnung sucht, findet sie ueber den Text.

Wer hier „60 % unvollstaendig" ruft, misst an einer Ordnung, die im Betrieb bisher niemand
gebraucht hat. Das ist die ehrliche Gegenposition zu diesem Konzept, und sie ist nicht schwach:
die Felder sind genau deshalb leer, weil die Suche auch ohne sie trug.

Der Punkt, an dem sie kippt, ist ein anderer als die Suche — es ist die Frage nach der
Aufbewahrung. Die beantwortet kein Volltext.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | 1410 Dokumente, 864 ohne Korrespondent, 849 ohne Dokumenttyp, 0 ohne Tag | Annahme→belegt | C2, psql gegen `documents_document`; Gegenprobe: dieselbe Abfrage findet 4176 Tag-Zuordnungen, die Null ist kein Filterfehler | belegt |
| L2 | Das Vokabular steht bereits: 17 Dokumenttypen, 49 Korrespondenten, durchweg sprechend | Annahme→belegt | C2; `Rechnung` 297, `Bescheid` 70, `Vertrag` 48, `Kontoauszug` 15 | belegt |
| L3 | Der Dokumenttyp ist das einzige Feld mit **genau einem** Wert je Dokument | Entscheidung | Paperless-Datenmodell: `document_type_id` ist FK, Tags sind m:n | belegt |
| L4 | Aufbewahrungsfristen existieren heute nirgends — auch nicht als Notiz | Annahme→belegt | C2: `documents_customfield` = 0; kein Retention-Feature in Paperless 3.0.4 | belegt |
| L5 | Die Nachbearbeitung ist **kein** Systemproblem — 379 `Posteingang` gehen auf eine Urlaubsvertretung zurueck | Annahme | Owner-Auskunft 2026-09-23 | akzeptiert |
| L6 | Der Jahres-Tag ist **nicht** die Dopplung von `created` | Annahme→belegt | C2: 26 von 1312 weichen ab, 1 Dokument traegt zwei Jahres-Tags; C3: `auto-title.py` leitet den Tag aus dem **Dokumentdatum im Text** ab (`jahres_tag_setzen`, `dokumentdatum_bestimmen`), nicht aus `created` | belegt, These verworfen |
| L7 | Die Automatik laeuft, aber als Post-Consume-Skript, nicht als Paperless-Workflow | Annahme→belegt | C2: `documents_workflow` = 0, `documents_storagepath` = 0; C3: `auto-title.py` setzt Titel, Datum, Jahres-Tag, Rechte und leitet Steuer-Relevantes weiter | belegt |
| L8 | Die Host-Kopie des Skripts weicht von der Repo-Kopie ab | Risiko | C3 19629 B / md5 `cf0b8ce6…` gegen C4 18354 B / md5 `3a094c1f…`; bereits erfasst als doc-hub#18 (C6) | offen, **fremd verfolgt** |
| L9 | 381 Dateien liegen im Einzug unter `consume/schleuse/` — 354 JPG, 20 `.safetensors` | Risiko | C7; damit ist Akzeptanzkriterium 2 aus #2083 (C5) messbar **nicht** erfuellt | offen, **fremd verfolgt** |
| L10 | Zwei Pflichtfelder ohne Durchsetzung sind eine Bitte, keine Konvention | Risiko | Erfahrung mit den Kfz-Kostenstellen (#3341): dort traegt eine Pruefung im Werkzeug die Regel, nicht die Absicht | offen → MVC |

**L8 und L9 gehoeren nicht in dieses Konzept.** Beide sind gemessen worden, waehrend die
Grundlage fuer dieses Konzept erhoben wurde, und beide haben bereits einen Vorgang
(doc-hub#18 bzw. #2083). Sie stehen hier als Messwert, nicht als Arbeitspaket — die Zahlen
sind an den jeweiligen Vorgang gemeldet.

## MVC — kleinster tragfaehiger Schnitt

**Ausfuehrungsform** (Step 2a): Frage 1 — braucht es mehrere Schritte? Nein. Eine Abfrage,
ein Bericht. **Ein Aufruf, keine Kette, kein Graph, keine Schleife.**

1. **`tools/paperless_bestand.py`** (neu, platform) — ein Kommando, das die Kennzahlen aus L1
   erzeugt: Dokumentanzahl, Anteile ohne Korrespondent / ohne Dokumenttyp, Tag-, Korrespondenten-
   und Typ-Inventar. Zweimal ausgefuehrt identisch. Loest Akzeptanzkriterium 1 aus #3414 und
   ersetzt die handgeschriebene psql-Zeile.
2. **Aufbewahrungstabelle** als Abschnitt in diesem Dokument (unten) — je der 17 vorhandenen
   Dokumenttypen eine Frist oder ein ausdrueckliches „keine Frist, weil …". Kein neues Feld
   in Paperless, solange die Tabelle nicht steht; ein leeres Custom-Field waere eine zweite
   Wahrheit ohne Inhalt.
3. **Pflichtfeld-Messung statt Pflichtfeld-Zwang.** Paperless kann die beiden Felder nicht
   erzwingen. Der Bericht aus (1) zeigt den Anteil der **in den letzten 30 Tagen** eingelaufenen
   Dokumente ohne Korrespondent/Typ. Das ist die Zahl, an der das Kill-Gate haengt.

Bewusst **nicht** im MVC: Custom-Fields anlegen, Workflows konfigurieren, Speicherpfade setzen,
Altbestand nachpflegen, Korrespondenten auf sevdesk-Kontakte abbilden. Jedes davon ist ein
eigener Schritt, der erst Sinn ergibt, wenn die Tabelle aus (2) steht.

## Aufbewahrung — zwei kurze Listen statt einer langen Tabelle

**Owner-Einwand 2026-09-23, und er traegt:** die meisten Dokumente im Bestand sind keine
Rechnungen, sondern eigene Unterlagen. Fuer die gibt es keine gesetzliche Frist, und bei
1,7 GB Archivgroesse gibt es auch keinen Druck, irgendetwas loszuwerden. Eine Frist je
Dokumenttyp ueber alle 17 Typen haette fuer zwei Drittel des Bestands eine Frage beantwortet,
die niemand stellt.

Gemessen am 2026-09-23: 399 Dokumente tragen einen Finanz-Typ, 161 einen privaten,
849 gar keinen; Tag `Steuer-relevant` 174; Medienordner 1,7 GB.

Deshalb bleiben nur die zwei Listen, die etwas entscheiden:

**Liste 1 — muss auf Verlangen vorlegbar sein** (§147 AO, 10 Jahre ab Jahresende):
`Rechnung` (297) · `Abrechnung` (51) · `Mahnung` (21) · `Kontoauszug` (15) · `Quittung` (8) ·
`Gutschrift` (2) · `Auftrag` (1) · `Lohnabrechnung` (0). Zusammen **395** Dokumente.
Der Zweck ist **Auffindbarkeit**, nicht Loeschung — bei einer Pruefung muss der Beleg
kommen, nicht verschwinden.

**Liste 2 — darf nie verloren gehen** (dauerhaft, Prioritaet bei Sicherung und Wiederherstellung):
`Bescheid` (70) · `Vertrag` (48) · `Steuerbescheid` (5) · `Versicherungsschein` (5) ·
`Befund`/`Arztbrief` (4). Zusammen **132** Dokumente.

**Alles Uebrige: keine Frist.** Das ist eine Entscheidung, kein Versaeumnis, und sie wird
hier einmal festgehalten, damit die Frage nicht jaehrlich wiederkommt. Betroffen sind
`Mitteilung`, `Angebot`, `Praesentation` und der gesamte typlose Bestand.

Grundlage: §147 AO und die Owner-Haltung „100 % GoBD ist meist unrealistisch" (2026-07-29).
Die Listen ordnen, sie beraten nicht — und sie gelten fuer Eigenbedarf, **nicht** fuer
LRA-Workloads.

## Befunde inkl. Advocatus Diabolus

| # | Befund | Herkunft | Antwort |
|---|---|---|---|
| B1 | „Pflichtfeld" ohne technischen Zwang ist eine Bitte | Diabolus | Anerkannt. Deshalb misst der MVC statt zu behaupten, und das Kill-Gate kippt die Konvention statt sie zu verschaerfen |
| B2 | Eine Fristentabelle in einem Dokument ist keine Loeschung | Diabolus | Richtig. Sie ist auch nicht als solche gemeint — ohne beantwortete Frist gibt es keinen Loeschvorgang, der sie nutzen koennte. Automatisches Loeschen bleibt ausdruecklich draussen |
| B3 | Erzeugt die Tabelle eine zweite Wahrheit neben Paperless? | SSoT-Pruefung | Solange kein Custom-Field existiert, ist sie die **einzige** Wahrheit. Sobald eines angelegt wird, wird die Tabelle zu dessen Quelle und das Dokument verweist darauf — nicht umgekehrt |
| B4 | Der Maintainer 2028 findet 17 Typen und eine Tabelle — was, wenn ein 18. Typ entsteht? | Maintainer-2028 | Der Bericht aus dem MVC listet Typen ohne Frist. Ein neuer Typ faellt darin auf, ohne dass jemand daran denken muss |
| B5 | Warum nicht einfach den Steuerberater fragen, statt eine Tabelle zu bauen? | Diabolus | Weil die Frage „welche Frist" erst gestellt werden kann, wenn die Klassen benannt sind. Die Tabelle ist die Vorlage fuer genau dieses Gespraech |

## Alternativen

| # | Alternative | Warum nicht |
|---|---|---|
| A1 | Custom-Field „Aufbewahrung bis" je Dokument pflegen | 1410 Dokumente einzeln — die Frist gehoert an die Klasse, nicht an das Einzelstueck. Als Folgeschritt sinnvoll, sobald die Klassentabelle steht |
| A2 | Aufbewahrung ueber Tags abbilden (`10-jahre`, `dauerhaft`) | Tags sind m:n und bereits 107 Stueck. Ein Dokument koennte zwei widersprechende Fristen tragen — genau das, was der Dokumenttyp ausschliesst (L3) |

## Top-3-Risiken

| # | Risiko | Eintritt erkennbar an | Gegenmittel |
|---|---|---|---|
| R1 | Die Pflichtfelder bleiben eine Absichtserklaerung, weil Paperless sie nicht erzwingt | Anteil neuer Dokumente ohne Typ/Korrespondent sinkt nach 60 Tagen nicht unter 20 % | Kill-Gate zieht: Konvention zuruecknehmen, nicht verschaerfen |
| R2 | Die Fristentabelle wird beschlossen und danach nie wieder angefasst; ein 18. Dokumenttyp entsteht ohne Frist | Bericht listet einen Typ ohne Frist | Der Bericht aus dem MVC prueft das bei jedem Lauf — der Typ meldet sich selbst |
| R3 | Die Tabelle wird als Rechtsauskunft gelesen und traegt eine Loeschung, die sie nicht decken kann | Jemand loescht ein Dokument mit Verweis auf dieses Konzept | Automatisches Loeschen bleibt ausserhalb des Scope; die Tabelle ordnet, sie autorisiert nicht |

## Kill-Gate

**Schwelle:** 60 Tage nach Einfuehrung der Pflichtfelder liegt der Anteil der neu eingelaufenen
Dokumente ohne Korrespondent **oder** ohne Dokumenttyp ueber 20 %.

**Dann:** Die Konvention wird zurueckgenommen, nicht verschaerft. Begruendung im Voraus: wenn
zwei Felder bei taeglicher Nutzung nicht nebenbei gefuellt werden, ist der Aufwand hoeher als
der Nutzen, und eine strengere Regel wuerde denselben Befund nur lauter wiederholen.

**Exception-Budget:** einmalig 30 Tage Verlaengerung, wenn eine Urlaubsvertretung die Messung
verzerrt (wie bei L5). Datiert, nicht wiederholbar.

| Kriterium | Status | Beleg |
|---|---|---|
| Bericht `tools/paperless_bestand.py` existiert und ist zweimal identisch | offen | — |
| Aufbewahrungstabelle je Dokumenttyp vom Owner entschieden | offen | — |
| Anteil neuer Dokumente ohne Korrespondent/Typ < 20 % nach 60 Tagen | offen | Messung ab Einfuehrung |
| Kein Dokumenttyp ohne Frist-Entscheidung | offen | — |

## Abgrenzung zu laufenden Vorgaengen

| Vorgang | Gegenstand | Verhaeltnis |
|---|---|---|
| [#2083](https://github.com/achimdehnert/platform/issues/2083) | doc-hub-Stack versioniert, Schleuse aus dem Einzug, Mailversand | L9 ist ein frischer Messwert dazu, kein neuer Vorgang |
| [doc-hub#18](https://github.com/achimdehnert/doc-hub/issues/18) | `auto-title.py` nur auf prod geaendert | L8 ist die Bezifferung dazu |
| [#3102](https://github.com/achimdehnert/platform/issues/3102) | sevdesk-Routinen, Tag `verbuchen` | Der Dokumenttyp `Gutschrift` (L3) beruehrt die Vorzeichen-Falle — Vorschlag, kein Umbau |
| [ADR-144](../adr/ADR-144-doc-hub-paperless-ngx.md) | Wahl des Systems | Bleibt gueltig. Dieses Konzept ist ein Amendment-Kandidat zur **Nutzung**, nicht zur Wahl |
