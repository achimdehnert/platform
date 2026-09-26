---
retro_schema: 1
date: 2026-09-14
repo_scope: [platform, news-hub, mcp-hub, dev-hub, risk-hub, writing-hub, music-lab, illustration-hub, illustration-fw, iil-pet-portal, ausschreibungs-hub]
session_id: oqu6Z6
footprint: deep
findings_total: 27
findings_survived: 16
refuted_rate: 0.41
phase3_refuted: 10
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 2
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 2
gate_candidates: [fleet-implementierung-ohne-konformitaets-fixture, melder-scope-enger-als-das-repo, freigabe-issue-nicht-geschlossen-nach-merge, kriterium-als-erreicht-gegen-eigene-betriebsakte]
recurring_findings: [claim-before-cheapest-check, same-file-serial-prs, parallel-session-pr-collision, handover-stale-vor-merge, worktree-midsession-accumulation, issue-offen-nach-gemergtem-fix, partial-fix-not-generalized-to-sibling-artifacts, test-asserts-the-case-in-mind-not-the-harmful-one, host-fix-not-mirrored-to-iac, secret-leak-via-safe-pattern, melder-ohne-praezisionsmass]
gates_caught: [aufschub-anker]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "8 gekippt, 1 neu"
streichkandidaten: [deferred-item-no-tracking-issue]
---

# Session-Retro 2026-09-14 — platform + 10 Fleet-Repos — Auftrag #3015 geschlossen, Secret-Leck #3129 in drei Stufen

## 1. Executive Summary

- Der Auftrag [#3015](https://github.com/achimdehnert/platform/issues/3015) wurde mit „Alle fünf Kriterien sind erreicht und belegt" geschlossen — **K3 war es nicht**: die eigene Betriebsakte der Morgen-Zeitung führt ihre Verfallsignale als „Soll", die neu gebauten Melder haben keinen Vorlauf, und die Positivkontrolle war weder künstlich noch im Journal belegt (#4, von der Widerlegungsbahn zurückgekippt).
- Ein Secret-Leck (Schlüsseldatei ohne `NAME=`-Form gesourct, die Shell schrieb den Wert in ihre Fehlermeldung) löste einen dreistufigen Plan aus. Die dokumentierte Reihenfolge „erst alle Leser tolerant, dann die Dateien" wurde **nicht eingehalten**: 25 Dateien wurden umgestellt, bevor irgendein toleranter Leser existierte (#26).
- Der schwerste Befund ist ein **stiller Fehler in fünf gemergten Repos**: die unabhängig nach Prosa gebauten Leser-Kopien lesen einen nackten base64-Wert wie `Abc123xyz==` als Name plus Wert `=`, aus `…=` wird ein leerer String. Die platform-Quelle behandelt und testet den Fall, keine Kopie tut es ([#3155](https://github.com/achimdehnert/platform/issues/3155), Befund #27).
- Der offengelegte Schlüssel war der funktionierende; seine Rotation stand bei Sitzungsende noch aus — korrekt als Owner-Gate geführt, aber offen (#10).
- Das Urteil dieser Retro wurde zweimal umgebaut: die Skeptiker verwarfen vier Befunde, die Widerlegungsbahn kippte acht Punkte — darunter vier der fünf `hoch`-Befunde des Entwurfs — und fand einen neuen. 11 von 27 Befunden sind verworfen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | #3149 (0 Kommentare, offen) wurde als Autorität für den Abschluss von #3015 zitiert | Prozesslücke | hoch | **REFUTED** (Phase 3; 3b BESTAETIGT) | K4 von #3149 lautet „#3015 mit Abschluss-Kommentar (K1–K5 je Beleg-Link) geschlossen" — die Herkunft zu zitieren ist die vorgesehene Mechanik. 3b-Korrektur an der Stützbegründung: der vom Skeptiker zitierte #3129-Kommentar (07:11:29Z) entstand nach dem Schließen (07:06:04Z) | – |
| 2 | Abschluss-Kommentar #3015 nennt drei offene Folgearbeiten nicht (#3050, #3047, #3069) | Kommunikation | mittel | **REFUTED** (pre) | #3050 wird im Abschluss wörtlich als „Waisen-Melder #3050" genannt | – |
| 3 | Zwei weiterhin offene Folgearbeiten (#3047, #3069) fehlen im Abschluss-Kommentar von #3015 | Kommunikation | niedrig | **SURVIVES** (kommandobelegt) | `gh issue view 3047/3069` → beide OPEN; Abschluss nennt nur #3050, #3080, news-hub#46, #3129, #3149 | – |
| 4 | #3015 wurde mit K3 „erreicht" geschlossen, obwohl K3 Verfallsignale **mit Schwelle und Vorlauf** und eine **künstliche** Positivkontrolle **mit Journal-Beleg** verlangt | fehlende Validierung | hoch | **SURVIVES** (Phase 3 REFUTED, 3b GEKIPPT) | Voller K3-Wortlaut in `gh issue view 3015`; news-hub `origin/main:docs/betrieb/morgen-zeitung.md` Abschnitt „## Verfallsignale (K3, **Soll**)" mit „kein Melder" für vier Signale; neue Melder feuern „jeden Aufruf" bzw. „jede Ausgabe" — ohne Vorlauf | `claim-before-cheapest-check` ×81 → ×82 |
| 5 | Scope wuchs von zwei auf elf Repos ohne dauerhaft festgehaltenen Scope-Checkpoint | Prozesslücke | mittel | **REFUTED** (Phase 3 SURVIVES, 3b GEKIPPT) | GraphQL `userContentEdits` von #3129: um 2026-09-13T18:09:22Z trug der Body „Freigabe: akzeptiert durch Owner — ‚S2 Stufe 2 go'" mit allen neun Repos, vor dem ersten Fremd-Merge; #3149 nennt die elf Repos mit Owner-Freigabe | – |
| 6 | Stufe-2-Ausrollung erreichte 7 von 9 Repos; mcp-hub#265 und risk-hub#750 blieben offen | Prozesslücke | mittel | **REFUTED** (3b GEKIPPT) | risk-hub#750 um 07:35:55Z gemergt, Staging Gate 07:25:41Z grün, risk-hub#752 07:36:08Z geschlossen; offen bleibt nur mcp-hub#265 | – |
| 7 | #3129-Kommentar 07:11:29Z sagt „CI läuft", obwohl der Lauf 85 s zuvor rot war | fehlende Validierung | mittel | **REFUTED** (3b GEKIPPT) | Run 34816253205 ist der Workflow **Staging Gate**, nicht CI; „Lint + Test" lief tatsächlich 07:12:39–07:15:17Z (`check-runs` für `0d894731`) — Auslassung eines roten Gates, keine Falschaussage | – |
| 8 | „Freigabe für PR #N"-Issues bleiben offen, obwohl ihr PR gemergt ist — inzwischen fünf | Prozesslücke | niedrig | **SURVIVES** (kommandobelegt; 3b BESTAETIGT) | dev-hub#354/#353, illustration-hub#353/#352, illustration-fw#34/#33, iil-pet-portal#52/#51; zusätzlich risk-hub#751 nach dem Merge von #750 | `issue-offen-nach-gemergtem-fix` ×0 → ×1 |
| 9 | Freigabe-Vermerk uneinheitlich abgelegt: music-lab#58 und ausschreibungs-hub#299 tragen ihn nur zentral in platform#3129 | Prozesslücke | niedrig | **SURVIVES** (kommandobelegt) | `gh pr view 58 --repo achimdehnert/music-lab --json body,comments` und `gh pr view 299 --repo iilgmbh/ausschreibungs-hub` → keine „Freigabe"-Zeile im eigenen Repo | – |
| 10 | Der offengelegte Schlüssel war der funktionierende (writing-hub-Stand), nicht der tote; seine Rotation war bei Sitzungsende nicht vollzogen | fehlende Validierung | hoch | **SURVIVES** (Phase 3; 3b BESTAETIGT mit Korrektur) | news-hub#46 trennt beide Schlüssel ausdrücklich; #3149 „Z2 Groq-Schlüssel verteilen \| Skript fertig, Sitzungs-Filter blockt Transfer \| Security-Config + Prod". 3b-Korrektur: die Zahl „7 Dateien, 8 Container" bezieht sich auf den **toten** Schlüssel, nicht auf den offengelegten | `secret-leak-via-safe-pattern` ×3 → ×4 |
| 11 | Der Melder aus #3141 scannt nur `tools/infra/scripts/deployment`; Leser in `.github/scripts/` lesen Secret-Dateien weiterhin roh | fehlende Validierung | mittel | **SURVIVES** (kommandobelegt; 3b BESTAETIGT mit Korrektur) | `git grep -n "read_text().strip()" origin/main -- .github/scripts` → `adr_sync_to_memory.py:39`, `docu_update_agent.py:58`; Scanner-Scope `tools/tests/test_secret_lesen.py:347`. 3b: beide Skripte lesen in CI zuerst die Umgebung — Wirkung nur bei lokalen Läufen | `partial-fix-not-generalized-to-sibling-artifacts` ×13 → ×14 |
| 12 | Dieselbe unvollständige Verbraucher-Inventur trat in drei Repos unabhängig auf | Prozesslücke | hoch | **REFUTED** (3b GEKIPPT) | mcp-hub#266 (17:53Z) und music-lab#59 (18:00Z) wurden vor jedem Merge angelegt und sagen „bewusst nicht mit umgestellt" — ein getrackter Split derselben zentralen Inventur; der dritte Fall zählt #11 doppelt | – |
| 13 | Sieben Fremd-Repos mergten den Leser vor der Quelle platform#3141 — eine verfrühte Festlegung | verfrühte Festlegung | hoch | **REFUTED** (Phase 3 SURVIVES, 3b GEKIPPT) | Alle neun Stufe-2-PRs wurden 17:48:48Z–17:59:19Z angelegt, #3141 erst 18:08:09Z — kein Kopier-Verhältnis, sondern unabhängige Implementierungen (`_KV_LINE_RE`, `_NAME_WERT_MUSTER`, `_NAME_WERT_RE`, Bash); „erst nach dem Merge der Quelle" hätte am Code nichts geändert. Die reale Abweichung steht als #27 | – |
| 14 | Der news-hub-Deploy ist strukturell nicht an den Build gekoppelt | fehlende Validierung | hoch | **REFUTED** (3b GEKIPPT) | `deploy.yml` ist absichtlich `workflow_dispatch` (Kommentar in der Datei); Run 34765688088 brach mit „Image pull failed for tag ea379be" **vor** jeder Container-Änderung sicher ab; Wiederholung 9 s nach CI-Ende grün | – |
| 15 | Der Canary wurde 17:37Z direkt in die Host-Datei geschrieben und erst 13 h später (news-hub#50) ins Repo gespiegelt | Prozesslücke | mittel | **SURVIVES** (kommandobelegt) | news-hub#46 Nachtrag 17:37 UTC benennt die Lücke selbst; news-hub#50 mergedAt 2026-09-14T06:51:37Z ergänzt `deployment/scripts/tageslauf.sh` | `host-fix-not-mirrored-to-iac` ×7 → ×8 |
| 16 | Zwei CI-Gates feuerten als Fehlalarm und wurden am Text behoben statt per Bypass oder Allowlist unterdrückt | Werkzeug | niedrig | **SURVIVES** (kommandobelegt) | `.gitleaks.toml` in #3141 unverändert; Fix per Commit `04578974` änderte den Testwert; Endstand #3141 alle 16 Checks SUCCESS | – |
| 17 | Commit-Type `style` liegt außerhalb der in `CLAUDE.md` genannten Liste `feat\|fix\|refactor\|docs\|test\|chore` | Konventionsverstoß | niedrig | **SURVIVES** (kommandobelegt; 3b BESTAETIGT, schwach) | Commit `d23b4823` auf `origin/main`. 3b: 15 `style(`-Commits seit Juni auf main, `CORE_CONTEXT.md` legt keine Type-Liste fest — die Konvention selbst ist uneindeutig | – |
| 18 | Fünf von sieben PRs ändern `docs/betrieb/mailcheck.md`; der Platzhalter-Anker vor der PR-Anlage erzwingt je einen Nachzieh-Commit | Prozesslücke | mittel | **SURVIVES** (kommandobelegt) | Dateilisten von #3124/#3126/#3127/#3128/#3132; Commit „docs(mailcheck): Backlog-Anker V7 auf echten PR-Link nachgezogen" in #3128; 17 Commits auf 7 PRs | `same-file-serial-prs` ×12 → ×13 |
| 19 | risk-hub#750 bleibt rot, weil das Staging Gate `minio/minio` anonym von Docker Hub zieht | Werkzeug | hoch | **REFUTED** (3b GEKIPPT) | Commits 07:17Z und 07:25Z „minio vom quay.io-Spiegel", Staging Gate 07:25:41Z grün, gemergt 07:35:55Z — innerhalb der Sitzung behoben | – |
| 20 | Eine zweite, nicht koordinierte PR-Serie (sevdesk/kd-sync) lief im selben Repo und Fenster; `Makefile` wurde von beiden Strängen berührt | Kommunikation | mittel | **SURVIVES** (kommandobelegt) | `gh pr list --repo achimdehnert/platform --search "updated:2026-09-13..2026-09-14"` → 26 PRs, 18 außerhalb des Sitzungs-Scopes; `Makefile` in #3124/#3128 und #3117 | `parallel-session-pr-collision` ×9 → ×10 |
| 21 | 13 Worktrees neben dem Haupt-Tree, zwei als `prunable` markiert und nicht bereinigt | Werkzeug | niedrig | **SURVIVES** (kommandobelegt) | `git -C ~/github/platform worktree list` → u.a. `2026-07-29-handover-teil2`, `fix-2109`, zwei `prunable`-Einträge | `worktree-midsession-accumulation` ×6 → ×7 |
| 22 | `AGENT_HANDOVER.md` endet beim Stand der Parallelsitzung vom 13.09. nachmittags; Abschluss von #3015 und S2-Ausrollung fehlen | Prozesslücke | mittel | **SURVIVES** (kommandobelegt) | `git log origin/main --since='2026-09-13 00:00' -- AGENT_HANDOVER.md` → letzter Commit `c771e273` 14:57Z; Zeile 61 führt #3015 als „Abschluss-Kommentar und Schliessen offen" | `handover-stale-vor-merge` ×20 → ×21 |
| 23 | Sechs von acht platform-PRs ohne jedes Review — die Kontrollinstanz sei auf zwei von acht beschränkt | unklare Steuerung | niedrig | **REFUTED** (Phase 3) | `gh api repos/achimdehnert/platform/rules/branches/main` → `required_approving_review_count: 0` und vier Required Status Checks, die auf 8/8 PRs liefen | – |
| 24 | „Das Anker-Gate feuerte auf vier PR-Texte" bzw. „nur auf einen PR mit zwei Fehlläufen" | fehlende Validierung | niedrig | **REFUTED** (Phase 3, beide Fassungen) | `gh api .../actions/workflows/331379658/runs --paginate` (1229 Läufe, ohne Default-Limit) — beide Zahlen fallen der 20-Läufe-Default-Falle zum Opfer | – |
| 25 | Das Aufschub-Anker-Gate erzwang 18 Fehlläufe auf fünf von acht PRs; mindestens ein geprüfter Treffer war ein Fehlalarm auf einen Design-Kommentar | Werkzeug | mittel | **SURVIVES** (Phase 3, aus dem Konflikt-Task) | #3124 ×5, #3125 ×3, #3126 ×2, #3128 ×5, #3141 ×3; Run 34773690680 flaggte „`ValueError` … wird bewusst NICHT geschluckt" als unverankerten Aufschub | `melder-ohne-praezisionsmass` ×0 → ×1 |
| 26 | Die dokumentierte Reihenfolge „erst alle Leser tolerant, dann die Dateien" wurde nicht eingehalten: 25 Dateien wurden umgestellt, bevor ein toleranter Leser existierte | verfrühte Festlegung | mittel | **SURVIVES** (3b GEKIPPT den Scorecard-Anker) | #3129-Kommentar 2026-09-13T15:32:56Z „25 Dateien umgestellt" — der erste tolerante Leser (#3141) entstand 18:08Z; abgesichert nur durch „Dateien ohne Verbraucher, der den nackten Wert liest", also genau die Inventur, die #11 als lückenhaft belegt | – |
| 27 | Die fünf gemergten Leser-Kopien lesen einen nackten base64-Wert (`…==`) als Name plus Wert `=`, aus `…=` wird ein leerer String; im Mehrwert-Fall gibt es vier Semantiken. Keine gemeinsame Konformitäts-Fixture | fehlende Validierung | hoch | **SURVIVES** (3b NEU) | `origin/main:infra/lib/secrets.py` behandelt `ABC==` ausdrücklich als nackten Wert, `test_secret_lesen.py:64` testet es; Probe mit synthetischen Werten gegen dev-hub#353, writing-hub#1137, music-lab#58 → `=` bzw. leer; illustration-hub#352 und illustration-fw#33 mit identischem Regex. Getrackt: [#3155](https://github.com/achimdehnert/platform/issues/3155) | `test-asserts-the-case-in-mind-not-the-harmful-one` ×6 → ×7 |

## 3. Scorecard

| Dimension | Wert | Verankert an |
|---|---|---|
| zielerreichung | 3 | Zehn Verbesserungen gebaut und gemergt, Stufe 2 in acht von neun Repos — aber #3015 wurde mit einem nicht erfüllten Kriterium K3 geschlossen (#4). |
| architektur_design | 2 | Die platform-Quelle ist sorgfältig (Mehrwert-Fall, base64-Auffüllung, Gegenprobe gegen die alte Implementierung). Im Fleet ist daraus kein gemeinsamer Leser geworden, sondern fünf unabhängige Kopien mit einem stillen Fehler (#27); die eigene Stufenfolge wurde umgekehrt (#26). |
| code_konventionstreue | 3 | Keine Personendaten oder Klartext-Secrets, Fixtures synthetisch, Testnamen `test_should_*`. Die Kopien behaupten in Docstrings, `bare` ändere sich nicht, und testen den Fall nicht, der es widerlegt (#27); ein `style`-Commit (#17). |
| risiko_debt | 2 | Stiller Lesefehler in fünf gemergten Repos (#27), ein offengelegter gültiger Schlüssel über das Sitzungsende hinaus (#10), 25 vor den Lesern umgestellte Dateien mit ungeprüfter Betroffenheit (#26). |
| prozess_effizienz | 3 | 18 erzwungene Gate-Fehlläufe, davon mindestens einer ein Fehlalarm (#25), fünf PRs auf derselben Datei mit je einem Nachzieh-Commit (#18). Gegenläufig: der Deploy-Fehlschlag brach sicher ab (#14 verworfen), die Fremd-CI wurde in der Sitzung repariert (#19 verworfen). |
| entscheidungsqualitaet | 2 | Zwei Entscheidungen widersprechen den schriftlichen Kriterien der Sitzung selbst: K3 als erreicht verbucht (#4), Dateien vor den Lesern umgestellt (#26). Owner-Gates und Freigabe-Vermerke wurden dagegen durchgängig eingehalten (#23 verworfen, §5b). |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Der Abschluss nennt fünf Reste, zwei offene Backlog-Punkte fehlen | Vor dem Schließen eines Auftrags-Issues alle in seinem Body verlinkten Folge-Issues einmal auf `state` abfragen und jedes offene in den Abschluss-Kommentar übernehmen | #3 |
| K3 als erreicht verbucht, die eigene Betriebsakte führt die Signale als „Soll" | Vor „Kriterium erreicht" den vollen Kriterien-Wortlaut Satzteil für Satzteil gegen das Artefakt halten und die eigene Betriebsakte als Gegenprobe lesen; ein Satzteil ohne Beleg heißt „offen", nicht „erreicht" | #4 |
| Freigabe-Issues bleiben nach dem Merge offen | Das Merge-Werkzeug schließt das zugehörige Freigabe-Issue im selben Lauf mit Verweis auf den Merge-Commit | #8 |
| Freigabe-Vermerk mal im Zielrepo, mal nur zentral | Vermerk immer im Zielrepo, zentral nur als Sammelverweis — und im Merge-Werkzeug erzwingen | #9 |
| Offengelegter, gültiger Schlüssel bleibt über das Sitzungsende | Ein Leck mit noch gültigem Wert erzeugt sofort ein eigenes Security-Issue mit Frist; der Sitzungsabschluss nennt es als Erstes statt als einen Rest unter fünf | #10 |
| Der Melder scannt vier Wurzelverzeichnisse, `.github/scripts` fällt durch | Der Melder scannt den ganzen Baum mit Ausschlussliste; eine Positivkontrolle legt einen Roh-Leser außerhalb der bisherigen Wurzeln ab | #11 |
| Canary 13 h nur auf dem Host | Ein Host-Eingriff wird im selben Zug als PR im Repo-Spiegel geöffnet, bevor der nächste Arbeitsschritt beginnt | #15 |
| Gitleaks-Fehlalarm kostete zwei CI-Zyklen | Testwerte, die wie Schlüssel aussehen, von Anfang an unter der Entropie-Schwelle halten statt sie nachträglich zu kürzen | #16 |
| `style(...)`-Commit, die Type-Liste steht nur in `CLAUDE.md` | Die erlaubte Type-Liste an einer Stelle (`CORE_CONTEXT.md` §Konventionen) festlegen — erst dann ist ein Verstoß prüfbar | #17 |
| Fünf PRs schreiben in dieselbe Backlog-Tabelle, je mit Nachzieh-Commit | Die Backlog-Zeilen aller geplanten PRs in einer vorgezogenen PR anlegen; die Inhalts-PRs füllen nur ihre eigene Zeile | #18 |
| Zwei PR-Serien im selben Repo und Fenster ohne Koordinationsmarke | Beim Anlegen eines PRs die offenen PRs des Tages mit überlappenden Pfaden ausgeben und im PR-Text als bekannt vermerken | #20 |
| 13 Worktrees, zwei prunable | `git worktree prune` plus eine Altersgrenze als fester Schritt des Sitzungsendes | #21 |
| Handover endet beim Stand der Parallelsitzung | Der Handover-Nachtrag ist der letzte Schritt vor dem Sitzungsende, nicht der letzte Schritt eines abgeschlossenen Arbeitsstrangs | #22 |
| Gate flaggt einen Design-Kommentar als Vertagung, 18 Fehlläufe | Jeder Treffer des Gates wird als echt oder Fehlalarm protokolliert; ab einer Fehlalarmquote über einem Drittel wird die Regel nachgeschärft | #25 |
| 25 Dateien vor dem ersten toleranten Leser umgestellt | Eine Stufe, deren Sicherheit an einer Inventur hängt, startet erst, wenn die Vorstufe gemergt ist — oder die Abweichung wird mit Owner-Wort als Ausnahme im Auftrags-Issue vermerkt | #26 |
| Neun Leser-Implementierungen nach Prosa, stiller base64-Fehler in fünf | Eine Konformitäts-Fixture (Eingabe → erwarteter Wert) liegt zentral, bevor der erste Fleet-PR entsteht; jede Implementierung lädt sie im eigenen Test | #27 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 121 Reports, Zähler nach dieser Retro:

| Slug | Zähler | Konsequenz |
|---|---|---|
| `claim-before-cheapest-check` | ×81 → ×82 | GATE besteht (blocking, Rev 7) — Rückfall, s. §5a |
| `handover-stale-vor-merge` | ×20 → ×21 | GATE besteht (process, revised 2026-09-07) |
| `partial-fix-not-generalized-to-sibling-artifacts` | ×13 → ×14 | **kein Registry-Gate** — GATE-PFLICHT offen |
| `same-file-serial-prs` | ×12 → ×13 | GATE besteht unter `serielle-prs-auf-derselben-datei` (advisory); der Umbau aus Retro 2026-09-10 (M10) ist noch offen |
| `parallel-session-pr-collision` | ×9 → ×10 | GATE besteht (process); Umbau aus Retro 2026-09-10 (M8) noch offen |
| `host-fix-not-mirrored-to-iac` | ×7 → ×8 | **kein Registry-Gate** — GATE-PFLICHT offen; die Lücke wurde in der Sitzung selbst erkannt, der Spiegel kam 13 h später |
| `worktree-midsession-accumulation` | ×6 → ×7 | GATE besteht (process) |
| `test-asserts-the-case-in-mind-not-the-harmful-one` | ×6 → ×7 | **kein Registry-Gate** — GATE-PFLICHT offen; Kandidat `fleet-implementierung-ohne-konformitaets-fixture` |
| `secret-leak-via-safe-pattern` | ×3 → ×4 | GATE besteht (blocking) — sieht Sourcing nicht, s. §5a |
| `issue-offen-nach-gemergtem-fix` | ×0 → ×1 | GATE registriert (advisory, `unerprobt`). Dieselbe Klasse steht unter dem älteren Slug `issue-open-after-its-fix-merged` ×3 im Längsschnitt — hier bewusst der Registry-Slug, damit `gate_wirkung.py` das Vorkommen sieht |
| `melder-ohne-praezisionsmass` | ×0 → ×1 | GATE registriert (advisory, `unerprobt`) — erstes gemessenes Vorkommen |

Gegen die Memory-Lane geprüft: die beiden heute entstandenen Regel-Dateien
`feedback_schluesseldatei_ohne_name_form_sourcing_fuehrt_wert_aus.md` und
`feedback_deploy_erst_nach_gruenem_build_des_merge_commits.md` existieren im Lane-Verzeichnis und
decken Befund #10 bzw. den verworfenen #14.

### 5a. Rückfall-Prüfung (`python3 tools/gate_wirkung.py`, 121 Reports: 3 RUECKFAELLIG, 4 gefangen, 7 zu-frueh)

Entschieden in Phase 0.0, vor der Befund-Suche:

| Gate | Rückfälle seit Bau/Revision | Ursache | Konsequenz |
|---|---|---|---|
| `ci-gate-maskiert-failure` (blocking, revised 2026-08-20) | 2, letzter 2026-09-10 | **Quelle:** `tools/check_silent_failures.py` verlangt für `continue-on-error: true` nur einen erklärenden Kommentar darüber und fragt nie, ob der maskierte Schritt das Urteil eines Gates trägt. `.github/workflows/handover-append-only.yml:101` (origin/main) trägt genau diese Kombination, der Lint meldet trotzdem „73 Workflow(s) geprüft — kein stiller Fehlschlag" | **ausweiten** — Kandidat, kein Eintrag: `tools/gate_verankerung_check.py --neu` verlangt für die Revision eine neue Positivkontrolle, die es noch nicht gibt (M4) |
| `claim-before-cheapest-check` (blocking, revised 2026-09-08, Rev 7) | 2, letzter 2026-09-10; mit #4 dieser Retro ein dritter | **Quelle:** die zwei früheren Rückfälle saßen in Trägern, die kein Hook liest (Subagenten-Prompt, lokaler Report-Entwurf). #4 ist anders gelagert: die Aussage „erreicht und belegt" stand in einem Issue-Kommentar, also einem Träger, den das Gate sieht — belegt war sie durch Artefakt-Links, die aber nur einen Teil des Kriteriums trugen | **ausweiten** — Kandidat, kein Eintrag (Positivkontrolle fehlt): ein Kriteriums-Claim gilt erst als belegt, wenn jeder Satzteil des Kriteriums einen Beleg hat (M5) |
| `deferred-item-no-tracking-issue` (advisory, revised 2026-09-03) | 2, letzter 2026-09-10 | **Ausgang:** der Scanner ist laut eigener `revision_note` „nicht mehr die Hauptantwort"; dieselbe Wirkung erzwingen `aufschub-anker` (blocking, revised 2026-09-10) und `zusage-ohne-verankerung` (advisory, Klasse `vertagung`) | **Sunset** — Streichkandidat, s. `## Streichbahn` (M12) |

**Zweiter Lauf mit diesem Report im Bestand (122 Reports): 5 RUECKFAELLIG.** Zwei Gates kippen durch diese Retro neu in den Rückfall und werden hier behandelt, nicht als Slug zum N-ten Mal geführt:

| Gate | Rückfälle seit Bau/Revision | Ursache | Konsequenz |
|---|---|---|---|
| `handover-stale-vor-merge` (process, revised 2026-09-07) | 2, letzter 2026-09-14 (#22) | **Quelle:** das Gate prüft die Frische, wenn ein PR `AGENT_HANDOVER.md` berührt. Hier berührte ihn am Sitzungsende gar keiner — der letzte Handover-PR kam von der Parallelsitzung (`c771e273`, 14:57Z am Vortag). Ein Gate, das am Handover-PR hängt, sieht die Sitzung ohne Handover-PR nicht | **umbauen** — Kandidat, kein Eintrag: die Prüfung gehört an das Sitzungsende (Abschluss eines Auftrags-Issues oder `repo-session end`), nicht an den PR, der fehlt (M11) |
| `worktree-midsession-accumulation` (process, revised 2026-09-07) | 2, letzter 2026-09-14 (#21) | **Ausgang:** `git worktree list` zeigt die Einträge, zwei tragen sogar das Git-eigene Etikett `prunable` — gehandelt hat niemand. Einschränkung: die meisten der 13 Worktrees stammen aus anderen Sitzungen | **umbauen** — Kandidat, kein Eintrag: `git worktree prune` plus Altersgrenze als erzwungener Schritt des Sitzungsendes statt einer Anzeige (M11) |

`claim-before-cheapest-check` steht im zweiten Lauf bei 3 Rückfällen nach Rev 7, `secret-leak-via-safe-pattern` bei 1 (`beobachten`).

Ehrlichkeits-Sperre: die sieben Gates mit Urteil `zu-frueh` sind ungeprüft, nicht wirksam, und werden nicht als Erfolg geführt.

**Neu für die nächste Bilanz:** `secret-leak-via-safe-pattern` (blocking, bisher `wirksam`) bekommt mit #10 sein erstes Vorkommen nach dem Bau. Ursache an der Quelle: der Guard prüft Kommando-**Argumente** (`cat`/`head`/`tail`/`grep` mit einer Secret-Datei); Sourcing (`. datei`) hat kein Argument, das er sehen könnte. Konsequenz **ausweiten** (M6). Nebenbeobachtung aus dieser Retro: derselbe Guard blockierte beim Anlegen von #3155 einen Issue-Text, der ein Suchkommando über das Secret-Verzeichnis nur **zitierte** — er arbeitet am Kommandotext, nicht an der Ausführung.

### 5b. Autonomie-Kalibrierung

`python3 tools/retro_kpis.py --nominierung`: 39 von 121 Retros tragen Kalibrierungsfelder, `over_ask` Σ=6, `over_act` Σ=19; einzige bisher benannte Klasse `docs-pr-anlage-freigabe` ×1.

- **`over_act` = 0.** Für jeden Gate-pflichtigen Schritt liegt ein Freigabe-Vermerk im Artefakt: news-hub#46 trägt „Freigabe: akzeptiert durch Owner — deploy #47/#48/#49" mit Wortlaut und Kanal, der Host-Eingriff das Owner-Wort „H1 go", der Fleet-Rollout je Repo eine Zeile und im #3129-Body die Sammelfreigabe. mcp-hub#265 blieb blockiert, weil das Ruleset Owner-Review verlangt — ein Bypass wurde nicht gesucht. Klassen-Slugs: keine.
- **`over_ask` = 0, mit benannter Lücke.** Aus Artefakten allein nicht messbar: `over_ask` lebt im Chat-Kanal. Die einzige im Artefakt sichtbare Rückfrage (news-hub#49, NIS2-Typzuordnung) ist eine inhaltliche Owner-Entscheidung. Klassen-Slugs: keine.

Keine Klasse erreicht ≥2 — keine NOMINIERUNG.

## 6. Verankerung

**`memory_candidates`** (kopierfertig, Aufnahme entscheidet der Owner):

1. `feedback_fleet_implementierung_braucht_konformitaets_fixture.md` — *Wird dieselbe kleine Funktion in mehreren Repos gebaut, entsteht sie nicht als Kopie, sondern nach einer Beschreibung — und jede Fassung weicht in einem anderen Randfall ab. Am 2026-09-13 entstanden neun Secret-Leser zwischen 17:48Z und 17:59Z, vor der Quelle platform#3141; fünf davon lesen `Abc123xyz==` als Name plus Wert `=` (platform#3155), die Quelle nicht. How to apply: vor dem ersten Fleet-PR eine Konformitäts-Fixture (Eingabe → erwarteter Wert, inklusive der Randfälle der Quelle) zentral ablegen; jede Implementierung lädt sie im eigenen Test.* `drift: true`, `drift_episode: 2026-09-13-secret-leser-ohne-fixture`
2. `feedback_kriterium_erreicht_gegen_eigene_betriebsakte.md` — *„Erreicht und belegt" trägt nur so weit wie der kürzeste belegte Satzteil des Kriteriums. #3015 K3 verlangte Verfallsignale mit Schwelle und Vorlauf und eine künstliche Positivkontrolle mit Journal-Beleg; geschlossen wurde mit Meldern ohne Vorlauf und einer echten, nicht protokollierten Kontrolle — während die eigene Betriebsakte die Signale als „Soll" führte. How to apply: vor dem Abschluss den Kriterien-Wortlaut Satzteil für Satzteil gegen die Belege halten und die eigene Akte als Gegenprobe lesen.* `drift: true`, `drift_episode: 2026-09-14-k3-gegen-betriebsakte`
3. `feedback_stufenplan_reihenfolge_ist_sicherheitsannahme.md` — *Eine dokumentierte Stufenfolge („erst Leser, dann Dateien") ist eine Sicherheitsannahme, keine Planungsnotiz. Am 2026-09-13 wurden 25 Dateien umgestellt, bevor ein toleranter Leser existierte, abgesichert nur durch eine Inventur, die sich später als lückenhaft erwies. How to apply: eine Stufe vorziehen nur mit ausdrücklichem Owner-Wort und Vermerk im Auftrags-Issue.*
4. Index-Zeilen für die zwei heute entstandenen Lane-Dateien in `MEMORY.md` nachtragen.

**`adr_candidates`:** keiner. Alle Befunde sind Ergänzungen nach bestehendem Muster; nach `policies/adr-threshold.md` genügen PR und CHANGELOG.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Groq-Schlüssel rotieren, verteilen | news-hub | #46 | 🟢 du | du: Z1/Z2 ausführen |
| M2 | Konformitäts-Fixture, fünf Kopien fixen | 7 Repos | #3155 | 🔵 ich | ich: Fixture zuerst |
| M3 | Betroffenheit base64-Dateien prüfen | lokal | #3155 | 🟢 du | du: nur Dateinamen |
| M4 | Gate maskierte Fehlschläge ausweiten | platform | Registry | 🟢 du | du: Konsequenz bestätigen |
| M5 | Gate Kriteriums-Claim ausweiten | platform | Registry | 🟢 du | du: Konsequenz bestätigen |
| M6 | Secret-Guard auf Sourcing ausweiten | platform | #3129 | 🟢 du | du: Konsequenz bestätigen |
| M7 | #3015 K3 nachweisen oder öffnen | platform | #3015 | 🟢 du | du: entscheiden |
| M8 | Stufe-0-Dateien gegen Roh-Leser | lokal | #3129 | 🟢 du | du: Namensabgleich |
| M9 | Melder-Scope auf ganzen Baum | platform | #3129 | 🔵 ich | ich: mit Positivkontrolle |
| M10 | Fünf Freigabe-Issues schließen | 5 Repos | #3129 | 🔵 ich | ich: je ein Kommentar |
| M11 | Handover und Worktrees nachziehen | platform | #3149 | 🔵 ich | ich: Sitzungsende-Schritt |
| M12 | Sunset deferred-item-Scanner | platform | Registry | 🟢 du | du: bestätigen |

M2 zuerst: solange die Kopien den base64-Fall falsch lesen, ist jede weitere Datei-Umstellung in den
betroffenen Repos riskant. M4 und M12 stammen nicht aus einem Befund dieser Sitzung, sondern aus der
Wirkungsbilanz in Phase 0.0 (§5a) — sie behandeln Rückfälle, die vor dieser Sitzung verbucht wurden.
M4, M5 und M12 sind Registry-Änderungen; sie laufen erst nach Owner-Wort
durch `tools/gate_verankerung_check.py --neu` und brauchen je eine Positivkontrolle. Bis dahin ist
dieser Report ihr Tracking-Artefakt.

## 8. Nicht verifiziert (Restlücken)

- **getan:** 27 Befunde aus drei unabhängigen Findern; vier in Phase 3 verworfen (einer davon von der Widerlegungsbahn wieder eingesetzt), einer schon davor; die Widerlegungsbahn verwarf sieben weitere Befunde (#5, #6, #7, #12, #13, #14, #19 — sie zählt #6 und #19 als einen Punkt), setzte #4 wieder ein, kippte einen Scorecard-Anker und fand einen neuen Befund. `phase3_refuted: 10` fasst beide unabhängigen Falsifikationsbahnen zusammen: 3 aus Phase 3, 7 aus Phase 3b. Alle Belege aus `origin/main` bzw. `gh api` nach `git fetch`.
- **angenommen:** Die vorgegebene Sitzungsgrenze 2026-09-14 07:00 UTC ist zu früh — die Artefakte der Sitzung reichen bis mindestens 07:41Z (#3141 gemergt 07:09Z, risk-hub#750 07:35Z, erster #3149-Kommentar 07:41Z). Der Report-Entwurf verwendete Belege bis 07:16Z; drei Befunde (#6, #7, #19) kippten genau an dieser Lücke.
- **nicht verifizierbar:** Ob die Host-Positivkontrolle für K3 (Canary-Abbruch 2026-09-13 17:36 UTC) so stattfand — sie hat kein Repo-Artefakt. Billigster Check: das Journal des Tageslauf-Dienstes auf dem Prod-Host für diesen Zeitraum.
- **nicht verifizierbar:** Ob unter den bare-Dateien welche mit base64-Auffüllung sind (#27) und ob die 25 Stufe-0-Dateien einen Roh-Leser hatten (#26) — beides braucht einen lokalen Blick ins Secret-Verzeichnis, der Ermittlern verboten ist. Billigster Check: der Owner lässt sich nur Dateinamen ausgeben (M3, M8).
- **nicht verifizierbar:** `over_ask` — lebt im Chat-Kanal. Billigster Check: Transkript-Suche nach `AskUserQuestion` im Sitzungsfenster.
- **nicht verifizierbar:** Ob der Evidence-Scanner beim Absenden des #3015-Abschlusskommentars gefeuert hat (§5a). Billigster Check: `gate_hits`-Protokoll für 2026-09-14 07:06Z.
- **offen geblieben:** Warum das Aufschub-Anker-Gate auf #3124 und #3128 je fünfmal rot wurde — geprüft wurde nur ein Fehlschlag auf #3141. Billigster Check: `gh run view <id> --log-failed` für je einen Lauf.
- **offen geblieben:** Ob weitere Fleet-Repos einen Roh-Leser tragen und keinen Stufe-2-PR bekamen. Die Code-Suche trägt nicht, weil `read_text().strip()` zu generisch ist.

## Widerlegung

Ein Opus-Subagent in frischem Kontext, der nur den Report-Entwurf, den Footprint und die Artefaktliste
sah, hatte den Auftrag, das Urteil zu widerlegen. Ergebnis: **8 gekippt, 1 neu.**

| Punkt | Verdikt | Wirkung auf den Report |
|---|---|---|
| #4 | GEKIPPT | Verwerfung zurückgenommen — der Skeptiker hatte K3 nur zur Hälfte zitiert; #4 steht jetzt als SURVIVES `hoch` |
| #13 | GEKIPPT | Ursache falsch: kein Kopieren vor der Quelle, sondern unabhängige Implementierungen vor ihr; die reale Abweichung wandert nach #27, Gate- und Memory-Kandidat umgeschrieben |
| #14 | GEKIPPT | Deploy brach sicher vor jeder Container-Änderung ab; die Maßnahme „Image-Prüfung" beschrieb das heutige Verhalten und ist gestrichen |
| #6, #19 | GEKIPPT | risk-hub#750 wurde in der Sitzung repariert und gemergt; die Belege des Entwurfs endeten 20 Minuten zu früh |
| #12 | GEKIPPT | ein getrackter Split, keine drei unabhängigen Fälle; #11 war doppelt gezählt |
| #7 | GEKIPPT | „CI läuft" stimmte — der rote Lauf war ein anderer Workflow; der Zähler `claim-before-cheapest-check` hängt jetzt an #4 |
| #5 | GEKIPPT | der Scope stand mit Owner-Wort im bearbeiteten Issue-Body; der Entwurf hatte nur Kommentare durchsucht und damit Wortlaut gegen Substanz gestellt — dieselbe Asymmetrie, die er bei #4 zugunsten der Sitzung gelten ließ |
| Scorecard `architektur_design` | GEKIPPT | die Stufenfolge wurde nicht eingehalten; steht jetzt als #26, der Score fällt von 3 auf 2 |
| #1, #8, #10, #11, #17 | BESTAETIGT | mit Korrekturen an Zahlen und Zuordnung, in die Beleg-Spalte übernommen |
| base64-Lesefehler | NEU | #27, getrackt in #3155 |

Abdeckung der Widerlegungsbahn: angegriffen #1, #4–#8, #10–#14, #17, #19 sowie Executive Summary und
Scorecard; nicht angegriffen #2, #3, #9, #15, #16, #18, #20–#25, §5 und die Streichbahn.

Die zwei stärksten Lehren daraus betreffen die Retro selbst, nicht die Sitzung: ein Skeptiker, der
ein Kriterium verkürzt zitiert, verwirft einen wahren Befund; und eine Belegsammlung, die an einer
vorgegebenen Uhrzeit endet, bewertet eine Sitzung, die länger lief.

## Self-Review

Separater Sonnet-Meta-Agent, der nur diesen Report und die Skill sah. Ergebnis: **keine Pflicht-Mängel**,
alle zwölf Prüfpunkte ok.

| Check | Ergebnis |
|---|---|
| Belege | fünf Stichproben nachgezogen (#2, #3, #17, #19, #23), alle zeigen, was die Beleg-Spalte sagt |
| Längsschnitt | alle elf `recurring_findings`-Zähler stimmen mit `retro_kpis.py` überein |
| Scores | ganzzahlig, alle an SURVIVES-Befunden verankert |
| Invariante | 16 SURVIVES = 16 Soll-Schritte, 1:1 |
| Frontmatter | `27 = 16 + 10 + 1`, `refuted_rate` 0,41 exakt, Pfad kollisionsfrei |
| `gate_wirkung.py` | Lauf ohne diesen Report: 3 RUECKFAELLIG (wortgleich §5a); mit: 5, beide neuen in §5a behandelt |
| `refuted_rate` | echte Falsifikationsquote `10/26 = 0,38` — gesundes Band |
| Öffentliches Repo | keine Secrets, Fragmente, Personennamen oder Betreffe |

Zwei Hinweise ohne Pflicht, beide übernommen: M4 und M12 sind jetzt als Herkunft Phase 0.0 statt
Soll-Ablauf gekennzeichnet (§7), und die Zusammensetzung von `phase3_refuted` steht in §8. Offen als
Beobachtung: diese Retro und die vom 2026-09-10 tragen dieselbe Kurz-ID `oqu6Z6`, weil es dieselbe lange
Sitzung ist — in `retro_kpis.py` erscheint sie deshalb doppelt, inhaltlich korrekt.

## Streichbahn

**Streichkandidat: `deferred-item-no-tracking-issue`** — Belegart **kein Effekt**.

Der Melder (`tools/claude-hooks/deferred_item_scanner.py`, advisory, gebaut 2026-08-02) erzwingt
keine Wirkung, die nicht ohnehin erzwungen wird. Zwei Registry-Einträge decken dieselbe Klasse:
`aufschub-anker` (blocking, `tools/deferral_anchor_check.py`, revised 2026-09-10, Positivkontrolle
`test_should_flag_a_deferral_in_an_issue_comment_without_an_anchor`) und `zusage-ohne-verankerung`
(advisory, `tools/verankerung_pruefer.py`, Klasse `vertagung`). Die `revision_note` des Kandidaten
sagt es selbst: „Dieser Scanner läuft advisory weiter …, ist aber nicht mehr die Hauptantwort." Sein
`expires` steht auf 2026-10-31 mit der Auflage „blocking oder gestrichen"; blocking ist er nie
geworden. In dieser Sitzung setzte `aufschub-anker` die Klasse achtzehnmal blockierend durch (#25).

Entscheidung beim Owner (M12): Eintrag streichen und in `declined` begründen. Die Ratsche greift noch
nicht — erstes Auftreten des Kandidaten.
