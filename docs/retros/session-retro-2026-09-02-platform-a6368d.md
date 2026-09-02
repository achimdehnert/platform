---
retro_schema: 1
date: 2026-09-02
repo_scope: [platform, risk-hub]
session_id: a6368d
footprint: deep
findings_total: 17
findings_survived: 12
refuted_rate: 0.29
phase3_refuted: 5
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 4
gate_candidates: [pruefung-belegt-transport-nicht-inhalt, prod-vollzug-nicht-nachgetragen, claim-gate-sieht-nur-den-chat]
recurring_findings: [claim-before-cheapest-check, issue-open-after-its-fix-merged, same-file-serial-prs, lint-failure-no-local-gate, deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded, untested-command-handed-to-user]
gates_caught: [deferred-item-no-tracking-issue, scope-checkpoint-not-durably-recorded, untested-command-handed-to-user]
over_ask: 0
over_act: 0
over_ask_klassen: []
over_act_klassen: []
---

# Session-Retro 2026-09-02 — platform (+ risk-hub), Session a6368d

## 1. Executive Summary

- **8 PRs, alle gemergt** (#2665, #2673, #2674, #2675, #2677, #2679, #2683, #2686 — `gh pr view` je PR: `MERGED`). Ein unabhängiger Prüfer hat fünf Zahlenbehauptungen aus den PR-Texten nachgerechnet (35 Tests, 14 Tests, 3365 grün, 2 Host-Audit-Findings, gesetzte Nachweisdaten) — alle fünf bestätigt.
- **Der teuerste Befund ist eine Klasse, kein Einzelfall:** zweimal unabhängig wurde geprüft, ob der *Transport* stimmt (Prüfsumme gleich, Endpunkt antwortet), nie, ob der *Inhalt* der richtige ist. Beim Escrow sicherte das eine Datei, die den Schlüssel gar nicht enthält; beim Tunnel-Werkzeug bliebe ein falsch formatierter Ursprung still.
- **Ein Prod-Deploy hat keinen durablen Vermerk.** Der risk-hub-Produktionslauf ist erfolgreich, aber kein Issue, kein PR, kein Handover nennt ihn. Die Lesefläche führt ihn weiterhin als offen.
- **Das Gate `claim-before-cheapest-check` hat viermal im Chat gegriffen — und genau denselben Fehler im PR-Text durchgelassen.** Der Scanner sieht die Antwort an den Owner, nicht den Text, der ins Repo wandert. Das ist ein Rückfall mit klarer Diagnose und einem klaren Weg: das Gate ausweiten.
- **Positiv, mit Beleg:** eine eigene Fehlaussage wurde am selben Tag zurückgenommen und mit Positivkontrolle korrigiert (#2486-Kommentar 10:32:10Z, Gegenprobe vom gx10 inkl. Kontrollport). Die Wiederanlaufprobe ist als Repo-Artefakt abgelegt (`docs/messungen/2026-09-02-escrow-wiederanlaufprobe.md`, PR #2683); ihre Host-Ergebnisse selbst waren für die Prüfer **nicht** nachvollziehbar — siehe §8.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Prod-Deploy risk-hub (Lauf 33620470085, success 10:38:05Z) hat in keinem Issue, PR oder Handover einen Vermerk; #2148 führt den Dispatch weiter als offen | Prozesslücke | **hoch** | SURVIVES | Skeptiker mit bestandener Positivkontrolle (`33046756805` und „Gate-Stau" werden von derselben Suche gefunden); letzter #2148-Kommentar 09:19:44Z, also vor dem Lauf | neu |
| 2 | PR #2673 nannte den Escrow „ausgeführt", sicherte aber `offsite-backup.env` — die Datei enthält per `RESTIC_PASSWORD_FILE` nur einen Zeiger, nicht den Schlüssel | fehlende Validierung | **hoch** | SURVIVES | #2673 Body „Der Escrow ist **ausgeführt**"; #2675 (40 Min. später) belegt den Zeiger; die Verifikation verglich sha256 auf der falschen Ebene | ×N `claim-before-cheapest-check` |
| 3 | `ORIGIN` wird ungeprüft in die Tunnel-Config geschrieben; die nachgelagerte Prüfung kann ein defektes Ziel nicht von einer korrekten Abweisung unterscheiden (beides „nicht 200") | fehlende Validierung | mittel | SURVIVES | `tools/cf_access/tunnel_anlegen.py` Z. 40/76; `veroeffentlichen.sh` Schritt 3/4 prüft nur `code != 200` | neu |
| 4 | Vier PRs (#2673, #2674, #2675, #2677) ändern `infra/secrets-inventory.yaml` in 50 Minuten | Prozesslücke | mittel | SURVIVES | `git log origin/main --oneline -- infra/secrets-inventory.yaml` → 4 Commits 11:16–12:03 | ×N `same-file-serial-prs` |
| 5 | `gh run rerun` auf einen concurrency-abgebrochenen Lauf spielte die alte Ereignis-Nutzlast ab, machte aus `CANCELLED` ein `FAILURE` und erzwang einen Leer-Commit | Werkzeug | mittel | SURVIVES | Commit `f363d9cb`; Wurzelursache in #2676 dokumentiert, Fix PR #2679 | neu |
| 6 | Issue-Body #2504 führt Punkte weiter als offen, die ein eigener Kommentar abhakt — zwei widersprüchliche Wahrheiten in einem Issue | Prozesslücke | mittel | SURVIVES | `gh issue view 2504 --json body` gegen Kommentar 2026-08-30 | neu |
| 7 | Kein Zielzustand mit Akzeptanzkriterien, obwohl die Sitzung 8 PRs, 4 Hosts und mehrere Prod-Schritte umfasste; die Einordnung „trivial" ist durch den eigenen Scope-Checkpoint der Sitzung widerlegt | Prozesslücke | mittel | SURVIVES | Skeptiker gegen die Milde-Einschätzung des Finders; Scope-Checkpoint-Kommentar auf #2486 | neu |
| 8 | `actor` und `approvals.user` können Mensch und Agent nicht trennen, wenn beide dasselbe Token nutzen — die Herkunft einer Prod-Handlung ist aus GitHub-Artefakten nicht belegbar | fehlende Validierung | mittel | SURVIVES | `gh api .../runs/33620470085` und `.../approvals`: beide zeigen nur das Konto | neu |
| 9 | Roter Gate-Lauf auf PR #2683, lokal vermeidbar: `deferral_anchor_check.py` ist ohne CI ausführbar und wurde vor dem Push nicht gefahren | fehlende Validierung | niedrig | SURVIVES | `gh run view 33634955894 --log-failed`; Folgelauf auf identischem SHA grün | ×N `lint-failure-no-local-gate` |
| 10 | Commit `f363d9cb` verletzt die Commit-Konvention (kein `(scope)`) | Prozesslücke | niedrig | SURVIVES | `git show origin/main --oneline f363d9cb` | neu |
| 11 | Issue #2676 blieb offen, obwohl PR #2679 es vollständig behebt — der PR-Text sagt „Refs" statt „Closes" | Prozesslücke | niedrig | SURVIVES | `gh issue view 2676 --json state` → OPEN; `gh pr view 2679 --json state` → MERGED | ×N `issue-open-after-its-fix-merged` |
| 12 | Der Owner-Entscheid zu netcup R3 fiel, nachdem die Änderung bereits umgesetzt war | Kommunikation | niedrig | SURVIVES | #2486-Kommentar 09:08:14Z benennt es selbst; Umsetzung lief am 2026-09-01 | neu |
| 13 | „PR #2679 wurde vom **Bot** freigegeben, obwohl er Tabu-Pfade ändert — Gate-Umgehung" | Prozesslücke | hoch (behauptet) | **REFUTED** | `gh api users/wirdigital` → `type: User`; Bot ist `IIL-Lotse` und übersprang den PR nachweislich um 12:41:53Z („Tabu-Pfad — bleibt Mensch"), Merge erst 13:09:41Z; CODEOWNERS führt das Konto als zweiten Code-Owner | — |
| 14 | „`juengste_je_name` wirft namenlose Prüfeinträge in einen gemeinsamen Eimer, der ältere verschwindet" | fehlende Validierung | mittel (behauptet) | **REFUTED** | Stichprobe über 5 PRs: jeder Rollup-Eintrag ist `CheckRun` mit gesetztem `name`; die auslösende Eingabeklasse tritt an echten Daten nicht auf | — |
| 15 | „Die offenen Punkte in #2504 sind ausreichend verankert, weil das Issue offen ist" | Prozesslücke | — (Milde-Urteil) | **REFUTED** | Body-Drift (Befund 6) macht das Issue als Lesefläche unzuverlässig | — |
| 16 | „Für diese Sitzung war kein eigener Zielzustand nötig (trivial)" | Prozesslücke | — (Milde-Urteil) | **REFUTED** | Umfang der Sitzung + eigener Scope-Checkpoint (Befund 7) | — |
| 17 | „Der Prod-Deploy wurde nachweislich vom Owner selbst ausgeführt, Beleg `actor: achimdehnert`" | fehlende Validierung | — (Milde-Urteil) | **REFUTED** | Das Feld trägt die Aussage nicht (Befund 8) | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Jeder Auftragspunkt aus #2486 und #2504 trägt im Issue-Kommentarverlauf einen Ausgang; 8 PRs gemergt. Abzug für Befund 2 (ein „erledigt" war zum Zeitpunkt der Aussage falsch) und Befund 1 (ein Vollzug fehlt in der Lesefläche) |
| architektur_design | **4** | Auslagerung der Bot-Auswahl in ein testbares Modul und die Umstellung der Frist auf das Dateinamen-Datum sind saubere Lösungen; Abzug für Befund 3 |
| code_konventionstreue | **4** | Testnamen, Commit-Format und Secrets-Disziplin durchgehend eingehalten (Finder-Suche über alle 8 PR-Diffs ohne Fund); Abzug für Befund 10 |
| risiko_debt | **3** | Escrow vollständig plus bestandene Wiederanlaufprobe stehen gegen zwei hohe Befunde (1, 2) und eine stille Validierungslücke (3) |
| prozess_effizienz | **2** | Vier PRs auf eine Datei (4), zwei vermeidbare rote Läufe (9), ein Leer-Commit und ein Wiederholungslauf, der die Lage verschlechterte (5) |
| entscheidungsqualitaet | **4** | Belegte Positiventscheide: Auslagerung in ein testbares Modul statt Inline-Flick (PR #2679, 14 Tests), Frist aus dem Dateinamen statt der Dateizeit (PR #2686), Protokoll bewusst außerhalb des Melder-Ordners abgelegt (#2682, `docs/messungen/`). Abzug für Befund 5 (Wiederholungslauf). Eine vierte Entscheidung — die Weigerung, einen ungetesteten Freigabe-Befehl weiterzureichen — ist **nur durch den Sitzungsverlauf gedeckt** und daher hier nicht als Anker gezählt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Der Prod-Lauf wurde gestartet, freigegeben und danach nirgends vermerkt (#2148 führt ihn weiter als offen) | Ein Prod-Vollzug schreibt seinen Ausgang im selben Zug dorthin, wo er vorher als offen stand — Lauf-ID, Ergebnis, laufender Stand am Ziel | #1 |
| „Escrow ist ausgeführt" auf Basis gleicher Prüfsummen; die kopierte Datei enthielt nur einen Zeiger | Vor jedem Erledigt-Satz über eine kopierte Datei einmal ihre **Feldnamen** ausgeben und gegen den behaupteten Inhalt halten — Prüfsumme belegt die Kopie, nicht die Eignung | #2 |
| `ORIGIN` wandert ungeprüft in die Config, Erfolg wird unbedingt gemeldet | Der Parameter wird gegen `host:port` geprüft, bevor die Datei geschrieben wird; die Erfolgsmeldung erst nach der Prüfung | #3 |
| Vier PRs auf dieselbe Datei, weil jede Owner-Antwort sofort umgesetzt wurde | Offene Entscheidungen zu einer Datei sammeln und in einem Zug einarbeiten, solange keine davon blockiert | #4 |
| Wiederholungslauf auf einen abgebrochenen Lauf, der die Lage verschlechterte | Einen abgebrochenen Prüf-Zwilling nie wiederholen — er spielt die alte Nutzlast ab; stattdessen einen frischen Lauf über eine neue Kopfänderung auslösen | #5 |
| Issue mehrfach kommentiert, Body mit veralteten Haken belassen | Wer ein Issue kommentiert, zieht im selben Zug dessen Checkboxen nach — sonst tragen Body und Kommentare zwei Wahrheiten | #6 |
| Sitzung mit 8 PRs und mehreren Prod-Schritten ohne eigenen Zielzustand | Sobald die zweite Owner-Freigabe eintrifft, einmal einen Zielzustand mit Abnahmekriterien festhalten, statt Punkt für Punkt zu arbeiten | #7 |
| Die Herkunft einer Prod-Handlung wurde aus `actor` abgeleitet | Wer eine Prod-Handlung ausführt, schreibt das in den Freigabe-Kommentar hinein („ausgeführt vom Agenten auf Owner-Wort X") — das Feld kann es nicht | #8 |
| Push ohne lokalen Lauf des Gates, das den PR-Text prüft | Vor jedem Push die Gates lokal fahren, die ohne CI laufen — Linter und Textprüfer zuerst, dann die Suite | #9 |
| Commit-Nachricht ohne Bereichsangabe | Auch ein reiner Auslöse-Commit trägt das Format; die Nachricht ist die einzige Stelle, an der er sich später erklärt | #10 |
| PR-Text sagt „Refs" bei einem PR, der das Issue vollständig behebt | „Closes" schreiben, wenn der PR den Auftrag erschöpft; sonst bleibt das Tracking hinter dem Vollzug zurück | #11 |
| Entscheid wurde nach dem Vollzug protokolliert | Wenn ein Punkt bereits umgesetzt ist, bevor die Entscheidung fällt, dies der Entscheidung voranstellen statt sie als Auftrag zu lesen | #12 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 110 Retros:

- **41 Slugs ≥2 ⇒ gate-pflichtig**, davon **11 ohne registriertes Gate**. Drei davon trafen diese Sitzung direkt: `issue-open-after-its-fix-merged` (Befund 11), `same-file-serial-prs` (Befund 4), `partial-fix-not-generalized-to-sibling-artifacts` (verwandt mit Befund 3).
- **Score-Mittel über 110 Retros:** `risiko_debt` bleibt mit **2,55** die schwächste Dimension. Diese Sitzung liegt mit 3 darüber, aber die beiden hohen Befunde sind genau dieser Klasse zuzurechnen.
- **`refuted_rate` 0,29** liegt im gesunden Band (weder dauerhaft >0,8 noch <0,2). Alle fünf Widerlegungen stammen aus Phase 3, `pre_refuted` ist 0.
- Die Längsschnitt-Behauptung zu Befund 2 wurde auf Existenz geprüft: die Drift-Notiz `feedback_claim_reaches_further_than_the_look` existiert (`rule_class: A`, `drift_episode: 2026-07-31`). Keine Phantom-Referenz.

## 5a. Rückfall-Prüfung — hat ein gebautes Gate versagt?

`python3 tools/gate_wirkung.py`: **4 Gates rückfällig**, darunter `claim-before-cheapest-check` (blocking seit 2026-08-02, letzter Rückfall **2026-09-02** — diese Sitzung).

**Der Befund lautet nicht „claim-before-cheapest-check zum N-ten Mal", sondern: das Gate ist rückfällig, und diese Sitzung zeigt warum.**

| Beobachtung | Beleg |
|---|---|
| Das Gate feuerte **viermal** gegen Antworten an den Owner und wurde jedes Mal befolgt | vier Stop-Hook-Auslösungen, je mit anschließender Korrektur |
| Derselbe Fehlertyp wanderte **ungehindert** in einen PR-Text und einen Merge-Commit | Befund 2: „Der Escrow ist **ausgeführt**" in #2673 |

**Diagnose:** Der Scanner liest die Antwort an den Owner. PR-Texte, Commit-Nachrichten und Issue-Kommentare durchlaufen ihn nicht — und genau dorthin schreibt eine Sitzung ihre dauerhaften Behauptungen.

**Antwort nach Phase 5a: ausweiten** (nicht umbauen, nicht herabstufen). Der Prüfpfad muss den Text erfassen, der ins Repo geht. Ein Vorschlag dazu steht in §6; die Entscheidung bleibt beim Owner.

Ehrlichkeits-Vermerk: 7 Gates stehen auf `zu-frueh`. Dass sie in dieser Sitzung nicht auffielen, ist **kein** Wirksamkeits-Beleg.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Begründung |
|---|---|---|
| `over_ask` | **0** | Kein deterministisch-reversibler Punkt wurde vorgelegt. Der Dispatch für risk-hub ging an den Owner, weil der Auto-Mode-Classifier ihn dreimal ablehnte — eine äußere Sperre, keine Vorsicht |
| `over_act` | **0** | Jeder Prod-Schritt trug ein ausdrückliches Wort: „9 go", „6 go" (zweimal), „24 go", „25 go", „28 go". Die Environment-Freigabe wurde erst nach „mach es autonom" in direkter Antwort auf den Freigabe-Link gesetzt |

**Selbst eingeschätzt, nicht fremdgeprüft** — siehe §8. Die Einordnung der Environment-Freigabe als gedeckt ist die einzige, bei der eine zweite Meinung sinnvoll wäre.

## 6. Verankerung (Vorschläge — Entscheidung beim Owner)

### memory_candidates

```markdown
---
name: feedback_pruefung_belegt_transport_nicht_inhalt
description: "Pruefsumme und HTTP-Antwort belegen den Transport, nie den Inhalt — vor jedem Erledigt-Satz die Feldnamen der Zieldatei gegen die Behauptung halten"
metadata:
  node_type: memory
  drift: true
  drift_episode: 2026-09-02-escrow-zeiger
  type: feedback
---

Zweimal unabhaengig am 2026-09-02: (1) Ein Escrow wurde als „ausgefuehrt" gemeldet,
weil die Kopie byte-gleich zur Quelle war — die kopierte Datei enthielt aber nur
`RESTIC_PASSWORD_FILE=<pfad>`, also einen Zeiger. (2) `tunnel_anlegen.py` schreibt
einen ungeprueften `ORIGIN` in die Config und meldet Erfolg; die nachgelagerte
Pruefung akzeptiert jedes „nicht 200" und kann ein defektes Ziel nicht von einer
korrekten Access-Abweisung unterscheiden.

**Why:** Eine Pruefsumme beantwortet „ist die Kopie gleich?", nicht „ist die Menge
vollstaendig?". Eine HTTP-Antwort beantwortet „antwortet jemand?", nicht „antwortet
der Richtige?". Beide Fehler sehen im Protokoll wie ein bestandener Test aus.

**How to apply:** Vor jedem Erledigt-Satz ueber eine kopierte oder verdrahtete
Sache einmal den INHALT anfassen: Feldnamen ausgeben (`grep -oE '^[A-Za-z_]+='`),
jedem Verweis bis zum Wert folgen, bei Endpunkten eine Positivkontrolle mit
bekanntem Inhalt. Verwandt: [[feedback_claim_reaches_further_than_the_look]],
[[feedback_http_200_is_not_proof_of_payload]].
```

```markdown
---
name: feedback_prod_vollzug_gehoert_zurueck_in_die_leseflaeche
description: "Ein Prod-Schritt, der als offen dokumentiert wurde, braucht nach dem Vollzug einen Nachtrag an derselben Stelle — sonst liest die naechste Sitzung den alten Stand"
metadata:
  node_type: memory
  type: feedback
---

Am 2026-09-02 wurde der risk-hub-Produktionsdeploy (Lauf 33620470085) erfolgreich
ausgefuehrt, nachdem ein Kommentar auf platform#2148 ihn als offen und beim Owner
liegend beschrieben hatte. Danach folgte kein Nachtrag — weder in #2148, #2486,
#2504 noch im Handover. Suche mit bestandener Positivkontrolle.

**Why:** Der Vermerk „liegt beim Owner" altert in dem Moment, in dem gehandelt
wird. Wer die Lesefläche danach nicht nachzieht, hinterlaesst eine Zeile, die aktiv
in die Irre fuehrt — teurer als gar keine Zeile.

**How to apply:** Wer einen Prod-Schritt als offen dokumentiert, traegt seinen
Ausgang an derselben Stelle nach: Lauf-ID, Ergebnis, laufender Stand am Ziel.
Und: `actor`/`approvals.user` in GitHub trennen Mensch und Agent nicht, wenn beide
dasselbe Token nutzen — wer gehandelt hat, gehoert in den Text.
```

### adr_candidates

Keine. Beide Befunde sind Ausfuehrungs-Disziplin, keine Architekturentscheidung
(`policies/adr-threshold.md`: Ergaenzung nach bestehendem Muster = kein ADR).

### Gate-Vorschlag zu 5a (erweitert die Reichweite eines bestehenden Gates)

`claim-before-cheapest-check` prueft heute nur die Antwort an den Owner. Vorschlag:
denselben Scanner zusaetzlich auf **PR-Body und Commit-Nachricht** anwenden, als
Pre-Push- oder CI-Schritt. Messpunkt fuer die Wirksamkeit: faellt die Zahl der
Retro-Befunde, deren Beleg ein PR-Text ist, ueber die naechsten 10 Retros?

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Prod-Vollzug nachtragen | platform | [#2148](https://github.com/achimdehnert/platform/issues/2148) | 🔵 | Lauf-Ausgang kommentieren |
| 11 | Issue schliessen | platform | [#2676](https://github.com/achimdehnert/platform/issues/2676) | 🔵 | Mit Fix-Verweis schliessen |
| 3 | ORIGIN validieren | platform | [#2682](https://github.com/achimdehnert/platform/issues/2682) | 🔵 | Neues Issue + Fix-PR |
| 6 | Issue-Body nachziehen | platform | [#2504](https://github.com/achimdehnert/platform/issues/2504) | 🔵 | Erledigte Haken setzen |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5a | Gate ausweiten | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 | Scanner auf PR-Text entscheiden |
| 6b | Zwei Memory-Kandidaten | platform | §6 dieses Berichts | 🟢 | Uebernehmen oder verwerfen |
| 5b | Autonomie-Einordnung | platform | §5b | 🟢 | Environment-Freigabe gegenpruefen |

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| Befund 4 (Serien-PRs) hat den **Bewertungsteil** „wäre bündelbar gewesen" nicht durch einen Skeptiker geprüft — das Skeptiker-Budget (≤3, eines je Dimension) war ausgeschöpft | Ein Skeptiker mit der Frage, ob eine Bündelung ohne Informationsverlust möglich gewesen wäre (~55k Token) |
| Die Autonomie-Einordnung in §5b ist **selbst** vorgenommen — genau der Regel-1-Bruch, den die Methode sonst vermeidet | Ein Skeptiker auf die Frage, ob „mach es autonom" als spezifisches Wort für eine Prod-Freigabe zählt |
| Alle Host-Aussagen der Sitzung (302 am veröffentlichten Namen, sha256 der Escrow-Kopien, 126 Snapshots, SSH-Konfiguration auf prod-b, Gruppen-Zugehörigkeit auf netcup) waren für die Finder **nicht** prüfbar — kein Host-Zugriff aus deren Kontext | Wiederholung der Kommandos aus einer Sitzung mit ssh-Zugang |
| Befund 8 nennt die Session-Transkript-Spur als einzig tragfähigen Beleg für die Herkunft einer Prod-Handlung; sie wurde nicht ausgewertet | Auswertung des Werkzeugverlaufs dieser Sitzung gegen die Zeitstempel der Prod-Aufrufe |
| Phase 6 (anbieter-fremde Zweitmeinung) wurde **nicht** gefahren, obwohl `deep` sie erlaubt | Briefing nach `~/shared/` schreiben, Owner holt die Zweitmeinung ein |

**Vierer-Abschluss**

- **Getan:** 8 PRs gemergt (Zustand je PR geprüft), zwei Melder-Defekte behoben (PR #2679, #2686, Tests nachgerechnet). Die vier Prod-Eingriffe und die Wiederanlaufprobe sind als Artefakt abgelegt, ihre Host-Ergebnisse aber aus dem Retro-Kontext nicht nachprüfbar.
- **Angenommen:** dass die Host-Messungen der Sitzung korrekt waren — sie sind aus dem Retro-Kontext nicht nachprüfbar.
- **Nicht verifizierbar:** die Herkunft der Prod-Handlungen aus GitHub-Artefakten; die Bewertungsanteile der Befunde 4 und §5b.
- **Offen geblieben:** vier Owner-Schritte in #2504, die Gate-Ausweitung aus §5a, die zwei Memory-Kandidaten.

## Self-Review (Phase 5, Meta-Agent gegen die Methode)

Ein separater Prüfer hat **nur diesen Bericht** gegen die Regeln der Methode gehalten,
nicht die Sitzung. Neun von zehn Punkten OK: Belegpflicht in der Befund-Tabelle
lückenlos, Scores ganzzahlig und je an einer Befund-Nummer verankert, Invariante
12 = 12 erfüllt, Frontmatter-Arithmetik korrekt (12 + 5 + 0 = 17, Quote 0,29),
Pfad kollisionsfrei, §5a mit Werkzeug-Gegenlauf und zulässiger Antwort, §8 mit
billigstem Check je Lücke, Verankerung erkennbar als Vorschlag.

**Ein Befund am Bericht:** unbelegte Positiv-Pauschalen — die Erfolgsbilanz in der
Zusammenfassung, die Aussage zur Wiederanlaufprobe und vier „Richtig"-Punkte im
Scorecard-Anker trugen keinen Beleg im Dokument, obwohl die Befund-Tabelle selbst
lückenlos belegt war. Alle vier Stellen sind nachgebessert: belegt, wo ein Artefakt
existiert; als nur-durch-Sitzungsverlauf-gedeckt gekennzeichnet, wo keines existiert.

Der Befund ist die Meta-Ebene desselben Musters, das die Sitzung inhaltlich teuer
zu stehen kam (Befund 2): eine Aussage reichte weiter als ihr Beleg — diesmal in
der eigenen Retrospektive.

**Numerische Einordnung der Quote:** 0,29 liegt am oberen Rand des bisherigen
Bands (0,00–0,29 über die vorangehenden acht Retros), nicht darüber. Kein Hinweis
auf zu laxe Finder (>0,8) und keiner auf Falsifikations-Theater (<0,2).

## Korrektur zu §5a (nachgetragen 2026-09-02, nach Owner-Go zur Umsetzung)

**Die Diagnose in §5a war falsch.** Dort steht, der Scanner des Gates
`claim-before-cheapest-check` lese nur die Antwort an den Owner und nicht den
Text, der ins Repo wandert. Beim Bau der empfohlenen Ausweitung stellte sich
heraus: **er liest PR- und Issue-Texte längst.**

`tools/claude-hooks/evidence_claim_scanner.py` enthält `_published_bodies()` —
die Funktion sammelt Texte aus `gh`-Kommandos mit `--body`, Heredoc und
`--body-file` und löst dabei sogar `Write`-Inhalte desselben Zuges auf. Der
Escrow-Satz aus Befund 2 lief genau über diesen Weg und wurde also **gesehen**.

**Warum er trotzdem durchkam:** Das Gate feuert, wenn eine prüfbare Behauptung
vorliegt **und** der Zug keinen belegenden Werkzeug-Lauf hat. Beim Escrow lief
ein Werkzeug — `scp` und `sha256sum` — es belegte nur die falsche Ebene. Das ist
die Klasse *„Werkzeug lief, trägt aber nicht"*, die die Messung zu #2374 am
selben Tag auf rund 13 % geschätzt hat, nicht die Klasse *„kein Werkzeug"*.

### Die dafür gebaute Regel existiert bereits — und ist gemessen worden

Der Scanner trägt eine **Subjektbindung**: ein Werkzeug-Lauf entlastet nur, wenn
er den genannten Gegenstand berührt. Sie steht seit 2026-08-20 in einem
Kalibrierfenster, protokolliert also nur (`kinds=subjekt-unbelegt-kalibrierung`),
statt zu blocken. `gate_wirkung.py` meldete die Mindestzahl als erreicht.

Ein fremder Prüfer hat die protokollierten Fälle beurteilt — neutral beauftragt,
im Zweifel gegen die Regel:

| | |
|---|---|
| Protokollierte Fälle | 13 |
| Als **echt** beurteilt | **1** |
| Trefferquote | **8 %** |
| Hausschwelle für ein blockierendes Gate | ~50 % |

Der eine echte Treffer ist inhaltlich einschlägig: ein Lauf von `make test-pg`
lokal, danach die Aussage, die CI-Tests liefen wieder.

**Empfehlung, geändert gegenüber §5a:** nicht *ausweiten* — die Ausweitung gibt
es schon — sondern die Subjektbindung in ihrer heutigen Form **herabstufen**. Die
Erkennung ist zu grob: jede Zeichenkette in Backticks und jede Issue-Nummer gilt
als Gegenstand, und die bloße Abwesenheit dieser Zeichenkette im Belegtext löst
aus. Der Prüfer schlägt stattdessen eine Kontextprüfung vor: nur feuern, wenn der
Belegtext ein **anderes** CI-/Prod-/Repo-Stichwort trägt als der Behauptungssatz —
genau das Muster des einzigen echten Falls.

Die Registry-Änderung selbst bleibt Owner-Zug (Charta: Gate-Zustände sind nicht
selbstbetreffend änderbar). Das Kalibrierfenster läuft am **2026-09-03** ab.

### Was diese Korrektur über die Retro selbst sagt

Der Befund in §5a war die **einzige Stelle des Berichts, an der eine Diagnose
ohne Blick in den Code entstand** — aus dem beobachteten Verhalten geschlossen
statt an der Quelle geprüft. Er hat den Meta-Review passiert, weil dieser die
Belegpflicht der Befund-Tabelle prüft, nicht die der Empfehlungen in §5a/§6.

Das ist dieselbe Klasse wie Befund 2 und Befund 3, diesmal in der Retrospektive:
eine Aussage reichte weiter als ihr Beleg. Der billigste Check wäre ein `grep`
im Scanner gewesen, vor dem Satz.
