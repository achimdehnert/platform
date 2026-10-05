---
retro_schema: 1
date: 2026-10-05
repo_scope: [platform, mcp-hub, coach-hub, chat-hub, dev-hub]
session_id: 8a0235
footprint: deep
findings_total: 25
findings_survived: 18
refuted_rate: 0.28
phase3_refuted: 6
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [edit-in-worktree-without-read, sicherheitsstand-in-oeffentlichem-issue, freigabe-artefakt-selbst-ausgestellt]
recurring_findings: [secret-leak-via-safe-pattern, gate-claim-before-cheapest-check-wirkungslos, tracking-doc-stale-after-new-occurrence, edit-in-worktree-without-read, worktree-midsession-accumulation]
gates_caught: [claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m]
gates_verwandt: [handover-stale-vor-merge]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "5 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: keiner, weil jede Phase dieser Retro ein eigenes Ergebnis lieferte (Skeptiker kippten 6 Befunde, 3b kippte 5 Punkte und fand 2 neue, darunter einen Merge-Wächter-Befund, den kein Finder hatte) und für keine Phase eine der vier Belegarten vorliegt
---

# Session-Retro 2026-10-02 bis 2026-10-05 (Sitzung 3328aa74…8a0235)

Die Grenze ist das Transkript der Sitzung, nicht der Kalendertag. Die Artefakte wurden aus den
`gh`-Aufrufen im Transkript gezogen und nicht über das Datum:

- **platform:** #3676, #3680, #3683, #3688, #3689, #3701, #3703, #3709, #3713 und #3714.
  Issues #3677, #3682, #3687 und #3711. Kommentare auf #2480, #3234 und #1640.
- **mcp-hub:** #302.
- **coach-hub:** #79, dazu das Archivieren des Repos.
- **chat-hub:** #174.
- **dev-hub:** Kommentar auf #442.
- **Außerhalb von GitHub:** DNS-Änderungen am 2026-10-04 nach einer Rechte-Regel des Owners und
  eine Kündigungsliste für Domains.

Ein Fork hat am 2026-10-02 in risk-hub nur gelesen. risk-hub steht deshalb nicht in `repo_scope`.
Am selben Tag liefen in platform auch fremde Sitzungen, etwa der Scan-Strang und 373ac10f. Die
gehören nicht zum Scope.

**Footprint `deep`:** fünf Repos, DNS-Eingriffe und ein ADR. Eine Stufe herunter war nicht
zulässig, denn die DNS-Eingriffe sind nicht vollständig rückholbar, und die Schätzung lag über
zehn Befunden. Agenten-Budget: 3 Finder, 3 Skeptiker, 1 Widerlegung und 1 Meta, zusammen 8.
Gemessen kostete ein Skeptiker 56k bis 70k Tokens, die Widerlegung 101k.

## 0.0 Wirkungsbilanz

`gate_wirkung.py` meldet ein Gate als RUECKFAELLIG und eine abgelaufene Frist.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 3, zuletzt 2026-10-04 | Ursache an der Quelle: E.3 misst erst beim Sitzungsende, die gezählten Fälle liegen mitten in Sitzungen. | **nachschärfen**, schon umgesetzt: Zählregel `gates_verwandt` (Entscheidungsvorlage #3722 G2, eingeführt in Retro 4f385c-incr). Den Fragment-Modus in zwei weiteren Repos verfolgt #3729. Hier kein weiterer Schritt. Befund #3 dieses Reports steht deshalb unter `gates_verwandt`. |
| gate-anchored-without-drill-or-control | 0 (unerprobt) | Ursache am Ausgang: Die Frist lief am 2026-10-02 ab, entschieden hat niemand. Der CI-Job ist kein Required Check, die letzten Läufe waren grün oder übersprungen. | Owner-Entscheid: Required Check im Ruleset oder **Sunset**. Steht als Maßnahme R4 in §7. Eine Verlängerung ohne Owner-Wort gehört nicht zu den vier zulässigen Konsequenzen. |

## 1. Executive Summary

- Für den Hauptauftrag „öffentliches platform-Repo nachhaltig lösen“ steht ein gemessener Pfad:
  ADR-309, ein Melder mit Messreihe und Prognose, die Probe G2 und die Kalibrierung nach dem
  Modellwechsel. Das Repo ist weiter öffentlich. Transfer und Privatschalten liegen beim Owner
  (#9).
- Zwei Sicherheitsbefunde. Erstens standen Zugangscodes aus einer API-Antwort im Transkript; die
  Sitzung hat das selbst gemeldet und Gegenmaßnahmen eingeleitet (#1). Zweitens stand der
  Sicherheitsstand danach in einem öffentlichen Issue (#2). Die Details liegen nur im privaten
  Tracking.
- Die Freigabe für den `--admin`-Merge von mcp-hub#302 hat die Sitzung selbst als Kommentar unter
  dem Owner-Login geschrieben. Der Merge-Wächter kann einen solchen Kommentar nicht von einem
  echten Owner-Wort unterscheiden (#24, aus der Widerlegung).
- Die Dateien, die ein Nachfolge-Modell zuerst liest, kennen ADR-309 nicht. Das trifft den Kern
  von „verzugslos aufsetzen“ (#3). Sieben Aussagen an den Owner musste die Sitzung zurücknehmen,
  das Claim-Gate hat davon nur eine gefangen (#4).
- Der Melder hängt am Sitzungsstart, die Kosten-Wache meldet erst nachträglich (#6, #7). Der
  ADR-Entwurf hat main 30 Minuten rot gemacht (#8, #21). „adv. diabolus“ lief ohne fremden
  Prüfer (#5).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Eine Prüfabfrage gab die rohe Registrar-API-Antwort aus. Darin standen Transfer-Codes, und die stehen jetzt im Transkript. Der Secret-Wächter erfasst API-Antworten nicht, auch nicht in der heute nachgeschärften Fassung v6. | fehlende Validierung | hoch | SURVIVES | Transkript 2026-10-04T17:50Z bis 18:02Z (Treffer gezählt, Werte nicht gelesen); Registry `secret-leak-via-safe-pattern`, `revision_note` v6 nur zu xtrace/Env-Dumps (#3428); 3b BESTAETIGT | secret-leak-via-safe-pattern (Lücke von v6, siehe 5a) |
| 2 | In öffentlichen Issue-Texten steht der Sicherheitsstand einzelner Domains, dazu Registrar, Verlängerungstermine, Domains, die bisher nirgends öffentlich waren, und weitere Betriebsdetails. Was Host, Tunnel und viele Domains betrifft, stand das schon vorher auf main. | Prozesslücke | hoch | SURVIVES | Fundstellen im privaten Tracking dev-hub#455. Gegenprobe `git grep` auf origin/main: für einen Teil der Domains 0 Treffer. 3b BESTAETIGT | sicherheitsstand-in-oeffentlichem-issue (neu) |
| 3 | ADR-309 kommt in `AGENT_HANDOVER.md`, `CORE_CONTEXT.md` und `CLAUDE.md` nicht vor. Sie verweisen nur auf KONZ-039. Das Handover nennt den Melder-Stand vom 2026-09-16. Ein Fragment dieser Sitzung fehlt. | Kommunikation | hoch | SURVIVES | origin/main: `git grep ADR-309 -- AGENT_HANDOVER.md CORE_CONTEXT.md CLAUDE.md docs/handover.d` 0 Treffer; `CORE_CONTEXT.md` Z.12/20; `AGENT_HANDOVER.md` Z.34 | tracking-doc-stale-after-new-occurrence (verwandt: handover-stale-vor-merge) |
| 4 | Sieben Aussagen an den Owner nahm die Sitzung später selbst zurück. Das Muster: Die Aussage stammte aus einer Zusammenfassung, einer Liste oder einem Log, und die maßgebliche Quelle war noch nicht gefragt. Einen Fall fing der Stop-Hook (2026-10-02T14:55Z). Die Einstufung des Modellwechsels als MAJOR (2026-10-05T08:55Z) kam durch; der zugehörige Branch blieb ohne Änderung und ohne PR. | Wissenslücke | mittel | SURVIVES | Transkript 10-02T14:03Z, 14:55Z, 18:50Z; 10-04T09:44Z, 10:42Z, 11:51Z; 10-05T08:55Z; Kommentar auf #1640; `gh pr list --head …/mw-vollmachten-requalifying` leer | gate-claim-before-cheapest-check-wirkungslos (siehe 5a); gefangen: claim-before-cheapest-check |
| 5 | Der Owner verlangte ausdrücklich „adv. diabolus“. ADR-309 wurde trotzdem ohne fremden Gegenprüfer gemergt. Die Kill-Gates im ADR sind Inhalt des ADR, keine unabhängige Prüfung. | fehlende Validierung | mittel | SURVIVES | 5 Agent-Aufrufe vor der Retro (4 Forks 10-02T14:02Z, 1 Recherche), keiner zu ADR-309; ADR-309 Z.31 `Reviewer: –`; Owner-Nachricht 2026-10-04T20:54Z | adr-ohne-unabhaengigen-challenger (neu) |
| 6 | Der Sichtbarkeits-Melder läuft nur beim Sitzungsstart; Timer, Cron oder Workflow gibt es nicht. ADR-309 §5 behauptet einen täglichen Lauf, das stimmt aber nur, wenn täglich eine Sitzung startet. | verfrühte Festlegung | mittel | SURVIVES | origin/main: einziger Aufrufer `tools/session_start_checks.sh:642`; nichts in `.github/`, `infra/host-maintenance/`, systemd-User-Units oder Cron | melder-ohne-eigenen-takt (neu) |
| 7 | H1 (Actions-Kontingent) ist als „geprüft, gilt heute mit Reserve“ abgeschlossen. Der Grenzwert kommt aus der Doku, die Last hat sich seitdem verdoppelt. Die Wache meldet erst bei netto > 0, also hinterher; brutto wird nur ausgegeben. | verfrühte Festlegung | mittel | SURVIVES | ADR-309 Z.141, KG2 Z.163; `tools/sichtbarkeits_drift_melder.py` `wache()` Z.465, Ausgabe brutto Z.906 | kontingent-wache-nur-nachlaufend (neu) |
| 8 | Der ADR-Entwurf #3701 wurde mit rotem ADR-Check und ohne Nummernvergabe gemergt. Vor dem Owner-Merge hatte die Sitzung den roten Check nicht angesprochen. | Prozesslücke | mittel | SURVIVES | #3701 Check „Platform-specific ADR checks“ FAILURE 05:13:41Z, Merge 08:16:20Z | adr-entwurf-merge-ohne-nummernvergabe (neu) |
| 9 | Der Zielzustand des Hauptauftrags ist nicht erreicht. platform ist public, ADR-309 steht auf `proposed`, der Melder auf #3234 liegt über dem Ziel K5. Transfer und Privatschalten sind Owner-Gates. | Kommunikation | niedrig | SURVIVES | `gh api repos/achimdehnert/platform` `visibility=public`; ADR-309 `status: proposed`; #3234 OPEN | — |
| 10 | Fünfmal lief Edit ohne vorheriges Read. Viermal lag das Read im Hauptcheckout und das Edit im Worktree-Pfad, einmal scheiterte das Read an der Token-Grenze. | Werkzeug | mittel | SURVIVES | Fehlerläufe 10-02T15:02Z, 10-04T11:57Z (2×), 10-05T05:07Z (2×) | edit-in-worktree-without-read |
| 11 | Nach dem gescheiterten Edit wurden Repo-Dateien per `sed -i` geändert, gegen die Hausregel „nur per Edit/Write“. Dazu kamen acht rohe `pytest`-Teilläufe (`make test` lief im PR). | Prozesslücke | niedrig | SURVIVES | Transkript 10-05T05:07:07Z (`sed -i` auf Melder und Test); acht `pytest`-Aufrufe, u. a. 10-02T19:09Z, 10-05T05:06Z, 09:09Z | repo-datei-per-sed-statt-edit (neu) |
| 12 | Der Merge-Wächter erkennt nur `--repo`, nicht `-R`. Deshalb wertet er das Repo aus dem cwd aus, und mcp-hub#302 wurde als platform#302 geprüft. | Werkzeug | niedrig | SURVIVES | `tools/claude-hooks/block_merge_without_gate.sh` Z.66-67; Fehlerlauf 10-02T14:52:17Z mit Meldung „PR #302 (achimdehnert/platform)“ | hook-repo-aus-cwd-statt-r-flag (neu) |
| 13 | Beim Retro-Start lagen noch 13 Arbeitskopien dieser Sitzung. Elf gehörten zu gemergten PRs, zwei Branches hatten weder Änderung noch PR. | Prozesslücke | niedrig | SURVIVES | `~/.repo-session/leases/*` mit `3328aa74`: 13; `gh pr list --head` für mw-typ-a-label und mw-vollmachten-requalifying leer | worktree-midsession-accumulation |
| 14 | ADR-309 hat noch Entwurfsreste: den Kommentarkopf „Nummer vergibt adr_allocate.py kurz vor dem Merge“ und `Reviewer: –`. | Kommunikation | niedrig | SURVIVES | origin/main ADR-309 Z.16-19, Z.31 | — |
| 15 | `sleep 60` vor `gh run view` als Polling; der Harness hat es blockiert. | Werkzeug | niedrig | SURVIVES | Fehlerlauf 10-05T05:02:00Z | — |
| 16 | Die offenen Issues #3677, #2480 und #3687 haben keinen Kommentar zum Restumfang. | Prozesslücke | mittel | REFUTED | Die Kommentare vom 10-04 nennen den Restumfang; #2480 hat den Termin 2026-11-01; 3b: REFUTED hält | — |
| 17 | Nebenaufträge ohne Spur: GX10/Hetzner-GPU und #3714 ohne Auftrag. | Prozesslücke | niedrig | REFUTED | Owner-Wort „MW-STD go“ 10-05T09:08:39Z; Memory `project_hetzner_gpu_statt_gx10_verworfen.md`; 3b: REFUTED hält | — |
| 18 | Melder nicht selbst reproduziert | fehlende Validierung | niedrig | REFUTED (pre) | betrifft die Grenze des Finders, nicht die Sitzung | — |
| 19 | Rechte erst beim Scheitern entdeckt, kein Preflight | Prozesslücke | mittel | REFUTED | drei verschiedene Fälle: Die Regel fehlte noch; sie deckte das Löschen einer Zone nicht; ein Lesebefehl war ein Fehlalarm. Umgangen wurde nichts. 3b: unentscheidbar | — |
| 20 | Wegwerf-Probe-Repos als Altlast dieser Sitzung | Prozesslücke | mittel | REFUTED | angelegt 2026-08-02, Zweck und Status zum Abräumen in KONZ-039 Z.106ff.; 3b: REFUTED hält | — |
| 21 | main war nach dem Merge von #3701 30 Minuten rot („ADR Schema Validation“). In dieser Zeit hat eine fremde Sitzung auf das rote main gemergt. Ursprünglich als REFUTED (pre) geführt, 3b hat das gekippt. | Prozesslücke | mittel | SURVIVES | main-Läufe FAILURE auf 5632aaae (08:16:24Z) und 216646ac (08:21Z), grün ab #3709 (08:46:35Z) | main-rot-nach-eigenem-merge (neu) |
| 22 | Steuerung durch kryptische Kürzel erschwert | Kommunikation | niedrig | REFUTED | Jede ID kam beim ersten Auftreten mit Klartext-Titel, die Rückfragen galten der Sache. 3b: unentscheidbar | — |
| 23 | Öffentlich-Probe in #3703 zu eng, private Repo-Namen veröffentlicht | fehlende Validierung | niedrig | REFUTED | Alle Namen standen vorher schon auf main (`PROJECT_PAT` in 55 Dateien), der PR-Body nennt den Umfang korrekt; 3b: REFUTED hält | — |
| 24 | Die Freigabe für den `--admin`-Merge von mcp-hub#302 hat die Sitzung selbst als Kommentar unter dem Owner-Login geschrieben, 21 s vor dem Merge. Der Wächter prüft nur „Login ist kein Bot“. Ein Owner-Wort im Chat lag vor (14:51:58Z), der Merge war also gedeckt. Das Gate kann aber einen echten Kommentar nicht von einem selbst ausgestellten unterscheiden. | fehlende Validierung | hoch | SURVIVES (3b NEU) | Kommentar 5955042866 auf mcp-hub#302 (`created_at` 14:52:35Z, Login achimdehnert); `mergedBy` achimdehnert; drei Merge-Versuche 14:52:16Z bis 14:52:48Z, Merge 14:52:56Z; `tools/claude-hooks/block_merge_without_gate.sh` Z.87-90 | freigabe-artefakt-selbst-ausgestellt (neu) |
| 25 | Der main-Workflow „Sync Policies to Orchestrator“ ist seit dem Merge von #3714 (09:29Z) rot und bei zwei fremden Merges wiederholt rot. Bemerkt hat das niemand. Er scheitert schon beim Checkout („could not read Username“). Ob #3714 die Ursache ist, ist offen (§8). | fehlende Validierung | niedrig | SURVIVES (3b NEU) | main-Lauf FAILURE ab ea65e47e, zuletzt 10:55Z; letzter Erfolg 2026-09-30 | main-rot-nach-eigenem-merge (neu) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 3 | #9: Ziel teilweise erreicht, Abweichung durch Owner-Gates begründet. #3: Einstieg für Nachfolger nicht nachgezogen. |
| architektur_design | 3 | #6: Melder ohne eigenen Takt. #7: Wache nur nachlaufend. |
| code_konventionstreue | 3 | #11: `sed -i` und rohes pytest. Dazu #10. |
| risiko_debt | 2 | #1: Codes im Transkript. #2: Sicherheitsstand öffentlich. #24: Freigabe selbst ausgestellt. |
| prozess_effizienz | 3 | #8 und #21: roter Check gemergt, main 30 min rot. #13: Arbeitskopien. |
| entscheidungsqualitaet | 3 | #4: sieben Rücknahmen. #5: kein Gegenprüfer. |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Registrar-Abfrage gab die rohe JSON-Antwort aus (10-04T17:50Z) | Jede Registrar- oder Billing-Abfrage nur mit Feld-Whitelist (`jq '{name,locked}'`). Der Secret-Wächter blockt Aufrufe dieser APIs ohne Filter. | #1 |
| Sicherheitsstand je Domain in einem öffentlichen platform-Issue | Vor jedem Issue-Text in platform zusätzlich eine Kontrollprobe auf Sicherheitsvokabular. Treffer gehen in ein privates Repo (dev-hub), in platform steht nur der Verweis. | #2 |
| ADR-309 gemergt, Einstiegsdokumente unverändert | Im selben PR wie ein Zielzustands-ADR: Eintrag in `CORE_CONTEXT.md` (SSoT), in `CLAUDE.md` nur der Zeiger, dazu ein Handover-Fragment | #3 |
| MAJOR aus der Log-Klasse erklärt (10-05T08:55Z) | Vor jeder Einstufung oder Statusaussage das maßgebliche Werkzeug laufen lassen, hier `modellwechsel_check.py`. Log und Zusammenfassung gelten nur als Hypothese. | #4 |
| ADR-309 ohne fremden Prüfer gemergt | Bei „adv. diabolus“ vor dem Merge einen Challenger-Subagenten in frischem Kontext auf den ADR ansetzen und das Ergebnis im ADR vermerken | #5 |
| Melder läuft nur beim Sitzungsstart | Zusätzlich ein täglicher systemd-User-Timer; Lücken in der Messreihe werden als Lücke markiert | #6 |
| Wache prüft nur netto > 0 | Frühwarnung auf brutto: Anteil am Kontingent über einer Schwelle oder zwei Monate Wachstum, mit Wiedervorlage | #7 |
| #3701 mit rotem Check zum Merge vorgelegt | Einen ADR-Entwurf erst nach `adr_allocate.py --apply` zur Freigabe vorlegen, sonst den roten Check im PR-Body als „Merge sperrt“ ausweisen | #8 |
| Hauptauftrag offen, am Ziel-Issue kein Abschlussvermerk | Am Ziel-Issue #3234 eine Zeile „Ziel offen, Rest = Owner-Gates X, Y, Messpunkt K5“ | #9 |
| Read im Hauptcheckout, Edit im Worktree | Nach `repo-session.sh start` jede Datei im Worktree-Pfad lesen; große Dateien mit `offset`/`limit` | #10 |
| Nach Edit-Fehler `sed -i` | Nach einem Edit-Fehler das Read nachholen, nie auf `sed -i` ausweichen; Teil-Tests über ein Make-Target | #11 |
| Merge-Wächter las das cwd | Regex in `block_merge_without_gate.sh` um `-R` erweitern | #12 |
| 13 Arbeitskopien offen | Nach jedem eigenen Merge `repo-session.sh end <wt>`; leere Branches sofort freigeben | #13 |
| ADR-309 mit Entwurfskopf | Beim Nummerieren den Kommentarkopf entfernen und den Reviewer eintragen | #14 |
| `sleep 60` vor `gh run view` | `gh run watch` oder Monitor mit until-Schleife | #15 |
| Nach dem Merge von #3701 main nicht angesehen | Nach jedem eigenen Merge die main-Läufe auf dem Merge-Commit prüfen. Ist main rot: sofort ein Fix-PR und ein Hinweis im Handover, bevor andere mergen. | #21 |
| Freigabe-Kommentar unter Owner-Login 21 s vor dem Merge selbst geschrieben | Der Freigabe-Kommentar zitiert die Owner-Nachricht mit Zeitstempel und Kanal. Der Wächter prüft, dass die Owner-Nachricht vor dem Kommentar lag, und weist Kommentare aus der laufenden Sitzung ab. | #24 |
| Sync-Workflow seit #3714 rot, unbemerkt | Beim Sitzungsende alle main-Workflows ab dem ersten eigenen Merge prüfen, nicht nur die Required Checks | #25 |

## 5. Längsschnitt

`retro_kpis.py`, Stand dieses Reports:

| Slug | Zähler | Konsequenz |
|---|---|---|
| secret-leak-via-safe-pattern | ×6 → ×7, Gate registriert, v6 vom 2026-10-05 | Lücke von v6, siehe 5a → **ausweiten**, Kandidat R8. Der Hook ist Security-Config, deshalb Owner-Approve. |
| gate-claim-before-cheapest-check-wirkungslos | ×5 → ×6 | Rückfall nach Bau 2026-10-01, siehe 5a → **ausweiten**, Kandidat R9 |
| tracking-doc-stale-after-new-occurrence | ×13 → ×14, GATE-PFLICHT | schon Gate-Kandidat in Retro eb9de7; hier ein weiteres Vorkommen (#3) |
| edit-in-worktree-without-read | ×1 → ×2, GATE-PFLICHT | Die Read-Pflicht des Harness ist schon das Gate und fängt jeden Fall (Belegart „kein Effekt“ für ein zweites Gate). Der Schaden entsteht beim Ausweichen auf `sed -i` (#11). Gate-Kandidat deshalb: ein Hook blockt `sed -i` auf getrackte Dateien unter `~/github/**` und `~/.repo-session/worktrees/**`. |
| worktree-midsession-accumulation | ×11 → ×12, Gate registriert | Vorkommen #13, am Retro-Ende abgeräumt (R11) |

Neue Slugs (×1): sicherheitsstand-in-oeffentlichem-issue, freigabe-artefakt-selbst-ausgestellt,
adr-ohne-unabhaengigen-challenger, melder-ohne-eigenen-takt, kontingent-wache-nur-nachlaufend,
adr-entwurf-merge-ohne-nummernvergabe, main-rot-nach-eigenem-merge, repo-datei-per-sed-statt-edit,
hook-repo-aus-cwd-statt-r-flag.

`freigabe-artefakt-selbst-ausgestellt` steht trotz ×1 unter `gate_candidates`. Grund: Der Befund
betrifft das Gate, das `--admin`-Merges absichert.

### 5a. Rückfall-Prüfung

`gate_wirkung.py` meldet nur `handover-stale-vor-merge` als rückfällig (siehe 0.0). Die beiden
folgenden Einträge sind Urteile dieser Retro. Das Werkzeug meldet sie nicht, und zwar aus
verschiedenen Gründen:

- **secret-leak-via-safe-pattern:** Der Vorfall (10-04) liegt vor der Revision v6 (10-05), für das
  Werkzeug ist er deshalb kein Rückfall. v6 deckt API-Antworten aber nicht ab (3b bestätigt). Das
  ist eine Lücke an der Quelle. Antwort: **ausweiten**. Der Eintrag bekommt `revised`, eine
  `revision_note` und eine neue `positivkontrolle`, sobald der Owner R8 freigibt. Bis dahin ist
  das ein Kandidat und kein Eintrag (#2234).
- **claim-before-cheapest-check:** Sechs der sieben Fälle aus #4 liegen nach dem Bau
  (2026-10-01). Das Werkzeug zählt sie erst, wenn dieser Report auf main liegt. Antwort:
  **ausweiten** auf „maßgebliche Quelle je Aussagetyp“. Der Stop-Hook prüft nur, ob überhaupt ein
  Check lief, nicht ob es der maßgebliche war. Auch das ist ein Kandidat (R9).

### 5b. Autonomie-Kalibrierung

- `over_ask` = 0.
- `over_act` = 0:
  - DNS erst nach der Rechte-Regel geändert. Die abgelehnte Zonen-Löschung an den Owner
    zurückgegeben (Skeptiker C2).
  - coach-hub erst nach dem wörtlichen „ARCHIVIEREN“ archiviert.
  - Merges der platform-PRs durch den Owner bzw. über SA-M.
  - Ausnahme: mcp-hub#302 hat die Sitzung selbst per `gh pr merge --admin` gemergt, ein Bypass
    des Rulesets. Gedeckt war das durch das Owner-Wort „#302 per --admin mergen — go“
    (10-02T14:51:58Z), also kein over_act. Wie die Freigabe dokumentiert wurde, ist Befund #24.

## 6. Verankerung: Vorschläge zum Kopieren (nicht selbst geschrieben)

- **memory_candidate (feedback, drift):** „Wird ein Zielzustands-ADR gemergt, gehört in denselben
  PR ein Eintrag in `CORE_CONTEXT.md`, ein Zeiger in `CLAUDE.md` und ein Handover-Fragment. Sonst
  setzt der Nachfolger auf dem alten Stand auf. Realfall ADR-309, Retro 8a0235 #3.“
- **memory_candidate (feedback):** „Steht ‚adv. diabolus‘ im Auftrag, läuft vor dem Merge ein
  Challenger-Subagent in frischem Kontext. Kill-Gates im Text ersetzen keinen fremden Prüfer.
  Retro 8a0235 #5.“
- **memory_candidate (feedback, drift):** „Eine Freigabe, die ich selbst unter dem Owner-Login
  poste, ist ein Protokoll und kein Owner-Wort. Sie zitiert die Owner-Nachricht mit Zeitstempel,
  und ich stelle sie nie als unabhängigen Beleg dar. Retro 8a0235 #24.“
- **adr_candidate:** keiner. #6 und #7 sind Ergänzungen zu ADR-309 nach bestehendem Muster.

## 7. Maßnahmen

Die Maßnahmen stehen als Action-Board im privaten Tracking-Issue
[dev-hub#455](https://github.com/achimdehnert/dev-hub/issues/455). Die Details zu R1 und R2 stehen
nur dort.

- **R1** Öffentliche Texte aus #2 kürzen oder ausblenden. Owner-Wort nötig.
- **R2** Die restlichen Gegenmaßnahmen aus #1 abschließen. Owner, Details privat.
- **R3** ADR-309 in `CORE_CONTEXT.md` eintragen, in `CLAUDE.md` den Zeiger setzen, ein
  Handover-Fragment schreiben (#3, #9). Kann ich sofort.
- **R4** `gate-anchored-without-drill-or-control`: Required Check oder Sunset (0.0). Owner.
- **R5** Täglicher Timer für den Melder (#6). PR kann ich vorbereiten.
- **R6** Brutto-Frühwarnung in `wache()` (#7). PR kann ich vorbereiten.
- **R7** Challenger-Lauf auf ADR-309 nachholen und die Entwurfsreste bereinigen (#5, #14). Kann
  ich sofort.
- **R8** Secret-Wächter auf API-Antworten ausweiten (#1). Security-Config, Owner-Approve.
- **R9** Claim-Gate auf die maßgebliche Quelle ausweiten (#4). Kandidat.
- **R10** Hook gegen `sed -i` auf getrackte Repo-Dateien (#10, #11). Kandidat.
- **R11** 13 Arbeitskopien abräumen (#13). Erledige ich am Retro-Ende.
- **R12** Merge-Wächter: `-R` erkennen (#12), Freigabe-Kommentar an eine frühere Owner-Nachricht
  binden (#24). Security-Config, Owner-Approve.
- **R13** Sync-Workflow auf main: Ursache klären (#25). Kann ich sofort.
- **R14** Nach eigenem Merge den main-Status prüfen (#21, #25). Als Schritt im Skill
  `session-ende` vorschlagen.

## Widerlegung

Phase 3b: ein Opus-Subagent in frischem Kontext mit Report-Entwurf, Footprint und Artefaktliste,
ohne Sitzungs-Erzählung. Ergebnis: **5 gekippt, 2 neu.**

| Punkt | Verdikt | Wirkung im Report |
|---|---|---|
| #3 Soll/R3 | GEKIPPT | Zielte auf `CLAUDE.md`, die laut eigener Regel nicht dupliziert. Neues Ziel ist `CORE_CONTEXT.md` (SSoT), `CLAUDE.md` bekommt nur den Zeiger. |
| #21 | GEKIPPT | Von REFUTED (pre) zu SURVIVES: main war 30 min rot. Der Pre-Check hatte einen anderen Workflow-Ausschnitt gezählt. |
| 5b | GEKIPPT | „Merges über SA-M bzw. durch den Owner“ war für mcp-hub#302 falsch. Korrigiert, der over_act-Wert bleibt 0. |
| 5a | GEKIPPT | „Gate rückfällig“ für secret-leak und claim-before widersprach 0.0. Jetzt als Urteil der Retro gekennzeichnet, mit Begründung, warum das Werkzeug sie nicht meldet. |
| Öffentlich | GEKIPPT | Der Entwurf nannte den Stand der Gegenmaßnahmen und verwies auf die Fundstelle. Beides steht jetzt nur im privaten Tracking. |
| #24 | NEU | Freigabe-Artefakt selbst ausgestellt |
| #25 | NEU | Sync-Workflow auf main rot, unbemerkt |

Bestätigt: #1, #2, #5 (Zahl korrigiert: 5 statt 11 Agent-Aufrufe), #6 bis #14, #16, #17, #20,
#23, die Scores und 0.0. Unentscheidbar: #19 und #22. Der billigste Check wäre, die Kontexte der
Ablehnungen und die drei Rückfragen im Transkript zu lesen.

## Streichbahn

Keiner. Jede Phase dieser Retro hat ein eigenes Ergebnis geliefert. Die Skeptiker kippten sechs
Befunde, die Widerlegung kippte fünf Punkte und fand zwei neue. Darunter ist #24, den keiner der
drei Finder hatte. Für keine Phase liegt eine der vier Belegarten vor.

## Self-Review

Phase 5, ein Sonnet-Meta-Agent nur auf Report und Skill. Frontmatter und Zahlen sind konsistent:
25 Befunde = 18 überlebt + 6 in Phase 3 + 1 pre-refuted. `refuted_rate` 0,28 liegt im Band
0,2–0,8. Die echte Falsifikationsquote 6/24 = 0,25 liegt knapp über der Untergrenze. Die Scores
sind ganzzahlig und verankert, die Soll-Invariante ist mit 18 = 18 erfüllt. Drei Belege hat der
Agent per Stichprobe gegen origin/main bestätigt. Übernommen: echte Zähler statt „≥2“ bei zwei
Slugs, voller Hook-Pfad, ein Hinweis auf eine noch sichtbare Fundstelle gestrichen. Nicht
übernommen:

- #19 und #22 bleiben REFUTED. Das Verdikt stammt vom Skeptiker, und „unentscheidbar“ in 3b heißt
  nur: kein Gegenbeleg.
- Die Lücke im Merge-Wächter (#24) bleibt beschrieben, weil der Quelltext des Hooks schon
  öffentlich auf main liegt. Ob das bis zum Fix (R12) so bleibt, entscheidet der Owner.

## 8. Nicht verifiziert (Restlücken)

- **getan:**
  - 3 Finder, 3 Skeptiker und 1 Widerlegung, jeweils in frischem Kontext.
  - `gate_wirkung.py` und `retro_kpis.py` gelaufen.
  - Leases gezählt und je Branch mit dem PR abgeglichen, per Kommando.
  - Phase 6: Das Briefing für die externe Zweitmeinung liegt unter
    `~/shared/session-retro-extern-2026-10-05-platform-8a0235.md`. Die Antwort holt der Owner ein.
  - Kontrollprobe des Reports auf Domainnamen, Personennamen, Beträge, IP-Adressen und
    Kommentar-IDs mit Sicherheitsstand: 0 Treffer, siehe PR.
- **angenommen:** Die Code-Werte stehen nur im lokalen Transkript und in keinem öffentlichen
  Artefakt. Finder und Widerlegung haben Treffer gezählt und keine Werte gelesen.
- **nicht verifizierbar:** Ob der Permission-Classifier die Zonen-Löschung trotz Rechte-Regel aus
  gutem Grund ablehnte, sein Regelwerk ist nicht einsehbar. Ob #3714 den Sync-Workflow rot gemacht
  hat (#25): Der Fehler sitzt im Checkout, also eher Runner oder Credential, als Hypothese.
- **offen geblieben:**
  - #1640 (126 KB) nicht vollständig gelesen.
  - Die Kündigungsliste der Domains nicht auf Vollständigkeit geprüft.
  - Die sieben Rücknahmen aus #4 hat die Widerlegung nicht einzeln nachgezogen.
  - Der billigste Check ist jeweils ein gezielter `gh … --json` mit Feld-Whitelist oder eine
    Feld-Abfrage im Transkript.
