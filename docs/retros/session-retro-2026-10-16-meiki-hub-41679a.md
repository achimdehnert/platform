---
retro_schema: 1
date: 2026-10-16
repo_scope: [meiki-hub, iil-assist-core, post-hub, schreib-hub, frist-hub, buerger-hub]
session_id: 41679a
footprint: full
footprint_reduction_reason: "deep ausgelöst durch 6 Repos und einen PyPI-Publish; reduziert auf full, weil der Publish per Owner-Skript freigegeben war, alles per Revert-PR bzw. PyPI-Yank umkehrbar ist, keine Migration und kein Prod-Schritt lief und die Finder 10 Befunde lieferten."
findings_total: 11
findings_survived: 4
refuted_rate: 0.64
phase3_refuted: 7
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [pypi-index-verzug-host-ci-rot]
recurring_findings: [pypi-index-verzug-host-ci-rot, edit-in-worktree-without-read, claim-before-cheapest-check, repo-datei-per-bash-statt-edit, aufschub-anker]
gates_caught: [inline-heredoc-quoting-rework, claim-before-cheapest-check]
gates_verwandt: [aufschub-anker]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede teure Bahn dieser Retro das Ergebnis geändert hat: Phase 2.5 löste einen Faktenwiderspruch, Phase 3 verwarf acht Bewertungsbefunde, Phase 3b kippte zwei Urteile und brachte einen neuen Befund."
---

# Session-Retro 41679a — `/healthz/` aus dem Kern in allen vier Assists (meiki-hub, Kern, vier Hosts)

Sitzung `c71be7ee-6d37-4130-a656-47611d41679a`, 2026-10-16 10:17Z bis 15:25Z. Auftrag (Owner):
„mach weiter, wo wir aufgehört haben" — Zielanker
[meiki-hub#639](https://github.com/meiki-lra/meiki-hub/issues/639) mit vier Kriterien
(Kern-View, Kern-Tests, vier Hosts, Messung im getrennten Prod-Compose), Teil von K5 in
[meiki-hub#621](https://github.com/meiki-lra/meiki-hub/issues/621). Sitzungsgrenze: Branches
`session/2026-10-16/achim-dehnert/healthz-639` und `…/handover-639`. Sechs PRs in sechs Repos,
alle gemergt: [iil-assist-core#86](https://github.com/iilgmbh/iil-assist-core/pull/86) (Release
0.16.11 per Owner-Skript), [post-hub#136](https://github.com/meiki-lra/post-hub/pull/136),
[schreib-hub#116](https://github.com/meiki-lra/schreib-hub/pull/116),
[frist-hub#250](https://github.com/meiki-lra/frist-hub/pull/250),
[buerger-hub#28](https://github.com/meiki-lra/buerger-hub/pull/28),
[meiki-hub#640](https://github.com/meiki-lra/meiki-hub/pull/640) (Übergabe). Nicht im Scope:
meiki-hub#638, #637, #636, buerger-hub#27 (andere Sitzungen). Scope-Grundlage: Owner-Zeile
`scope +post-hub +schreib-hub +frist-hub +buerger-hub +iil-assist-core` in #621 (13.10.).

## Phase 0.0 — Wirkungsbilanz

Die vier `RUECKFAELLIG`-Gates aus `tools/gate_wirkung.py` sind in der Retro desselben Tages
entschieden — Link statt Neuverhandlung:
[session-retro-2026-10-16-platform-d9f597 §0.0](session-retro-2026-10-16-platform-d9f597.md#phase-00--wirkungsbilanz).

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 7 | Quelle | nachschärfen — beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666)); in dieser Sitzung gefangen, kein neuer Rückfall (Befund 3) |
| check-ohne-positivkontrolle | 4 | Quelle | nachschärfen — beschlossen (Rev 2, [#3722](https://github.com/achimdehnert/platform/issues/3722)); kein neuer Fall |
| built-but-never-called | 3 | Quelle | ausweiten — beschlossen (Owner „187 go"); kein neuer Fall |
| edit-in-worktree-without-read | 2 (ohne diese Retro), 3 mit | Quelle | ausweiten — beschlossen ([#3906](https://github.com/achimdehnert/platform/issues/3906)); Befunde 3 und 11 sind ein neuer Rückfall mit Ursache am Ausgang ⇒ zusätzlich umbauen, §5a |

## 1. Executive Summary

- Ziel erreicht: alle vier Kriterien von #639 sind mit PRs, Tests und Messung belegt, das Issue ist mit vollständiger Kriterientabelle geschlossen; K5 in #621 bleibt für Alarmweg und Backup offen.
- Prozessbefund (1): rote Erst-CI-Jobs in drei Hosts und ein zu früher Rerun, weil das Release-Skript nach dem Publish nur die PyPI-JSON-API abfragt. Der Index-Verzug war je Runner verschieden; eine einzelne erfolgreiche pip-Probe reicht deshalb nicht. Die vorhandene Memory beschreibt nur das Symptom. Schaden: rund acht Minuten.
- Gate-Rückfall (3, 11): zwei Edits ohne Read in frischen Worktrees, obwohl `repo-session.sh start` den Read-Batch-Hinweis ausgibt — einmal überlesen, einmal per `grep | head` weggefiltert. Das Werkzeug verweigerte beide Edits, Schaden 0.
- Aufschub ohne Anker (4): der Nebenbefund zur Identitäts-Middleware stand nur im geschlossenen #639; Anker in #567 inzwischen gesetzt.
- Widerlegt: Host-PRs vor dem Upload, schwache Host-Tests, irreführender Mutationsbeleg, Lastrisiko `/healthz/`, Patch statt Minor, Kopplung an das CLI-Modul, Klartext im Messskript.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Erst-CI rot nach dem Release: Job `Security Scan` in post und schreib, Lauf frist (`Unit Tests`, „Could not find a version … kommunalassist-core<0.17,>=0.16.11"); post-Rerun nach 4 min noch rot. `~/zug/rel1611.sh` prüft nach dem Publish nur `pypi.org/pypi/…/json` `info.version` | fehlende Validierung | mittel | SURVIVES | PyPI upload_time 11:14:36Z; Attempt 1 post 11:15:55Z, schreib 11:15:59Z, frist 11:16:04Z; post `Unit Tests` lädt 0.16.11 um 11:16:28, frist scheitert 11:16:29 (Index-Sicht je Runner verschieden); post Run 38892626591 Attempt 2 11:18:54Z rot, Attempt 3 11:24:15Z grün | wiederkehrend: Memory `kern-release-minor-bricht-frist-paket-pin` Z. 23–24 und Outline-Lessons 2026-09-14 nennen den Verzug, nur als Rerun-Hinweis |
| 2 | Host-PRs wurden geöffnet bzw. ihre CI startete, bevor 0.16.11 auf PyPI lag | fehlende Validierung | mittel | REFUTED | Phase-2.5-Konflikt: PR-createdAt 11:15:51Z–11:16:01Z und Attempt-1-Starts liegen rund 80 s nach dem Upload; Ursache ist Index-Verzug, siehe 1 | — |
| 3 | Drei Fehlgriffe vom Werkzeug gefangen: Edit `CHANGELOG.md` im Kern-Worktree „File has not been read yet" (10:50:06), obwohl `repo-session.sh start` um 10:45:17 den Read-Batch-Hinweis zeigte; Shell-Schreibschleife über vier Worktrees blockiert (10:54:41); Evidenz-Hook am Stop (11:03) | Werkzeug | niedrig | SURVIVES | Transkript c71be7ee; Registry `edit-in-worktree-without-read` (erster Fall „frischer Worktree, Zieldateien nur im Haupt-Tree gelesen"), `inline-heredoc-quoting-rework` (covers `repo-datei-per-bash-statt-edit`), `claim-before-cheapest-check` | Rückfall `edit-in-worktree-without-read`; die anderen zwei gefangen (§5a) |
| 4 | Nebenbefund der Messung (Monitor ohne Token erreicht `/healthz/` bei eingeschalteter Identitäts-Middleware, Token ohne Konto 403) nur im geschlossenen #639 und im Handover-Fragment, nicht im offenen [#567](https://github.com/meiki-lra/meiki-hub/issues/567), wo die Entscheidung fällig wird | Prozesslücke | niedrig | SURVIVES | Phase 3 REFUTED, Phase 3b GEKIPPT: #567 enthielt 0 Treffer für `healthz`; Hausregel „Bewusst Ausgelassenes → Issue oder Ledger-Zeile mit Link"; Anker nachgezogen: [#567 Kommentar](https://github.com/meiki-lra/meiki-hub/issues/567#issuecomment-6219057366) | `aufschub-anker` (Längsschnitt §5) |
| 5 | Host-Tests zu `/healthz/` schwach (Statuskopplung tautologisch) und uneinheitlich (Leak-Test nur in buerger, frist ohne `test_health.py`) | fehlende Validierung | niedrig | REFUTED | Host-Tests prüfen Routing auf `gesundheit.readiness` und Schlüsselmenge (frist: `tests/test_smoke.py::test_should_route_healthz_to_core_readiness`), Verhalten testet der Kern; Uneinheitlichkeit stammt aus den Onboarding-Skeletten | — |
| 6 | Close-Kommentar nennt „Mutationsprobe 2 failed" als Beleg für Kriterium 2, obwohl Ausnahmetext nur für `offene_migrationen` getestet ist | Kommunikation | niedrig | REFUTED | `tests/test_gesundheit.py`: Gut-Fall Z. 67, sechs Verdorben-Fälle, Ausnahmetext-Test Z. 140; PR #86 legt den Mutationsumfang offen; DB-Zweig baut ein festes Dict ohne `str(exc)` | — |
| 7 | `/healthz/` führt je Aufruf mehrere DB-Abfragen ohne Cache oder Rate-Limit aus — Last-/DoS-Risiko | verfrühte Festlegung | mittel | REFUTED | Compose-Healthchecks pollen `/livez/`; Katalog-Lookups sind Standard für Readiness; Lastpfad unbelegt (Hypothese: vorgelagerter Proxy nicht eingesehen, §8) | — |
| 8 | Release 0.16.11 als Patch, obwohl `assist_rls --check` strenger prüft | verfrühte Festlegung | niedrig | REFUTED | CHANGELOG „Changed" begründet Patch mit frist-Pin `<0.17`; jeder Host ruft `--check` nur direkt nach `--apply`; Release im Feature-PR hat Vorläufer (#58–#67) | — |
| 9 | `gesundheit.py` importiert aus `management/commands/assist_rls.py` — Laufzeit-API hängt an einem CLI-Modul | Architektur | niedrig | REFUTED | Funktionen öffentlich, Import ohne Seiteneffekte, Teilung gewollt (Docstring „Grundlage für `--check` und `/healthz/`") | — |
| 10 | Messskript `probe639.sh` schreibt Zufallspasswörter ohne `umask 077`, Fehlerpfad gibt Compose-Log aus | Sicherheit | niedrig | REFUTED | Scratchpad `drwx------`, Einmalwerte, `trap` räumt Stapel und Env-Dateien ab | — |
| 11 | Gate-Hinweis weggefiltert: die vier Host-Worktrees starteten um 10:52:48 mit `repo-session.sh start … 2>&1 \| grep -oE '<pfad>' \| head -1`; der Read-Batch-Hinweis erreichte die Sitzung nicht, um 10:54:00 scheiterte der Edit auf `buerger-hub/tests/test_health.py` | Werkzeug | niedrig | SURVIVES | Phase 3b NEU, Transkript c71be7ee 10:52:48 und 10:54:00 | neu; Ursache des Rückfalls in 3 (§5a) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | #4: alle vier Kriterien belegt, ein Aufschub ohne Anker |
| architektur_design | 4 | #9: Schichtungsgeruch ohne Mangel |
| code_konventionstreue | 3 | #3, #11: Gate-Rückfall bei angezeigtem bzw. weggefiltertem Hinweis |
| risiko_debt | 4 | #7, #10: kein Risiko belegt |
| prozess_effizienz | 3 | #1: rote Erst-Jobs in drei Hosts, ein zu früher Rerun |
| entscheidungsqualitaet | 4 | #8: Patch-Entscheid hielt der Widerlegung stand |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `rel1611.sh` wartet auf `info.version` der JSON-API; Host-PRs starten 80 s nach dem Upload, Index-Sicht je Runner verschieden, Rerun nach 4 min noch rot | `publish-pypi.yml` in iil-assist-core bekommt nach `publish` einen Prüfschritt: `pip download kommunalassist-core==<tag> --no-deps --no-cache-dir` muss mehrmals in Folge über mehrere Minuten gelingen; das Release-Skript wartet auf diesen Lauf, erst danach Host-PRs und Reruns | #1 |
| Edit auf `CHANGELOG.md` im frischen Worktree trotz angezeigtem Read-Batch-Hinweis | Direkt nach `repo-session.sh start` die genannten Zieldateien in einem Read-Batch lesen, bevor die erste Edit-Salve läuft | #3 |
| Nebenbefund nur im geschlossenen Ziel-Issue | Aufgeschobene Entscheidung im Issue verankern, in dem sie fällig wird (hier #567), im selben Zug wie der Messkommentar | #4 |
| `repo-session.sh start … \| grep \| head -1` schluckt den Gate-Hinweis | Worktree-Start nie filtern; das Werkzeug schreibt den Read-Batch-Hinweis zusätzlich in eine Zustandsdatei, die der Edit-Hook liest, statt nur auf stdout | #11 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Worktree mit diesem Report): `pypi-index-verzug-host-ci-rot` ist
in den Retros neu (Zähler 1), im Betrieb aber nicht: die Memory
`kern-release-minor-bricht-frist-paket-pin` (Z. 23–24) und die Outline-Lessons vom 2026-09-14
halten denselben Verzug schon fest — als Symptom mit der Anweisung „Rerun", ohne Vorab-Check.
Eine Memory, die den Fall nicht verhindert, ist der Grund, den Slug als `gate_candidates` zu
führen. `aufschub-anker` (×2: df4715, 41679a) ist durch das Gate `aufschub-anker` gedeckt; der
Fall hier liegt außerhalb seines Zuschnitts (5a). `edit-in-worktree-without-read` ×13, gedeckt,
Gate laut `gate_wirkung.py` jetzt mit 3 Rückfällen (5a). Refuted-Band laut `retro_kpis.py`:
gesund.

### 5a. Rückfall-Prüfung

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| Gate edit-in-worktree-without-read rückfällig (advisory) | #3, #11: zwei Edits ohne Read in frischen Worktrees (10:50:06, 10:54:00) | Ausgang: der Hinweis feuerte, wurde einmal überlesen und einmal per Pipe weggefiltert; ein reiner stdout-Hinweis hat keinen Zugriff auf den Edit | **umbauen**: Hinweis als Zustand an den Edit-Hook übergeben (Soll #11). Kandidat, kein Registry-Edit in dieser Retro; Umsetzungsort neben [#3906](https://github.com/achimdehnert/platform/issues/3906) |
| inline-heredoc-quoting-rework (blocking) | #3: Shell-Schreibschleife über vier Worktrees | — | gefangen (`gates_caught`), Beleg für das Gate; Nebenbefund: die Meldung nannte `~/github/meiki-hub/requirements.txt` statt der vier Worktree-Ziele |
| claim-before-cheapest-check (blocking) | #3: Stop-Hook 11:03 | — | gefangen (`gates_caught`) |
| aufschub-anker (advisory, Melder) | #4 | Zuschnitt: das Gate fängt Aufschub-Formulierungen in PR-Text und Issue-Schluss; der Nebenbefund stand als „ohne Handlungsbedarf" in einem Messkommentar, ohne Aufschubwort | `gates_verwandt`, kein Rückfall; die Lücke (Befund als „kein Handlungsbedarf" eingestuft, obwohl die Entscheidung später fällig wird) ist mit Fall-Text kein Gate-Muster |

### 5b. Autonomie-Kalibrierung

- over_act: keine Klasse — Kern-Merge, Tag und PyPI-Publish liefen über `~/zug/rel1611.sh`, Host-Merges über `~/zug/m639.sh`, Übergabe über `~/zug/m640.sh`, jeweils vom Owner ausgeführt. Scope-Zeile für die fünf Repos aus #621 (13.10.).
- over_ask: keine Klasse.

## 6. Verankerung

memory_candidates (der Owner entscheidet, nichts davon ist geschrieben):

Ergänzung an `kern-release-minor-bricht-frist-paket-pin.md`, Zeilen 23–24 ersetzen:

```markdown
PyPI-Index hinkt Minuten nach, je Runner verschieden (JSON-API zeigt die Version früher als
`/simple/`). Vor Host-Push und vor jedem Rerun: `pip download kommunalassist-core==X --no-deps
--no-cache-dir -d <tmp>` mehrmals in Folge über einige Minuten, bis stabil Exit 0 — die
JSON-Probe reicht nicht (16.10.: rote Erst-Jobs in drei Hosts, ein zu früher Rerun, Retro 41679a).
```

Neue Memory `worktree-start-nicht-filtern.md`:

```markdown
---
name: worktree-start-nicht-filtern
description: repo-session.sh start nie per grep/head filtern; der Read-Batch-Hinweis ist Teil der Ausgabe
metadata:
  type: feedback
---
`repo-session.sh start` nie durch `grep`/`head` pipen: der Hinweis „in EINEM Read-Batch lesen"
fällt sonst weg, der erste Edit scheitert (16.10., Retro 41679a Befund 11).
**Why:** Werkzeug-Sparsamkeit darf keinen Gate-Hinweis stummschalten.
**How to apply:** Start ungefiltert, danach die genannten Dateien in einem Read-Batch lesen.
```

adr_candidates: keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Index-Probe im Publish-Workflow | iil-assist-core | Issue anlegen | 🟢 | Owner-Wort, dann Issue + PR |
| M2 | Memory-Zeile Index-Probe | meiki-hub | Memory `kern-release-minor-bricht-frist-paket-pin` | 🟢 | Owner-Wort |
| M3 | Read-Hinweis als Hook-Zustand | platform | [#3906](https://github.com/achimdehnert/platform/issues/3906) | 🟢 | Owner-Wort: mit #3906 bündeln |
| M4 | Memory Worktree-Start ungefiltert | meiki-hub | Memory `worktree-start-nicht-filtern` | 🟢 | Owner-Wort |
| M5 | Anker Nebenbefund in #567 | meiki-hub | [#567](https://github.com/meiki-lra/meiki-hub/issues/567#issuecomment-6219057366) | ✅ | erledigt nach Hausregel „im selben Turn Issue oder Ledger-Zeile", Kommentar im Sitzungs-Repo, löschbar |

## 8. Nicht verifiziert (Restlücken)

- Traceback um 11:04 nach dem Evidenz-Hook (Prozess-Finder P4): Folgen nicht an einen Skeptiker gegeben. Billigster Check: Transkript-Zeile 11:04 lesen und prüfen, ob danach eine Aussage ohne Beleg stehen blieb.
- Ob die geschärfte Index-Probe (mehrere Treffer in Folge) alle roten Jobs verhindert hätte, ist kontrafaktisch; der Verzug war je Runner verschieden. Billigster Check: beim nächsten Release Probe-Dauer und Host-Erstlauf protokollieren.
- Close-Kommentar von #639 erwähnt übersprungene CI-Jobs nicht; Zahl und Art nicht nachgezählt. Billigster Check: `gh run view <run> --json jobs` je main-Lauf.
- `up639.log` liegt im Scratchpad und wird vom `trap` nicht gelöscht; ob er im Fehlerfall eine `DATABASE_URL` trägt, ist offen (Hypothese: nein, Einmalwerte). Billigster Check: `grep -c postgres:// up639.log`.
- Befunde 7, 9, 10 hat Phase 3b nicht erneut geprüft. Zu 7: Rate-Begrenzung am vorgelagerten Proxy nicht eingesehen. Billigster Check: Proxy-Konfiguration des Pilot-Hosts auf `/healthz/` greppen.

## Widerlegung

Phase 3b (Opus, frischer Kontext, nur Report-Entwurf, Footprint und Artefaktliste):

| Befund | Ergebnis | Verdikt | Beleg |
|---|---|---|---|
| 1 | hält, mit zwei Korrekturen: post und schreib hatten nur einen roten Job, kein roter Lauf; Index-Sicht je Runner verschieden, eine einzelne pip-Probe hätte 11:16:29 nicht verhindert | BESTAETIGT | Job-Logs: post lädt 11:16:28, frist scheitert 11:16:29 |
| 3 | Befund hält, die Zuordnung `gates_verwandt` nicht: der Fall ist der erste Eintrag im `faengt`-Katalog des Gates, der Hinweis war angezeigt | GEKIPPT (§5a-Zeile) | `repo-session.sh start` 10:45:17 mit Hinweis, Edit-Fehler 10:50:06 im selben Worktree |
| 4 | zu früh verworfen: #567 ohne `healthz`, Entscheidung dort fällig | GEKIPPT | `gh issue view 567 --comments`: 0 Treffer |
| 2, 5, 6, 8 | halten | — | PyPI-JSON, `test_smoke.py`, `test_gesundheit.py` Z. 140, Release-Historie #58–#85 |
| 11 | gedämpfter Gate-Hinweis per Pipe | NEU | Transkript 10:52:48 / 10:54:00 |

Dazu ein Faktenfehler im Kopf (sieben statt sechs PRs), korrigiert. Ohne Fund geprüft:
Commit-Titel aller sechs PRs (5× `feat(gesundheit)`, 1× `docs(handover)`), Refs statt Closes
mit Handschluss und vollständiger Tabelle, K5-Zeile in #621, Scope-Zeile vom 13.10., Merge und
Publish nur über Owner-Skripte.

## Self-Review

Meta-Agent (Phase 5, nur Report und Werkzeuge) meldete acht Punkte; übernommen: Slug ohne
Begründung aus `gate_candidates` entfernt, §5a auf eine Antwort (umbauen) gebracht, „erster
Fall" präzisiert, Befund 7 als Hypothese gekennzeichnet, Streichbahn-Zählung korrigiert,
Grundlage für M5 genannt. Verworfen: `gates_caught`/`gates_verwandt` aus `recurring_findings`
streichen (laut Schema Teilmengen davon) und Score-Anker nur an Überlebenden (Rubrik verlangt
einen Befund-Anker, nicht dessen Überleben). `refuted_rate` 0.64 im Band.

## Streichbahn

Frage: welche Phase, welcher Melder, welche Skill-Sektion oder welches Gate gehört weg?
Antwort: keiner, weil jede teure Bahn dieser Retro das Ergebnis geändert hat — Phase 2.5 löste
den Zeitwiderspruch (Befund 2), Phase 3 verwarf acht Bewertungsbefunde, Phase 3b holte einen
davon zurück (Befund 4), korrigierte die Gate-Zuordnung von Befund 3 und fand Befund 11.

## Abschluss

- **getan:** Wirkungsbilanz, Artefaktliste, drei Finder, Phase-2.5-Klärung, zwei Skeptiker, Widerlegungsbahn, Soll-Ablauf, Längsschnitt, Anker in #567.
- **angenommen:** Der Read-Batch-Hinweis von `repo-session.sh start` hätte bei ungefilterter Ausgabe den zweiten Edit-Fehler verhindert (der erste zeigt, dass ein angezeigter Hinweis allein nicht reicht).
- **nicht verifizierbar:** Ob eine geschärfte Index-Probe alle roten Jobs verhindert hätte (kontrafaktisch).
- **offen geblieben:** §8.
