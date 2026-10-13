---
concept_id: KONZ-platform-071
title: Raum-Rechte je Chatraum — eine Wahrheit, technisch erzwungen, billig requalifizierbar
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []   # keine SoR-Spec: Governance-/Perimeter-Konzept, kein Fachmodul (ADR-211 greift nicht)
adr_threshold: Amendment   # an ADR-308 (Sandbox-Front) und an die Registry-Meta (Ratifikation, 5er-Grenze); kein neuer ADR
review_by: 2026-12-31
kill_criteria: "Stufe 1 bis 2026-11-15 nicht gemergt ODER Requalifikation nach Stufe 4 kostet den Owner > 30 min je Modellwechsel ODER Abgleich Manifest↔Rechte-Datei > 7 Tage rot ohne Fix"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "iilgmbh/chat-hub: deploy/lotse_session.sh", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C2, source_path: "iilgmbh/chat-hub: deploy/lotse_raum_chat.sh", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C3, source_path: "iilgmbh/chat-hub: deploy/raum-sessions/achim/settings.json", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C4, source_path: "iilgmbh/chat-hub: deploy/raum-sessions/achim/befehle.txt", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C5, source_path: "iilgmbh/chat-hub: deploy/raum-sessions/achim/auftrag-repos.yaml", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C6, source_path: "iilgmbh/chat-hub: tests/test_raum_sessions.py", commit_or_pr: d227693, opened_in_session: true}
  - {claim_id: C7, source_path: registry/lotse-authorizations.yaml, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C8, source_path: docs/governance/model-rebaseline-runbook.md, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C9, source_path: docs/adr/ADR-308-sandbox-werkstatt-als-weiterentwicklungs-template.md, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C10, source_path: tools/sandbox/egress_proxy.py, commit_or_pr: "#3695", opened_in_session: true}
  - {claim_id: C11, source_path: tools/sandbox/vorschlagsregister.md, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C12, source_path: governance/melder-register.yaml, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C13, source_path: docs/konzepte/KONZ-platform-025-lotsen-charta.md, commit_or_pr: 82012117, opened_in_session: true}
  - {claim_id: C14, source_path: "lokal: Modellwechsel-Protokoll des Session-Start-Hooks", commit_or_pr: "—", opened_in_session: true}
created: 2026-10-13
---

# KONZ-platform-071 — Raum-Rechte je Chatraum

## 1 Executive Summary

Der Owner will drei Klassen von Chaträumen:
- Der Raum **Achim/Lotse** wird schrittweise freier.
- Ein neuer Raum **Lotse/Achim-Sandbox** arbeitet ohne Einschränkungen, aber nur in der Org `iilsandbox`.
- **Alle anderen Räume** (Schulung, Privates, Telefon) bekommen keine oder ausdrücklich festgelegte Rechte (Owner-Wort 2026-10-13).

Die Idee ist richtig. Heute ist die Grundregel allerdings falsch herum umgesetzt: Ein Raum ohne Rechte-Datei läuft mit allen Rechten des Hosts.

Das Konzept fügt drei Dinge hinzu, auf die der Owner-Fokus zielt:
1. **Eine Wahrheit**: ein Manifest je Raum, das auf die Vollmachten-Registry verweist, statt sie zu kopieren.
2. **Technische statt erzählte Grenzen**: Start nur mit Profil, der Raum ist an seine eigene Raum-ID gebunden, Ratifikation auch für Rechte-Dateien.
3. **Billige Requalifikation**: Köder-Tests als ausführbarer Drill. So setzt ein neues Modell sofort auf dem Stand auf, bekommt das Vertrauen aber erst nach einem grünen Lauf.

Der Sandbox-Raum ist **keine** freie Host-Session. Er ist eine schmale Chat-Front zum bestehenden ADR-308-Container. „Ohne Einschränkungen" gilt nur im Container.

## 2 Scope & Evidenzbasis

**Im Umfang:**
- Rechte der Raum-Sessions (`iilgmbh/chat-hub`, privat).
- Verknüpfung mit der Vollmachten-Registry und der Charta (platform).
- Anbindung an die Sandbox-Werkstatt (ADR-308).

**Nicht im Umfang:**
- Live-Bot ohne Kapitäns-Sitzung (chat-hub#48, eigener Charta-Entscheid).
- Inhalt einzelner Vollmachten.
- Matrix-Serverkonfiguration.

**Evidenz:** Belegt sind alle Aussagen mit `C<n>` im Frontmatter. Drei unabhängige Prüfer (Steelman, Advocatus Diabolus, Maintainer-2028) haben die Quellen getrennt gelesen. Ihr Dissens steht in §6.2.

**Korrekturen an der Ausgangslage (E2):**
- Egress-Allowlist und Secret-Scan der Sandbox sind seit #3695 gebaut und werden vor jedem Lauf aufgerufen (C9, C10). ADR-308 nennt sie an einer Stelle noch „fehlen noch". Das ist Doku-Drift und wird in Stufe 3 nachgezogen.
- Aktiv sind **5** Vollmachten, nicht 6 (C7). Eine hat den Status `gate-dokumentiert`.

**Öffentliches Repo:** Sicherheitsbefunde stehen hier nur als Befundklasse. Ausnutzungswege, Raum-IDs, Hostnamen und Zugangsdatei-Namen stehen nicht im Dokument. Die Einzelheiten gehören in ein Issue im privaten chat-hub, Freigabe `scope +chat-hub`.

## 3 Infrastruktur-Fit (Ist, gemessen)

| # | Fakt | Beleg |
|---|---|---|
| I1 | Startskript: Liegt eine Rechte-Datei vor, läuft der Raum mit Positivliste und `dontAsk`. Fehlt sie, startet er ohne jede Einschränkung und erbt die Host-Rechte (31 Freigaben, darunter Fernzugriff). | C1 |
| I2 | Nur der Raum `achim` hat eine Rechte-Datei (39 allow, 10 deny). Fünf weitere Raum-Ordner haben keine. | C1, C3 |
| I3 | Der Chat-Wrapper nimmt eine beliebige Ziel-Raum-Angabe an. Nur ohne Angabe gilt der eigene Raum. | C2 |
| I4 | Die Rechte-Datei von `achim` erlaubt Lesen, Monitor und Web-Abruf ohne Muster. | C3 |
| I5 | Ein Befehl wird angeboten (Mail senden), für den die Rechte-Datei kein Muster hat. Das ist ein Schein-Recht. | C3, C4 |
| I6 | Die Tests prüfen Rechte-Dateien nur für `achim`. Die Web-Grenze wird nur als Text im Brief geprüft. | C6 |
| I7 | Die Registry kennt keine Räume. chat-hub verweist nirgends auf die Registry (0 Treffer). | C7 |
| I8 | Die Ratifikationsregel (GitHub-APPROVE) greift nur bei Änderungen an der Registry, nicht an Rechte-Dateien in chat-hub. | C7 |
| I9 | Die 5er-Grenze aktiver Vollmachten ist erreicht. 9 von 10 Einträgen laufen am selben Tag ab (2027-02-06). | C7 |
| I10 | Der Modellwechsel-Melder meldete zwischen 05.10. und 13.10. sechsmal MAJOR, im Wechsel zwischen zwei Modellfamilien. Er misst das Modell der interaktiven Sitzung, nicht das des Raums. | C14 |
| I11 | Realfall 2026-09-03: Bei einem MAJOR-Wechsel hat der Owner alle Vollmachten pauschal neu erteilt, statt sie requalifizieren zu lassen. | C7, C8 |
| I12 | Die Repo-Aufträge im Raum `achim` haben schon eine Stufenleiter: gesperrt, pr, merge. Aufstieg nach 3 Abnahmen, Abstieg automatisch bei Fehler. | C5 |
| I13 | Die Sandbox (ADR-308) hat Selbstprüfung (Token nur `iilsandbox`), `cap-drop ALL`, Budget-Wächter, Egress-Allowlist und Secret-Scan. Der Container-Agent läuft ohne Rückfragen. | C9, C10 |

## 4 Steelman

Rechte gehören an den Raum und nicht an die Sitzung. Freiheit gibt es dort, wo eine Fehlwirkung nichts kostet (Sandbox). Vertrauen wächst dort, wo es belegt ist (Achim). Geschlossen bleibt, wo Dritte mitlesen.

Der Mechanismus existiert schon (I1), die Stufenleiter auch (I12), und die Sandbox ist reifer als angenommen (I13). Die Idee verallgemeinert also laufende Muster, statt neue zu erfinden. Sie setzt Charta Art. 1 („nur die Kapitäns-Session ist Kommandokanal") und Art. 2.4 (Nie-Kandidaten) technisch durch.

**Nicht abschwächen:**
- „Ohne Einschränkungen" im Container. Teilsperren zerstören den Lernwert der Werkstatt.
- „Andere Räume ohne Rechte". Das ist kein Übermaß, sondern die Umkehr eines falschen Defaults.

## 5 Konzeptdefinition

### 5.1 Zielzustand (ein Satz)

Jeder Raum startet nur mit einem Profil aus **einem** Manifest. Was er darf, steht dort einmal, verweist für alles mit Außenwirkung auf eine Vollmacht und wird technisch erzwungen. Ein neues Modell bekommt das Vertrauen über einen ausführbaren Drill zurück, nicht über Handarbeit.

### 5.2 Bausteine

| # | Baustein | Wirkt gegen |
|---|---|---|
| B1 | **Fail-closed-Start**: Ohne Manifest-Eintrag startet kein Raum. | I1 |
| B2 | **Raum-Bindung**: Der Chat-Wrapper lehnt jede fremde Ziel-Raum-Angabe ab. Nachrichten anderer Absender als des Kapitäns werden bei der Beobachtung als Daten markiert. Werkzeugaufrufe gibt es nur auf Kapitäns-Nachrichten. | I3, Charta Art. 1 |
| B3 | **Manifest** `deploy/raum-rechte.yaml` (chat-hub) mit Profilen. Ein Generator erzeugt daraus die Rechte-Dateien, ein CI-Abgleich prüft Manifest gegen Datei. Jedes Recht mit Außenwirkung trägt `lv: LV-0xx`. | I7, I5 |
| B4 | **Brief ohne Rechte-Prosa**: Der Abschnitt „Reichweite" im Brief wird aus dem Manifest erzeugt. | dritte Wahrheit |
| B5 | **Ratifikation erweitert**: Änderungen an Manifest, Rechte-Dateien und Repo-Auftragsstufen brauchen das GitHub-APPROVE des Kapitäns (CODEOWNERS plus Pflicht-Review in chat-hub). | I8 |
| B6 | **Enge statt pauschale Freigaben**: Lesen nur per Positivliste, Web-Abruf nur für benannte Domänen, Monitor nur für die Raum-Beobachtung. | I4 |
| B7 | **Requalifikation als Drill**: Jedes Recht hat `assessed_with` und mindestens einen Köder-Fall. Der Drill startet den Raum ohne Oberfläche gegen jeden Köder und prüft die **technische** Abweisung. Der Owner setzt nur das APPROVE auf den Bericht. | I11 |
| B8 | **Modellbindung je Raum**: Das Startskript vergleicht das Raum-Modell mit `assessed_with`. Bei MAJOR startet der Raum eine Profilstufe tiefer, bis der Drill grün ist. Der Melder misst das Raum-Modell, nicht die interaktive Sitzung. | I10 |
| B9 | **Sandbox-Front**: Der Raum `sandbox` hat ein Profil, das nur den Chat-Wrapper und den Aufruf `tools/sandbox/sandbox.sh <Auftragskarte>` erlaubt. Den Rückweg liest ein eigenes Profil: nur Lesen, kein Netz. Übernahme nur als PR. | D1, D8 |
| B10 | **Brief und Rechte aus `origin/main`**: Eine lokal geänderte Arbeitskopie startet nicht (chat-hub#97). | „wirksam erst per PR" nur behauptet |

### 5.3 Profile (Vorschlag, Owner-Entscheid O1)

| Profil | Rechte | Für |
|---|---|---|
| `leer` | nichts, Start verweigert | Default, jeder Raum ohne Eintrag |
| `chat` | nur Chat-Wrapper im eigenen Raum | Schulung, Telefon |
| `lesen` | `chat` plus Lesen in benannten Pfaden | Privates, Briefing |
| `sandbox-front` | `chat` plus Auftragskarte an die Sandbox | Lotse/Achim-Sandbox |
| `achim` | wie heute, verengt nach B6, Erweiterung nur per Stufe | Kapitän |

**Telefon bekommt keinen Kalender.** Termine des Owners an Dritte herauszugeben ist Handeln im Namen Dritter und damit ein Nie-Kandidat nach Charta Art. 2.4. Das korrigiert den ersten Vorschlag RS1.

### 5.4 Wo die Wahrheit liegt (SSoT-Prüfung)

| Frage | Ort | Grund |
|---|---|---|
| Welche Handlung mit Außenwirkung, welcher Reifegrad, welche Grenzen? | Registry (platform) | Charta 2.6, besteht schon |
| Welches Werkzeug-Muster in welchem Raum? | Manifest (chat-hub, privat) | Muster verraten Infrastruktur, sie gehören nicht ins öffentliche Repo |
| Verbindung | `lv:`-Verweis plus CI-Abgleich | Verweis statt Kopie, daher keine zweite Wahrheit |

Verworfen ist die Variante „alles in die Registry". Sie würde Werkzeugmuster veröffentlichen, solange platform öffentlich ist (KONZ-039).

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus (verdichtet)

| ID | Einwand | Schwere | Antwort im Konzept |
|---|---|---|---|
| D1 | Die Sandbox-Raum-Session läuft auf dem Host, ist also keine Sandbox. | hoch | B9: eine schmale Front, frei nur im Container |
| D2 | Ohne Rechte-Datei gelten alle Host-Rechte, und Tests decken nur `achim` ab. | hoch | B1, Test über alle Raum-Ordner |
| D3 | Breite Freigaben (Lesen, Monitor, Web-Abruf) machen das Werkzeug zur eigentlichen Grenze, mit möglichem Abflusskanal. Für Monitor ist das eine **Hypothese**, ungeprüft. | hoch | B6, Köder-Lesetest auf Zugangsdateien |
| D4 | Die Raum-Trennung ist nur behauptet (I3). | hoch | B2 |
| D5 | Drei Quellen: Registry, Rechte-Datei, Repo-Auftragsstufen. Gelesen wird aus der Arbeitskopie. | hoch | B3, B10 |
| D6 | Die Ratifikation greift nicht bei Rechte-Dateien. Viele Einzelfreigaben erzeugen die Last vom 2026-09-03. | hoch | B5, wenige Profilstufen statt Einzelfähigkeiten |
| D7 | Fremde Raumteilnehmer können per Nachricht Werkzeugaufrufe anstoßen. Telefon plus Kalender ist ein Nie-Kandidat. | hoch | B2, §5.3 |
| D8 | Der Rückweg aus dem Container ist ein Kanal für eingeschleuste Anweisungen. | mittel | B9: Leser-Profil ohne Netz, Übernahme nur per PR |
| D9 | Ein stärkeres Modell findet Seitenkanäle eher. Rechte-Dateien kennen kein `assessed_with`. | mittel | B7, B8, Red-Team-Köder je Upgrade |

**Die Annahme, die das Konzept am stärksten kippt:** „Ein Chatraum ist eine Rechte-Grenze." Ohne B1, B2 und B5 ist er das nicht. Es gibt ein Matrix-Konto, einen Host-Benutzer und ein gemeinsames Dateisystem. Deshalb ist Stufe 1 Pflicht vor jeder Erweiterung.

### 6.2 Konfliktmatrix (Dissens der drei Prüfer)

| Thema | Steelman | Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|
| Sandbox „ohne Einschränkungen" | nicht abschwächen, das Startskript ruft den Container statt `claude` | Raum-Session ist Host-Session, braucht eine enge Rechte-Datei | Invariante `token_orgs == [iilsandbox]` | **Beide haben recht, auf verschiedenen Ebenen.** Der Container-Agent erreicht Matrix nicht (Egress nur zu den API-Zielen), also braucht es eine Front. Front eng (B9), Container frei. |
| 5er-Grenze | Sandbox-Rechte zählen nicht, weil ohne Außenwirkung (H) | jeder Schritt löst den Sechs-Artefakt-Ausbau aus oder umgeht die Registry | Melder bei 5 von 5 | **Owner-Entscheid O2.** Empfehlung: Profilrechte ohne Außenwirkung zählen nicht, die Regel steht dann ausdrücklich in der Registry-Meta. |
| Granularität der Erweiterung | Aufstieg je Fähigkeit nach Zähler | Einzelfreigaben erzeugen Freigabe-Müdigkeit | Schatten-Modus vor jeder Erweiterung | **Profilstufen als Freigabe-Einheit**, Zähler je Fähigkeit nur als Beleg. Ein APPROVE je Stufe, Drill automatisch. |
| Sichtbar oder verhindern | Melder als Wartung | „sichtbar" ersetzt kein „verhindern" | neun Melder | **Grenzen technisch** (B1, B2, B5, B6), Melder nur für Wartung und Verfall. Fünf Melder statt neun (§7.3). |
| Brief als Rechte-Quelle | — | — | sonst drei Wahrheiten | übernommen als B4 |

Keine Divergenz gab es bei: Egress und Secret-Scan existieren (alle drei), Default „geschlossen" ist richtig (alle drei).

## 7 Deep-Dive

### 7.1 Zukünftiges Modell setzt verzugslos auf (Owner-Fokus 1)

Heute braucht ein neues Modell etwa 25 Dateien, rund 3500 Zeilen und zwei Quellen außerhalb jedes Repos, um zu wissen, was ein Raum darf (Maintainer-Kaltstart-Test). Nach Stufe 2 ist es **eine** Datei plus Verweise.

Der Hebel liegt aber woanders. I10 und I11 zeigen zusammen: Requalifikation, die bei jedem Familienwechsel Handarbeit kostet, wird übersprungen. Deshalb:

1. **Drill statt Prüfgespräch** (B7). §3a des Runbooks wird ein Testlauf. Der Owner setzt je Profilstufe ein APPROVE auf den Bericht.
2. **Raum-Modell statt Sitzungs-Modell** (B8). Ein Wechsel der interaktiven Sitzung zwischen Familien löst keine Raum-Requalifikation aus. Nur ein neues `RAUM_MODEL` löst sie aus. Das beendet das Flattern aus I10.
3. **Kaltstart-Abnahme**: Ein frisches Modell liest nur das Manifest und beantwortet 10 Fragen („Darf Raum X Y? Seit wann? Beleg?"). Die Antworten werden gegen den generierten Sollwert verglichen.
4. **Vertrauen bleibt nicht übertragbar** (Charta 2.5). Das neue Modell erbt die Struktur sofort und startet eine Stufe tiefer. Die Stufe zurück bekommt es nach dem grünen Drill, in Minuten statt Tagen.

### 7.2 Continuous Improvement (Owner-Fokus 2)

Kein neues System. Die vorhandenen Signale laufen als **Entwurf** zum Owner. Der Lotse öffnet nie selbst einen PR auf Rechte (Charta-Kurzform 3).

| Signal | Schwelle | Ergebnis |
|---|---|---|
| `dontAsk`-Ablehnungen im Raum-Transkript (Format **H**, nicht geöffnet) | ≥3 gleiche in 14 Tagen | Antragsentwurf „Recht X für Profil Y" mit Belegzitaten |
| Abnahmen der Repo-Aufträge (I12) | wie heute 3 in Folge | unverändert, nur als Beleg an die Profilstufe gehängt |
| Fehler-Grad ≥2 (Charta 2.2) | 1 Fall | Rückstufungs-Entwurf |
| ungenutztes Recht | 60 Tage | Entzugs-Entwurf |

Die Entwürfe landen im vorhandenen Vorschlagsregister-Muster (C11), nicht in einem neuen Ordner.

### 7.3 Predictive Maintenance (Owner-Fokus 3)

Fünf Melder, jeder mit Leser im Melder-Register (C12):

| Melder | Signal | Schwelle | Leser |
|---|---|---|---|
| Ablauf-Klippe | `expires_at` der Registry | 45 Tage vorher, WARN wenn ≥3 am selben Tag (heute 9 von 10) | Owner |
| Raum ohne Profil | Raum-Ordner ohne Manifest-Eintrag | ab 1 | Sitzungsagent, PR-Entwurf |
| Pfad-Drift | Befehl oder Muster ohne Gegenstück (I5) | ab 1 | Sitzungsagent |
| Ruhender Raum | letzte Aktivität | > 28 Tage | Owner: stilllegen oder bestätigen |
| Modell-Abstand | `RAUM_MODEL` gegen `assessed_with` | MAJOR | Owner, Drill vor dem nächsten Start |

Verworfen: Token-Ablauf (deckt `0.7.25` schon ab) und 5er-Grenze (ist nach O2 eine Regel, kein Melder).

## 8 Alternativen

| Alternative | Warum nicht |
|---|---|
| A1 Je Raum ein eigener Host-Benutzer | stärkste Trennung, aber ein Matrix-Konto bleibt für alle Räume, und der Betrieb verdoppelt sich. Kandidat, falls B2 in Stufe 1 nicht hält. |
| A2 Alles in die Registry | veröffentlicht Werkzeugmuster (§5.4) |
| A3 Nur RS1 (fail-closed), kein Manifest | schließt I1, lässt aber zwei Wahrheiten und teure Requalifikation stehen. Ist gleichzeitig Stufe 1 dieses Konzepts. |

## 9 Out-of-the-Box

| Idee | Preis | Kill-Kriterium |
|---|---|---|
| **Schatten-Recht**: Ein neues Recht läuft 7 Tage nur protokolliert (Charta-Stufe C), bevor es wirkt. | ~2 Tage, Hook-Modus „log statt deny" | nach 3 Erweiterungen hat das Schattenprotokoll keine Entscheidung geändert |
| **Rotes Team als Raum**: wöchentliche Köder-Nachrichten Dritter in einen Testraum | ~3 Tage plus geringe Token-Kosten | 8 Wochen ohne Befund und ohne neuen Köder |
| **Rechte-Kontoauszug**: montags Raum × Recht × genutzt × abgelehnt × läuft ab | ~1 Tag | Owner öffnet ihn 4 Wochen lang nicht |
| **Verfall durch Nichtnutzung**: Ein Recht ohne Nutzung in 90 Tagen fällt weg, Verlängerung durch Gebrauch | 1 Feld plus Melder | Owner holt > 2 Rechte je Quartal manuell zurück |

## 10 Befunde (sofort relevant)

| ID | Befund | Lage heute | Zug |
|---|---|---|---|
| F1 | Räume ohne Rechte-Datei hätten Host-Rechte | keiner läuft | bis Stufe 1 keinen anderen Raum als `achim` starten |
| F2 | Raum-Grenze nur im Prompt (I3) | `achim` aktiv genutzt | Stufe 1 |
| F3 | breite Freigaben in `achim` (I4) | aktiv | Stufe 1 |
| F4 | Schein-Recht Mail senden (I5) | harmlos, aber verwirrend | Stufe 1: Befehl entfernen |
| F5 | ADR-308 nennt Egress und Secret-Scan noch als fehlend | Doku-Drift | Stufe 3 |
| F6 | Modellwechsel-Melder flattert (I10) | 6× MAJOR in 9 Tagen | Stufe 4 (B8) |

## 11 Top-5-Risiken

1. **Freigabe-Müdigkeit** (Realfall 2026-09-03): Gegenmittel sind Profilstufen und Drill statt Einzelprüfung.
2. **Raum-Bindung hält nicht**, weil Matrix-Konto und Host geteilt sind: Fallback ist A1.
3. **Generator und Hand-Edit laufen auseinander**: CI-Abgleich, Kill-Kriterium (c).
4. **Drill prüft Prompt statt Technik**: Der Drill wertet nur die `dontAsk`-Ablehnung und den Exit-Code, nie die Modellantwort.
5. **5er-Grenze blockiert alles**: O2 vor Stufe 3.

## 12 Empfehlungen und Stufenplan

| Stufe | Inhalt | Repo | Gate |
|---|---|---|---|
| 0 | dieses Konzept | platform | Merge |
| 1 Dichtmachen | B1, B2, B6, Schein-Recht weg, Test über alle Raum-Ordner, B10 | chat-hub | `scope +chat-hub`, APPROVE (Rechte-Änderung) |
| 2 Eine Wahrheit | B3, B4, B5, `lv:`-Abgleich | chat-hub, platform (Registry-Meta) | APPROVE, O3 |
| 3 Sandbox-Raum | B9, ADR-308-Amendment (Front plus Doku-Drift) | chat-hub, platform | APPROVE, O2, Pilot mit 3 Auftragskarten |
| 4 Billiger Modellwechsel | B7, B8, Kaltstart-Abnahme | chat-hub, platform (Runbook §3a) | ein grüner Drill auf dem laufenden Modell |
| 5 Wartung | 5 Melder (§7.3), Entwürfe (§7.2) | platform | Melder-Register-Check grün |
| danach | `achim` je Profilstufe erweitern | chat-hub | APPROVE je Stufe |

**Ablaufform (Step 2a):** Der Drill ist eine feste Kette ohne Schleife: je Köder ein Lauf und ein Abgleich. Das Abbruchkriterium ist die Anzahl der Köder.

## 13 Entscheidung, Kill-Gate, 30/60/90

**Entscheidungen (Owner):** Owner-Wort 2026-10-13 10:20: „scope +chat-hub · RS1 go · RR1 go · RR2 go · RR3 go · RR4 go“. Im Board hießen O1–O4 RR1–RR4, Stufe 1 hieß RS1.
- **O1** Profile nach §5.3, Telefon ohne Kalender. **Entschieden (RR1 go).**
- **O2** Profilrechte ohne Außenwirkung (`chat`, `lesen`, `sandbox-front`) zählen nicht zur 5er-Grenze. Die Regel kommt ausdrücklich in die Registry-Meta. **Entschieden (RR2 go).** Der Registry-Eintrag selbst steht noch aus, siehe unten.
- **O3** Ratifikation (APPROVE) gilt auch für Rechte-Dateien in chat-hub. **Entschieden (RR3 go).**
- **O4** Ruhende Räume stilllegen statt profilieren. Betroffen sind die drei Raum-Ordner ohne Aktivität seit 2026-09-05; neu nur mit Profil. **Entschieden (RR4 go).** Erweitert um den Raum-Ordner `risk-hub` (Owner-Wort „RR5 go“, 2026-10-13).
- **Freigabe-Identität:** Rechte- und Governance-PRs eröffnet die GitHub App `lotse-autor`, der Owner approvt. Ein zweites Personenkonto ist kein Freigabe-Weg. **Entschieden (Owner-Wort „RA1 go“, 2026-10-13; [#3916](https://github.com/achimdehnert/platform/issues/3916)).**

**Umsetzungsweg (2026-10-13):** Stufe 1 ist als Auftrag in iilgmbh/chat-hub#184 spezifiziert, mit den Detailbefunden. Die Lotse-Sitzung baut Rechte-Änderungen nicht selbst. Der Auto-Mode-Klassifikator hat schon das Lesen der Raum-Rechte zur Änderung als Self-Approval gesperrt, im Einklang mit Charta-Kurzform Punkt 3. Das gilt auch für den Registry-Eintrag zu O2. Beides baut eine vom Owner dafür gestartete Sitzung oder der Owner selbst. Gemergt wird mit Owner-APPROVE.

**Nachtrag 2026-10-13 nachmittags:** Stufe 1 ist mit dem Owner-Mandat „scope +chat-hub · RS1 go“ und der neuen Freigabe-Identität gebaut. chat-hub#186 wurde um 12:06Z gemergt, der Code-Owner-Review für die Rechte-Dateien gilt seit 12:10Z (K8). Der Merge lief ohne Approve, der Schutzschalter kam erst danach. Der Owner hat den Inhalt nachträglich bestätigt (Owner-Wort „M1 go“, 13:12Z). Befund und Lehre stehen in [Retro e50644](../retros/session-retro-2026-10-13-platform-e50644.md). Offen bleibt die Live-Abnahme am 2026-10-14 um 05:00, der erste Briefing-Lauf mit Profil. Weiter aus steht auch der Registry-Eintrag zu O2.

**30/60/90:** 30 Tage: Stufe 1 und 2 · 60 Tage: Stufe 3 und 4 · 90 Tage: Stufe 5 und erste Profilstufe für `achim`.

**Kill-Gate:**
- (a) Stufe 1 ist bis 2026-11-15 nicht gemergt: Das Konzept schrumpft auf A3.
- (b) Die Requalifikation kostet nach Stufe 4 den Owner mehr als 30 Minuten je Modellwechsel: Der Drill-Ansatz wird verworfen.
- (c) Der Abgleich Manifest↔Rechte-Datei ist länger als 7 Tage rot ohne Fix: Der Generator wird verworfen, die Rechte-Datei bleibt Quelle.

**Exception-Budget:** bis 2026-11-15 darf `achim` mit den Befunden F2 und F3 weiterlaufen, nur mit dem Kapitän im Raum.

| Kriterium | Status | Beleg |
|---|---|---|
| (a) Stufe 1 bis 2026-11-15 gemergt | erfüllt | iilgmbh/chat-hub#186, gemergt 2026-10-13 12:06Z |
| Stufe 1 live abgenommen | offen | erster Briefing-Lauf 2026-10-14 05:00, iilgmbh/chat-hub#184 |
| Code-Owner-Review für Rechte-Dateien (K8) | erfüllt | chat-hub-Ruleset seit 2026-10-13 12:10Z |
| Registry-Meta-Regel zu O2 | offen | [#3916](https://github.com/achimdehnert/platform/issues/3916) |
| (b) Requalifikation ≤ 30 min je Modellwechsel | offen | — |
| (c) Abgleich nie > 7 Tage rot | offen | — |
| O1–O4 entschieden | erfüllt | Owner-Wort 2026-10-13 10:20 |
| Stufe 1 spezifiziert | erfüllt | iilgmbh/chat-hub#184 |

**Enforcement-Grenze:** `review_by` und `kill_criteria` wirken erst, wenn ein Lifecycle-Gate sie liest. Bis dahin sind sie ein Review-Gate, kein Exit-Code.
