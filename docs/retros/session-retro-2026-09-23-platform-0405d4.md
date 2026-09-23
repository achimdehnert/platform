---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, meiki-hub, cad-hub, sqf-hub, ttz-hub, chat-hub]
session_id: 0405d4
footprint: deep
findings_total: 12
findings_survived: 5
refuted_rate: 0.58
phase3_refuted: 7
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [akte-geprueft-zustand-nicht, handover-in-public-repo-unredigiert]
recurring_findings: [claim-before-cheapest-check, built-but-never-called, deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded, gate-untested-command-handed-to-user-wirkungslos]
gates_caught: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
over_ask_klassen: [mail-versand-nach-textfreigabe]
over_act_klassen: []
widerlegung: "3 gekippt, 1 neu"
streichkandidaten: [retro-dimension-soll-ist-ohne-ueberlebende]
---

# Session-Retro 2026-09-23 — platform (0405d4)

Sitzung vom 2026-09-22 15:07 UTC bis 2026-09-23 07:45 UTC. Auslöser: eine Anfrage aus dem Raum Achim/Lotse, ob das Hochladen von Bauunterlagen beim Landratsamt über Schnittstellen lösbar sei. Daraus wurden ein T3-Konzept, ein Angebotsschreiben an den Kunden, zwei Produktions-Deploys und sechs berührte Repos.

## 1 · Executive Summary

- Der Auftrag ist erfüllt: Konzept gemergt, Schreiben und Vorschlag beim Kunden, Mail versendet.
- **Der teuerste Fehler war ein übersprungener Check.** Zwei neue Endpunkte galten als „in Betrieb", weil ein `GET` mit 405 antwortete. Ein `POST` gegen dieselbe Adresse lieferte 403 — es gab keinen Aufrufer. Behoben, in Produktion gegengeprüft.
- **Ein Klarname eines Dritten stand 13 Stunden 46 Minuten in einem öffentlichen Repo.** Die Sitzung hat den Befund selbst erzeugt und ihn als „keine Personendaten Dritter" fehleingeordnet — genau deshalb kam keine Sofortmaßnahme.
- Von zwölf Befunden halten fünf. Die Widerlegungsbahn hat zwei Einstufungen gesenkt und einen Befund gefunden, den keine der drei Ermittlungsrichtungen hatte.
- Die Ursache des Datenschutzfalls ist behoben, nicht nur der Fall: die Übergabe-Automatik bricht künftig ab, wenn das Zielrepo öffentlich ist.

## 2 · Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Klarname eines Ansprechpartners 13 h 46 min unredigiert im öffentlichen Repo; eigene Fehleinordnung „keine Personendaten Dritter" verhinderte die Sofortmaßnahme | Prozesslücke | kritisch | SURVIVES | [platform#3380](https://github.com/achimdehnert/platform/issues/3380) angelegt 15:07:22Z, redigiert 04:53:54Z; [#3234-Kommentar](https://github.com/achimdehnert/platform/issues/3234#issuecomment-5779111658) | handover-in-public-repo-unredigiert (1×) |
| 2 | Zwei Endpunkte nach Produktion ausgeliefert, dort nicht nutzbar: `POST` → 403, kein Aufrufer im gesamten Code | fehlende Validierung | kritisch | SURVIVES (neu aus 3b) | `curl` gegen nl2cad.de 2026-09-23; `git grep` über `origin/main` ohne Treffer | built-but-never-called (5×) — Zuordnung korrigiert 2026-09-23 |
| 3 | Angebots-PDF an den Kunden änderte 228 Zeilen und wuchs um eine Seite; der PR-Text nannte Firmierung und Datum | fehlende Validierung | mittel | SURVIVES (3b: von kritisch gesenkt) | [ttz-hub#40](https://github.com/ttz-lif/ttz-hub/pull/40), `pdftotext`-Diff der Blobs um `b62eb7bd` | deferred-item-no-tracking-issue (43×) |
| 4 | Warnung im Produktions-Deploy („COMPOSE_PROJECT_NAME mismatch — running='apo-hub'") seit drei Läufen unbeachtet; die Klasse ist anderswo gelöst | fehlende Validierung | mittel | SURVIVES | Run 35760930849, Job „🚀 Production"; gelöste Zwillinge `dms-hub#16`, `illustration-hub#44` | — |
| 5 | Von zwei neuen Endpunkten hatte nur einer einen Test über HTTP | fehlende Validierung | niedrig | SURVIVES (3b: von hoch gesenkt) | [cad-hub#69](https://github.com/achimdehnert/cad-hub/pull/69), `tests/test_pdf_handlers.py`; beide Views teilen `_PDFHandlerViewBase` | — |
| 6 | Freigabeprotokoll sei „rückwirkend fabriziert" | Prozesslücke | kritisch | REFUTED | [#3380-Kommentar 5789169966](https://github.com/achimdehnert/platform/issues/3380#issuecomment-5789169966), Schlusssatz „Nachgetragen im Zuge der Retrospektive" — die Nachträglichkeit ist ausgewiesen, nicht verdeckt | — |
| 7 | Unklar, wer den Mailversand auslöste | Kommunikation | hoch | REFUTED | Dieselbe Tabelle, Zeile „Mail an das Landratsamt senden — Owner hat selbst gesendet, 04:31"; unbelegt ≠ unklar | — |
| 8 | Prod-Deploy widerspreche dem eigenen „kein Bau vor M1/M2" | verfrühte Festlegung | hoch | REFUTED | `meiki-hub:docs/konzepte/KONZ-meiki-010-vollstaendigkeitspruefung-bauantrag.md` §3.1 und §12 REC-6: „Katalog ja, Code nein" | — |
| 9 | PR-Text nenne eine Kopie in einem Repo, das nicht existiert | fehlende Validierung | mittel | REFUTED | `git -C ~/github/platform-pinned remote get-url origin` → `achimdehnert/platform`; `git diff origin/main` auf der Datei leer | — |
| 10 | sqf-hub-Restmangel nur im PR-Text nachgehalten | Prozesslücke | mittel | REFUTED | [#3380-Kommentar 5789169966](https://github.com/achimdehnert/platform/issues/3380#issuecomment-5789169966), Zeile „sqf-hub stilllegen statt mergen" mit Link auf [sqf-hub#9](https://github.com/bahn-sqf/sqf-hub/pull/9) | deferred-item-no-tracking-issue (43×) |
| 11 | cad-hub Issue 68 zu früh geschlossen (Vision-Handler weder eingefroren noch entfernt) | Prozesslücke | niedrig | REFUTED | `cad-hub:apps/dxf/handlers/pdf_vision.py` Modul-Docstring „NICHT FREIGEGEBEN (Issue #68)"; `tests/test_pdf_handlers.py::test_should_not_expose_vision_handler_as_endpoint` | issue-open-after-its-fix-merged |
| 12 | Werkzeug-Ökonomie an dieser Stichprobe nicht beurteilbar | Kommunikation | mittel | REFUTED | Freigabe-Tabelle in [#3380](https://github.com/achimdehnert/platform/issues/3380#issuecomment-5789169966) grenzt die Substory mit sieben nummerierten Schritten ab | — |

**Hinweis zu #11:** Der Befund wurde auf seiner ausdrücklichen Begründung widerlegt — der Vision-Handler ist sehr wohl geordnet eingefroren. Sein Kern („Issue zu früh geschlossen") ist trotzdem richtig, nur aus einem anderen Grund: dem fehlenden Aufrufer aus #2. Das Issue ist wieder geöffnet worden.

## 3 · Scorecard

| Dimension | Wert | Verankerung |
|---|---|---|
| Zielerreichung | **4** | Konzept, Schreiben und Mail geliefert und abgenommen; kein Überlebender greift die Lieferung an |
| Architektur & Design | **3** | KONZ-meiki-010 hielt der Prüfung stand (kein Befund), aber #2: eine Route ohne Aufrufer ausgeliefert |
| Code- & Konventionstreue | **4** | ADR-089 bewusst eingehalten (Vision-Handler ohne Endpunkt, mit Test), ruff sauber; Abzug für #5 |
| Risiko & Schulden | **2** | #1 (13 h Klarname öffentlich), #4 (Warnung dreimal ignoriert), #3 (Kundendokument änderte mehr als angekündigt) |
| Prozess-Effizienz | **3** | #12 REFUTED — die 184 Aufrufe sind der Substory zurechenbar und damit bewertbar; kein Überlebender betrifft Rework, aber #5 (fehlender Endpunkt-Test) und #2 (fehlender Prod-Check) sind je ein Arbeitsgang, der später teurer nachgeholt wurde |
| Entscheidungsqualität | **3** | Gute Züge (Vision-Handler einfrieren statt beleben, „messen vor bauen"), aber #2: „in Betrieb" auf einem `GET` gegründet |

## 4 · Soll-Ablauf

Ein Schritt je überlebendem Befund — fünf Überlebende, fünf Schritte.

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Der eigene Datenschutzbefund wurde als „keine Personendaten Dritter" eingeordnet und an ein Sichtbarkeits-Programm gehängt | Ein Klarname eines Dritten in einem öffentlichen Repo wird **im selben Zug redigiert**, bevor irgendetwas anderes weiterläuft; die Einordnung folgt danach | #1 |
| Nach dem Deploy wurde `GET` geprüft, 405 gesehen und „in Betrieb" geschlossen | Nach einem Deploy, der einen **Schreib-Endpunkt** liefert, wird der Weg gefahren, den der echte Aufrufer nimmt: Seite holen, Token entnehmen, `POST` mit Nutzlast | #2 |
| Das Neuerzeugen eines Kundendokuments wurde mit „das Datum zieht mit" angekündigt | Wird ein eingechecktes Erzeugnis neu gebaut, steht vor dem Commit ein `diff` der alten gegen die neue Fassung; die **gemessene** Zahl geht in den PR-Text, nicht die vermutete | #3 |
| Der Deploy galt als grün, weil alle Jobs grün waren | Ein Deploy-Lauf gilt erst als gelesen, wenn auch seine **Warnungen** gelesen sind; jede unbeantwortete Warnung wird ein Issue oder ausdrücklich verworfen | #4 |
| Ein zweiter Endpunkt entstand als Klassenvariante und bekam keinen eigenen HTTP-Test | Jeder neue Eintrag in `urls.py` bekommt im selben PR einen Test, der ihn über `reverse()` aufruft — auch wenn er sich eine Basisklasse teilt | #5 |

## 5 · Längsschnitt

`python3 tools/retro_kpis.py` über 133 Reports, Stand 2026-09-23:

| Slug | Zähler | Status |
|---|---|---|
| `claim-before-cheapest-check` | 87 | GATE-PFLICHT, Gate existiert (blocking) — hat in dieser Sitzung **zweimal gefangen** |
| `deferred-item-no-tracking-issue` | 43 | GATE-PFLICHT — Befund #3 ist ein weiteres Vorkommen |
| `scope-checkpoint-not-durably-recorded` | 30 | GATE-PFLICHT, Gate existiert (advisory) — hat in dieser Sitzung **gefangen** |
| `built-but-never-called` | 5 | GATE-PFLICHT — Befund #2 ist Vorkommen 6 |

Abgleich gegen `MEMORY.md`: `claim-before-cheapest-check` ist dort unter „Beweiskraft" geführt, `scope-checkpoint` unter „Arbeitsweise & Autonomie". Für `built-but-never-called` findet `grep` keinen Eintrag — das ist die Lücke, die Gate-Kandidat `akte-geprueft-zustand-nicht` schließen soll.

## 5a · Rückfall-Prüfung

`python3 tools/gate_wirkung.py` über 133 Reports: **kein Gate meldet `RUECKFAELLIG`.** Drei Gates haben in dieser Sitzung gefangen und sind damit Wirksamkeitsbeleg, nicht Rückfall:

| Gate | Wirkung in dieser Sitzung |
|---|---|
| `claim-before-cheapest-check` | zweimal, jeweils vor dem Absenden einer ungedeckten Behauptung |
| `scope-checkpoint-not-durably-recorded` | einmal, Fehlerform B — Checkpoint ausgesprochen, nicht protokolliert; daraufhin nachgetragen |

**Nachtrag 2026-09-23 (Owner-Entscheid „187 go"):** Befund 2 trug in der Recurrence-Spalte zwei Slugs, `claim-before-cheapest-check` **und** `built-but-never-called`. Der erste ist gestrichen. Begründung: zwei ausgelieferte Endpunkte ohne Aufrufer sind kein Fall von „behauptet vor dem billigsten Check" — es wurde nichts behauptet, es wurde etwas gebaut und nie gerufen. Das ist der namensgebende Fall des zweiten Slugs. Die Doppelnennung hatte `claim-before-cheapest-check` einen Rückfall zugeschrieben, den ein anderes Gate zu verantworten hat, und damit die Wirkungsbilanz beider verzerrt. Quelle: Retro 3bdc4e §5a, Maßnahme 7.

### Ein Gate ist rückfällig: `gate-untested-command-handed-to-user-wirkungslos`

In dieser Sitzung habe ich dem Owner einen Anmeldebefehl in einer Board-Zeile übergeben; er endete bei ihm mit einer Fehlermeldung, weil ich das Kürzel statt der Adresse verwendet hatte. Genau davor soll `untested-command-handed-to-user` schützen — es steht auf `blocking` und deckt laut Registry ausdrücklich die `!`-Übergabekonvention ab. Es hat nicht gefeuert.

**Ursache gemessen**, nicht vermutet. Der Melder gegen die tatsächlichen Textformen laufen lassen:

| Textform | Melder |
|---|---|
| Board-Zeile mit `` `! befehl` `` (der Realfall) | still |
| nackte Zeile `! befehl` | still |
| eingerahmter Codeblock **mit** `!` | feuert |
| eingerahmter Codeblock **ohne** `!` | feuert |
| Fließtext mit `` `befehl` `` | still |

**Der Melder sieht nur eingerahmte Codeblöcke.** Das ist die Ursache an der Quelle — und sie steht im Widerspruch zum hauseigenen Antwortformat: eine Board-Zelle muss knapp sein und trägt einen Befehl deshalb **immer** als Inline-Code, nie als Block. Je konsequenter das Board benutzt wird, desto blinder wird dieses Gate.

**Zulässige Antwort: ausweiten.** Der bestehende Eintrag bekommt `revised` plus `revision_note` und eine neue `positivkontrolle` für Inline-Code; ein zweites Gate unter neuem Namen wäre falsch. Umsetzung steht aus — Maßnahme 8.

## 5b · Autonomie-Kalibrierung

- **`over_act`: keiner.** Der Produktions-Merge in cad-hub war ausdrücklich freigegeben („PR 69 mergen go"), nachdem ich die Deploy-Folge im Zug benannt hatte. Ebenso die Merges in platform, ttz-hub und chat-hub.
- **`over_ask`: einer**, Klasse `mail-versand-nach-textfreigabe`. Auf „passt, mail entwurf und PR mergen" habe ich zurückgefragt, ob ich senden soll. Die Rückfrage war vertretbar (externer Empfänger, unklare Formulierung), aber sie kostete eine Runde. Erstes Vorkommen dieser Klasse; eine Nominierung braucht zwei.

## 6 · Verankerung

Kopierfertige Vorschläge — geschrieben wird nur auf Owner-Wort.

### memory_candidates

```markdown
---
name: feedback_route_ohne_aufrufer_ist_kein_betrieb
description: Ein Endpunkt, der nach dem Deploy auf GET mit 405 antwortet, ist geroutet — nicht in Betrieb. Der Beweis ist der POST mit Token.
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-23-cad-hub-endpunkt-ohne-aufrufer
---

Am 2026-09-23 galten zwei neu ausgelieferte Endpunkte als „erreichbar, getestet
und in Betrieb", weil `GET` mit 405 antwortete. `POST` lieferte 403, und im
ganzen Repo rief sie nichts auf — kein Template, kein Skript. Die neun Tests
waren grün, weil Djangos Test-Client die CSRF-Prüfung abschaltet.

**Why:** 405 beweist die Route, nicht den Zugang. Wer einen Schreib-Endpunkt
ausliefert, hat ihn erst geprüft, wenn er den Weg des echten Aufrufers gefahren
ist: Seite holen, Token entnehmen, `POST` mit Nutzlast.

**How to apply:** Nach jedem Deploy, der einen POST-Endpunkt neu bringt, einmal
`curl -c cookies` auf die aufrufende Seite, Token aus dem Cookie, dann `POST`
mit `-b cookies -H "X-CSRFToken: …" -H "Referer: …"`. Und im Test:
`Client(enforce_csrf_checks=True)` plus Gegenprobe ohne Token —
sonst ist der Test von einer abgeschalteten Prüfung nicht zu unterscheiden.
Verwandt: [[feedback_reporting_table_format]].
```

```markdown
---
name: feedback_klarname_dritter_wird_im_selben_zug_redigiert
description: Ein Klarname eines Dritten in einem öffentlichen Repo wird sofort redigiert — die Einordnung kommt danach, nicht davor.
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-23-klarname-public-repo-13h
---

Am 2026-09-22 stand der Klarname eines Ansprechpartners bei einem Landratsamt
samt dessen internem Prozessproblem 13 Stunden 46 Minuten im öffentlichen Repo
`achimdehnert/platform`. Der Befund wurde **in derselben Sitzung selbst erzeugt**
— zwölf Minuten nach Anlage des Issues — und dabei als „keine Verletzung einer
Regel (keine Personendaten Dritter)" eingeordnet und an ein laufendes
Sichtbarkeits-Programm gehängt.

**Why:** Die Fehleinordnung war der Grund, warum nichts geschah. Ein Name ist
ein personenbezogenes Datum; die Frage „ist das ein Verstoß?" darf dem Handeln
nicht vorausgehen. Schwärzen macht eine Veröffentlichung ohnehin nicht
rückgängig — jede Stunde zählt.

**How to apply:** Sobald ein Klarname eines Dritten in einem öffentlichen Repo
auffällt: redigieren, dann erst einordnen. Danach prüfen, ob die
Bearbeitungshistorie den alten Stand noch ausliefert (anonym abrufen, nicht mit
eigenem Token). Verwandt: [[project_platform_privat_auftrag_3234]].
```

### adr_candidates

Keine. Beide Fälle sind Ausführungsdisziplin, keine Architekturentscheidung — nach `adr-threshold.md` wäre ein ADR hier überschießend.

## 7 · Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Aufrufer gebaut, Prod geprüft | cad-hub | [#71](https://github.com/achimdehnert/cad-hub/pull/71) | ✅ | — |
| 2 | Übergabe bricht bei öffentlichem Ziel ab | chat-hub | [#137](https://github.com/iilgmbh/chat-hub/pull/137) | ✅ | — |
| 3 | Klarname redigiert, Fehleinordnung berichtigt | platform | [#3234](https://github.com/achimdehnert/platform/issues/3234) | ✅ | — |
| 4 | Angebotsfassung für den Kunden klären | ttz-hub | [#41](https://github.com/ttz-lif/ttz-hub/issues/41) | ✅ | Geklärt: das Repo-Dokument war nie das eingereichte |
| 5 | Deploy-Warnung `apo-hub`/`cad-hub` | cad-hub | [#75](https://github.com/achimdehnert/cad-hub/issues/75) | ✅ | Bewusst verworfen, Owner-Entscheid |
| 6 | Maßstab wird doppelt geschrieben | cad-hub | [#73](https://github.com/achimdehnert/cad-hub/issues/73) | ✅ | Behoben, in Produktion gegengeprüft |
| 7 | Zwei Memory-Kandidaten verankern | platform | Auto-Memory | ✅ | Beide verankert |
| 8 | Melder sieht nur Codeblöcke, nicht Inline-Code | platform | [#3418](https://github.com/achimdehnert/platform/pull/3418) | ✅ | Gemergt; Nachschärfung in [#3430](https://github.com/achimdehnert/platform/pull/3430) |
| 9 | Phase 6 kollidiert mit der Datensouveränität | platform | dieser Report §7a | 🟢 | Skill-Änderung entscheiden |

> **Nachgezogen 2026-09-23 auf den Endstand.** Die Zeilen 4 bis 8 zeigten bis dahin den Stand vom Mergezeitpunkt des Reports, obwohl die Maßnahmen danach weiterliefen; Zeile 6 verwies zudem auf das falsche Issue. Der Befund dazu steht in [`…-0405d4-incr.md`](session-retro-2026-09-23-platform-0405d4-incr.md) als Nummer 5 — eine Maßnahmen-Tabelle ist ab ihrem Merge Fiktion, wenn niemand sie schließt.

## 7a · Phase 6 (Extern-Handoff) — begründetes n/a

**Nicht durchgeführt, und zwar aus einem Grund, der über diese Sitzung hinausweist.**

Der Skill sieht bei Footprint `deep` eine anbieterfremde Zweitmeinung vor: der Report wandert nach `~/shared/`, der Owner holt die Kritik über eine externe Oberfläche. Für diesen Report geht das nicht. Er zitiert Inhalte aus `meiki-lra/meiki-hub` und `ttz-lif/ttz-hub` — beide Organisationen fallen unter `data-sovereignty.md`, das die Weitergabe an externe SaaS-Modelle ausdrücklich untersagt. Die Regel ist fail-closed formuliert; im Zweifel gilt Abbruch.

Ein geschwärzter Auszug wäre denkbar, aber er nähme der Kritik genau das, was sie prüfen soll: die Befund-Belege. Eine Methodenkritik ohne die Fälle ist wenig wert.

**Das ist ein Befund am Skill, nicht an dieser Sitzung.** Phase 6 ist als „optional, nur `deep`" geführt, die Abschluss-Checkliste verlangt aber „geschrieben **oder begründet n/a**". Beides fehlte hier zunächst — ich hatte die Phase stillschweigend übersprungen und den Report trotzdem als abgeschlossen bezeichnet. Nachgetragen 2026-09-23 nach einem Evidenz-Check.

**Vorschlag für den Skill:** Phase 6 bekommt eine ausdrückliche Ausnahme — berührt der Scope eine Organisation aus `data-sovereignty.md`, ist der Extern-Handoff nicht optional, sondern **unzulässig**, und das n/a ist vorgezeichnet statt begründungspflichtig.

## 8 · Nicht verifiziert (Restlücken)

**Getan:** Drei Ermittler und drei Skeptiker in frischem Kontext, eine Widerlegungsbahn auf höherem Tier, zwölf Befunde geprüft, fünf gehalten; vier Repos mit Artefakten korrigiert; der Produktionsweg einmal echt gefahren.

**Angenommen:** Dass die Freigaben des Owners im Chat so gefallen sind, wie das nachgetragene Protokoll sie wiedergibt — der Kanal ist nicht über `git`/`gh` einsehbar. Dass die 184 Bash-Aufrufe dieser Substory zuzurechnen sind und nicht den rund zwanzig fremden Arbeitssträngen im selben Zeitfenster.

**Nicht verifizierbar:** Was ein **eingeloggter Fremder ohne Schreibrecht** in der Bearbeitungshistorie von platform#3380 sieht. Anonym ist der alte Stand nicht abrufbar (Seite: 0 Treffer, Historien-Pfad: 404, Gegenprobe positiv); für die dritte Sicht bräuchte es ein zweites Konto. Billigster Check: ein fremdes GitHub-Konto das Issue öffnen lassen.

**Offen geblieben:** Ob die Compose-Warnung wirklich in drei Läufen steht — belegt ist sie in einem, die beiden Vorläufe hat die Widerlegungsbahn nicht nachgezogen. Ob das Angebot für TTZ Leipheim in der alten oder neuen Fassung gilt. Der doppelte Maßstab im Erkennungsmuster. Und der Nebenbefund der Widerlegungsbahn, den niemand geprüft hat: das Angebot trägt zwei verschiedene Kontaktadressen und keine Pflichtangaben nach § 35a GmbHG.

## Widerlegung

Phase 3b, höheres Tier, frischer Kontext, ohne Kenntnis der Ermittler-Aufträge.

| # | Punkt | Verdikt |
|---|---|---|
| 1 | Überlebender „Testlücke" — Einstufung hoch | **GEKIPPT** auf niedrig: beide Views teilen `_PDFHandlerViewBase`, ungeprüft bleibt allein ein Routing-Fehler |
| 2 | Überlebender „Angebots-PR" — Einstufung kritisch | **GEKIPPT** auf mittel: Richtung und Außenwirkungsrisiko standen im PR-Text, verschwiegen war die Größenordnung |
| 3 | Überlebende „Klarname" und „Deploy-Warnung" | **BESTAETIGT**, beide verschärft: 13 h 46 min statt „Stunden", drei Fundstellen statt einer; zweite unbeachtete Warnung im selben Job |
| 4 | Widerlegung „Datenschutzbefund delegiert" | **GEKIPPT**: die Delegation war Folge der Fehleinordnung, nicht ihr Ersatz |
| 5 | Fehlende Dimension | **NEU**: niemand hat den **Zustand** geprüft, den die Akten erzeugt haben — `POST` gegen Produktion ergab 403 |

Der fünfte Punkt ist der Ertrag dieser Bahn. Drei Ermittlungsrichtungen haben dieselbe Quelle gelesen: das, was die Sitzung über sich selbst aufgeschrieben hat. Wo die Akte ordentlich war, ging „erledigt" durch.

## Streichbahn

**Kandidat:** `retro-dimension-soll-ist-ohne-ueberlebende`.

**Belegart „kein Effekt":** Die Ermittlungsrichtung „Soll-Ist und Scope" lieferte sechs Befunde. Fünf davon wurden vom Skeptiker widerlegt, der sechste war eine Dublette der Richtung „Entscheidungen und Fehler". Null Überlebende bei rund 106 000 Token. Die beiden anderen Richtungen lieferten je zwei Überlebende.

**Einschränkung, die gegen sofortiges Streichen spricht:** Das ist **ein** Vorkommen. Nach der Ratsche dieser Skill wird ein Kandidat, der zwei Retros hintereinander auftaucht und nicht gestrichen wurde, selbst zum Befund — also beobachten, nicht jetzt entfernen. Der Verdacht ist nicht, dass die Dimension überflüssig wäre, sondern dass ihr Auftrag zu nah an der Selbstbeschreibung der Sitzung liegt: sie prüft, ob die Akte zum Auftrag passt, und findet deshalb vor allem Formfehler in der Akte.
